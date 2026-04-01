"""
Script: scripts/download_data.py
Responsibility: Download historical OHLCV data from Binance and save as parquet.
  - Incremental: only downloads missing candles (resume-friendly)
  - Gap detection: logs any gap > 2 consecutive missing candles
  - Output: data/raw/{symbol}_{timeframe}.parquet

Usage:
  python scripts/download_data.py --symbol BTCUSDT --timeframe 1h --years 2
  python scripts/download_data.py --symbol ETHUSDT --timeframe 1h --years 2
  python scripts/download_data.py --symbol BTCUSDT --timeframe 4h --years 3

  # FASE E — MT5 provider (requires terminal running)
  python scripts/download_data.py --symbol EURUSD  --timeframe 1h --years 2 --provider mt5
  python scripts/download_data.py --symbol XAUUSD  --timeframe 1h --years 2 --provider mt5
"""
from __future__ import annotations

import argparse
import asyncio
import io
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("download_data")

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"

TIMEFRAME_MS: dict[str, int] = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

BINANCE_INTERVAL_MAP = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


def _parse_raw_kline(symbol: str, k: list) -> dict:
    return {
        "timestamp": pd.Timestamp(k[0], unit="ms", tz="UTC"),
        "symbol": symbol,
        "open": float(k[1]),
        "high": float(k[2]),
        "low": float(k[3]),
        "close": float(k[4]),
        "volume": float(k[5]),
        "quote_volume": float(k[7]),
        "trades_count": int(k[8]),
        "taker_buy_volume": float(k[9]),
    }


def _detect_gaps(df: pd.DataFrame, timeframe: str) -> int:
    """Return count of gaps > 2 consecutive missing candles."""
    if len(df) < 2:
        return 0
    expected_ms = TIMEFRAME_MS[timeframe]
    timestamps = df["timestamp"].astype("int64") // 1_000_000  # ms
    diffs = timestamps.diff().dropna()
    gaps = diffs[diffs > expected_ms * 2]
    if not gaps.empty:
        for idx, gap_ms in gaps.items():
            gap_candles = int(gap_ms / expected_ms) - 1
            ts = df.loc[idx, "timestamp"]
            logger.warning(
                "data_gap_detected",
                symbol=df["symbol"].iloc[0],
                at=str(ts),
                missing_candles=gap_candles,
            )
    return len(gaps)


def _load_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        logger.info("existing_data_loaded", path=str(path), rows=len(df))
        return df
    except Exception as e:
        logger.warning("existing_data_load_failed", path=str(path), error=str(e))
        return pd.DataFrame()


async def _download_binance(
    symbol: str, timeframe: str, start_ms: int, end_ms: int
) -> list[dict]:
    """Fetch all klines in [start_ms, end_ms] using pagination."""
    from binance.client import AsyncClient

    client = await AsyncClient.create()
    rows: list[dict] = []
    interval = BINANCE_INTERVAL_MAP[timeframe]
    step_ms = TIMEFRAME_MS[timeframe]
    batch_size = 1000
    current_ms = start_ms

    try:
        while current_ms < end_ms:
            batch_end = min(current_ms + step_ms * batch_size, end_ms)
            raw = await client.get_klines(
                symbol=symbol,
                interval=interval,
                startTime=current_ms,
                endTime=batch_end - 1,
                limit=batch_size,
            )
            if not raw:
                break
            rows.extend(_parse_raw_kline(symbol, k) for k in raw)
            current_ms = int(raw[-1][0]) + step_ms
            logger.info(
                "batch_downloaded",
                symbol=symbol,
                fetched=len(raw),
                total=len(rows),
                up_to=str(pd.Timestamp(raw[-1][0], unit="ms")),
            )
    finally:
        await client.close_connection()

    return rows


