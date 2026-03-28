"""
Module: core/strategies/strategy_builder.py
Responsibility: Build strategy logic from configuration (no-code)
Dependencies: base_strategy, models
"""

from __future__ import annotations

from core.config.constants import ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER
from core.models import FeatureSet
from core.strategies.base_strategy import AbcStrategy

OPERATORS = {
    "lt": lambda a, b: a < b,
    "gt": lambda a, b: a > b,
    "lte": lambda a, b: a <= b,
    "gte": lambda a, b: a >= b,
    "eq": lambda a, b: a == b,
}


class BuiltStrategy(AbcStrategy):
    def __init__(self, config: dict):
        self.strategy_id = config["id"]
        self.name = config["name"]
        self.version = config.get("version", "1.0.0")
        self._entry_conditions = config.get("entry_conditions", [])
        self._exit_conditions = config.get("exit_conditions", [])
        self._config = config

    def should_enter(self, features: FeatureSet) -> dict | None:
        if not self._evaluate_conditions(self._entry_conditions, features):
            return None
        entry = features.close
        atr = features.atr_14
        action = self._config.get("default_action", "BUY")
        if action == "BUY":
            sl = entry - ATR_STOP_LOSS_MULTIPLIER * atr
            tp = entry + ATR_TAKE_PROFIT_MULTIPLIER * atr
        else:
            sl = entry + ATR_STOP_LOSS_MULTIPLIER * atr
            tp = entry - ATR_TAKE_PROFIT_MULTIPLIER * atr
        return {
            "action": action,
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
        }

    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        return self._evaluate_conditions(self._exit_conditions, features)

    def to_dict(self) -> dict:
        return {**super().to_dict(), **self._config}

    def _evaluate_conditions(
        self, conditions: list[dict], features: FeatureSet
    ) -> bool:
        if not conditions:
            return False
        for cond in conditions:
            feature_val = getattr(features, cond["feature"], None)
            if feature_val is None:
                return False
            op_fn = OPERATORS.get(cond["operator"])
            if op_fn is None:
                return False
            compare_val = cond["value"]
            if isinstance(compare_val, str):
                compare_val = getattr(features, compare_val, 0.0)
            if not op_fn(feature_val, compare_val):
                return False
        return True


class StrategyBuilder:
    def build(self, config: dict) -> BuiltStrategy:
        self._validate(config)
        return BuiltStrategy(config)

    def _validate(self, config: dict) -> None:
        required = ["id", "name", "entry_conditions"]
        for field in required:
            if field not in config:
                raise ValueError(f"Strategy config missing required field: {field}")
        if not config["entry_conditions"]:
            raise ValueError("Strategy must have at least one entry condition")
        for cond in config["entry_conditions"]:
            if cond.get("operator") not in OPERATORS:
                raise ValueError(f"Unknown operator: {cond.get('operator')}")
