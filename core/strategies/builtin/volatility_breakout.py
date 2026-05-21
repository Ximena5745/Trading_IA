"""
Module: core/strategies/builtin/volatility_breakout.py
Responsibility: Volatility Breakout strategy.
  - Detectar consolidación (ATR contraction)
  - Señal en ruptura con filtro de volumen
  - Post-consolidación régimen óptimo
Dependencies: base_strategy, models
"""
from __future__ import annotations

from collections import deque
from typing import Optional

from core.models import FeatureSet, MarketRegime
from core.strategies.base_strategy import AbcStrategy


class VolatilityBreakoutStrategy(AbcStrategy):
    """
    Volatility Breakout strategy.

    M4.4: Volatility Breakout Adaptive (P1).

    Entry rules:
      - Consolidación: ATR actual < 50% del ATR promedio (20 períodos)
      - Ruptura: precio rompe máxima/mínima de consolidación con volumen
      - Filtro: volumen > 1.5x promedio

    Exit rules:
      - Stop loss: ATR * 2
      - Take profit: 3x riesgo
      - Vuelve a consolidación
    """

    strategy_id = "vol_breakout_v1"
    name = "Volatility Breakout"
    version = "1.0.0"

    def __init__(
        self,
        atr_period: int = 20,
        consolidation_threshold: float = 0.5,
        volume_multiplier: float = 1.5,
        atr_multiplier_sl: float = 2.0,
        risk_per_trade: float = 0.01,
    ):
        self._atr_period = atr_period
        self._consolidation_threshold = consolidation_threshold
        self._volume_multiplier = volume_multiplier
        self._atr_multiplier_sl = atr_multiplier_sl
        self._risk_per_trade = risk_per_trade

        self._atr_history: deque = deque(maxlen=atr_period)
        self._volume_history: deque = deque(maxlen=20)
        self._consolidation_high: float = 0.0
        self._consolidation_low: float = 0.0
        self._in_consolidation: bool = False
        self._consolidation_start: int = 0

    def should_enter(self, features: FeatureSet) -> Optional[dict]:
        """Generar señal de entrada basada en ruptura de volatilidad."""
        self._update_history(features)

        if len(self._atr_history) < self._atr_period:
            return None

        avg_atr = sum(self._atr_history) / len(self._atr_history)
        current_atr = features.atr_14

        if self._in_consolidation:
            return self._check_breakout(features, avg_atr)
        else:
            return self._check_consolidation_start(features, avg_atr, current_atr)

    def should_exit(self, features: FeatureSet, position: dict) -> bool:
        """Evaluar si cerrar posición."""
        side = position.get("side", "BUY")
        consolidation_range = position.get("consolidation_range", 0)

        if side == "BUY":
            if features.close < position.get("stop_loss", 0):
                return True

            if features.close > position.get("take_profit", float("inf")):
                return True

            if features.atr_14 < consolidation_range * 0.5:
                return True

        elif side == "SELL":
            if features.close > position.get("stop_loss", float("inf")):
                return True

            if features.close < position.get("take_profit", 0):
                return True

            if features.atr_14 < consolidation_range * 0.5:
                return True

        return False

    def _update_history(self, features: FeatureSet) -> None:
        """Actualizar historiales de ATR y volumen."""
        self._atr_history.append(features.atr_14)
        self._volume_history.append(features.volume_sma_20)

    def _check_consolidation_start(
        self, features: FeatureSet, avg_atr: float, current_atr: float
    ) -> Optional[dict]:
        """Detectar inicio de consolidación (ATR contraído)."""
        if current_atr < avg_atr * self._consolidation_threshold:
            self._in_consolidation = True
            self._consolidation_high = features.close
            self._consolidation_low = features.close
            self._consolidation_start = len(self._atr_history)
            logger.info(
                "consolidation_started",
                atr_ratio=current_atr / avg_atr,
                threshold=self._consolidation_threshold,
            )
            return None

        return None

    def _check_breakout(
        self, features: FeatureSet, avg_atr: float
    ) -> Optional[dict]:
        """Verificar ruptura de consolidación."""
        current_atr = features.atr_14

        if current_atr > avg_atr * (self._consolidation_threshold + 0.2):
            if features.close > self._consolidation_high:
                return self._create_buy_breakout(features)
            elif features.close < self._consolidation_low:
                return self._create_sell_breakout(features)

        if features.close > self._consolidation_high:
            self._consolidation_high = features.close
        elif features.close < self._consolidation_low:
            self._consolidation_low = features.close

        if current_atr > avg_atr * 1.5:
            self._in_consolidation = False
            logger.info("consolidation_expired", reason="ATR expanded")

        return None

    def _create_buy_breakout(self, features: FeatureSet) -> dict:
        """Crear señal de compra por ruptura bullish."""
        avg_volume = sum(self._volume_history) / len(self._volume_history) if self._volume_history else 1
        if features.volume_sma_20 < avg_volume * self._volume_multiplier:
            self._in_consolidation = False
            return None

        entry = features.close
        range_size = self._consolidation_high - self._consolidation_low
        sl = entry - self._atr_multiplier_sl * features.atr_14
        tp = entry + range_size * 3

        self._in_consolidation = False

        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "side": "BUY",
            "confidence": 0.7,
            "consolidation_range": range_size,
            "breakout_type": "bullish",
        }

    def _create_sell_breakout(self, features: FeatureSet) -> dict:
        """Crear señal de venta por ruptura bearish."""
        avg_volume = sum(self._volume_history) / len(self._volume_history) if self._volume_history else 1
        if features.volume_sma_20 < avg_volume * self._volume_multiplier:
            self._in_consolidation = False
            return None

        entry = features.close
        range_size = self._consolidation_high - self._consolidation_low
        sl = entry + self._atr_multiplier_sl * features.atr_14
        tp = entry - range_size * 3

        self._in_consolidation = False

        return {
            "action": "SELL",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "side": "SELL",
            "confidence": 0.7,
            "consolidation_range": range_size,
            "breakout_type": "bearish",
        }

    def get_optimal_regimes(self) -> list[MarketRegime]:
        """Regímenes óptimos para Volatility Breakout."""
        return [MarketRegime.SIDEWAYS_HIGH_VOL, MarketRegime.BULL_TRENDING]

    def to_dict(self) -> dict:
        return {
            **super().to_dict(),
            "description": "Detecta consolidación (ATR contraído) y opera ruptura con volumen",
            "parameters": {
                "atr_period": self._atr_period,
                "consolidation_threshold": self._consolidation_threshold,
                "volume_multiplier": self._volume_multiplier,
                "atr_multiplier_sl": self._atr_multiplier_sl,
            },
            "timeframe": "1h",
            "symbols": ["BTCUSDT", "ETHUSDT", "XAUUSD"],
            "regimes": ["sideways_high_vol", "bull_trending"],
            "max_capital_pct": 0.15,
            "risk_per_trade_pct": self._risk_per_trade,
            "status": "active",
        }