"""
Tests for SPEC-B03 — one asset universe (G-10, D-11).

`core.config.constants.TRADED_UNIVERSE` is the single source of truth; settings,
the pipeline schedule and the I1 gate must all derive from it.
"""
from __future__ import annotations

import pytest

from core.config import constants
from core.config.settings import Settings
from core.ml.i1_gate_validator.config import PIPELINE_SYMBOLS
from scripts.run_pipeline import SCHEDULE

UNIVERSE = set(constants.TRADED_UNIVERSE)


def test_universe_is_single_source():
    """The three consumers produce exactly the same set."""
    assert set(Settings().SUPPORTED_SYMBOLS) == UNIVERSE
    assert set(PIPELINE_SYMBOLS) == UNIVERSE
    assert {sym for sym, _ in SCHEDULE} == UNIVERSE


def test_schedule_is_derived_and_non_overlapping():
    assert len(SCHEDULE) == len(constants.TRADED_UNIVERSE)
    offsets = [off for _, off in SCHEDULE]
    assert len(set(offsets)) == len(offsets), "staggered cycles must not collide"
    assert all(0 <= off < 60 for off in offsets)
    # order preserved from the canonical list
    assert [sym for sym, _ in SCHEDULE] == list(constants.TRADED_UNIVERSE)


def test_broker_symbol_map_covers_universe():
    for sym in constants.TRADED_UNIVERSE:
        assert sym in constants.BROKER_SYMBOL_MAP, f"{sym} missing from BROKER_SYMBOL_MAP"
        natives = constants.BROKER_SYMBOL_MAP[sym]
        assert natives and all(natives.values()), f"{sym} has an empty native mapping"


def test_index_nomenclature_is_canonical():
    """ADR-004: SPX500 alias removed in favour of US500."""
    assert "SPX500" not in constants.SUPPORTED_SYMBOLS
    assert "SPX500" not in Settings().SUPPORTED_SYMBOLS
    assert "US500" in constants.TRADED_UNIVERSE
    assert constants.DEFAULT_SYMBOLS_BY_CLASS["indices"] == "US500"


def test_data_availability_flags():
    assert constants.has_market_data("BTCUSDT") is True   # live crypto venue
    assert constants.has_raw_data("EURUSD") is True        # parquet present
    assert constants.has_market_data("EURUSD") is True
    assert constants.has_raw_data("NOPE123") is False
    assert constants.has_market_data("NOPE123") is False
    dmap = constants.data_available_map()
    assert set(dmap) == UNIVERSE
    assert all(isinstance(v, bool) for v in dmap.values())


@pytest.mark.parametrize("sym", sorted(UNIVERSE))
def test_every_traded_symbol_has_an_asset_class(sym):
    from core.models import detect_asset_class

    assert detect_asset_class(sym) is not None
