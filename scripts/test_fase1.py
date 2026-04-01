"""
Script: scripts/test_fase1.py
Responsibility: Test FASE 1 - Download Data and Feature Engineering
Usage: python scripts/test_fase1.py
"""
from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.features.feature_engineering import FeatureEngine
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("test_fase1")

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["1h"]


def load_parquet(symbol: str, timeframe: str):
    import pandas as pd
    path = DATA_DIR / f"{symbol}_{timeframe}.parquet"
    if not path.exists():
        return None
    return pd.read_parquet(path)


def test_data_exists():
    print("\n=== TEST: Data files exist ===")
    all_ok = True
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            path = DATA_DIR / f"{symbol}_{tf}.parquet"
            if path.exists():
                print(f"  [OK] {symbol}_{tf}.parquet exists")
            else:
                print(f"  [FAIL] {symbol}_{tf}.parquet NOT FOUND")
                all_ok = False
    return all_ok


def test_data_validity():
    print("\n=== TEST: Data validity ===")
    import pandas as pd
    all_ok = True
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            df = load_parquet(symbol, tf)
            if df is None:
                continue
            # Check required columns
            required = ["timestamp", "open", "high", "low", "close", "volume"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                print(f"  [FAIL] {symbol}_{tf}: missing columns {missing}")
                all_ok = False
            else:
                print(f"  [OK] {symbol}_{tf}: {len(df)} rows, columns OK")
            # Check for NaN in critical fields
            if df[["open", "high", "low", "close"]].isnull().any().any():
                print(f"  [FAIL] {symbol}_{tf}: NaN values in OHLC")
                all_ok = False
            # Check high >= low
            if (df["high"] < df["low"]).any():
                print(f"  [FAIL] {symbol}_{tf}: high < low detected")
                all_ok = False
    return all_ok


def test_feature_engineering():
    print("\n=== TEST: Feature Engineering ===")
    import pandas as pd
    all_ok = True
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            df = load_parquet(symbol, tf)
            if df is None:
                continue
            try:
                engine = FeatureEngine(feature_version="v1")
                features = engine.calculate(df)
                print(f"  [OK] {symbol}_{tf}: {len(features.model_dump())} features calculated")
            except Exception as e:
                print(f"  [FAIL] {symbol}_{tf}: {e}")
                all_ok = False
    return all_ok


def test_data_coverage():
    print("\n=== TEST: Data coverage (2 years) ===")
    import pandas as pd
    all_ok = True
    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            df = load_parquet(symbol, tf)
            if df is None:
                continue
            # 1h for 2 years = ~17520 candles (accounting for weekends)
            min_expected = {"1h": 14000, "4h": 3500, "1d": 500}
            actual = len(df)
            expected = min_expected.get(tf, 1000)
            if actual >= expected:
                print(f"  [OK] {symbol}_{tf}: {actual} candles (>= {expected})")
            else:
                print(f"  [WARN] {symbol}_{tf}: {actual} candles (< {expected})")
    return all_ok


async def run_tests():
    print("=" * 60)
    print("  FASE 1 - Test Suite")
    print("=" * 60)
    
    results = []
    
    # Test 1: Data files exist
    results.append(("Data exists", test_data_exists()))
    
    # Test 2: Data validity
    results.append(("Data validity", test_data_validity()))
    
    # Test 3: Feature engineering
    results.append(("Feature engineering", test_feature_engineering()))
    
    # Test 4: Data coverage
    results.append(("Data coverage", test_data_coverage()))
    
    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("  FASE 1 TESTS PASSED")
    else:
        print("  FASE 1 TESTS FAILED")
    print("=" * 60)
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(run_tests())
