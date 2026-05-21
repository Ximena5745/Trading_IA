"""
Module: core/strategies/base_strategy.py
Responsibility: Abstract interface for all trading strategies
Dependencies: models
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.models import FeatureSet, MarketRegime


class AbcStrategy(ABC):
    strategy_id: str
    name: str
    version: str

    @abstractmethod
    def should_enter(self, features: FeatureSet) -> Optional[dict]:
        """Return entry signal dict or None if no entry."""
        ...

    @abstractmethod
    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        """Return True if the open position should be closed."""
        ...

    def get_required_features(self) -> list[str]:
        return []

    def get_optimal_regimes(self) -> list[MarketRegime]:
        return list(MarketRegime)

    @property
    def min_sharpe_to_activate(self) -> float:
        return 0.8

    def to_dict(self) -> dict:
        return {
            "id": self.strategy_id,
            "name": self.name,
            "version": self.version,
            "status": "active",
            "min_sharpe_to_activate": self.min_sharpe_to_activate,
        }
