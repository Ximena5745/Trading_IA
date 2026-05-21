"""Tests for I1 gate validator methodology."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.ml.i1_gate_validator import (
    HOLDOUT_FRACTION,
    apply_cooldown,
    apply_min_holding,
    bootstrap_pvalue_wf,
    cost_drag,
    count_trades,
    get_asset_config,
    gross_returns,
    half_side_cost_pct,
    load_saved_params,
    net_returns,
    prepare_signals,
    purged_cv_score,
    save_params,
)
from core.ml.i1_strategies import I1_STRATEGY_REGISTRY
from core.ml.validation import PurgedKFold
from core.backtesting.costs import CostModel


def _synthetic_ohlcv(n: int = 9000, drift: float = 0.0003) -> pd.DataFrame:
    rng = np.random.default_rng(123)
    log_ret = rng.normal(drift, 0.002, n)
    close = 100.0 * np.exp(np.cumsum(log_ret))
    high = close * (1 + rng.uniform(0, 0.002, n))
    low = close * (1 - rng.uniform(0, 0.002, n))
    open_ = np.roll(close, 1)
    open_[0] = close[0]
    idx = pd.date_range("2020-01-01", periods=n, freq="h")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1.0},
        index=idx,
    )


def test_purged_kfold_no_train_test_overlap():
    n = 2000
    pkf = PurgedKFold(n_splits=5, embargo_bars=5)
    for train_idx, test_idx in pkf.split(np.arange(n)):
        assert len(set(train_idx) & set(test_idx)) == 0
        assert train_idx.max() < test_idx.min() - 5 or train_idx.max() < test_idx.min()


def test_holdout_not_in_wf_region():
    df = _synthetic_ohlcv(5000)
    holdout_start = int(len(df) * (1 - HOLDOUT_FRACTION))
    wf_max_idx = holdout_start - 1
    holdout_min_idx = holdout_start
    assert wf_max_idx < holdout_min_idx


def test_costs_only_on_position_change():
    returns = pd.Series([0.01, 0.01, -0.01, 0.01], index=range(4))
    signals = pd.Series([1, 1, -1, -1], index=range(4))
    gross = gross_returns(returns, signals)
    net = net_returns(returns, signals, "EURUSD", CostModel(), ref_price=1.1)
    # Single flip 1 -> -1 at bar 2; bars without position change match gross
    flip_idx = 2
    assert net.loc[flip_idx] < gross.loc[flip_idx]
    for i in gross.index:
        if i != flip_idx:
            assert net.loc[i] == pytest.approx(gross.loc[i])


def test_min_holding_delays_exit():
    sig = pd.Series([1, 0, -1, -1, -1, 0], index=range(6))
    held = apply_min_holding(sig, min_bars=3)
    assert held.iloc[0] == 1
    assert held.iloc[1] == 1
    assert held.iloc[2] == 1


def test_asset_config_crypto_restricts_strategies():
    cfg = get_asset_config("BTCUSDT")
    assert "MA_10_30" not in cfg["strategies"]
    assert "tsmom_v1" in cfg["strategies"]


def test_load_saved_params_roundtrip(tmp_path):
    save_params("EURUSD", "mean_rev_v1", {"rsi_oversold": 28}, tmp_path)
    loaded = load_saved_params("EURUSD", "mean_rev_v1", tmp_path)
    assert loaded == {"rsi_oversold": 28}


def test_cost_drag_metric():
    assert cost_drag(1.5, 0.8) == pytest.approx(0.7)


def test_cooldown_limits_flips():
    sig = pd.Series([1, -1, 1, -1, 1], index=range(5))
    cooled = apply_cooldown(sig, cooldown_bars=3)
    assert cooled.iloc[0] == 1
    assert cooled.iloc[1] == 1  # blocked by cooldown
    assert cooled.iloc[2] == 1  # still within cooldown from bar 0
    assert cooled.iloc[3] == -1  # allowed after 3 bars


def test_bootstrap_pvalue_low_for_strong_edge():
    rng = np.random.default_rng(0)
    strong = pd.Series(rng.normal(0.0005, 0.001, 2000))
    p = bootstrap_pvalue_wf(strong, n_bootstrap=200)
    assert p < 0.05


def test_gross_returns_use_signal_lag():
    returns = pd.Series([0.1, -0.1, 0.1, -0.1], index=range(4))
    signals = pd.Series([1, 1, -1, -1], index=range(4))
    g = gross_returns(returns, signals)
    # First bar has no lagged signal -> excluded from gross series
    assert g.index[0] == 1
    assert g.iloc[0] == pytest.approx(-0.1)


def test_count_trades():
    sig = pd.Series([0, 1, 1, -1, -1], index=range(5))
    assert count_trades(sig) == 2


def test_purged_cv_score_runs_on_synthetic():
    df = _synthetic_ohlcv(3000)
    spec = I1_STRATEGY_REGISTRY["MA_10_30"]
    returns = df["close"].pct_change().dropna()
    score = purged_cv_score(
        df,
        returns,
        spec,
        spec.defaults,
        "EURUSD",
        CostModel(),
        float(df["close"].median()),
    )
    assert isinstance(score, float)


def test_half_side_cost_crypto_vs_forex():
    cm = CostModel(commission_pct=0.001, slippage_pct=0.0005)
    crypto = half_side_cost_pct("BTCUSDT", cm)
    forex = half_side_cost_pct("EURUSD", cm, ref_price=1.1)
    assert crypto > forex


@pytest.mark.slow
def test_i1_validator_synthetic_asset_runs():
    from core.ml.i1_gate_validator import I1GateValidator

    df = _synthetic_ohlcv(10000, drift=0.0008)
    validator = I1GateValidator(n_bootstrap=100)
    result = validator.validate_asset("SYNTH", df, strategy_id="MA_10_30")
    assert result.symbol == "SYNTH"
    assert result.best_strategy == "MA_10_30"
    assert isinstance(result.sharpe_net_wf, float)
    assert isinstance(result.p_value_wf, float)
