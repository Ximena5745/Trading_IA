"""
Module: core/ingestion/unified_pipeline.py
Responsibility: Unified data pipeline for multi-exchange ingestion
M2.13: Unified Data Pipeline
Dependencies: exchange clients, data_validator, redis, logger
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional

import redis.asyncio as aioredis

from core.ingestion.data_validator import DataValidator
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)


class UnifiedDataPipeline:
    """Unified data pipeline that normalizes data from multiple exchanges.

    Supported exchanges:
    - Binance
    - Bybit
    - OANDA
    - Interactive Brokers
    - MetaTrader 5
    - Alpha Vantage

    Features:
    - Normalize data format across exchanges
    - Data validation
    - Redis caching
    - Error handling per exchange
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        enable_validation: bool = True,
    ):
        self._redis_url = redis_url
        self._enable_validation = enable_validation

        self._redis: Optional[aioredis.Redis] = None
        self._validator = DataValidator() if enable_validation else None

        self._clients = {}
        self._running = False

        self._cache_ttl = 300
        self._stream_prefix = "unified_market_data"

    async def initialize(self) -> None:
        self._redis = await aioredis.from_url(self._redis_url)
        self._running = True
        logger.info("unified_pipeline_initialized")

    async def shutdown(self) -> None:
        self._running = False
        for exchange_id, client in self._clients.items():
            if hasattr(client, "disconnect"):
                await client.disconnect()
        if self._redis:
            await self._redis.aclose()
        logger.info("unified_pipeline_shutdown")

    def register_client(self, exchange_id: str, client) -> None:
        self._clients[exchange_id] = client
        logger.info("client_registered", exchange=exchange_id)

    async def fetch_klines(
        self,
        exchange: str,
        symbol: str,
        interval: str = "1h",
        count: int = 500,
    ) -> list[MarketData]:
        """Fetch klines from specified exchange and normalize."""
        client = self._clients.get(exchange)

        if not client:
            raise ValueError(f"No client registered for exchange: {exchange}")

        try:
            if not hasattr(client, "get_klines"):
                raise AttributeError(f"Client {exchange} does not support get_klines")

            data = await client.get_klines(symbol, interval, count)

            normalized = [self._normalize_market_data(d, exchange) for d in data]

            if self._validator:
                for md in normalized:
                    self._validator.validate_market_data(md)

            await self._cache_klines(exchange, symbol, interval, normalized)

            logger.info(
                "klines_fetched",
                exchange=exchange,
                symbol=symbol,
                count=len(normalized),
            )

            return normalized

        except Exception as e:
            logger.error(
                "klines_fetch_failed",
                exchange=exchange,
                symbol=symbol,
                error=str(e),
            )
            raise

    async def fetch_latest(
        self,
        exchange: str,
        symbol: str,
    ) -> Optional[MarketData]:
        """Fetch latest price from specified exchange."""
        client = self._clients.get(exchange)

        if not client:
            raise ValueError(f"No client registered for exchange: {exchange}")

        try:
            if hasattr(client, "get_order_book"):
                order_book = await client.get_order_book(symbol)
                if order_book and "asks" in order_book and "bids" in order_book:
                    asks = order_book.get("asks", [])
                    bids = order_book.get("bids", [])

                    if asks and bids:
                        ask_price = Decimal(str(asks[0][0]))
                        bid_price = Decimal(str(bids[0][0]))
                        mid = (ask_price + bid_price) / 2

                        return MarketData(
                            timestamp=datetime.utcnow(),
                            symbol=symbol,
                            open=mid,
                            high=ask_price,
                            low=bid_price,
                            close=mid,
                            volume=Decimal(0),
                            source=exchange,
                        )

            return None

        except Exception as e:
            logger.error("latest_fetch_failed", exchange=exchange, symbol=symbol, error=str(e))
            return None

    def _normalize_market_data(self, data: MarketData, exchange: str) -> MarketData:
        """Normalize market data to standard format."""
        return MarketData(
            timestamp=data.timestamp,
            symbol=data.symbol.upper(),
            open=Decimal(str(data.open)),
            high=Decimal(str(data.high)),
            low=Decimal(str(data.low)),
            close=Decimal(str(data.close)),
            volume=Decimal(str(data.volume)),
            quote_volume=data.quote_volume,
            trades_count=data.trades_count,
            taker_buy_volume=data.taker_buy_volume,
            source=exchange,
            asset_class=data.asset_class or self._infer_asset_class(data.symbol, exchange),
        )

    def _infer_asset_class(self, symbol: str, exchange: str) -> str:
        symbol_upper = symbol.upper()

        if exchange in ("binance", "bybit", "alpha_vantage"):
            if symbol_upper.endswith("USDT") or symbol_upper.endswith("BTC"):
                return "crypto"
            return "crypto"

        if exchange in ("oanda", "ib"):
            if len(symbol_upper) == 6:
                return "forex"
            elif symbol_upper in ("SPX500", "NAS100", "US30", "DE40", "UK100"):
                return "indices"
            elif symbol_upper.startswith("XAU"):
                return "commodities"

        return "unknown"

    async def _cache_klines(
        self,
        exchange: str,
        symbol: str,
        interval: str,
        klines: list[MarketData],
    ) -> None:
        if not self._redis:
            return

        cache_key = f"klines:{exchange}:{symbol}:{interval}"

        try:
            cache_data = [
                {
                    "timestamp": k.timestamp.isoformat(),
                    "open": str(k.open),
                    "high": str(k.high),
                    "low": str(k.low),
                    "close": str(k.close),
                    "volume": str(k.volume),
                }
                for k in klines[-100:]
            ]

            await self._redis.set(
                cache_key,
                str(cache_data),
                ex=self._cache_ttl,
            )

        except Exception as e:
            logger.warning("cache_write_failed", error=str(e))

    async def get_cached_klines(
        self,
        exchange: str,
        symbol: str,
        interval: str,
    ) -> Optional[list[MarketData]]:
        """Get cached klines if available."""
        if not self._redis:
            return None

        cache_key = f"klines:{exchange}:{symbol}:{interval}"

        try:
            cached = await self._redis.get(cache_key)
            if cached:
                logger.info("cache_hit", exchange=exchange, symbol=symbol)
                return []
        except Exception:
            pass

        return None

    async def publish_to_stream(self, data: MarketData) -> None:
        """Publish normalized data to Redis stream."""
        if not self._redis:
            return

        stream_key = f"{self._stream_prefix}:{data.source}:{data.symbol}"

        payload = {
            "timestamp": data.timestamp.isoformat(),
            "symbol": data.symbol,
            "open": str(data.open),
            "high": str(data.high),
            "low": str(data.low),
            "close": str(data.close),
            "volume": str(data.volume),
            "source": data.source,
            "asset_class": data.asset_class or "unknown",
        }

        try:
            await self._redis.xadd(stream_key, payload, maxlen=1000)
        except Exception as e:
            logger.warning("stream_publish_failed", error=str(e))

    def get_exchange_status(self) -> dict:
        """Get connection status for all registered exchanges."""
        status = {}

        for exchange_id, client in self._clients.items():
            connected = False
            if hasattr(client, "is_connected"):
                connected = client.is_connected()
            elif hasattr(client, "_connected"):
                connected = getattr(client, "_connected", False)

            status[exchange_id] = {
                "connected": connected,
                "registered": True,
            }

        return status

    def is_healthy(self) -> bool:
        """Check if at least one exchange is connected."""
        if not self._clients:
            return False

        for client in self._clients.values():
            if hasattr(client, "is_connected"):
                if client.is_connected():
                    return True
            elif hasattr(client, "_connected"):
                if client._connected:
                    return True

        return False


async def create_unified_pipeline(
    redis_url: str = "redis://localhost:6379",
    enable_validation: bool = True,
) -> UnifiedDataPipeline:
    pipeline = UnifiedDataPipeline(redis_url, enable_validation)
    await pipeline.initialize()
    return pipeline