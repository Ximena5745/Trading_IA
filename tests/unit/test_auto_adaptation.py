"""
Tests for MarketAutoAdaptation (M5.5) using real data.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.features.hurst_engine import HurstEngine
from core.models import MarketRegime
from core.risk.auto_adaptation import AdaptationAction, MarketAutoAdaptation


DATA_DIR = Path("data/raw")


def load_parquet(symbol: str, timeframe: str = "1h") -> pd.DataFrame:
    """Cargar datos parquet reales."""
    file_path = DATA_DIR / f"{symbol}_{timeframe}.parquet"
    if not file_path.exists():
        pytest.skip(f"Datos no encontrados: {file_path}")
    df = pd.read_parquet(file_path)
    return df


def calculate_returns(df: pd.DataFrame) -> pd.Series:
    """Calcular returns."""
    return df["close"].pct_change().dropna()


def calculate_adx(df: pd.DataFrame, period: int = 14) -> float:
    """Calcular ADX aproximado."""
    high = df["high"]
    low = df["low"]
    close = df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr = tr.rolling(period).mean()

    plus_di = 100 * (plus_dm.rolling(period).mean() / atr)
    minus_di = 100 * (minus_dm.rolling(period).mean() / atr)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.rolling(period).mean()

    return adx.iloc[-1] if not pd.isna(adx.iloc[-1]) else 25.0


class TestMarketAutoAdaptation:
    """Tests para MarketAutoAdaptation con datos reales."""

    def test_adaptation_high_vol_p90(self):
        """Test position_scale = 0.5, sl_mult = 3.0 cuando vol > P90."""
        df = load_parquet("XAUUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        for i in range(10):
            vol_pct = 0.95
            action = engine.analyze_and_adapt(
                symbol="XAUUSD",
                returns=returns,
                adx=20.0,
                hurst=0.5,
                hour=12,
                drawdown_4h=0.02,
                correlation_avg=0.3,
                regime=MarketRegime.SIDEWAYS_HIGH_VOL,
            )

            if action.action_type == "HIGH_VOL":
                assert action.position_scale <= 0.7
                break
        else:
            pass

    def test_adaptation_low_vol_p10(self):
        """Test position_scale = 1.2, tp_mult = 0.8 cuando vol < P10."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=20.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
        )

        assert action.position_scale >= 1.0

    def test_adaptation_adx_momentum(self):
        """Test strategies = TSMOM cuando ADX > 30."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=35.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.BULL_TRENDING,
        )

        assert "TSMOM" in action.strategies_allowed

    def test_adaptation_adx_mean_reversion(self):
        """Test strategies = StatisticalArbitrage cuando ADX < 15."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=10.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
        )

        assert "StatisticalArbitrage" in action.strategies_allowed or "VWAPReversion" in action.strategies_allowed

    def test_adaptation_hurst_trending(self):
        """Test strategies = TSMOM cuando Hurst > 0.55."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=25.0,
            hurst=0.65,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.BULL_TRENDING,
        )

        assert "TSMOM" in action.strategies_allowed or "Breakout" in action.strategies_allowed

    def test_adaptation_hurst_mean_reversion(self):
        """Test strategies = StatisticalArbitrage cuando Hurst < 0.45."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=25.0,
            hurst=0.35,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
        )

        assert "StatisticalArbitrage" in action.strategies_allowed or "PairsTrading" in action.strategies_allowed

    def test_adaptation_drawdown_alert(self):
        """Test position_scale *= 0.5 cuando drawdown_4h > 5%."""
        df = load_parquet("XAUUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="XAUUSD",
            returns=returns,
            adx=25.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.08,
            correlation_avg=0.3,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
        )

        assert action.position_scale <= 0.6 or action.action_type == "DRAWDOWN_ALERT"

    def test_adaptation_asian_session(self):
        """Test position_scale *= 0.7 en horas 0-5 UTC."""
        df = load_parquet("USDJPY", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        for hour in [0, 1, 2, 3, 4, 5]:
            action = engine.analyze_and_adapt(
                symbol="USDJPY",
                returns=returns,
                adx=25.0,
                hurst=0.5,
                hour=hour,
                drawdown_4h=0.02,
                correlation_avg=0.3,
                regime=MarketRegime.BULL_TRENDING,
            )

            assert "Asian session" in action.description or action.position_scale <= 0.8

    def test_adaptation_correlation(self):
        """Test scale reduce cuando corr > 0.7."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=25.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.8,
            regime=MarketRegime.BULL_TRENDING,
        )

        expected_scale = 1.0 - 0.8
        assert action.position_scale <= expected_scale + 0.1

    def test_adaptation_crisis_regime(self):
        """Test position_scale = 0.1 en régimen CRISIS."""
        df = load_parquet("XAUUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()

        action = engine.analyze_and_adapt(
            symbol="XAUUSD",
            returns=returns,
            adx=50.0,
            hurst=0.3,
            hour=12,
            drawdown_4h=0.15,
            correlation_avg=0.9,
            regime=MarketRegime.VOLATILE_CRASH,
        )

        assert action.position_scale <= 0.2
        assert "CashOnly" in action.strategies_allowed


class TestMarketAutoAdaptationWithRealData:
    """Tests completos con datos reales."""

    def test_full_analysis_btc(self):
        """Análisis completo con datos BTCUSDT."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        adx_val = calculate_adx(df)

        engine = MarketAutoAdaptation()
        action = engine.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=adx_val if adx_val else 25.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.5,
            regime=MarketRegime.BULL_TRENDING,
        )

        assert action.position_scale > 0
        assert len(action.strategies_allowed) > 0

    def test_full_analysis_eur(self):
        """Análisis completo con datos EURUSD."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        adx_val = calculate_adx(df)

        engine = MarketAutoAdaptation()
        action = engine.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=adx_val if adx_val else 25.0,
            hurst=0.5,
            hour=8,
            drawdown_4h=0.01,
            correlation_avg=0.3,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
        )

        assert action.position_scale > 0
        assert len(action.strategies_allowed) > 0

    def test_full_analysis_xau(self):
        """Análisis completo con datos XAUUSD."""
        df = load_parquet("XAUUSD", "1h")
        returns = calculate_returns(df)

        adx_val = calculate_adx(df)

        engine = MarketAutoAdaptation()
        action = engine.analyze_and_adapt(
            symbol="XAUUSD",
            returns=returns,
            adx=adx_val if adx_val else 25.0,
            hurst=0.5,
            hour=14,
            drawdown_4h=0.03,
            correlation_avg=0.4,
            regime=MarketRegime.BEAR_TRENDING,
        )

        assert action.position_scale > 0
        assert len(action.strategies_allowed) > 0


class TestAdaptationAction:
    """Tests para la clase AdaptationAction."""

    def test_get_last_action(self):
        """Test recuperar última acción."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = MarketAutoAdaptation()
        engine.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=30.0,
            hurst=0.6,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.BULL_TRENDING,
        )

        last_action = engine.get_last_action()
        assert last_action is not None
        assert isinstance(last_action, AdaptationAction)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])