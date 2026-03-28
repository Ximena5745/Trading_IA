"""
Script: scripts/run_backtest.py
Responsibility: CLI to run walk-forward backtest and print results
Usage: python scripts/run_backtest.py --symbol BTCUSDT --interval 1h --days 365
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

sys.path.insert(0, ".")

from datetime import datetime, timedelta

from core.backtesting.engine import BacktestEngine
from core.backtesting.metrics import compute_all
from core.config.settings import get_settings
from core.features.feature_engineering import FeatureEngine
from core.ingestion.binance_client import BinanceClient
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("run_backtest")
settings = get_settings()


async def run(symbol: str, interval: str, days: int, output: str | None) -> None:
    client = BinanceClient(
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        testnet=settings.BINANCE_TESTNET,
    )
    await client.connect()

    try:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=days)

        print(f"📥 Fetching {days} days of {interval} candles for {symbol}...")
        klines = await client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_dt,
            end_time=end_dt,
        )
        print(f"   → {len(klines)} candles fetched")

        if len(klines) < 300:
            print("❌ Not enough data for backtesting (need ≥ 300 candles)")
            return

        print("🔧 Computing features...")
        engine = FeatureEngine()
        features = engine.calculate_batch(klines)
        print(f"   → {len(features)} feature sets computed")

        print("⚙️  Running walk-forward backtest...")
        backtest = BacktestEngine()
        results = backtest.run_walk_forward(features, symbol=symbol)

        print("\n" + "=" * 60)
        print(f"  BACKTEST RESULTS: {symbol} ({interval}, {days}d)")
        print("=" * 60)

        all_pnls = []
        for i, window in enumerate(results):
            pnls = window.get("trade_pnls", [])
            all_pnls.extend(pnls)
            m = compute_all(pnls) if pnls else {}
            passed = window.get("passes_thresholds", False)
            status = "✅ PASS" if passed else "❌ FAIL"
            print(
                f"  Window {i+1:02d}: {status} | "
                f"Sharpe={m.get('sharpe_ratio', 0):.2f} | "
                f"MaxDD={m.get('max_drawdown', 0)*100:.1f}% | "
                f"WR={m.get('win_rate', 0)*100:.1f}% | "
                f"Trades={len(pnls)}"
            )

        if all_pnls:
            overall = compute_all(all_pnls)
            print("\n  OVERALL METRICS:")
            for k, v in overall.items():
                print(f"    {k:25s}: {v:.4f}")

        print("=" * 60)

        if output:
            with open(output, "w") as f:
                json.dump(
                    {"symbol": symbol, "interval": interval, "windows": results},
                    f,
                    indent=2,
                    default=str,
                )
            print(f"\n💾 Results saved to {output}")

    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run walk-forward backtest")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1h")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--output", help="Save JSON results to file", default=None)
    args = parser.parse_args()

    asyncio.run(run(args.symbol, args.interval, args.days, args.output))


if __name__ == "__main__":
    main()
