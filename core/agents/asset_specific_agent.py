"""
Module: core/agents/asset_specific_agent.py
Responsibility: Asset-specific multi-model agent with ensemble architecture
Dependencies: lightgbm, xgboost, catboost, sklearn, base_agent, models

Este agente implementa la arquitectura multi-modelo específica por activo:
- Selecciona modelos según el tipo de activo (CRYPTO, FOREX, INDICES, COMMODITIES)
- Ejecuta múltiples modelos especializados (trend, mean reversion, volatility)
- Usa un meta-modelo (stacking) para la decisión final
- Aplica filtros de decisión basados en umbral, retorno esperado y riesgo
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from typing import Any, Optional

import numpy as np

from core.agents.base_agent import AbcAgent
from core.exceptions import AgentPredictionError
from core.models import AgentOutput, FeatureSet
from core.models.asset_specific_models import (
    AssetClass,
    AssetModelConfig,
    EnsemblePrediction,
    ModelPrediction,
    ModelSpec,
    ModelType,
    StrategyType,
    get_model_config_for_symbol,
)
from core.observability.logger import get_logger

logger = get_logger(__name__)


class AssetSpecificModel:
    """Wrapper para un modelo individual especializado."""
    
    def __init__(self, spec: ModelSpec, asset_class: AssetClass):
        self.spec = spec
        self.asset_class = asset_class
        self.model: Optional[Any] = None
        self.is_trained = False
        self.feature_names: list[str] = []
        
    def load(self, model_path: str) -> bool:
        """Carga el modelo desde disco."""
        try:
            if os.path.exists(model_path):
                with open(model_path, "rb") as f:
                    payload = pickle.load(f)
                    self.model = payload.get("model")
                    self.feature_names = payload.get("feature_names", [])
                    self.is_trained = True
                return True
        except Exception as e:
            logger.warning(
                "model_load_failed",
                model_type=self.spec.model_type.value,
                error=str(e)
            )
        return False
    
    def predict(self, features: FeatureSet, feature_vector: np.ndarray) -> Optional[ModelPrediction]:
        """Realiza predicción con el modelo."""
        if self.model is None:
            return None
            
        try:
            # Obtener probabilidades
            if hasattr(self.model, 'predict_proba'):
                proba = self.model.predict_proba(feature_vector)[0]
            else:
                # Para modelos sin predict_proba (ej. SVM sin probability)
                pred = self.model.predict(feature_vector)[0]
                proba = self._create_probability_distribution(pred)
            
            # Calcular dirección y score según tipo de target
            direction, score, confidence = self._calculate_output(proba)
            
            # Calcular SHAP si está disponible
            shap_values = self._compute_shap(feature_vector)
            
            return ModelPrediction(
                model_type=self.spec.model_type.value,
                strategy_type=self.spec.strategy_type.value,
                direction=direction,
                score=round(score, 4),
                confidence=round(confidence, 4),
                probability=self._format_probabilities(proba),
                features_used=self.feature_names or [],
                shap_values=shap_values,
            )
        except Exception as e:
            logger.error(
                "model_prediction_failed",
                model_type=self.spec.model_type.value,
                error=str(e)
            )
            return None
    
    def _calculate_output(self, proba: np.ndarray) -> tuple[str, float, float]:
        """Calcula dirección, score y confianza según el tipo de target."""
        if self.spec.target_type.value == "ternary":
            # 3 clases: 0=SELL, 1=HOLD, 2=BUY
            if len(proba) == 3:
                direction_map = {0: 'SELL', 1: 'NEUTRAL', 2: 'BUY'}
                direction = direction_map[np.argmax(proba)]
                confidence = float(np.max(proba))
                score = float(proba[2] - proba[0])  # BUY - SELL
            else:
                # Fallback a binario
                direction = 'BUY' if proba[1] > 0.5 else 'SELL'
                confidence = float(max(proba))
                score = float(proba[1] - proba[0])
        elif self.spec.target_type.value == "regression":
            # Regresión: el valor es el retorno esperado
            score = float(proba[0]) if len(proba) == 1 else 0.0
            direction = 'BUY' if score > 0 else 'SELL' if score < 0 else 'NEUTRAL'
            confidence = min(abs(score) * 2, 1.0)
        else:
            # Binario: 0=SELL, 1=BUY
            direction = 'BUY' if proba[1] > proba[0] else 'SELL'
            confidence = float(max(proba))
            score = float(proba[1] - proba[0])
        
        return direction, score, confidence
    
    def _create_probability_distribution(self, pred: int | float) -> np.ndarray:
        """Crea distribución de probabilidad para modelos sin predict_proba."""
        if isinstance(pred, (int, np.integer)):
            proba = np.zeros(2)
            proba[pred] = 1.0
            return proba
        # Para regresión, crear distribución simple
        return np.array([pred])
    
    def _format_probabilities(self, proba: np.ndarray) -> dict[str, float]:
        """Formatea probabilidades para serialización."""
        if len(proba) == 3:
            return {"sell": round(proba[0], 4), "hold": round(proba[1], 4), "buy": round(proba[2], 4)}
        elif len(proba) == 2:
            return {"sell": round(proba[0], 4), "buy": round(proba[1], 4)}
        else:
            return {"value": round(float(proba[0]), 4)}
    
    def _compute_shap(self, feature_vector: np.ndarray) -> dict[str, float]:
        """Calcula valores SHAP si el explainer está disponible."""
        # TODO: Implementar SHAP para cada tipo de modelo
        return {}


class AssetSpecificAgent(AbcAgent):
    """
    Agente especializado por tipo de activo con arquitectura multi-modelo.
    
    Implementa:
    1. Selección automática de modelos según el activo
    2. Ejecución de múltiples modelos especializados
    3. Meta-modelo (stacking) para decisión final
    4. Filtros de decisión basados en umbral, retorno y riesgo
    """
    
    agent_id = "asset_specific_v1"
    model_version = "v1.0.0"
    
    def __init__(
        self,
        asset_class: Optional[AssetClass] = None,
        symbol: Optional[str] = None,
        model_base_path: str = "data/models/asset_specific",
    ):
        """
        Inicializa el agente específico por activo.
        
        Args:
            asset_class: Clase de activo (si es None, se detecta del símbolo)
            symbol: Símbolo del activo (ej: BTCUSD, EURUSD)
            model_base_path: Ruta base para los modelos entrenados
        """
        self._asset_class = asset_class
        self._symbol = symbol
        self._model_base_path = Path(model_base_path)
        
        # Configuración específica del activo
        self._config: Optional[AssetModelConfig] = None
        self._models: dict[str, AssetSpecificModel] = {}
        self._meta_model: Optional[Any] = None
        
        # Historial para cálculo de métricas
        self._prediction_history: list[EnsemblePrediction] = []
        
        self._load_configuration()
        self._load_models()
    
    def _load_configuration(self) -> None:
        """Carga la configuración específica para el activo."""
        if self._asset_class is not None:
            from core.models.asset_specific_models import get_asset_model_config
            self._config = get_asset_model_config(self._asset_class)
        elif self._symbol is not None:
            self._config = get_model_config_for_symbol(self._symbol)
        else:
            raise ValueError("Debe especificar asset_class o symbol")
        
        logger.info(
            "asset_config_loaded",
            asset_class=self._config.asset_class.value,
            n_models=len(self._config.models),
            meta_model=self._config.meta_model_type.value,
        )
    
    def _load_models(self) -> None:
        """Carga todos los modelos especializados."""
        if self._config is None:
            return
        
        for spec in self._config.models:
            model_wrapper = AssetSpecificModel(spec, self._config.asset_class)
            
            # Construir ruta del modelo
            model_filename = f"{self._config.asset_class.value}_{spec.strategy_type.value}_{spec.model_type.value}.pkl"
            model_path = str(self._model_base_path / model_filename)
            
            # Intentar cargar
            loaded = model_wrapper.load(model_path)
            
            model_key = f"{spec.strategy_type.value}_{spec.model_type.value}"
            self._models[model_key] = model_wrapper
            
            logger.info(
                "model_loaded" if loaded else "model_not_found",
                model_key=model_key,
                model_type=spec.model_type.value,
                strategy=spec.strategy_type.value,
            )
        
        # Cargar meta-modelo
        self._load_meta_model()
    
    def _load_meta_model(self) -> None:
        """Carga el meta-modelo de stacking."""
        if self._config is None:
            return
        
        meta_filename = f"{self._config.asset_class.value}_meta_model.pkl"
        meta_path = self._model_base_path / meta_filename
        
        try:
            if meta_path.exists():
                with open(meta_path, "rb") as f:
                    payload = pickle.load(f)
                    self._meta_model = payload.get("model")
                logger.info("meta_model_loaded", path=str(meta_path))
        except Exception as e:
            logger.warning("meta_model_load_failed", error=str(e))
    
    def is_ready(self) -> bool:
        """Verifica si al menos un modelo está listo."""
        return any(m.is_trained for m in self._models.values())
    
    def predict(self, features: FeatureSet) -> AgentOutput:
        """
        Realiza predicción usando el ensemble de modelos especializados.
        
        Args:
            features: FeatureSet con los datos de entrada
            
        Returns:
            AgentOutput con la decisión final del ensemble
        """
        try:
            # Obtener predicciones de todos los modelos
            predictions = self._get_individual_predictions(features)
            
            if not predictions:
                # Fallback si no hay modelos disponibles
                return self._fallback_prediction(features)
            
            # Calcular decisión del ensemble
            ensemble_result = self._compute_ensemble(predictions, features)
            
            # Aplicar filtros de decisión
            final_decision = self._apply_decision_filters(ensemble_result)
            
            # Crear output del agente
            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=features.timestamp,
                symbol=features.symbol,
                direction=final_decision.final_direction,
                score=round(final_decision.final_score, 4),
                confidence=round(final_decision.final_confidence, 4),
                features_used=self._get_all_feature_names(),
                shap_values=self._aggregate_shap_values(predictions),
                model_version=f"{self.model_version}_{self._config.asset_class.value}",
            )
        except Exception as e:
            raise AgentPredictionError(f"AssetSpecificAgent prediction failed: {e}") from e
    
    def _get_individual_predictions(self, features: FeatureSet) -> list[ModelPrediction]:
        """Obtiene predicciones de todos los modelos individuales."""
        predictions = []
        
        for model_key, model_wrapper in self._models.items():
            if not model_wrapper.is_trained:
                continue
            
            # Preparar vector de features
            feature_vector = self._prepare_features(features, model_wrapper.spec)
            
            # Realizar predicción
            pred = model_wrapper.predict(features, feature_vector)
            if pred is not None:
                predictions.append(pred)
        
        return predictions
    
    def _prepare_features(self, features: FeatureSet, spec: ModelSpec) -> np.ndarray:
        """Prepara el vector de features según la especificación del modelo."""
        # Extraer features según los nombres requeridos
        feature_values = []
        for feature_name in spec.features:
            value = getattr(features, feature_name, 0.0)
            feature_values.append(float(value) if value is not None else 0.0)
        
        return np.array([feature_values], dtype=np.float32)
    
    def _compute_ensemble(
        self,
        predictions: list[ModelPrediction],
        features: FeatureSet,
    ) -> EnsemblePrediction:
        """Calcula la predicción del ensemble usando stacking o promedio ponderado."""
        
        if not predictions:
            raise ValueError("No predictions available for ensemble")
        
        # Calcular pesos dinámicos si está habilitado
        weights = self._calculate_weights(predictions)
        
        # Calcular score ponderado
        weighted_score = sum(
            pred.score * weights.get(pred.strategy_type, 1.0)
            for pred in predictions
        ) / sum(weights.values()) if weights else 0.0
        
        # Calcular confianza ponderada
        weighted_confidence = sum(
            pred.confidence * weights.get(pred.strategy_type, 1.0)
            for pred in predictions
        ) / sum(weights.values()) if weights else 0.0
        
        # Determinar dirección final
        final_direction = self._score_to_direction(weighted_score)
        
        # Usar meta-modelo si está disponible
        meta_contribution = 0.0
        if self._meta_model is not None and self._config.use_stacking:
            try:
                # Preparar input para meta-modelo
                meta_input = self._prepare_meta_input(predictions)
                meta_pred = self._meta_model.predict_proba(meta_input)[0]
                meta_score = float(meta_pred[1] - meta_pred[0]) if len(meta_pred) == 2 else 0.0
                
                # Combinar con el promedio ponderado
                alpha = 0.7  # Peso del meta-modelo
                weighted_score = alpha * meta_score + (1 - alpha) * weighted_score
                final_direction = self._score_to_direction(weighted_score)
                meta_contribution = alpha
            except Exception as e:
                logger.warning("meta_model_prediction_failed", error=str(e))
        
        return EnsemblePrediction(
            asset_class=self._config.asset_class.value,
            symbol=features.symbol,
            timestamp=str(features.timestamp),
            final_direction=final_direction,
            final_score=round(weighted_score, 4),
            final_confidence=round(weighted_confidence, 4),
            individual_predictions=predictions,
            model_weights=weights,
            meta_model_contribution=meta_contribution,
        )
    
    def _calculate_weights(self, predictions: list[ModelPrediction]) -> dict[str, float]:
        """Calcula pesos dinámicos para cada modelo."""
        weights = {}
        
        for pred in predictions:
            # Buscar el peso configurado para este tipo de estrategia
            for spec in self._config.models:
                if spec.strategy_type.value == pred.strategy_type:
                    # Ajustar peso basado en confianza
                    confidence_factor = pred.confidence if self._config.use_dynamic_weights else 1.0
                    weights[pred.strategy_type] = spec.weight * confidence_factor
                    break
        
        return weights
    
    def _prepare_meta_input(self, predictions: list[ModelPrediction]) -> np.ndarray:
        """Prepara el input para el meta-modelo."""
        # Crear vector con scores y confianzas de cada modelo
        meta_features = []
        for pred in predictions:
            meta_features.extend([pred.score, pred.confidence])
        
        return np.array([meta_features], dtype=np.float32)
    
    def _apply_decision_filters(self, ensemble: EnsemblePrediction) -> EnsemblePrediction:
        """Aplica filtros de decisión al resultado del ensemble."""
        if self._config is None:
            return ensemble
        
        # Filtro 1: Umbral de señal
        passed_threshold = abs(ensemble.final_score) >= self._config.signal_threshold
        
        # Filtro 2: Retorno esperado
        expected_return = self._estimate_expected_return(ensemble)
        passed_return = expected_return >= self._config.min_expected_return
        
        # Filtro 3: Evaluación de riesgo
        risk_assessment = self._assess_risk(ensemble)
        passed_risk = risk_assessment in ["low", "medium"]
        
        # Decisión final
        should_trade = passed_threshold and passed_return and passed_risk
        
        # Calcular tamaño de posición sugerido
        position_size = self._calculate_position_size(ensemble) if should_trade else 0.0
        
        return EnsemblePrediction(
            **ensemble.model_dump(),
            passed_threshold=passed_threshold,
            expected_return=round(expected_return, 6),
            risk_assessment=risk_assessment,
            should_trade=should_trade,
            suggested_position_size=round(position_size, 4),
        )
    
    def _estimate_expected_return(self, ensemble: EnsemblePrediction) -> float:
        """Estima el retorno esperado basado en el score y confianza."""
        # Heurística simple: score * confianza * factor de escala
        base_return = abs(ensemble.final_score) * ensemble.final_confidence
        
        # Ajustar por clase de activo
        asset_factors = {
            AssetClass.CRYPTO: 0.01,
            AssetClass.FOREX: 0.0005,
            AssetClass.INDICES: 0.001,
            AssetClass.COMMODITIES: 0.0008,
        }
        factor = asset_factors.get(self._config.asset_class, 0.001)
        
        return base_return * factor
    
    def _assess_risk(self, ensemble: EnsemblePrediction) -> str:
        """Evalúa el nivel de riesgo de la señal."""
        # Analizar dispersión de predicciones
        scores = [p.score for p in ensemble.individual_predictions]
        if len(scores) < 2:
            return "unknown"
        
        score_std = np.std(scores)
        
        # Consenso bajo = mayor riesgo
        if score_std > 0.5:
            return "high"
        elif score_std > 0.3:
            return "medium"
        else:
            return "low"
    
    def _calculate_position_size(self, ensemble: EnsemblePrediction) -> float:
        """Calcula el tamaño de posición sugerido basado en confianza y riesgo."""
        base_size = ensemble.final_confidence
        
        # Ajustar por riesgo
        risk_multiplier = {
            "low": 1.0,
            "medium": 0.7,
            "high": 0.4,
            "unknown": 0.5,
        }.get(ensemble.risk_assessment, 0.5)
        
        # Limitar por riesgo máximo
        max_size = self._config.max_risk_per_trade if self._config else 0.02
        
        return min(base_size * risk_multiplier, max_size)
    
    def _score_to_direction(self, score: float) -> str:
        """Convierte score a dirección."""
        threshold = self._config.signal_threshold if self._config else 0.3
        if score >= threshold:
            return "BUY"
        elif score <= -threshold:
            return "SELL"
        return "NEUTRAL"
    
    def _fallback_prediction(self, features: FeatureSet) -> AgentOutput:
        """Predicción de fallback cuando no hay modelos disponibles."""
        # Usar reglas simples basadas en RSI y tendencia
        score = 0.0
        
        if hasattr(features, 'rsi_14'):
            if features.rsi_14 < 30:
                score += 0.3
            elif features.rsi_14 > 70:
                score -= 0.3
        
        if hasattr(features, 'trend_direction'):
            if features.trend_direction == "bullish":
                score += 0.2
            elif features.trend_direction == "bearish":
                score -= 0.2
        
        direction = self._score_to_direction(score)
        confidence = min(abs(score) * 2, 1.0)
        
        return AgentOutput(
            agent_id=self.agent_id,
            timestamp=features.timestamp,
            symbol=features.symbol,
            direction=direction,
            score=round(score, 4),
            confidence=round(confidence, 4),
            features_used=["rsi_14", "trend_direction"],
            shap_values={},
            model_version=f"{self.model_version}_fallback",
        )
    
    def _get_all_feature_names(self) -> list[str]:
        """Obtiene todos los nombres de features usados."""
        if self._config is None:
            return []
        return self._config.feature_config.all_features
    
    def _aggregate_shap_values(self, predictions: list[ModelPrediction]) -> dict[str, float]:
        """Agrega valores SHAP de todos los modelos."""
        aggregated = {}
        for pred in predictions:
            for feature, value in pred.shap_values.items():
                if feature not in aggregated:
                    aggregated[feature] = 0.0
                aggregated[feature] += value / len(predictions) if predictions else 0
        return aggregated
    
    def get_model_status(self) -> dict[str, Any]:
        """Retorna el estado de todos los modelos."""
        return {
            "asset_class": self._config.asset_class.value if self._config else None,
            "models_loaded": sum(1 for m in self._models.values() if m.is_trained),
            "models_total": len(self._models),
            "meta_model_loaded": self._meta_model is not None,
            "individual_models": {
                key: {
                    "type": wrapper.spec.model_type.value,
                    "strategy": wrapper.spec.strategy_type.value,
                    "trained": wrapper.is_trained,
                }
                for key, wrapper in self._models.items()
            },
        }


# Factory para crear agentes específicos
def create_asset_agent(
    symbol: str,
    asset_class: Optional[AssetClass] = None,
    model_base_path: str = "data/models/asset_specific",
) -> AssetSpecificAgent:
    """
    Factory para crear un agente específico por activo.
    
    Args:
        symbol: Símbolo del activo
        asset_class: Clase de activo (opcional, se detecta automáticamente)
        model_base_path: Ruta base para los modelos
        
    Returns:
        AssetSpecificAgent: Agente configurado para el activo
    """
    return AssetSpecificAgent(
        asset_class=asset_class,
        symbol=symbol,
        model_base_path=model_base_path,
    )


__all__ = [
    "AssetSpecificAgent",
    "AssetSpecificModel",
    "create_asset_agent",
]
