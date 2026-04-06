"""
Module: api/routes/signals.py
Responsibility: Signal endpoints — list, detail, latest
Dependencies: require_trader, models
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencies import require_trader

router = APIRouter(prefix="/signals", tags=["signals"])

# In-memory store for MVP
_signals: dict[str, dict] = {}


@router.get("")
async def list_signals(
    symbol: Optional[str] = None,
    signal_status: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, le=200),
):
    """Public endpoint for dashboard without auth requirement."""
    results = list(_signals.values())
    if symbol:
        results = [s for s in results if s["symbol"] == symbol.upper()]
    if signal_status:
        results = [s for s in results if s["status"] == signal_status]
    results.sort(key=lambda s: s["timestamp"], reverse=True)
    return {"count": len(results[:limit]), "signals": results[:limit]}


@router.get("/latest/{symbol}")
async def get_latest_signal(symbol: str, _: dict = Depends(require_trader)):
    symbol = symbol.upper()
    active = [
        s
        for s in _signals.values()
        if s["symbol"] == symbol and s["status"] == "pending"
    ]
    if not active:
        return None
    return sorted(active, key=lambda s: s["timestamp"], reverse=True)[0]


@router.get("/{signal_id}")
async def get_signal(signal_id: str, _: dict = Depends(require_trader)):
    signal = _signals.get(signal_id)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
        )
    return signal


def store_signal(signal: dict) -> None:
    _signals[signal["id"]] = signal


def update_signal_status(signal_id: str, new_status: str) -> None:
    if signal_id in _signals:
        _signals[signal_id]["status"] = new_status
