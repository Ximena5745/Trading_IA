"""
Module: core/ingestion/oanda_websocket_stream.py
Responsibility: OANDA WebSocket streaming for real-time prices
M2.8: OANDA WebSocket Streaming
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

from core.ingestion.exchange_adapter import to_oanda_symbol
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

MAX_RECONNECT_ATTEMPTS = 10
BACKOFF_BASE_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 30
STREAM_KEY_PREFIX = "market_data_oanda"


class OandaWebsocketStream:
    """OANDA WebSocket stream for real-time price updates.

    Uses OANDA's v3 streaming API:
    - Practice: wss://stream-fxpractice.oanda.com
    - Live: wss://stream-fxtrade.oanda.com
    """

    def __init__(
        self,
        api_key: str,
        account_id: str,
        symbols: list[str],
        redis_url: str = "redis://localhost:6379",
        environment: str = "practice",
        on_price: Optional[Callable[[MarketData], None]] = None,
    ):
        self._api_key = api_key
        self._account_id = account_id
        self._symbols = [to_oanda_symbol(s) for s in symbols]
        self._generic_symbols = symbols
        self._redis_url = redis_url
        self._environment = environment
        self._on_price = on_price

        self._ws_url = (
            "wss://stream-fxpractice.oanda.com/v3/accounts/{accountId}/prices"
            if environment == "practice"
            else "wss://stream-fxtrade.oanda.com/v3/accounts/{accountId}/prices"
        ).format(accountId=account_id)

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
        logger.info("oanda_ws_starting", symbols=self._generic_symbols)

        await self._connect_and_stream()

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        if self._redis:
            await self._redis.aclose()
        logger.info("oanda_ws_stopped")

    async def _connect_and_stream(self) -> None:
        attempt = 0
        last_heartbeat = asyncio.get_event_loop().time()

        while self._running and attempt < MAX_RECONNECT_ATTEMPTS:
            try:
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }

                async with self._session.ws_connect(
                    self._ws_url,
                    headers=headers,
                ) as ws:
                    self._ws = ws
                    logger.info("oanda_ws_connected", attempt=attempt)

                    await self._subscribe(ws)

                    async for msg in ws:
                        if not self._running:
                            break

                        now = asyncio.get_event_loop().time()
                        if now - last_heartbeat > HEARTBEAT_INTERVAL_SECONDS:
                            logger.debug("oanda_ws_heartbeat")
                            last_heartbeat = now

                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_message(msg.data)
                        elif msg.type == aiohttp.WSMsgType.ERROR:
                            logger.error("oanda_ws_error", error=str(ws.exception()))

            except Exception as e:
                attempt += 1
                backoff = BACKOFF_BASE_SECONDS ** attempt
                logger.warning(
                    "oanda_ws_reconnecting",
                    attempt=attempt,
                    backoff_seconds=backoff,
                    error=str(e),
                )

                if attempt >= MAX_RECONNECT_ATTEMPTS:
                    logger.critical("oanda_ws_max_reconnects_exceeded")
                    break

                await asyncio.sleep(backoff)

    async def _subscribe(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        subscribe_msg = {
            "type": "subscribe",
            "instruments": self._symbols,
        }
        await ws.send_json(subscribe_msg)
        logger.info("oanda_ws_subscribed", instruments=self._symbols)

    async def _handle_message(self, data: str) -> None:
        self._messages_received += 1

        try:
            msg = json.loads(data)

            msg_type = msg.get("type")

            if msg_type == "price":
                await self._handle_price(msg)
            elif msg_type == "heartbeat":
                logger.debug("oanda_heartbeat_received")
            elif msg_type == "error":
                logger.error("oanda_ws_api_error", error=msg.get("error"))

        except json.JSONDecodeError as e:
            logger.warning("oanda_ws_json_error", error=str(e))

    async def _handle_price(self, msg: dict) -> None:
        try:
            instrument = msg.get("instrument", "")
            bids = msg.get("bids", [])
            asks = msg.get("asks", [])

            if not bids or not asks:
                return

            bid_price = Decimal(bids[0]["price"])
            ask_price = Decimal(asks[0]["price"])
            mid_price = (bid_price + ask_price) / 2

            timestamp_str = msg.get("time", "")
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

            generic_symbol = self._get_generic_symbol(instrument)

            market_data = MarketData(
                timestamp=timestamp,
                symbol=generic_symbol,
                open=mid_price,
                high=ask_price,
                low=bid_price,
                close=mid_price,
                volume=Decimal(0),
                source="oanda",
                asset_class="forex",
            )

            self._messages_processed += 1
            self._last_message_time = datetime.utcnow()

            if self._on_price:
                await self._on_price(market_data)

            await self._publish_to_redis(market_data)

        except Exception as e:
            logger.warning("oanda_price_handling_error", error=str(e))

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
            "exchange": "oanda",
        }
        await self._redis.xadd(stream_key, payload, maxlen=1000)

    def _get_generic_symbol(self, oanda_symbol: str) -> str:
        for generic, oanda in zip(self._generic_symbols, self._symbols):
            if oanda == oanda_symbol:
                return generic
        return oanda_symbol.replace("_", "")

    def get_stats(self) -> dict:
        return {
            "messages_received": self._messages_received,
            "messages_processed": self._messages_processed,
            "last_message_time": self._last_message_time,
            "running": self._running,
        }


async def create_oanda_stream(
    api_key: str,
    account_id: str,
    symbols: list[str],
    redis_url: str = "redis://localhost:6379",
    environment: str = "practice",
    on_price: Optional[Callable[[MarketData], None]] = None,
) -> OandaWebsocketStream:
    stream = OandaWebsocketStream(
        api_key=api_key,
        account_id=account_id,
        symbols=symbols,
        redis_url=redis_url,
        environment=environment,
        on_price=on_price,
    )
    await stream.start()
    return stream