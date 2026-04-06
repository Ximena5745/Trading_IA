"""
Script: scripts/train_asset_specific_models.py
Responsibility: Training pipeline for asset-specific multi-model architecture

Este script entrena modelos especializados por tipo de activo:
- CRYPTO: LightGBM, LSTM, Temporal Fusion Transformer, CatBoost
- FOREX: LightGBM, HMM, Logistic Regression, SVM
- INDICES: LightGBM, XGBoost, Random Forest, RL (placeholder)
- COMMODITIES: LightGBM, HMM, CatBoost, Gaussian Mixture

Uso:
    python scripts/train_asset_specific_models.py --asset-class crypto --symbol BTCUSD
    python scripts/train_asset_specific_models.py --asset-class forex --symbol EURUSD
    python scripts/train_asset_specific_models.py --asset-class indices --symbol US500
    python scripts/train_asset_specific_models.py --asset-class commodities --symbol XAUUSD
"""
from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit

# Asegurar que el path del proyecto esté disponible
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.models.asset_specific_models import (
    AssetClass,
    AssetModelConfig,
    AssetSpecificTrainingConfig,
    FeatureConfig,
    ModelSpec,
    ModelType,
    StrategyType,
    TargetType,
    get_asset_model_config,
)
from core.observability.logger import get_logger

logger = get_logger(__name__)


