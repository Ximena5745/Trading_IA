"""
Module: core/consensus/voting_engine.py
Responsibility: Weighted voting across agents with regime gate.
  Weights are conditional on asset_class (decision v2.4):
    Crypto:          Technical 45% | Regime 35% | Microstructure 20%
    Forex/Indices/Commodities: Technical 55% | Regime 45% | Microstructure 0%
  MicrostructureAgent receives 0% weight for non-crypto assets because
  MT5 does not expose L2 order book data.
Dependencies: conflict_logger, models, logger
"""
from __future__ import annotations

from datetime import datetime

from core.consensus.conflict_logger import ConflictLogger
from core.models import (
    AgentOutput,
    AssetClass,
    ConsensusOutput,
    RegimeOutput,
    detect_asset_class,
)
from core.observability.logger import get_logger

logger = get_logger(__name__)

# ── Agent weights by asset class (decision v2.4) ─────────────────────────────
AGENT_WEIGHTS_CRYPTO: dict[str, float] = {
    "technical_v1": 0.45,
    "regime_v1": 0.35,
    "microstructure_v1": 0.20,
}

AGENT_WEIGHTS_MT5: dict[str, float] = {
    "technical_v1": 0.55,
    "regime_v1": 0.45,
    "microstructure_v1": 0.00,  # disabled — MT5 has no L2 book
}

MIN_CONSENSUS_SCORE = 0.30
MIN_AGENTS_AGREEING = 0.60

# Alias for backward compatibility — defaults to crypto weights
AGENT_WEIGHTS: dict[str, float] = AGENT_WEIGHTS_CRYPTO


def _weights_for_symbol(symbol: str) -> dict[str, float]:
    asset_class = detect_asset_class(symbol)
    if asset_class == AssetClass.CRYPTO:
        return AGENT_WEIGHTS_CRYPTO
    return AGENT_WEIGHTS_MT5


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
        weights = _weights_for_symbol(symbol)

        # Gate 1: regime veto (VOLATILE_CRASH or low confidence)
        if not regime.signal_allowed:
            logger.info(
                "signal_blocked_by_regime",
                symbol=symbol,
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

        # Weighted score — skip agents with 0 weight
        total_weight = 0.0
        weighted_score = 0.0
        for output in agent_outputs:
            weight = weights.get(output.agent_id, 0.10)
            if weight == 0.0:
                continue
            weighted_score += output.score * weight
            total_weight += weight

        if total_weight > 0:
            weighted_score /= total_weight

        # Agreement ratio (among agents with non-zero weight)
        active_outputs = [
            o for o in agent_outputs if weights.get(o.agent_id, 0.10) > 0.0
        ]

        if abs(weighted_score) >= MIN_CONSENSUS_SCORE and active_outputs:
            dominant = "BUY" if weighted_score > 0 else "SELL"
            agreeing = sum(
                1
                for o in active_outputs
                if (dominant == "BUY" and o.score > 0)
                or (dominant == "SELL" and o.score < 0)
            )
            agreement = agreeing / len(active_outputs)
        else:
            dominant = "NEUTRAL"
            agreement = 0.0

        # Gate 2: minimum agreement
        if agreement < MIN_AGENTS_AGREEING and dominant != "NEUTRAL":
            logger.info(
                "signal_blocked_low_agreement",
                symbol=symbol,
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
            weight_mode="crypto" if weights is AGENT_WEIGHTS_CRYPTO else "mt5",
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
