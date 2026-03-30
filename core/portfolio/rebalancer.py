"""
Module: core/portfolio/rebalancer.py
Responsibility: Periodic rebalancing between strategies based on performance
Dependencies: portfolio_manager, logger
"""
from __future__ import annotations

from datetime import datetime

from core.observability.logger import get_logger

logger = get_logger(__name__)


class Rebalancer:
    def __init__(self, rebalance_interval_days: int = 7):
        self._interval = rebalance_interval_days
        self._last_rebalance: datetime | None = None

    def should_rebalance(self) -> bool:
        if self._last_rebalance is None:
            return True
        delta = (datetime.utcnow() - self._last_rebalance).days
        return delta >= self._interval

    def rebalance(
        self,
        strategy_metrics: dict[str, dict],
        total_capital: float,
    ) -> dict[str, float]:
        """
        Allocate capital proportionally to Sharpe ratio.
        Strategies below threshold get 0 allocation.
        """
        MIN_SHARPE = 0.5
        eligible = {
            sid: m
            for sid, m in strategy_metrics.items()
            if m.get("sharpe_ratio", 0) >= MIN_SHARPE and m.get("status") == "active"
        }
        if not eligible:
            logger.warning("rebalancer_no_eligible_strategies")
            return {}

        total_sharpe = sum(m["sharpe_ratio"] for m in eligible.values())
        allocations = {}
        for sid, m in eligible.items():
            weight = (
                m["sharpe_ratio"] / total_sharpe
                if total_sharpe > 0
                else 1 / len(eligible)
            )
            allocations[sid] = round(total_capital * weight * 0.90, 2)  # 90% deployed

        self._last_rebalance = datetime.utcnow()
        logger.info(
            "portfolio_rebalanced",
            strategies=list(allocations.keys()),
            total=total_capital,
        )
        return allocations
