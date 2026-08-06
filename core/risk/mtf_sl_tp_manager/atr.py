"""
Module: core/risk/mtf_sl_tp_manager/atr.py
Responsibility: Multi-timeframe ATR and volatility regime classification
Dependencies: numpy, pandas, core.features.indicators (shared ATR math)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from core.features.indicators import calculate_atr_series
from core.risk.mtf_sl_tp_manager.config import Timeframe


@dataclass
class ATRMultiTimeframe:
    """ATR calculado en múltiples timeframes."""
    atr_15m: float = 0.0
    atr_1h: float = 0.0
    atr_4h: float = 0.0
    atr_1d: float = 0.0

    @property
    def volatility_regime(self) -> str:
        """Determina el régimen de volatilidad basado en ratios."""
        if self.atr_4h > 0 and self.atr_1h > 0:
            ratio = self.atr_4h / self.atr_1h
            if ratio > 3.0:
                return "EXTREME"
            elif ratio > 2.0:
                return "HIGH"
            elif ratio > 1.5:
                return "ELEVATED"
            else:
                return "NORMAL"
        return "UNKNOWN"

    def get_atr_for_timeframe(self, tf: Timeframe) -> float:
        """Obtiene el ATR correspondiente al timeframe."""
        mapping = {
            Timeframe.M15: self.atr_15m,
            Timeframe.H1: self.atr_1h,
            Timeframe.H4: self.atr_4h,
            Timeframe.D1: self.atr_1d,
        }
        return mapping.get(tf, self.atr_1h)


def calculate_atr(df: Optional[pd.DataFrame], period: int = 14) -> float:
    """Calcula el ATR promedio (misma fórmula que core.features.indicators)."""
    if df is None or len(df) < period:
        return 0.0

    atr_series = calculate_atr_series(df['high'], df['low'], df['close'], period)
    atr = atr_series.iloc[-1]

    return float(atr) if not np.isnan(atr) else 0.0


def calculate_atr_mtf(
    df_1h: pd.DataFrame,
    df_4h: Optional[pd.DataFrame],
    df_1d: Optional[pd.DataFrame],
    df_15m: Optional[pd.DataFrame],
) -> ATRMultiTimeframe:
    """Calcula ATR en múltiples timeframes."""
    atr_1h = calculate_atr(df_1h, 14)
    atr_4h = calculate_atr(df_4h, 14) if df_4h is not None else atr_1h * 2
    atr_1d = calculate_atr(df_1d, 14) if df_1d is not None else atr_1h * 4
    atr_15m = calculate_atr(df_15m, 14) if df_15m is not None else atr_1h / 4

    return ATRMultiTimeframe(
        atr_15m=atr_15m,
        atr_1h=atr_1h,
        atr_4h=atr_4h,
        atr_1d=atr_1d,
    )
