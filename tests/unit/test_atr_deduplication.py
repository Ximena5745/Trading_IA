"""
Tests for the shared ATR calculation (core/features/indicators.calculate_atr_series).

Antes: core/features/indicators.py y core/risk/mtf_sl_tp_manager.py calculaban
ATR con formulas distintas (EWM/Wilder vs. SMA sobre True Range) -- riesgo de
divergencia numerica entre la senal y el sizing de riesgo (hallazgo de calidad
de la auditoria del 2026-07-25). Ahora ambos usan la misma funcion.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.features.indicators import calculate_atr_series
from core.risk.mtf_sl_tp_manager.atr import calculate_atr


def _make_ohlc(n: int = 60, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + rng.uniform(0.1, 1.0, n)
    low = close - rng.uniform(0.1, 1.0, n)
    return pd.DataFrame({"high": high, "low": low, "close": close})


class TestSharedATR:
    def test_calculate_atr_series_returns_full_series(self):
        df = _make_ohlc()
        atr = calculate_atr_series(df["high"], df["low"], df["close"], period=14)
        assert isinstance(atr, pd.Series)
        assert len(atr) == len(df)

    def test_mtf_atr_uses_same_math_as_indicators(self):
        """core.risk.mtf_sl_tp_manager.atr.calculate_atr debe coincidir con calculate_atr_series."""
        df = _make_ohlc()

        mtf_atr = calculate_atr(df, period=14)
        expected = calculate_atr_series(df["high"], df["low"], df["close"], period=14).iloc[-1]

        assert mtf_atr == pytest.approx(float(expected))

    def test_mtf_atr_returns_zero_for_insufficient_data(self):
        short_df = _make_ohlc(n=5)
        assert calculate_atr(short_df, period=14) == 0.0

    def test_mtf_atr_handles_none(self):
        assert calculate_atr(None, period=14) == 0.0