async def download(symbol: str, timeframe: str, years: int) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{symbol}_{timeframe}.parquet"

    existing = _load_existing(out_path)
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    target_start = now_ms - years * 365 * 24 * 3_600_000

    if existing.empty:
        start_ms = target_start
        logger.info("fresh_download", symbol=symbol, timeframe=timeframe, years=years)
    else:
        last_ts = existing["timestamp"].max()
        start_ms = int(last_ts.timestamp() * 1000) + TIMEFRAME_MS[timeframe]
        if start_ms >= now_ms - TIMEFRAME_MS[timeframe]:
            logger.info("data_up_to_date", symbol=symbol, last=str(last_ts))
            return
        logger.info("incremental_download", symbol=symbol, from_ts=str(last_ts))

    new_rows = await _download_binance(symbol, timeframe, start_ms, now_ms)
    if not new_rows:
        logger.warning("no_new_data", symbol=symbol)
        return

    new_df = pd.DataFrame(new_rows)
    combined = (
        pd.concat([existing, new_df], ignore_index=True)
        if not existing.empty
        else new_df
    )
    combined = (
        combined.drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    gap_count = _detect_gaps(combined, timeframe)
    combined.to_parquet(out_path, index=False)

    logger.info(
        "download_complete",
        symbol=symbol,
        timeframe=timeframe,
        rows=len(combined),
        gaps=gap_count,
        path=str(out_path),
    )
    print(f"✅ {symbol} {timeframe}: {len(combined):,} candles guardadas en {out_path}")
    if gap_count:
        print(f"⚠️  {gap_count} gaps detectados en los datos — revisar el log")


async def _download_mt5(symbol: str, timeframe: str, years: int) -> None:
    """Download historical data via MT5 (FASE E)."""
    from core.config.settings import get_settings
    from core.ingestion.providers.mt5_client import MT5Client

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / f"{symbol}_{timeframe}.parquet"
    existing = _load_existing(out_path)

    settings = get_settings()
    # MT5 connection settings come from environment (add to .env for FASE E):
    mt5_server = getattr(settings, "MT5_SERVER", "ICMarketsSC-Demo04")
    mt5_login = int(getattr(settings, "MT5_LOGIN", "0"))
    mt5_password = getattr(settings, "MT5_PASSWORD", "")

    client = MT5Client(server=mt5_server, login=mt5_login, password=mt5_password)
    await client.connect()

    bars_needed = years * 365 * 24  # rough estimate for 1h; adjust for other TFs
    try:
        candles = await client.get_historical_klines(
            symbol, timeframe, min(bars_needed, 50000)
        )
    finally:
        await client.disconnect()

    if not candles:
        print(f"⚠️  No data returned from MT5 for {symbol}")
        return

    rows = [
        {
            "timestamp": c.timestamp,
            "symbol": c.symbol,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume),
        }
        for c in candles
    ]
    new_df = pd.DataFrame(rows)
    combined = (
        pd.concat([existing, new_df], ignore_index=True)
        if not existing.empty
        else new_df
    )
    combined = (
        combined.drop_duplicates(subset=["timestamp"])
        .sort_values("timestamp")
        .reset_index(drop=True)
    )
    gap_count = _detect_gaps(combined, timeframe)
    combined.to_parquet(out_path, index=False)
    print(f"✅ {symbol} {timeframe} (MT5): {len(combined):,} candles → {out_path}")
    if gap_count:
        print(f"⚠️  {gap_count} gaps detectados")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical OHLCV data")
    parser.add_argument(
        "--symbol", default="BTCUSDT", help="Trading pair, e.g. BTCUSDT or EURUSD"
    )
    parser.add_argument(
        "--timeframe", default="1h", help="Candle interval: 1m 5m 15m 1h 4h 1d"
    )
    parser.add_argument(
        "--years", type=int, default=2, help="Years of history to download"
    )
    parser.add_argument(
        "--provider",
        default="binance",
        choices=["binance", "mt5"],
        help="Data provider: binance (default) or mt5 (FASE E)",
    )
    args = parser.parse_args()

    if args.timeframe not in TIMEFRAME_MS:
        print(f"❌ Invalid timeframe '{args.timeframe}'. Valid: {list(TIMEFRAME_MS)}")
        sys.exit(1)

    print("📥 TRADER AI — Download Data")
    print(f"   Symbol    : {args.symbol}")
    print(f"   Timeframe : {args.timeframe}")
    print(f"   Years     : {args.years}")
    print(f"   Provider  : {args.provider}")

    if args.provider == "mt5":
        asyncio.run(_download_mt5(args.symbol, args.timeframe, args.years))
    else:
        asyncio.run(download(args.symbol, args.timeframe, args.years))


if __name__ == "__main__":
    main()
