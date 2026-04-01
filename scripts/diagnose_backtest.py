#!/usr/bin/env python3
"""Diagnóstico de por qué los backtests no tienen datos para algunos símbolos."""
from pathlib import Path
import pandas as pd

symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD", "US500", "US30"]
data_dir = Path("data/raw/parquet/1d")

print("=" * 70)
print("DIAGNÓSTICO DE DATOS PARA BACKTEST")
print("=" * 70)

for symbol in symbols:
    parquet_file = data_dir / f"{symbol.lower()}_1d.parquet"
    
    if not parquet_file.exists():
        print(f"❌ {symbol:10s} - ARCHIVO NO EXISTE")
        continue
    
    try:
        df = pd.read_parquet(parquet_file)
        n_rows = len(df)
        
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            min_date = df["timestamp"].min()
            max_date = df["timestamp"].max()
            date_range = f"({min_date.date()} → {max_date.date()})"
        else:
            date_range = "NO TIMESTAMP"
        
        status = "✅ OK" if n_rows >= 1000 else f"⚠️  BAJO ({n_rows} < 1000)"
        print(f"✅ {symbol:10s} - {n_rows:5d} filas {date_range:40s} {status}")
        
    except Exception as e:
        print(f"❌ {symbol:10s} - ERROR: {str(e)}")

print("=" * 70)
print("CÁLCULO DE VENTANAS (train=700, test=200, step=100):")
print("=" * 70)

for symbol in symbols:
    parquet_file = data_dir / f"{symbol.lower()}_1d.parquet"
    if parquet_file.exists():
        df = pd.read_parquet(parquet_file)
        n_rows = len(df)
        train_size = 700
        test_size = 200
        step_size = 100
        
        start = train_size
        windows = 0
        while start + test_size <= n_rows:
            windows += 1
            start += step_size
        
        print(f"{symbol:10s} - {windows:2d} ventanas ({n_rows} filas)")
