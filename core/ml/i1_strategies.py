"""
Module: core/ml/i1_strategies.py
Responsibility: I1 strategy registry — signal generators with optimizable params.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np
import pandas as pd

from core.features.indicators import calculate_all
from core.ml.i1_ml_signal import DEFAULT_ML_MODEL_DIR, signal_ml_lgb


@dataclass
class I1StrategySpec:
    strategy_id: str
    param_grid: dict[str, list[Any]]
    signal_fn: Callable[[pd.DataFrame, dict[str, Any]], pd.Series]
    defaults: dict[str, Any] = field(default_factory=dict)


def _ensure_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if "adx_14" in df.columns and "rsi_14" in df.columns:
        return df
    if len(df) < 200:
        return df
    try:
        return calculate_all(df.copy())
    except Exception:
        return df


def signal_ma_cross(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    fast = int(params.get("fast", 10))
    slow = int(params.get("slow", 30))
    f = df["close"].rolling(fast).mean()
    s = df["close"].rolling(slow).mean()
    sig = np.where(f > s, 1, np.where(f < s, -1, 0))
    return pd.Series(sig, index=df.index).fillna(0)


def signal_bb_zscore(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    window = int(params.get("window", 20))
    z_entry = float(params.get("z_entry", 2.0))
    ma = df["close"].rolling(window).mean()
    std = df["close"].rolling(window).std()
    z = (df["close"] - ma) / std.replace(0, np.nan)
    sig = np.where(z < -z_entry, 1, np.where(z > z_entry, -1, 0))
    return pd.Series(sig, index=df.index).fillna(0)


def signal_momentum(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    lookback = int(params.get("lookback", 12))
    ret = df["close"].pct_change()
    mom = np.sign(ret.rolling(lookback).mean()).fillna(0)
    return pd.Series(mom, index=df.index)


def signal_ema_rsi(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    df = _ensure_indicators(df)
    if "ema_9" not in df.columns:
        return pd.Series(0, index=df.index)
    rsi_low = float(params.get("rsi_low", 35))
    rsi_high = float(params.get("rsi_high", 65))
    buy = (df["ema_9"] > df["ema_21"]) & (df["rsi_14"] > rsi_low) & (df["rsi_14"] < rsi_high)
    sell = (df["ema_9"] < df["ema_21"]) & (df["rsi_14"] < (100 - rsi_low)) & (df["rsi_14"] > (100 - rsi_high))
    sig = np.where(buy, 1, np.where(sell, -1, 0))
    return pd.Series(sig, index=df.index).fillna(0)


def signal_mean_reversion(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    df = _ensure_indicators(df)
    if "bb_lower" not in df.columns:
        return signal_bb_zscore(df, params)
    rsi_os = float(params.get("rsi_oversold", 30))
    rsi_ob = float(params.get("rsi_overbought", 70))
    buy = (df["close"] < df["bb_lower"]) & (df["rsi_14"] < rsi_os)
    sell = (df["close"] > df["bb_upper"]) & (df["rsi_14"] > rsi_ob)
    sig = np.where(buy, 1, np.where(sell, -1, 0))
    return pd.Series(sig, index=df.index).fillna(0)


def signal_tsmom(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    lookback = int(params.get("lookback", 12))
    ret = df["close"].pct_change()
    mom = ret.rolling(lookback).sum()
    sig = pd.Series(np.sign(mom).fillna(0), index=df.index)
    if "adx_14" in df.columns:
        sig = sig.where(df["adx_14"] > float(params.get("min_adx", 20)), 0)
    return sig.fillna(0)


def signal_vol_breakout(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    df = _ensure_indicators(df)
    if "atr_14" not in df.columns:
        return pd.Series(0, index=df.index)
    mult = float(params.get("atr_mult", 2.0))
    lookback = int(params.get("lookback", 20))
    high_roll = df["high"].rolling(lookback).max().shift(1)
    low_roll = df["low"].rolling(lookback).min().shift(1)
    buy = df["close"] > high_roll
    sell = df["close"] < low_roll
    sig = np.where(buy, 1, np.where(sell, -1, 0))
    atr_pct = df["atr_14"] / df["close"]
    sig = np.where(atr_pct > atr_pct.rolling(100).median() * 0.5, sig, 0)
    return pd.Series(sig, index=df.index).fillna(0)


I1_STRATEGY_REGISTRY: dict[str, I1StrategySpec] = {
    "MA_10_30": I1StrategySpec(
        "MA_10_30",
        {"fast": [8, 10, 12], "slow": [26, 30, 34]},
        signal_ma_cross,
        {"fast": 10, "slow": 30},
    ),
    "BB_ZScore": I1StrategySpec(
        "BB_ZScore",
        {"window": [15, 20, 25], "z_entry": [1.5, 2.0, 2.5]},
        signal_bb_zscore,
        {"window": 20, "z_entry": 2.0},
    ),
    "Momentum": I1StrategySpec(
        "Momentum",
        {"lookback": [8, 12, 16]},
        signal_momentum,
        {"lookback": 12},
    ),
    "ema_rsi_v1": I1StrategySpec(
        "ema_rsi_v1",
        {"rsi_low": [30, 35], "rsi_high": [65, 70]},
        signal_ema_rsi,
        {"rsi_low": 35, "rsi_high": 65},
    ),
    "mean_rev_v1": I1StrategySpec(
        "mean_rev_v1",
        {"rsi_oversold": [25, 30], "rsi_overbought": [70, 75]},
        signal_mean_reversion,
        {"rsi_oversold": 30, "rsi_overbought": 70},
    ),
    "tsmom_v1": I1StrategySpec(
        "tsmom_v1",
        {"lookback": [10, 12, 24], "min_adx": [18, 22]},
        signal_tsmom,
        {"lookback": 12, "min_adx": 20},
    ),
    "vol_breakout_v1": I1StrategySpec(
        "vol_breakout_v1",
        {"lookback": [15, 20], "atr_mult": [1.5, 2.0]},
        signal_vol_breakout,
        {"lookback": 20, "atr_mult": 2.0},
    ),
    "ml_lgb_v1": I1StrategySpec(
        "ml_lgb_v1",
        {"forward_bars": [6]},
        signal_ml_lgb,
        {"symbol": "", "model_dir": str(DEFAULT_ML_MODEL_DIR), "forward_bars": 6},
    ),
}


def strategies_for_symbol(symbol: str, allowed: list[str] | None = None) -> dict[str, I1StrategySpec]:
    """Return strategy subset; include ML if trained model exists."""
    from core.ml.i1_ml_signal import model_path_for

    keys = allowed if allowed else list(I1_STRATEGY_REGISTRY.keys())
    out = {k: I1_STRATEGY_REGISTRY[k] for k in keys if k in I1_STRATEGY_REGISTRY}
    if model_path_for(symbol).exists() and "ml_lgb_v1" in I1_STRATEGY_REGISTRY:
        out["ml_lgb_v1"] = I1_STRATEGY_REGISTRY["ml_lgb_v1"]
    return out


def iter_param_combinations(spec: I1StrategySpec) -> list[dict[str, Any]]:
    """Cartesian product of param grid (small grids only)."""
    keys = list(spec.param_grid.keys())
    if not keys:
        return [dict(spec.defaults)]
    combos: list[dict[str, Any]] = [{}]
    for key in keys:
        next_combos = []
        for combo in combos:
            for val in spec.param_grid[key]:
                c = dict(combo)
                c[key] = val
                next_combos.append(c)
        combos = next_combos
    return combos