class AssetSpecificTrainer:
    """Entrenador de modelos específicos por activo."""
    
    def __init__(
        self,
        config: AssetSpecificTrainingConfig,
        output_path: str = "data/models/asset_specific",
    ):
        self.config = config
        self.output_path = Path(output_path)
        self.output_path.mkdir(parents=True, exist_ok=True)
        
        # Cargar configuración del activo
        self.asset_config = get_asset_model_config(config.asset_class)
        
        # Datos de entrenamiento
        self.X_train: Optional[np.ndarray] = None
        self.X_val: Optional[np.ndarray] = None
        self.X_test: Optional[np.ndarray] = None
        self.y_train: Optional[np.ndarray] = None
        self.y_val: Optional[np.ndarray] = None
        self.y_test: Optional[np.ndarray] = None
        
        # Métricas
        self.training_metrics: dict[str, Any] = {}
        
    def load_data(self, data_path: Optional[str] = None) -> bool:
        """Carga y prepara los datos de entrenamiento."""
        try:
            # Intentar cargar desde archivo parquet
            if data_path is None:
                data_path = f"data/raw/{self.config.symbol}_{self.config.timeframe}.parquet"
            
            data_file = Path(data_path)
            if not data_file.exists():
                logger.error("data_file_not_found", path=str(data_file))
                return False
            
            # Cargar datos
            df = pd.read_parquet(data_file)
            logger.info("data_loaded", rows=len(df), columns=len(df.columns))
            
            # Preparar features y target
            self._prepare_features(df)
            
            return True
            
        except Exception as e:
            logger.error("data_loading_failed", error=str(e))
            return False
    
    def _prepare_features(self, df: pd.DataFrame) -> None:
        """Prepara las features según la configuración del activo."""
        feature_config = self.asset_config.feature_config
        
        # Calcular features técnicas
        df = self._calculate_technical_features(df, feature_config)
        
        # Calcular features de tiempo
        df = self._calculate_time_features(df, feature_config)
        
        # Calcular features de mercado
        df = self._calculate_market_structure_features(df, feature_config)
        
        # Calcular features de volatilidad
        df = self._calculate_volatility_features(df, feature_config)
        
        # Calcular features de retornos
        df = self._calculate_return_features(df, feature_config)
        
        # Calcular target
        df = self._calculate_target(df)
        
        # Eliminar NaN
        df = df.dropna()
        
        # Separar X e y
        all_features = feature_config.all_features
        available_features = [f for f in all_features if f in df.columns]
        
        X = df[available_features].values
        y = df['target'].values
        
        # Split temporal
        n = len(X)
        test_size = int(n * self.config.test_size)
        val_size = int(n * self.config.validation_size)
        train_size = n - test_size - val_size
        
        self.X_train = X[:train_size]
        self.X_val = X[train_size:train_size + val_size]
        self.X_test = X[train_size + val_size:]
        
        self.y_train = y[:train_size]
        self.y_val = y[train_size:train_size + val_size]
        self.y_test = y[train_size + val_size:]
        
        logger.info(
            "features_prepared",
            n_features=len(available_features),
            train_size=len(self.X_train),
            val_size=len(self.X_val),
            test_size=len(self.X_test),
        )
        
        # Guardar nombres de features
        self.feature_names = available_features
    
    def _calculate_technical_features(self, df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
        """Calcula indicadores técnicos."""
        # RSI
        if 'rsi_14' in config.technical_indicators:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi_14'] = 100 - (100 / (1 + rs))
        
        if 'rsi_7' in config.technical_indicators:
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=7).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=7).mean()
            rs = gain / loss
            df['rsi_7'] = 100 - (100 / (1 + rs))
        
        # EMAs
        for period in [9, 21, 50, 200]:
            col = f'ema_{period}'
            if col in config.technical_indicators:
                df[col] = df['close'].ewm(span=period, adjust=False).mean()
        
        # MACD
        if any(c in config.technical_indicators for c in ['macd_line', 'macd_signal', 'macd_histogram']):
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd_line'] = ema_12 - ema_26
            df['macd_signal'] = df['macd_line'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd_line'] - df['macd_signal']
        
        # Bollinger Bands
        if any(c in config.technical_indicators for c in ['bb_upper', 'bb_lower', 'bb_width']):
            sma_20 = df['close'].rolling(window=20).mean()
            std_20 = df['close'].rolling(window=20).std()
            df['bb_upper'] = sma_20 + (std_20 * 2)
            df['bb_lower'] = sma_20 - (std_20 * 2)
            df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / sma_20
        
        # ATR
        if 'atr_14' in config.technical_indicators:
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift())
            low_close = np.abs(df['low'] - df['close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = np.max(ranges, axis=1)
            df['atr_14'] = true_range.rolling(14).mean()
        
        # VWAP
        if 'vwap' in config.technical_indicators:
            typical_price = (df['high'] + df['low'] + df['close']) / 3
            df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        # Volume features
        if 'volume_sma_20' in config.technical_indicators:
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
        if 'volume_ratio' in config.technical_indicators:
            df['volume_sma_20'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        return df
    
    def _calculate_time_features(self, df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
        """Calcula features temporales."""
        if 'hour' in config.time_features:
            df['hour'] = pd.to_datetime(df.index).hour if isinstance(df.index, pd.DatetimeIndex) else 0
        
        if 'day_of_week' in config.time_features:
            df['day_of_week'] = pd.to_datetime(df.index).dayofweek if isinstance(df.index, pd.DatetimeIndex) else 0
        
        # Sesiones de Forex
        if 'is_london_session' in config.time_features:
            df['is_london_session'] = ((df['hour'] >= 8) & (df['hour'] <= 16)).astype(int)
        
        if 'is_ny_session' in config.time_features:
            df['is_ny_session'] = ((df['hour'] >= 13) & (df['hour'] <= 21)).astype(int)
        
        if 'is_asian_session' in config.time_features:
            df['is_asian_session'] = ((df['hour'] >= 0) & (df['hour'] <= 8)).astype(int)
        
        return df
    
    def _calculate_market_structure_features(self, df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
        """Calcula features de estructura de mercado."""
        # Higher highs / Lower lows
        if 'higher_highs' in config.market_structure:
            df['higher_highs'] = (df['high'] > df['high'].shift(1).rolling(5).max()).astype(int)
        
        if 'lower_lows' in config.market_structure:
            df['lower_lows'] = (df['low'] < df['low'].shift(1).rolling(5).min()).astype(int)
        
        # Trend direction
        if 'trend_direction' in config.market_structure:
            df['ema_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['trend_direction'] = np.where(df['close'] > df['ema_50'], 'bullish', 'bearish')
        
        return df
    
    def _calculate_volatility_features(self, df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
        """Calcula features de volatilidad."""
        if 'atr_percentile' in config.volatility_features and 'atr_14' in df.columns:
            df['atr_percentile'] = df['atr_14'].rolling(100).apply(
                lambda x: pd.Series(x).rank(pct=True).iloc[-1]
            )
        
        if 'volatility_regime' in config.volatility_features and 'atr_14' in df.columns:
            atr_mean = df['atr_14'].rolling(50).mean()
            atr_std = df['atr_14'].rolling(50).std()
            df['volatility_regime'] = pd.cut(
                (df['atr_14'] - atr_mean) / atr_std,
                bins=[-np.inf, -1, 1, np.inf],
                labels=['low', 'medium', 'high']
            )
        
        return df
    
    def _calculate_return_features(self, df: pd.DataFrame, config: FeatureConfig) -> pd.DataFrame:
        """Calcula features de retornos."""
        # Retornos a diferentes horizontes
        for period in [1, 3, 6, 12, 24]:
            col = f'ret_{period}'
            if col in config.return_features:
                df[col] = df['close'].pct_change(period)
        
        return df
    
    def _calculate_target(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula el target según el tipo especificado."""
        # Calcular retorno futuro
        future_return = df['close'].shift(-1) / df['close'] - 1
        
        if self.config.target_type == TargetType.TERNARY:
            # 3 clases: -1 (venta), 0 (neutro), 1 (compra)
            threshold = 0.001  # 0.1%
            df['target'] = np.where(
                future_return > threshold, 2,
                np.where(future_return < -threshold, 0, 1)
            )
        elif self.config.target_type == TargetType.BINARY:
            # 2 clases: 0 (venta), 1 (compra)
            df['target'] = (future_return > 0).astype(int)
        elif self.config.target_type == TargetType.REGRESSION:
            # Retorno continuo
            df['target'] = future_return
        else:
            df['target'] = (future_return > 0).astype(int)
        
        return df
    
    def train_all_models(self) -> dict[str, Any]:
        """Entrena todos los modelos para el activo."""
        results = {}
        
        for spec in self.asset_config.models:
            if spec.model_type not in self.config.models_to_train:
                logger.info("skipping_model", model_type=spec.model_type.value)
                continue
            
            logger.info(
                "training_model",
                model_type=spec.model_type.value,
                strategy=spec.strategy_type.value,
            )
            
            try:
                model_result = self._train_single_model(spec)
                results[f"{spec.strategy_type.value}_{spec.model_type.value}"] = model_result
            except Exception as e:
                logger.error(
                    "model_training_failed",
                    model_type=spec.model_type.value,
                    error=str(e),
                )
        
        # Entrenar meta-modelo si está habilitado
        if self.config.train_meta_model and results:
            self._train_meta_model(results)
        
        # Guardar métricas
        self._save_metrics(results)
        
        return results
    
    def _train_single_model(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo individual."""
        model_type = spec.model_type
        
        if model_type == ModelType.LIGHTGBM:
            return self._train_lightgbm(spec)
        elif model_type == ModelType.XGBOOST:
            return self._train_xgboost(spec)
        elif model_type == ModelType.CATBOOST:
            return self._train_catboost(spec)
        elif model_type == ModelType.RANDOM_FOREST:
            return self._train_random_forest(spec)
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            return self._train_logistic_regression(spec)
        elif model_type == ModelType.SVM:
            return self._train_svm(spec)
        elif model_type == ModelType.HMM:
            return self._train_hmm(spec)
        elif model_type == ModelType.GAUSSIAN_MIXTURE:
            return self._train_gaussian_mixture(spec)
        else:
            raise ValueError(f"Model type {model_type} not implemented")
    
    def _train_lightgbm(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo LightGBM."""
        try:
            import lightgbm as lgb
            
            # Determinar tipo de objetivo
            if self.config.target_type == TargetType.TERNARY:
                objective = 'multiclass'
                num_class = 3
            elif self.config.target_type == TargetType.BINARY:
                objective = 'binary'
                num_class = None
            else:
                objective = 'regression'
                num_class = None
            
            model = lgb.LGBMClassifier(
                objective=objective,
                num_class=num_class,
                **spec.hyperparams
            ) if objective != 'regression' else lgb.LGBMRegressor(
                objective=objective,
                **spec.hyperparams
            )
            
            # Entrenar
            if self.config.use_cross_validation:
                scores = self._cross_validate(model, self.X_train, self.y_train)
                logger.info("lightgbm_cv_scores", mean=scores.mean(), std=scores.std())
            
            model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_val, self.y_val)] if self.X_val is not None else None,
                callbacks=[lgb.early_stopping(self.config.early_stopping_rounds)] 
                if self.X_val is not None else None,
            )
            
            # Evaluar
            train_score = model.score(self.X_train, self.y_train)
            val_score = model.score(self.X_val, self.y_val) if self.X_val is not None else None
            test_score = model.score(self.X_test, self.y_test) if self.X_test is not None else None
            
            # Guardar modelo
            model_path = self._save_model(model, spec)
            
            return {
                "model_type": "lightgbm",
                "train_score": train_score,
                "val_score": val_score,
                "test_score": test_score,
                "model_path": model_path,
            }
            
        except ImportError:
            logger.error("lightgbm_not_installed")
            raise
    
    def _train_xgboost(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo XGBoost."""
        try:
            import xgboost as xgb
            
            model = xgb.XGBClassifier(
                **spec.hyperparams
            ) if self.config.target_type != TargetType.REGRESSION else xgb.XGBRegressor(
                **spec.hyperparams
            )
            
            model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_val, self.y_val)] if self.X_val is not None else None,
                early_stopping_rounds=self.config.early_stopping_rounds,
                verbose=False,
            )
            
            train_score = model.score(self.X_train, self.y_train)
            val_score = model.score(self.X_val, self.y_val) if self.X_val is not None else None
            
            model_path = self._save_model(model, spec)
            
            return {
                "model_type": "xgboost",
                "train_score": train_score,
                "val_score": val_score,
                "model_path": model_path,
            }
            
        except ImportError:
            logger.error("xgboost_not_installed")
            raise
    
    def _train_catboost(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo CatBoost."""
        try:
            from catboost import CatBoostClassifier, CatBoostRegressor
            
            model = CatBoostClassifier(
                **spec.hyperparams,
                verbose=False,
            ) if self.config.target_type != TargetType.REGRESSION else CatBoostRegressor(
                **spec.hyperparams,
                verbose=False,
            )
            
            model.fit(
                self.X_train, self.y_train,
                eval_set=(self.X_val, self.y_val) if self.X_val is not None else None,
                early_stopping_rounds=self.config.early_stopping_rounds,
            )
            
            train_score = model.score(self.X_train, self.y_train)
            val_score = model.score(self.X_val, self.y_val) if self.X_val is not None else None
            
            model_path = self._save_model(model, spec)
            
            return {
                "model_type": "catboost",
                "train_score": train_score,
                "val_score": val_score,
                "model_path": model_path,
            }
            
        except ImportError:
            logger.error("catboost_not_installed")
            raise
    
    def _train_random_forest(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo Random Forest."""
        from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
        
        model = RandomForestClassifier(
            **spec.hyperparams,
            random_state=42,
        ) if self.config.target_type != TargetType.REGRESSION else RandomForestRegressor(
            **spec.hyperparams,
            random_state=42,
        )
        
        model.fit(self.X_train, self.y_train)
        
        train_score = model.score(self.X_train, self.y_train)
        val_score = model.score(self.X_val, self.y_val) if self.X_val is not None else None
        
        model_path = self._save_model(model, spec)
        
        return {
            "model_type": "random_forest",
            "train_score": train_score,
            "val_score": val_score,
            "model_path": model_path,
        }
    
    def _train_logistic_regression(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo de Regresión Logística."""
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', LogisticRegression(**spec.hyperparams)),
        ])
        
        model.fit(self.X_train, self.y_train)
        
        train_score = model.score(self.X_train, self.y_train)
        val_score = model.score(self.X_val, self.y_val) if self.X_val is not None else None
        
        model_path = self._save_model(model, spec)
        
        return {
            "model_type": "logistic_regression",
            "train_score": train_score,
            "val_score": val_score,
            "model_path": model_path,
        }
    
    def _train_svm(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo SVM."""
        from sklearn.svm import SVC
        from sklearn.preprocessing import StandardScaler
        from sklearn.pipeline import Pipeline
        
        model = Pipeline([
            ('scaler', StandardScaler()),
            ('classifier', SVC(**spec.hyperparams)),
        ])
        
        model.fit(self.X_train, self.y_train)
        
        train_score = model.score(self.X_train, self.y_train)
        val_score = model.score(self.X_val, self.y_val) if self.X_val is not None else None
        
        model_path = self._save_model(model, spec)
        
        return {
            "model_type": "svm",
            "train_score": train_score,
            "val_score": val_score,
            "model_path": model_path,
        }
    
    def _train_hmm(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo HMM."""
        try:
            from hmmlearn.hmm import GaussianHMM
            
            # HMM trabaja con features continuas
            model = GaussianHMM(
                **spec.hyperparams,
                random_state=42,
            )
            
            # Usar retornos como observaciones
            returns = self.X_train[:, 0].reshape(-1, 1)  # Usar primera feature
            model.fit(returns)
            
            model_path = self._save_model(model, spec)
            
            return {
                "model_type": "hmm",
                "n_components": spec.hyperparams.get('n_components', 5),
                "model_path": model_path,
            }
            
        except ImportError:
            logger.error("hmmlearn_not_installed")
            raise
    
    def _train_gaussian_mixture(self, spec: ModelSpec) -> dict[str, Any]:
        """Entrena un modelo Gaussian Mixture."""
        from sklearn.mixture import GaussianMixture
        
        model = GaussianMixture(
            **spec.hyperparams,
            random_state=42,
        )
        
        model.fit(self.X_train)
        
        model_path = self._save_model(model, spec)
        
        return {
            "model_type": "gaussian_mixture",
            "n_components": spec.hyperparams.get('n_components', 5),
            "model_path": model_path,
        }
    
    def _cross_validate(self, model, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Realiza validación cruzada temporal."""
        tscv = TimeSeriesSplit(n_splits=self.config.n_folds)
        scores = []
        
        for train_idx, val_idx in tscv.split(X):
            X_train_cv, X_val_cv = X[train_idx], X[val_idx]
            y_train_cv, y_val_cv = y[train_idx], y[val_idx]
            
            model.fit(X_train_cv, y_train_cv)
            scores.append(model.score(X_val_cv, y_val_cv))
        
        return np.array(scores)
    
    def _save_model(self, model: Any, spec: ModelSpec) -> str:
        """Guarda el modelo entrenado."""
        filename = f"{self.config.asset_class.value}_{spec.strategy_type.value}_{spec.model_type.value}.pkl"
        model_path = self.output_path / filename
        
        payload = {
            "model": model,
            "feature_names": self.feature_names,
            "hyperparams": spec.hyperparams,
            "asset_class": self.config.asset_class.value,
            "symbol": self.config.symbol,
            "trained_at": datetime.utcnow().isoformat(),
        }
        
        with open(model_path, "wb") as f:
            pickle.dump(payload, f)
        
        logger.info("model_saved", path=str(model_path))
        return str(model_path)
    
    def _train_meta_model(self, individual_results: dict[str, Any]) -> None:
        """Entrena el meta-modelo de stacking."""
        logger.info("training_meta_model")
        
        # Preparar datos de meta-features
        meta_features = []
        meta_labels = []
        
        # Para cada muestra de validación, obtener predicciones de todos los modelos
        for i in range(len(self.X_val)):
            sample_features = self.X_val[i:i+1]
            sample_label = self.y_val[i]
            
            model_predictions = []
            for key, result in individual_results.items():
                if 'model_path' in result:
                    # Cargar modelo y predecir
                    with open(result['model_path'], 'rb') as f:
                        payload = pickle.load(f)
                        model = payload['model']
                        try:
                            proba = model.predict_proba(sample_features)[0]
                            model_predictions.extend(proba)
                        except:
                            pred = model.predict(sample_features)[0]
                            model_predictions.append(pred)
            
            if model_predictions:
                meta_features.append(model_predictions)
                meta_labels.append(sample_label)
        
        if not meta_features:
            logger.warning("no_meta_features_available")
            return
        
        meta_X = np.array(meta_features)
        meta_y = np.array(meta_labels)
        
        # Entrenar meta-modelo
        if self.config.meta_model_type == ModelType.LIGHTGBM:
            import lightgbm as lgb
            meta_model = lgb.LGBMClassifier(**self.config.meta_model_params)
        elif self.config.meta_model_type == ModelType.LOGISTIC_REGRESSION:
            from sklearn.linear_model import LogisticRegression
            meta_model = LogisticRegression(**self.config.meta_model_params)
        elif self.config.meta_model_type == ModelType.XGBOOST:
            import xgboost as xgb
            meta_model = xgb.XGBClassifier(**self.config.meta_model_params)
        else:
            from sklearn.linear_model import LogisticRegression
            meta_model = LogisticRegression()
        
        meta_model.fit(meta_X, meta_y)
        
        # Guardar meta-modelo
        meta_filename = f"{self.config.asset_class.value}_meta_model.pkl"
        meta_path = self.output_path / meta_filename
        
        with open(meta_path, "wb") as f:
            pickle.dump({
                "model": meta_model,
                "individual_models": list(individual_results.keys()),
                "trained_at": datetime.utcnow().isoformat(),
            }, f)
        
        logger.info("meta_model_saved", path=str(meta_path))
    
    def _save_metrics(self, results: dict[str, Any]) -> None:
        """Guarda las métricas de entrenamiento."""
        metrics_path = self.output_path / f"{self.config.asset_class.value}_training_metrics.json"
        
        metrics = {
            "asset_class": self.config.asset_class.value,
            "symbol": self.config.symbol,
            "timeframe": self.config.timeframe,
            "trained_at": datetime.utcnow().isoformat(),
            "target_type": self.config.target_type.value,
            "n_features": len(self.feature_names) if hasattr(self, 'feature_names') else 0,
            "train_size": len(self.X_train) if self.X_train is not None else 0,
            "val_size": len(self.X_val) if self.X_val is not None else 0,
            "test_size": len(self.X_test) if self.X_test is not None else 0,
            "models": results,
        }
        
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2, default=str)
        
        logger.info("metrics_saved", path=str(metrics_path))


def main():
    """Función principal del script."""
    parser = argparse.ArgumentParser(
        description="Train asset-specific multi-model architecture"
    )
    parser.add_argument(
        "--asset-class",
        type=str,
        required=True,
        choices=["crypto", "forex", "indices", "commodities"],
        help="Asset class to train models for",
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="Symbol to train (e.g., BTCUSD, EURUSD, XAUUSD)",
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1h",
        help="Timeframe for training (default: 1h)",
    )
    parser.add_argument(
        "--data-path",
        type=str,
        default=None,
        help="Path to training data (optional)",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        default="data/models/asset_specific",
        help="Output path for trained models",
    )
    parser.add_argument(
        "--target-type",
        type=str,
        default="ternary",
        choices=["binary", "ternary", "regression"],
        help="Target type for training",
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=None,
        help="Specific models to train (default: all)",
    )
    
    args = parser.parse_args()
    
    # Crear configuración de entrenamiento
    asset_class = AssetClass(args.asset_class)
    
    # Determinar qué modelos entrenar
    asset_config = get_asset_model_config(asset_class)
    available_models = [spec.model_type for spec in asset_config.models]
    
    if args.models:
        models_to_train = [ModelType(m) for m in args.models]
    else:
        models_to_train = available_models
    
    config = AssetSpecificTrainingConfig(
        asset_class=asset_class,
        symbol=args.symbol,
        timeframe=args.timeframe,
        models_to_train=models_to_train,
        target_type=TargetType(args.target_type),
    )
    
    # Crear entrenador
    trainer = AssetSpecificTrainer(config, output_path=args.output_path)
    
    # Cargar datos
    if not trainer.load_data(args.data_path):
        logger.error("failed_to_load_data")
        sys.exit(1)
    
    # Entrenar modelos
    results = trainer.train_all_models()
    
    # Resumen
    print("\n" + "=" * 60)
    print(f"TRAINING COMPLETE: {args.asset_class.upper()} - {args.symbol}")
    print("=" * 60)
    print(f"\nModels trained: {len(results)}")
    for key, result in results.items():
        print(f"\n{key}:")
        print(f"  - Train score: {result.get('train_score', 'N/A')}")
        print(f"  - Val score: {result.get('val_score', 'N/A')}")
        print(f"  - Model path: {result.get('model_path', 'N/A')}")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
