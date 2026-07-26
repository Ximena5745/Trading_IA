"""
Module: api/routes/execution.py
Responsibility: Order execution, cancellation and order tracking endpoints
Dependencies: executor, order_tracker, risk_manager, auth dependencies
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, require_trader
from core.db.repositories import AuditRepository, OrderRepository, SignalRepository
from core.db.session import get_pool
from core.execution.order_tracker import OrderTracker
from core.execution.paper_executor import PaperExecutor
from core.models import Signal
from core.observability.logger import get_logger
from core.risk.risk_manager import RiskManager

limiter = Limiter(key_func=get_remote_address)
logger = get_logger(__name__)
router = APIRouter(prefix="/execution", tags=["execution"])

_order_tracker: OrderTracker | None = None
_risk_manager: RiskManager | None = None
_portfolio_manager = None
_paper_executor: PaperExecutor | None = None
_signal_repo: SignalRepository | None = None
_order_repo: OrderRepository | None = None
_audit_repo: AuditRepository | None = None


def set_order_tracker(ot: OrderTracker) -> None:
    global _order_tracker
    _order_tracker = ot


def set_risk_manager(rm: RiskManager) -> None:
    global _risk_manager
    _risk_manager = rm


def set_portfolio_manager(pm) -> None:
    global _portfolio_manager
    _portfolio_manager = pm


def set_paper_executor(executor: PaperExecutor) -> None:
    global _paper_executor
    _paper_executor = executor


def set_repositories(
    signal_repo: SignalRepository,
    order_repo: OrderRepository,
    audit_repo: AuditRepository,
) -> None:
    global _signal_repo, _order_repo, _audit_repo
    _signal_repo = signal_repo
    _order_repo = order_repo
    _audit_repo = audit_repo


def _get_ot() -> OrderTracker:
    if _order_tracker is None:
        raise RuntimeError("OrderTracker not initialized")
    return _order_tracker


def _get_rm() -> RiskManager:
    if _risk_manager is None:
        raise RuntimeError("RiskManager not initialized")
    return _risk_manager


def _db_available() -> bool:
    try:
        get_pool()
        return True
    except RuntimeError:
        return False


class ExecuteRequest(BaseModel):
    signal_id: str
    symbol: str
    direction: str  # BUY | SELL
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    idempotency_key: Optional[str] = None
    quantity: Optional[float] = None


@router.post(
    "", dependencies=[Depends(require_trader)], status_code=status.HTTP_202_ACCEPTED
)
@limiter.limit("10/minute")
async def execute_signal(
    request: Request,
    req: ExecuteRequest,
    user=Depends(get_current_user),
):
    """Submit a signal for execution after risk validation."""
    rm = _get_rm()
    ot = _get_ot()
    executor = _paper_executor or PaperExecutor()

    signal = Signal(
        id=req.signal_id or str(uuid4()),
        symbol=req.symbol.upper(),
        action=req.direction.upper(),
        entry_price=req.entry_price,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        confidence=req.confidence,
        idempotency_key=req.idempotency_key or req.signal_id or str(uuid4()),
        explanation=[],
        risk_reward_ratio=abs(req.take_profit - req.entry_price)
        / max(abs(req.entry_price - req.stop_loss), 1e-9),
        summary="API execution",
        regime=None,
        strategy_id="manual",
        status="accepted",
        timestamp=datetime.now(timezone.utc),
    )

    portfolio_state = None
    if _portfolio_manager is not None:
        portfolio_state = _portfolio_manager.get_portfolio()

    approved, reason = rm.validate_signal(
        signal,
        portfolio=portfolio_state.model_dump() if portfolio_state else None,
    )
    if not approved:
        logger.warning(
            "api_execution_rejected",
            signal_id=signal.id,
            reason=reason,
            user=user.get("user_id"),
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"status": "rejected", "reason": reason},
        )

    quantity = req.quantity
    if quantity is None and _portfolio_manager is not None:
        quantity = rm.calculate_position_size(
            signal.model_dump(),
            portfolio_state.model_dump() if portfolio_state else {},
        )
    if not quantity or quantity <= 0:
        quantity = 0.01

    order = await executor.execute(signal.model_dump(), quantity)

    if _portfolio_manager is not None:
        try:
            _portfolio_manager.open_position(signal, quantity, order["fill_price"])
        except TypeError:
            _portfolio_manager.open_position(
                signal.model_dump(), quantity, order["fill_price"]
            )

    if hasattr(ot, "register"):
        ot.register(order)
    elif hasattr(ot, "add"):
        ot.add(order)

    if _db_available() and _signal_repo and _order_repo:
        try:
            await _signal_repo.create(signal)
            await _order_repo.create(order)
            if _audit_repo:
                await _audit_repo.log_action(
                    action="order_executed",
                    user_id=user.get("user_id", "unknown"),
                    changes={"signal_id": signal.id, "order_id": order["id"]},
                    resource_type="order",
                    entity_id=order["id"],
                )
        except Exception as exc:
            logger.warning("execution_persist_failed", error=str(exc))

    logger.info(
        "api_execution_completed",
        signal_id=signal.id,
        order_id=order.get("id"),
        symbol=signal.symbol,
        user=user.get("user_id"),
    )
    return {
        "status": "executed",
        "signal_id": signal.id,
        "order_id": order.get("id"),
        "idempotency_key": signal.idempotency_key,
        "fill_price": order.get("fill_price"),
        "quantity": quantity,
    }


@router.get("/orders")
async def get_orders(symbol: Optional[str] = None, user=Depends(get_current_user)):
    """Return open orders, optionally filtered by symbol."""
    ot = _get_ot()
    orders = ot.get_open_orders() if hasattr(ot, "get_open_orders") else []
    if symbol:
        orders = [o for o in orders if o.get("symbol") == symbol.upper()]
    return {
        "orders": [o.model_dump() if hasattr(o, "model_dump") else o for o in orders],
        "total": len(orders),
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str, user=Depends(get_current_user)):
    """Return a specific order by ID."""
    ot = _get_ot()
    try:
        order = ot.get(order_id)
    except (KeyError, AttributeError):
        if _db_available() and _order_repo:
            row = await _order_repo.get_by_id(order_id)
            if row:
                return row
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")
    return order.model_dump() if hasattr(order, "model_dump") else order


@router.delete("/orders/{order_id}", dependencies=[Depends(require_trader)])
async def cancel_order(order_id: str, user=Depends(get_current_user)):
    """Cancel a pending order."""
    ot = _get_ot()
    try:
        ot.get(order_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

    ot.update_status(order_id, "cancelled")
    logger.info("api_order_cancelled", order_id=order_id, user=user.get("user_id"))
    return {"status": "cancelled", "order_id": order_id}
