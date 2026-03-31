# FASE 1 — Descarga 2 años BTCUSDT 1h desde Binance
import requests
import pandas as pd
import time
from datetime import datetime, timedelta
import json

def download_years_of_data(symbol, timeframe, years):
    """Descarga N años de datos con paginación"""
    
    BASE_URL = "https://api.binance.com/api/v3/klines"
    LIMIT = 1000  # Max per request
    INTERVAL_MS = {
        "1h": 3600 * 1000,
        "4h": 4 * 3600 * 1000,
    }
    
    interval_ms = INTERVAL_MS[timeframe]
    total_ms = years * 365 * 24 * 3600 * 1000
    total_candles_needed = int(total_ms / interval_ms)
    chunks = (total_candles_needed + LIMIT - 1) // LIMIT
    
    all_candles = []
    current_time = int(datetime.utcnow().timestamp() * 1000)
    
    for chunk_idx in range(chunks):
        end_time = current_time - (chunk_idx * LIMIT * interval_ms)
        start_time = end_time - (LIMIT * interval_ms)
        
        retries = 0
        while retries < 3:
            try:
                r = requests.get(BASE_URL, params={
                    "symbol": symbol,
                    "interval": timeframe,
                    "startTime": start_time,
                    "endTime": end_time,
                    "limit": LIMIT,
                }, timeout=10)
                
                if r.status_code == 200:
                    data = r.json()
                    if not data:
                        break
                    
                    for c in data:
                        all_candles.append({
                            'timestamp': pd.to_datetime(c[0], unit='ms', utc=True),
                            'open': float(c[1]),
                            'high': float(c[2]),
                            'low': float(c[3]),
                            'close': float(c[4]),
                            'volume': float(c[5]),
                        })
                    
                    time.sleep(0.01)  # Rate limit
                    break
            except Exception as e:
                retries += 1
                time.sleep(2 ** retries)
        
        if (chunk_idx + 1) % 5 == 0:
            print(f"Progress: {chunk_idx + 1}/{chunks} chunks downloaded")
    
    df = pd.DataFrame(all_candles).sort_values('timestamp').reset_index(drop=True)
    return df

try:
    print("=" * 60)
    print("DESCARGANDO BTCUSDT 1h - 2 AÑOS")
    print("=" * 60)
    
    # Download
    print("Descargando...")
    df = download_years_of_data("BTCUSDT", "1h", 2)
    
    # Save
    print(f"\nGuardando {len(df)} candles...")
    import pathlib
    pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_parquet("data/raw/btcusdt_1h.parquet")
    
    # Result
    result = {
        "status": "SUCCESS",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "candles": len(df),
        "date_range": {
            "start": str(df['timestamp'].min()),
            "end": str(df['timestamp'].max()),
        },
        "file": "data/raw/btcusdt_1h.parquet"
    }
    
    with open("download_result.json", "w") as f:
        json.dump(result, f, indent=2)
    
    print(f"✓ ÉXITO: {len(df)} candles descargadas")
    print(f"  Período: {df['timestamp'].min()} a {df['timestamp'].max()}")
    print(f"  Archivo: data/raw/btcusdt_1h.parquet")

except Exception as e:
    result = {
        "status": "ERROR",
        "error": str(e),
        "type": type(e).__name__
    }
    with open("download_result.json", "w") as f:
        json.dump(result, f, indent=2)
