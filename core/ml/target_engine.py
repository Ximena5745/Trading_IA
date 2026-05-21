"""
Module: core/ml/target_engine.py
Responsibility: Enhanced target calculation for ML models
M2.5: Target ML optimizado - Dynamic, multi-step, asymmetric, risk-adjusted targets
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Literal


@dataclass
class TargetConfig:
    """Configuración para cálculo de target optimizado."""
    target_type: str = "binary"
    horizon: int = 1
    dynamic_threshold: bool = True
    volatility_window: int = 100
    asymmetric_ratio: float = 1.5
    min_threshold_pct: float = 0.0005
    risk_free_rate: float = 0.0


def calculate_dynamic_threshold(
    returns: pd.Series,
    window: int = 100,
    min_threshold: float = 0.0005,
) -> float:
    """Calcula threshold dinámico basado en desviación estándar de retornos."""
    if len(returns) < window:
        return min_threshold
    recent = returns.tail(window)
    std = recent.std()
    threshold = max(std * 0.5, min_threshold)
    return threshold


def calculate_asymmetric_threshold(
    returns: pd.Series,
    up_ratio: float = 1.5,
    min_threshold: float = 0.0005,
) -> tuple[float, float]:
    """Calcula thresholds asimétricos para señales up vs down."""
    if len(returns) < 2:
        return min_threshold, min_threshold

    up_moves = returns[returns > 0]
    down_moves = abs(returns[returns < 0])

    up_threshold = up_moves.mean() * 0.5 if len(up_moves) > 0 else min_threshold
    down_threshold = down_moves.mean() * 0.5 if len(down_moves) > 0 else min_threshold

    up_threshold = max(up_threshold / up_ratio, min_threshold)
    down_threshold = max(down_threshold * up_ratio, min_threshold)

    return up_threshold, down_threshold


def calculate_volatility_regime(
    returns: pd.Series,
    window: int = 100,
    low_quantile: float = 0.25,
    high_quantile: float = 0.75,
) -> pd.Series:
    """Identifica régimen de volatilidad: low, normal, high."""
    rolling_std = returns.rolling(window).std()
    low_thresh = rolling_std.quantile(low_quantile)
    high_thresh = rolling_std.quantile(high_quantile)

    regime = pd.Series(index=returns.index, data="normal")
    regime = regime.where(rolling_std >= low_thresh, "low")
    regime = regime.where(rolling_std < high_thresh, "high")

    return regime


def build_ternary_training_labels(
    df: pd.DataFrame,
    forward_bars: int = 6,
    atr_col: str = "atr_14",
) -> np.ndarray:
    """
    QWQ-2 / M2.5: Target ternario unificado (0=SELL, 1=HOLD, 2=BUY).
    Zona muerta calibrada con ATR% y percentil 30 de |returns|.
    """
    closes = df["close"].values.astype(float)
    if len(closes) <= forward_bars:
        return np.array([], dtype=np.int32)

    atr = df[atr_col].values.astype(float) if atr_col in df.columns else None
    pct_moves = np.abs(np.diff(closes) / closes[:-1])
    q30 = float(np.nanpercentile(pct_moves, 30)) if len(pct_moves) else 0.0003

    labels: list[int] = []
    for i in range(len(closes) - forward_bars):
        fwd = (closes[i + forward_bars] - closes[i]) / closes[i]
        if atr is not None and closes[i] > 0:
            threshold = max((atr[i] / closes[i]) * q30, 0.0001)
        else:
            threshold = q30
        if fwd > threshold:
            labels.append(2)
        elif fwd < -threshold:
            labels.append(0)
        else:
            labels.append(1)
    return np.array(labels, dtype=np.int32)


def compute_target(
    df: pd.DataFrame,
    config: TargetConfig,
) -> pd.DataFrame:
    """Calcula el target según la configuración especificada."""
    df = df.copy()

    future_return = df['close'].shift(-config.horizon) / df['close'] - 1
    df['future_return'] = future_return

    match config.target_type:
        case "binary":
            df['target'] = (future_return > 0).astype(int)

        case "ternary":
            threshold = config.min_threshold_pct
            if config.dynamic_threshold:
                threshold = calculate_dynamic_threshold(
                    df['close'].pct_change().dropna(),
                    config.volatility_window,
                    config.min_threshold_pct,
                )
            df['target'] = np.where(
                future_return > threshold, 2,
                np.where(future_return < -threshold, 0, 1)
            )

        case "regression":
            df['target'] = future_return

        case "percentile":
            df['target'] = pd.qcut(
                future_return.dropna(),
                q=5,
                labels=False,
                duplicates='drop'
            )

        case "dynamic":
            df['target'] = _dynamic_target(df, config)

        case "multi_step":
            df['target'] = _multi_step_target(df, config)

        case "asymmetric":
            df['target'] = _asymmetric_target(df, config)

        case "risk_adjusted":
            df['target'] = _risk_adjusted_target(df, config)

        case "volatility_regime":
            df['target'] = _volatility_regime_target(df, config)

        case _:
            df['target'] = (future_return > 0).astype(int)

    df = df.drop(columns=['future_return'], errors='ignore')
    return df


def _dynamic_target(df: pd.DataFrame, config: TargetConfig) -> pd.Series:
    """Target con threshold dinámico basado en volatilidad."""
    future_return = df['close'].shift(-config.horizon) / df['close'] - 1
    returns_series = df['close'].pct_change().dropna()

    targets = []
    for i in range(len(df)):
        if i < config.volatility_window:
            threshold = config.min_threshold_pct
        else:
            recent_returns = returns_series.iloc[:i]
            threshold = calculate_dynamic_threshold(
                recent_returns,
                config.volatility_window,
                config.min_threshold_pct,
            )

        if future_return.iloc[i] > threshold:
            targets.append(1)
        elif future_return.iloc[i] < -threshold:
            targets.append(0)
        else:
            targets.append(2)

    return pd.Series(targets, index=df.index)


def _multi_step_target(df: pd.DataFrame, config: TargetConfig) -> pd.Series:
    """Target multi-step: predice retorno acumulado de N barras."""
    horizons = [1, 2, 3, 5] if config.horizon == 1 else [config.horizon]

    multi_return = pd.Series(0.0, index=df.index)
    for h in horizons:
        shift = df['close'].shift(-h)
        ret = shift / df['close'] - 1
        multi_return += ret

    multi_return /= len(horizons)

    threshold = calculate_dynamic_threshold(
        df['close'].pct_change().dropna(),
        config.volatility_window,
        config.min_threshold_pct,
    )

    return np.where(
        multi_return > threshold, 2,
        np.where(multi_return < -threshold, 0, 1)
    )


def _asymmetric_target(df: pd.DataFrame, config: TargetConfig) -> pd.Series:
    """Target con thresholds asimétricos para up vs down."""
    future_return = df['close'].shift(-config.horizon) / df['close'] - 1
    returns_series = df['close'].pct_change().dropna()

    up_thresh, down_thresh = calculate_asymmetric_threshold(
        returns_series,
        config.asymmetric_ratio,
        config.min_threshold_pct,
    )

    return np.where(
        future_return > up_thresh, 2,
        np.where(future_return < -down_thresh, 0, 1)
    )


def _risk_adjusted_target(df: pd.DataFrame, config: TargetConfig) -> pd.Series:
    """Target basado en Sharpe-like return (return / risk)."""
    future_return = df['close'].shift(-config.horizon) / df['close'] - 1

    rolling_return = df['close'].pct_change().rolling(config.volatility_window)
    rolling_std = rolling_return.std()

    sharpe_like = future_return / rolling_std
    median = sharpe_like.median()

    return (sharpe_like > median).astype(int)


def _volatility_regime_target(df: pd.DataFrame, config: TargetConfig) -> pd.Series:
    """Target consciente del régimen de volatilidad."""
    returns = df['close'].pct_change()
    regime = calculate_volatility_regime(returns, config.volatility_window)

    future_return = df['close'].shift(-config.horizon) / df['close'] - 1

    thresholds = {"low": 0.0003, "normal": 0.0005, "high": 0.001}

    targets = []
    for i, (idx, r) in enumerate(regime.items()):
        if pd.isna(future_return.iloc[i]):
            targets.append(1)
        else:
            thresh = thresholds.get(r, config.min_threshold_pct)
            if future_return.iloc[i] > thresh:
                targets.append(2)
            elif future_return.iloc[i] < -thresh:
                targets.append(0)
            else:
                targets.append(1)

    return pd.Series(targets, index=df.index)


def get_available_targets() -> list[str]:
    """Retorna lista de targets disponibles."""
    return [
        "binary",
        "ternary",
        "regression",
        "percentile",
        "dynamic",
        "multi_step",
        "asymmetric",
        "risk_adjusted",
        "volatility_regime",
    ]