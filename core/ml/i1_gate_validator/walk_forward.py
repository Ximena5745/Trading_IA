"""
Module: core/ml/i1_gate_validator/walk_forward.py
Responsibility: Walk-forward out-of-sample evaluation of one strategy
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.backtesting.costs import CostModel
from core.backtesting.metrics import sharpe_ratio
from core.ml.i1_gate_validator.config import PERIODS_PER_YEAR_1H, get_asset_config, signal_kwargs
from core.ml.i1_gate_validator.costs import gross_returns, net_returns
from core.ml.i1_gate_validator.optimization import optimize_params
from core.ml.i1_gate_validator.signal_filters import prepare_signals
from core.ml.i1_gate_validator.windows import iter_wf_windows
from core.ml.i1_strategies import I1StrategySpec


def evaluate_strategy_wf(
    wf_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
    params_dir: Path | None = None,
) -> tuple[pd.Series, pd.Series, list[dict[str, Any]], dict[str, Any]]:
    asset_cfg = asset_cfg or get_asset_config(symbol)
    sig_kw = signal_kwargs(asset_cfg)
    windows = iter_wf_windows(len(wf_df))
    oos_gross_parts: list[pd.Series] = []
    oos_net_parts: list[pd.Series] = []
    window_meta: list[dict[str, Any]] = []
    last_params: dict[str, Any] = dict(spec.defaults)

    for w in windows:
        train_df = wf_df.iloc[w["train_start"] : w["train_end"]]
        test_df = wf_df.iloc[w["test_start"] : w["test_end"]]
        train_ret = returns.reindex(train_df.index)
        hist = wf_df.iloc[: w["test_end"]]

        if spec.strategy_id == "ml_lgb_v1":
            # Genuine walk-forward: retrain per window on train_df only (never
            # on test_df) instead of reusing one model fit on the whole WF
            # slice — otherwise every WF test window is in-sample for the model.
            from core.ml.i1_ml_signal import fit_model_in_memory, predict_signals_from_bundle

            forward_bars = int(spec.defaults.get("forward_bars", 6))
            bundle = fit_model_in_memory(train_df, forward_bars=forward_bars)
            last_params = {"symbol": symbol, "forward_bars": forward_bars}
            if bundle is None:
                continue
            raw_sig = predict_signals_from_bundle(hist, bundle)
            sig = prepare_signals(hist, spec, last_params, **sig_kw, raw_override=raw_sig)
        else:
            last_params = optimize_params(
                train_df,
                train_ret,
                spec,
                symbol,
                cost_model,
                ref_price,
                asset_cfg,
                params_dir,
            )
            sig = prepare_signals(hist, spec, last_params, **sig_kw)

        sig_test = sig.reindex(test_df.index).fillna(0)
        ret_test = returns.reindex(test_df.index).dropna()

        g = gross_returns(ret_test, sig_test)
        n = net_returns(ret_test, sig_test, symbol, cost_model, ref_price)
        oos_gross_parts.append(g)
        oos_net_parts.append(n)
        window_meta.append(
            {
                **w,
                "params": dict(last_params),
                "sharpe_net": sharpe_ratio(n.tolist(), periods_per_year=PERIODS_PER_YEAR_1H),
            }
        )

    if not oos_net_parts:
        return pd.Series(dtype=float), pd.Series(dtype=float), window_meta, last_params

    gross_concat = pd.concat(oos_gross_parts)
    net_concat = pd.concat(oos_net_parts)
    return gross_concat, net_concat, window_meta, last_params
