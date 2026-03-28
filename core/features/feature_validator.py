"""
Module: core/features/feature_validator.py
Responsibility: Detect NaN, outliers and feature drift
Dependencies: models, logger
"""

from __future__ import annotations

import math

from core.exceptions import FeatureCalculationError
from core.models import FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)

CRITICAL_FEATURES = ["rsi_14", "ema_50", "ema_200", "atr_14", "macd_line"]
DRIFT_STD_THRESHOLD = 5.0


class FeatureValidator:
    def validate(self, features: FeatureSet) -> FeatureSet:
        """Validate a single FeatureSet. Raises FeatureCalculationError on failure."""
        self._check_no_nan(features)
        self._check_rsi_range(features)
        return features

    def check_drift(self, features: FeatureSet, history: list[FeatureSet]) -> bool:
        """Returns True if current features are within normal range of history."""
        if len(history) < 20:
            return True
        for field in ("rsi_14", "volume_ratio", "bb_width"):
            values = [
                getattr(f, field) for f in history if not math.isnan(getattr(f, field))
            ]
            if not values:
                continue
            mean = sum(values) / len(values)
            std = (sum((v - mean) ** 2 for v in values) / len(values)) ** 0.5
            current = getattr(features, field)
            if std > 0 and abs(current - mean) / std > DRIFT_STD_THRESHOLD:
                logger.warning(
                    "feature_drift_detected",
                    field=field,
                    current=current,
                    mean=mean,
                    std=std,
                )
                return False
        return True

    def _check_no_nan(self, features: FeatureSet) -> None:
        for field in CRITICAL_FEATURES:
            val = getattr(features, field, None)
            if val is None or math.isnan(val):
                raise FeatureCalculationError(
                    f"NaN detected in critical feature: {field}"
                )

    def _check_rsi_range(self, features: FeatureSet) -> None:
        for field in ("rsi_14", "rsi_7"):
            val = getattr(features, field)
            if not (0 <= val <= 100):
                raise FeatureCalculationError(f"{field} out of range: {val}")
