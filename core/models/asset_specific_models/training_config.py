"""
Module: core/models/asset_specific_models/training_config.py
Responsibility: Pydantic training configuration per asset/symbol
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from core.models.asset_specific_models.enums import AssetClass, ModelType, TargetType


class AssetSpecificTrainingConfig(BaseModel):
    """Configuración de entrenamiento específica por activo."""
    asset_class: AssetClass
    symbol: str
    timeframe: str = "1h"
    train_start_date: Optional[str] = None
    train_end_date: Optional[str] = None
    test_size: float = 0.2
    validation_size: float = 0.1

    # Configuración de modelos
    models_to_train: list[ModelType] = Field(default_factory=list)
    target_type: TargetType = TargetType.TERNARY

    # Hiperparámetros de entrenamiento
    use_cross_validation: bool = True
    n_folds: int = 5
    early_stopping_rounds: int = 50

    # Configuración de features
    feature_selection: bool = True
    max_features: int = 50

    # Configuración de ensemble
    train_meta_model: bool = True
    meta_model_type: ModelType = ModelType.LIGHTGBM
