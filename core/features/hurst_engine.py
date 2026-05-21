"""
Module: core/features/hurst_engine.py
Responsibility: Hurst Exponent rolling calculation for strategy selection.
  - H > 0.55 → trending → activar momentum strategies
  - H < 0.45 → mean-reverting → activar mean reversion strategies
  - 0.45 ≤ H ≤ 0.55 → random walk → reducir exposición
  Ventanas: 100, 250, 500 barras (consenso de tres ventanas)
Dependencies: numpy, pandas
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.observability.logger import get_logger

logger = get_logger(__name__)


class HurstEngine:
    """
    Hurst Exponent rolling por activo para selección de estrategia.

    M3.5: Hurst Exponent como feature y selector de estrategia.
    """

    def __init__(self, windows: list[int] = None):
        self.windows = windows or [100, 250, 500]

    def _compute_hurst(self, prices: pd.Series, window: int) -> float:
        """Calculate Hurst exponent using R/S analysis for a window."""
        if len(prices) < window:
            return 0.5

        try:
            returns = np.diff(np.log(prices.values))
            n = len(returns)

            if n < window:
                return 0.5

            subseries = []
            for size in [2, 4, 8, 16, 32]:
                if n >= size:
                    n_subseries = n // size
                    if n_subseries < 2:
                        continue
                    rs_values = []
                    for i in range(n_subseries):
                        sub = returns[i * size:(i + 1) * size]
                        if len(sub) < 2:
                            continue
                        mean_sub = np.mean(sub)
                        cumdev = np.cumsum(sub - mean_sub)
                        R = np.max(cumdev) - np.min(cumdev)
                        S = np.std(sub, ddof=1)
                        if S > 0:
                            rs_values.append(R / S)
                    if rs_values:
                        subseries.append(np.mean(rs_values))

            if len(subseries) >= 2:
                log_n = np.log(np.array([2, 4, 8, 16, 32][:len(subseries)]))
                log_rs = np.log(np.array(subseries))
                if len(log_n) > 1:
                    coeffs = np.polyfit(log_n, log_rs, 1)
                    return max(0.0, min(1.0, coeffs[0]))
        except Exception as e:
            logger.debug("hurst_calc_error", error=str(e))

        return 0.5

    def calculate_rolling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Hurst exponent for multiple windows."""
        close = df["close"]
        result = df.copy()

        for window in self.windows:
            col_name = f"hurst_{window}"
            result[col_name] = close.rolling(window=window, min_periods=window).apply(
                lambda x: self._compute_hurst(pd.Series(x), len(x)), raw=False
            )

        result["hurst_consensus"] = result[[f"hurst_{w}" for w in self.windows]].mean(axis=1)
        return result

    def get_regime(self, hurst_value: float) -> str:
        """Determine market regime based on Hurst value."""
        if hurst_value > 0.55:
            return "trending"
        if hurst_value < 0.45:
            return "mean_reverting"
        return "random_walk"

    def select_strategy(self, hurst_value: float) -> list[str]:
        """Select optimal strategies based on Hurst value."""
        regime = self.get_regime(hurst_value)

        if regime == "trending":
            return ["TSMOM", "CrossSectionalMomentum", "VolatilityBreakout"]
        if regime == "mean_reverting":
            return ["StatisticalArbitrage", "VWAPReversion", "PairsTrading"]
        return ["ReducedExposure", "TrendFollowing"]