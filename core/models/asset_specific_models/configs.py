"""
Module: core/models/asset_specific_models/configs.py
Responsibility: Concrete per-asset-class model ensembles, registry and lookup

Configuraciones concretas según las propuestas de mejora:
- CRYPTO: Alta volatilidad, momentum fuerte
- FOREX: Mean reversion + sesiones temporales
- INDICES: Tendencias limpias
- COMMODITIES (GOLD): Macro-driven
"""
from __future__ import annotations

from core.models.asset_specific_models.enums import AssetClass, ModelType, StrategyType, TargetType
from core.models.asset_specific_models.features import (
    COMMODITIES_FEATURES,
    CRYPTO_FEATURES,
    FOREX_FEATURES,
    INDICES_FEATURES,
)
from core.models.asset_specific_models.specs import AssetModelConfig, ModelSpec

# CRYPTO: BTC, ETH - Alta volatilidad, momentum fuerte
CRYPTO_MODEL_CONFIG = AssetModelConfig(
    asset_class=AssetClass.CRYPTO,
    feature_config=CRYPTO_FEATURES,
    models=[
        ModelSpec(
            model_type=ModelType.LIGHTGBM,
            strategy_type=StrategyType.MOMENTUM,
            target_type=TargetType.TERNARY,
            hyperparams={
                "n_estimators": 500,
                "learning_rate": 0.05,
                "num_leaves": 127,
                "max_depth": 10,
                "min_child_samples": 20,
                "reg_alpha": 0.1,
                "reg_lambda": 0.2,
                "feature_fraction": 0.8,
                "bagging_fraction": 0.8,
            },
            weight=0.35,
            description="LightGBM optimizado para momentum en crypto",
        ),
        ModelSpec(
            model_type=ModelType.LSTM,
            strategy_type=StrategyType.TREND_FOLLOWING,
            target_type=TargetType.REGRESSION,
            hyperparams={
                "units": 128,
                "dropout": 0.3,
                "recurrent_dropout": 0.2,
                "learning_rate": 0.001,
                "sequence_length": 60,
                "batch_size": 32,
            },
            weight=0.30,
            description="LSTM para capturar tendencias de largo plazo",
        ),
        ModelSpec(
            model_type=ModelType.TEMPORAL_FUSION,
            strategy_type=StrategyType.VOLATILITY_BREAKOUT,
            target_type=TargetType.TERNARY,
            hyperparams={
                "hidden_size": 160,
                "attention_head_size": 4,
                "num_heads": 4,
                "dropout": 0.1,
                "learning_rate": 0.001,
            },
            weight=0.25,
            description="Temporal Fusion Transformer para volatilidad",
        ),
        ModelSpec(
            model_type=ModelType.CATBOOST,
            strategy_type=StrategyType.MEAN_REVERSION,
            target_type=TargetType.BINARY,
            hyperparams={
                "iterations": 500,
                "depth": 8,
                "learning_rate": 0.05,
                "l2_leaf_reg": 3.0,
            },
            weight=0.10,
            description="CatBoost para mean reversion en rangos",
        ),
    ],
    meta_model_type=ModelType.LIGHTGBM,
    meta_model_params={
        "n_estimators": 200,
        "learning_rate": 0.05,
        "num_leaves": 31,
    },
    signal_threshold=0.65,
    min_expected_return=0.005,
)

