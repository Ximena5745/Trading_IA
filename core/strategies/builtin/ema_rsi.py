"""
Module: core/strategies/builtin/ema_rsi.py
Responsibility: Default EMA crossover + RSI confirmation strategy
Dependencies: base_strategy, models
"""
from __future__ import annotations

from typing import Optional

from core.config.constants import ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER
from core.models import FeatureSet
from core.strategies.base_strategy import AbcStrategy


class EmaRsiStrategy(AbcStrategy):
    """
    Entry rules:
      BUY:  EMA9 > EMA21 AND EMA50 > EMA200 AND RSI14 < 65 AND RSI14 > 30
      SELL: EMA9 < EMA21 AND EMA50 < EMA200 AND RSI14 > 35 AND RSI14 < 70

    Exit rules:
      - RSI14 crosses opposite extreme (>70 for BUY, <30 for SELL)
      - EMA crossover reverses
    """

    strategy_id = "ema_rsi_v1"
    name = "EMA Crossover + RSI"
    version = "1.0.0"

    def __init__(
        self,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        min_volume_ratio: float = 1.2,
    ):
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.min_volume_ratio = min_volume_ratio

    def should_enter(self, features: FeatureSet) -> Optional[dict]:
        if features.volume_ratio < self.min_volume_ratio:
            return None
        if features.volatility_regime == "extreme":
            return None

        if self._is_buy(features):
            entry = features.close
            sl = entry - ATR_STOP_LOSS_MULTIPLIER * features.atr_14
            tp = entry + ATR_TAKE_PROFIT_MULTIPLIER * features.atr_14
            return {"action": "BUY", "entry_price": entry, "stop_loss": sl, "take_profit": tp}

        if self._is_sell(features):
            entry = features.close
            sl = entry + ATR_STOP_LOSS_MULTIPLIER * features.atr_14
            tp = entry - ATR_TAKE_PROFIT_MULTIPLIER * features.atr_14
            return {"action": "SELL", "entry_price": entry, "stop_loss": sl, "take_profit": tp}

        return None

    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        side = position.get("side", "BUY")
        if side == "BUY":
            return features.rsi_14 > self.rsi_overbought or features.ema_9 < features.ema_21
        return features.rsi_14 < self.rsi_oversold or features.ema_9 > features.ema_21

    def _is_buy(self, f: FeatureSet) -> bool:
        return (
            f.ema_9 > f.ema_21
            and f.ema_50 > f.ema_200
            and self.rsi_oversold < f.rsi_14 < 65
            and f.macd_histogram > 0
        )

    def _is_sell(self, f: FeatureSet) -> bool:
        return (
            f.ema_9 < f.ema_21
            and f.ema_50 < f.ema_200
            and 35 < f.rsi_14 < self.rsi_overbought
            and f.macd_histogram < 0
        )

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "description": "EMA crossover with RSI confirmation and volume filter",
            "parameters": {
                "rsi_oversold": self.rsi_oversold,
                "rsi_overbought": self.rsi_overbought,
                "min_volume_ratio": self.min_volume_ratio,
            },
            "timeframe": "1h",
            "symbols": [
                # Crypto
                "BTCUSDT", "ETHUSDT",
                # Forex
                "EURUSD", "GBPUSD", "USDJPY",
                # Indices
                "SPX500", "NAS100",
                # Commodities
                "XAUUSD", "USOIL",
            ],
            "max_capital_pct": 0.20,
            "risk_per_trade_pct": 0.01,
            "status": "active",
        }
