"""
Module: core/ml/i1_gate_validator/params_io.py
Responsibility: Persist/load per-symbol/strategy optimized parameters as JSON
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.ml.i1_gate_validator.config import DEFAULT_I1_PARAMS_DIR


def load_saved_params(
    symbol: str,
    strategy_id: str,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    base = base_dir or DEFAULT_I1_PARAMS_DIR
    path = base / f"{symbol.upper()}_{strategy_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data.get("params", {}))
    except (json.JSONDecodeError, OSError):
        return None


def save_params(symbol: str, strategy_id: str, params: dict[str, Any], base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{symbol.upper()}_{strategy_id}.json"
    path.write_text(
        json.dumps({"symbol": symbol.upper(), "strategy": strategy_id, "params": params}, indent=2),
        encoding="utf-8",
    )
    return path
