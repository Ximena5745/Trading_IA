"""
Module: core/features/indicators.py
Responsibility: Calculate all 17 required technical indicators
Dependencies: pandas, pandas-ta, numpy
"""
from __future__ import annotations

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    ta = None  # type: ignore

from core.exceptions import FeatureCalculationError
from core.observability.logger import get_logger

logger = get_logger(__name__)

REQUIRED_INDICATORS = [
    "rsi_14", "rsi_7",
    "ema_9", "ema_21", "ema_50", "ema_200",
    "macd_line", "macd_signal", "macd_histogram",
    "atr_14",
    "bb_upper", "bb_lower", "bb_width",
    "vwap", "volume_ratio", "obv",
    "trend_direction", "volatility_regime",
]

MIN_CANDLES = 200
MAX_NAN_PCT = 0.05


def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all required indicators on an OHLCV DataFrame.
    Columns expected: open, high, low, close, volume, quote_volume, taker_buy_volume
    Returns enriched DataFrame with all indicator columns.
    """
    if len(df) < MIN_CANDLES:
        raise FeatureCalculationError(
            f"Need at least {MIN_CANDLES} candles, got {len(df)}"
        )

    df = df.copy()
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["close"] = df["close"].astype(float)
    df["high"] = df["high"].astype(float)
    df["low"] = df["low"].astype(float)
    df["open"] = df["open"].astype(float)
    df["volume"] = df["volume"].astype(float)

    df = _calc_rsi(df)
    df = _calc_ema(df)
    df = _calc_macd(df)
    df = _calc_atr(df)
    df = _calc_bollinger(df)
    df = _calc_volume_indicators(df)
    df = _calc_trend_direction(df)
    df = _calc_volatility_regime(df)

    _validate_nan(df)
    return df


def _calc_rsi(df: pd.DataFrame) -> pd.DataFrame:
    if ta:
        df["rsi_14"] = ta.rsi(df["close"], length=14)
        df["rsi_7"] = ta.rsi(df["close"], length=7)
    else:
        df["rsi_14"] = _rsi_manual(df["close"], 14)
        df["rsi_7"] = _rsi_manual(df["close"], 7)
    return df


def _calc_ema(df: pd.DataFrame) -> pd.DataFrame:
    for period in (9, 21, 50, 200):
        col = f"ema_{period}"
        if ta:
            df[col] = ta.ema(df["close"], length=period)
        else:
            df[col] = df["close"].ewm(span=period, adjust=False).mean()
    return df


def _calc_macd(df: pd.DataFrame) -> pd.DataFrame:
    if ta:
        macd = ta.macd(df["close"], fast=12, slow=26, signal=9)
        df["macd_line"] = macd["MACD_12_26_9"]
        df["macd_signal"] = macd["MACDs_12_26_9"]
        df["macd_histogram"] = macd["MACDh_12_26_9"]
    else:
        ema12 = df["close"].ewm(span=12, adjust=False).mean()
        ema26 = df["close"].ewm(span=26, adjust=False).mean()
        df["macd_line"] = ema12 - ema26
        df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False).mean()
        df["macd_histogram"] = df["macd_line"] - df["macd_signal"]
    return df


def _calc_atr(df: pd.DataFrame) -> pd.DataFrame:
    if ta:
        df["atr_14"] = ta.atr(df["high"], df["low"], df["close"], length=14)
    else:
        hl = df["high"] - df["low"]
        hc = (df["high"] - df["close"].shift(1)).abs()
        lc = (df["low"] - df["close"].shift(1)).abs()
        tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        df["atr_14"] = tr.ewm(span=14, adjust=False).mean()
    return df


def _calc_bollinger(df: pd.DataFrame) -> pd.DataFrame:
    if ta:
        bb = ta.bbands(df["close"], length=20, std=2)
        df["bb_upper"] = bb["BBU_20_2.0"]
        df["bb_lower"] = bb["BBL_20_2.0"]
    else:
        sma20 = df["close"].rolling(20).mean()
        std20 = df["close"].rolling(20).std()
        df["bb_upper"] = sma20 + 2 * std20
        df["bb_lower"] = sma20 - 2 * std20
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["close"]
    return df


def _calc_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # VWAP (rolling daily approximation)
    df["vwap"] = (df["close"] * df["volume"]).rolling(20).sum() / df["volume"].rolling(20).sum()

    df["volume_sma_20"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"].replace(0, np.nan)

    # OBV
    obv = [0.0]
    for i in range(1, len(df)):
        if df["close"].iloc[i] > df["close"].iloc[i - 1]:
            obv.append(obv[-1] + df["volume"].iloc[i])
        elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
            obv.append(obv[-1] - df["volume"].iloc[i])
        else:
            obv.append(obv[-1])
    df["obv"] = obv
    return df


def _calc_trend_direction(df: pd.DataFrame) -> pd.DataFrame:
    def trend(row: pd.Series) -> str:
        if row["ema_50"] > row["ema_200"] and row["close"] > row["ema_50"]:
            return "bullish"
        if row["ema_50"] < row["ema_200"] and row["close"] < row["ema_50"]:
            return "bearish"
        return "sideways"

    df["trend_direction"] = df.apply(trend, axis=1)
    return df


def _calc_volatility_regime(df: pd.DataFrame) -> pd.DataFrame:
    atr_pct = df["atr_14"] / df["close"]
    q25 = atr_pct.quantile(0.25)
    q75 = atr_pct.quantile(0.75)
    q90 = atr_pct.quantile(0.90)

    def regime(v: float) -> str:
        if v <= q25:
            return "low"
        if v <= q75:
            return "medium"
        if v <= q90:
            return "high"
        return "extreme"

    df["volatility_regime"] = atr_pct.apply(regime)
    return df


def _validate_nan(df: pd.DataFrame) -> None:
    critical = ["rsi_14", "ema_50", "ema_200", "atr_14", "macd_line"]
    last_100 = df.tail(100)
    for col in critical:
        if col in last_100.columns:
            nan_pct = last_100[col].isna().mean()
            if nan_pct > MAX_NAN_PCT:
                raise FeatureCalculationError(
                    f"Too many NaN in {col}: {nan_pct:.1%} > {MAX_NAN_PCT:.1%}"
                )


def _rsi_manual(series: pd.Series, period: int) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))
