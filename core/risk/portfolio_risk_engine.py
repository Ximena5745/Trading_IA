"""
Module: core/risk/portfolio_risk_engine.py
Responsibility: Risk engine a nivel portfolio con CVaR y correlaciones.
  - CVaR al 95%: pérdida esperada en el 5% peor de los casos
  - Correlación entre posiciones: reducir si corr > 0.7
  - Max exposure por régimen de mercado
Dependencies: numpy, pandas
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from core.models import MarketRegime
from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class PositionRisk:
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    risk_amount: float
    pnl: float


@dataclass
class PortfolioRiskMetrics:
    total_exposure: float
    cvar_95: float
    max_correlation: float
    max_position_pct: float
    portfolio_vol: float


class PortfolioRiskEngine:
    """
    Risk engine a nivel de portfolio.

    M5.4: Portfolio Risk con CVaR 95% + correlaciones.
    """

    def __init__(
        self,
        max_correlation: float = 0.70,
        max_position_pct: float = 0.40,
        cvar_confidence: float = 0.95,
    ):
        self._max_corr = max_correlation
        self._max_pos_pct = max_position_pct
        self._cvar_conf = cvar_confidence
        self._returns_history: dict[str, pd.Series] = {}
        self._positions: dict[str, PositionRisk] = {}

    def calculate_cvar(self, returns: pd.Series, alpha: float = 0.05) -> float:
        """CVaR al 95%: pérdida esperada en el 5% peor de los casos."""
        if len(returns) < 2:
            return 0.0

        var = returns.quantile(alpha)
        cvar = returns[returns <= var].mean()
        return abs(cvar) if not np.isnan(cvar) else 0.0

    def correlation_adjusted_size(
        self,
        new_symbol: str,
        existing_positions: list[str],
    ) -> float:
        """Reducir tamaño si correlación > 0.7 con posiciones existentes."""
        if not existing_positions:
            return 1.0

        max_corr = 0.0
        for pos_symbol in existing_positions:
            if new_symbol in self._returns_history and pos_symbol in self._returns_history:
                r1 = self._returns_history[new_symbol]
                r2 = self._returns_history[pos_symbol]
                common_idx = r1.index.intersection(r2.index)
                if len(common_idx) > 10:
                    corr = r1.loc[common_idx].corr(r2.loc[common_idx])
                    max_corr = max(max_corr, abs(corr))

        if max_corr > self._max_corr:
            adjustment = 1.0 - (max_corr - self._max_corr)
            logger.info(
                "correlation_adjustment",
                new_symbol=new_symbol,
                max_correlation=max_corr,
                adjustment=adjustment,
            )
            return max(0.3, adjustment)

        return 1.0

    def max_portfolio_exposure(self, vol_regime: str, regime: MarketRegime) -> float:
        """Calcular exposición máxima basada en riesgo sistémico."""
        vol_factor = {
            "low": 1.0,
            "medium": 0.8,
            "high": 0.5,
            "extreme": 0.2,
        }

        regime_factor = {
            MarketRegime.BULL_TRENDING: 1.0,
            MarketRegime.SIDEWAYS_LOW_VOL: 0.7,
            MarketRegime.BEAR_TRENDING: 0.5,
            MarketRegime.VOLATILE_CRASH: 0.1,
            MarketRegime.SIDEWAYS_HIGH_VOL: 0.6,
        }

        return 0.80 * vol_factor.get(vol_regime, 0.5) * regime_factor.get(regime, 0.5)

    def calculate_metrics(self) -> PortfolioRiskMetrics:
        """Calcular métricas de riesgo del portfolio."""
        total_exposure = sum(p.risk_amount for p in self._positions.values())

        all_returns = pd.concat(list(self._returns_history.values()))
        cvar = self.calculate_cvar(all_returns, 1 - self._cvar_conf)

        max_pos = max((p.risk_amount / total_exposure for p in self._positions.values()), default=0)

        portfolio_vol = all_returns.std() * np.sqrt(252 * 24) if len(all_returns) > 1 else 0

        max_corr = 0.0
        symbols = list(self._returns_history.keys())
        for i, s1 in enumerate(symbols):
            for s2 in symbols[i+1:]:
                r1, r2 = self._returns_history[s1], self._returns_history[s2]
                common = r1.index.intersection(r2.index)
                if len(common) > 10:
                    max_corr = max(max_corr, abs(r1.loc[common].corr(r2.loc[common])))

        return PortfolioRiskMetrics(
            total_exposure=total_exposure,
            cvar_95=cvar,
            max_correlation=max_corr,
            max_position_pct=max_pos,
            portfolio_vol=portfolio_vol,
        )

    def record_position(self, position: PositionRisk) -> None:
        """Registrar posición para tracking de riesgo."""
        self._positions[position.symbol] = position

    def record_returns(self, symbol: str, returns: pd.Series) -> None:
        """Registrar returns históricos para correlaciones."""
        self._returns_history[symbol] = returns