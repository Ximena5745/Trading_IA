"""
Module: api/routes/simulation.py
Responsibility: Historical simulator endpoints — "what if" scenario analysis
Dependencies: historical_simulator, strategy_registry, auth dependencies
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, field_validator

from api.dependencies import get_current_user
from core.observability.logger import get_logger
from core.simulation.historical_simulator import HistoricalSimulator, SimulationConfig
from core.strategies.strategy_registry import StrategyRegistry

logger = get_logger(__name__)
router = APIRouter(prefix="/simulation", tags=["simulation"])

_simulator: HistoricalSimulator | None = None
_strategy_registry: StrategyRegistry | None = None
_jobs: dict[str, dict] = {}  # job_id → status


def set_simulator(sim: HistoricalSimulator) -> None:
    global _simulator
    _simulator = sim


def set_strategy_registry(reg: StrategyRegistry) -> None:
    global _strategy_registry
    _strategy_registry = reg


def _get_sim() -> HistoricalSimulator:
    if _simulator is None:
        raise RuntimeError("HistoricalSimulator not initialized")
    return _simulator


# ── Request / Response models ──────────────────────────────────────────────


class SimulationRequest(BaseModel):
    symbol: str = "BTCUSDT"
    strategy_id: str
    start: datetime
    end: datetime
    initial_capital: float = 10_000.0
    risk_per_trade_pct: float = 0.02
    commission_pct: float = 0.001
    slippage_pct: float = 0.0005

    @field_validator("end")
    @classmethod
    def end_after_start(cls, v: datetime, info) -> datetime:
        start = info.data.get("start")
        if start and v <= start:
            raise ValueError("end must be after start")
        return v


# ── Background task ────────────────────────────────────────────────────────


def _run_simulation_job(job_id: str, request: SimulationRequest) -> None:
    from core.features.feature_store import FeatureStore

    _jobs[job_id]["status"] = "running"

    try:
        sim = _get_sim()
        reg = _strategy_registry

        if reg is None:
            raise RuntimeError("StrategyRegistry not available")

        strategy = reg.get(request.strategy_id)

        # Load features from store
        feature_store = FeatureStore()
        features = feature_store.get_history(request.symbol, limit=5000)

        if not features:
            raise ValueError(f"No feature data found for {request.symbol}")

        config = SimulationConfig(
            symbol=request.symbol,
            start=request.start,
            end=request.end,
            initial_capital=request.initial_capital,
            risk_per_trade_pct=request.risk_per_trade_pct,
            commission_pct=request.commission_pct,
            slippage_pct=request.slippage_pct,
            strategy_id=request.strategy_id,
        )

        result = sim.run(strategy=strategy, features=features, config=config)
        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["simulation_id"] = result.simulation_id
        _jobs[job_id]["result"] = result.to_dict()

    except Exception as exc:
        logger.error("simulation_job_failed", job_id=job_id, error=str(exc))
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"] = str(exc)


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def run_simulation(
    req: SimulationRequest,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Submit a historical simulation job. Returns a job_id to poll."""
    import uuid

    job_id = str(uuid.uuid4())[:12]
    _jobs[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "strategy_id": req.strategy_id,
        "symbol": req.symbol,
        "submitted_at": datetime.utcnow().isoformat(),
    }
    background_tasks.add_task(_run_simulation_job, job_id, req)
    logger.info(
        "simulation_job_submitted",
        job_id=job_id,
        strategy_id=req.strategy_id,
        user=user.get("sub"),
    )
    return {"job_id": job_id, "status": "queued"}


@router.get("/{job_id}")
async def get_simulation_status(job_id: str, user=Depends(get_current_user)):
    """Check the status of a simulation job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404, detail=f"Simulation job {job_id} not found"
        )
    # Return status without the heavy result payload
    return {k: v for k, v in job.items() if k != "result"}


@router.get("/{job_id}/results")
async def get_simulation_results(job_id: str, user=Depends(get_current_user)):
    """Get full results of a completed simulation."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404, detail=f"Simulation job {job_id} not found"
        )
    if job["status"] != "completed":
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Simulation status: {job['status']}",
        )
    return job.get("result", {})


@router.get("")
async def list_simulations(limit: int = 20, user=Depends(get_current_user)):
    """List recent simulation jobs."""
    sim = _get_sim()
    return {"simulations": sim.list_results(limit=limit)}
