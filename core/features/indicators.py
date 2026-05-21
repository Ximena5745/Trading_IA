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
    "rsi_14",
    "rsi_7",
    "ema_9",
    "ema_21",
    "ema_50",
    "ema_200",
    "macd_line",
    "macd_signal",
    "macd_histogram",
    "atr_14",
    "bb_upper",
    "bb_lower",
    "bb_width",
    "bb_pct_b",
    "bb_bandwidth",
    "vwap",
    "volume_ratio",
    "obv",
    "trend_direction",
    "trend_score",
    "volatility_regime",
    "ret_1",
    "ret_3",
    "ret_6",
    "ret_12",
    "ret_24",
    "adx_14",
    "vol_adj_ret",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "is_london_session",
    "is_new_york_session",
    "is_overlap_session",
    "is_weekend",
    "hurst_exponent",
    "rolling_kurtosis",
    "rolling_skewness",
    "autocorr_lag1",
    "autocorr_lag2",
    "autocorr_lag3",
    "z_score_vs_ma20",
    "volume_price_corr",
    "volume_imbalance",
    "returns_autocorr",
    "rolling_sharpe_20",
    "rolling_sharpe_50",
    "rolling_sharpe_100",
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
    df = _calc_returns(df)
    df = _calc_adx(df)
    df = _calc_vol_adj_returns(df)
    df = _calc_temporal_features(df)
    df = calculate_advanced_features(df)

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

    # Bollinger Band additional metrics
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["close"]

    # %B: posición del precio dentro de las bandas (0=lower, 1=upper)
    bb_range = df["bb_upper"] - df["bb_lower"]
    df["bb_pct_b"] = np.where(
        bb_range > 0,
        (df["close"] - df["bb_lower"]) / bb_range,
        0.5
    )

    # Bandwidth normalizado
    sma20 = df["close"].rolling(20).mean()
    df["bb_bandwidth"] = np.where(
        sma20 > 0,
        (df["bb_upper"] - df["bb_lower"]) / sma20,
        0
    )

    return df


