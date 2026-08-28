"""
Module: core/ml/i1_gate_validator/signal_filters.py
Responsibility: Post-process raw strategy signals (min-hold, cooldown, regime gate)
"""
from __future__ import annotations

from typing import Any

import pandas as pd

from core.ml.i1_strategies import I1StrategySpec, _ensure_indicators


def apply_min_holding(signals: pd.Series, min_bars: int = 0) -> pd.Series:
    """Enforce minimum bars in each non-zero position before allowing exit/flip."""
    if min_bars <= 0:
        return signals
    arr = signals.fillna(0).astype(float).values.copy()
    current = 0.0
    bars_in_position = 0
    for i in range(len(arr)):
        desired = float(arr[i])
        if desired == current:
            if current != 0:
                bars_in_position += 1
            continue
        if current == 0:
            current = desired
            bars_in_position = 1
        elif bars_in_position >= min_bars:
            current = desired
            bars_in_position = 1 if desired != 0 else 0
        arr[i] = current
    return pd.Series(arr, index=signals.index)


def apply_cooldown(signals: pd.Series, cooldown_bars: int = 3) -> pd.Series:
    arr = signals.fillna(0).astype(float).values.copy()
    current = 0.0
    last_change = -cooldown_bars - 1
    for i in range(len(arr)):
        desired = float(arr[i])
        if desired != current:
            if i - last_change >= cooldown_bars:
                current = desired
                last_change = i
        arr[i] = current
    return pd.Series(arr, index=signals.index)


def apply_regime_filter(signals: pd.Series, df: pd.DataFrame, min_adx: float = 20.0) -> pd.Series:
    df = _ensure_indicators(df)
    if "adx_14" not in df.columns:
        return signals
    tradable = df["adx_14"] >= min_adx
    return signals.where(tradable.reindex(signals.index).fillna(False), 0)


def prepare_signals(
    df: pd.DataFrame,
    spec: I1StrategySpec,
    params: dict[str, Any],
    *,
    cooldown: int = 3,
    min_hold_bars: int = 0,
    min_adx: float = 20.0,
    regime_filter: bool = True,
    raw_override: pd.Series | None = None,
) -> pd.Series:
    if raw_override is not None:
        raw = raw_override
    else:
        merged = {**spec.defaults, **params}
        raw = spec.signal_fn(df, merged)
    if regime_filter:
        raw = apply_regime_filter(raw, df, min_adx=min_adx)
    if min_hold_bars > 0:
        raw = apply_min_holding(raw, min_hold_bars)
    if cooldown > 0:
        raw = apply_cooldown(raw, cooldown)
    return raw.fillna(0)
