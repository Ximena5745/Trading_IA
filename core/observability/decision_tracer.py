"""
Module: core/observability/decision_tracer.py
Responsibility: Full audit trail for every signal lifecycle
Dependencies: logger
"""
from __future__ import annotations

from datetime import datetime

from core.observability.logger import get_logger

logger = get_logger(__name__)


class DecisionTracer:
    """Records the complete decision chain for each generated signal."""

    def trace(self, signal_id: str, step: str, **context) -> None:
        logger.info(
            "signal_lifecycle",
            signal_id=signal_id,
            step=step,
            ts=datetime.utcnow().isoformat(),
            **context,
        )

    def trace_market_data(self, signal_id: str, symbol: str, ohlcv: dict) -> None:
        self.trace(signal_id, "market_data_received", symbol=symbol, ohlcv=ohlcv)

    def trace_features(
        self, signal_id: str, feature_version: str, key_values: dict
    ) -> None:
        self.trace(
            signal_id,
            "features_calculated",
            feature_version=feature_version,
            key_values=key_values,
        )

    def trace_agent_output(
        self, signal_id: str, agent_id: str, score: float, confidence: float
    ) -> None:
        self.trace(
            signal_id,
            "agent_output",
            agent_id=agent_id,
            score=score,
            confidence=confidence,
        )

    def trace_consensus(
        self, signal_id: str, weighted_score: float, blocked: bool
    ) -> None:
        self.trace(
            signal_id,
            "consensus_result",
            weighted_score=weighted_score,
            blocked_by_regime=blocked,
        )

    def trace_signal(
        self, signal_id: str, action: str, entry: float, sl: float, tp: float
    ) -> None:
        self.trace(
            signal_id,
            "signal_generated",
            action=action,
            entry=entry,
            stop_loss=sl,
            take_profit=tp,
        )

    def trace_risk_check(self, signal_id: str, approved: bool, reason: str) -> None:
        self.trace(signal_id, "risk_check", approved=approved, reason=reason)

    def trace_execution(
        self, signal_id: str, fill_price: float, quantity: float, commission: float
    ) -> None:
        self.trace(
            signal_id,
            "execution_result",
            fill_price=fill_price,
            quantity=quantity,
            commission=commission,
        )
