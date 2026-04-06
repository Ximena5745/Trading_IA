"""
Module: core/models/asset_specific_models.py
Responsibility: Asset-specific model configurations and specialized architectures
Dependencies: pydantic, enum, typing

Este módulo define las configuraciones específicas de modelos por tipo de activo
según las propuestas de mejora:
- CRYPTO: Alta volatilidad, momentum fuerte
- FOREX: Mean reversion + sesiones temporales
- INDICES: Tendencias limpias
- COMMODITIES (GOLD): Macro-driven
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums y Tipos Base
# ---------------------------------------------------------------------------

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


class StrategyType(str, Enum):
    """Tipos de estrategias por modelo."""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY_BREAKOUT = "volatility_breakout"
    MOMENTUM = "momentum"
    RANGE_TRADING = "range_trading"
    MACRO_DRIVEN = "macro_driven"


# ---------------------------------------------------------------------------
# Configuración de Features por Activo
# ---------------------------------------------------------------------------

@dataclass
class FeatureConfig:
    """Configuración de features específica por activo."""
    
    # Features técnicas base
    technical_indicators: list[str] = field(default_factory=list)
    
    # Features de tiempo (críticas para Forex)
    time_features: list[str] = field(default_factory=list)
    
    # Features de mercado/estructura
    market_structure: list[str] = field(default_factory=list)
    
    # Features de volatilidad
    volatility_features: list[str] = field(default_factory=list)
    
    # Features de retornos
    return_features: list[str] = field(default_factory=list)
    
    # Features de microestructura
    microstructure: list[str] = field(default_factory=list)
    
    # Features macro (para commodities)
    macro_features: list[str] = field(default_factory=list)
    
    # Features específicas del activo
    asset_specific: list[str] = field(default_factory=list)
    
    @property
    def all_features(self) -> list[str]:
        """Retorna todas las features combinadas."""
        return (
            self.technical_indicators +
            self.time_features +
            self.market_structure +
            self.volatility_features +
            self.return_features +
            self.microstructure +
            self.macro_features +
            self.asset_specific
        )


# Configuraciones específicas por tipo de activo
CRYPTO_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_7", "rsi_21",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width", "bb_percent_b",
        "atr_14", "atr_21",
        "vwap", "vwap_std",
        "volume_sma_20", "volume_ratio", "obv", "volume_ema",
    ],
    time_features=[
        "hour", "day_of_week", "is_weekend",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "swing_high", "swing_low",
        "break_of_structure", "order_blocks",
    ],
    volatility_features=[
        "atr_percentile", "volatility_regime", "volatility_zscore",
        "bollinger_squeeze", "keltner_width",
    ],
    return_features=[
        "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
        "ret_1_vol_adj", "ret_3_vol_adj",
    ],
    microstructure=[
        "bid_ask_spread", "order_book_imbalance", "volume_delta",
        "liquidity_gaps", "bid_ask_pressure", "trade_flow_imbalance",
    ],
    asset_specific=[
        "btc_dominance", "eth_btc_ratio", "funding_rate",
        "open_interest", "liquidations", "exchange_inflows",
    ],
)

FOREX_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_7",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width",
        "atr_14", "atr_7",
        "vwap", "vwap_daily",
        "pivot_points", "pivot_support", "pivot_resistance",
    ],
    time_features=[
        "hour", "minute",
        "is_london_session", "is_ny_session", "is_asian_session",
        "session_overlap", "day_of_week", "is_nfp_day",
        "is_fomc_week", "month", "quarter_end",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "swing_points",
        "support_level", "resistance_level", "break_of_structure",
    ],
    volatility_features=[
        "atr_percentile", "volatility_regime", "session_volatility",
        "daily_range", "range_percentile",
    ],
    return_features=[
        "ret_1", "ret_4", "ret_8", "ret_12", "ret_24",
        "session_return", "overnight_return",
    ],
    microstructure=[
        "bid_ask_spread", "spread_percentile", "tick_volume",
    ],
    macro_features=[
        "dxy_index", "vix_index", "yield_spread_10y_2y",
    ],
)

INDICES_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_21",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "sma_50", "sma_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width",
        "atr_14", "atr_21",
        "adx", "adx_plus_di", "adx_minus_di",
        "vwap", "vwap_monthly",
    ],
    time_features=[
        "hour", "day_of_week", "is_month_start", "is_month_end",
        "quarter", "days_to_expiry", "is_opm_week",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "trend_strength",
        "ema_cross_9_21", "ema_cross_50_200", "golden_cross", "death_cross",
    ],
    volatility_features=[
        "atr_percentile", "vix_level", "vix_regime",
        "volatility_contraction", "volatility_expansion",
    ],
    return_features=[
        "ret_1", "ret_3", "ret_6", "ret_12", "ret_24", "ret_48",
        "gap", "gap_filled",
    ],
    macro_features=[
        "vix_index", "dxy_index", "ten_year_yield",
        "credit_spread", "advance_decline_line",
    ],
)

COMMODITIES_FEATURES = FeatureConfig(
    technical_indicators=[
        "rsi_14", "rsi_21", "rsi_50",
        "ema_9", "ema_21", "ema_50", "ema_200",
        "macd_line", "macd_signal", "macd_histogram",
        "bb_upper", "bb_lower", "bb_width", "bb_squeeze",
        "atr_14", "atr_21", "atr_50",
        "vwap", "vwap_weekly",
    ],
    time_features=[
        "hour", "day_of_week", "month", "season",
    ],
    market_structure=[
        "higher_highs", "lower_lows", "break_of_structure",
        "key_levels", "support_zones", "resistance_zones",
    ],
    volatility_features=[
        "atr_percentile", "volatility_regime", "volatility_breakout",
        "bollinger_bandwidth", "keltner_channels",
    ],
    return_features=[
        "ret_1", "ret_3", "ret_6", "ret_12", "ret_24",
        "intraday_range", "range_expansion",
    ],
    macro_features=[
        "dxy_index", "real_yield", "inflation_expectations",
        "gold_futures_oi", "etf_flows", "central_bank_activity",
        "geopolitical_risk_index",
    ],
    asset_specific=[
        "gold_silver_ratio", "gold_dxy_correlation",
    ],
)


# ---------------------------------------------------------------------------
# Configuración de Modelos por Activo
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Configuraciones Específicas por Activo
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Registro de Configuraciones
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Modelos Pydantic para Serialización
# ---------------------------------------------------------------------------

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


# Exportar configuraciones
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
