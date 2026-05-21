"""
Module: core/ingestion/ib_websocket_stream.py
Responsibility: Interactive Brokers WebSocket streaming for real-time prices
M2.10: IB WebSocket Streaming
Dependencies: ib_insync, redis, logger
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Callable, Optional

import redis.asyncio as aioredis

from core.observability.logger import get_logger

logger = get_logger(__name__)

MAX_RECONNECT_ATTEMPTS = 10
BACKOFF_BASE_SECONDS = 2
STREAM_KEY_PREFIX = "market_data_ib"

IB_AVAILABLE = True
try:
    from ib_insync import IB, Forex, Index, Stock, ContFuture, Contract
except ImportError:
    IB_AVAILABLE = False


class IBWebsocketStream:
    """Interactive Brokers WebSocket stream for real-time price updates.

    Uses ib_insync to connect to TWS/IB Gateway and stream real-time data.
    Connection: TWS on port 7497 (live) or 7498 (paper)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        symbols: list[str] = None,
        redis_url: str = "redis://localhost:6379",
        is_paper: bool = True,
        on_price: Optional[Callable] = None,
    ):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.symbols = symbols or []
        self.redis_url = redis_url
        self.is_paper = is_paper
        self.on_price = on_price

        self._running = False
        self._ib: Optional[IB] = None
        self._redis: Optional[aioredis.Redis] = None
        self._contracts = {}
        self._bars = {}

        self._messages_received = 0
        self._messages_processed = 0
        self._last_message_time: Optional[datetime] = None

    async def start(self) -> None:
        if not IB_AVAILABLE:
            raise RuntimeError("ib_insync not installed")

        self._redis = await aioredis.from_url(self.redis_url)
        self._ib = IB()
        self._running = True

        logger.info("ib_ws_starting", symbols=self.symbols, port=self.port)

        await self._connect_and_stream()

    async def stop(self) -> None:
        self._running = False
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
        if self._redis:
            await self._redis.aclose()
        logger.info("ib_ws_stopped")

    async def _connect_and_stream(self) -> None:
        attempt = 0

        while self._running and attempt < MAX_RECONNECT_ATTEMPTS:
            try:
                await self._ib.connectAsync(
                    host=self.host,
                    port=self.port,
                    clientId=self.client_id,
                    readonly=True,
                )

                logger.info("ib_ws_connected", attempt=attempt)

                self._setup_contracts()
                self._run_event_loop()

                while self._running and self._ib.isConnected():
                    await asyncio.sleep(1)

            except Exception as e:
                attempt += 1
                backoff = BACKOFF_BASE_SECONDS ** attempt
                logger.warning(
                    "ib_ws_reconnecting",
                    attempt=attempt,
                    backoff_seconds=backoff,
                    error=str(e),
                )

                if attempt >= MAX_RECONNECT_ATTEMPTS:
                    logger.critical("ib_ws_max_reconnects_exceeded")
                    break

                await asyncio.sleep(backoff)

    def _setup_contracts(self) -> None:
        """Create IB contracts for each symbol."""
        for symbol in self.symbols:
            contract = self._create_contract(symbol)
            self._contracts[symbol] = contract
            self._bars[symbol] = None

            self._ib.reqMktData(contract, "", False, False)
            self._ib.pendingTickersEvent += self._on_pending_tickers

    def _create_contract(self, symbol: str) -> Contract:
        """Create IB contract based on symbol."""
        from ib_insync import Forex, Index, Stock, ContFuture

        symbol_upper = symbol.upper()

        if len(symbol_upper) == 6 and symbol_upper[:3] in (
            "EUR", "GBP", "USD", "AUD", "NZD", "CAD", "CHF", "JPY"
        ):
            return Forex(pair=symbol)
        elif symbol_upper in ("SPX500", "NAS100", "US30", "DE40", "UK100", "JP225"):
            return Index(symbol=symbol_upper, exchange="CME")
        elif symbol_upper.startswith("XAU") or symbol_upper.startswith("XAG"):
            return Forex(pair=symbol)
        else:
            return Stock(symbol=symbol, exchange="SMART", currency="USD")

    def _on_pending_tickers(self, tickers):
        """Handle pending ticker updates."""
        for ticker in tickers:
            if not ticker.contract:
                continue

            symbol = ticker.contract.symbol

            if ticker.bid and ticker.ask:
                mid = (ticker.bid + ticker.ask) / 2

                self._messages_received += 1
                self._messages_processed += 1
                self._last_message_time = datetime.utcnow()

                from core.models import MarketData

                market_data = MarketData(
                    timestamp=datetime.utcnow(),
                    symbol=symbol,
                    open=Decimal(str(mid)),
                    high=Decimal(str(ticker.ask)),
                    low=Decimal(str(ticker.bid)),
                    close=Decimal(str(mid)),
                    volume=Decimal(str(ticker.volume)) if ticker.volume else Decimal(0),
                    source="ib",
                )

                if self.on_price:
                    asyncio.create_task(self.on_price(market_data))

                asyncio.create_task(self._publish_to_redis(market_data))

    async def _publish_to_redis(self, data) -> None:
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
            "exchange": "ib",
        }
        await self._redis.xadd(stream_key, payload, maxlen=1000)

    def _run_event_loop(self) -> None:
        """Process IB messages in background."""
        if self._ib.isConnected():
            self._ib.sleep()

    def get_stats(self) -> dict:
        return {
            "messages_received": self._messages_received,
            "messages_processed": self._messages_processed,
            "last_message_time": self._last_message_time,
            "running": self._running,
            "connected": self._ib.isConnected() if self._ib else False,
        }


async def create_ib_stream(
    host: str = "127.0.0.1",
    port: int = 7498,
    client_id: int = 1,
    symbols: list[str] = None,
    redis_url: str = "redis://localhost:6379",
    on_price: Optional[Callable] = None,
) -> IBWebsocketStream:
    stream = IBWebsocketStream(
        host=host,
        port=port,
        client_id=client_id,
        symbols=symbols,
        redis_url=redis_url,
        is_paper=True,
        on_price=on_price,
    )
    await stream.start()
    return stream