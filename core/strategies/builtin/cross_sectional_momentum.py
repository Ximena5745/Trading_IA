"""
Module: core/strategies/builtin/cross_sectional_momentum.py
Responsibility: Cross-sectional momentum across crypto universe (P1).
"""
from __future__ import annotations

from typing import Optional

from core.models import FeatureSet, MarketRegime
from core.strategies.base_strategy import AbcStrategy

CRYPTO_UNIVERSE = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")


class CrossSectionalMomentumStrategy(AbcStrategy):
    """
    M4 P1: Rank crypto assets by momentum; long strongest, short weakest.
  Requires cross-sectional return ranks passed via features.metadata or ret_12.
    """

    strategy_id = "cross_sectional_v1"
    name = "Cross-Sectional Momentum"
    version = "1.0.0"

    def __init__(self, lookback: int = 12, top_quantile: float = 0.75):
        self._lookback = lookback
        self._top_quantile = top_quantile
        self._momentum_cache: dict[str, float] = {}

    def get_required_features(self) -> list[str]:
        return ["ret_12", "hurst_exponent", "adx_14"]

    def get_optimal_regimes(self) -> list[MarketRegime]:
        return [
            MarketRegime.BULL_TRENDING,
            MarketRegime.BEAR_TRENDING,
        ]

    @property
    def min_sharpe_to_activate(self) -> float:
        return 0.8

    def update_universe_momentum(self, symbol_returns: dict[str, float]) -> None:
        self._momentum_cache = dict(symbol_returns)

    def should_enter(self, features: FeatureSet) -> Optional[dict]:
        symbol = features.symbol.upper()
        if symbol not in CRYPTO_UNIVERSE:
            return None

        momentum = getattr(features, "ret_12", None)
        if momentum is None and self._momentum_cache:
            momentum = self._momentum_cache.get(symbol)
        if momentum is None:
            return None

        ranked = sorted(self._momentum_cache.items(), key=lambda x: x[1])
        if len(ranked) < 2:
            rank_score = float(momentum)
        else:
            values = [v for _, v in ranked]
            rank_score = (values.index(float(momentum)) + 1) / len(values)

        hurst = getattr(features, "hurst_exponent", 0.5) or 0.5
        if hurst < 0.5:
            return None

        if rank_score >= self._top_quantile:
            return {
                "action": "BUY",
                "confidence": min(0.95, 0.5 + rank_score * 0.4),
                "strategy_id": self.strategy_id,
                "reason": f"cross_sectional_rank={rank_score:.2f}",
            }
        if rank_score <= (1 - self._top_quantile):
            return {
                "action": "SELL",
                "confidence": min(0.95, 0.5 + (1 - rank_score) * 0.4),
                "strategy_id": self.strategy_id,
                "reason": f"cross_sectional_rank={rank_score:.2f}",
            }
        return None

    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        side = position.get("side", "BUY")
        momentum = getattr(features, "ret_12", 0) or 0
        if side == "BUY" and momentum < 0:
            return True
        if side == "SELL" and momentum > 0:
            return True
        return False
