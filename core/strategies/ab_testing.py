"""
Module: core/strategies/ab_testing.py
Responsibility: A/B Testing Framework para comparar modelos candidatos.
  - Shadow mode: modelo candidato corre en paralelo sin ejecutar órdenes
  - Comparación estadística: Mann-Whitney U test de Sharpe OOS
  - Criterio de graduación: p-value < 0.05 + mejora ≥ 10% en Sharpe
  - Duración mínima: 100 predicciones
Dependencies: scipy, numpy, pandas
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ABTestResult:
    candidate_id: str
    control_sharpe: float
    candidate_sharpe: float
    improvement_pct: float
    p_value: float
    passed: bool
    reason: str
    n_predictions: int


@dataclass
class ABTestConfig:
    min_predictions: int = 100
    max_p_value: float = 0.05
    min_improvement_pct: float = 10.0
    evaluation_window: int = 20


class ABTestingFramework:
    """
    Framework para A/B testing de modelos en modo shadow.

    M4.5: A/B Testing Framework.
    """

    def __init__(self, config: Optional[ABTestConfig] = None):
        self._config = config or ABTestConfig()
        self._tests: dict[str, dict] = {}
        self._active_tests: list[str] = []

    def start_test(
        self,
        test_id: str,
        candidate_model_id: str,
        control_model_id: str,
        description: str = "",
    ) -> dict:
        """
        Iniciar un nuevo A/B test.

        Args:
            test_id: Identificador único del test
            candidate_model_id: ID del modelo candidato
            control_model_id: ID del modelo control (actual)
            description: Descripción opcional

        Returns:
            Configuración del test iniciado
        """
        if test_id in self._tests:
            logger.warning("test_already_exists", test_id=test_id)
            return self._tests[test_id]["config"]

        self._tests[test_id] = {
            "config": {
                "test_id": test_id,
                "candidate_id": candidate_model_id,
                "control_id": control_model_id,
                "description": description,
                "start_time": datetime.utcnow(),
            },
            "candidate_predictions": [],
            "control_predictions": [],
            "candidate_returns": [],
            "control_returns": [],
            "status": "running",
        }
        self._active_tests.append(test_id)

        logger.info(
            "ab_test_started",
            test_id=test_id,
            candidate=candidate_model_id,
            control=control_model_id,
        )

        return self._tests[test_id]["config"]

    def record_prediction(
        self,
        test_id: str,
        candidate_prediction: float,
        control_prediction: float,
        actual_return: float,
    ) -> None:
        """
        Registrar resultado de predicción para un test activo.

        Args:
            test_id: ID del test
            candidate_prediction: Predicción del modelo candidato (-1 a 1)
            control_prediction: Predicción del modelo control (-1 a 1)
            actual_return: Return real del activo (porcentaje)
        """
        if test_id not in self._tests:
            logger.warning("test_not_found", test_id=test_id)
            return

        test = self._tests[test_id]

        if test["status"] != "running":
            logger.warning("test_not_running", test_id=test_id, status=test["status"])
            return

        test["candidate_predictions"].append(candidate_prediction)
        test["control_predictions"].append(control_prediction)

        candidate_return = candidate_prediction * actual_return
        control_return = control_prediction * actual_return

        test["candidate_returns"].append(candidate_return)
        test["control_returns"].append(control_return)

    def evaluate_test(self, test_id: str) -> ABTestResult:
        """
        Evaluar resultados de un A/B test.

        Returns:
            ABTestResult con métricas y decisión de graduación
        """
        if test_id not in self._tests:
            raise ValueError(f"Test not found: {test_id}")

        test = self._tests[test_id]
        candidate_returns = np.array(test["candidate_returns"])
        control_returns = np.array(test["control_returns"])

        n_preds = len(candidate_returns)
        config = test["config"]

        if n_preds < self._config.min_predictions:
            logger.info(
                "ab_test_insufficient_predictions",
                test_id=test_id,
                current=n_preds,
                required=self._config.min_predictions,
            )
            return ABTestResult(
                candidate_id=config["candidate_id"],
                control_sharpe=0.0,
                candidate_sharpe=0.0,
                improvement_pct=0.0,
                p_value=1.0,
                passed=False,
                reason=f"Insufficient predictions: {n_preds} < {self._config.min_predictions}",
                n_predictions=n_preds,
            )

        candidate_sharpe = self._calculate_sharpe(candidate_returns)
        control_sharpe = self._calculate_sharpe(control_returns)

        improvement = 0.0
        if control_sharpe != 0:
            improvement = ((candidate_sharpe - control_sharpe) / abs(control_sharpe)) * 100

        p_value = self._mann_whitney_test(candidate_returns, control_returns)

        passed = (
            p_value < self._config.max_p_value
            and improvement >= self._config.min_improvement_pct
        )

        if passed:
            reason = "PASSED: Criterios cumplidos"
            test["status"] = "passed"
            logger.info(
                "ab_test_passed",
                test_id=test_id,
                candidate_sharpe=candidate_sharpe,
                control_sharpe=control_sharpe,
                improvement=improvement,
                p_value=p_value,
            )
        else:
            reasons = []
            if p_value >= self._config.max_p_value:
                reasons.append(f"p-value {p_value:.3f} >= {self._config.max_p_value}")
            if improvement < self._config.min_improvement_pct:
                reasons.append(f"improvement {improvement:.1f}% < {self._config.min_improvement_pct}%")
            reason = f"FAILED: {'; '.join(reasons)}"
            test["status"] = "failed"
            logger.info(
                "ab_test_failed",
                test_id=test_id,
                reason=reason,
            )

        return ABTestResult(
            candidate_id=config["candidate_id"],
            control_sharpe=control_sharpe,
            candidate_sharpe=candidate_sharpe,
            improvement_pct=improvement,
            p_value=p_value,
            passed=passed,
            reason=reason,
            n_predictions=n_preds,
        )

    def _calculate_sharpe(self, returns: np.ndarray, periods_per_year: int = 8760) -> float:
        """Calculate Sharpe ratio from returns."""
        if len(returns) < 2:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)

        if std_return == 0:
            return 0.0

        sharpe = (mean_return / std_return) * np.sqrt(periods_per_year)
        return float(sharpe)

    def _mann_whitney_test(
        self, candidate_returns: np.ndarray, control_returns: np.ndarray
    ) -> float:
        """
        Mann-Whitney U test para comparar distribuciones.

        Returns:
            p-value del test
        """
        if len(candidate_returns) < 3 or len(control_returns) < 3:
            return 1.0

        try:
            statistic, p_value = stats.mannwhitneyu(
                candidate_returns, control_returns, alternative="greater"
            )
            return float(p_value)
        except Exception as e:
            logger.warning("mann_whitney_failed", error=str(e))
            return 1.0

    def get_active_tests(self) -> list[dict]:
        """Obtener lista de tests activos."""
        return [
            {
                "test_id": test_id,
                "status": self._tests[test_id]["status"],
                "n_predictions": len(self._tests[test_id]["candidate_predictions"]),
                "config": self._tests[test_id]["config"],
            }
            for test_id in self._active_tests
        ]

    def get_test_status(self, test_id: str) -> Optional[dict]:
        """Obtener estado de un test específico."""
        if test_id not in self._tests:
            return None

        test = self._tests[test_id]
        return {
            "test_id": test_id,
            "status": test["status"],
            "n_predictions": len(test["candidate_predictions"]),
            "candidate_sharpe": self._calculate_sharpe(np.array(test["candidate_returns"])),
            "control_sharpe": self._calculate_sharpe(np.array(test["control_returns"])),
            "start_time": test["config"]["start_time"],
        }

    def graduate_candidate(self, test_id: str) -> Optional[dict]:
        """
        Graduar candidato y promover a producción.

        Returns:
            Configuración del candidato graduado o None si falló
        """
        if test_id not in self._tests:
            logger.warning("test_not_found_for_graduation", test_id=test_id)
            return None

        result = self.evaluate_test(test_id)

        if not result.passed:
            logger.warning(
                "candidate_not_graduated_failed_criteria",
                test_id=test_id,
                reason=result.reason,
            )
            return None

        logger.info(
            "candidate_graduated",
            test_id=test_id,
            candidate_id=result.candidate_id,
        )

        self._active_tests.remove(test_id)

        return {
            "candidate_id": result.candidate_id,
            "sharpe": result.candidate_sharpe,
            "improvement": result.improvement_pct,
            "p_value": result.p_value,
            "graduated_at": datetime.utcnow().isoformat(),
        }