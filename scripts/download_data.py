"""
Script: scripts/download_data.py
Responsibility: Download historical OHLCV data from Binance and save as parquet.
  - Incremental: only downloads missing candles (resume-friendly)
  - Gap detection: logs any gap > 2 consecutive missing candles
  - Output: data/raw/{symbol}_{timeframe}.parquet

Usage:
  python scripts/download_data.py --symbol BTCUSDT --timeframe 1h --years 2
  python scripts/download_data.py --asset-class crypto --years 2
  python scripts/download_data.py --all --years 2
"""
from __future__ import annotations

import argparse
import io
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("download_data")

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "raw"

BINANCE_BASE_URL = "https://api.binance.com/api/v3/klines"

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

# Symbol mapping: Binance → Yahoo Finance
YFINANCE_SYMBOL_MAP = {
    "BTCUSDT": "BTC-USD",
    "ETHUSDT": "ETH-USD",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "JPY=X",
    "XAUUSD": "GC=F",
    "US500": "^GSPC",
    "US30": "^DJI",
}


def _parse_raw_kline(symbol: str, k: list) -> dict:
    """Parse Binance kline data into standardized format."""
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
    """Load existing parquet file if it exists."""
    if not path.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        logger.info("existing_data_loaded", path=str(path), rows=len(df))
        return df
    except Exception as e:
        logger.warning("existing_data_load_failed", path=str(path), error=str(e))
        return pd.DataFrame()


def _download_binance(
    symbol: str, timeframe: str, start_ms: int, end_ms: int
) -> list[dict]:
    """Fetch all klines in [start_ms, end_ms] using pagination (synchronous REST API)."""
    rows: list[dict] = []
    interval = BINANCE_INTERVAL_MAP[timeframe]
    step_ms = TIMEFRAME_MS[timeframe]
    batch_size = 1000
    current_ms = start_ms

    try:
        while current_ms < end_ms:
            batch_end = min(current_ms + step_ms * batch_size, end_ms)
            
            params = {
                "symbol": symbol,
                "interval": interval,
                "startTime": current_ms,
                "endTime": batch_end - 1,
                "limit": batch_size,
            }
            
            response = requests.get(BINANCE_BASE_URL, params=params, timeout=10)
            response.raise_for_status()
            
            raw = response.json()
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
            
            # Rate limiting: Binance allows ~10 requests/sec
            time.sleep(0.2)

    except requests.exceptions.RequestException as e:
        logger.error("binance_download_error", symbol=symbol, error=str(e))
        raise

    return rows


def _download_yfinance(symbol: str, timeframe: str, years: int) -> list[dict]:
    """Download via yfinance (more robust). Maps Binance symbols to Yahoo Finance symbols."""
    import yfinance as yf
    
    # Convert timeframe to yfinance interval
    interval_map = {
        "1m": "1m",
        "5m": "5m", 
        "15m": "15m",
        "1h": "1h",
        "4h": None,  # yfinance doesn't support 4h directly
        "1d": "1d",
    }
    
    if timeframe not in interval_map or interval_map[timeframe] is None:
        logger.warning(f"yfinance doesn't support {timeframe}, skipping")
        return []
    
    # Map symbol to yfinance symbol
    yf_symbol = YFINANCE_SYMBOL_MAP.get(symbol, symbol)
    interval = interval_map[timeframe]
    period = f"{years}y"
    
    try:
        print(f"   📥 Descargando {symbol} ({yf_symbol}) {timeframe} desde yfinance...")
        data = yf.download(yf_symbol, period=period, interval=interval, progress=False)
        
        if data is None or (hasattr(data, 'empty') and data.empty) or len(data) == 0:
            logger.warning("yfinance_empty", symbol=symbol, yf_symbol=yf_symbol)
            return []
        
        # DEBUG: Log data structure
        logger.debug(f"yfinance data shape: {data.shape}, columns: {list(data.columns)}", 
                    has_multiindex=isinstance(data.columns, pd.MultiIndex))
        
        # Handle MultiIndex columns from yfinance
        # For single ticker: [('Close', 'BTC-USD'), ('High', 'BTC-USD'), ...] → [Close, High, Low, Open, Volume]
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel(1)
        
        rows = []
        row_count = 0
        
        for timestamp, row_data in data.iterrows():
            row_count += 1
            try:
                # After flattening yfinance MultiIndex, columns are: [Close, High, Low, Open, Volume]
                # Safer to access by position: [0]=Close, [1]=High, [2]=Low, [3]=Open, [4]=Volume
                
                # Get Close - required value
                close_val = float(row_data.iloc[0])  # Position 0 is Close after droplevel
                
                if close_val <= 0 or pd.isna(close_val):
                    continue
                
                # Get OHLCV by position (yfinance column order after droplevel)
                open_val = float(row_data.iloc[3])      # Position 3 is Open
                high_val = float(row_data.iloc[1])      # Position 1 is High
                low_val = float(row_data.iloc[2])       # Position 2 is Low
                volume_val = float(row_data.iloc[4]) if len(row_data) >= 5 else 0.0  # Position 4 is Volume
                
                # Handle NaN values
                if pd.isna(open_val): open_val = close_val
                if pd.isna(high_val): high_val = close_val
                if pd.isna(low_val): low_val = close_val
                if pd.isna(volume_val): volume_val = 0.0
                
                # Handle timestamp - it already has timezone info from yfinance
                ts = pd.Timestamp(timestamp) if not isinstance(timestamp, pd.Timestamp) else timestamp
                
                rows.append({
                    "timestamp": ts,
                    "symbol": symbol,
                    "open": open_val,
                    "high": max(high_val, open_val, close_val),
                    "low": min(low_val, open_val, close_val),
                    "close": close_val,
                    "volume": volume_val,
                    "quote_volume": close_val * volume_val,
                    "trades_count": 0,
                    "taker_buy_volume": 0,
                })
            except (ValueError, TypeError, IndexError):
                continue
        
        logger.info("yfinance_download_complete", symbol=symbol, yf_symbol=yf_symbol, rows=len(rows), 
                   total_iterated=row_count)
        return rows
        
    except Exception as e:
        logger.error("yfinance_error", symbol=symbol, yf_symbol=yf_symbol, error=str(e))
        return []


