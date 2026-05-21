"""
Tests for AdaptivePositionRisk (M5.2) using real data.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest

from core.models import MarketRegime
from core.risk.adaptive_position_risk import AdaptivePositionRisk, RiskProfile


DATA_DIR = Path("data/raw")


def load_parquet(symbol: str, timeframe: str = "1h") -> pd.DataFrame:
    """Cargar datos parquet reales."""
    file_path = DATA_DIR / f"{symbol}_{timeframe}.parquet"
    if not file_path.exists():
        pytest.skip(f"Datos no encontrados: {file_path}")
    df = pd.read_parquet(file_path)
    return df


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calcular ATR (Average True Range)."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()

    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr


class TestAdaptivePositionRisk:
    """Tests para AdaptivePositionRisk con datos reales."""

    def test_sl_bull_trending_btc(self):
        """Test SL = 1.5x ATR en régimen BULL_TRENDING con datos BTCUSDT."""
        df = load_parquet("BTCUSDT", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = engine.calculate_dynamic_sl(
            atr=current_atr,
            regime=MarketRegime.BULL_TRENDING,
            entry_price=current_price,
            direction="BUY",
        )

        expected_multiplier = 1.5
        actual_distance_pct = (current_price - sl) / current_price

        expected_distance_pct = expected_multiplier * (current_atr / current_price)
        assert abs(actual_distance_pct - expected_distance_pct) < 0.001

    def test_sl_bear_trending_eur(self):
        """Test SL = 2.0x ATR en régimen BEAR_TRENDING con datos EURUSD."""
        df = load_parquet("EURUSD", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = engine.calculate_dynamic_sl(
            atr=current_atr,
            regime=MarketRegime.BEAR_TRENDING,
            entry_price=current_price,
            direction="SELL",
        )

        expected_multiplier = 2.0
        actual_distance_pct = (sl - current_price) / current_price

        expected_distance_pct = expected_multiplier * (current_atr / current_price)
        assert abs(actual_distance_pct - expected_distance_pct) < 0.001

    def test_sl_volatile_crash_xau(self):
        """Test SL = 3.0x ATR en régimen VOLATILE_CRASH con datos XAUUSD."""
        df = load_parquet("XAUUSD", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = engine.calculate_dynamic_sl(
            atr=current_atr,
            regime=MarketRegime.VOLATILE_CRASH,
            entry_price=current_price,
            direction="BUY",
        )

        expected_multiplier = 3.0
        actual_distance_pct = (current_price - sl) / current_price
        expected_distance_pct = expected_multiplier * (current_atr / current_price)

        assert abs(actual_distance_pct - expected_distance_pct) < 0.001

    def test_sl_sideways_low_vol(self):
        """Test SL = 1.0x ATR en régimen SIDEWAYS_LOW_VOL."""
        df = load_parquet("EURUSD", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = engine.calculate_dynamic_sl(
            atr=current_atr,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
            entry_price=current_price,
            direction="BUY",
        )

        expected_multiplier = 1.0
        actual_distance_pct = (current_price - sl) / current_price
        expected_distance_pct = expected_multiplier * (current_atr / current_price)

        assert abs(actual_distance_pct - expected_distance_pct) < 0.001

    def test_sl_sideways_high_vol(self):
        """Test SL = 2.0x ATR en régimen SIDEWAYS_HIGH_VOL."""
        df = load_parquet("XAUUSD", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = engine.calculate_dynamic_sl(
            atr=current_atr,
            regime=MarketRegime.SIDEWAYS_HIGH_VOL,
            entry_price=current_price,
            direction="BUY",
        )

        expected_multiplier = 2.0
        actual_distance_pct = (current_price - sl) / current_price
        expected_distance_pct = expected_multiplier * (current_atr / current_price)

        assert abs(actual_distance_pct - expected_distance_pct) < 0.001

    def test_tp_high_confidence(self):
        """Test TP = 2.0x risk cuando confidence > 0.7."""
        df = load_parquet("BTCUSDT", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = current_price - (current_atr * 1.5)

        tp = engine.calculate_dynamic_tp(
            atr=current_atr,
            regime=MarketRegime.BULL_TRENDING,
            entry_price=current_price,
            sl_price=sl,
            direction="BUY",
            model_confidence=0.8,
        )

        risk = current_price - sl
        expected_reward = risk * 2.0
        actual_reward = tp - current_price

        assert abs(actual_reward - expected_reward) < 0.01

    def test_tp_low_confidence(self):
        """Test TP = 1.5x risk cuando confidence < 0.7."""
        df = load_parquet("EURUSD", "1h")
        df = df.dropna()

        atr = calculate_atr(df)
        current_atr = atr.iloc[-1]
        current_price = df["close"].iloc[-1]

        engine = AdaptivePositionRisk()
        sl = current_price - (current_atr * 2.0)

        tp = engine.calculate_dynamic_tp(
            atr=current_atr,
            regime=MarketRegime.BEAR_TRENDING,
            entry_price=current_price,
            sl_price=sl,
            direction="SELL",
            model_confidence=0.5,
        )

        risk = abs(current_price - sl)
        expected_reward = risk * 1.5
        actual_reward = abs(current_price - tp)

        assert abs(actual_reward - expected_reward) < 0.01

    def test_position_size_limits(self):
        """Test que qty no excede max_position_pct."""
        profile = RiskProfile(risk_multiplier=1.0, max_position_pct=0.10)
        engine = AdaptivePositionRisk(profile)

        capital = 10000.0
        entry_price = 100.0
        sl_price = 95.0

        qty = engine.calculate_position_size(
            capital=capital,
            entry_price=entry_price,
            sl_price=sl_price,
            risk_pct=0.01,
        )

        max_qty = (capital * profile.max_position_pct) / entry_price
        assert qty <= max_qty + 1e-6

    def test_position_size_zero_risk(self):
        """Test retorna 0.0 cuando entry_price == sl_price."""
        engine = AdaptivePositionRisk()

        qty = engine.calculate_position_size(
            capital=10000.0,
            entry_price=100.0,
            sl_price=100.0,
            risk_pct=0.01,
        )

        assert qty == 0.0

    def test_position_size_with_profile(self):
        """Test position sizing con perfil custom."""
        profile = RiskProfile(risk_multiplier=0.5, max_position_pct=0.05)
        engine = AdaptivePositionRisk(profile)

        capital = 10000.0
        entry_price = 100.0
        sl_price = 90.0

        qty = engine.calculate_position_size(
            capital=capital,
            entry_price=entry_price,
            sl_price=sl_price,
            risk_pct=0.01,
        )

        risk_amount = capital * 0.01 * profile.risk_multiplier
        risk_per_unit = entry_price - sl_price
        expected_qty = risk_amount / risk_per_unit
        max_qty = (capital * profile.max_position_pct) / entry_price

        assert abs(qty - min(expected_qty, max_qty)) < 1e-6


class TestATRCalculation:
    """Tests para verificación de cálculo de ATR."""

    def test_atr_positive(self):
        """ATR debe ser siempre positivo."""
        df = load_parquet("BTCUSDT", "1h")
        atr = calculate_atr(df)
        assert atr.iloc[-1] > 0

    def test_atr_increases_with_volatility(self):
        """ATR debe ser mayor en activos más volátiles."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        btc_atr = calculate_atr(btc_df).iloc[-1]
        eur_atr = calculate_atr(eur_df).iloc[-1]

        btc_atr_pct = btc_atr / btc_df["close"].iloc[-1]
        eur_atr_pct = eur_atr / eur_df["close"].iloc[-1]

        assert btc_atr_pct > eur_atr_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])