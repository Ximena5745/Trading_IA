"""
Integration tests for complete FASE 5 risk pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from core.features.hurst_engine import HurstEngine
from core.models import MarketRegime
from core.risk.adaptive_position_risk import AdaptivePositionRisk
from core.risk.auto_adaptation import MarketAutoAdaptation
from core.risk.portfolio_risk_engine import PortfolioRiskEngine
from core.risk.user_profile_engine import UserProfileEngine
from core.risk.volatility_targeting import VolatilityTargetingEngine


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
    """Calcular ADX."""
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


class TestFullRiskPipelineBTC:
    """Tests de integración completos con datos BTCUSDT."""

    def test_full_risk_pipeline_btc(self):
        """Ejecutar todos los módulos de riesgo con datos BTC."""
        df = load_parquet("BTCUSDT", "1h")
        df = df.dropna()

        returns = calculate_returns(df)
        adx_val = calculate_adx(df)

        auto_adapt = MarketAutoAdaptation()
        action = auto_adapt.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=adx_val,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.5,
            regime=MarketRegime.BULL_TRENDING,
        )

        vol_target = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = vol_target.calculate_scale_factor(returns)

        portfolio_risk = PortfolioRiskEngine()
        cvar = portfolio_risk.calculate_cvar(returns)

        high = df["high"]
        low = df["low"]
        close = df["close"]
        tr1 = high - low
        tr2 = (high - close.shift()).abs()
        tr3 = (low - close.shift()).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(14).mean().iloc[-1]

        adaptive_risk = AdaptivePositionRisk()
        sl = adaptive_risk.calculate_dynamic_sl(
            atr=atr,
            regime=MarketRegime.BULL_TRENDING,
            entry_price=close.iloc[-1],
            direction="BUY",
        )

        assert action.position_scale > 0
        assert 0.2 <= scale <= 2.0
        assert cvar >= 0
        assert sl > 0
        assert sl < close.iloc[-1]

    def test_risk_pipeline_with_profile(self):
        """Pipeline con perfil de usuario."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        profile_engine = UserProfileEngine()
        profile = profile_engine.get_profile("swing")

        adaptive_risk = AdaptivePositionRisk(
            profile=None,
        )

        vol_target = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = vol_target.calculate_scale_factor(returns)

        assert profile.risk_per_trade > 0
        assert scale > 0


class TestFullRiskPipelineForex:
    """Tests de integración con datos forex."""

    def test_full_risk_pipeline_eur(self):
        """Ejecutar con datos EURUSD."""
        df = load_parquet("EURUSD", "1h")
        df = df.dropna()

        returns = calculate_returns(df)
        adx_val = calculate_adx(df)

        auto_adapt = MarketAutoAdaptation()
        action = auto_adapt.analyze_and_adapt(
            symbol="EURUSD",
            returns=returns,
            adx=adx_val,
            hurst=0.5,
            hour=8,
            drawdown_4h=0.01,
            correlation_avg=0.2,
            regime=MarketRegime.SIDEWAYS_LOW_VOL,
        )

        vol_target = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = vol_target.calculate_scale_factor(returns)

        portfolio_risk = PortfolioRiskEngine()
        cvar = portfolio_risk.calculate_cvar(returns)

        assert action.position_scale > 0
        assert 0.2 <= scale <= 2.0
        assert cvar >= 0


