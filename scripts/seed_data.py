"""
Script: scripts/seed_data.py
Responsibility: Seed TimescaleDB with historical Binance candles for development
Usage: python scripts/seed_data.py --symbol BTCUSDT --interval 1h --days 90
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, ".")

from core.config.settings import get_settings
from core.ingestion.binance_client import BinanceClient
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("seed_data")

settings = get_settings()


async def seed(symbol: str, interval: str, days: int) -> None:
    client = BinanceClient(
        api_key=settings.BINANCE_API_KEY,
        api_secret=settings.BINANCE_API_SECRET,
        testnet=settings.BINANCE_TESTNET,
    )

    await client.connect()
    logger.info("seed_start", symbol=symbol, interval=interval, days=days)

    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)

    try:
        klines = await client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_dt,
            end_time=end_dt,
        )
        logger.info("seed_fetched", symbol=symbol, candles=len(klines))

        # Print sample
        for k in klines[:3]:
            print(
                f"  {k.timestamp} O={k.open} H={k.high} L={k.low} C={k.close} V={k.volume}"
            )

        print(
            f"\n✅ Fetched {len(klines)} candles for {symbol} ({interval}) over last {days} days"
        )
        print("   Connect a TimescaleDB writer to persist these to the DB.")

    finally:
        await client.disconnect()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed market data from Binance")
    parser.add_argument(
        "--symbol", default="BTCUSDT", help="Trading pair (default: BTCUSDT)"
    )
    parser.add_argument(
        "--interval", default="1h", help="Candle interval (default: 1h)"
    )
    parser.add_argument(
        "--days", type=int, default=90, help="Days of history (default: 90)"
    )
    args = parser.parse_args()

    asyncio.run(seed(args.symbol, args.interval, args.days))


if __name__ == "__main__":
    main()
