"""
Module: api/routes/risk.py
Responsibility: Kill switch status and manual control endpoints
Dependencies: require_admin, kill_switch
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import require_admin, require_trader
from core.config.settings import get_settings
from core.risk.kill_switch import KillSwitch

router = APIRouter(prefix="/risk", tags=["risk"])
settings = get_settings()
_kill_switch = KillSwitch(settings)


@router.get("/status")
async def get_risk_status(_: dict = Depends(require_trader)):
    s = _kill_switch.state
    return {
        "kill_switch": {
            "active": s.active,
            "triggered_by": s.triggered_by,
            "triggered_at": s.triggered_at,
            "reset_at": s.reset_at,
        },
        "daily_loss_current": s.daily_loss_current,
        "daily_loss_limit": s.daily_loss_limit,
        "consecutive_losses": s.consecutive_losses,
        "max_consecutive_losses": s.max_consecutive_losses,
    }


@router.get("/status/public")
async def get_risk_status_public():
    """Public endpoint for dashboard — returns risk metrics."""
    s = _kill_switch.state
    return {
        "kill_switch": {
            "active": s.active,
            "triggered_by": s.triggered_by,
            "triggered_at": s.triggered_at,
            "reset_at": s.reset_at,
        },
        "daily_loss_current": s.daily_loss_current,
        "daily_loss_limit": s.daily_loss_limit,
        "consecutive_losses": s.consecutive_losses,
        "max_consecutive_losses": s.max_consecutive_losses,
    }


@router.post("/kill-switch/activate")
async def activate_kill_switch(admin: dict = Depends(require_admin)):
    _kill_switch._trigger("manual")
    return {"message": "Kill switch activated", "triggered_by": "manual"}


@router.post("/kill-switch/reset")
async def reset_kill_switch(admin: dict = Depends(require_admin)):
    if not _kill_switch.is_active():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Kill switch is not active"
        )
    _kill_switch.reset(admin_token=admin["user_id"])
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
