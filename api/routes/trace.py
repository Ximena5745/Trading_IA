"""
Module: api/routes/trace.py
Responsibility: GET /trace/{correlation_id} — reconstruct one pipeline decision
  end to end (market data → features → agents → consensus → signal → risk →
  execution → portfolio). SPEC-B04 / F-06.
Dependencies: require_trader, decision_tracer.TraceStore
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import require_trader
from core.observability.decision_tracer import TRACE_STEPS, get_trace_store

router = APIRouter(prefix="/trace", tags=["trace"])


@router.get("/{correlation_id}", dependencies=[Depends(require_trader)])
async def get_trace(correlation_id: str) -> dict:
    steps = get_trace_store().get(correlation_id)
    if not steps:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No trace for correlation_id {correlation_id}",
        )
    seen = [s["step"] for s in steps]
    return {
        "correlation_id": correlation_id,
        "step_count": len(steps),
        "stages_present": [s for s in TRACE_STEPS if s in seen],
        "complete": all(s in seen for s in TRACE_STEPS),
        "steps": steps,
    }
