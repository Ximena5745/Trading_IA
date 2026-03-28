"""
Module: core/features/feature_engineering.py
Responsibility: Convert enriched DataFrame into a FeatureSet Pydantic model
Dependencies: indicators, models, logger
"""

from __future__ import annotations

import pandas as pd

from core.exceptions import FeatureCalculationError
from core.features.indicators import calculate_all
from core.models import FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)


class FeatureEngine:
    def __init__(self, feature_version: str = "v1"):
        self._version = feature_version

    def calculate(self, ohlcv_df: pd.DataFrame) -> FeatureSet:
        """
        Full pipeline: raw OHLCV DataFrame → validated FeatureSet.
        Raises FeatureCalculationError if data is insufficient or invalid.
        """
        enriched = calculate_all(ohlcv_df)
        last = enriched.iloc[-1]
        return self._to_feature_set(last, ohlcv_df["symbol"].iloc[-1])

    def calculate_batch(self, ohlcv_df: pd.DataFrame) -> list[FeatureSet]:
        """Calculate features for every row (use for backtesting)."""
        enriched = calculate_all(ohlcv_df)
        symbol = ohlcv_df["symbol"].iloc[0]
        return [self._to_feature_set(row, symbol) for _, row in enriched.iterrows()]

    def _to_feature_set(self, row: pd.Series, symbol: str) -> FeatureSet:
        try:
            return FeatureSet(
                timestamp=(
                    row["timestamp"]
                    if hasattr(row["timestamp"], "isoformat")
                    else row.name
                ),
                symbol=symbol,
                version=self._version,
                rsi_14=float(row["rsi_14"]),
                rsi_7=float(row["rsi_7"]),
                macd_line=float(row["macd_line"]),
                macd_signal=float(row["macd_signal"]),
                macd_histogram=float(row["macd_histogram"]),
                ema_9=float(row["ema_9"]),
                ema_21=float(row["ema_21"]),
                ema_50=float(row["ema_50"]),
                ema_200=float(row["ema_200"]),
                trend_direction=str(row["trend_direction"]),
                atr_14=float(row["atr_14"]),
                bb_upper=float(row["bb_upper"]),
                bb_lower=float(row["bb_lower"]),
                bb_width=float(row["bb_width"]),
                volatility_regime=str(row["volatility_regime"]),
                vwap=float(row["vwap"]),
                volume_sma_20=float(row["volume_sma_20"]),
                volume_ratio=float(row["volume_ratio"]),
                obv=float(row["obv"]),
                close=float(row["close"]),
            )
        except (KeyError, ValueError) as e:
            raise FeatureCalculationError(f"Failed to build FeatureSet: {e}") from e
