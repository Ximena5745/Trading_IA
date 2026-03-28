"""
Module: core/strategies/strategy_registry.py
Responsibility: Dynamic registration and lifecycle management of strategies
Dependencies: base_strategy, builtin strategies, logger
"""
from __future__ import annotations

from core.exceptions import StrategyNotFoundError
from core.observability.logger import get_logger
from core.strategies.base_strategy import AbcStrategy
from core.strategies.builtin.ema_rsi import EmaRsiStrategy
from core.strategies.builtin.mean_reversion import MeanReversionStrategy

logger = get_logger(__name__)


class StrategyRegistry:
    def __init__(self):
        self._strategies: dict[str, AbcStrategy] = {}
        self._load_builtins()

    def _load_builtins(self) -> None:
        self.register(EmaRsiStrategy())
        self.register(MeanReversionStrategy())

    def register(self, strategy: AbcStrategy) -> None:
        self._strategies[strategy.strategy_id] = strategy
        logger.info("strategy_registered", strategy_id=strategy.strategy_id, name=strategy.name)

    def get(self, strategy_id: str) -> AbcStrategy:
        strategy = self._strategies.get(strategy_id)
        if not strategy:
            raise StrategyNotFoundError(f"Strategy not found: {strategy_id}")
        return strategy

    def list_all(self) -> list[dict]:
        return [s.to_dict() for s in self._strategies.values()]

    def list_active(self) -> list[AbcStrategy]:
        return [
            s for s in self._strategies.values()
            if s.to_dict().get("status") == "active"
        ]

    def set_status(self, strategy_id: str, status: str) -> dict:
        strategy = self.get(strategy_id)
        config = strategy.to_dict()
        config["status"] = status
        logger.info("strategy_status_changed", strategy_id=strategy_id, status=status)
        return config

    def unregister(self, strategy_id: str) -> None:
        if strategy_id not in self._strategies:
            raise StrategyNotFoundError(f"Strategy not found: {strategy_id}")
        del self._strategies[strategy_id]
        logger.info("strategy_unregistered", strategy_id=strategy_id)
