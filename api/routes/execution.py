"""
Module: api/routes/execution.py
Responsibility: Order execution, cancellation and order tracking endpoints
Dependencies: executor, order_tracker, risk_manager, auth dependencies
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_current_user, require_trader
from core.execution.order_tracker import OrderTracker
from core.models import Signal
from core.observability.logger import get_logger
from core.risk.risk_manager import RiskManager

logger = get_logger(__name__)
router = APIRouter(prefix="/execution", tags=["execution"])

# Module-level singletons
_order_tracker: OrderTracker | None = None
_risk_manager: RiskManager | None = None


def set_order_tracker(ot: OrderTracker) -> None:
    global _order_tracker
    _order_tracker = ot


def set_risk_manager(rm: RiskManager) -> None:
    global _risk_manager
    _risk_manager = rm


def _get_ot() -> OrderTracker:
    if _order_tracker is None:
        raise RuntimeError("OrderTracker not initialized")
    return _order_tracker


def _get_rm() -> RiskManager:
    if _risk_manager is None:
        raise RuntimeError("RiskManager not initialized")
    return _risk_manager


class ExecuteRequest(BaseModel):
    signal_id: str
    symbol: str
    direction: str  # BUY | SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    idempotency_key: Optional[str] = None


@router.post("", dependencies=[Depends(require_trader)], status_code=status.HTTP_202_ACCEPTED)
async def execute_signal(
    req: ExecuteRequest,
    user=Depends(get_current_user),
):
    """Submit a signal for execution after risk validation."""
    rm = _get_rm()
    _get_ot()  # validate tracker is initialized

    # Build a minimal Signal for risk validation
    signal = Signal(
        id=req.signal_id,
        symbol=req.symbol,
        action=req.direction,
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        confidence=req.confidence,
        idempotency_key=req.idempotency_key or req.signal_id,
        explanation=None,
    )

    approved, reason = rm.validate_signal(signal, portfolio=None)
    if not approved:
        logger.warning(
            "api_execution_rejected",
            signal_id=req.signal_id,
            reason=reason,
            user=user.get("sub"),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"status": "rejected", "reason": reason},
        )

    logger.info(
        "api_execution_accepted",
        signal_id=req.signal_id,
        symbol=req.symbol,
        direction=req.direction,
        user=user.get("sub"),
    )
    return {
        "status": "accepted",
        "signal_id": req.signal_id,
        "idempotency_key": signal.idempotency_key,
        "message": "Signal accepted for execution",
    }


@router.get("/orders")
async def get_orders(symbol: Optional[str] = None, user=Depends(get_current_user)):
    """Return open orders, optionally filtered by symbol."""
    ot = _get_ot()
    orders = ot.get_open_orders(symbol=symbol)
    return {
        "orders": [o.model_dump() if hasattr(o, "model_dump") else o for o in orders],
        "total": len(orders),
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user)):
    """Return a specific order by ID."""
    ot = _get_ot()
    order = ot.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order.model_dump() if hasattr(order, "model_dump") else order


@router.delete("/orders/{order_id}", dependencies=[Depends(require_trader)])
async def cancel_order(order_id: str, user=Depends(get_current_user)):
    """Cancel a pending order."""
    ot = _get_ot()
    order = ot.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    ot.update_status(order_id, "cancelled")
    logger.info("api_order_cancelled", order_id=order_id, user=user.get("sub"))
    return {"status": "cancelled", "order_id": order_id}