# FOREX: EURUSD, GBPUSD, USDJPY - Mean reversion + sesiones
FOREX_MODEL_CONFIG = AssetModelConfig(
    asset_class=AssetClass.FOREX,
    feature_config=FOREX_FEATURES,
    models=[
        ModelSpec(
            model_type=ModelType.LIGHTGBM,
            strategy_type=StrategyType.MEAN_REVERSION,
            target_type=TargetType.TERNARY,
            hyperparams={
                "n_estimators": 400,
                "learning_rate": 0.03,
                "num_leaves": 63,
                "max_depth": 8,
                "min_child_samples": 50,
                "reg_alpha": 0.2,
                "reg_lambda": 0.3,
            },
            weight=0.40,
            description="LightGBM con features temporales para Forex",
        ),
        ModelSpec(
            model_type=ModelType.HMM,
            strategy_type=StrategyType.RANGE_TRADING,
            target_type=TargetType.BINARY,
            hyperparams={
                "n_components": 5,
                "covariance_type": "full",
                "n_iter": 100,
            },
            weight=0.25,
            description="Hidden Markov Model para detección de regímenes",
        ),
        ModelSpec(
            model_type=ModelType.LOGISTIC_REGRESSION,
            strategy_type=StrategyType.TREND_FOLLOWING,
            target_type=TargetType.BINARY,
            hyperparams={
                "C": 1.0,
                "penalty": "l2",
                "solver": "lbfgs",
                "max_iter": 1000,
            },
            weight=0.20,
            description="Regresión logística como baseline robusto",
        ),
        ModelSpec(
            model_type=ModelType.SVM,
            strategy_type=StrategyType.MOMENTUM,
            target_type=TargetType.BINARY,
            hyperparams={
                "C": 10.0,
                "kernel": "rbf",
                "gamma": "scale",
                "probability": True,
            },
            weight=0.15,
            description="SVM para momentum en Forex",
        ),
    ],
    meta_model_type=ModelType.LOGISTIC_REGRESSION,
    meta_model_params={
        "C": 1.0,
        "penalty": "l2",
    },
    signal_threshold=0.60,
    min_expected_return=0.0003,
)

# INDICES: US500, US30 - Tendencias limpias
INDICES_MODEL_CONFIG = AssetModelConfig(
    asset_class=AssetClass.INDICES,
    feature_config=INDICES_FEATURES,
    models=[
        ModelSpec(
            model_type=ModelType.LIGHTGBM,
            strategy_type=StrategyType.TREND_FOLLOWING,
            target_type=TargetType.TERNARY,
            hyperparams={
                "n_estimators": 500,
                "learning_rate": 0.03,
                "num_leaves": 63,
                "max_depth": 8,
                "min_child_samples": 30,
            },
            weight=0.35,
            description="LightGBM para trend following",
        ),
        ModelSpec(
            model_type=ModelType.XGBOOST,
            strategy_type=StrategyType.MOMENTUM,
            target_type=TargetType.BINARY,
            hyperparams={
                "n_estimators": 400,
                "max_depth": 8,
                "learning_rate": 0.05,
                "subsample": 0.8,
                "colsample_bytree": 0.8,
            },
            weight=0.30,
            description="XGBoost como baseline fuerte",
        ),
        ModelSpec(
            model_type=ModelType.RANDOM_FOREST,
            strategy_type=StrategyType.MEAN_REVERSION,
            target_type=TargetType.BINARY,
            hyperparams={
                "n_estimators": 300,
                "max_depth": 15,
                "min_samples_split": 10,
                "min_samples_leaf": 5,
            },
            weight=0.20,
            description="Random Forest para robustez",
        ),
        ModelSpec(
            model_type=ModelType.REINFORCEMENT_LEARNING,
            strategy_type=StrategyType.TREND_FOLLOWING,
            target_type=TargetType.REGRESSION,
            hyperparams={
                "algorithm": "PPO",
                "learning_rate": 0.0003,
                "gamma": 0.99,
                "n_steps": 2048,
            },
            weight=0.15,
            description="Reinforcement Learning (fase avanzada)",
        ),
    ],
    meta_model_type=ModelType.XGBOOST,
    meta_model_params={
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.05,
    },
    signal_threshold=0.60,
    min_expected_return=0.001,
)