def download(symbol: str, timeframe: str, years: int) -> None:
    """Download and save OHLCV data for a symbol."""
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
            print(f"✅ {symbol} {timeframe}: Ya está actualizado (último: {last_ts})")
            return
        logger.info("incremental_download", symbol=symbol, from_ts=str(last_ts))

    # Try Binance first, then yfinance as fallback
    new_rows = None
    try:
        new_rows = _download_binance(symbol, timeframe, start_ms, now_ms)
    except Exception as e:
        print(f"⚠️  Binance falló para {symbol} {timeframe}: {e}")
        print(f"   Intentando con yfinance como alternativa...")
        new_rows = _download_yfinance(symbol, timeframe, years)
    
    if not new_rows:
        logger.warning("no_new_data", symbol=symbol)
        print(f"❌ {symbol} {timeframe}: No se pudo descargar (ambos proveedores fallaron)")
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
        print(f"⚠️  {gap_count} gaps detectados en los datos")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download historical OHLCV data")
    parser.add_argument(
        "--symbol", default=None, help="Trading pair, e.g. BTCUSDT or EURUSD"
    )
    parser.add_argument(
        "--timeframe", default="1h", help="Candle interval: 1m 5m 15m 1h 4h 1d"
    )
    parser.add_argument(
        "--years", type=int, default=2, help="Years of history to download"
    )
    parser.add_argument(
        "--all", action="store_true", help="Download all assets (CRYPTO, FOREX, INDICES, COMMODITIES)"
    )
    parser.add_argument(
        "--asset-class", 
        choices=["crypto", "forex", "indices", "commodities"],
        default=None,
        help="Download all symbols for a specific asset class"
    )
    args = parser.parse_args()

    # Define symbols by asset class
    ASSET_SYMBOLS = {
        "crypto": [
            ("BTCUSDT", ["1h", "4h"]),
            ("ETHUSDT", ["1h", "4h"]),
        ],
        "forex": [
            ("EURUSD", ["1h", "4h", "1d"]),
            ("GBPUSD", ["1h", "4h", "1d"]),
            ("USDJPY", ["1h", "4h", "1d"]),
        ],
        "indices": [
            ("US500", ["1h", "4h", "1d"]),
            ("US30", ["1h", "4h", "1d"]),
        ],
        "commodities": [
            ("XAUUSD", ["1h", "4h", "1d"]),
        ],
    }

    # Build download list
    download_list = []

    if args.all:
        # Download all symbols from all asset classes (only CRYPTO uses binance)
        for asset_class in ASSET_SYMBOLS:
            for symbol, timeframes in ASSET_SYMBOLS[asset_class]:
                for tf in timeframes:
                    download_list.append((symbol, tf))
    elif args.asset_class:
        # Download all symbols from specific asset class
        for symbol, timeframes in ASSET_SYMBOLS[args.asset_class]:
            for tf in timeframes:
                download_list.append((symbol, tf))
    elif args.symbol:
        # Download single symbol
        if args.timeframe not in TIMEFRAME_MS:
            print(f"❌ Invalid timeframe '{args.timeframe}'. Valid: {list(TIMEFRAME_MS)}")
            sys.exit(1)
        download_list.append((args.symbol, args.timeframe))
    else:
        print("❌ Please specify either --symbol, --asset-class, or --all")
        parser.print_help()
        sys.exit(1)

    print("📥 TRADER AI — Download Data (Binance REST API)")
    if args.all:
        print(f"   Mode      : Download ALL assets (CRYPTO, FOREX, INDICES, COMMODITIES)")
    elif args.asset_class:
        print(f"   Mode      : Download all {args.asset_class.upper()} assets")
        if args.asset_class == "crypto":
            print(f"   Provider  : Binance (REST API)")
        else:
            print(f"   Provider  : Binance + MT5/yfinance (based on availability)")
    else:
        print(f"   Symbol    : {args.symbol}")
        print(f"   Timeframe : {args.timeframe}")
    print(f"   Years     : {args.years}")
    print(f"   Total downloads: {len(download_list)}")
    print()

    # Execute downloads (Binance only for now, REST API synchronous)
    completed = 0
    failed = 0
    for symbol, timeframe in download_list:
        try:
            download(symbol, timeframe, args.years)
            completed += 1
        except Exception as e:
            print(f"❌ Failed to download {symbol} {timeframe}: {e}")
            logger.error("download_failed", symbol=symbol, timeframe=timeframe, error=str(e))
            failed += 1

    print()
    print(f"✅ Download complete: {completed} successful, {failed} failed")
    if failed:
        print(f"⚠️  Some downloads failed. Check logs or run again to retry.")


if __name__ == "__main__":
    main()
