"""
Module: core/ingestion/exchange_selector.py
Responsibility: Select appropriate exchange client based on symbol/asset class
Dependencies: exchange clients, logger
"""
from __future__ import annotations

from typing import Optional

from core.observability.logger import get_logger

logger = get_logger(__name__)


class ExchangeSelector:
    """Select appropriate exchange client based on symbol or asset class.

    Maps:
    - Crypto symbols -> Binance (primary) or Bybit (fallback)
    - Forex symbols -> MT5 (primary) or OANDA (fallback)
    - Indices -> MT5 (primary) or IB (fallback)
    - Commodities -> MT5 (primary) or OANDA (fallback)
    """

    DEFAULT_MAPPING = {
        "crypto": "binance",
        "forex": "mt5",
        "indices": "mt5",
        "commodities": "mt5",
    }

    FALLBACK_MAPPING = {
        "crypto": "bybit",
        "forex": "oanda",
        "indices": "ib",
        "commodities": "oanda",
    }

    def __init__(self, primary_clients: dict, fallback_clients: dict = None):
        self._primary_clients = primary_clients
        self._fallback_clients = fallback_clients or {}

    def get_client(self, symbol: str, asset_class: str = None) -> tuple[Optional[any], str]:
        """Get appropriate client for symbol.

        Returns: (client, exchange_name) or (None, "none")
        """
        if asset_class is None:
            asset_class = self._infer_asset_class(symbol)

        primary_exchange = self.DEFAULT_MAPPING.get(asset_class, "binance")

        if primary_exchange in self._primary_clients:
            logger.debug("exchange_selected", symbol=symbol, exchange=primary_exchange, role="primary")
            return self._primary_clients[primary_exchange], primary_exchange

        fallback_exchange = self.FALLBACK_MAPPING.get(asset_class)
        if fallback_exchange and fallback_exchange in self._fallback_clients:
            logger.warning("using_fallback_exchange", symbol=symbol, fallback=fallback_exchange)
            return self._fallback_clients[fallback_exchange], fallback_exchange

        logger.error("no_exchange_available", symbol=symbol, asset_class=asset_class)
        return None, "none"

    def _infer_asset_class(self, symbol: str) -> str:
        symbol_upper = symbol.upper()

        if symbol_upper.endswith(("USDT", "BTC", "ETH")):
            return "crypto"

        if symbol_upper in ("EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "USDCHF"):
            return "forex"

        if symbol_upper in ("SPX500", "NAS100", "US30", "US500", "DE40", "UK100", "JP225"):
            return "indices"

        if symbol_upper.startswith(("XAU", "XAG", "XPT")) or symbol_upper in ("WTI", "BRENT", "NATGAS"):
            return "commodities"

        return "crypto"


def create_selector_from_registry() -> ExchangeSelector:
    """Create selector using registered exchanges in ExchangeRegistry."""
    from core.ingestion.exchange_registry import ExchangeRegistry

    primary = {}
    fallback = {}

    status = ExchangeRegistry.get_status()

    for exchange, info in status.items():
        if info.get("connected") or info.get("has_client"):
            asset_class = _exchange_to_asset_class(exchange)
            if asset_class in ("crypto", "forex"):
                if asset_class == "crypto" and not primary.get("binance"):
                    primary["binance"] = ExchangeRegistry.get_client(exchange)
                elif asset_class == "forex" and not primary.get("mt5"):
                    primary["mt5"] = ExchangeRegistry.get_client(exchange)

    return ExchangeSelector(primary, fallback)


def _exchange_to_asset_class(exchange: str) -> str:
    mapping = {
        "binance": "crypto",
        "bybit": "crypto",
        "oanda": "forex",
        "ib": "indices",
        "mt5": "forex",
        "alpha_vantage": "crypto",
    }
    return mapping.get(exchange, "crypto")