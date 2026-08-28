"""
Module: api/routes/risk.py
Responsibility: Kill switch status and manual control endpoints
Dependencies: require_admin, kill_switch
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from api.dependencies import require_admin, require_trader
from core.config.settings import get_settings
from core.models import detect_asset_class
from core.risk.mtf_sl_tp_manager import (
    SLTPConfig,
    Timeframe,
    clear_sltp_override,
    get_sltp_config,
    has_sltp_override,
    set_sltp_override,
)
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/risk", tags=["risk"])
settings = get_settings()

_kill_switch = None

# ── Filter / risk-decision history ────────────────────────────────────────────
# In-memory ring buffer of risk-filter events (config overrides, kill-switch
# toggles, and — once a trading loop wires it — per-signal RiskManager verdicts).
# MVP: not persisted, lost on restart (same pattern as api/routes/signals.py).
# Any pipeline can push events via record_filter_event().
_filter_history: deque = deque(maxlen=300)


def record_filter_event(
    *,
    filter_name: str,
    decision: str,
    reason: str,
    symbol: str | None = None,
    actor: str = "system",
    details: dict | None = None,
) -> None:
    """Append a risk-filter event to the in-memory history buffer.

    decision: "applied" | "blocked" | "override" | "reset" | "activated"
    """
    _filter_history.appendleft({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filter": filter_name,
        "symbol": symbol,
        "decision": decision,
        "reason": reason,
        "actor": actor,
        "details": details or {},
    })


def set_kill_switch(ks) -> None:
    global _kill_switch
    _kill_switch = ks


def _get_kill_switch():
    if _kill_switch is None:
        raise RuntimeError("KillSwitch not initialized")
    return _kill_switch


def _state_payload(ks) -> dict:
    s = ks.state
    if isinstance(s, dict):
        return {
            "active": s.get("active", False),
            "triggered_by": s.get("triggered_by"),
            "triggered_at": s.get("triggered_at"),
            "reset_at": s.get("reset_at"),
            "daily_loss_current": s.get("daily_loss_current", 0.0),
            "daily_loss_limit": s.get(
                "daily_loss_limit", settings.DAILY_LOSS_LIMIT_PCT
            ),
            "consecutive_losses": s.get("consecutive_losses", 0),
            "max_consecutive_losses": s.get(
                "max_consecutive_losses", settings.MAX_CONSECUTIVE_LOSSES
            ),
        }
    return {
        "active": s.active,
        "triggered_by": s.triggered_by,
        "triggered_at": s.triggered_at.isoformat() if s.triggered_at else None,
        "reset_at": s.reset_at.isoformat() if s.reset_at else None,
        "daily_loss_current": s.daily_loss_current,
        "daily_loss_limit": s.daily_loss_limit,
        "consecutive_losses": s.consecutive_losses,
        "max_consecutive_losses": s.max_consecutive_losses,
    }


@router.get("/status")
async def get_risk_status(_: dict = Depends(require_trader)):
    ks = _get_kill_switch()
    return {"kill_switch": _state_payload(ks)}


@router.get("/status/public")
async def get_risk_status_public():
    """Public endpoint for dashboard — returns risk metrics."""
    ks = _get_kill_switch()
    return {"kill_switch": _state_payload(ks)}


@router.post("/kill-switch/activate")
@limiter.limit("3/minute")
async def activate_kill_switch(request: Request, admin: dict = Depends(require_admin)):
    ks = _get_kill_switch()
    if hasattr(ks, "activate"):
        ks.activate("manual")
    elif hasattr(ks, "_trigger"):
        ks._trigger("manual")
    else:
        raise HTTPException(status_code=500, detail="Kill switch not configurable")
    record_filter_event(
        filter_name="kill_switch", decision="activated",
        reason="Activación manual del kill switch — todas las órdenes bloqueadas.",
        actor=admin.get("user_id", "admin"),
    )
    return {"message": "Kill switch activated", "triggered_by": "manual"}


@router.post("/kill-switch/reset")
async def reset_kill_switch(admin: dict = Depends(require_admin)):
    ks = _get_kill_switch()
    if not ks.is_active():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Kill switch is not active"
        )
    ks.reset(admin_token=admin["user_id"])
    record_filter_event(
        filter_name="kill_switch", decision="reset",
        reason="Kill switch restablecido — trading reactivado.",
        actor=admin["user_id"],
    )
    return {"message": "Kill switch reset successfully"}


@router.get("/filter-history")
async def get_filter_history(limit: int = Query(default=100, ge=1, le=300)):
    """Recent risk-filter events (config overrides, kill-switch toggles, and
    per-signal RiskManager verdicts once a trading loop feeds record_filter_event).

    Public: read-only, no sensitive data. Empty on a fresh process — nothing in
    this repo pushes per-signal verdicts yet; overrides/kill-switch toggles show
    up here as soon as they happen.
    """
    events = list(_filter_history)[:limit]
    return {"count": len(events), "events": events}


@router.get("/limits")
async def get_limits(_: dict = Depends(require_trader)):
    return {
        "MAX_RISK_PER_TRADE_PCT": settings.MAX_RISK_PER_TRADE_PCT,
        "MAX_PORTFOLIO_RISK_PCT": settings.MAX_PORTFOLIO_RISK_PCT,
        "DAILY_LOSS_LIMIT_PCT": settings.DAILY_LOSS_LIMIT_PCT,
        "MAX_CONSECUTIVE_LOSSES": settings.MAX_CONSECUTIVE_LOSSES,
        "MAX_DRAWDOWN_PCT": settings.MAX_DRAWDOWN_PCT,
    }


class SLTPConfigUpdate(BaseModel):
    symbol: str
    timeframe: str
    atr_sl_multiplier: float = Field(gt=0, le=10)
    atr_tp_multiplier: float = Field(gt=0, le=15)
    atr_fib_weight: float = Field(ge=0, le=1)
    min_rr_ratio: float = Field(ge=0.5, le=10)
    max_sl_pct: float = Field(gt=0, le=0.2)


def _parse_timeframe(raw: str) -> Timeframe:
    try:
        return Timeframe(raw)
    except ValueError:
        valid = ", ".join(t.value for t in Timeframe)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Timeframe inválido '{raw}'. Válidos: {valid}",
        )


@router.get("/sltp-config")
async def get_sltp_config_public(symbol: str, timeframe: str):
    """Config efectiva de SL/TP (override si existe, si no el default) para symbol+timeframe.

    Público: solo lectura, no expone nada sensible. El override real aplica
    por (asset_class, timeframe) — no por símbolo individual — porque así
    está diseñado core/risk/mtf_sl_tp_manager: ver docstring de PUT abajo.
    """
    tf = _parse_timeframe(timeframe)
    asset_class = detect_asset_class(symbol)
    cfg = get_sltp_config(asset_class, tf)
    return {
        "symbol": symbol.upper(),
        "asset_class": asset_class.value,
        "timeframe": tf.value,
        "is_override": has_sltp_override(asset_class, tf),
        "atr_sl_multiplier": cfg.atr_sl_multiplier,
        "atr_tp_multiplier": cfg.atr_tp_multiplier,
        "atr_fib_weight": cfg.atr_fib_weight,
        "min_rr_ratio": cfg.min_rr_ratio,
        "max_sl_pct": cfg.max_sl_pct,
    }


@router.put("/sltp-config")
async def update_sltp_config(body: SLTPConfigUpdate, _: dict = Depends(require_trader)):
    """Sobrescribe en memoria (no persiste a disco/DB, se pierde al reiniciar el
    proceso — MVP, mismo patrón que el store en memoria de api/routes/signals.py)
    la configuración de SL/TP que `MTFSLTPManager.calculate_sl_tp()` usa de
    verdad para calcular niveles reales.

    El override se guarda por (asset_class, timeframe), no por símbolo — así
    es como get_sltp_config() ya indexaba la tabla por defecto. Guardar un
    override para EURUSD afecta a TODOS los pares forex en ese timeframe.
    """
    tf = _parse_timeframe(body.timeframe)
    asset_class = detect_asset_class(body.symbol)
    cfg = SLTPConfig(
        atr_sl_multiplier=body.atr_sl_multiplier,
        atr_tp_multiplier=body.atr_tp_multiplier,
        atr_fib_weight=body.atr_fib_weight,
        min_rr_ratio=body.min_rr_ratio,
        max_sl_pct=body.max_sl_pct,
    )
    set_sltp_override(asset_class, tf, cfg)
    record_filter_event(
        filter_name="sltp_config_override", decision="override", symbol=body.symbol.upper(),
        reason=(
            f"Override SL/TP para clase {asset_class.value} @ {tf.value}: "
            f"ATR SL x{body.atr_sl_multiplier}, ATR TP x{body.atr_tp_multiplier}, "
            f"peso ATR/Fib {body.atr_fib_weight}, min R:R {body.min_rr_ratio}"
        ),
        actor="trader",
        details=body.model_dump(),
    )
    return {
        "message": "SL/TP config actualizada",
        "asset_class": asset_class.value,
        "timeframe": tf.value,
        "affects": f"Todos los símbolos de clase {asset_class.value} en timeframe {tf.value}",
    }


@router.delete("/sltp-config")
async def reset_sltp_config(symbol: str, timeframe: str, _: dict = Depends(require_trader)):
    tf = _parse_timeframe(timeframe)
    asset_class = detect_asset_class(symbol)
    clear_sltp_override(asset_class, tf)
    cfg = get_sltp_config(asset_class, tf)
    record_filter_event(
        filter_name="sltp_config_override", decision="reset", symbol=symbol.upper(),
        reason=f"Override SL/TP eliminado para clase {asset_class.value} @ {tf.value} — vuelve a default.",
        actor="trader",
    )
    return {
        "message": "Override eliminado, restablecido a valores por defecto",
        "atr_sl_multiplier": cfg.atr_sl_multiplier,
        "atr_tp_multiplier": cfg.atr_tp_multiplier,
        "atr_fib_weight": cfg.atr_fib_weight,
        "min_rr_ratio": cfg.min_rr_ratio,
        "max_sl_pct": cfg.max_sl_pct,
    }
