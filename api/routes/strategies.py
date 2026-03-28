"""
Module: api/routes/strategies.py
Responsibility: Strategy CRUD, status management, and custom builder
Dependencies: strategy_registry, strategy_builder, auth dependencies
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_current_user, require_admin, require_trader
from core.exceptions import StrategyNotFoundError
from core.observability.logger import get_logger
from core.strategies.strategy_registry import StrategyRegistry

logger = get_logger(__name__)
router = APIRouter(prefix="/strategies", tags=["strategies"])

_registry: StrategyRegistry | None = None


def set_strategy_registry(reg: StrategyRegistry) -> None:
    global _registry
    _registry = reg


def _get_registry() -> StrategyRegistry:
    if _registry is None:
        raise RuntimeError("StrategyRegistry not initialized")
    return _registry


class StrategyStatusUpdate(BaseModel):
    status: str  # active | paused | disabled


class CustomStrategyRequest(BaseModel):
    strategy_id: str
    name: str
    description: str = ""
    conditions: list[dict[str, Any]]
    exit_conditions: list[dict[str, Any]]


@router.get("")
async def list_strategies(user=Depends(get_current_user)):
    """List all registered strategies."""
    reg = _get_registry()
    return {"strategies": reg.list_all(), "total": len(reg.list_all())}


@router.get("/active")
async def list_active_strategies(user=Depends(get_current_user)):
    """List only active strategies."""
    reg = _get_registry()
    active = reg.list_active()
    return {
        "strategies": [s.to_dict() for s in active],
        "total": len(active),
    }


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str, user=Depends(get_current_user)):
    """Return details for a specific strategy."""
    reg = _get_registry()
    try:
        strategy = reg.get(strategy_id)
        return strategy.to_dict()
    except StrategyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{strategy_id}/status", dependencies=[Depends(require_trader)])
async def update_strategy_status(
    strategy_id: str,
    body: StrategyStatusUpdate,
    user=Depends(get_current_user),
):
    """Update a strategy's status (active/paused/disabled)."""
    allowed = {"active", "paused", "disabled"}
    if body.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Status must be one of: {allowed}",
        )
    reg = _get_registry()
    try:
        updated = reg.set_status(strategy_id, body.status)
        logger.info(
            "api_strategy_status_updated",
            strategy_id=strategy_id,
            status=body.status,
            user=user.get("sub"),
        )
        return updated
    except StrategyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/custom", dependencies=[Depends(require_admin)], status_code=status.HTTP_201_CREATED)
async def create_custom_strategy(
    body: CustomStrategyRequest,
    user=Depends(get_current_user),
):
    """Register a custom strategy built from JSON conditions."""
    from core.strategies.strategy_builder import StrategyBuilder

    reg = _get_registry()
    builder = StrategyBuilder()

    try:
        strategy = builder.build(body.model_dump())
        reg.register(strategy)
        logger.info(
            "api_strategy_created",
            strategy_id=body.strategy_id,
            user=user.get("sub"),
        )
        return {"status": "created", "strategy": strategy.to_dict()}
    except Exception as exc:
        logger.error("api_strategy_build_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Strategy build failed: {exc}",
        )


@router.delete("/{strategy_id}", dependencies=[Depends(require_admin)])
async def delete_strategy(strategy_id: str, user=Depends(get_current_user)):
    """Unregister a strategy."""
    reg = _get_registry()
    try:
        reg.unregister(strategy_id)
        logger.info(
            "api_strategy_deleted",
            strategy_id=strategy_id,
            user=user.get("sub"),
        )
        return {"status": "deleted", "strategy_id": strategy_id}
    except StrategyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
