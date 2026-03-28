"""
Module: core/consensus/conflict_logger.py
Responsibility: Log explicit disagreements between agents
Dependencies: logger
"""
from __future__ import annotations

from core.models import AgentOutput
from core.observability.logger import get_logger

logger = get_logger(__name__)


class ConflictLogger:
    def detect_conflicts(self, agent_outputs: list[AgentOutput]) -> list[str]:
        """Return human-readable descriptions of agent disagreements."""
        conflicts: list[str] = []
        directions = [a.direction for a in agent_outputs if a.direction != "NEUTRAL"]

        if len(set(directions)) > 1:
            summary = ", ".join(f"{a.agent_id}={a.direction}({a.score:+.2f})" for a in agent_outputs)
            conflicts.append(f"Direction conflict: {summary}")

        high_conf = [a for a in agent_outputs if a.confidence >= 0.70]
        if len(high_conf) >= 2:
            dirs = {a.direction for a in high_conf}
            if len(dirs) > 1:
                conflicts.append(
                    "High-confidence conflict: "
                    + ", ".join(f"{a.agent_id}={a.direction}" for a in high_conf)
                )

        if conflicts:
            logger.warning(
                "agent_conflict_detected",
                conflicts=conflicts,
                agents=[a.agent_id for a in agent_outputs],
            )
        return conflicts
