"""
F2.5 / SPEC-C01 — consolidated quant report generator.
Unit-level checks on the pure helpers; the full run is exercised via the script
(and cross-checked against data/reports/i1_gate_report.json when data is present).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.run_quant_report import _metrics, _split_trades, _tail_ratio


def test_split_trades_groups_consecutive_same_sign():
    idx = pd.RangeIndex(8)
    net = pd.Series([0.0, 0.01, 0.02, 0.0, -0.01, -0.02, 0.0, 0.03], index=idx)
    sig = pd.Series([0, 1, 1, 0, -1, -1, 0, 1], index=idx)
    trades = _split_trades(net, sig)
    assert [round(t["net_pnl"], 4) for t in trades] == [0.03, -0.03, 0.03]


def test_tail_ratio_guarded():
    assert _tail_ratio(pd.Series([0.0] * 5)) == 0.0  # too few
    r = pd.Series(np.concatenate([np.full(60, 0.01), np.full(60, -0.005)]))
    assert _tail_ratio(r) > 0


def test_metrics_bundle_shape():
    rng = np.random.default_rng(0)
    net = pd.Series(rng.normal(0.0002, 0.01, 500))
    sig = pd.Series(np.where(rng.random(500) > 0.5, 1, 0))
    m = _metrics(net, net, sig)
    for k in (
        "sharpe_net", "sharpe_gross", "sortino_net", "calmar", "expectancy",
        "profit_factor", "win_rate", "max_drawdown", "exposure",
        "turnover_per_year", "cost_drag", "tail_ratio", "n_trades",
    ):
        assert k in m, f"missing metric: {k}"
    assert 0.0 <= m["exposure"] <= 1.0
    assert m["max_drawdown"] >= 0.0


def test_metrics_empty_series():
    assert _metrics(pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float)) == {"n_bars": 0}
