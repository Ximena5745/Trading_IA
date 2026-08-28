"""
Module: api/routes/monitoring.py
Responsibility: Observability panels for the dashboard "Monitoring" tab —
  - audit-log traceability (decision -> risk validation -> order execution)
  - live concept-drift indicator (KL-divergence on cached market features)
  - alpha-decay status per strategy
Dependencies: core.compliance.audit_system, core.ml.drift_detector (method reuse),
  core.ml.alpha_decay_monitor, api.routes.market cache
"""
from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
from fastapi import APIRouter, Query
from scipy import stats

from api.routes.market import _market_data_cache
from core.compliance.audit_system import AuditLog

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

# Features watched for drift — same spirit as core.ml.drift_detector._DRIFT_FEATURES,
# restricted to columns present in cached candle records.
_DRIFT_FEATURES = ("rsi_14", "atr_14", "macd_histogram", "volume_ratio", "trend_score")


@router.get("/audit-log")
async def get_audit_log(
    limit: int = Query(default=100, ge=1, le=1000),
    action_type: str | None = None,
    days: int = Query(default=90, ge=1, le=365),
):
    """Immutable audit trail: decision -> risk validation -> order execution.

    Reads the real JSONL files written by
    core.compliance.audit_system.AuditLog (logs/audit/audit_YYYYMM.jsonl).
    Returns [] when nothing has been logged yet — no trading pipeline in this
    repo currently calls ComplianceAuditSystem, so on a fresh install the panel
    shows an explicit empty state instead of fabricated rows. The backend works;
    it just has no producer wired in yet.
    """
    try:
        log = AuditLog()
        start = datetime.utcnow() - timedelta(days=days)
        entries = log.query(start_date=start, action_type=action_type)
    except Exception as exc:  # unreadable / corrupt log dir
        return {"count": 0, "entries": [], "source": "logs/audit", "error": str(exc)}

    entries = sorted(entries, key=lambda e: e.timestamp, reverse=True)[:limit]
    return {
        "count": len(entries),
        "source": "logs/audit",
        "entries": [
            {
                "timestamp": e.timestamp.isoformat(),
                "user_id": e.user_id,
                "action_type": e.action_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "result": e.result,
                "details": e.details,
                "metadata": e.metadata,
            }
            for e in entries
        ],
    }


def _js_distance(ref: np.ndarray, cur: np.ndarray) -> float:
    """Jensen-Shannon distance between the two feature distributions.

    Symmetric and bounded to [0, 1] (unlike raw KL-divergence, which explodes when
    the histograms barely overlap and makes every real series read as "grave").
    Same 20-bin shared-histogram discretisation the DriftDetector uses; 0 = identical
    distribution, 1 = disjoint.
    """
    ref = ref[np.isfinite(ref)]
    cur = cur[np.isfinite(cur)]
    if len(ref) < 20 or len(cur) < 20:
        return 0.0
    lo = float(min(ref.min(), cur.min()))
    hi = float(max(ref.max(), cur.max()))
    if hi <= lo:
        return 0.0
    # 12 bins: with ~40-120 samples per window that keeps the empty-bin noise
    # floor near JS~0.15 for a stationary feature (measured on this repo's data).
    bins = np.linspace(lo, hi, 13)
    p = np.histogram(ref, bins=bins)[0].astype(float)
    q = np.histogram(cur, bins=bins)[0].astype(float)
    p = p / p.sum() if p.sum() else p
    q = q / q.sum() if q.sum() else q
    p = np.clip(p, 1e-12, None)
    q = np.clip(q, 1e-12, None)
    m = 0.5 * (p + q)
    js = 0.5 * stats.entropy(p, m, base=2) + 0.5 * stats.entropy(q, m, base=2)
    return float(np.sqrt(max(js, 0.0)))


@router.get("/drift")
async def get_drift(
    symbol: str = Query(...),
    timeframe: str = "1d",
    window: int = Query(default=120, ge=40, le=500),
):
    """Live concept-drift read for a symbol.

    Same discretise-then-compare idea as core.ml.drift_detector.DriftDetector, but
    with a bounded Jensen-Shannon distance and a baseline derived on the fly:
    reference = all cached candles before the current window, current = the last
    `window` candles. Needs no persisted baseline (nothing in the repo calls
    DriftDetector.set_baseline in production), so it works from the market-data
    cache alone.

    Thresholds are calibrated to this data's noise floor: a stationary feature
    split in half sits around JS 0.15, so per-feature drift is flagged above 0.45
    and the overall level only reaches "grave" past 0.70.
    """
    symbol = symbol.upper()
    candles = (_market_data_cache.get(symbol, {}) or {}).get(timeframe) or []
    if len(candles) < window + 40:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "insufficient_data",
            "available_candles": len(candles),
            "needed": window + 40,
            "features": {},
        }

    ref_rows = candles[:-window][-500:]
    cur_rows = candles[-window:]
    feats: dict[str, dict] = {}
    max_js = 0.0
    for f in _DRIFT_FEATURES:
        ref = np.array([r.get(f) for r in ref_rows if r.get(f) is not None], dtype=float)
        cur = np.array([r.get(f) for r in cur_rows if r.get(f) is not None], dtype=float)
        if len(ref) < 40 or len(cur) < 40:
            feats[f] = {"js_distance": None, "status": "n/a"}
            continue
        js = _js_distance(ref, cur)
        max_js = max(max_js, js)
        feats[f] = {
            "js_distance": round(js, 4),
            "ref_mean": round(float(np.mean(ref)), 4),
            "cur_mean": round(float(np.mean(cur)), 4),
            "status": "drift" if js > 0.45 else ("watch" if js > 0.3 else "stable"),
        }

    level = (
        "grave" if max_js > 0.70
        else "moderado" if max_js > 0.50
        else "leve" if max_js > 0.35
        else "none"
    )
    action = {
        "grave": "DESACTIVAR_MODELO_FALLBACK",
        "moderado": "REENTRENAMIENTO_URGENTE",
        "leve": "AUMENTAR_PESO_ONLINE",
        "none": "CONTINUAR_NORMAL",
    }[level]
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "status": "ok",
        "window": window,
        "max_feature_drift": round(max_js, 4),
        "level": level,
        "recommended_action": action,
        "features": feats,
    }


@router.get("/alpha-decay")
async def get_alpha_decay():
    """Per-strategy alpha-decay status.

    core.ml.alpha_decay_monitor.AlphaDecayMonitor tracks rolling Sharpe / win-rate
    from live trade results, but no component in this repo feeds it record_trade()
    yet. Until a trading loop wires it, this returns the monitor's configured
    thresholds and an explicit wired=False flag rather than fabricated Sharpe
    numbers. The panel renders that honestly.
    """
    from core.ml.alpha_decay_monitor import AlphaDecayMonitor

    monitor = AlphaDecayMonitor()
    states = monitor.get_all_status()  # {} on a fresh instance
    return {
        "wired": False,
        "note": (
            "AlphaDecayMonitor no recibe record_trade() de ningún pipeline "
            "todavía — sin datos de trades en vivo no hay Sharpe rolling que mostrar."
        ),
        "strategies": [
            {"strategy_id": sid, "state": st} for sid, st in states.items()
        ],
        "thresholds": {
            "sharpe_threshold": 0.5,
            "win_rate_decay_threshold": 0.10,
            "consecutive_negative_threshold": 20,
            "window_size": 50,
        },
    }
