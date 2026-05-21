"""
Module: core/risk/auto_adaptation.py
Responsibility: Adaptación automática al mercado basada en condiciones.
  Respuestas automáticas:
    - Volatilidad > P90: reducir position 50%, SL 3x ATR, desactivar mean reversion
    - Volatilidad < P10: activar range trading, reducir TP
    - ADX > 30: activar momentum, desactivar mean reversion
    - Hurst < 0.40: activar mean reversion, z-score strategies
    - Drawdown > 5% en 4h: kill switch parcial
    - Baja liquidez (Asian session): reducir tamaño 70%
    - Alta correlación: reducir exposición total
Dependencies: numpy, pandas, models
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from core.models import MarketRegime
from core.observability.logger import get_logger
from core.features.hurst_engine import HurstEngine

logger = get_logger(__name__)


@dataclass
class AdaptationAction:
    action_type: str
    description: str
    position_scale: float
    sl_multiplier: float
    tp_multiplier: float
    strategies_allowed: list[str]
    confidence_adjustment: float


class MarketAutoAdaptation:
    """
    Motor de adaptación automática a condiciones de mercado.

    M5.5: Adaptación automática al mercado (7 condiciones).
    """

    def __init__(self):
        self._hurst_engine = HurstEngine()
        self._volatility_percentiles: dict[str, tuple[float, float]] = {}
        self._last_action: Optional[AdaptationAction] = None

    def analyze_and_adapt(
        self,
        symbol: str,
        returns: pd.Series,
        adx: float,
        hurst: float,
        hour: int,
        drawdown_4h: float,
        correlation_avg: float,
        regime: MarketRegime,
    ) -> AdaptationAction:
        """Analizar condiciones y generar acción adaptativa."""
        vol_percentile = self._calculate_vol_percentile(symbol, returns)
        self._update_vol_percentiles(symbol, vol_percentile)

        position_scale = 1.0
        sl_mult = 1.0
        tp_mult = 1.0
        strategies = ["TSMOM", "MeanReversion", "StatisticalArbitrage"]
        conf_adj = 0.0
        action_type = "NORMAL"
        description_parts = []

        if vol_percentile > 0.9:
            action_type = "HIGH_VOL"
            position_scale = 0.5
            sl_mult = 3.0
            strategies = ["TSMOM"]
            conf_adj = -0.1
            description_parts.append("Volatility P90+ - reducir exposición, SL 3x")

        elif vol_percentile < 0.1:
            action_type = "LOW_VOL"
            position_scale = 1.2
            tp_mult = 0.8
            strategies = ["StatisticalArbitrage", "VWAPReversion"]
            description_parts.append("Volatility P10- - range trading")

        if adx > 30:
            strategies = ["TSMOM", "CrossSectionalMomentum"]
            description_parts.append(f"ADX {adx:.1f} > 30 - momentum")
        elif adx < 15:
            strategies = ["StatisticalArbitrage", "VWAPReversion"]
            description_parts.append(f"ADX {adx:.1f} < 15 - mean reversion")

        if hurst > 0.55:
            strategies = ["TSMOM", "Breakout"]
            description_parts.append(f"Hurst {hurst:.2f} > 0.55 - trending")
        elif hurst < 0.45:
            strategies = ["StatisticalArbitrage", "PairsTrading"]
            description_parts.append(f"Hurst {hurst:.2f} < 0.45 - mean reverting")

        if drawdown_4h > 0.05:
            action_type = "DRAWDOWN_ALERT"
            position_scale *= 0.5
            description_parts.append(f"Drawdown 4h {drawdown_4h:.1%} > 5%")

        if hour in [0, 1, 2, 3, 4, 5]:
            position_scale *= 0.7
            description_parts.append("Asian session - reducir 30%")

        if correlation_avg > 0.7:
            position_scale *= (1 - correlation_avg)
            description_parts.append(f"High correlation {correlation_avg:.2f}")

        if regime == MarketRegime.VOLATILE_CRASH:
            action_type = "CRISIS"
            position_scale = 0.1
            strategies = ["CashOnly"]
            description_parts.append("CRISIS regime - modo defensivo")

        action = AdaptationAction(
            action_type=action_type,
            description=" | ".join(description_parts) if description_parts else "Normal operation",
            position_scale=position_scale,
            sl_multiplier=sl_mult,
            tp_multiplier=tp_mult,
            strategies_allowed=strategies,
            confidence_adjustment=conf_adj,
        )

        self._last_action = action
        logger.info(
            "market_adaptation",
            symbol=symbol,
            action_type=action_type,
            position_scale=position_scale,
            description=action.description,
        )

        return action

    def _calculate_vol_percentile(self, symbol: str, returns: pd.Series) -> float:
        """Calcular percentil de volatilidad."""
        if len(returns) < 20:
            return 0.5

        current_vol = returns.tail(20).std()
        historical = self._volatility_percentiles.get(symbol, (0.01, 0.02))
        min_vol, max_vol = historical

        if max_vol <= min_vol:
            return 0.5

        percentile = (current_vol - min_vol) / (max_vol - min_vol)
        return np.clip(percentile, 0.0, 1.0)

    def _update_vol_percentiles(self, symbol: str, current: float) -> None:
        """Actualizar percentiles de volatilidad."""
        if symbol not in self._volatility_percentiles:
            self._volatility_percentiles[symbol] = (current, current)
        else:
            min_v, max_v = self._volatility_percentiles[symbol]
            min_v = min(min_v, current)
            max_v = max(max_v, current)
            self._volatility_percentiles[symbol] = (min_v, max_v)

    def get_last_action(self) -> Optional[AdaptationAction]:
        """Obtener última acción de adaptación."""
        return self._last_action