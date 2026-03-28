"""
Module: core/risk/kill_switch.py
Responsibility: Automatic circuit breakers for trading — takes precedence over ALL logic
Dependencies: settings, logger, alert_engine
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from core.config.settings import Settings
from core.observability.logger import get_logger

logger = get_logger(__name__)


class KillSwitchState:
    def __init__(
        self, daily_loss_limit: float, max_consecutive_losses: int, max_drawdown: float
    ):
        self.active: bool = False
        self.triggered_at: datetime | None = None
        self.triggered_by: str | None = None
        self.daily_loss_current: float = 0.0
        self.daily_loss_limit: float = daily_loss_limit
        self.consecutive_losses: int = 0
        self.max_consecutive_losses: int = max_consecutive_losses
        self.max_drawdown: float = max_drawdown
        self.reset_at: datetime | None = None


class AbcKillSwitch(ABC):
    @abstractmethod
    def is_active(self) -> bool: ...

    @abstractmethod
    def check_and_trigger(
        self, daily_pnl_pct: float, drawdown_current: float, recent_trades: list
    ) -> None: ...

    @abstractmethod
    def reset(self, admin_token: str) -> None: ...


class KillSwitch(AbcKillSwitch):
    """
    Circuit breakers — cannot be bypassed by any business logic.
    Only admin role can reset manually.
    """

    def __init__(self, settings: Settings):
        self._settings = settings
        self.state = KillSwitchState(
            daily_loss_limit=settings.DAILY_LOSS_LIMIT_PCT,
            max_consecutive_losses=settings.MAX_CONSECUTIVE_LOSSES,
            max_drawdown=settings.MAX_DRAWDOWN_PCT,
        )

    def is_active(self) -> bool:
        return self.state.active

    def check_and_trigger(
        self, daily_pnl_pct: float, drawdown_current: float, recent_trades: list
    ) -> None:
        self.state.daily_loss_current = daily_pnl_pct

        if daily_pnl_pct <= -self._settings.DAILY_LOSS_LIMIT_PCT:
            self._trigger("daily_loss_limit")
            return

        if drawdown_current >= self._settings.MAX_DRAWDOWN_PCT:
            self._trigger("max_drawdown")
            return

        consecutive = self._count_consecutive_losses(recent_trades)
        self.state.consecutive_losses = consecutive
        if consecutive >= self._settings.MAX_CONSECUTIVE_LOSSES:
            self._trigger("consecutive_losses")

    def _trigger(self, reason: str) -> None:
        if self.state.active:
            return
        self.state.active = True
        self.state.triggered_by = reason
        self.state.triggered_at = datetime.utcnow()
        logger.critical(
            "kill_switch_triggered",
            reason=reason,
            daily_pnl=self.state.daily_loss_current,
            limit=self.state.daily_loss_limit,
        )

    def _count_consecutive_losses(self, recent_trades: list) -> int:
        count = 0
        for trade in reversed(recent_trades):
            pnl = (
                trade.get("net_pnl", 0)
                if isinstance(trade, dict)
                else getattr(trade, "net_pnl", 0)
            )
            if pnl < 0:
                count += 1
            else:
                break
        return count

    def reset(self, admin_token: str) -> None:
        """Only admin can reset. Token validation happens at API layer."""
        logger.warning("kill_switch_reset", triggered_by=self.state.triggered_by)
        self.state.active = False
        self.state.triggered_by = None
        self.state.triggered_at = None
        self.state.reset_at = datetime.utcnow()
