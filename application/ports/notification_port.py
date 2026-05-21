"""
Port: INotificationPort
Responsibility: Interface for notifications (Telegram, email, etc.)
"""
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional


class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class INotificationPort(ABC):
    """Abstract interface for notification systems."""

    @abstractmethod
    async def send_alert(
        self,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        title: Optional[str] = None,
    ) -> bool:
        """Send alert notification."""
        ...

    @abstractmethod
    async def send_signal_alert(
        self,
        symbol: str,
        action: str,
        confidence: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> bool:
        """Send trading signal alert."""
        ...

    @abstractmethod
    async def send_trade_alert(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        pnl: Optional[float] = None,
    ) -> bool:
        """Send trade execution alert."""
        ...

    @abstractmethod
    async def send_risk_alert(
        self,
        alert_type: str,
        message: str,
        current_value: float,
        threshold: float,
    ) -> bool:
        """Send risk-related alert (drawdown, kill switch, etc.)."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Connection status."""
        ...