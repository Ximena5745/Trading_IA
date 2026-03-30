"""
Module: core/ingestion/exchange_adapter.py
Responsibility: Multi-exchange / multi-asset abstraction layer
Dependencies: base_client, logger

Supported asset classes:
  - crypto      → Binance, Bybit
  - forex       → OANDA (EUR/USD, GBP/USD, USD/JPY, etc.)
  - indices     → OANDA (SPX500, NAS100, US30, DE40, UK100, JP225)
  - commodities → OANDA (XAU/USD, XAG/USD, WTI Oil, Brent, Natural Gas)

OANDA covers forex, indices AND commodities via a single API, which means
adding one adapter unlocks three asset classes simultaneously.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

# ── Supported exchange/broker IDs ────────────────────────────────────────────
SUPPORTED_EXCHANGES = (
    # Crypto
    "binance",
    "bybit",
    # Multiactivos (Forex, Índices, Commodities, Acciones, Futuros)
    "ib",  # Interactive Brokers
    "mt5",  # MetaTrader 5
    # Alternativas
    "oanda",  # Forex + Indices + Commodities
    "alpha_vantage",  # Market data universal
)

# ── Asset class → recommended adapter ────────────────────────────────────────
ASSET_CLASS_ADAPTER: dict[str, str] = {
    "crypto": "binance",  # Binance es el estándar para cripto
    "forex": "ib",  # IB es el mejor para forex (latencia, spreads)
    "indices": "ib",  # IB: excelente cobertura de índices globales
    "commodities": "ib",  # IB: futuros de commodities
    "stocks": "ib",  # IB: acciones de múltiples mercados
    "futures": "ib",  # IB: futuros de alta liquidez
}


class ExchangeAdapter(ABC):
    """Normalised interface for any exchange or broker.

    Concrete adapters must map exchange-specific responses to core models
    so the rest of the system is exchange-agnostic.

    Each adapter declares which asset classes it supports via
    `supported_asset_classes`.
    """

    exchange_id: str = ""
    supported_asset_classes: tuple[str, ...] = ()

    # ── Connection lifecycle ───────────────────────────────────────────────

    @abstractmethod
    async def connect(self) -> None:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        ...

    # ── Market data ────────────────────────────────────────────────────────

    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
    ) -> list[MarketData]:
        ...

    @abstractmethod
    async def get_order_book(
        self,
        symbol: str,
        depth: int = 20,
    ) -> dict:
        ...

    # ── Account & trading ─────────────────────────────────────────────────

    @abstractmethod
    async def get_balance(self, asset: str = "USD") -> float:
        ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        client_order_id: Optional[str] = None,
    ) -> dict:
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        ...

    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> dict:
        ...

    # ── Normalisation helpers (shared) ────────────────────────────────────

    def normalise_symbol(self, symbol: str) -> str:
        """Ensure symbol is in exchange-native format.

        Override in concrete adapters when the exchange uses a different
        convention (e.g. OANDA uses "EUR_USD" instead of "EURUSD").
        """
        return symbol.upper().replace("-", "").replace("/", "")

    def log_request(self, method: str, endpoint: str) -> None:
        logger.debug(
            "exchange_request",
            exchange=self.exchange_id,
            method=method,
            endpoint=endpoint,
        )


# ── OANDA symbol normalisation helper ────────────────────────────────────────


def to_oanda_symbol(symbol: str) -> str:
    """Convert generic symbol to OANDA instrument format.

    Examples:
        EURUSD  → EUR_USD
        XAUUSD  → XAU_USD
        SPX500  → SPX500   (indices don't need underscore)
        USOIL   → WTICO_USD
    """
    _overrides = {
        "USOIL": "WTICO_USD",
        "UKOIL": "BCO_USD",
        "NATGAS": "NATGAS_USD",
        "WHEAT": "WHEAT_USD",
        "SPX500": "SPX500_USD",
        "NAS100": "NAS100_USD",
        "US30": "US30_USD",
        "DE40": "DE30_EUR",
        "UK100": "UK100_GBP",
        "JP225": "JP225_USD",
    }
    s = symbol.upper()
    if s in _overrides:
        return _overrides[s]
    # Forex pairs: EURUSD → EUR_USD
    if len(s) == 6 and s.isalpha():
        return f"{s[:3]}_{s[3:]}"
    # Metals: XAUUSD → XAU_USD
    if s.startswith(("XAU", "XAG", "XPT", "XPD")) and len(s) == 6:
        return f"{s[:3]}_{s[3:]}"
    return s


# ── Registry ─────────────────────────────────────────────────────────────────


class ExchangeAdapterRegistry:
    """Singleton registry that stores one adapter per exchange."""

    _adapters: dict[str, ExchangeAdapter] = {}

    @classmethod
    def register(cls, adapter: ExchangeAdapter) -> None:
        cls._adapters[adapter.exchange_id] = adapter
        logger.info(
            "exchange_adapter_registered",
            exchange=adapter.exchange_id,
            asset_classes=adapter.supported_asset_classes,
        )

    @classmethod
    def get(cls, exchange_id: str) -> ExchangeAdapter:
        adapter = cls._adapters.get(exchange_id)
        if not adapter:
            raise KeyError(f"No adapter registered for exchange: {exchange_id}")
        return adapter

    @classmethod
    def get_for_asset_class(cls, asset_class: str) -> ExchangeAdapter:
        """Return the best registered adapter for a given asset class."""
        preferred = ASSET_CLASS_ADAPTER.get(asset_class)
        if preferred and preferred in cls._adapters:
            return cls._adapters[preferred]
        # Fallback: scan for any adapter that supports the class
        for adapter in cls._adapters.values():
            if asset_class in adapter.supported_asset_classes:
                return adapter
        raise KeyError(
            f"No adapter registered for asset class '{asset_class}'. "
            f"Register one of: {ASSET_CLASS_ADAPTER.get(asset_class, 'oanda')}"
        )

    @classmethod
    def list_available(cls) -> list[str]:
        return list(cls._adapters.keys())
