"""
Module: api/routes/risk.py
Responsibility: Kill switch status and manual control endpoints
Dependencies: require_admin, kill_switch
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.dependencies import require_admin, require_trader
from core.config.settings import get_settings
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/risk", tags=["risk"])
settings = get_settings()

_kill_switch = None


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
    return {"message": "Kill switch activated", "triggered_by": "manual"}


@router.post("/kill-switch/reset")
async def reset_kill_switch(admin: dict = Depends(require_admin)):
    ks = _get_kill_switch()
    if not ks.is_active():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Kill switch is not active"
        )
    ks.reset(admin_token=admin["user_id"])
    return {"message": "Kill switch reset successfully"}


@router.get("/limits")
async def get_limits(_: dict = Depends(require_trader)):
    return {
        "MAX_RISK_PER_TRADE_PCT": settings.MAX_RISK_PER_TRADE_PCT,
        "MAX_PORTFOLIO_RISK_PCT": settings.MAX_PORTFOLIO_RISK_PCT,
        "DAILY_LOSS_LIMIT_PCT": settings.DAILY_LOSS_LIMIT_PCT,
        "MAX_CONSECUTIVE_LOSSES": settings.MAX_CONSECUTIVE_LOSSES,
        "MAX_DRAWDOWN_PCT": settings.MAX_DRAWDOWN_PCT,
    }
