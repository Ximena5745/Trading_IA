"""
Module: core/ingestion/base_client.py
Responsibility: Abstract interface for exchange clients
Dependencies: models
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import MarketData, Order


class ExchangeClient(ABC):
    @abstractmethod
    async def get_historical_klines(
        self, symbol: str, interval: str, limit: int
    ) -> list[MarketData]:
        """Fetch historical OHLCV candles."""
        ...

    @abstractmethod
    async def get_order_book(self, symbol: str, depth: int = 20) -> dict:
        """Fetch order book snapshot."""
        ...

    @abstractmethod
    async def place_order(
        self, symbol: str, side: str, quantity: float, **kwargs
    ) -> Order:
        """Submit an order to the exchange."""
        ...

    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Cancel an open order."""
        ...

    @abstractmethod
    async def get_account_balance(self) -> dict:
        """Fetch account balances."""
        ...