# COMMODITIES: GOLD (XAUUSD) - Macro-driven
COMMODITIES_MODEL_CONFIG = AssetModelConfig(
    asset_class=AssetClass.COMMODITIES,
    feature_config=COMMODITIES_FEATURES,
    models=[
        ModelSpec(
            model_type=ModelType.LIGHTGBM,
            strategy_type=StrategyType.MACRO_DRIVEN,
            target_type=TargetType.TERNARY,
            hyperparams={
                "n_estimators": 400,
                "learning_rate": 0.03,
                "num_leaves": 63,
                "max_depth": 8,
                "min_child_samples": 40,
                "reg_alpha": 0.1,
                "reg_lambda": 0.2,
            },
            weight=0.40,
            description="LightGBM con features macro para oro",
        ),
        ModelSpec(
            model_type=ModelType.HMM,
            strategy_type=StrategyType.VOLATILITY_BREAKOUT,
            target_type=TargetType.BINARY,
            hyperparams={
                "n_components": 4,
                "covariance_type": "diag",
                "n_iter": 100,
            },
            weight=0.30,
            description="Regime switching model para volatilidad",
        ),
        ModelSpec(
            model_type=ModelType.CATBOOST,
            strategy_type=StrategyType.MEAN_REVERSION,
            target_type=TargetType.BINARY,
            hyperparams={
                "iterations": 400,
                "depth": 8,
                "learning_rate": 0.03,
            },
            weight=0.20,
            description="CatBoost para mean reversion",
        ),
        ModelSpec(
            model_type=ModelType.GAUSSIAN_MIXTURE,
            strategy_type=StrategyType.RANGE_TRADING,
            target_type=TargetType.BINARY,
            hyperparams={
                "n_components": 5,
                "covariance_type": "full",
            },
            weight=0.10,
            description="Gaussian Mixture para clustering de mercado",
        ),
    ],
    meta_model_type=ModelType.LIGHTGBM,
    meta_model_params={
        "n_estimators": 150,
        "learning_rate": 0.05,
        "num_leaves": 31,
    },
    signal_threshold=0.60,
    min_expected_return=0.0005,
)


ASSET_MODEL_REGISTRY: dict[AssetClass, AssetModelConfig] = {
    AssetClass.CRYPTO: CRYPTO_MODEL_CONFIG,
    AssetClass.FOREX: FOREX_MODEL_CONFIG,
    AssetClass.INDICES: INDICES_MODEL_CONFIG,
    AssetClass.COMMODITIES: COMMODITIES_MODEL_CONFIG,
}


def get_asset_model_config(asset_class: AssetClass | str) -> AssetModelConfig:
    """
    Obtiene la configuración de modelos para una clase de activo.

    Args:
        asset_class: Clase de activo (crypto, forex, indices, commodities)

    Returns:
        AssetModelConfig: Configuración de modelos específica

    Raises:
        ValueError: Si la clase de activo no está soportada
    """
    if isinstance(asset_class, str):
        asset_class = AssetClass(asset_class.lower())

    if asset_class not in ASSET_MODEL_REGISTRY:
        raise ValueError(f"Asset class '{asset_class}' not supported")

    return ASSET_MODEL_REGISTRY[asset_class]


def get_model_config_for_symbol(symbol: str) -> AssetModelConfig:
    """
    Determina la configuración de modelos basada en el símbolo.

    Args:
        symbol: Símbolo del activo (ej: BTCUSD, EURUSD, XAUUSD)

    Returns:
        AssetModelConfig: Configuración apropiada para el símbolo
    """
    symbol_upper = symbol.upper()

    # Crypto
    if symbol_upper.endswith(("USDT", "USDC", "BUSD", "BTC", "ETH", "BNB")) or \
       symbol_upper in ("BTCUSD", "ETHUSD"):
        return ASSET_MODEL_REGISTRY[AssetClass.CRYPTO]

    # Commodities (Oro, Plata, etc.)
    if symbol_upper.startswith(("XAU", "XAG", "XPT", "XPD")):
        return ASSET_MODEL_REGISTRY[AssetClass.COMMODITIES]

    # Indices
    if symbol_upper in (
        "US500", "US30", "UK100", "DE40", "JP225",
        "NAS100", "SPX500", "AUS200", "HK50", "FR40"
    ):
        return ASSET_MODEL_REGISTRY[AssetClass.INDICES]

    # Forex (default)
    return ASSET_MODEL_REGISTRY[AssetClass.FOREX]
