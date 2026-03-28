"""
Module: api/routes/portfolio.py
Responsibility: Portfolio state, positions, history, and performance endpoints
Dependencies: portfolio_manager, performance_tracker, auth dependencies
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from api.dependencies import get_current_user, require_trader
from core.monitoring.performance_tracker import PerformanceTracker
from core.observability.logger import get_logger
from core.portfolio.portfolio_manager import PortfolioManager

logger = get_logger(__name__)
router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Module-level singletons (injected at app startup via app.state)
_portfolio_manager: PortfolioManager | None = None
_performance_tracker: PerformanceTracker | None = None


def set_portfolio_manager(pm: PortfolioManager) -> None:
    global _portfolio_manager
    _portfolio_manager = pm


def set_performance_tracker(pt: PerformanceTracker) -> None:
    global _performance_tracker
    _performance_tracker = pt


def _get_pm() -> PortfolioManager:
    if _portfolio_manager is None:
        raise RuntimeError("PortfolioManager not initialized")
    return _portfolio_manager


def _get_pt() -> PerformanceTracker:
    if _performance_tracker is None:
        raise RuntimeError("PerformanceTracker not initialized")
    return _performance_tracker


@router.get("")
async def get_portfolio(user=Depends(get_current_user)):
    """Return current portfolio state."""
    pm = _get_pm()
    portfolio = pm.get_portfolio()
    logger.info("api_portfolio_requested", user=user.get("sub"))
    return portfolio.model_dump()


@router.get("/positions")
async def get_positions(user=Depends(get_current_user)):
    """Return all open positions."""
    pm = _get_pm()
    portfolio = pm.get_portfolio()
    return {
        "positions": [p.model_dump() for p in portfolio.positions.values()],
        "total": len(portfolio.positions),
    }


@router.get("/history")
async def get_portfolio_history(limit: int = 100, user=Depends(get_current_user)):
    """Return portfolio snapshots history."""
    pt = _get_pt()
    snapshots = pt.get_snapshots(limit=limit)
    return {"snapshots": snapshots, "count": len(snapshots)}


@router.get("/performance")
async def get_performance(user=Depends(get_current_user)):
    """Return performance metrics per strategy."""
    pt = _get_pt()
    metrics = pt.get_all_metrics()
    return {"strategies": metrics, "total_strategies": len(metrics)}


@router.get("/performance/{strategy_id}")
async def get_strategy_performance(strategy_id: str, user=Depends(get_current_user)):
    """Return performance metrics for a specific strategy."""
    pt = _get_pt()
    metrics = pt.get_strategy_metrics(strategy_id)
    return metrics


@router.post("/reset-daily", dependencies=[Depends(require_trader)])
async def reset_daily(user=Depends(get_current_user)):
    """Reset daily P&L counters (called at session start)."""
    pm = _get_pm()
    pm.reset_daily()
    logger.info("api_portfolio_daily_reset", user=user.get("sub"))
    return {"status": "ok", "message": "Daily counters reset"}
