"""
Module: api/routes/backtesting.py
Responsibility: Async backtest job submission and results
Dependencies: require_trader, BacktestEngine
"""
from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
    return {k: v for k, v in job.items() if k != "results"}


@router.get("/{job_id}/results")
async def get_backtest_results(job_id: str, _: dict = Depends(require_trader)):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
        )
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


# ============================================================================
# CRYPTO VALIDATION ENDPOINTS
# ============================================================================

@router.get("/crypto/validation")
async def get_crypto_validation(_: dict = Depends(require_trader)):
    """Get comprehensive crypto backtesting validation results with realistic costs"""
    results_dir = Path("backtest_results")
    val_file = results_dir / "comprehensive_validation.json"
    
    if not val_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation results not found. Run validate_crypto_deployment.py first"
        )
    
    with open(val_file, 'r') as f:
        validation_data = json.load(f)
    
    return validation_data


@router.get("/crypto/config")
async def get_crypto_config(_: dict = Depends(require_trader)):
    """Get live trading configuration for CRYPTO models"""
    results_dir = Path("backtest_results")
    config_file = results_dir / "live_trading_config.json"
    
    if not config_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Config not found"
        )
    
    with open(config_file, 'r') as f:
        config_data = json.load(f)
    
    return config_data


@router.get("/crypto/reports/{symbol}")
async def get_crypto_report(symbol: str, _: dict = Depends(require_trader)):
    """Get backtest report for specific symbol"""
    results_dir = Path("backtest_results")
    report_file = results_dir / f"report_{symbol}_1h.json"
    
    if not report_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report not found for {symbol}"
        )
    
    with open(report_file, 'r') as f:
        report_data = json.load(f)
    
    return report_data


@router.get("/crypto/summary")
async def get_crypto_summary(_: dict = Depends(require_trader)):
    """Get quick summary of crypto validation results"""
    results_dir = Path("backtest_results")
    val_file = results_dir / "comprehensive_validation.json"
    
    if not val_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Validation results not found"
        )
    
    with open(val_file, 'r') as f:
        val_data = json.load(f)
    
    results = val_data.get('results', {})
    
    # Aggregate summary
    btcusdt = results.get('BTCUSDT', {})
    ethusdt = results.get('ETHUSDT', {})
    
    summary = {
        'timestamp': val_data.get('timestamp'),
        'models_approved': sum(1 for r in results.values() if r.get('status') == 'APPROVED'),
        'total_models': len(results),
        'btcusdt': {
            'return': btcusdt.get('realistic_return'),
            'win_rate': btcusdt.get('win_rate'),
            'profit_factor': btcusdt.get('profit_factor'),
            'sharpe_ratio': btcusdt.get('sharpe_ratio'),
            'status': btcusdt.get('status')
        },
        'ethusdt': {
            'return': ethusdt.get('realistic_return'),
            'win_rate': ethusdt.get('win_rate'),
            'profit_factor': ethusdt.get('profit_factor'),
            'sharpe_ratio': ethusdt.get('sharpe_ratio'),
            'status': ethusdt.get('status')
        },
        'avg_sharpe': (btcusdt.get('sharpe_ratio', 0) + ethusdt.get('sharpe_ratio', 0)) / 2,
        'avg_return': (btcusdt.get('realistic_return', 0) + ethusdt.get('realistic_return', 0)) / 2
    }
    
    return summary
