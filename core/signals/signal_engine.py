"""
Module: core/signals/signal_engine.py
Responsibility: Aggregate consensus into actionable signal with XAI explanation
Dependencies: xai_module, models, constants, logger
"""
from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Optional
from uuid import uuid4

from core.config.constants import (
    ATR_STOP_LOSS_MULTIPLIER,
    ATR_TAKE_PROFIT_MULTIPLIER,
    HARD_LIMITS,
)
from core.exceptions import AgentPredictionError
from core.models import ConsensusOutput, FeatureSet, MarketRegime, Signal
from core.observability.logger import get_logger
from core.signals.xai_module import XAIModule

logger = get_logger(__name__)

# QWQ-5: SL/TP adaptativos por activo (percentiles ATR histórico)
ATR_PERCENTILES: dict[str, tuple[float, float]] = {
    "BTCUSDT": (1.5, 2.5),
    "ETHUSDT": (1.5, 2.5),
    "EURUSD": (1.0, 2.0),
    "GBPUSD": (1.0, 2.0),
    "USDJPY": (1.0, 2.0),
    "XAUUSD": (1.2, 2.0),
    "US500": (1.0, 1.5),
    "US30": (1.0, 1.5),
}

# QWQ-5: Cache para percentiles ATR calculados dinámicamente
_ATR_PERCENTILE_CACHE: dict[str, tuple[float, float]] = {}


def compute_atr_percentiles(atr_series: "pd.Series", symbol: str) -> tuple[float, float]:
    """
    QWQ-5: Calcula percentiles (P20, P80) del ATR como múltiplos dinámicos.
    P20 -> multiplicador SL (más ajustado en volatilidad baja)
    P80 -> multiplicador TP (más amplio en volatilidad alta)
    """
    global _ATR_PERCENTILE_CACHE

    if symbol in _ATR_PERCENTILE_CACHE:
        return _ATR_PERCENTILE_CACHE[symbol]

    if len(atr_series) < 100:
        default = ATR_PERCENTILES.get(symbol, (1.5, 2.5))
        return default

    p20 = atr_series.quantile(0.20)
    p80 = atr_series.quantile(0.80)

    # Evitar valores extremos
    p20 = max(p20, atr_series.median() * 0.5)
    p80 = min(p80, atr_series.median() * 1.5)

    # Mapeo a múltiplos: percentil bajo = multiplicador bajo (SL más ajustado)
    default_sl, default_tp = ATR_PERCENTILES.get(symbol, (1.5, 2.5))
    sl_mult = default_sl * (p20 / atr_series.median())
    tp_mult = default_tp * (p80 / atr_series.median())

    # Clampear valores razonables
    sl_mult = round(max(0.8, min(3.0, sl_mult)), 2)
    tp_mult = round(max(1.2, min(4.0, tp_mult)), 2)

    _ATR_PERCENTILE_CACHE[symbol] = (sl_mult, tp_mult)
    return sl_mult, tp_mult


class SignalEngine:
    def __init__(self) -> None:
        self._xai = XAIModule()
        # QWQ-6: Cooldown mínimo 3 barras entre señales del mismo símbolo
        self._last_signal_time: dict[str, datetime] = {}
        self._cooldown_bars = 3

    def generate(
        self,
        consensus: ConsensusOutput,
        features: FeatureSet,
        strategy_id: str = "default_v1",
    ) -> Optional[Signal]:
        if consensus.final_direction == "NEUTRAL":
            logger.debug(
                "signal_not_generated",
                reason="NEUTRAL consensus",
                symbol=features.symbol,
            )
            return None

        # QWQ-6: Cooldown de 3 barras entre señales del mismo símbolo
        symbol = features.symbol
        last_time = self._last_signal_time.get(symbol)
        if last_time and features.timestamp:
            bars_since_last = (features.timestamp - last_time).total_seconds() / 3600
            if bars_since_last < self._cooldown_bars:
                logger.info(
                    "signal_cooldown_active",
                    symbol=symbol,
                    bars_since_last=bars_since_last,
                )
                return None

        try:
            entry = features.close
            atr = features.atr_14
            direction = consensus.final_direction

            stop_loss, take_profit = self._compute_sl_tp(entry, atr, direction, features.symbol)
            risk_reward = self._compute_rr(entry, stop_loss, take_profit)

            if risk_reward < HARD_LIMITS["min_risk_reward_ratio"]:
                logger.info(
                    "signal_rejected_low_rr",
                    symbol=features.symbol,
                    rr=risk_reward,
                    min_rr=HARD_LIMITS["min_risk_reward_ratio"],
                )
                return None

            explanation = self._xai.build_explanation(consensus)
            confidence = round(
                (abs(consensus.weighted_score) + consensus.agents_agreement) / 2, 4
            )
            summary = self._xai.generate_summary(
                explanation, direction, confidence, features.symbol
            )
            idempotency_key = self._make_key(
                features.symbol, features.timestamp, direction
            )

            signal = Signal(
                id=str(uuid4()),
                idempotency_key=idempotency_key,
                timestamp=features.timestamp,
                symbol=features.symbol,
                action=direction,
                entry_price=round(entry, 8),
                stop_loss=round(stop_loss, 8),
                take_profit=round(take_profit, 8),
                risk_reward_ratio=round(risk_reward, 2),
                confidence=confidence,
                explanation=explanation,
                summary=summary,
                regime=consensus.agent_outputs[0].agent_id
                and self._extract_regime(consensus),
                strategy_id=strategy_id,
                status="pending",
            )

            self._last_signal_time[symbol] = features.timestamp

            logger.info(
                "signal_generated",
                signal_id=signal.id,
                symbol=signal.symbol,
                action=signal.action,
                confidence=signal.confidence,
                rr=signal.risk_reward_ratio,
                summary=signal.summary,
            )
            return signal

        except Exception as e:
            raise AgentPredictionError(f"SignalEngine failed: {e}") from e

    def _compute_sl_tp(
        self, entry: float, atr: float, direction: str, symbol: str = None,
        atr_history: "pd.Series" = None
    ) -> tuple[float, float]:
        """
        Calculate SL/TP with adaptive multipliers based on asset (QWQ-5).
        Uses dynamic ATR percentiles if available, otherwise falls back to static dict.
        """
        default_mults = (ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER)

        if symbol and atr_history is not None and len(atr_history) >= 100:
            sl_mult, tp_mult = compute_atr_percentiles(atr_history, symbol)
        else:
            sl_mult, tp_mult = ATR_PERCENTILES.get(symbol, default_mults) if symbol else default_mults

        if direction == "BUY":
            sl = entry - sl_mult * atr
            tp = entry + tp_mult * atr
        else:
            sl = entry + sl_mult * atr
            tp = entry - tp_mult * atr
        return sl, tp

    def _compute_rr(self, entry: float, sl: float, tp: float) -> float:
        risk = abs(entry - sl)
        reward = abs(tp - entry)
        return reward / risk if risk > 0 else 0.0

    @staticmethod
    def _make_key(symbol: str, timestamp: datetime, direction: str) -> str:
        raw = f"{symbol}:{timestamp.isoformat()}:{direction}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @staticmethod
    def _extract_regime(consensus: ConsensusOutput) -> MarketRegime:
        for output in consensus.agent_outputs:
            if output.agent_id == "regime_v1":
                try:
                    score = output.score
                    if score >= 0.5:
                        return MarketRegime.BULL_TRENDING
                    if score <= -0.5:
                        return MarketRegime.BEAR_TRENDING
                except Exception:
                    pass
        return MarketRegime.SIDEWAYS_LOW_VOL
