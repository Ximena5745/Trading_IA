"""
Module: core/ingestion/websocket_stream.py
Responsibility: Binance WebSocket with exponential backoff reconnection
Dependencies: python-binance, redis, data_validator, logger
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from decimal import Decimal

import redis.asyncio as aioredis
from binance import AsyncClient, BinanceSocketManager

from core.exceptions import DataValidationError
from core.ingestion.data_validator import DataValidator
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

MAX_RECONNECT_ATTEMPTS = 10
BACKOFF_BASE_SECONDS = 2
HEARTBEAT_INTERVAL_SECONDS = 30
STREAM_KEY_PREFIX = "market_data"


class BinanceWebsocketStream:
    def __init__(
        self,
        client: AsyncClient,
        redis_url: str,
        symbols: list[str],
        interval: str = "1h",
    ):
        self._client = client
        self._redis_url = redis_url
        self._symbols = symbols
        self._interval = interval
        self._validator = DataValidator()
        self._running = False
        self._redis: aioredis.Redis | None = None

    async def start(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url)
        self._running = True
        await asyncio.gather(*[self._stream_symbol(s) for s in self._symbols])

    async def stop(self) -> None:
        self._running = False
        if self._redis:
            await self._redis.aclose()
        logger.info("websocket_stream_stopped")

    async def _stream_symbol(self, symbol: str) -> None:
        attempt = 0
        while self._running and attempt < MAX_RECONNECT_ATTEMPTS:
            try:
                await self._connect_and_stream(symbol)
                attempt = 0  # reset on successful run
            except Exception as e:
                attempt += 1
                backoff = BACKOFF_BASE_SECONDS**attempt
                logger.warning(
                    "websocket_reconnecting",
                    symbol=symbol,
                    attempt=attempt,
                    backoff_seconds=backoff,
                    error=str(e),
                )
                if attempt >= 3:
                    logger.error(
                        "websocket_repeated_failures", symbol=symbol, attempt=attempt
                    )
                    # TODO: send Telegram alert here (Fase 5)
                if attempt >= MAX_RECONNECT_ATTEMPTS:
                    logger.critical("websocket_max_reconnects_exceeded", symbol=symbol)
                    break
                await asyncio.sleep(backoff)

    async def _connect_and_stream(self, symbol: str) -> None:
        bsm = BinanceSocketManager(self._client)
        stream = bsm.kline_socket(symbol, self._interval)

        async with stream as ts:
            logger.info("websocket_connected", symbol=symbol, interval=self._interval)
            last_heartbeat = asyncio.get_event_loop().time()

            while self._running:
                msg = await ts.recv()
                now = asyncio.get_event_loop().time()

                # Heartbeat to detect zombie connections
                if now - last_heartbeat > HEARTBEAT_INTERVAL_SECONDS:
                    logger.debug("websocket_heartbeat", symbol=symbol)
                    last_heartbeat = now

                if msg and msg.get("e") == "kline" and msg["k"]["x"]:  # closed candle
                    await self._handle_kline(msg["k"])

    async def _handle_kline(self, k: dict) -> None:
        try:
            data = MarketData(
                timestamp=datetime.utcfromtimestamp(k["t"] / 1000),
                symbol=k["s"],
                open=Decimal(k["o"]),
                high=Decimal(k["h"]),
                low=Decimal(k["l"]),
                close=Decimal(k["c"]),
                volume=Decimal(k["v"]),
                quote_volume=Decimal(k["q"]),
                trades_count=int(k["n"]),
                taker_buy_volume=Decimal(k["V"]),
            )
            self._validator.validate_market_data(data)
            await self._publish_to_redis(data)
        except (DataValidationError, Exception) as e:
            stream_key = f"dead_letter:{k.get('s', 'unknown')}"
            if self._redis:
                await self._redis.xadd(
                    stream_key, {"raw": json.dumps(k), "error": str(e)}
                )
            logger.warning("kline_validation_failed", error=str(e))

    async def _publish_to_redis(self, data: MarketData) -> None:
        stream_key = f"{STREAM_KEY_PREFIX}:{data.symbol}"
        payload = {
            "timestamp": data.timestamp.isoformat(),
            "symbol": data.symbol,
            "open": str(data.open),
            "high": str(data.high),
            "low": str(data.low),
            "close": str(data.close),
            "volume": str(data.volume),
            "quote_volume": str(data.quote_volume),
            "trades_count": str(data.trades_count),
            "taker_buy_volume": str(data.taker_buy_volume),
        }
        if self._redis:
            await self._redis.xadd(stream_key, payload, maxlen=1000)
            logger.debug("kline_published", symbol=data.symbol, stream=stream_key)
