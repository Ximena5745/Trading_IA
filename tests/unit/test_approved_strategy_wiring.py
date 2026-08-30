"""
Tests for SPEC-B06 / SPEC-D01 (F1.4) — one strategy source + I1 params wired
to the pipeline, fail-safe when a symbol has no approved strategy.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import pytest

from core.config.constants import TRADED_UNIVERSE
from core.ml.i1_strategies import I1_STRATEGY_REGISTRY
from core.strategies.approved_params import (
    ApprovedStrategy,
    approved_symbols,
    load_approved_strategy,
    write_approved_params,
)
from core.strategies.strategy_registry import StrategyRegistry

REPO = Path(__file__).resolve().parents[2]


# ── single source of strategies ───────────────────────────────────────────
def test_strategy_registry_is_single_source():
    reg = StrategyRegistry()
    assert set(I1_STRATEGY_REGISTRY).issubset(reg.strategy_ids())
    for sid in I1_STRATEGY_REGISTRY:
        assert reg.has(sid)
        assert reg.get_i1_spec(sid) is I1_STRATEGY_REGISTRY[sid]


# ── approved-params contract + fail-safe ──────────────────────────────────
def test_load_approved_strategy_contract(tmp_path):
    (tmp_path / "XAUUSD.json").write_text(
        json.dumps(
            {
                "strategy_id": "Momentum",
                "params": {"lookback": 16},
                "sharpe_net_holdout": 1.32,
                "approved_at": "2026-07-26T06:54:29+00:00",
            }
        )
    )
    got = load_approved_strategy("xauusd", params_dir=tmp_path)
    assert got == ApprovedStrategy(
        symbol="XAUUSD",
        strategy_id="Momentum",
        params={"lookback": 16},
        sharpe_net_holdout=1.32,
        approved_at="2026-07-26T06:54:29+00:00",
    )


def test_missing_file_returns_none_and_legacy_is_ignored(tmp_path):
    assert load_approved_strategy("BTCUSDT", params_dir=tmp_path) is None
    # a legacy <symbol>_<strategy>.json must NOT count as approved
    (tmp_path / "BTCUSDT_tsmom_v1.json").write_text(
        json.dumps({"symbol": "BTCUSDT", "strategy": "tsmom_v1", "params": {}})
    )
    assert load_approved_strategy("BTCUSDT", params_dir=tmp_path) is None
    assert approved_symbols(tmp_path) == set()


def test_pipeline_only_trades_approved_symbols_repo_state():
    """With only XAUUSD.json present in the repo, XAUUSD is the sole approved."""
    approved = {s for s in TRADED_UNIVERSE if load_approved_strategy(s) is not None}
    assert approved == {"XAUUSD"}


def test_pipeline_only_trades_approved_symbols_generalises(tmp_path):
    write_approved_params(
        symbol="EURUSD",
        strategy_id="mean_rev_v1",
        params={"rsi_oversold": 25},
        sharpe_net_holdout=0.91,
        params_dir=tmp_path,
    )
    approved = {s for s in TRADED_UNIVERSE if load_approved_strategy(s, tmp_path)}
    assert approved == {"EURUSD"}
    reloaded = json.loads((tmp_path / "EURUSD.json").read_text())
    assert set(reloaded) == {"strategy_id", "params", "sharpe_net_holdout", "approved_at"}


# ── strategy confirmation filter ─────────────────────────────────────────
def test_strategy_confirms_vetoes_opposite_direction():
    from scripts.run_pipeline import _strategy_confirms

    df = pd.DataFrame({"close": [1.0, 2.0, 3.0]})

    class Spec:
        defaults = {}

        def __init__(self, val):
            self._val = val

        def signal_fn(self, _df, _p):
            return pd.Series([self._val] * len(_df))

    assert _strategy_confirms(Spec(1), df, {}, "BUY")[0] is True
    assert _strategy_confirms(Spec(-1), df, {}, "BUY")[0] is False
    assert _strategy_confirms(Spec(-1), df, {}, "SELL")[0] is True
    assert _strategy_confirms(Spec(0), df, {}, "BUY")[0] is True  # flat never vetoes

    class Boom:
        defaults = {}

        def signal_fn(self, *_a):
            raise RuntimeError("indicator blew up")

    assert _strategy_confirms(Boom(), df, {}, "BUY")[0] is False  # fail-closed


# ── the single "default_v1" point ───────────────────────────────────────
def test_default_v1_is_a_single_documented_point():
    hits: list[str] = []
    for base in ("scripts", "core"):
        for p in (REPO / base).rglob("*.py"):
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                if "default_v1" in line:
                    hits.append(f"{p.relative_to(REPO)}:{i}")
    assert len(hits) == 1, f"expected exactly one 'default_v1' point, found: {hits}"
    assert hits[0].startswith("core/signals/signal_engine.py") or hits[0].startswith(
        "core\\signals\\signal_engine.py"
    )
