"""
Module: core/risk/risk_manager.py
Responsibility: Validate signals and enforce all risk limits
Dependencies: settings, kill_switch, position_sizer, constants
"""
from __future__ import annotations

from typing import Union

from core.config.constants import HARD_LIMITS
from core.config.settings import Settings
from core.models import Signal
from core.observability.logger import get_logger
from core.risk.kill_switch import KillSwitch
from core.risk.position_sizer import PositionSizer

logger = get_logger(__name__)


# QWQ-7: Risk exposure real: |entry-SL|*qty / capital
def calculate_real_risk_exposure(
    entry_price: float,
    stop_loss: float,
    quantity: float,
    total_capital: float
) -> float:
    """
    Calcula el riesgo real de una posición como porcentaje del capital.
    QWQ-7: |entry_price - stop_loss| * quantity / total_capital
    Esto mide el riesgo real (pérdida máxima potencial) vs el riesgo nominal.
    """
    if total_capital <= 0 or quantity <= 0 or entry_price <= 0:
        return 0.0

    price_risk = abs(entry_price - stop_loss)
    if price_risk == 0:
        return 0.0

    position_value = quantity * entry_price
    max_loss_pct = price_risk / entry_price  # Pérdida máxima como % del precio
    real_exposure = max_loss_pct * (position_value / total_capital)

    return real_exposure


class RiskManager:
    def __init__(self, settings: Settings, kill_switch: KillSwitch):
        self._settings = settings
        self._kill_switch = kill_switch
        self._sizer = PositionSizer(settings)

    def _to_dict(self, signal: Union[Signal, dict]) -> dict:
        """Convert Signal object to dict if needed."""
        if hasattr(signal, "model_dump"):
            return signal.model_dump()
        return signal

    def validate_signal(self, signal: Union[Signal, dict], portfolio: dict) -> tuple[bool, str]:
        """Returns (approved, rejection_reason)."""
        signal_dict = self._to_dict(signal)

        if self._kill_switch.is_active():
            state = self._kill_switch.state
            triggered_by = state.get("triggered_by") if isinstance(state, dict) else state.triggered_by
            reason = f"Kill switch active: {triggered_by}"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        # QWQ-7: Usar risk exposure real en lugar del nominal
        total_capital = portfolio.get("total_capital", 10000.0)
        entry = signal_dict.get("entry_price", 0.0)
        sl = signal_dict.get("stop_loss", 0.0)
        qty = signal_dict.get("quantity", 0.0)

        if entry > 0 and sl > 0 and qty > 0:
            risk_exposure = calculate_real_risk_exposure(entry, sl, qty, total_capital)
            logger.debug("real_risk_exposure_calculated", exposure=risk_exposure)
        else:
            risk_exposure = portfolio.get("risk_exposure", 0.0)

        if risk_exposure >= self._settings.MAX_PORTFOLIO_RISK_PCT:
            reason = f"Portfolio real risk at maximum ({risk_exposure:.1%})"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        drawdown = portfolio.get("drawdown_current", 0.0)
        if drawdown >= self._settings.MAX_DRAWDOWN_PCT:
            reason = f"Max drawdown reached ({drawdown:.1%})"
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        rr = signal_dict.get("risk_reward_ratio", 0.0)
        if rr < HARD_LIMITS["min_risk_reward_ratio"]:
            reason = (
                f"R:R ratio too low ({rr:.2f} < {HARD_LIMITS['min_risk_reward_ratio']})"
            )
            logger.warning("signal_rejected", reason=reason)
            return False, reason

        return True, ""

    def calculate_position_size(
        self,
        signal: dict,
        portfolio: dict,
        instrument=None,  # Optional[InstrumentConfig] — routes forex/CFD sizing
    ) -> float:
        available = portfolio.get("available_capital", 0.0)
        total = portfolio.get("total_capital", 0.0)
        entry = signal.get("entry_price", 0.0)
        sl = signal.get("stop_loss", 0.0)
        symbol = signal.get("symbol", "")

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
