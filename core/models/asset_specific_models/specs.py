"""
Module: core/models/asset_specific_models/specs.py
Responsibility: Per-model and per-asset-class model configuration dataclasses
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from core.models.asset_specific_models.enums import AssetClass, ModelType, StrategyType, TargetType
from core.models.asset_specific_models.features import FeatureConfig


@dataclass
class ModelSpec:
    """Especificación de un modelo individual."""
    model_type: ModelType
    strategy_type: StrategyType
    target_type: TargetType
    hyperparams: dict[str, Any] = field(default_factory=dict)
    features: list[str] = field(default_factory=list)
    weight: float = 1.0  # Peso en el ensemble
    min_confidence: float = 0.5
    description: str = ""


@dataclass
class AssetModelConfig:
    """Configuración completa de modelos para un tipo de activo."""
    asset_class: AssetClass
    feature_config: FeatureConfig
    models: list[ModelSpec] = field(default_factory=list)
    meta_model_type: ModelType = ModelType.LIGHTGBM
    meta_model_params: dict[str, Any] = field(default_factory=dict)

    # Umbrales de decisión
    signal_threshold: float = 0.6
    min_expected_return: float = 0.001
    max_risk_per_trade: float = 0.02

    # Configuración de ensemble
    use_stacking: bool = True
    use_dynamic_weights: bool = True

    def get_model_by_strategy(self, strategy: StrategyType) -> Optional[ModelSpec]:
        """Obtiene modelo por tipo de estrategia."""
        for model in self.models:
            if model.strategy_type == strategy:
                return model
        return None
