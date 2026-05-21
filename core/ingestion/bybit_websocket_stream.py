"""
Module: core/ingestion/bybit_websocket_stream.py
Responsibility: Bybit WebSocket streaming for real-time prices
Dependencies: aiohttp, redis, logger
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

import aiohttp
import redis.asyncio as aioredis

from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

MAX_RECONNECT_ATTEMPTS = 10
BACKOFF_BASE_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 30
STREAM_KEY_PREFIX = "market_data_bybit"

BYBIT_WS_URL = "wss://stream.bybit.com/v5/public/spot"
BYBIT_TESTNET_WS_URL = "wss://stream-testnet.bybit.com/v5/public/spot"


class BybitWebsocketStream:
    """Bybit WebSocket stream for real-time price updates.

    Uses Bybit V5 WebSocket API:
    - Production: wss://stream.bybit.com/v5/public/spot
    - Testnet: wss://stream-testnet.bybit.com/v5/public/spot
    """

    def __init__(
        self,
        symbols: list[str],
        redis_url: str = "redis://localhost:6379",
        testnet: bool = True,
        on_price: Optional[Callable[[MarketData], None]] = None,
    ):
        self._symbols = [s.upper().replace("USDT", "") + "USDT" for s in symbols]
        self._generic_symbols = symbols
        self._redis_url = redis_url
        self._testnet = testnet
        self._on_price = on_price

        self._ws_url = BYBIT_TESTNET_WS_URL if testnet else BYBIT_WS_URL

        self._running = False
        self._ws: Optional[aiohttp.ClientWebSocketResponse] = None
        self._session: Optional[aiohttp.ClientSession] = None
        self._redis: Optional[aioredis.Redis] = None

        self._messages_received = 0
        self._messages_processed = 0
        self._last_message_time: Optional[datetime] = None

    async def start(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url)
        self._session = aiohttp.ClientSession()
        self._running = True

        logger.info("bybit_ws_starting", symbols=self._generic_symbols, testnet=self._testnet)

        await self._connect_and_stream()

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        if self._redis:
            await self._redis.aclose()
        logger.info("bybit_ws_stopped")

    async def _connect_and_stream(self) -> None:
        attempt = 0
        last_heartbeat = asyncio.get_event_loop().time()

        while self._running and attempt < MAX_RECONNECT_ATTEMPTS:
            try:
                async with self._session.ws_connect(self._ws_url) as ws:
                    self._ws = ws
                    logger.info("bybit_ws_connected", attempt=attempt)

                    await self._subscribe(ws)

                    async for msg in ws:
                        if not self._running:
                            break

                        now = asyncio.get_event_loop().time()
                        if now - last_heartbeat > HEARTBEAT_INTERVAL_SECONDS:
                            logger.debug("bybit_ws_heartbeat")
                            last_heartbeat = now

                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message(msg.data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error("bybit_ws_error", error=str(ws.exception()))

            except Exception as e:
                attempt += 1
                backoff = BACKOFF_BASE_SECONDS ** attempt
                logger.warning(
                    "bybit_ws_reconnecting",
                    attempt=attempt,
                    backoff_seconds=backoff,
                    error=str(e),
                )

                if attempt >= MAX_RECONNECT_ATTEMPTS:
                    logger.critical("bybit_ws_max_reconnects_exceeded")
                    break

                await asyncio.sleep(backoff)

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        for symbol in self._symbols:
            subscribe_msg = {
                "op": "subscribe",
                "args": [f"kline.1m.{symbol}"],
            }
            await ws.send_json(subscribe_msg)

        logger.info("bybit_ws_subscribed", symbols=self._symbols)

    async def _handle_message(self, data: str) -> None:
        self._messages_received += 1

        try:
            msg = json.loads(data)

            if msg.get("topic", "").startswith("kline."):
                await self._handle_kline(msg)
            elif msg.get("e") == "heartbeat":
                logger.debug("bybit_heartbeat_received")

        except json.JSONDecodeError as e:
            logger.warning("bybit_ws_json_error", error=str(e))

    async def _handle_kline(self, msg: dict) -> None:
        try:
            topic = msg.get("topic", "")
            data = msg.get("data", {})

            if not data.get("confirm", False):
                return

            symbol = topic.split(".")[-1]
            generic_symbol = self._get_generic_symbol(symbol)

            k = data
            timestamp = datetime.utcfromtimestamp(int(k["start"]) / 1000)

            market_data = MarketData(
                timestamp=timestamp,
                symbol=generic_symbol,
                open=Decimal(k["open"]),
                high=Decimal(k["high"]),
                low=Decimal(k["low"]),
                close=Decimal(k["close"]),
                volume=Decimal(k["volume"]),
                quote_volume=Decimal(k.get("turnover", "0")),
                trades_count=int(k.get("confirm", 0)),
                source="bybit",
                asset_class="crypto",
            )

            self._messages_processed += 1
            self._last_message_time = datetime.utcnow()

            if self._on_price:
                await self._on_price(market_data)

            await self._publish_to_redis(market_data)

        except Exception as e:
            logger.warning("bybit_kline_handling_error", error=str(e))

    async def _publish_to_redis(self, data: MarketData) -> None:
        if not self._redis:
            return

        stream_key = f"{STREAM_KEY_PREFIX}:{data.symbol}"
        payload = {
            "timestamp": data.timestamp.isoformat(),
            "symbol": data.symbol,
            "open": str(data.open),
            "high": str(data.high),
            "low": str(data.low),
            "close": str(data.close),
            "volume": str(data.volume),
            "exchange": "bybit",
        }
        await self._redis.xadd(stream_key, payload, maxlen=1000)

    def _get_generic_symbol(self, bybit_symbol: str) -> str:
        return bybit_symbol.replace("USDT", "")

    def get_stats(self) -> dict:
        return {
            "messages_received": self._messages_received,
            "messages_processed": self._messages_processed,
            "last_message_time": self._last_message_time,
            "running": self._running,
        }


async def create_bybit_stream(
    symbols: list[str],
    redis_url: str = "redis://localhost:6379",
    testnet: bool = True,
    on_price: Optional[Callable[[MarketData], None]] = None,
) -> BybitWebsocketStream:
    stream = BybitWebsocketStream(
        symbols=symbols,
        redis_url=redis_url,
        testnet=testnet,
        on_price=on_price,
    )
    await stream.start()
    return stream