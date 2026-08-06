"""
Script: scripts/seed_data.py
Responsibility: Seed TimescaleDB with historical Binance candles for development
Usage: python scripts/seed_data.py --symbol BTCUSDT --interval 1h --days 90
"""
from __future__ import annotations

import argparse
import asyncio
import sys

sys.path.insert(0, ".")

from core.config.settings import get_settings
from core.ingestion.binance_client import BinanceClient
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("seed_data")

settings = get_settings()

# Candles/day per interval, used to size the `limit` passed to get_klines
# (Binance caps a single klines request at 1000 candles).
_CANDLES_PER_DAY = {
    "1m": 1440, "5m": 288, "15m": 96, "1h": 24, "4h": 6, "1d": 1,
}


async def seed(symbol: str, interval: str, days: int) -> None:
    client = BinanceClient(
        api_key=settings.BINANCE_API_KEY,
        secret_key=settings.BINANCE_SECRET_KEY,
        testnet=settings.BINANCE_TESTNET,
    )

    await client.connect()
    logger.info("seed_start", symbol=symbol, interval=interval, days=days)

    per_day = _CANDLES_PER_DAY.get(interval, 24)
    limit = min(days * per_day, 1000)  # Binance klines cap per request

    try:
        klines = await client.get_klines(symbol, interval, limit)
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
