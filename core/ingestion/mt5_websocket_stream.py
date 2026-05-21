"""
Module: core/ingestion/mt5_websocket_stream.py
Responsibility: MetaTrader 5 real-time data streaming
Dependencies: MetaTrader5, redis, logger

Note: MT5 no tiene WebSocket nativo - usa API de notificaciones
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

import redis.asyncio as aioredis

from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

STREAM_KEY_PREFIX = "market_data_mt5"
MT5_AVAILABLE = True

try:
    import MetaTrader5 as mt5
except ImportError:
    MT5_AVAILABLE = False


class MT5WebsocketStream:
    """MetaTrader 5 streaming for real-time prices.

    MT5 uses polling with notifications instead of WebSocket.
    Handles: Forex, Indices, Commodities, Stocks, Futures

    Connection:
    - Account number and server from .env
    - Must initialize MT5 terminal first
    """

    def __init__(
        self,
        symbols: list[str],
        redis_url: str = "redis://localhost:6379",
        account: int = 0,
        server: str = "",
        on_price: Optional[Callable[[MarketData], None]] = None,
    ):
        self._symbols = [s.upper() for s in symbols]
        self._redis_url = redis_url
        self._account = account
        self._server = server
        self._on_price = on_price

        self._running = False
        self._initialized = False
        self._redis: Optional[aioredis.Redis] = None
        self._last_prices = {}

        self._messages_received = 0
        self._messages_processed = 0
        self._last_message_time: Optional[datetime] = None

        self._poll_interval = 1.0

    async def start(self) -> None:
        if not MT5_AVAILABLE:
            raise RuntimeError("MetaTrader5 package not installed")

        self._redis = await aioredis.from_url(self._redis_url)
        self._running = True

        logger.info("mt5_ws_starting", symbols=self._symbols, account=self._account)

        if not mt5.initialize():
            error = mt5.last_error()
            logger.error("mt5_init_failed", error=error)
            raise RuntimeError(f"MT5 initialize failed: {error}")

        self._initialized = True
        logger.info("mt5_initialized", account=self._account)

        await self._poll_prices()

    async def stop(self) -> None:
        self._running = False
        if self._initialized:
            mt5.shutdown()
        if self._redis:
            await self._redis.aclose()
        logger.info("mt5_ws_stopped")

    async def _poll_prices(self) -> None:
        while self._running:
            try:
                for symbol in self._symbols:
                    await self._fetch_price(symbol)

                await asyncio.sleep(self._poll_interval)

            except Exception as e:
                logger.warning("mt5_poll_error", error=str(e))
                await asyncio.sleep(5)

    async def _fetch_price(self, symbol: str) -> None:
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 1)

            if rates is None or len(rates) == 0:
                return

            rate = rates[0]
            self._messages_received += 1

            market_data = MarketData(
                timestamp=datetime.fromtimestamp(rate["time"]),
                symbol=symbol,
                open=Decimal(str(rate["open"])),
                high=Decimal(str(rate["high"])),
                low=Decimal(str(rate["low"])),
                close=Decimal(str(rate["close"])),
                volume=Decimal(str(rate["tick_volume"])),
                source="mt5",
                asset_class=self._infer_asset_class(symbol),
            )

            self._messages_processed += 1
            self._last_message_time = datetime.utcnow()

            if self._on_price:
                await self._on_price(market_data)

            await self._publish_to_redis(market_data)

            self._last_prices[symbol] = market_data

        except Exception as e:
            logger.warning("mt5_fetch_price_error", symbol=symbol, error=str(e))

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
            "exchange": "mt5",
        }
        await self._redis.xadd(stream_key, payload, maxlen=1000)

    def _infer_asset_class(self, symbol: str) -> str:
        symbol_upper = symbol.upper()

        forex_pairs = ("EUR", "GBP", "USD", "JPY", "CHF", "AUD", "NZD", "CAD")
        if any(symbol_upper.startswith(p) for p in forex_pairs):
            return "forex"

        if symbol_upper in ("SPX500", "NAS100", "US30", "US500", "DE40", "UK100", "JP225"):
            return "indices"

        if symbol_upper.startswith(("XAU", "XAG", "XPT")):
            return "commodities"

        return "unknown"

    def get_stats(self) -> dict:
        return {
            "messages_received": self._messages_received,
            "messages_processed": self._messages_processed,
            "last_message_time": self._last_message_time,
            "running": self._running,
            "initialized": self._initialized,
            "symbols_tracked": list(self._last_prices.keys()),
        }


async def create_mt5_stream(
    symbols: list[str],
    redis_url: str = "redis://localhost:6379",
    account: int = 0,
    server: str = "",
    on_price: Optional[Callable[[MarketData], None]] = None,
) -> MT5WebsocketStream:
    stream = MT5WebsocketStream(
        symbols=symbols,
        redis_url=redis_url,
        account=account,
        server=server,
        on_price=on_price,
    )
    await stream.start()
    return stream