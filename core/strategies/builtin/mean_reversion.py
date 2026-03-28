"""
Module: core/strategies/builtin/mean_reversion.py
Responsibility: Bollinger Bands mean reversion strategy
Dependencies: base_strategy, models
"""

from __future__ import annotations

from core.config.constants import ATR_STOP_LOSS_MULTIPLIER
from core.models import FeatureSet
from core.strategies.base_strategy import AbcStrategy


class MeanReversionStrategy(AbcStrategy):
    """
    Entry rules:
      BUY:  close < bb_lower AND RSI14 < rsi_oversold AND volume_ratio > min_vol
      SELL: close > bb_upper AND RSI14 > rsi_overbought AND volume_ratio > min_vol

    Exit: price returns to VWAP or midband
    """

    strategy_id = "mean_reversion_v1"
    name = "Bollinger Bands Mean Reversion"
    version = "1.0.0"

    def __init__(
        self,
        rsi_oversold: float = 28.0,
        rsi_overbought: float = 72.0,
        min_volume_ratio: float = 1.0,
    ):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.min_volume_ratio = min_volume_ratio

    def should_enter(self, features: FeatureSet) -> dict | None:
        if features.volume_ratio < self.min_volume_ratio:
            return None
        if features.volatility_regime in ("extreme",):
            return None

        if self._is_buy(features):
            entry = features.close
            sl = entry - ATR_STOP_LOSS_MULTIPLIER * features.atr_14
            tp = features.vwap  # target: revert to VWAP
            if tp <= entry:
                return None
            return {
                "action": "BUY",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
            }

        if self._is_sell(features):
            entry = features.close
            sl = entry + ATR_STOP_LOSS_MULTIPLIER * features.atr_14
            tp = features.vwap  # target: revert to VWAP
            if tp >= entry:
                return None
            return {
                "action": "SELL",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
            }

        return None

    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        side = position.get("side", "BUY")
        midband = (features.bb_upper + features.bb_lower) / 2
        if side == "BUY":
            return features.close >= midband or features.rsi_14 > 55
        return features.close <= midband or features.rsi_14 < 45

    def _is_buy(self, f: FeatureSet) -> bool:
        return (
            f.close < f.bb_lower
            and f.rsi_14 < self.rsi_oversold
            and f.volume_ratio >= self.min_volume_ratio
        )

    def _is_sell(self, f: FeatureSet) -> bool:
        return (
            f.close > f.bb_upper
            and f.rsi_14 > self.rsi_overbought
            and f.volume_ratio >= self.min_volume_ratio
        )

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "description": "Bollinger Bands mean reversion with RSI confirmation",
            "parameters": {
                "rsi_oversold": self.rsi_oversold,
                "rsi_overbought": self.rsi_overbought,
                "min_volume_ratio": self.min_volume_ratio,
            },
            "timeframe": "1h",
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "max_capital_pct": 0.15,
            "risk_per_trade_pct": 0.01,
            "status": "active",
        }
