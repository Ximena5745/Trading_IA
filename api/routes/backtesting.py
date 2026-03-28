"""
Module: api/routes/backtesting.py
Responsibility: Async backtest job submission and results
Dependencies: require_trader, BacktestEngine
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import require_trader

router = APIRouter(prefix="/backtest", tags=["backtesting"])

_jobs: dict[str, dict] = {}


class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str
    from_ts: datetime
    to_ts: datetime
    walk_forward: bool = True


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def submit_backtest(
    body: BacktestRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_trader),
):
    job_id = str(uuid.uuid4())
    job = {
        "job_id": job_id,
        "status": "pending",
        "strategy_id": body.strategy_id,
        "symbol": body.symbol,
        "from_ts": body.from_ts.isoformat(),
        "to_ts": body.to_ts.isoformat(),
        "walk_forward": body.walk_forward,
        "submitted_by": user["user_id"],
        "submitted_at": datetime.utcnow().isoformat(),
        "results": None,
        "error": None,
    }
    _jobs[job_id] = job
    background_tasks.add_task(_run_backtest_job, job_id)
    return {"job_id": job_id, "status": "pending"}


@router.get("/{job_id}")
async def get_backtest_job(job_id: str, _: dict = Depends(require_trader)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return {k: v for k, v in job.items() if k != "results"}


@router.get("/{job_id}/results")
async def get_backtest_results(job_id: str, _: dict = Depends(require_trader)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job["status"] != "done":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job status is '{job['status']}', not 'done'",
        )
    return job["results"]


async def _run_backtest_job(job_id: str) -> None:
    job = _jobs.get(job_id)
    if not job:
        return
    try:
        job["status"] = "running"
        # Simulate async work — real implementation calls BacktestEngine
        await asyncio.sleep(1)
        job["status"] = "done"
        job["results"] = {
            "job_id": job_id,
            "strategy_id": job["strategy_id"],
            "symbol": job["symbol"],
            "message": "Backtest engine integration pending — connect BacktestEngine in Fase 4",
            "sharpe_ratio": None,
            "total_trades": 0,
        }
    except Exception as e:
        job["status"] = "failed"
        job["error"] = str(e)
