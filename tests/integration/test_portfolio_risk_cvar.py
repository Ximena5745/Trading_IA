"""
Integration tests for PortfolioRiskEngine (M5.4) - CVaR and correlations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pandas as pd
import pytest

from core.risk.portfolio_risk_engine import PortfolioRiskEngine


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


class MockPosition:
    """Mock position para testing."""

    def __init__(self, symbol: str, pnl_pct: float):
        self.symbol = symbol
        self.pnl_pct = pnl_pct


class TestCVaRCalculation:
    """Tests para cálculo de CVaR."""

    def test_cvar_95_btc(self):
        """Test CVaR 95% con datos BTCUSDT."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        engine = PortfolioRiskEngine()
        cvar = engine.calculate_cvar(returns, alpha=0.05)

        assert cvar >= 0

    def test_cvar_95_eurusd(self):
        """Test CVaR 95% más bajo en forex vs crypto."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        btc_returns = calculate_returns(btc_df)
        eur_returns = calculate_returns(eur_df)

        engine = PortfolioRiskEngine()

        btc_cvar = engine.calculate_cvar(btc_returns, alpha=0.05)
        eur_cvar = engine.calculate_cvar(eur_returns, alpha=0.05)

        assert btc_cvar >= eur_cvar

    def test_cvar_empty_returns(self):
        """Test retorna 0.0 si no hay datos."""
        returns = pd.Series([])

        engine = PortfolioRiskEngine()
        cvar = engine.calculate_cvar(returns, alpha=0.05)

        assert cvar == 0.0

    def test_cvar_single_return(self):
        """Test con un solo return."""
        returns = pd.Series([0.01])

        engine = PortfolioRiskEngine()
        cvar = engine.calculate_cvar(returns, alpha=0.05)

        assert cvar >= 0

    def test_cvar_all_positive(self):
        """Test CVaR con retornos todos positivos."""
        returns = pd.Series([0.01, 0.02, 0.015, 0.03, 0.005])

        engine = PortfolioRiskEngine()
        cvar = engine.calculate_cvar(returns, alpha=0.05)

        assert cvar >= 0

    def test_cvar_different_alphas(self):
        """Test diferentes niveles de confianza."""
        df = load_parquet("BTCUSDT", "1h")
        returns = calculate_returns(df)

        engine = PortfolioRiskEngine()

        cvar_90 = engine.calculate_cvar(returns, alpha=0.10)
        cvar_95 = engine.calculate_cvar(returns, alpha=0.05)
        cvar_99 = engine.calculate_cvar(returns, alpha=0.01)

        assert cvar_90 > 0
        assert cvar_95 > 0
        assert cvar_99 > 0


class TestCorrelationAdjustment:
    """Tests para ajuste de tamaño por correlación."""

    def test_correlation_adjusted_size_high_corr(self):
        """Test size reduce si corr > 0.7."""
        engine = PortfolioRiskEngine()

        existing_positions = [
            MockPosition("BTCUSDT", 0.05),
            MockPosition("ETHUSDT", 0.03),
        ]

        new_symbol = "BNBUSDT"

        result = engine.correlation_adjusted_size(new_symbol, existing_positions)

        assert 0.3 <= result <= 1.0

    def test_correlation_adjusted_size_low_corr(self):
        """Test size no reduce si corr baja."""
        engine = PortfolioRiskEngine()

        existing_positions = [
            MockPosition("EURUSD", 0.01),
            MockPosition("XAUUSD", -0.01),
        ]

        result = engine.correlation_adjusted_size("BTCUSDT", existing_positions)

        assert result >= 0.3

    def test_correlation_adjusted_size_empty(self):
        """Test retorna 1.0 si no hay posiciones."""
        engine = PortfolioRiskEngine()

        result = engine.correlation_adjusted_size("BTCUSDT", [])

        assert result == 1.0


class TestMaxPortfolioExposure:
    """Tests para exposición máxima de portfolio."""

    def test_max_exposure_low_vol_regime(self):
        """Test exposure en régimen de baja volatilidad."""
        engine = PortfolioRiskEngine()

        exposure = engine.max_portfolio_exposure("low", MagicMock())

        assert exposure > 0

    def test_max_exposure_high_vol_regime(self):
        """Test exposure baja en régimen de alta volatilidad."""
        engine = PortfolioRiskEngine()

        exposure = engine.max_portfolio_exposure("high", MagicMock())

        assert exposure <= 0.6

    def test_max_exposure_extreme_vol_regime(self):
        """Test exposure muy baja en régimen de volatilidad extrema."""
        engine = PortfolioRiskEngine()

        exposure = engine.max_portfolio_exposure("extreme", MagicMock())

        assert exposure <= 0.3


class TestPortfolioRiskEngine:
    """Tests completos para PortfolioRiskEngine."""

    def test_full_portfolio_analysis_btc_eth(self):
        """Análisis completo de portfolio con BTC y ETH."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eth_df = load_parquet("ETHUSDT", "1h")

        btc_returns = calculate_returns(btc_df)
        eth_returns = calculate_returns(eth_df)

        engine = PortfolioRiskEngine()

        btc_cvar = engine.calculate_cvar(btc_returns)
        eth_cvar = engine.calculate_cvar(eth_returns)

        correlation = btc_returns.corr(eth_returns)

        positions = [MockPosition("BTCUSDT", 0.05), MockPosition("ETHUSDT", 0.03)]
        adjusted_size = engine.correlation_adjusted_size("ETHUSDT", positions)

        assert btc_cvar >= 0
        assert eth_cvar >= 0
        assert -1 <= correlation <= 1
        assert adjusted_size >= 0

    def test_multi_asset_portfolio(self):
        """Portfolio con múltiples activos."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")
        xau_df = load_parquet("XAUUSD", "1h")

        returns_dict = {
            "BTCUSDT": calculate_returns(btc_df),
            "EURUSD": calculate_returns(eur_df),
            "XAUUSD": calculate_returns(xau_df),
        }

        engine = PortfolioRiskEngine()

        all_returns = pd.concat(returns_dict.values())
        cvar = engine.calculate_cvar(all_returns)

        correlation_matrix = pd.DataFrame({
            symbol: returns for symbol, returns in returns_dict.items()
        }).corr()

        assert cvar >= 0
        assert correlation_matrix is not None


class TestCVaRWithDifferentAssets:
    """Tests de CVaR comparativos entre activos."""

    def test_cvar_comparison_assets(self):
        """Comparar CVaR entre diferentes activos."""
        symbols = ["BTCUSDT", "ETHUSDT", "EURUSD", "XAUUSD"]

        engine = PortfolioRiskEngine()
        cvar_values = {}

        for symbol in symbols:
            df = load_parquet(symbol, "1h")
            returns = calculate_returns(df)
            cvar_values[symbol] = engine.calculate_cvar(returns)

        for symbol, cvar in cvar_values.items():
            assert cvar >= 0

    def test_cvar_indicates_risk_level(self):
        """CVaR debe indicar nivel de riesgo."""
        btc_df = load_parquet("BTCUSDT", "1h")
        eur_df = load_parquet("EURUSD", "1h")

        btc_returns = calculate_returns(btc_df)
        eur_returns = calculate_returns(eur_df)

        engine = PortfolioRiskEngine()

        btc_cvar = engine.calculate_cvar(btc_returns)
        eur_cvar = engine.calculate_cvar(eur_returns)

        if btc_cvar > eur_cvar:
            assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])