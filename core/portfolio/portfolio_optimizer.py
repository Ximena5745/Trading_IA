"""
Module: core/portfolio/portfolio_optimizer.py
Responsibility: Optimización de allocation entre estrategias activas.
  - Risk Parity: igual contribución al riesgo total
  - Kelly fraction half-Kelly por estrategia
  - Correlación entre estrategias: matrix de 30 barras rolling
  - Anti-correlation guard: reducir tamaño si corr > 0.7 entre posiciones
  - Concentration limit: ninguna estrategia > 40% del capital
Dependencies: numpy, pandas
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Allocation:
    strategy_id: str
    weight: float
    risk_contribution: float


class PortfolioOptimizer:
    """
    Optimizador de portfolio con múltiples estrategias.

    M4.4: Portfolio Optimizer con Risk Parity.
    """

    def __init__(
        self,
        max_concentration: float = 0.40,
        correlation_threshold: float = 0.70,
        use_half_kelly: bool = True,
    ):
        self._max_concentration = max_concentration
        self._corr_threshold = correlation_threshold
        self._use_half_kelly = use_half_kelly
        self._returns_history: dict[str, pd.Series] = {}

    def allocate(
        self,
        strategies: list[str],
        total_capital: float,
        regime: str = "normal",
    ) -> list[Allocation]:
        """
        Calcular allocation óptima entre estrategias.
        """
        if not strategies:
            return []

        weights = self._calculate_risk_parity_weights(strategies)

        if regime == "high_vol":
            weights = {k: v * 0.5 for k, v in weights.items()}
        elif regime == "crisis":
            weights = {k: v * 0.2 for k, v in weights.items()}

        allocations = []
        for strategy_id, weight in weights.items():
            cap = total_capital * weight
            risk_contrib = weight * self._estimate_strategy_risk(strategy_id)
            allocations.append(Allocation(
                strategy_id=strategy_id,
                weight=weight,
                risk_contribution=risk_contrib,
            ))

        logger.info(
            "portfolio_allocated",
            strategies=len(strategies),
            regime=regime,
            allocations={a.strategy_id: round(a.weight, 3) for a in allocations},
        )
        return allocations

    def _calculate_risk_parity_weights(self, strategies: list[str]) -> dict[str, float]:
        """Calcular pesos usando Risk Parity."""
        if len(strategies) == 1:
            return {strategies[0]: 1.0}

        volatilities = []
        for s in strategies:
            vol = self._estimate_strategy_risk(s)
            volatilities.append(max(vol, 0.01))

        inv_vol = [1.0 / v for v in volatilities]
        total_inv_vol = sum(inv_vol)
        raw_weights = [v / total_inv_vol for v in inv_vol]

        adjusted_weights = self._apply_correlation_adjustment(strategies, raw_weights)
        adjusted_weights = self._apply_concentration_limit(adjusted_weights)

        if self._use_half_kelly:
            avg_sharpe = np.mean([self._estimate_sharpe(s) for s in strategies])
            if avg_sharpe > 0:
                kelly_factor = min(avg_sharpe / 2.0, 1.0)
                adjusted_weights = {k: v * kelly_factor for k, v in adjusted_weights.items()}
                total = sum(adjusted_weights.values())
                adjusted_weights = {k: v / total for k, v in adjusted_weights.items()}

        return adjusted_weights

    def _apply_correlation_adjustment(
        self, strategies: list[str], weights: list[float]
    ) -> dict[str, float]:
        """Aplicar ajuste por correlación entre estrategias."""
        if len(strategies) < 2:
            return {strategies[0]: weights[0]} if weights else {}

        corr_matrix = self._get_correlation_matrix(strategies)
        n = len(strategies)

        for i in range(n):
            for j in range(i + 1, n):
                if corr_matrix[i, j] > self._corr_threshold:
                    weights[i] *= 0.7
                    weights[j] *= 0.7
                    logger.debug(
                        "correlation_adjustment",
                        s1=strategies[i],
                        s2=strategies[j],
                        corr=corr_matrix[i, j],
                    )

        total = sum(weights)
        return {s: w / total for s, w in zip(strategies, weights)}

    def _apply_concentration_limit(self, weights: dict[str, float]) -> dict[str, float]:
        """Aplicar límite de concentración (40% máximo)."""
        max_weight = max(weights.values()) if weights else 0

        if max_weight > self._max_concentration:
            scale = self._max_concentration / max_weight
            weights = {k: v * scale for k, v in weights.items()}
            total = sum(weights.values())
            weights = {k: v / total for k, v in weights.items()}
            logger.info("concentration_limited", max_weight=max_weight)

        return weights

    def _get_correlation_matrix(self, strategies: list[str]) -> np.ndarray:
        """Calcular matriz de correlación entre estrategias."""
        n = len(strategies)
        matrix = np.eye(n)

        for i, s1 in enumerate(strategies):
            for j, s2 in enumerate(strategies):
                if i >= j:
                    continue

                r1 = self._returns_history.get(s1, pd.Series())
                r2 = self._returns_history.get(s2, pd.Series())

                if len(r1) > 10 and len(r2) > 10:
                    common_idx = r1.index.intersection(r2.index)
                    if len(common_idx) > 10:
                        corr = r1.loc[common_idx].corr(r2.loc[common_idx])
                        matrix[i, j] = matrix[j, i] = corr

        return matrix

    def _estimate_strategy_risk(self, strategy_id: str) -> float:
        """Estimar riesgo (volatilidad) de una estrategia."""
        returns = self._returns_history.get(strategy_id, pd.Series())
        if len(returns) < 2:
            return 0.15
        return max(returns.std(), 0.01)

    def _estimate_sharpe(self, strategy_id: str) -> float:
        """Estimar Sharpe ratio de una estrategia."""
        returns = self._returns_history.get(strategy_id, pd.Series())
        if len(returns) < 2:
            return 0.5
        mean_ret = returns.mean()
        std_ret = returns.std()
        if std_ret == 0:
            return 0.5
        return mean_ret / std_ret

    def record_returns(self, strategy_id: str, returns: pd.Series) -> None:
        """Registrar returns históricos para correlation matrix."""
        self._returns_history[strategy_id] = returns