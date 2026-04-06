"""
Module: core/agents/__init__.py
Responsibility: Agent exports for the trading system
"""
from core.agents.asset_specific_agent import AssetSpecificAgent, create_asset_agent
from core.agents.base_agent import AbcAgent
from core.agents.fundamental_agent import FundamentalAgent
from core.agents.microstructure_agent import MicrostructureAgent
from core.agents.regime_agent import RegimeAgent
from core.agents.technical_agent import TechnicalAgent

__all__ = [
    # Base
    "AbcAgent",
    # Existing agents
    "TechnicalAgent",
    "RegimeAgent",
    "MicrostructureAgent",
    "FundamentalAgent",
    # Asset-specific multi-model agent
    "AssetSpecificAgent",
    "create_asset_agent",
]
