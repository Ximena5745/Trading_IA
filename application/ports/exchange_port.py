"""
Port: IExchangePort
Responsibility: Interface for exchange connectivity (Binance, OANDA, etc.)
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from domain.entities import Order, Signal


class IExchangePort(ABC):
    """Abstract interface for exchange adapters."""

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to exchange."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to exchange."""
        ...

    @abstractmethod
    async def get_balance(self) -> dict[str, float]:
        """Get account balance."""
        ...

    @abstractmethod
    async def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol."""
        ...

    @abstractmethod
    async def get_historical_klines(
        self,
        symbol: str,
        interval: str,
        start_time: datetime,
        end_time: datetime,
    ) -> list[dict]:
        """Fetch historical klines/candles."""
        ...

    @abstractmethod
    async def place_order(self, signal: Signal, quantity: float) -> Order:
        """Place order based on signal."""
        ...

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order."""
        ...

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """Get status of an order."""
        ...

    @abstractmethod
    async def get_positions(self) -> list[dict]:
        """Get all open positions."""
        ...

    @property
    @abstractmethod
    def exchange_name(self) -> str:
        """Name of the exchange."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Connection status."""
        ...