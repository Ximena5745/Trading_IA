"""
Module: core/ml/ab_testing.py
Responsibility: Shadow mode para modelos candidatos con comparación estadística.
  - Shadow mode: modelo candidato corre en paralelo sin ejecutar órdenes
  - Comparación: Mann-Whitney U test de Sharpe OOS
  - Criterio graduación: p-value < 0.05 + mejora ≥ 10% en Sharpe
  - Duración mínima: 100 predicciones
Dependencies: scipy, numpy, pandas
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional

import numpy as np
import pandas as pd
from scipy import stats

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ABTestResult:
    candidate_name: str
    control_name: str
    control_sharpe: float
    candidate_sharpe: float
    improvement_pct: float
    p_value: float
    approved: bool
    n_predictions: int
    timestamp: datetime


class ABTestingFramework:
    """
    Framework para testing A/B de modelos.

    M4.5: A/B Testing Framework con shadow mode.
    """

    def __init__(
        self,
        min_predictions: int = 100,
        improvement_threshold: float = 1.10,
        p_value_threshold: float = 0.05,
    ):
        self._min_predictions = min_predictions
        self._improvement_threshold = improvement_threshold
        self._p_value_threshold = p_value_threshold
        self._active_tests: dict[str, dict] = {}

    def start_shadow_test(
        self,
        candidate_name: str,
        control_name: str,
        candidate_predict_fn: Callable,
    ) -> None:
        """Iniciar test en shadow mode para un candidato."""
        self._active_tests[candidate_name] = {
            "control": control_name,
            "predict_fn": candidate_predict_fn,
            "predictions": [],
            "actuals": [],
            "returns": [],
            "started_at": datetime.utcnow(),
        }
        logger.info(
            "ab_test_started",
            candidate=candidate_name,
            control=control_name,
            min_predictions=self._min_predictions,
        )

    def record_prediction(
        self,
        candidate_name: str,
        prediction: float,
        actual_return: float,
    ) -> None:
        """Registrar predicción y resultado real."""
        if candidate_name not in self._active_tests:
            logger.warning("ab_test_not_found", candidate=candidate_name)
            return

        test = self._active_tests[candidate_name]
        test["predictions"].append(prediction)
        test["actuals"].append(actual_return)
        test["returns"].append(actual_return)

        if len(test["returns"]) % 50 == 0:
            logger.info(
                "ab_test_progress",
                candidate=candidate_name,
                n=len(test["returns"]),
            )

    def evaluate(
        self,
        candidate_name: str,
        control_returns: list[float],
    ) -> ABTestResult:
        """
        Evaluar resultado del test A/B.
        """
        if candidate_name not in self._active_tests:
            raise ValueError(f"No active test for {candidate_name}")

        test = self._active_tests[candidate_name]
        n_predictions = len(test["returns"])

        if n_predictions < self._min_predictions:
            return ABTestResult(
                candidate_name=candidate_name,
                control_name=test["control"],
                control_sharpe=self._sharpe(control_returns),
                candidate_sharpe=0.0,
                improvement_pct=0.0,
                p_value=1.0,
                approved=False,
                n_predictions=n_predictions,
                timestamp=datetime.utcnow(),
            )

        candidate_sharpe = self._sharpe(test["returns"])
        control_sharpe = self._sharpe(control_returns)

        improvement = (candidate_sharpe / control_sharpe) if control_sharpe > 0 else 0
        improvement_pct = (improvement - 1) * 100

        if len(test["returns"]) >= 20 and len(control_returns) >= 20:
            _, p_value = stats.mannwhitneyu(
                test["returns"], control_returns, alternative="greater"
            )
        else:
            p_value = 1.0

        approved = (
            improvement >= self._improvement_threshold
            and p_value < self._p_value_threshold
        )

        result = ABTestResult(
            candidate_name=candidate_name,
            control_name=test["control"],
            control_sharpe=control_sharpe,
            candidate_sharpe=candidate_sharpe,
            improvement_pct=improvement_pct,
            p_value=p_value,
            approved=approved,
            n_predictions=n_predictions,
            timestamp=datetime.utcnow(),
        )

        logger.info(
            "ab_test_result",
            candidate=candidate_name,
            approved=approved,
            improvement=improvement_pct,
            p_value=p_value,
        )

        if approved:
            logger.info("ab_test_graduated", candidate=candidate_name)
        else:
            logger.warning("ab_test_rejected", candidate=candidate_name)

        return result

    def _sharpe(self, returns: list[float]) -> float:
        """Calcular Sharpe ratio."""
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns)
        mean_ret = arr.mean()
        std_ret = arr.std()
        if std_ret == 0:
            return 0.0
        return mean_ret / std_ret * np.sqrt(252)

    def get_active_tests(self) -> list[dict]:
        """Obtener lista de tests activos."""
        return [
            {
                "candidate": name,
                "started_at": info["started_at"].isoformat(),
                "n_predictions": len(info["returns"]),
            }
            for name, info in self._active_tests.items()
        ]