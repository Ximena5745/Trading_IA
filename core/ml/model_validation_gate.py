"""
Module: core/ml/model_validation_gate.py
Responsibility: Validación de modelos antes de deployment.
  - Comparar Sharpe OOS con modelo actual
  - Solo reemplazar si Sharpe_nuevo >= Sharpe_actual * 1.10
  - Verificar distribución de predicciones
  - Verificar max drawdown OOS < 20%
  - Registrar decisión en audit log
Dependencies: numpy, pandas, sklearn
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from core.backtesting.metrics import sharpe_ratio
from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ModelValidationResult:
    approved: bool
    reason: str
    current_sharpe: float
    new_sharpe: float
    sharpe_improvement: float
    drawdown_new: float
    prediction_diversity: float
    timestamp: datetime


class ModelValidationGate:
    """
    Validador de modelos antes de deployment.

    M3.2: Model Validation Gate - ningún modelo peor entra a producción.
    Criterios:
      - Sharpe_nuevo >= Sharpe_actual * 1.10 (mejora ≥10%)
      - Max drawdown OOS < 20%
      - Predicciones no son todas iguales (diversidad > 0.1)
    """

    def __init__(
        self,
        min_improvement: float = 1.10,
        max_drawdown: float = 0.20,
        min_diversity: float = 0.1,
    ):
        self.min_improvement = min_improvement
        self.max_drawdown = max_drawdown
        self.min_diversity = min_diversity

    def validate(
        self,
        current_model_sharpe: float,
        new_model_sharpe: float,
        returns_new: pd.Series,
        predictions_new: np.ndarray,
    ) -> ModelValidationResult:
        """Validar si el nuevo modelo puede reemplazar al actual."""
        sharpe_improvement = (
            new_model_sharpe / current_model_sharpe if current_model_sharpe > 0 else float("inf")
        )

        drawdown_new = self._calculate_max_drawdown(returns_new)
        prediction_diversity = self._calculate_diversity(predictions_new)

        approved = (
            new_model_sharpe >= current_model_sharpe * self.min_improvement
            and drawdown_new < self.max_drawdown
            and prediction_diversity > self.min_diversity
        )

        if approved:
            reason = "APPROVED"
        elif new_model_sharpe < current_model_sharpe * self.min_improvement:
            reason = f"REJECTED: Sharpe improvement {sharpe_improvement:.2f} < {self.min_improvement}"
        elif drawdown_new >= self.max_drawdown:
            reason = f"REJECTED: Max drawdown {drawdown_new:.1%} >= {self.max_drawdown:.1%}"
        else:
            reason = f"REJECTED: Prediction diversity {prediction_diversity:.2f} < {self.min_diversity}"

        logger.info(
            "model_validation_result",
            approved=approved,
            reason=reason,
            current_sharpe=current_model_sharpe,
            new_sharpe=new_model_sharpe,
            improvement=sharpe_improvement,
            drawdown=drawdown_new,
            diversity=prediction_diversity,
        )

        return ModelValidationResult(
            approved=approved,
            reason=reason,
            current_sharpe=current_model_sharpe,
            new_model_sharpe=new_model_sharpe,
            sharpe_improvement=sharpe_improvement,
            drawdown_new=drawdown_new,
            prediction_diversity=prediction_diversity,
            timestamp=datetime.utcnow(),
        )

    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """Calculate maximum drawdown from returns."""
        if len(returns) == 0:
            return 0.0
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        return abs(drawdown.min())

    def _calculate_diversity(self, predictions: np.ndarray) -> float:
        """Calculate diversity of predictions (std of predictions)."""
        if len(predictions) == 0:
            return 0.0
        return float(np.std(predictions))