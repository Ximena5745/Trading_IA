"""
Module: core/models/__init__.py
Responsibility: Model exports and asset-specific configurations
"""
import sys
import importlib.util
from pathlib import Path

# Load the core/models.py file dynamically to avoid naming conflict with the models/ directory
_models_file = Path(__file__).parent.parent / "models.py"
_spec = importlib.util.spec_from_file_location("core_models_module", _models_file)
_models_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_models_module)

# Import from the dynamically loaded module
from core.models.asset_specific_models import (
    AssetClass,
    AssetModelConfig,
    AssetSpecificTrainingConfig,
    COMMODITIES_FEATURES,
    COMMODITIES_MODEL_CONFIG,
    CRYPTO_FEATURES,
    CRYPTO_MODEL_CONFIG,
    EnsemblePrediction,
    FOREX_FEATURES,
    FOREX_MODEL_CONFIG,
    FeatureConfig,
    INDICES_FEATURES,
    INDICES_MODEL_CONFIG,
    ModelPrediction,
    ModelSpec,
    ModelType,
    StrategyType,
    TargetType,
    get_asset_model_config,
    get_model_config_for_symbol,
)

# Re-export critical classes from core/models.py
AgentOutput = _models_module.AgentOutput
FeatureSet = _models_module.FeatureSet
MarketData = _models_module.MarketData
MarketRegime = _models_module.MarketRegime
RegimeOutput = _models_module.RegimeOutput
InstrumentConfig = _models_module.InstrumentConfig
ConsensusOutput = _models_module.ConsensusOutput
Signal = _models_module.Signal
Order = _models_module.Order
Portfolio = _models_module.Portfolio
Position = _models_module.Position
SignalExplanationFactor = _models_module.SignalExplanationFactor
OrderStatus = _models_module.OrderStatus
KillSwitchStateModel = _models_module.KillSwitchStateModel
detect_asset_class = _models_module.detect_asset_class
get_instrument = _models_module.get_instrument

__all__ = [
    # Enums
    "AssetClass",
    "ModelType",
    "TargetType",
    "StrategyType",
    "MarketRegime",
    "OrderStatus",
    # Configs
    "FeatureConfig",
    "ModelSpec",
    "AssetModelConfig",
    "AssetSpecificTrainingConfig",
    # Feature configs por activo
    "CRYPTO_FEATURES",
    "FOREX_FEATURES",
    "INDICES_FEATURES",
    "COMMODITIES_FEATURES",
    # Model configs por activo
    "CRYPTO_MODEL_CONFIG",
    "FOREX_MODEL_CONFIG",
    "INDICES_MODEL_CONFIG",
    "COMMODITIES_MODEL_CONFIG",
    # Predicciones
    "ModelPrediction",
    "EnsemblePrediction",
    # Data models
    "AgentOutput",
    "FeatureSet",
    "MarketData",
    "RegimeOutput",
    "InstrumentConfig",
    "ConsensusOutput",
    "Signal",
    "SignalExplanationFactor",
    "Order",
    "Portfolio",
    "Position",
    "KillSwitchStateModel",
    # Funciones
    "get_asset_model_config",
    "get_model_config_for_symbol",
    "detect_asset_class",
    "get_instrument",
]
