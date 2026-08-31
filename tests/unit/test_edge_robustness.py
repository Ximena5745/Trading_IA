"""
F2.6 / SPEC-C02 — edge robustness battery. Unit-level checks on the pure
analytical helpers with synthetic series; the full per-asset run is exercised
by the script against data/models/i1_params/<SYMBOL>.json.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.backtesting.costs import CostModel
from scripts.run_edge_robustness import (
    _COST_FACTORS,
    _block_bootstrap_sharpe,
    _cost_sweep,
    _net_with_cost_mult,
)


def _pos_drift_series(n=4000, seed=0):
    rng = np.random.default_rng(seed)
    r = pd.Series(rng.normal(0.0004, 0.01, n))
    s = pd.Series(np.ones(n))  # always long
    return r, s


def test_block_bootstrap_shape_and_determinism():
    rng = np.random.default_rng(1)
    net = rng.normal(0.0005, 0.01, 3000)
    a = _block_bootstrap_sharpe(net, n_paths=200, block=24, seed=42)
    b = _block_bootstrap_sharpe(net, n_paths=200, block=24, seed=42)
    assert a["status"] == "ok"
    assert a == b  # fixed seed -> identical
    assert a["ci95_lower"] <= a["percentiles"]["50"] <= a["ci95_upper"]
    assert 0.0 <= a["prob_positive"] <= 1.0


def test_block_bootstrap_guards_short_series():
    out = _block_bootstrap_sharpe(np.zeros(30), n_paths=100, block=24, seed=42)
    assert out["status"] == "insufficient_data"


def test_cost_sweep_monotonic_non_increasing_sharpe():
    r, s = _pos_drift_series()
    sweep = _cost_sweep(r, s, "XAUUSD", CostModel(), ref_price=2000.0)
    sharpes = [row["sharpe_net"] for row in sweep["by_factor"]]
    assert [row["factor"] for row in sweep["by_factor"]] == _COST_FACTORS
    # higher cost multiplier never improves net Sharpe
    assert all(b <= a + 1e-9 for a, b in zip(sharpes, sharpes[1:]))


def test_net_with_cost_mult_scales_costs():
    r, s = _pos_drift_series()
    # a flip every other bar so there is turnover to be charged
    s = pd.Series(np.tile([1.0, -1.0], len(r) // 2))
    n1 = _net_with_cost_mult(r, s, "XAUUSD", CostModel(), 2000.0, 1.0)
    n3 = _net_with_cost_mult(r, s, "XAUUSD", CostModel(), 2000.0, 3.0)
    assert n3.sum() < n1.sum()  # more cost -> less net


def test_cost_sweep_nullification_factor_is_ordered():
    r, s = _pos_drift_series()
    sweep = _cost_sweep(r, s, "XAUUSD", CostModel(), ref_price=2000.0)
    nz = sweep["nullification_factor_zero"]
    ng = sweep["nullification_factor_gate"]
    if nz is not None and ng is not None:
        assert ng <= nz  # crosses the gate threshold before it crosses zero
