"""
Module: core/consensus/__init__.py
Responsibility: Consensus engine exports
"""
from core.consensus.asset_specific_consensus import (
    ASSET_SPECIFIC_WEIGHTS,
    AssetSpecificConsensusEngine,
    create_consensus_engine,
)
from core.consensus.conflict_logger import ConflictLogger
from core.consensus.voting_engine import (
    AGENT_WEIGHTS_CRYPTO,
    AGENT_WEIGHTS_MT5,
    ConsensusEngine,
)

__all__ = [
    # Legacy consensus
    "ConsensusEngine",
    "AGENT_WEIGHTS_CRYPTO",
    "AGENT_WEIGHTS_MT5",
    "ConflictLogger",
    # Asset-specific consensus
    "AssetSpecificConsensusEngine",
    "create_consensus_engine",
    "ASSET_SPECIFIC_WEIGHTS",
]
