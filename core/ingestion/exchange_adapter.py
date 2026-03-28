"""
Module: core/ingestion/exchange_adapter.py
Responsibility: Multi-exchange abstraction layer — normalises API differences
Dependencies: base_client, logger
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

SUPPORTED_EXCHANGES = ("binance", "bybit")


class ExchangeAdapter(ABC):
    """Normalised interface for any exchange.

    Concrete adapters must map exchange-specific responses to core models
    so the rest of the system is exchange-agnostic.
    """

    exchange_id: str = ""

    # ── Connection lifecycle ───────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    def is_connected(self) -> bool: ...

    # ── Market data ────────────────────────────────────────────────────────

    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
    ) -> list[MarketData]: ...

    @abstractmethod
    async def get_order_book(
        self,
        symbol: str,
        depth: int = 20,
    ) -> dict: ...

    # ── Account & trading ─────────────────────────────────────────────────

    @abstractmethod
    async def get_balance(self, asset: str = "USDT") -> float: ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        client_order_id: str | None = None,
    ) -> dict: ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> dict: ...

    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> dict: ...

    # ── Normalisation helpers (shared) ────────────────────────────────────

    def normalise_symbol(self, symbol: str) -> str:
        """Ensure symbol is in exchange-native format."""
        return symbol.upper().replace("-", "").replace("/", "")

    def log_request(self, method: str, endpoint: str) -> None:
        logger.debug(
            "exchange_request",
            exchange=self.exchange_id,
            method=method,
            endpoint=endpoint,
        )


class ExchangeAdapterRegistry:
    """Singleton registry that stores one adapter per exchange."""

    _adapters: dict[str, ExchangeAdapter] = {}

    @classmethod
    def register(cls, adapter: ExchangeAdapter) -> None:
        cls._adapters[adapter.exchange_id] = adapter
        logger.info("exchange_adapter_registered", exchange=adapter.exchange_id)

    @classmethod
    def get(cls, exchange_id: str) -> ExchangeAdapter:
        adapter = cls._adapters.get(exchange_id)
        if not adapter:
            raise KeyError(f"No adapter registered for exchange: {exchange_id}")
        return adapter

    @classmethod
    def list_available(cls) -> list[str]:
        return list(cls._adapters.keys())
