"""
F2.4 — 1h data hygiene audit. Unit checks on the pure detectors with crafted
frames; the full universe run is exercised by the script.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from scripts.audit_data_quality import (
    _check_cadence,
    _check_ohlc,
    _check_outliers,
    _ret_limit,
)


def _clean_frame(n=60):
    ts = pd.date_range("2024-01-01", periods=n, freq="1h", tz="UTC")
    base = np.linspace(100, 110, n)
    return pd.DataFrame(
        {
            "timestamp": ts,
            "open": base,
            "high": base + 1.0,
            "low": base - 1.0,
            "close": base + 0.5,
            "volume": np.full(n, 1000.0),
        }
    )


def test_ohlc_clean_frame_has_no_violations():
    assert _check_ohlc(_clean_frame())["total"] == 0


def test_ohlc_detects_high_low_inversion_and_nonpositive():
    df = _clean_frame()
    df.loc[3, "high"] = df.loc[3, "low"] - 5  # high < low
    df.loc[7, "close"] = -1.0                 # nonpositive
    res = _check_ohlc(df)
    assert res["violations"]["high_lt_low"] >= 1
    assert res["violations"]["nonpositive_price"] >= 1
    assert res["total"] >= 2


def test_cadence_flags_intraday_gap_but_not_weekend():
    df = _clean_frame(48)
    ts = list(df["timestamp"])
    # drop 5 bars mid-week -> one intraday gap
    ts = ts[:20] + ts[25:]
    cad = _check_cadence(pd.Series(ts))
    assert cad["modal_delta_seconds"] == 3600.0
    assert cad["n_intraday_gaps"] >= 1


def test_outliers_detects_a_price_spike():
    df = _clean_frame(600)
    close = df["close"].copy()
    close.iloc[400] *= 1.5  # +50% one-bar jump
    res = _check_outliers(close, "EURUSD")
    assert res["n_bars_over_limit"] >= 1


def test_ret_limit_by_asset_class():
    assert _ret_limit("BTCUSDT") == 0.20
    assert _ret_limit("EURUSD") == 0.10
    assert _ret_limit("XAUUSD") == 0.12
