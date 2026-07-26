"""
Module: core/ml/i1_ml_signal.py
Responsibility: Per-symbol LightGBM signals for I1 gate (fallback when rule-based fails).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pickle

import numpy as np
import pandas as pd

from core.features.indicators import calculate_all
from core.ml.target_engine import build_ternary_training_labels
from core.observability.logger import get_logger

logger = get_logger(__name__)

DEFAULT_ML_MODEL_DIR = Path("data/models/i1_ml")
OHLCV_COLS = {"open", "high", "low", "close", "volume", "timestamp", "symbol"}


def model_path_for(symbol: str, base_dir: Path | None = None) -> Path:
    base = base_dir or DEFAULT_ML_MODEL_DIR
    return base / f"{symbol.upper()}_lgb.joblib"


def _feature_matrix(df: pd.DataFrame) -> pd.DataFrame:
    cols = [
        c
        for c in df.columns
        if c not in OHLCV_COLS
        and not c.startswith("target")
        and pd.api.types.is_numeric_dtype(df[c])
    ]
    return df[cols].replace([np.inf, -np.inf], np.nan).fillna(0)


def _is_enriched(df: pd.DataFrame) -> bool:
    return "adx_14" in df.columns and "rsi_14" in df.columns and "atr_14" in df.columns


def fit_model_in_memory(
    df: pd.DataFrame,
    *,
    forward_bars: int = 6,
    min_rows: int = 500,
) -> dict[str, Any] | None:
    """Train LightGBM ternary classifier on `df` only, no persistence.

    Returns None (instead of raising) when there is not enough data —
    callers doing per-window walk-forward training expect to skip early
    windows rather than abort the whole run.

    If `df` already carries indicator columns (as produced upstream by
    `core.features.indicators.calculate_all`), skips recomputing them —
    critical for walk-forward loops that call this once per window:
    recomputing indicators on each truncated window slice is both wasteful
    and less correct (rolling indicators lose real warm-up history).
    """
    import lightgbm as lgb

    enriched = df if _is_enriched(df) else calculate_all(df.copy())
    labels = build_ternary_training_labels(enriched, forward_bars=forward_bars)
    if len(labels) < min_rows:
        return None

    n = len(labels)
    X = _feature_matrix(enriched.iloc[:n])
    y = labels.astype(int)

    model = lgb.LGBMClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=50,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(X, y)

    return {
        "model": model,
        "feature_columns": list(X.columns),
        "forward_bars": forward_bars,
    }


def predict_signals_from_bundle(df: pd.DataFrame, bundle: dict[str, Any]) -> pd.Series:
    """Map model output {0,1,2} -> signals {-1,0,1} using an in-memory bundle."""
    model = bundle["model"]
    feature_columns: list[str] = bundle["feature_columns"]

    enriched = df if _is_enriched(df) else calculate_all(df.copy())
    X = _feature_matrix(enriched).reindex(columns=feature_columns, fill_value=0)
    preds = model.predict(X)

    sig = pd.Series(0, index=df.index, dtype=float)
    sig.iloc[: len(preds)] = np.where(
        preds == 2, 1.0, np.where(preds == 0, -1.0, 0.0)
    )
    return sig


def train_ml_signal_model(
    df: pd.DataFrame,
    symbol: str,
    *,
    forward_bars: int = 6,
    model_dir: Path | None = None,
) -> Path:
    """Train LightGBM ternary classifier and persist joblib bundle."""
    bundle = fit_model_in_memory(df, forward_bars=forward_bars)
    if bundle is None:
        raise ValueError(f"Insufficient labeled rows for {symbol}")

    out = model_path_for(symbol, model_dir)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("wb") as f:
        pickle.dump({**bundle, "symbol": symbol.upper()}, f)
    logger.info("i1_ml_model_saved", symbol=symbol, path=str(out))
    return out


def predict_signals(
    df: pd.DataFrame,
    symbol: str,
    model_dir: Path | None = None,
) -> pd.Series:
    """Map model output {0,1,2} -> signals {-1,0,1} using the persisted model."""
    path = model_path_for(symbol, model_dir)
    if not path.exists():
        return pd.Series(0, index=df.index)

    with path.open("rb") as f:
        bundle = pickle.load(f)
    return predict_signals_from_bundle(df, bundle)


def signal_ml_lgb(df: pd.DataFrame, params: dict[str, Any]) -> pd.Series:
    symbol = params.get("symbol", "")
    model_dir = Path(params.get("model_dir", DEFAULT_ML_MODEL_DIR))
    return predict_signals(df, symbol, model_dir)
