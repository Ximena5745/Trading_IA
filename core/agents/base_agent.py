"""
Module: core/agents/base_agent.py
Responsibility: Abstract interface for all AI agents
Dependencies: models
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import AgentOutput, FeatureSet


class AbcAgent(ABC):
    agent_id: str
    model_version: str

    @abstractmethod
    def predict(self, features: FeatureSet) -> AgentOutput:
        """Run inference and return scored output with SHAP values."""
        ...

    @abstractmethod
    def is_ready(self) -> bool:
        """Return True if the model is loaded and ready to predict."""
        ...
