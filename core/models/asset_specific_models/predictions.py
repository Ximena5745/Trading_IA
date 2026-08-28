"""
Module: core/models/asset_specific_models/predictions.py
Responsibility: Pydantic serialization models for individual and ensemble predictions
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPrediction(BaseModel):
    """Predicción individual de un modelo."""
    model_type: str
    strategy_type: str
    direction: str  # BUY, SELL, NEUTRAL
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    probability: dict[str, float] = Field(default_factory=dict)
    features_used: list[str] = Field(default_factory=list)
    shap_values: dict[str, float] = Field(default_factory=dict)


class EnsemblePrediction(BaseModel):
    """Predicción del ensemble/meta-modelo."""
    asset_class: str
    symbol: str
    timestamp: str
    final_direction: str
    final_score: float = Field(ge=-1.0, le=1.0)
    final_confidence: float = Field(ge=0.0, le=1.0)
    individual_predictions: list[ModelPrediction] = Field(default_factory=list)
    model_weights: dict[str, float] = Field(default_factory=dict)
    meta_model_contribution: float = 0.0

    # Filtros de decisión
    passed_threshold: bool = False
    expected_return: float = 0.0
    risk_assessment: str = "unknown"

    # Decisión final
    should_trade: bool = False
    suggested_position_size: float = 0.0
