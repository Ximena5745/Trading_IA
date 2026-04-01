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
from pathlib import Path

import pandas as pd

sys.path.insert(0, ".")

from core.agents.technical_agent import TechnicalAgent
from core.backtesting.engine import BacktestEngine
from core.backtesting.metrics import compute_all
from core.features.feature_engineering import FeatureEngine
from core.ingestion.binance_client import BinanceClient
from core.observability.logger import configure_logging, get_logger
from core.config.settings import get_settings
from datetime import datetime, timedelta

configure_logging()
logger = get_logger("run_backtest")
settings = get_settings()


async def run(symbol: str, interval: str, days: int, output: str | None) -> None:
    if days is not None and days < 1000:
        print(
            "⚠️ Backtest requires al menos 1000 velas; ajustando 'days' a 1000"
        )
        days = 1000

    data_path = Path("data/raw/parquet") / interval / f"{symbol.lower()}_{interval}.parquet"
    if data_path.exists():
        print(f"📁 Using local data file: {data_path}")
        df = pd.read_parquet(data_path)
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)
        df["symbol"] = symbol

        if days is not None and len(df) > days:
            df = df.tail(days)

        if len(df) < 1000:
            raise ValueError(
                f"Datos insuficientes para backtest local: se requieren 1000, hay {len(df)}"
            )
    else:
        print("📥 Fetching from Binance API")
        client = BinanceClient(
            api_key=settings.BINANCE_API_KEY,
            secret_key=settings.BINANCE_SECRET_KEY,
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

            df = pd.DataFrame([kv.dict() for kv in klines])
            df["symbol"] = symbol

        finally:
            await client.disconnect()

    print("🔧 Computing walk-forward backtest input")

    model_file = "data/models/technical_agent_v1.pkl"
    if symbol in ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"]:
        model_file = "data/models/technical_forex_v1.pkl"
    elif symbol == "XAUUSD":
        model_file = "data/models/technical_commodity_v1.pkl"
    elif symbol in ["US500", "US30", "UK100"]:
        model_file = "data/models/technical_index_v1.pkl"

    agent = TechnicalAgent(model_path=model_file)

    def strategy_fn(features):
        """Generate trading signals with lower thresholds for more frequent trades."""
        out = agent.predict(features)
        score = out.score
        
        # Bajar thresholds para generar más operaciones (0.15 en vez de 0.30)
        if score >= 0.15:  # BUY signal
            entry = features.close
            return {
                "action": "BUY",
                "entry_price": entry,
                "stop_loss": entry * 0.97,  # tighter SL
                "take_profit": entry * 1.03,  # conservative TP
            }
        if score <= -0.15:  # SELL signal
            entry = features.close
            return {
                "action": "SELL",
                "entry_price": entry,
                "stop_loss": entry * 1.03,
                "take_profit": entry * 0.97,
            }
        return None

    engine = BacktestEngine()
    results = engine.run_walk_forward(
        df,
        strategy_fn,
        train_size=700,      # Entrena con 700 velas
        test_size=200,       # Backtestea con 200 velas (cumple Feature reqs)
        step_size=100,       # Avanza 100 velas por ventana
        initial_capital=10_000.0,
    )

    print("\n" + "=" * 60)
    print(f"  BACKTEST RESULTS: {symbol} ({interval}, {days}d)")
    print("=" * 60)

    for window in results.get("windows", []):
        w_num = window.get("window", "?")
        w_trades = window.get("trades", 0)
        w_sharpe = window.get("sharpe_ratio", 0)
        w_maxdd = window.get("max_drawdown", 0)
        w_wr = window.get("win_rate", 0)
        passed = window.get("passes_thresholds", False)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(
            f"  Window {w_num:02d}: {status} | "
            f"Sharpe={w_sharpe:.2f} | "
            f"MaxDD={w_maxdd*100:.1f}% | "
            f"WR={w_wr*100:.1f}% | "
            f"Trades={w_trades}"
        )

    print("\n  OVERALL METRICS:")
    for key in ["sharpe_ratio", "sortino_ratio", "win_rate", "max_drawdown", "total_trades", "final_capital", "initial_capital"]:
        if key in results:
            value = results[key]
            if key in ["max_drawdown", "win_rate"]:
                print(f"    {key:18s}: {value*100:.2f}%")
            else:
                print(f"    {key:18s}: {value:.4f}")

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(
                {"symbol": symbol, "interval": interval, "windows": results.get("windows", [])},
                f,
                indent=2,
                default=str,
            )
        print(f"\n💾 Results saved to {output_path}")


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
