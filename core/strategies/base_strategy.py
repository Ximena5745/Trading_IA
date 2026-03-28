"""
Module: core/strategies/base_strategy.py
Responsibility: Abstract interface for all trading strategies
Dependencies: models
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from core.models import FeatureSet, Signal


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

    def to_dict(self) -> dict:
        return {
            "id": self.strategy_id,
            "name": self.name,
            "version": self.version,
        }
