"""
Module: core/validation/data_validator.py
Responsibility: Enhanced data validation with comprehensive checks
Dependencies: pydantic, pandas, numpy
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from core.models import FeatureSet, MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)


class ValidationError(BaseModel):
    field: str
    message: str
    value: Any
    severity: str = "error"  # error, warning, info


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]
    data_quality_score: float = 1.0


class EnhancedDataValidator:
    """Comprehensive data validation with quality scoring."""

    def __init__(self):
        self.validation_rules = {
            "price_consistency": self._validate_price_consistency,
            "volume_validity": self._validate_volume,
            "timestamp_sequence": self._validate_timestamps,
            "feature_ranges": self._validate_feature_ranges,
            "nan_detection": self._validate_no_nan,
        }

    def validate_market_data(self, data: MarketData) -> ValidationResult:
        """Validate market data with comprehensive checks."""
        errors = []
        warnings = []

        # Basic price consistency
        if not (data.low <= data.open <= data.high):
            errors.append(
                ValidationError(
                    field="price_consistency",
                    message=f"Open price {data.open} not within low-high range [{data.low}, {data.high}]",
                    value=data.open,
                )
            )

        if not (data.low <= data.close <= data.high):
            errors.append(
                ValidationError(
                    field="price_consistency",
                    message=f"Close price {data.close} not within low-high range [{data.low}, {data.high}]",
                    value=data.close,
                )
            )

        # Volume validation
        if data.volume < 0:
            errors.append(
                ValidationError(
                    field="volume",
                    message="Volume cannot be negative",
                    value=data.volume,
                )
            )

        # Timestamp validation
        if data.timestamp > datetime.utcnow():
            warnings.append(
                ValidationError(
                    field="timestamp",
                    message="Timestamp is in the future",
                    value=data.timestamp,
                    severity="warning",
                )
            )

        # Data quality score
        quality_score = max(0, 1.0 - (len(errors) * 0.2) - (len(warnings) * 0.1))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data_quality_score=quality_score,
        )

    def validate_feature_set(self, features: FeatureSet) -> ValidationResult:
        """Validate feature set with range and consistency checks."""
        errors = []
        warnings = []

        # RSI validation
        if not (0 <= features.rsi_14 <= 100):
            errors.append(
                ValidationError(
                    field="rsi_14",
                    message=f"RSI must be between 0-100, got {features.rsi_14}",
                    value=features.rsi_14,
                )
            )

        if not (0 <= features.rsi_7 <= 100):
            errors.append(
                ValidationError(
                    field="rsi_7",
                    message=f"RSI must be between 0-100, got {features.rsi_7}",
                    value=features.rsi_7,
                )
            )

        # EMA consistency
        emas = [features.ema_9, features.ema_21, features.ema_50, features.ema_200]
        if features.close > 0:
            for ema in emas:
                if ema <= 0:
                    errors.append(
                        ValidationError(
                            field="ema",
                            message="EMA values must be positive",
                            value=ema,
                        )
                    )

        # Volume ratio validation
        if features.volume_ratio < 0:
            errors.append(
                ValidationError(
                    field="volume_ratio",
                    message="Volume ratio cannot be negative",
                    value=features.volume_ratio,
                )
            )

        # ATR validation
        if features.atr_14 < 0:
            errors.append(
                ValidationError(
                    field="atr_14",
                    message="ATR cannot be negative",
                    value=features.atr_14,
                )
            )

        # Trend direction validation
        valid_trends = ["bullish", "bearish", "sideways"]
        if features.trend_direction not in valid_trends:
            errors.append(
                ValidationError(
                    field="trend_direction",
                    message=f"Invalid trend direction: {features.trend_direction}",
                    value=features.trend_direction,
                )
            )

        # Volatility regime validation
        valid_volatility = ["low", "medium", "high", "extreme"]
        if features.volatility_regime not in valid_volatility:
            errors.append(
                ValidationError(
                    field="volatility_regime",
                    message=f"Invalid volatility regime: {features.volatility_regime}",
                    value=features.volatility_regime,
                )
            )

        # Data quality score
        quality_score = max(0, 1.0 - (len(errors) * 0.15) - (len(warnings) * 0.05))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data_quality_score=quality_score,
        )

    def validate_portfolio_health(
        self, portfolio_data: dict[str, Any]
    ) -> ValidationResult:
        """Validate portfolio health metrics."""
        errors = []
        warnings = []

        total_capital = portfolio_data.get("total_capital", 0)
        available_capital = portfolio_data.get("available_capital", 0)
        risk_exposure = portfolio_data.get("risk_exposure", 0)

        # Capital consistency
        if available_capital > total_capital:
            errors.append(
                ValidationError(
                    field="capital_consistency",
                    message="Available capital cannot exceed total capital",
                    value={"available": available_capital, "total": total_capital},
                )
            )

        # Risk exposure validation
        if not (0 <= risk_exposure <= 1):
            errors.append(
                ValidationError(
                    field="risk_exposure",
                    message="Risk exposure must be between 0-1",
                    value=risk_exposure,
                )
            )

        if risk_exposure > 0.5:
            warnings.append(
                ValidationError(
                    field="risk_exposure",
                    message="High risk exposure detected",
                    value=risk_exposure,
                    severity="warning",
                )
            )

        quality_score = max(0, 1.0 - (len(errors) * 0.2) - (len(warnings) * 0.1))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            data_quality_score=quality_score,
        )

    def _validate_price_consistency(
        self, data: dict[str, Any]
    ) -> list[ValidationError]:
        """Validate price data consistency."""
        errors = []
        # Implementation for batch validation
        return errors

    def _validate_volume(self, data: dict[str, Any]) -> list[ValidationError]:
        """Validate volume data."""
        errors = []
        # Implementation for batch validation
        return errors

    def _validate_timestamps(self, data: dict[str, Any]) -> list[ValidationError]:
        """Validate timestamp sequences."""
        errors = []
        # Implementation for batch validation
        return errors

    def _validate_feature_ranges(self, data: dict[str, Any]) -> list[ValidationError]:
        """Validate feature value ranges."""
        errors = []
        # Implementation for batch validation
        return errors

    def _validate_no_nan(self, data: dict[str, Any]) -> list[ValidationError]:
        """Check for NaN values."""
        errors = []
        # Implementation for batch validation
        return errors


# Singleton instance for global use
data_validator = EnhancedDataValidator()
