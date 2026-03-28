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

from core.config.constants import ATR_STOP_LOSS_MULTIPLIER, ATR_TAKE_PROFIT_MULTIPLIER, HARD_LIMITS
from core.exceptions import AgentPredictionError
from core.models import ConsensusOutput, FeatureSet, MarketRegime, Signal
from core.observability.logger import get_logger
from core.signals.xai_module import XAIModule

logger = get_logger(__name__)


class SignalEngine:
    def __init__(self) -> None:
        self._xai = XAIModule()

    def generate(
        self,
        consensus: ConsensusOutput,
        features: FeatureSet,
        strategy_id: str = "default_v1",
    ) -> Optional[Signal]:
        if consensus.final_direction == "NEUTRAL":
            logger.debug("signal_not_generated", reason="NEUTRAL consensus", symbol=features.symbol)
            return None

        try:
            entry = features.close
            atr = features.atr_14
            direction = consensus.final_direction

            stop_loss, take_profit = self._compute_sl_tp(entry, atr, direction)
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
            summary = self._xai.generate_summary(explanation, direction, confidence, features.symbol)
            idempotency_key = self._make_key(features.symbol, features.timestamp, direction)

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
                regime=consensus.agent_outputs[0].agent_id and self._extract_regime(consensus),
                strategy_id=strategy_id,
                status="pending",
            )

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

    def _compute_sl_tp(self, entry: float, atr: float, direction: str) -> tuple[float, float]:
        if direction == "BUY":
            sl = entry - ATR_STOP_LOSS_MULTIPLIER * atr
            tp = entry + ATR_TAKE_PROFIT_MULTIPLIER * atr
        else:
            sl = entry + ATR_STOP_LOSS_MULTIPLIER * atr
            tp = entry - ATR_TAKE_PROFIT_MULTIPLIER * atr
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
