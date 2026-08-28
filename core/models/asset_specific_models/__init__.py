"""
Package: core/models/asset_specific_models
Responsibility: Asset-specific model configurations and specialized architectures

Este paquete define las configuraciones específicas de modelos por tipo de activo
según las propuestas de mejora:
- CRYPTO: Alta volatilidad, momentum fuerte
- FOREX: Mean reversion + sesiones temporales
- INDICES: Tendencias limpias
- COMMODITIES (GOLD): Macro-driven

Antes un único archivo de 745 líneas con 4 enums + 6+ especificaciones de
modelo + factories (auditoría técnica 2026-07-25, hallazgo de calidad SRP).
Dividido en submódulos:
  - enums.py: AssetClass, ModelType, TargetType, StrategyType
  - features.py: FeatureConfig + *_FEATURES por clase de activo
  - specs.py: ModelSpec, AssetModelConfig
  - configs.py: *_MODEL_CONFIG concretos, ASSET_MODEL_REGISTRY, lookups
  - predictions.py: ModelPrediction, EnsemblePrediction (pydantic)
  - training_config.py: AssetSpecificTrainingConfig (pydantic)

El import path público `core.models.asset_specific_models` no cambia.

Nota: `AssetClass` aquí es una definición independiente de la `AssetClass` en
`core/models.py` (usada por `detect_asset_class`, `get_instrument`, etc.).
Ambas coinciden en valores string hoy, así que comparaciones/hash funcionan
por coincidencia — no por diseño. Es deuda técnica preexistente, no introducida
por este refactor; ver nota en PLAN_MAESTRO.md.
"""
from core.models.asset_specific_models.configs import (
    ASSET_MODEL_REGISTRY,
    COMMODITIES_MODEL_CONFIG,
    CRYPTO_MODEL_CONFIG,
    FOREX_MODEL_CONFIG,
    INDICES_MODEL_CONFIG,
    get_asset_model_config,
    get_model_config_for_symbol,
)
from core.models.asset_specific_models.enums import AssetClass, ModelType, StrategyType, TargetType
from core.models.asset_specific_models.features import (
    COMMODITIES_FEATURES,
    CRYPTO_FEATURES,
    FOREX_FEATURES,
    INDICES_FEATURES,
    FeatureConfig,
)
from core.models.asset_specific_models.predictions import EnsemblePrediction, ModelPrediction
from core.models.asset_specific_models.specs import AssetModelConfig, ModelSpec
from core.models.asset_specific_models.training_config import AssetSpecificTrainingConfig

__all__ = [
    "AssetClass",
    "ModelType",
    "TargetType",
    "StrategyType",
    "FeatureConfig",
    "ModelSpec",
    "AssetModelConfig",
    "CRYPTO_FEATURES",
    "FOREX_FEATURES",
    "INDICES_FEATURES",
    "COMMODITIES_FEATURES",
    "CRYPTO_MODEL_CONFIG",
    "FOREX_MODEL_CONFIG",
    "INDICES_MODEL_CONFIG",
    "COMMODITIES_MODEL_CONFIG",
    "ASSET_MODEL_REGISTRY",
    "get_asset_model_config",
    "get_model_config_for_symbol",
    "ModelPrediction",
    "EnsemblePrediction",
    "AssetSpecificTrainingConfig",
]
