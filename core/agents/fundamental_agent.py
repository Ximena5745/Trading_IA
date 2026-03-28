"""
Module: core/agents/fundamental_agent.py
Responsibility: Fundamental data stub — activatable in Fase 5
Dependencies: base_agent, models
"""
from __future__ import annotations

from core.agents.base_agent import AbcAgent
from core.models import AgentOutput, FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)


class FundamentalAgent(AbcAgent):
    """
    Stub — interface defined, data source activated in Fase 5.
    Will consume: fear & greed index, on-chain data, news sentiment.
    """

    agent_id = "fundamental_v1"
    model_version = "stub"

    def is_ready(self) -> bool:
        return False  # not active in MVP

    def predict(self, features: FeatureSet) -> AgentOutput:
        logger.debug("fundamental_agent_stub_called", symbol=features.symbol)
        return AgentOutput(
            agent_id=self.agent_id,
            timestamp=features.timestamp,
            symbol=features.symbol,
            direction="NEUTRAL",
            score=0.0,
            confidence=0.0,
            features_used=[],
            shap_values={},
            model_version=self.model_version,
        )
