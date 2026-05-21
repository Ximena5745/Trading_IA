"""
Module: core/risk/volatility_targeting.py
Responsibility: Ajustar tamaño de posición para mantener volatilidad objetivo.
  - target_annual_vol: 10% por defecto
  - Escalar inversamente a volatilidad realizada
  - Clip entre 20% y 200% del tamaño base
Dependencies: numpy, pandas
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.observability.logger import get_logger

logger = get_logger(__name__)


class VolatilityTargetingEngine:
    """
    Engine de targeting de volatilidad.

    M5.3: Volatility Targeting - exposure escala inversamente a vol realizada.
    """

    def __init__(
        self,
        target_annual_vol: float = 0.10,
        min_scale: float = 0.20,
        max_scale: float = 2.0,
        window: int = 20,
    ):
        self._target_vol = target_annual_vol
        self._min_scale = min_scale
        self._max_scale = max_scale
        self._window = window

    def calculate_scale_factor(self, returns: pd.Series) -> float:
        """
        Calcular factor de escala basado en volatilidad realizada.
        - Si vol > target: reducir exposición
        - Si vol < target: aumentar exposición
        """
        if len(returns) < 2:
            return 1.0

        realized_vol = returns.std() * np.sqrt(252 * 24)
        if realized_vol <= 0:
            logger.warning("zero_volatility_detected")
            return 1.0

        ratio = self._target_vol / realized_vol
        scale = np.clip(ratio, self._min_scale, self._max_scale)

        logger.debug(
            "volatility_targeting_calc",
            target=self._target_vol,
            realized=realized_vol,
            scale=scale,
        )
        return scale

    def scale_position(
        self,
        base_quantity: float,
        returns: pd.Series,
    ) -> float:
        """Escalar posición basándose en volatilidad."""
        scale = self.calculate_scale_factor(returns)
        return base_quantity * scale

    def get_current_volatility_regime(self, returns: pd.Series) -> str:
        """Determinar régimen de volatilidad actual."""
        if len(returns) < self._window:
            return "unknown"

        vol = returns.tail(self._window).std() * np.sqrt(252 * 24)
        percentile = (returns < vol).mean()

        if percentile > 0.9:
            return "extreme"
        if percentile > 0.75:
            return "high"
        if percentile > 0.25:
            return "normal"
        return "low"