def _calc_volume_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # M2.1.1: VWAP con reset diario (no rolling 20)
    # Usamos típico precio y volumen累积
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()

    # Reset diario basado en hora (para datos 1h, detectamos nuevo día)
    if "timestamp" in df.columns:
        day_change = df["timestamp"].dt.date != df["timestamp"].dt.date.shift(1)
        df.loc[day_change, "vwap"] = np.nan
        df["vwap"] = df["vwap"].ffill()

    df["volume_sma_20"] = df["volume"].rolling(20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"].replace(0, np.nan)

    # M2.1.2: OBV vectorizado con numpy (eliminar loop O(n))
    close_diff = np.diff(df["close"].values, prepend=df["close"].iloc[0])
    volume = df["volume"].values
    obv_direction = np.sign(close_diff)
    df["obv"] = np.cumsum(obv_direction * volume)

    return df


def _calc_trend_direction(df: pd.DataFrame) -> pd.DataFrame:
    # M2.1.4: Trend direction con score numérico + categoría
    # Score: +1 bullish, -1 bearish, 0 sideways

    ema_50 = df["ema_50"]
    ema_200 = df["ema_200"]
    close = df["close"]

    # Calcular score numérico
    trend_score = np.zeros(len(df))

    # EMA 50 vs EMA 200
    trend_score += np.where(ema_50 > ema_200, 0.5, -0.5)

    # Close vs EMA 50
    trend_score += np.where(close > ema_50, 0.5, -0.5)

    # Distancia de close a EMAs (fuerza de tendencia)
    distance = (close - ema_50) / close
    trend_score += np.clip(distance * 10, -0.5, 0.5)

    df["trend_score"] = trend_score

    # Categoría basada en score
    def categorize(score: float) -> str:
        if score > 0.3:
            return "bullish"
        if score < -0.3:
            return "bearish"
        return "sideways"

    df["trend_direction"] = df["trend_score"].apply(categorize)
    return df


def _calc_volatility_regime(df: pd.DataFrame) -> pd.DataFrame:
    # M2.1.3: Volatility regime con quantiles rolling (evita look-ahead bias)
    atr_pct = df["atr_14"] / df["close"]
    window = 100

    q25 = atr_pct.rolling(window, min_periods=20).quantile(0.25)
    q75 = atr_pct.rolling(window, min_periods=20).quantile(0.75)
    q90 = atr_pct.rolling(window, min_periods=20).quantile(0.90)

    regimes = []
    for i in range(len(df)):
        v = atr_pct.iloc[i]
        q25_v = q25.iloc[i]
        q75_v = q75.iloc[i]
        q90_v = q90.iloc[i]

        if pd.isna(q25_v):
            regimes.append("medium")
        elif v <= q25_v:
            regimes.append("low")
        elif v <= q75_v:
            regimes.append("medium")
        elif v <= q90_v:
            regimes.append("high")
        else:
            regimes.append("extreme")

    df["volatility_regime"] = regimes
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


def _calc_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate lagged returns over N periods."""
    for periods in [1, 3, 6, 12, 24]:
        df[f"ret_{periods}"] = df["close"].pct_change(periods)
    return df


def _calc_adx(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate ADX (Average Directional Index) for trend strength."""
    high, low, close = df["high"], df["low"], df["close"]

    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0

    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_14 = tr.ewm(span=14, adjust=False).mean()

    plus_di = 100 * (plus_dm.ewm(span=14, adjust=False).mean() / atr_14)
    minus_di = 100 * (minus_dm.ewm(span=14, adjust=False).mean() / atr_14)

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    df["adx_14"] = dx.ewm(span=14, adjust=False).mean()
    return df


def _calc_vol_adj_returns(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate volatility-adjusted returns (return / ATR)."""
    if "atr_14" in df.columns:
        df["vol_adj_ret"] = df["ret_1"] / (df["atr_14"] / df["close"]).replace(0, np.nan)
    return df


def _calc_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """M2.1.5: Features temporales cíclicas y sesiones de mercado."""
    if "timestamp" not in df.columns:
        return df

    ts = df["timestamp"]

    # Features cíclicas de hora (periodo 24h)
    hour = ts.dt.hour
    df["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    # Features cíclicas de día de semana (periodo 7 días)
    dow = ts.dt.dayofweek
    df["day_of_week_sin"] = np.sin(2 * np.pi * dow / 7)
    df["day_of_week_cos"] = np.cos(2 * np.pi * dow / 7)

    # Sesiones de mercado (UTC)
    # London: 8:00-16:00 UTC
    # New York: 13:00-21:00 UTC
    # Overlap: 13:00-16:00 UTC
    df["is_london_session"] = ((hour >= 8) & (hour < 16)).astype(int)
    df["is_new_york_session"] = ((hour >= 13) & (hour < 21)).astype(int)
    df["is_overlap_session"] = ((hour >= 13) & (hour < 16)).astype(int)

    # Fin de semana (crypto sigue operando pero forex no)
    df["is_weekend"] = (dow >= 5).astype(int)

    return df


def calculate_advanced_features(df: pd.DataFrame) -> pd.DataFrame:
    """M2.1 (extended): Advanced features with documented edge.

    Features based on quantitative finance literature:
    - Hurst Exponent: Mean-reversion vs momentum detection
    - Rolling Kurtosis: Tail risk detection
    - Rolling Skewness: Asymmetry detection
    - Autocorrelation: Pattern detection
    - Z-Score: Mean reversion signal
    - Volume-Price Correlation: Smart money detection
    """
    if "close" not in df.columns:
        return df

    close = df["close"]

    df["hurst_exponent"] = _calculate_hurst(close, window=100)

    pct = close.pct_change()
    for window, col in ((20, "rolling_sharpe_20"), (50, "rolling_sharpe_50"), (100, "rolling_sharpe_100")):
        mean_r = pct.rolling(window).mean()
        std_r = pct.rolling(window).std()
        df[col] = (mean_r / std_r.replace(0, np.nan) * np.sqrt(252 * 24)).fillna(0)

    returns = close.pct_change().rolling(20)
    df["rolling_kurtosis"] = returns.apply(lambda x: x.kurtosis() if len(x) > 3 else 0, raw=False)
    df["rolling_kurtosis"] = df["rolling_kurtosis"].fillna(0)

    df["rolling_skewness"] = returns.apply(lambda x: x.skew() if len(x) > 2 else 0, raw=False)
    df["rolling_skewness"] = df["rolling_skewness"].fillna(0)

    for lag in range(1, 6):
        df[f"autocorr_lag{lag}"] = close.pct_change().rolling(20).apply(
            lambda x: x.autocorr(lag=lag) if len(x) > lag else 0,
            raw=False
        )

    rolling_mean = close.rolling(20).mean()
    rolling_std = close.rolling(20).std()
    df["z_score_vs_ma20"] = (close - rolling_mean) / rolling_std
    df["z_score_vs_ma20"] = df["z_score_vs_ma20"].fillna(0)

    if "volume" in df.columns:
        volume = df["volume"]
        corr_values = []
        for i in range(len(close)):
            if i < 20:
                corr_values.append(0)
            else:
                c = close.iloc[i-20:i].corr(volume.iloc[i-20:i])
                corr_values.append(c if not pd.isna(c) else 0)
        df["volume_price_corr"] = corr_values

        df["volume_imbalance"] = _calculate_volume_imbalance(df)

    df["returns_autocorr"] = close.pct_change().rolling(10).apply(
        lambda x: x.autocorr(lag=1) if len(x) > 1 else 0,
        raw=False
    )

    return df


def _calculate_hurst(series: pd.Series, window: int = 100) -> pd.Series:
    """Calculate Hurst exponent using R/S method.

    H < 0.5: Mean-reverting
    H = 0.5: Random walk
    H > 0.5: Trending
    """
    hurst_values = []

    for i in range(window, len(series)):
        sub_series = series.iloc[i-window:i]
        n = len(sub_series)

        mean = sub_series.mean()
        cumdev = (sub_series - mean).cumsum()
        R = cumdev.max() - cumdev.min()
        S = sub_series.std()

        if S > 0:
            RS = R / S
            hurst = np.log(RS) / np.log(n)
        else:
            hurst = 0.5

        hurst_values.append(hurst)

    result = pd.Series([0.5] * window + hurst_values, index=series.index)
    return result


def _calculate_volume_imbalance(df: pd.DataFrame) -> pd.Series:
    """Calculate volume imbalance (up volume vs down volume)."""
    if "volume" not in df.columns or "close" not in df.columns:
        return pd.Series(0, index=df.index)

    returns = df["close"].diff()
    up_volume = df["volume"] * (returns > 0).astype(float)
    down_volume = df["volume"] * (returns < 0).astype(float)

    up_ma = up_volume.rolling(20).mean()
    down_ma = down_volume.rolling(20).mean()

    imbalance = (up_ma - down_ma) / (up_ma + down_ma + 1e-10)
    return imbalance.fillna(0)
