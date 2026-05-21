"""
Module: core/backtesting/metrics.py
Responsibility: Calculate all backtest performance metrics
Dependencies: numpy, pandas
"""
from __future__ import annotations

import math

import numpy as np


def sharpe_ratio(
    returns: list[float],
    risk_free: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate Sharpe ratio with correct annualization.

    QWQ-9: Corregir annualization Sharpe - usar sqrt(periods_per_year) dinámico.
    periods_per_year debe ser ajustado según el timeframe:
        - 1h: 24 * 252 = 6048 (si hay 24 horas de trading)
        - 4h: 6 * 252 = 1512
        - 1d: 252
    """
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / periods_per_year
    std = np.std(excess, ddof=1)
    return float(np.mean(excess) / std * math.sqrt(periods_per_year)) if std > 0 else 0.0


def sortino_ratio(
    returns: list[float],
    risk_free: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """Calculate Sortino ratio with correct annualization."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / periods_per_year
    downside = arr[arr < 0]
    downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 0.0
    return (
        float(np.mean(excess) / downside_std * math.sqrt(periods_per_year))
        if downside_std > 0
        else 0.0
    )


def max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    arr = np.array(equity_curve)
    peak = np.maximum.accumulate(arr)
    drawdown = (arr - peak) / peak
    return float(abs(drawdown.min()))


def calmar_ratio(annual_return: float, max_dd: float) -> float:
    return annual_return / max_dd if max_dd > 0 else 0.0


def win_rate(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t.get("net_pnl", 0) > 0)
    return wins / len(trades)


def profit_factor(trades: list[dict]) -> float:
    gross_profit = sum(t["net_pnl"] for t in trades if t.get("net_pnl", 0) > 0)
    gross_loss = abs(sum(t["net_pnl"] for t in trades if t.get("net_pnl", 0) < 0))
    return gross_profit / gross_loss if gross_loss > 0 else float("inf")


def expectancy(trades: list[dict]) -> float:
    if not trades:
        return 0.0
    return sum(t.get("net_pnl", 0) for t in trades) / len(trades)


def omega_ratio(
    returns: list[float],
    threshold: float = 0.0,
) -> float:
    """
    Calculate Omega ratio - measures probability-weighted ratio of gains vs losses.

    Omega = (sum of positive excess returns) / (abs(sum of negative excess returns))
    """
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - threshold
    gains = excess[excess > 0].sum()
    losses = abs(excess[excess < 0].sum())
    return float(gains / losses) if losses > 0 else 0.0


def bootstrap_confidence_interval(
    metric_func: callable,
    returns: list[float],
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> dict:
    """
    Calculate bootstrap confidence interval for a metric.

    Uses resampling with replacement to estimate uncertainty.
    """
    if len(returns) < 10:
        return {"ci_lower": 0.0, "ci_upper": 0.0, "std_error": 0.0}

    arr = np.array(returns)
    bootstrap_samples = []

    np.random.seed(42)
    for _ in range(n_bootstrap):
        sample = np.random.choice(arr, size=len(arr), replace=True)
        bootstrap_samples.append(metric_func(sample.tolist()))

    bootstrap_samples = np.array(bootstrap_samples)
    alpha = 1 - confidence

    return {
        "ci_lower": round(float(np.percentile(bootstrap_samples, alpha / 2 * 100)), 4),
        "ci_upper": round(float(np.percentile(bootstrap_samples, (1 - alpha / 2) * 100)), 4),
        "std_error": round(float(np.std(bootstrap_samples)), 4),
    }


def compute_all(trades: list[dict], equity_curve: list[float]) -> dict:
    returns = [
        t.get("net_pnl", 0) / equity_curve[i]
        for i, t in enumerate(trades)
        if equity_curve and equity_curve[i] != 0
    ]
    annual_return = sum(returns) if returns else 0.0
    dd = max_drawdown(equity_curve)

    sharpe_ci = bootstrap_confidence_interval(
        lambda r: sharpe_ratio(r), returns
    )
    sortino_ci = bootstrap_confidence_interval(
        lambda r: sortino_ratio(r), returns
    )

    return {
        "sharpe_ratio": round(sharpe_ratio(returns), 4),
        "sharpe_ci": sharpe_ci,
        "sortino_ratio": round(sortino_ratio(returns), 4),
        "sortino_ci": sortino_ci,
        "omega_ratio": round(omega_ratio(returns), 4),
        "max_drawdown": round(dd, 4),
        "calmar_ratio": round(calmar_ratio(annual_return, dd), 4),
        "win_rate": round(win_rate(trades), 4),
        "profit_factor": round(profit_factor(trades), 4),
        "expectancy": round(expectancy(trades), 4),
        "total_trades": len(trades),
        "total_return": round(sum(t.get("net_pnl", 0) for t in trades), 4),
    }
