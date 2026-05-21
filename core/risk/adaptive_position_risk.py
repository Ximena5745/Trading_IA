"""
Module: core/risk/adaptive_position_risk.py
Responsibility: Adaptive SL/TP basado en régimen de mercado y perfil de riesgo.
  ATR_MULTIPLIERS por régimen:
    - BULL_TRENDING_STRONG: 1.5
    - BEAR_TRENDING_STRONG: 2.0
    - RANGE_BOUND_NARROW: 1.0
    - RANGE_BOUND_WIDE: 2.0
    - VOLATILE_CRASH: 3.0
    - TRANSITION: 2.5
Dependencies: core.models
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.models import MarketRegime
from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RiskProfile:
    risk_multiplier: float = 1.0
    min_confidence: float = 0.5
    max_position_pct: float = 0.10


class AdaptivePositionRisk:
    """
    Engine de riesgo adaptativo basado en régimen.

    M5.2: Adaptive Position Risk (SL/TP dinámico por régimen).
    """

    ATR_MULTIPLIERS = {
        MarketRegime.BULL_TRENDING: 1.5,
        MarketRegime.BEAR_TRENDING: 2.0,
        MarketRegime.SIDEWAYS_LOW_VOL: 1.0,
        MarketRegime.SIDEWAYS_HIGH_VOL: 2.0,
        MarketRegime.VOLATILE_CRASH: 3.0,
    }

    def __init__(self, profile: Optional[RiskProfile] = None):
        self._profile = profile or RiskProfile()

    def calculate_dynamic_sl(
        self,
        atr: float,
        regime: MarketRegime,
        entry_price: float,
        direction: str,
    ) -> float:
        """Calcular stop loss dinámico basado en régimen."""
        base_multiplier = self.ATR_MULTIPLIERS.get(regime, 2.0)
        multiplier = base_multiplier * self._profile.risk_multiplier
        sl_distance = atr * multiplier

        if direction == "BUY":
            return entry_price - sl_distance
        return entry_price + sl_distance

    def calculate_dynamic_tp(
        self,
        atr: float,
        regime: MarketRegime,
        entry_price: float,
        sl_price: float,
        direction: str,
        model_confidence: float,
    ) -> float:
        """Calcular take profit proporcional al R:R mínimo y confianza."""
        min_rr = 1.5 if model_confidence < 0.7 else 2.0

        risk = abs(entry_price - sl_price)
        reward = risk * min_rr

        if direction == "BUY":
            return entry_price + reward
        return entry_price - reward

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        sl_price: float,
        risk_pct: float = 0.01,
    ) -> float:
        """Calcular tamaño de posición basado en riesgo."""
        risk_amount = capital * risk_pct
        risk_per_unit = abs(entry_price - sl_price)

        if risk_per_unit == 0:
            return 0.0

        qty = risk_amount / risk_per_unit
        max_qty = (capital * self._profile.max_position_pct) / entry_price

        return min(qty, max_qty)