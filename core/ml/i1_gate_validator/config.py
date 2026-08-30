"""
Module: core/ml/i1_gate_validator/config.py
Responsibility: I1 gate constants, thresholds, and per-asset overrides
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from core.config.constants import TRADED_UNIVERSE

PERIODS_PER_YEAR_1H = 252 * 24
GATE_SHARPE_NET = 0.8
GATE_P_VALUE = 0.05
GATE_SHARPE_HOLDOUT = 0.8
HOLDOUT_FRACTION = 0.2

# Single source of truth — ADR-004 / SPEC-B03. The gate validates exactly the
# symbols the pipeline may trade.
PIPELINE_SYMBOLS = list(TRADED_UNIVERSE)

DEFAULT_I1_PARAMS_DIR = Path("data/models/i1_params")

_DEFAULT_ASSET_CFG: dict[str, Any] = {
    "cooldown": 3,
    "min_hold_bars": 0,
    "min_adx": 20.0,
    "strategies": None,
}

I1_ASSET_OVERRIDES: dict[str, dict[str, Any]] = {
    "BTCUSDT": {
        "cooldown": 6,
        "min_hold_bars": 4,
        "min_adx": 22.0,
        "strategies": ["tsmom_v1", "vol_breakout_v1", "Momentum"],
    },
    "ETHUSDT": {
        "cooldown": 6,
        "min_hold_bars": 4,
        "min_adx": 22.0,
        "strategies": ["tsmom_v1", "vol_breakout_v1", "Momentum"],
    },
    "EURUSD": {
        "cooldown": 4,
        "min_hold_bars": 2,
        "min_adx": 18.0,
        "strategies": ["mean_rev_v1", "ema_rsi_v1", "BB_ZScore"],
    },
    "US500": {
        "cooldown": 5,
        "min_hold_bars": 3,
        "min_adx": 20.0,
        "strategies": ["vol_breakout_v1", "tsmom_v1"],
    },
    "US30": {
        "cooldown": 12,
        "min_hold_bars": 8,
        "min_adx": 24.0,
        "strategies": ["vol_breakout_v1", "tsmom_v1", "BB_ZScore", "mean_rev_v1"],
    },
}


def get_asset_config(symbol: str) -> dict[str, Any]:
    cfg = dict(_DEFAULT_ASSET_CFG)
    cfg.update(I1_ASSET_OVERRIDES.get(symbol.upper(), {}))
    return cfg


def signal_kwargs(asset_cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "cooldown": int(asset_cfg.get("cooldown", 3)),
        "min_hold_bars": int(asset_cfg.get("min_hold_bars", 0)),
        "min_adx": float(asset_cfg.get("min_adx", 20.0)),
    }
