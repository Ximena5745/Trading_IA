"""
Module: core/ml/online_learning_agent.py
Responsibility: Modelo incremental que se actualiza con cada nueva barra.
  Framework: River (ex scikit-multiflow)
  Modelos: AMFClassifier (adaptive random forest) + HoeffdingTreeClassifier
  Benchmark vs: LightGBM batch (reentrenado cada 100 barras)
  Criterio adopción: River mantiene ≥ 80% del Sharpe de LightGBM
Dependencies: river, sklearn, numpy, pandas
"""
from __future__ import annotations

from typing import Any, Optional

import numpy as np

from core.observability.logger import get_logger

logger = get_logger(__name__)

RIVER_AVAILABLE = True
try:
    from river import compose, linear_model, tree, ensemble, metrics, drift
except ImportError:
    RIVER_AVAILABLE = False


class OnlineLearningAgent:
    """
    Modelo incremental que se actualiza con cada nueva barra.

    M6.1: Online Learning con River.
    """

    def __init__(
        self,
        model_type: str = "hoeffding_tree",
        accuracy_threshold: float = 0.80,
    ):
        self._model_type = model_type
        self._accuracy_threshold = accuracy_threshold
        self._model: Optional[Any] = None
        self._metrics = metrics.Accuracy()
        self._feature_names: list[str] = []
        self._is_trained = False
        self._n_samples = 0
        self._batch_sharpe = 0.0
        self._online_sharpe = 0.0

        if not RIVER_AVAILABLE:
            logger.warning("river_not_available_using_fallback")

    def _build_model(self) -> Any:
        """Construir modelo River según tipo."""
        if self._model_type == "hoeffding_tree":
            return tree.HoeffdingTreeClassifier(
                grace_period=50,
                max_depth=10,
                split_criterion="gini",
            )
        elif self._model_type == "adaptive_forest":
            return ensemble.AdaptiveRandomForestClassifier(
                n_estimators=5,
                max_depth=10,
                seed=42,
            )
        elif self._model_type == "logistic":
            return linear_model.LogisticRegression()
        else:
            return tree.HoeffdingTreeClassifier()

    def fit(self, X: np.ndarray, y: np.ndarray, feature_names: list[str] = None) -> None:
        """Entrenar modelo inicial (offline)."""
        if not RIVER_AVAILABLE:
            logger.warning("river_not_available")
            return

        self._model = self._build_model()
        self._feature_names = feature_names or [f"f_{i}" for i in range(X.shape[1])]

        for i in range(len(X)):
            x_dict = dict(zip(self._feature_names, X[i]))
            self._model.learn_one(x_dict, int(y[i]))

        self._is_trained = True
        self._n_samples = len(X)
        logger.info("online_agent_trained", samples=self._n_samples)

    def partial_fit(self, X: np.ndarray, y: np.ndarray) -> dict:
        """Actualizar modelo con nuevos datos (online)."""
        if self._model is None:
            return {"error": "Model not initialized"}

        results = {"updated": False, "accuracy": 0.0}

        for i in range(len(X)):
            x_dict = dict(zip(self._feature_names, X[i]))
            pred = self._model.predict_one(x_dict)
            self._model.learn_one(x_dict, int(y[i]))

            self._metrics.update(int(y[i]), pred)
            self._n_samples += 1

        results["accuracy"] = self._metrics.get()
        results["updated"] = True

        if self._n_samples % 50 == 0:
            logger.info(
                "online_agent_updated",
                samples=self._n_samples,
                accuracy=results["accuracy"],
            )

        return results

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predecir con el modelo online."""
        if self._model is None:
            return np.zeros(len(X))

        predictions = []
        for i in range(len(X)):
            x_dict = dict(zip(self._feature_names, X[i]))
            pred = self._model.predict_one(x_dict)
            predictions.append(pred if pred is not None else 0)

        return np.array(predictions)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predecir probabilidades."""
        if self._model is None:
            return np.ones((len(X), 2)) * 0.5

        probas = []
        for i in range(len(X)):
            x_dict = dict(zip(self._feature_names, X[i]))
            pred = self._model.predict_proba_one(x_dict)
            proba = [pred.get(0, 0.5), pred.get(1, 0.5)]
            probas.append(proba)

        return np.array(probas)

    def compare_with_batch(
        self,
        batch_model: Any,
        X_test: np.ndarray,
        y_test: np.ndarray,
    ) -> dict:
        """Comparar performance con modelo batch."""
        batch_pred = batch_model.predict(X_test)
        batch_acc = np.mean(batch_pred == y_test)

        online_pred = self.predict(X_test)
        online_acc = np.mean(online_pred == y_test)

        ratio = online_acc / batch_acc if batch_acc > 0 else 0

        return {
            "batch_accuracy": batch_acc,
            "online_accuracy": online_acc,
            "ratio": ratio,
            "adopted": ratio >= self._accuracy_threshold,
        }

    def get_model_info(self) -> dict:
        """Obtener información del modelo."""
        return {
            "model_type": self._model_type,
            "is_trained": self._is_trained,
            "n_samples": self._n_samples,
            "accuracy": self._metrics.get(),
        }