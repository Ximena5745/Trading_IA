"""
Module: core/consensus/voting_engine.py
Responsibility: Weighted voting across agents with regime gate
Dependencies: conflict_logger, models, logger
"""

from __future__ import annotations

from datetime import datetime

from core.consensus.conflict_logger import ConflictLogger
from core.models import AgentOutput, ConsensusOutput, RegimeOutput
from core.observability.logger import get_logger

logger = get_logger(__name__)

AGENT_WEIGHTS: dict[str, float] = {
    "technical_v1": 0.45,
    "regime_v1": 0.35,
    "microstructure_v1": 0.20,
}
MIN_CONSENSUS_SCORE = 0.30
MIN_AGENTS_AGREEING = 0.60


class ConsensusEngine:
    def __init__(self) -> None:
        self._conflict_logger = ConflictLogger()

    def aggregate(
        self,
        agent_outputs: list[AgentOutput],
        regime: RegimeOutput,
    ) -> ConsensusOutput:

        conflicts = self._conflict_logger.detect_conflicts(agent_outputs)
        symbol = agent_outputs[0].symbol if agent_outputs else ""
        ts = agent_outputs[0].timestamp if agent_outputs else datetime.utcnow()

        # Gate 1: regime veto
        if not regime.signal_allowed:
            logger.info(
                "signal_blocked_by_regime",
                regime=regime.regime,
                confidence=regime.confidence,
            )
            return ConsensusOutput(
                timestamp=ts,
                symbol=symbol,
                final_direction="NEUTRAL",
                weighted_score=0.0,
                agents_agreement=0.0,
                blocked_by_regime=True,
                agent_outputs=agent_outputs,
                conflicts=conflicts,
            )

        # Weighted score
        total_weight = 0.0
        weighted_score = 0.0
        for output in agent_outputs:
            weight = AGENT_WEIGHTS.get(output.agent_id, 0.10)
            weighted_score += output.score * weight
            total_weight += weight

        if total_weight > 0:
            weighted_score /= total_weight

        # Agreement ratio
        if abs(weighted_score) >= MIN_CONSENSUS_SCORE:
            dominant = "BUY" if weighted_score > 0 else "SELL"
            agreeing = sum(
                1
                for o in agent_outputs
                if (dominant == "BUY" and o.score > 0)
                or (dominant == "SELL" and o.score < 0)
            )
            agreement = agreeing / len(agent_outputs) if agent_outputs else 0.0
        else:
            dominant = "NEUTRAL"
            agreement = 0.0

        # Gate 2: minimum agreement
        if agreement < MIN_AGENTS_AGREEING and dominant != "NEUTRAL":
            logger.info(
                "signal_blocked_low_agreement",
                agreement=agreement,
                threshold=MIN_AGENTS_AGREEING,
            )
            dominant = "NEUTRAL"

        # Gate 3: minimum score
        if abs(weighted_score) < MIN_CONSENSUS_SCORE:
            dominant = "NEUTRAL"

        logger.info(
            "consensus_result",
            symbol=symbol,
            direction=dominant,
            score=round(weighted_score, 4),
            agreement=round(agreement, 4),
            conflicts=len(conflicts),
        )

        return ConsensusOutput(
            timestamp=ts,
            symbol=symbol,
            final_direction=dominant,
            weighted_score=round(weighted_score, 4),
            agents_agreement=round(agreement, 4),
            blocked_by_regime=False,
            agent_outputs=agent_outputs,
            conflicts=conflicts,
        )
