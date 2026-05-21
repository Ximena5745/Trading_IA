"""
Module: core/strategies/builtin/tsmom.py
Responsibility: Time-Series Momentum strategy.
  - Señal = sign(ret_12) con filtro de tendencia
  - Activo en regímenes trending (Hurst > 0.55)
  - Reducir exposición en regímenes no trending
Dependencies: base_strategy, models
"""
from __future__ import annotations

from typing import Optional

from core.models import FeatureSet, MarketRegime
from core.strategies.base_strategy import AbcStrategy


class TSMOMStrategy(AbcStrategy):
    """
    Time-Series Momentum (TSMOM) strategy.

    M4.2: Time-Series Momentum (P1).

    Entry rules:
      - BUY: retorno 12 períodos > 0 Y tendencia bullish
      - SELL: retorno 12 períodos < 0 Y tendencia bearish

    Exit rules:
      - Señal opuesta
      - Stop loss por ATR
    """

    strategy_id = "tsmom_v1"
    name = "Time-Series Momentum"
    version = "1.0.0"

    def __init__(
        self,
        lookback_period: int = 12,
        trend_filter: bool = True,
        min_trend_strength: float = 0.5,
        atr_multiplier: float = 2.0,
        risk_per_trade: float = 0.01,
    ):
        self._lookback = lookback_period
        self._trend_filter = trend_filter
        self._min_trend_strength = min_trend_strength
        self._atr_multiplier = atr_multiplier
        self._risk_per_trade = risk_per_trade
        self._returns_history: list[float] = []

    def should_enter(self, features: FeatureSet) -> Optional[dict]:
        """Generar señal de entrada basada en momentum."""
        self._update_returns(features)

        if len(self._returns_history) < self._lookback:
            return None

        recent_returns = self._returns_history[-self._lookback:]
        momentum = sum(recent_returns) / len(recent_returns)

        if self._trend_filter and not self._is_trending(features):
            return None

        if momentum > 0:
            return self._create_buy_signal(features, momentum)
        elif momentum < 0:
            return self._create_sell_signal(features, momentum)

        return None

    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        """Evaluar si cerrar posición."""
        side = position.get("side", "BUY")
        entry_price = position.get("entry_price", 0)

        if entry_price == 0:
            return False

        if side == "BUY":
            current_momentum = (
                sum(self._returns_history[-self._lookback:]) / self._lookback
                if len(self._returns_history) >= self._lookback
                else 0
            )
            if current_momentum < 0:
                return True

            if features.close < position.get("stop_loss", 0):
                return True

        elif side == "SELL":
            current_momentum = (
                sum(self._returns_history[-self._lookback:]) / self._lookback
                if len(self._returns_history) >= self._lookback
                else 0
            )
            if current_momentum > 0:
                return True

            if features.close > position.get("stop_loss", float("inf")):
                return True

        return False

    def _update_returns(self, features: FeatureSet) -> None:
        """Actualizar historial de retornos."""
        if len(self._returns_history) > 0:
            last_price = self._returns_history[-1] + features.close
            if last_price > 0:
                ret = (features.close - last_price) / last_price
                self._returns_history.append(ret)
        else:
            self._returns_history.append(0.0)

        if len(self._returns_history) > 100:
            self._returns_history = self._returns_history[-100:]

    def _is_trending(self, features: FeatureSet) -> bool:
        """Determinar si el mercado está en tendencia."""
        trend_score = 0.0

        if features.trend_direction == "bullish":
            trend_score += 0.4
        elif features.trend_direction == "bearish":
            trend_score += 0.4

        if features.ema_9 > features.ema_21:
            trend_score += 0.2
        elif features.ema_9 < features.ema_21:
            trend_score += 0.2

        if features.macd_histogram > 0:
            trend_score += 0.2
        elif features.macd_histogram < 0:
            trend_score += 0.2

        if hasattr(features, "adx_14") and features.adx_14 > 25:
            trend_score += 0.2

        return trend_score >= self._min_trend_strength

    def _create_buy_signal(self, features: FeatureSet, momentum: float) -> dict:
        """Crear señal de compra."""
        entry = features.close
        sl = entry - self._atr_multiplier * features.atr_14
        tp = entry + (entry - sl) * 2.0

        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "side": "BUY",
            "confidence": min(abs(momentum) * 10, 1.0),
            "regime": features.trend_direction,
        }

    def _create_sell_signal(self, features: FeatureSet, momentum: float) -> dict:
        """Crear señal de venta."""
        entry = features.close
        sl = entry + self._atr_multiplier * features.atr_14
        tp = entry - (sl - entry) * 2.0

        return {
            "action": "SELL",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "side": "SELL",
            "confidence": min(abs(momentum) * 10, 1.0),
            "regime": features.trend_direction,
        }

    def get_optimal_regimes(self) -> list[MarketRegime]:
        """Regímenes óptimos para TSMOM."""
        return [MarketRegime.BULL_TRENDING, MarketRegime.BEAR_TRENDING]

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "description": "Time-Series Momentum: señal basada en retornos acumulados",
            "parameters": {
                "lookback_period": self._lookback,
                "trend_filter": self._trend_filter,
                "min_trend_strength": self._min_trend_strength,
                "atr_multiplier": self._atr_multiplier,
            },
            "timeframe": "1h",
            "symbols": ["BTCUSDT", "ETHUSDT", "EURUSD", "GBPUSD", "XAUUSD"],
            "regimes": ["bull_trending", "bear_trending"],
            "max_capital_pct": 0.25,
            "risk_per_trade_pct": self._risk_per_trade,
            "status": "active",
        }