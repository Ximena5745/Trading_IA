"""
Module: core/features/feature_engineering.py
Responsibility: Convert enriched DataFrame into a FeatureSet Pydantic model
Dependencies: indicators, models, logger
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

from core.exceptions import FeatureCalculationError
from core.features.indicators import calculate_all
from core.models import FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)


def resample_ohlcv(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample OHLCV DataFrame to a different timeframe.
    
    Args:
        df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
        timeframe: Target timeframe (e.g., '4h', '1D', '1W')
    
    Returns:
        Resampled DataFrame with OHLCV columns
    """
    df = df.copy()
    
    # Parse timeframe (pandas uses lowercase)
    freq_map = {
        '4h': '4h',   # 4 hours
        '1D': '1D',  # 1 day
        '1d': '1D',
        '1W': '1W',  # 1 week
        '1w': '1W',
        '1h': '1h',  # 1 hour
    }
    freq = freq_map.get(timeframe, timeframe)
    
    # Ensure timestamp is index for resampling
    if 'timestamp' in df.columns:
        df = df.set_index('timestamp')
    
    resampled = df.resample(freq).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum',
    })
    
    # Handle quote_volume and taker_buy_volume if present
    if 'quote_volume' in df.columns:
        resampled['quote_volume'] = df['quote_volume'].resample(freq).sum()
    if 'taker_buy_volume' in df.columns:
        resampled['taker_buy_volume'] = df['taker_buy_volume'].resample(freq).sum()
    
    result = resampled.dropna().reset_index()
    result = result.rename(columns={'index': 'timestamp'} if 'index' in result.columns else {})
    return result


class FeatureEngine:
    def __init__(self, feature_version: str = "v1"):
        self._version = feature_version

    def calculate(self, ohlcv_df: pd.DataFrame, symbol: str | None = None) -> FeatureSet:
        """
        Full pipeline: raw OHLCV DataFrame → validated FeatureSet.
        Raises FeatureCalculationError if data is insufficient or invalid.
        """
        enriched = calculate_all(ohlcv_df)
        last = enriched.iloc[-1]
        symbol_value = symbol
        if symbol_value is None and "symbol" in ohlcv_df.columns:
            symbol_value = str(ohlcv_df["symbol"].iloc[-1])
        if symbol_value is None:
            symbol_value = ""
        return self._to_feature_set(last, symbol_value)

    def calculate_batch(self, ohlcv_df: pd.DataFrame, symbol: str | None = None) -> list[FeatureSet]:
        """Calculate features for every row (use for backtesting)."""
        enriched = calculate_all(ohlcv_df)
        symbol_value = symbol
        if symbol_value is None and "symbol" in ohlcv_df.columns:
            symbol_value = str(ohlcv_df["symbol"].iloc[0])
        if symbol_value is None:
            symbol_value = ""
        return [self._to_feature_set(row, symbol_value) for _, row in enriched.iterrows()]

    def calculate_mtf_features(
        self,
        df_1h: pd.DataFrame,
        symbol: str,
        timeframes: list[str] = None
    ) -> pd.DataFrame:
        """
        Calculate features across multiple timeframes for MTF analysis.
        
        Args:
            df_1h: DataFrame with 1h OHLCV data (will be resampled for other TFs)
            symbol: Symbol name
            timeframes: List of timeframes to calculate (default: ['1h', '4h', '1d'])
        
        Returns:
            DataFrame with multi-timeframe features aligned to 1h index
        """
        if timeframes is None:
            timeframes = ['1h', '4h', '1d']
        
        # Ensure we have proper column names
        df_1h = df_1h.copy()
        if 'timestamp' not in df_1h.columns and df_1h.index.name == 'timestamp':
            df_1h = df_1h.reset_index()
        
        all_features = {}
        
        # Calculate features for each timeframe
        for tf in timeframes:
            if tf == '1h':
                df_tf = df_1h.copy()
            else:
                df_tf = resample_ohlcv(df_1h, tf)
            
            # Calculate indicators for this timeframe
            indicators_tf = calculate_all(df_tf)
            
            # Rename columns with suffix
            suffix = f'_{tf}' if tf != '1h' else ''
            for col in indicators_tf.columns:
                if col not in ['timestamp', 'symbol']:
                    new_col = f"{col}{suffix}" if suffix else col
                    # Forward fill to align to 1h index
                    if tf != '1h':
                        temp_df = indicators_tf[[col]].copy()
                        temp_df.index = indicators_tf['timestamp']
                        aligned = temp_df.reindex(df_1h['timestamp'], method='ffill')
                        all_features[new_col] = aligned[col].values
                    else:
                        all_features[new_col] = indicators_tf[col].values
        
        # Create alignment features (only if we have multiple TFs)
        if len(timeframes) > 1:
            # Create DataFrame from all_features
            df_features = pd.DataFrame(all_features, index=range(len(df_1h)))
            
            # Trend alignment: check if all TFs are aligned
            ema_200_cols = [c for c in df_features.columns if 'ema_200' in c]
            ema_50_cols = [c for c in df_features.columns if 'ema_50' in c]
            
            if ema_200_cols and ema_50_cols:
                # Bullish alignment: ema_200 > ema_50 in all TFs
                trend_scores = []
                for i in range(len(df_features)):
                    score = 0
                    for ema_200_col, ema_50_col in zip(ema_200_cols, ema_50_cols):
                        if pd.notna(df_features[ema_200_col].iloc[i]) and pd.notna(df_features[ema_50_col].iloc[i]):
                            if df_features[ema_200_col].iloc[i] > df_features[ema_50_col].iloc[i]:
                                score += 1
                    trend_scores.append(score / len(ema_200_cols))
                df_features['trend_alignment'] = trend_scores
                
                # RSI divergence: difference between TF RSI values
                rsi_14_cols = [c for c in df_features.columns if 'rsi_14' in c]
                if len(rsi_14_cols) >= 2:
                    base_rsi = df_features['rsi_14'].values if 'rsi_14' in df_features.columns else None
                    if base_rsi is not None:
                        # Calculate average RSI divergence with 4h
                        rsi_4h_col = [c for c in rsi_14_cols if '_4h' in c]
                        if rsi_4h_col:
                            df_features['rsi_divergence_4h'] = df_features[rsi_4h_col[0]].values - base_rsi
        else:
            df_features = pd.DataFrame(all_features)
        
        return df_features

    def _to_feature_set(self, row: pd.Series, symbol: str) -> FeatureSet:
        try:
            return FeatureSet(
                timestamp=row["timestamp"]
                if hasattr(row["timestamp"], "isoformat")
                else row.name,
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
