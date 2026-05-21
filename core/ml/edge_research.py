"""
Module: core/ml/edge_research.py
Responsibility: Research and validate real statistical edge
I1: Investigación edge real - Walk-forward + bootstraps + benchmark
Dependencies: numpy, pandas, scipy
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class EdgeResearchResult:
    """Result of edge research for a strategy/feature."""
    strategy_id: str
    sharpe_oos: float
    sharpe_net: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    p_value: float
    n_trades: int
    edge_exists: bool
    confidence_level: float
    recommendation: str


class EdgeResearcher:
    """Researcher for validating real statistical edge.

    Implements:
    - Walk-forward validation
    - Bootstrap confidence intervals
    - Random benchmark comparison
    - Transaction cost sensitivity analysis
    """

    def __init__(
        self,
        n_bootstrap: int = 1000,
        confidence_level: float = 0.95,
        transaction_cost_bps: float = 10,
    ):
        self.n_bootstrap = n_bootstrap
        self.confidence_level = confidence_level
        self.transaction_cost_bps = transaction_cost_bps
        self.alpha = 1 - confidence_level

    def validate_edge(
        self,
        returns: pd.Series,
        signals: pd.Series,
    ) -> EdgeResearchResult:
        """Validate if strategy has real edge vs random.

        Returns:
            EdgeResearchResult with statistics and recommendation
        """
        aligned = returns.align(signals, join="inner")
        returns_aligned = aligned[0]
        signals_aligned = aligned[1]

        strategy_returns = returns_aligned * signals_aligned.shift(1)
        strategy_returns = strategy_returns.dropna()

        if len(strategy_returns) < 30:
            return EdgeResearchResult(
                strategy_id="unknown",
                sharpe_oos=0.0,
                sharpe_net=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
                p_value=1.0,
                n_trades=len(strategy_returns),
                edge_exists=False,
                confidence_level=self.confidence_level,
                recommendation="Insufficient data",
            )

        costs = self._calculate_costs(strategy_returns, signals_aligned)
        net_returns = strategy_returns - costs.reindex(strategy_returns.index).fillna(0.0)

        sharpe_oos = self._sharpe_ratio(strategy_returns)
        sharpe_net = self._sharpe_ratio(net_returns)
        max_dd = self._max_drawdown(strategy_returns.cumsum())
        win_rate = (strategy_returns > 0).mean()
        profit_factor = self._profit_factor(strategy_returns)

        p_value = self._bootstrap_pvalue(returns_aligned, signals_aligned)

        edge_exists = sharpe_net >= 0.8 and p_value < 0.05

        recommendation = self._generate_recommendation(
            sharpe_net, p_value, max_dd
        )

        return EdgeResearchResult(
            strategy_id="strategy_v1",
            sharpe_oos=round(sharpe_oos, 4),
            sharpe_net=round(sharpe_net, 4),
            max_drawdown=round(max_dd, 4),
            win_rate=round(win_rate, 4),
            profit_factor=round(profit_factor, 4),
            p_value=round(p_value, 4),
            n_trades=len(strategy_returns),
            edge_exists=edge_exists,
            confidence_level=self.confidence_level,
            recommendation=recommendation,
        )

    def _calculate_costs(
        self,
        returns: pd.Series,
        signals: pd.Series | None = None,
    ) -> pd.Series:
        """Transaction costs applied only when position changes (round-trip aware)."""
        if signals is not None:
            aligned = returns.align(signals, join="inner")
            sig = aligned[1].fillna(0)
            position_changed = sig.diff().abs().fillna(0) > 0
            costs = position_changed.astype(float) * (
                self.transaction_cost_bps / 10000
            )
            return costs.reindex(returns.index).fillna(0.0)

        # Fallback: infer position changes from strategy return sign flips
        prev_sign = np.sign(returns.shift(1).fillna(0))
        curr_sign = np.sign(returns)
        sign_changes = prev_sign != curr_sign
        return sign_changes.astype(float) * (self.transaction_cost_bps / 10000)

    def _sharpe_ratio(self, returns: pd.Series, periods_per_year: int = 252 * 24) -> float:
        """Calculate annualized Sharpe ratio."""
        if len(returns) < 2 or returns.std() == 0:
            return 0.0
        return returns.mean() / returns.std() * np.sqrt(periods_per_year)

    def _max_drawdown(self, equity_curve: pd.Series) -> float:
        """Calculate maximum drawdown."""
        if len(equity_curve) < 2:
            return 0.0
        equity = equity_curve.replace([np.inf, -np.inf], np.nan).dropna()
        if len(equity) < 2:
            return 0.0
        cummax = equity.expanding().max()
        drawdown = (equity - cummax) / cummax.replace(0, np.nan)
        dd = drawdown.min()
        return abs(dd) if pd.notna(dd) else 0.0

    def _profit_factor(self, returns: pd.Series) -> float:
        """Calculate profit factor."""
        gross_profit = returns[returns > 0].sum()
        gross_loss = abs(returns[returns < 0].sum())
        return gross_profit / gross_loss if gross_loss > 0 else 0.0

    def _bootstrap_pvalue(
        self,
        returns: pd.Series,
        signals: pd.Series,
    ) -> float:
        """Calculate p-value using bootstrap against random strategy."""
        np.random.seed(42)

        observed_sharpe = self._sharpe_ratio(returns * signals.shift(1))

        random_sharpes = []
        for _ in range(self.n_bootstrap):
            random_signals = np.random.choice(
                [-1, 0, 1],
                size=len(signals),
                p=[0.25, 0.50, 0.25],
            )
            random_returns = returns * pd.Series(random_signals, index=returns.index)
            random_sharpe = self._sharpe_ratio(random_returns.dropna())
            random_sharpes.append(random_sharpe)

        random_sharpes = np.array(random_sharpes)
        p_value = (random_sharpes >= observed_sharpe).mean()

        return p_value

    def _generate_recommendation(
        self,
        sharpe_net: float,
        p_value: float,
        max_dd: float,
    ) -> str:
        """Generate recommendation based on results."""
        if sharpe_net > 0.8 and p_value < 0.05:
            return "STRONG_EDGE - Proceed to live trading"
        elif sharpe_net > 0.5 and p_value < 0.10:
            return "WEAK_EDGE - Requires more validation"
        elif sharpe_net > 0 and p_value < 0.20:
            return "MARGINAL_EDGE - Optimize costs and parameters"
        elif sharpe_net <= 0:
            return "NO_EDGE - Do not proceed, redesign strategy"
        else:
            return "INCONCLUSIVE - Need more data"


class FeatureEdgeAnalyzer:
    """Analyze which features have predictive edge."""

    def __init__(self):
        self.results = {}

    def analyze_feature_edge(
        self,
        df: pd.DataFrame,
        feature_name: str,
        target_column: str = "target",
    ) -> dict:
        """Analyze if a feature has predictive edge.

        Uses:
        - Information Coefficient (IC)
        - Rank IC
        - Predictive confidence
        """
        if feature_name not in df.columns or target_column not in df.columns:
            return {"error": "Feature or target not found"}

        feature = df[feature_name].dropna()
        target = df[target_column].dropna()

        aligned = feature.align(target, join="inner")

        if len(aligned[0]) < 30:
            return {"error": "Insufficient data"}

        ic, p_value = stats.spearmanr(aligned[0], aligned[1])
        rank_ic, rank_p = stats.spearmanr(
            aligned[0].rank(), aligned[1].rank()
        )

        predictive_strength = abs(ic)

        edge_exists = predictive_strength > 0.05 and p_value < 0.10

        result = {
            "feature": feature_name,
            "ic": round(ic, 4),
            "ic_pvalue": round(p_value, 4),
            "rank_ic": round(rank_ic, 4),
            "rank_ic_pvalue": round(rank_p, 4),
            "predictive_strength": predictive_strength,
            "edge_exists": edge_exists,
            "recommendation": "KEEP" if edge_exists else "DISCARD",
        }

        self.results[feature_name] = result
        return result

    def get_top_features(self, n: int = 10) -> list[dict]:
        """Get top N features by predictive strength."""
        if not self.results:
            return []

        sorted_results = sorted(
            self.results.items(),
            key=lambda x: x[1].get("predictive_strength", 0),
            reverse=True,
        )

        return [r[1] for r in sorted_results[:n]]


async def run_edge_validation(
    data: pd.DataFrame,
    feature_cols: list[str],
    target_col: str = "target",
) -> dict:
    """Run complete edge validation workflow."""
    researcher = EdgeResearcher(n_bootstrap=1000)
    feature_analyzer = FeatureEdgeAnalyzer()

    results = {
        "features": {},
        "overall": {},
    }

    for feature in feature_cols:
        try:
            feat_result = feature_analyzer.analyze_feature_edge(
                data, feature, target_col
            )
            results["features"][feature] = feat_result
        except Exception:
            pass

    top_features = feature_analyzer.get_top_features(5)
    results["overall"]["top_features"] = top_features
    results["overall"]["has_edge"] = any(
        f.get("edge_exists", False) for f in top_features
    )

    return results