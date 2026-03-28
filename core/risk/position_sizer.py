"""
Module: core/risk/position_sizer.py
Responsibility: Calculate position size based on risk parameters
Dependencies: settings, constants
"""

from __future__ import annotations

from core.config.constants import HARD_LIMITS
from core.config.settings import Settings
from core.observability.logger import get_logger

logger = get_logger(__name__)


class PositionSizer:
    def __init__(self, settings: Settings):
        self._settings = settings

    def fixed_fractional(
        self, available_capital: float, entry_price: float, stop_loss: float
    ) -> float:
        """Risk MAX_RISK_PER_TRADE_PCT of available capital."""
        risk_pct = min(
            self._settings.MAX_RISK_PER_TRADE_PCT,
            HARD_LIMITS["max_risk_per_trade_pct"],
        )
        capital_at_risk = available_capital * risk_pct
        price_risk = abs(entry_price - stop_loss)
        if price_risk == 0:
            logger.warning(
                "position_sizer_zero_price_risk", entry=entry_price, sl=stop_loss
            )
            return 0.0
        quantity = capital_at_risk / price_risk
        logger.info(
            "position_sized",
            quantity=round(quantity, 6),
            capital_at_risk=capital_at_risk,
            price_risk=price_risk,
        )
        return round(quantity, 6)

    def apply_symbol_cap(
        self, quantity: float, entry_price: float, total_capital: float
    ) -> float:
        """Ensure no single position exceeds max_position_single_symbol_pct."""
        max_value = total_capital * HARD_LIMITS["max_position_single_symbol_pct"]
        position_value = quantity * entry_price
        if position_value > max_value:
            capped = max_value / entry_price
            logger.warning(
                "position_capped_by_symbol_limit",
                original=quantity,
                capped=round(capped, 6),
            )
            return round(capped, 6)
        return quantity
