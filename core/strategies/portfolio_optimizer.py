"""
Module: core/strategies/portfolio_optimizer.py
Responsibility: Optimización de allocation entre estrategias activas.
  - Risk Parity: igual contribución al riesgo total
  - Kelly fraction half-Kelly por estrategia
  - Correlación entre estrategias: matrix de 30 barras rolling
  - Anti-correlation guard: reducir tamaño si corr > 0.7
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
class AllocationResult:
    allocations: dict[str, float]
    total_capital: float
    method: str
    risk_contributions: dict[str, float]


class PortfolioOptimizer:
    """
    Optimizador de portfolio multi-estrategia.

    M4.4: Portfolio Optimizer.
    """

    def __init__(
        self,
        total_capital: float = 100000.0,
        method: str = "risk_parity",
        use_half_kelly: bool = True,
        max_concentration: float = 0.40,
        correlation_threshold: float = 0.70,
    ):
        self._total_capital = total_capital
        self._method = method
        self._use_half_kelly = use_half_kelly
        self._max_concentration = max_concentration
        self._correlation_threshold = correlation_threshold
        self._strategy_returns: dict[str, pd.Series] = {}
        self._correlation_window = 30

    def update_returns(self, strategy_id: str, returns: pd.Series) -> None:
        """Actualizar histórico de returns para una estrategia."""
        self._strategy_returns[strategy_id] = returns

    def optimize(
        self,
        active_strategies: list[str],
        realized_vols: dict[str, float],
    ) -> AllocationResult:
        """
        Calcular allocation óptima entre estrategias activas.

        Args:
            active_strategies: Lista de estrategias activas
            realized_vols: Volatilidad realizada por estrategia

        Returns:
            AllocationResult con allocations y métricas
        """
        if not active_strategies:
            return AllocationResult(
                allocations={},
                total_capital=self._total_capital,
                method=self._method,
                risk_contributions={},
            )

        if self._method == "risk_parity":
            return self._risk_parity_allocation(active_strategies, realized_vols)
        elif self._method == "kelly":
            return self._kelly_allocation(active_strategies)
        elif self._method == "equal":
            return self._equal_allocation(active_strategies)
        else:
            logger.warning("unknown_method_using_equal", method=self._method)
            return self._equal_allocation(active_strategies)

    def _risk_parity_allocation(
        self,
        strategies: list[str],
        vols: dict[str, float],
    ) -> AllocationResult:
        """
        Risk Parity: cada estrategia contribuye igual al riesgo total.

        Riesgo_i = weight_i * vol_i
        Para risk parity: weight_i * vol_i = constant
        weight_i = constant / vol_i
        """
        allocations = {}
        risk_contributions = {}

        valid_vols = {s: max(vols.get(s, 0.01), 0.01) for s in strategies}

        inv_vols = np.array([1.0 / valid_vols[s] for s in strategies])
        total_inv_vol = inv_vols.sum()

        raw_weights = inv_vols / total_inv_vol

        for i, strategy in enumerate(strategies):
            weight = float(raw_weights[i])

            if weight > self._max_concentration:
                weight = self._max_concentration
                logger.info(
                    "concentration_capped",
                    strategy=strategy,
                    original_weight=raw_weights[i],
                    capped_weight=weight,
                )

            allocations[strategy] = weight * self._total_capital
            risk_contributions[strategy] = weight * valid_vols[strategy]

        normalized_weights = np.array(list(allocations.values())) / self._total_capital
        normalized_weights = normalized_weights / normalized_weights.sum()

        for i, strategy in enumerate(allocations):
            allocations[strategy] = normalized_weights[i] * self._total_capital

        logger.info(
            "risk_parity_allocation",
            strategies=strategies,
            allocations={s: round(a, 2) for s, a in allocations.items()},
        )

        return AllocationResult(
            allocations=allocations,
            total_capital=self._total_capital,
            method="risk_parity",
            risk_contributions=risk_contributions,
        )

    def _kelly_allocation(self, strategies: list[str]) -> AllocationResult:
        """
        Kelly Criterion: fraction = (win_rate * avg_win - avg_loss) / avg_win.

        Usa half-Kelly para ser más conservador.
        """
        allocations = {}
        kelly_fractions = []

        for strategy in strategies:
            if strategy not in self._strategy_returns:
                kelly_fractions.append(0.0)
                continue

            returns = self._strategy_returns[strategy]
            if len(returns) < 10:
                kelly_fractions.append(0.0)
                continue

            wins = returns[returns > 0]
            losses = returns[returns < 0]

            win_rate = len(wins) / len(returns) if len(returns) > 0 else 0.5
            avg_win = wins.mean() if len(wins) > 0 else 0.01
            avg_loss = abs(losses.mean()) if len(losses) > 0 else 0.01

            if avg_win > 0 and avg_loss > 0:
                kelly = (win_rate * avg_win - avg_loss) / avg_win
                kelly = max(0, min(kelly, 1.0))
            else:
                kelly = 0.0

            if self._use_half_kelly:
                kelly = kelly / 2

            kelly_fractions.append(kelly)

        total_kelly = sum(kelly_fractions)
        if total_kelly > 0:
            for i, strategy in enumerate(strategies):
                weight = kelly_fractions[i] / total_kelly

                if weight > self._max_concentration:
                    weight = self._max_concentration

                allocations[strategy] = weight * self._total_capital
        else:
            equal_weight = self._total_capital / len(strategies)
            for strategy in strategies:
                allocations[strategy] = equal_weight

        logger.info(
            "kelly_allocation",
            strategies=strategies,
            kelly_fractions=[round(k, 3) for k in kelly_fractions],
        )

        return AllocationResult(
            allocations=allocations,
            total_capital=self._total_capital,
            method="kelly",
            risk_contributions={s: 0.0 for s in strategies},
        )

    def _equal_allocation(self, strategies: list[str]) -> AllocationResult:
        """Equal weight allocation."""
        n = len(strategies)
        if n == 0:
            return AllocationResult({}, self._total_capital, "equal", {})

        weight = 1.0 / n

        if weight > self._max_concentration:
            logger.warning(
                "equal_weight_exceeds_concentration_limit",
                n_strategies=n,
                weight=weight,
                limit=self._max_concentration,
            )

        allocations = {s: weight * self._total_capital for s in strategies}

        logger.info(
            "equal_allocation",
            strategies=strategies,
            weight_per_strategy=weight,
        )

        return AllocationResult(
            allocations=allocations,
            total_capital=self._total_capital,
            method="equal",
            risk_contributions={s: weight for s in strategies},
        )

    def apply_correlation_adjustment(
        self,
        allocations: dict[str, float],
        strategy_returns: dict[str, pd.Series],
    ) -> dict[str, float]:
        """
        Reducir allocation si correlación entre estrategias > threshold.

        Si corr(A, B) > 0.7, reducir exposición total de ambas.
        """
        if len(allocations) < 2:
            return allocations

        strategies = list(allocations.keys())
        correlation_matrix = self._calculate_correlation_matrix(strategies, strategy_returns)

        adjustments = {}
        for i, s1 in enumerate(strategies):
            for j, s2 in enumerate(strategies):
                if i >= j:
                    continue
                corr = correlation_matrix.iloc[i, j]
                if corr > self._correlation_threshold:
                    reduction = 1.0 - (corr - self._correlation_threshold)
                    adjustments[s1] = min(adjustments.get(s1, 1.0), reduction)
                    adjustments[s2] = min(adjustments.get(s2, 1.0), reduction)
                    logger.info(
                        "correlation_adjustment",
                        strategy_1=s1,
                        strategy_2=s2,
                        correlation=round(corr, 3),
                        reduction=round(reduction, 3),
                    )

        adjusted = {}
        for strategy, allocation in allocations.items():
            factor = adjustments.get(strategy, 1.0)
            adjusted[strategy] = allocation * factor

        return adjusted

    def _calculate_correlation_matrix(
        self,
        strategies: list[str],
        returns: dict[str, pd.Series],
    ) -> pd.DataFrame:
        """Calcular matriz de correlación entre estrategias."""
        aligned_returns = {}
        min_length = float("inf")

        for strategy in strategies:
            if strategy in returns and len(returns[strategy]) > 0:
                aligned_returns[strategy] = returns[strategy]
                min_length = min(min_length, len(returns[strategy]))

        if not aligned_returns or min_length == 0:
            n = len(strategies)
            return pd.DataFrame(np.eye(n), index=strategies, columns=strategies)

        for strategy in aligned_returns:
            aligned_returns[strategy] = aligned_returns[strategy].iloc[-int(min_length):]

        df = pd.DataFrame(aligned_returns)
        corr = df.corr()

        for strategy in strategies:
            if strategy not in corr.index:
                corr.loc[strategy, :] = 0.0
                corr.loc[:, strategy] = 0.0
                corr.loc[strategy, strategy] = 1.0

        return corr.fillna(0.0)

    def get_portfolio_metrics(self, allocations: dict[str, float]) -> dict:
        """Calcular métricas del portfolio."""
        total_weight = sum(allocations.values()) / self._total_capital
        n_strategies = len(allocations)

        return {
            "total_weight": round(total_weight, 4),
            "n_strategies": n_strategies,
            "max_allocation_pct": round(max(allocations.values()) / self._total_capital * 100, 2)
            if allocations
            else 0,
            "min_allocation_pct": round(min(allocations.values()) / self._total_capital * 100, 2)
            if allocations
            else 0,
        }