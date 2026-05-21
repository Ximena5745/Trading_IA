"""
Module: core/ml/drift_detector.py
Responsibility: Detección de concept drift con múltiples métodos.
  Monitorea:
    1. Feature drift: KL-divergence entre distribución actual vs training
    2. Performance decay: Sharpe rolling cae > 30% vs baseline
    3. Regime change: HMM detecta transición a estado no visto
    4. Prediction distribution: predicciones todas iguales → error silencioso
  Respuesta: leve → aumentar peso online, moderado → reentrenar, grave → desactivar
Dependencies: numpy, pandas, scipy
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats

from core.observability.logger import get_logger

logger = get_logger(__name__)


class DriftLevel(Enum):
    NONE = "none"
    LEVE = "leve"
    MODERADO = "moderado"
    GRAVE = "grave"


@dataclass
class DriftReport:
    level: DriftLevel
    feature_drift: float
    performance_decay: float
    regime_change_detected: bool
    prediction_diversity: float
    recommended_action: str
    details: dict


class DriftDetector:
    """
    Detector de concept drift.

    M6.2: Concept Drift Detection.
    """

    def __init__(
        self,
        kl_threshold: float = 0.1,
        performance_decay_threshold: float = 0.30,
        prediction_diversity_threshold: float = 0.1,
        window_size: int = 100,
    ):
        self._kl_threshold = kl_threshold
        self._perf_decay_threshold = performance_decay_threshold
        self._diversity_threshold = prediction_diversity_threshold
        self._window = window_size
        self._baseline_distribution: Optional[dict] = None
        self._baseline_sharpe: Optional[float] = None
        self._rolling_sharpes: list[float] = []
        self._previous_regime: Optional[str] = None

    def set_baseline(
        self,
        feature_distributions: dict[str, np.ndarray],
        baseline_sharpe: float,
    ) -> None:
        """Establecer distribución baseline para comparaciones."""
        self._baseline_distribution = {
            k: np.histogram(v, bins=20, density=True)[0]
            for k, v in feature_distributions.items()
        }
        self._baseline_sharpe = baseline_sharpe
        logger.info("drift_detector_baseline_set", baseline_sharpe=baseline_sharpe)

    def detect(
        self,
        current_features: dict[str, np.ndarray],
        current_sharpe: float,
        current_predictions: np.ndarray,
        current_regime: Optional[str],
    ) -> DriftReport:
        """Detectar drift en datos actuales."""
        feature_drift = self._calculate_feature_drift(current_features)
        perf_decay = self._calculate_performance_decay(current_sharpe)
        pred_diversity = self._calculate_prediction_diversity(current_predictions)
        regime_change = self._detect_regime_change(current_regime)

        drift_score = self._calculate_drift_score(
            feature_drift, perf_decay, pred_diversity, regime_change
        )

        level, action = self._determine_level_and_action(
            drift_score, feature_drift, perf_decay, pred_diversity, regime_change
        )

        logger.info(
            "drift_analysis",
            level=level.value,
            feature_drift=feature_drift,
            performance_decay=perf_decay,
            pred_diversity=pred_diversity,
            regime_change=regime_change,
        )

        return DriftReport(
            level=level,
            feature_drift=feature_drift,
            performance_decay=perf_decay,
            regime_change_detected=regime_change,
            prediction_diversity=pred_diversity,
            recommended_action=action,
            details={
                "drift_score": drift_score,
                "current_sharpe": current_sharpe,
                "baseline_sharpe": self._baseline_sharpe,
            },
        )

    def _calculate_feature_drift(self, current_features: dict[str, np.ndarray]) -> float:
        """Calcular KL-divergence entre distribución actual y baseline."""
        if not self._baseline_distribution:
            return 0.0

        max_drift = 0.0
        for feat_name, current_vals in current_features.items():
            if feat_name not in self._baseline_distribution:
                continue

            baseline_hist = self._baseline_distribution[feat_name]
            current_hist = np.histogram(current_vals, bins=20, density=True)[0]

            current_hist = np.clip(current_hist, 1e-10, 1.0)
            baseline_hist = np.clip(baseline_hist, 1e-10, 1.0)

            kl_div = stats.entropy(current_hist, baseline_hist)
            max_drift = max(max_drift, kl_div)

        return max_drift

    def _calculate_performance_decay(self, current_sharpe: float) -> float:
        """Calcular decay de performance vs baseline."""
        if self._baseline_sharpe is None or self._baseline_sharpe <= 0:
            return 0.0

        self._rolling_sharpes.append(current_sharpe)
        if len(self._rolling_sharpes) > self._window:
            self._rolling_sharpes = self._rolling_sharpes[-self._window:]

        if len(self._rolling_sharpes) < 10:
            return 0.0

        recent_sharpe = np.mean(self._rolling_sharpes[-10:])
        decay = (self._baseline_sharpe - recent_sharpe) / self._baseline_sharpe

        return max(0.0, decay)

    def _calculate_prediction_diversity(self, predictions: np.ndarray) -> float:
        """Calcular diversidad de predicciones (std de predicciones)."""
        if len(predictions) == 0:
            return 0.0
        return float(np.std(predictions))

    def _detect_regime_change(self, current_regime: Optional[str]) -> bool:
        """Detectar cambio de régimen."""
        if current_regime is None or self._previous_regime is None:
            return False

        changed = current_regime != self._previous_regime
        self._previous_regime = current_regime
        return changed

    def _calculate_drift_score(
        self,
        feature_drift: float,
        perf_decay: float,
        pred_diversity: float,
        regime_change: bool,
    ) -> float:
        """Calcular score compuesto de drift."""
        score = 0.0

        if feature_drift > self._kl_threshold:
            score += 0.3
        if perf_decay > self._perf_decay_threshold:
            score += 0.4
        if pred_diversity < self._diversity_threshold:
            score += 0.2
        if regime_change:
            score += 0.1

        return min(score, 1.0)

    def _determine_level_and_action(
        self,
        drift_score: float,
        feature_drift: float,
        perf_decay: float,
        pred_diversity: float,
        regime_change: bool,
    ) -> tuple[DriftLevel, str]:
        """Determinar nivel de drift y acción recomendada."""
        if drift_score >= 0.7 or perf_decay > 0.5:
            return DriftLevel.GRAVE, "DESACTIVAR_MODELO_FALLBACK"
        if drift_score >= 0.4 or perf_decay > 0.3:
            return DriftLevel.MODERADO, "REENTRENAMIENTO_URGENTE"
        if drift_score >= 0.2 or feature_drift > self._kl_threshold * 0.5:
            return DriftLevel.LEVE, "AUMENTAR_PESO_ONLINE"
        return DriftLevel.NONE, "CONTINUAR_NORMAL"