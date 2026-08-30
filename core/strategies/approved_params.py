"""
Module: core/strategies/approved_params.py
Responsibility: Load / write the per-asset strategy parametrizations that the I1
  gate approved. This is the bridge between "what is validated" and "what the
  pipeline trades" (ADR-003, SPEC-B06 / SPEC-D01).

  Contract — data/models/i1_params/<SYMBOL>.json:
    {
      "strategy_id": "<key in StrategyRegistry / I1_STRATEGY_REGISTRY>",
      "params": { ... },
      "sharpe_net_holdout": 1.32,
      "approved_at": "2026-08-28T00:00:00+00:00"
    }

  Fail-safe: if a symbol has no <SYMBOL>.json, load_approved_strategy() returns
  None and the pipeline must NOT emit signals for it (logs no_approved_strategy).
Dependencies: stdlib only
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from core.observability.logger import get_logger

logger = get_logger(__name__)

I1_PARAMS_DIR = Path("data/models/i1_params")


@dataclass(frozen=True)
class ApprovedStrategy:
    symbol: str
    strategy_id: str
    params: dict[str, Any]
    sharpe_net_holdout: Optional[float]
    approved_at: Optional[str]


def _canonical_path(symbol: str, params_dir: Path) -> Path:
    return params_dir / f"{symbol.upper()}.json"


def load_approved_strategy(
    symbol: str, params_dir: Path | None = None
) -> Optional[ApprovedStrategy]:
    """Return the approved strategy for `symbol`, or None if none is approved.

    Only the canonical ``<SYMBOL>.json`` counts. Legacy ``<SYMBOL>_<strategy>.json``
    files are ignored on purpose — they predate the holdout gate criterion and
    are not evidence of an approved edge.
    """
    params_dir = params_dir or I1_PARAMS_DIR
    path = _canonical_path(symbol, params_dir)
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("approved_strategy_unreadable", symbol=symbol, path=str(path), error=str(exc))
        return None

    strategy_id = raw.get("strategy_id")
    if not strategy_id:
        logger.error("approved_strategy_missing_strategy_id", symbol=symbol, path=str(path))
        return None

    return ApprovedStrategy(
        symbol=symbol.upper(),
        strategy_id=str(strategy_id),
        params=dict(raw.get("params") or {}),
        sharpe_net_holdout=raw.get("sharpe_net_holdout"),
        approved_at=raw.get("approved_at"),
    )


def approved_symbols(params_dir: Path | None = None) -> set[str]:
    """Set of symbols with an approved canonical params file."""
    params_dir = params_dir or I1_PARAMS_DIR
    if not params_dir.exists():
        return set()
    out: set[str] = set()
    for p in params_dir.glob("*.json"):
        if "_" in p.stem:  # legacy <symbol>_<strategy>.json
            continue
        out.add(p.stem.upper())
    return out


def write_approved_params(
    *,
    symbol: str,
    strategy_id: str,
    params: dict[str, Any],
    sharpe_net_holdout: float,
    params_dir: Path | None = None,
    approved_at: str | None = None,
) -> Path:
    """Write a canonical <SYMBOL>.json. Called by the I1 gate for passed assets."""
    params_dir = params_dir or I1_PARAMS_DIR
    params_dir.mkdir(parents=True, exist_ok=True)
    path = _canonical_path(symbol, params_dir)
    payload = {
        "strategy_id": strategy_id,
        "params": params,
        "sharpe_net_holdout": round(float(sharpe_net_holdout), 4),
        "approved_at": approved_at or datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    logger.info(
        "approved_strategy_written",
        symbol=symbol.upper(),
        strategy_id=strategy_id,
        sharpe_net_holdout=payload["sharpe_net_holdout"],
    )
    return path
