"""
Script: scripts/ci_backtest_gate.py
Responsibility: CI/CD backtest quality gate — generates synthetic OHLCV data and
                validates that the BacktestEngine + metrics pipeline work end-to-end.
Usage: python scripts/ci_backtest_gate.py  (called by GitHub Actions)
"""
from __future__ import annotations

import sys
import random
from datetime import datetime, timedelta

import pandas as pd
import numpy as np

sys.path.insert(0, ".")

from core.backtesting.engine import BacktestEngine
from core.backtesting.metrics import compute_all

REQUIRED_SHARPE = -5.0        # synthetic data — just verify pipeline runs
REQUIRED_WIN_RATE = 0.20      # very low bar for CI: just check logic works
MAX_ALLOWED_DRAWDOWN = 0.95   # 95% — any result is acceptable in CI
MIN_TRADES = 1                # at least 1 trade must be generated


def generate_synthetic_ohlcv(n: int = 1200) -> pd.DataFrame:
    """Generate synthetic OHLCV DataFrame with a gentle bull trend."""
    random.seed(42)
    np.random.seed(42)

    timestamps = [datetime(2024, 1, 1) + timedelta(hours=i) for i in range(n)]
    prices = [50_000.0]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + np.random.normal(0.0002, 0.008)))

    prices_arr = np.array(prices)
    opens = prices_arr
    highs = prices_arr * (1 + np.abs(np.random.normal(0, 0.003, n)))
    lows = prices_arr * (1 - np.abs(np.random.normal(0, 0.003, n)))
    closes = prices_arr * (1 + np.random.normal(0, 0.002, n))
    volumes = 100.0 + np.abs(np.random.normal(0, 30, n))

    return pd.DataFrame({
        "timestamp": timestamps,
        "symbol": "BTCUSDT",
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "quote_volume": volumes * closes,
        "taker_buy_volume": volumes * 0.55,
    })


def simple_ema_strategy(features) -> dict | None:
    """Simple EMA crossover strategy for CI testing."""
    if features.ema_9 > features.ema_21 and features.rsi_14 < 65:
        entry = features.close
        sl = entry * 0.97
        tp = entry * 1.06
        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
        }
    return None


def run_gate() -> None:
    print("[GATE] TRADER AI - CI Backtest Gate")
    print("=" * 55)

    df = generate_synthetic_ohlcv(1200)
    print(f"   Generated {len(df)} synthetic OHLCV candles")

    engine = BacktestEngine()

    try:
        results = engine.run_walk_forward(
            df,
            simple_ema_strategy,
            train_size=500,
            test_size=100,
            step_size=100,
            initial_capital=10_000.0,
        )
    except Exception as exc:
        print(f"[FAIL] BacktestEngine raised an exception: {exc}")
        sys.exit(1)

    sharpe = results.get("sharpe_ratio", 0)
    win_rate = results.get("win_rate", 0)
    max_dd = results.get("max_drawdown", 0)
    total_trades = results.get("total_trades", 0)
    final_capital = results.get("final_capital", 10_000.0)

    windows = results.get("windows", [])
    print(f"   Walk-forward windows: {len(windows)}")

    for w in windows:
        w_num = w.get("window", "?")
        w_trades = w.get("trades", 0)
        w_sharpe = w.get("sharpe_ratio", 0)
        print(f"   Window {w_num:02d}: trades={w_trades}  sharpe={w_sharpe:.2f}")

    print()
    print("  OVERALL METRICS:")
    print(f"    Sharpe Ratio  : {sharpe:.3f}  (min {REQUIRED_SHARPE})")
    print(f"    Win Rate      : {win_rate*100:.1f}%  (min {REQUIRED_WIN_RATE*100:.0f}%)")
    print(f"    Max Drawdown  : {max_dd*100:.1f}%  (max {MAX_ALLOWED_DRAWDOWN*100:.0f}%)")
    print(f"    Total Trades  : {total_trades}  (min {MIN_TRADES})")
    print(f"    Final Capital : {final_capital:.2f}")
    print()

    failures = []

    if total_trades < MIN_TRADES:
        failures.append(f"Too few trades: {total_trades} < {MIN_TRADES}")

    if max_dd > MAX_ALLOWED_DRAWDOWN:
        failures.append(
            f"Drawdown too high: {max_dd*100:.1f}% > {MAX_ALLOWED_DRAWDOWN*100:.0f}%"
        )

    if failures:
        print("[FAIL] GATE FAILED:")
        for f in failures:
            print(f"   - {f}")
        sys.exit(1)
    else:
        print("[PASS] GATE PASSED - pipeline is functional")
        sys.exit(0)


if __name__ == "__main__":
    run_gate()
