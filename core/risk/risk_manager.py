"""
Module: core/risk/risk_manager.py
Responsibility: Validate signals and enforce all risk limits
Dependencies: settings, kill_switch, position_sizer, constants
"""
from __future__ import annotations

from core.config.constants import HARD_LIMITS
from core.config.settings import Settings
from core.observability.logger import get_logger
from core.risk.kill_switch import KillSwitch
from core.risk.position_sizer import PositionSizer

logger = get_logger(__name__)


class RiskManager:
    def __init__(self, settings: Settings, kill_switch: KillSwitch):
        self._settings = settings
        self._kill_switch = kill_switch
        self._sizer = PositionSizer(settings)

    def validate_signal(self, signal: dict, portfolio: dict) -> tuple[bool, str]:
        """Returns (approved, rejection_reason)."""
        if self._kill_switch.is_active():
            reason = f"Kill switch active: {self._kill_switch.state.triggered_by}"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        risk_exposure = portfolio.get("risk_exposure", 0.0)
        if risk_exposure >= self._settings.MAX_PORTFOLIO_RISK_PCT:
            reason = f"Portfolio risk at maximum ({risk_exposure:.1%})"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        drawdown = portfolio.get("drawdown_current", 0.0)
        if drawdown >= self._settings.MAX_DRAWDOWN_PCT:
            reason = f"Max drawdown reached ({drawdown:.1%})"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        rr = signal.get("risk_reward_ratio", 0.0)
        if rr < HARD_LIMITS["min_risk_reward_ratio"]:
            reason = f"R:R ratio too low ({rr:.2f} < {HARD_LIMITS['min_risk_reward_ratio']})"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        return True, ""

    def calculate_position_size(
        self,
        signal: dict,
        portfolio: dict,
        instrument=None,   # Optional[InstrumentConfig] — routes forex/CFD sizing
    ) -> float:
        available = portfolio.get("available_capital", 0.0)
        total     = portfolio.get("total_capital", 0.0)
        entry     = signal.get("entry_price", 0.0)
        sl        = signal.get("stop_loss", 0.0)
        symbol    = signal.get("symbol", "")

        return self._sizer.calculate(
            symbol=symbol,
            available_capital=available,
            total_capital=total,
            entry_price=entry,
            stop_loss=sl,
            instrument=instrument,
        )

    def update_kill_switch(self, portfolio: dict, recent_trades: list) -> None:
        self._kill_switch.check_and_trigger(
            daily_pnl_pct=portfolio.get("daily_pnl_pct", 0.0),
            drawdown_current=portfolio.get("drawdown_current", 0.0),
            recent_trades=recent_trades,
        )
