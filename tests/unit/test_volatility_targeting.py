"""
Tests for VolatilityTargetingEngine (M5.3) using real data.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

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
    """Calcular returns desde close price."""
    return df["close"].pct_change().dropna()


class TestVolatilityTargetingEngine:
    """Tests para VolatilityTargetingEngine con datos reales."""

    def test_scale_factor_high_vol_xau(self):
        """Test factor < 1.0 cuando vol > target (XAUUSD es más volátil)."""
        df = load_parquet("XAUUSD", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = engine.calculate_scale_factor(returns)

        assert 0.2 <= scale < 1.0

    def test_scale_factor_low_vol_eur(self):
        """Test factor > 1.0 cuando vol < target (EURUSD es menos volátil)."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = engine.calculate_scale_factor(returns)

        assert 1.0 <= scale <= 2.0

    def test_scale_factor_clipping_min(self):
        """Test clipping inferior (0.2) cuando vol extremadamente alta."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(
            target_annual_vol=0.01,
            min_scale=0.2,
            max_scale=2.0,
        )
        scale = engine.calculate_scale_factor(returns)

        assert scale >= 0.2

    def test_scale_factor_clipping_max(self):
        """Test clipping superior (2.0) cuando vol extremadamente baja."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(
            target_annual_vol=1.0,
            min_scale=0.2,
            max_scale=2.0,
        )
        scale = engine.calculate_scale_factor(returns)

        assert scale <= 2.0

    def test_scale_factor_insufficient_data(self):
        """Test retorna 1.0 cuando hay menos de 2 datos."""
        returns = pd.Series([0.01])

        engine = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = engine.calculate_scale_factor(returns)

        assert scale == 1.0

    def test_scale_factor_zero_volatility(self):
        """Test retorna 1.0 cuando volatilidad es cero."""
        returns = pd.Series([0.0, 0.0, 0.0])

        engine = VolatilityTargetingEngine(target_annual_vol=0.10)
        scale = engine.calculate_scale_factor(returns)

        assert scale == 1.0

    def test_scale_position(self):
        """Test scale_position escala quantity correctamente."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(target_annual_vol=0.10)
        base_quantity = 100.0
        scaled = engine.scale_position(base_quantity, returns)

        assert scaled > 0

    def test_vol_regime_extreme(self):
        """Test detecta régimen 'extreme' cuando vol > P90."""
        df = load_parquet("XAUUSD", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(window=20)
        regime = engine.get_current_volatility_regime(returns)

        assert regime in ["extreme", "high", "normal", "low", "unknown"]

    def test_vol_regime_low(self):
        """Test detecta régimen 'low' cuando vol baja."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine = VolatilityTargetingEngine(window=20)
        regime = engine.get_current_volatility_regime(returns)

        assert regime in ["extreme", "high", "normal", "low", "unknown"]

    def test_vol_regime_insufficient_data(self):
        """Test retorna 'unknown' con datos insuficientes."""
        returns = pd.Series([0.01, 0.02])

        engine = VolatilityTargetingEngine(window=20)
        regime = engine.get_current_volatility_regime(returns)

        assert regime == "unknown"


class TestVolatilityComparison:
    """Tests comparativos de volatilidad entre activos."""

    def test_btc_higher_vol_than_forex(self):
        """BTC debe tener mayor volatilidad anualizada que EURUSD."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        btc_returns = calculate_returns(btc_df)
        eur_returns = calculate_returns(eur_df)

        btc_annual_vol = btc_returns.std() * (252 * 24) ** 0.5
        eur_annual_vol = eur_returns.std() * (252 * 24) ** 0.5

        assert btc_annual_vol > eur_annual_vol

    def test_xau_higher_vol_than_forex(self):
        """XAU debe tener mayor volatilidad que EURUSD."""
        xau_df = load_parquet("XAUUSD", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        xau_returns = calculate_returns(xau_df)
        eur_returns = calculate_returns(eur_df)

        xau_annual_vol = xau_returns.std() * (252 * 24) ** 0.5
        eur_annual_vol = eur_returns.std() * (252 * 24) ** 0.5

        assert xau_annual_vol > eur_annual_vol

    def test_scale_inverse_to_volatility(self):
        """El factor de escala debe ser inverso a la volatilidad."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        btc_returns = calculate_returns(btc_df)
        eur_returns = calculate_returns(eur_df)

        engine = VolatilityTargetingEngine(target_annual_vol=0.10)

        btc_scale = engine.calculate_scale_factor(btc_returns)
        eur_scale = engine.calculate_scale_factor(eur_returns)

        assert btc_scale < eur_scale


class TestVolatilityTargetingConfiguration:
    """Tests para configuraciones del engine."""

    def test_default_configuration(self):
        """Test configuración por defecto."""
        engine = VolatilityTargetingEngine()

        assert engine._target_vol == 0.10
        assert engine._min_scale == 0.20
        assert engine._max_scale == 2.0
        assert engine._window == 20

    def test_custom_configuration(self):
        """Test configuración personalizada."""
        engine = VolatilityTargetingEngine(
            target_annual_vol=0.15,
            min_scale=0.3,
            max_scale=1.5,
            window=30,
        )

        assert engine._target_vol == 0.15
        assert engine._min_scale == 0.3
        assert engine._max_scale == 1.5
        assert engine._window == 30

    def test_different_targets_produce_different_scales(self):
        """Diferentes targets deben producir diferentes escalas."""
        df = load_parquet("EURUSD", "1h")
        returns = calculate_returns(df)

        engine_low = VolatilityTargetingEngine(target_annual_vol=0.05)
        engine_high = VolatilityTargetingEngine(target_annual_vol=0.20)

        scale_low = engine_low.calculate_scale_factor(returns)
        scale_high = engine_high.calculate_scale_factor(returns)

        assert scale_low != scale_high


if __name__ == "__main__":
    pytest.main([__file__, "-v"])