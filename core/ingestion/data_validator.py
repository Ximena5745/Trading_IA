"""
Module: core/ingestion/data_validator.py
Responsibility: Validate incoming market data from exchange
Dependencies: models, exceptions, logger
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from core.exceptions import DataValidationError
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

MAX_TIMESTAMP_AGE_BARS = 2
MAX_PRICE_STD_DEVS = 5.0


class DataValidator:
    def validate_market_data(self, data: MarketData) -> MarketData:
        """Validate a single MarketData record. Raises DataValidationError on failure."""
        self._check_prices_positive(data)
        self._check_high_low_consistency(data)
        self._check_volume_positive(data)
        return data

    def validate_batch(self, records: list[MarketData]) -> list[MarketData]:
        """Validate a list of records, skipping (and logging) invalid ones."""
        valid = []
        for record in records:
            try:
                valid.append(self.validate_market_data(record))
            except DataValidationError as e:
                logger.warning(
                    "market_data_validation_failed", error=str(e), symbol=record.symbol
                )
        return valid

    def check_timestamp_freshness(
        self, data: MarketData, timeframe_seconds: int
    ) -> bool:
        """Returns False if data is older than MAX_TIMESTAMP_AGE_BARS candles."""
        max_age = timedelta(seconds=timeframe_seconds * MAX_TIMESTAMP_AGE_BARS)
        age = datetime.utcnow() - data.timestamp.replace(tzinfo=None)
        if age > max_age:
            logger.warning(
                "stale_market_data", symbol=data.symbol, age_seconds=age.total_seconds()
            )
            return False
        return True

    def _check_prices_positive(self, data: MarketData) -> None:
        for field in ("open", "high", "low", "close"):
            val = getattr(data, field)
            if val <= Decimal("0"):
                raise DataValidationError(f"{field} must be positive, got {val}")

    def _check_high_low_consistency(self, data: MarketData) -> None:
        if data.high < data.low:
            raise DataValidationError(f"high ({data.high}) < low ({data.low})")
        if data.high < data.close:
            raise DataValidationError(f"high ({data.high}) < close ({data.close})")
        if data.low > data.close:
            raise DataValidationError(f"low ({data.low}) > close ({data.close})")

    def _check_volume_positive(self, data: MarketData) -> None:
        if data.volume < Decimal("0"):
            raise DataValidationError(f"volume must be >= 0, got {data.volume}")
