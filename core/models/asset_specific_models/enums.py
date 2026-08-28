"""
Module: core/models/asset_specific_models/enums.py
Responsibility: Base enums shared across asset-specific model configuration
"""
from __future__ import annotations

from enum import Enum


class AssetClass(str, Enum):
    """Clases de activos soportadas."""
    CRYPTO = "crypto"
    FOREX = "forex"
    INDICES = "indices"
    COMMODITIES = "commodities"


class ModelType(str, Enum):
    """Tipos de modelos ML disponibles."""
    LIGHTGBM = "lightgbm"
    XGBOOST = "xgboost"
    CATBOOST = "catboost"
    RANDOM_FOREST = "random_forest"
    LOGISTIC_REGRESSION = "logistic_regression"
    SVM = "svm"
    LSTM = "lstm"
    TRANSFORMER = "transformer"
    TEMPORAL_FUSION = "temporal_fusion_transformer"
    HMM = "hmm"
    GAUSSIAN_MIXTURE = "gaussian_mixture"
    REINFORCEMENT_LEARNING = "reinforcement_learning"


class TargetType(str, Enum):
    """Tipos de target para entrenamiento."""
    BINARY = "binary"  # Compra/Venta
    TERNARY = "ternary"  # Compra/Neutro/Venta
    REGRESSION = "regression"  # Retorno futuro
    PERCENTILE = "percentile"  # Percentiles de retorno
    DYNAMIC = "dynamic"  # Threshold dinámico por volatilidad
    MULTI_STEP = "multi_step"  # Multi-step ahead (2, 3, 5 bars)
    ASYMMETRIC = "asymmetric"  # Diferentes umbrales up/down
    RISK_ADJUSTED = "risk_adjusted"  # Sharpe-like target
    VOLATILITY_REGIME = "volatility_regime"  # Aware del régimen de volatilidad


class StrategyType(str, Enum):
    """Tipos de estrategias por modelo."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    MOMENTUM = "momentum"
    RANGE_TRADING = "range_trading"
    MACRO_DRIVEN = "macro_driven"
