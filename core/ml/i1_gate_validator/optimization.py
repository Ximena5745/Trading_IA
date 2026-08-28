"""
Module: core/ml/i1_gate_validator/optimization.py
Responsibility: Parameter search for I1 strategies (purged-CV objective, grid or Optuna)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.backtesting.costs import CostModel
from core.backtesting.metrics import sharpe_ratio
from core.ml.i1_gate_validator.config import PERIODS_PER_YEAR_1H, get_asset_config, signal_kwargs
from core.ml.i1_gate_validator.costs import net_returns
from core.ml.i1_gate_validator.params_io import load_saved_params
from core.ml.i1_gate_validator.signal_filters import prepare_signals
from core.ml.i1_strategies import I1StrategySpec, iter_param_combinations
from core.ml.validation import PurgedKFold


def purged_cv_score(
    train_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    params: dict[str, Any],
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
) -> float:
    asset_cfg = asset_cfg or get_asset_config(symbol)
    sig_kw = signal_kwargs(asset_cfg)
    pkf = PurgedKFold(n_splits=5, embargo_bars=5)
    scores: list[float] = []
    n = len(train_df)
    if n < 500:
        return -999.0

    for train_idx, test_idx in pkf.split(np.arange(n)):
        test_df = train_df.iloc[test_idx]
        hist_df = train_df.iloc[: test_idx[-1] + 1]
        sig = prepare_signals(hist_df, spec, params, **sig_kw)
        sig_test = sig.reindex(test_df.index).fillna(0)
        ret = returns.reindex(test_df.index).dropna()
        net = net_returns(ret, sig_test, symbol, cost_model, ref_price)
        if len(net) < 20:
            continue
        scores.append(sharpe_ratio(net.tolist(), periods_per_year=PERIODS_PER_YEAR_1H))
    return float(np.mean(scores)) if scores else -999.0


def optimize_params(
    train_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
    params_dir: Path | None = None,
) -> dict[str, Any]:
    asset_cfg = asset_cfg or get_asset_config(symbol)
    if spec.strategy_id == "ml_lgb_v1":
        p = dict(spec.defaults)
        p["symbol"] = symbol
        return p

    best_params = dict(spec.defaults)
    best_score = -999.0

    saved = load_saved_params(symbol, spec.strategy_id, params_dir)
    candidates: list[dict[str, Any]] = list(iter_param_combinations(spec))
    if saved:
        candidates.insert(0, saved)

    seen: set[str] = set()
    for params in candidates:
        key = json.dumps(params, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        score = purged_cv_score(
            train_df, returns, spec, params, symbol, cost_model, ref_price, asset_cfg
        )
        if score > best_score:
            best_score = score
            best_params = params
    return best_params


def optimize_params_optuna(
    train_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
    n_trials: int = 50,
) -> dict[str, Any]:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    asset_cfg = asset_cfg or get_asset_config(symbol)

    def objective(trial: optuna.Trial) -> float:
        params: dict[str, Any] = {}
        for key, values in spec.param_grid.items():
            if not values:
                continue
            if all(isinstance(v, bool) for v in values):
                params[key] = trial.suggest_categorical(key, values)
            elif all(isinstance(v, int) for v in values) and not isinstance(values[0], bool):
                params[key] = trial.suggest_int(key, int(min(values)), int(max(values)))
            elif all(isinstance(v, (int, float)) for v in values):
                lo, hi = float(min(values)), float(max(values))
                if lo == hi:
                    params[key] = lo
                else:
                    params[key] = trial.suggest_float(key, lo, hi)
            else:
                params[key] = trial.suggest_categorical(key, values)
        return purged_cv_score(
            train_df, returns, spec, params, symbol, cost_model, ref_price, asset_cfg
        )

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    if study.best_trial is not None:
        return dict(study.best_params)
    return dict(spec.defaults)
