"""
Module: core/backtesting/metrics.py
Responsibility: Calculate all backtest performance metrics
Dependencies: numpy, pandas
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def sharpe_ratio(returns: list[float], risk_free: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / periods
    std = np.std(excess, ddof=1)
    return float(np.mean(excess) / std * math.sqrt(periods)) if std > 0 else 0.0


def sortino_ratio(returns: list[float], risk_free: float = 0.0, periods: int = 252) -> float:
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns)
    excess = arr - risk_free / periods
    downside = arr[arr < 0]
    downside_std = np.std(downside, ddof=1) if len(downside) > 1 else 0.0
    return float(np.mean(excess) / downside_std * math.sqrt(periods)) if downside_std > 0 else 0.0


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


def compute_all(trades: list[dict], equity_curve: list[float]) -> dict:
    returns = [t.get("net_pnl", 0) / equity_curve[i] for i, t in enumerate(trades) if equity_curve]
    annual_return = sum(returns) if returns else 0.0
    dd = max_drawdown(equity_curve)

    return {
        "sharpe_ratio": round(sharpe_ratio(returns), 4),
        "sortino_ratio": round(sortino_ratio(returns), 4),
        "max_drawdown": round(dd, 4),
        "calmar_ratio": round(calmar_ratio(annual_return, dd), 4),
        "win_rate": round(win_rate(trades), 4),
        "profit_factor": round(profit_factor(trades), 4),
        "expectancy": round(expectancy(trades), 4),
        "total_trades": len(trades),
        "total_return": round(sum(t.get("net_pnl", 0) for t in trades), 4),
    }
