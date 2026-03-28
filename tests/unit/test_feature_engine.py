"""
Tests for FeatureEngine and indicators.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from core.exceptions import FeatureCalculationError
from core.features.feature_engineering import FeatureEngine
from core.features.feature_validator import FeatureValidator
from core.features.indicators import calculate_all


def make_ohlcv(n: int = 300, symbol: str = "BTCUSDT") -> pd.DataFrame:
    """Generate synthetic OHLCV data."""
    np.random.seed(42)
    base_price = 50000.0
    returns = np.random.normal(0, 0.01, n)
    close = base_price * np.cumprod(1 + returns)
    high = close * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = close * (1 - np.abs(np.random.normal(0, 0.005, n)))
    open_ = np.roll(close, 1)
    open_[0] = base_price
    volume = np.random.uniform(100, 1000, n)

    timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]

    return pd.DataFrame({
        "timestamp": timestamps,
        "symbol": symbol,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "quote_volume": volume * close,
        "taker_buy_volume": volume * 0.5,
    })


class TestIndicators:
    def test_all_indicators_calculated(self):
        df = make_ohlcv(300)
        result = calculate_all(df)
        expected = [
            "rsi_14", "rsi_7", "ema_9", "ema_21", "ema_50", "ema_200",
            "macd_line", "macd_signal", "macd_histogram",
            "atr_14", "bb_upper", "bb_lower", "bb_width",
            "vwap", "volume_sma_20", "volume_ratio", "obv",
            "trend_direction", "volatility_regime",
        ]
        for col in expected:
            assert col in result.columns, f"Missing column: {col}"

    def test_rsi_within_range(self):
        df = make_ohlcv(300)
        result = calculate_all(df)
        valid = result["rsi_14"].dropna()
        assert (valid >= 0).all() and (valid <= 100).all()

    def test_ema_200_requires_200_candles(self):
        df = make_ohlcv(250)
        result = calculate_all(df)
        assert result["ema_200"].notna().sum() > 0

    def test_raises_with_insufficient_data(self):
        df = make_ohlcv(50)
        with pytest.raises(FeatureCalculationError, match="at least"):
            calculate_all(df)

    def test_trend_direction_values(self):
        df = make_ohlcv(300)
        result = calculate_all(df)
        valid_values = {"bullish", "bearish", "sideways"}
        assert set(result["trend_direction"].unique()).issubset(valid_values)

    def test_volatility_regime_values(self):
        df = make_ohlcv(300)
        result = calculate_all(df)
        valid_values = {"low", "medium", "high", "extreme"}
        assert set(result["volatility_regime"].unique()).issubset(valid_values)

    def test_bb_upper_always_above_lower(self):
        df = make_ohlcv(300)
        result = calculate_all(df)
        valid = result.dropna(subset=["bb_upper", "bb_lower"])
        assert (valid["bb_upper"] >= valid["bb_lower"]).all()


class TestFeatureEngine:
    def test_returns_feature_set(self):
        engine = FeatureEngine()
        df = make_ohlcv(300)
        fs = engine.calculate(df)
        assert fs.symbol == "BTCUSDT"
        assert fs.version == "v1"
        assert 0 <= fs.rsi_14 <= 100

    def test_calculate_batch_length(self):
        engine = FeatureEngine()
        df = make_ohlcv(300)
        batch = engine.calculate_batch(df)
        assert len(batch) == 300

    def test_raises_on_insufficient_data(self):
        engine = FeatureEngine()
        df = make_ohlcv(50)
        with pytest.raises(FeatureCalculationError):
            engine.calculate(df)


class TestFeatureValidator:
    def test_validates_clean_features(self):
        engine = FeatureEngine()
        validator = FeatureValidator()
        df = make_ohlcv(300)
        fs = engine.calculate(df)
        result = validator.validate(fs)
        assert result is fs

    def test_detects_nan_in_critical_field(self):
        engine = FeatureEngine()
        validator = FeatureValidator()
        df = make_ohlcv(300)
        fs = engine.calculate(df)
        fs.rsi_14 = float("nan")
        with pytest.raises(FeatureCalculationError, match="NaN"):
            validator.validate(fs)