class TestFullRiskPipelineMultipleAssets:
    """Tests con múltiples activos."""

    def test_risk_with_multiple_assets(self):
        """Portfolio con BTC + ETH + EURUSD."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eth_df = load_parquet("ETHUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        btc_returns = calculate_returns(btc_df)
        eth_returns = calculate_returns(eth_df)
        eur_returns = calculate_returns(eur_df)

        portfolio_risk = PortfolioRiskEngine()

        btc_cvar = portfolio_risk.calculate_cvar(btc_returns)
        eth_cvar = portfolio_risk.calculate_cvar(eth_returns)
        eur_cvar = portfolio_risk.calculate_cvar(eur_returns)

        correlation_btc_eth = btc_returns.corr(eth_returns)
        correlation_eur_btc = eur_returns.corr(btc_returns)

        positions = [
            type("Position", (), {"symbol": "BTCUSDT", "pnl_pct": 0.05})(),
            type("Position", (), {"symbol": "ETHUSDT", "pnl_pct": 0.03})(),
        ]

        adjusted_eth = portfolio_risk.correlation_adjusted_size("ETHUSDT", positions)
        adjusted_eur = portfolio_risk.correlation_adjusted_size("EURUSD", positions)

        assert btc_cvar >= 0
        assert eth_cvar >= 0
        assert eur_cvar >= 0
        assert -1 <= correlation_btc_eth <= 1
        assert -1 <= correlation_eur_btc <= 1
        assert 0 <= adjusted_eth <= 1
        assert 0 <= adjusted_eur <= 1


class TestRiskPipelineEdgeCases:
    """Tests de casos extremos del pipeline."""

    def test_pipeline_low_data(self):
        """Test con datos insuficientes."""
        df = load_parquet("EURUSD", "1h").head(50)

        returns = calculate_returns(df)

        vol_target = VolatilityTargetingEngine()
        scale = vol_target.calculate_scale_factor(returns)

        portfolio_risk = PortfolioRiskEngine()
        cvar = portfolio_risk.calculate_cvar(returns)

        assert scale > 0
        assert cvar >= 0

    def test_pipeline_high_volatility(self):
        """Test con volatilidad extrema."""
        df = load_parquet("BTCUSDT", "1h")

        returns = calculate_returns(df)

        vol_target = VolatilityTargetingEngine(target_annual_vol=0.05)
        scale = vol_target.calculate_scale_factor(returns)

        assert scale >= 0.2

    def test_pipeline_low_volatility(self):
        """Test con volatilidad muy baja."""
        df = load_parquet("EURUSD", "1h")

        returns = calculate_returns(df)

        vol_target = VolatilityTargetingEngine(target_annual_vol=0.50)
        scale = vol_target.calculate_scale_factor(returns)

        assert scale <= 2.0


class TestRiskPipelineAdaptation:
    """Tests de adaptación automática en el pipeline."""

    def test_adaptation_influences_position_size(self):
        """La adaptación debe influir en el tamaño de posición."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        auto_adapt = MarketAutoAdaptation()

        action_normal = auto_adapt.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=25.0,
            hurst=0.5,
            hour=12,
            drawdown_4h=0.02,
            correlation_avg=0.3,
            regime=MarketRegime.BULL_TRENDING,
        )

        action_high_vol = auto_adapt.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=50.0,
            hurst=0.3,
            hour=12,
            drawdown_4h=0.10,
            correlation_avg=0.8,
            regime=MarketRegime.VOLATILE_CRASH,
        )

        assert action_high_vol.position_scale <= action_normal.position_scale


class TestRiskPipelineProfileSelection:
    """Tests de selección de perfil en el pipeline."""

    def test_different_profiles_different_behavior(self):
        """Diferentes perfiles deben producir diferente comportamiento."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        profile_engine = UserProfileEngine()

        scalper = profile_engine.get_profile("scalper")
        conservative = profile_engine.get_profile("conservative")

        vol_target_scalper = VolatilityTargetingEngine(
            target_annual_vol=0.15,
        )
        vol_target_conservative = VolatilityTargetingEngine(
            target_annual_vol=0.08,
        )

        scale_scalper = vol_target_scalper.calculate_scale_factor(returns)
        scale_conservative = vol_target_conservative.calculate_scale_factor(returns)

        assert scalper.max_signals_per_day > conservative.max_signals_per_day


class TestRiskPipelineComplete:
    """Tests completos del pipeline de riesgo."""

    def test_complete_risk_workflow(self):
        """Workflow completo de riesgo."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        profile_engine = UserProfileEngine()
        profile = profile_engine.get_profile("day_trader")

        vol_target = VolatilityTargetingEngine(target_annual_vol=0.10)
        vol_scale = vol_target.calculate_scale_factor(returns)
        vol_regime = vol_target.get_current_volatility_regime(returns)

        auto_adapt = MarketAutoAdaptation()
        adx = 30.0
        hurst = 0.55
        adaptation = auto_adapt.analyze_and_adapt(
            symbol="BTCUSDT",
            returns=returns,
            adx=adx,
            hurst=hurst,
            hour=10,
            drawdown_4h=0.03,
            correlation_avg=0.4,
            regime=MarketRegime.BULL_TRENDING,
        )

        portfolio_risk = PortfolioRiskEngine()
        cvar = portfolio_risk.calculate_cvar(returns)

        final_scale = vol_scale * adaptation.position_scale

        assert profile.profile_id == "day_trader"
        assert 0.2 <= vol_scale <= 2.0
        assert vol_regime in ["low", "normal", "high", "extreme", "unknown"]
        assert adaptation.position_scale > 0
        assert cvar >= 0
        assert final_scale > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])