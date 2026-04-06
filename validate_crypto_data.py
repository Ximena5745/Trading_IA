#!/usr/bin/env python3
"""
Script: validate_crypto_data.py
Validate downloaded CRYPTO data quality and consistency
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path("data/raw")
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["1h", "1d"]

def validate_parquet(symbol: str, timeframe: str) -> dict:
    """Validate a parquet file for data quality"""
    path = DATA_DIR / f"{symbol}_{timeframe}.parquet"
    
    if not path.exists():
        return {"symbol": symbol, "timeframe": timeframe, "status": "❌ NOT FOUND"}
    
    try:
        df = pd.read_parquet(path)
        
        # Check required columns
        required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        missing_cols = required_cols - set(df.columns)
        
        if missing_cols:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": f"❌ Missing columns: {missing_cols}"
            }
        
        # Check for NaN values
        nan_counts = df.isnull().sum()
        if nan_counts.sum() > 0:
            nan_info = dict(nan_counts[nan_counts > 0])
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": f"⚠️ NaN values: {nan_info}"
            }
        
        # Check OHLC validity (high >= low, open/close within range)
        valid_ohlc = (
            (df['high'] >= df['low']) &
            (df['high'] >= df['open']) &
            (df['high'] >= df['close']) &
            (df['low'] <= df['open']) &
            (df['low'] <= df['close'])
        ).sum()
        
        invalid_count = len(df) - valid_ohlc
        if invalid_count > 0:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": f"⚠️ Invalid OHLC: {invalid_count} rows"
            }
        
        # Check timestamps are monotonic
        ts_sorted = df['timestamp'].is_monotonic_increasing
        if not ts_sorted:
            return {
                "symbol": symbol,
                "timeframe": timeframe,
                "status": "⚠️ Timestamps not sorted"
            }
        
        # Stats
        stats = {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": "✅ VALID",
            "rows": len(df),
            "date_range": f"{df['timestamp'].min().date()} to {df['timestamp'].max().date()}",
            "close_min": df['close'].min(),
            "close_max": df['close'].max(),
            "close_mean": df['close'].mean(),
            "volume_total": df['volume'].sum(),
        }
        
        return stats
        
    except Exception as e:
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "status": f"❌ Error: {str(e)}"
        }

def main():
    print("=" * 80)
    print("📊 VALIDACIÓN DE DATOS CRYPTO")
    print("=" * 80)
    
    results = []
    
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            result = validate_parquet(symbol, timeframe)
            results.append(result)
    
    # Display results
    print("\n" + "-" * 80)
    for result in results:
        symbol = result.get("symbol", "?")
        timeframe = result.get("timeframe", "?")
        status = result.get("status", "?")
        
        print(f"\n{symbol} {timeframe:>3}: {status}")
        
        if "rows" in result:
            print(f"  Rows: {result['rows']:,}")
            print(f"  Date Range: {result['date_range']}")
            print(f"  Close: [{result['close_min']:.2f}, {result['close_max']:.2f}], avg={result['close_mean']:.2f}")
            print(f"  Volume Total: {result['volume_total']:.0f}")
    
    print("\n" + "=" * 80)
    print("✨ VALIDACIÓN COMPLETADA")
    print("=" * 80)
    
    # Summary
    valid_count = sum(1 for r in results if "✅" in r.get("status", ""))
    total_count = len(results)
    print(f"\n✓ {valid_count}/{total_count} archivos validados exitosamente")
    
    return 0 if valid_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())
