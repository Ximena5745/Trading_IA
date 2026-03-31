# Descarga múltiples símbolos y timeframes
import requests
import pandas as pd
import time
from datetime import datetime
import json

def download_data(symbol, timeframe, years):
    """Descarga datos de Binance"""
    BASE_URL = "https://api.binance.com/api/v3/klines"
    LIMIT = 1000
    INTERVAL_MS = {"1h": 3600000, "4h": 14400000}
    
    interval_ms = INTERVAL_MS[timeframe]
    total_ms = years * 365 * 24 * 3600 * 1000
    total_candles_needed = int(total_ms / interval_ms)
    chunks = (total_candles_needed + LIMIT - 1) // LIMIT
    
    all_candles = []
    from datetime import timezone
    current_time = int(datetime.now(timezone.utc).timestamp() * 1000)
    
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
                    time.sleep(0.01)
                    break
            except:
                retries += 1
                time.sleep(2 ** retries)
    
    df = pd.DataFrame(all_candles).sort_values('timestamp').reset_index(drop=True)
    return df

# DESCARGA DE TODOS LOS SÍMBOLOS
symbols_tf = [
    ("BTCUSDT", "4h"),
    ("ETHUSDT", "1h"),
    ("ETHUSDT", "4h"),
]

results = {}

for symbol, tf in symbols_tf:
    print(f"\n📥 Descargando {symbol} {tf}...")
    try:
        df = download_data(symbol, tf, 2)
        fname = f"data/raw/{symbol.lower()}_{tf}.parquet"
        df.to_parquet(fname)
        results[f"{symbol}_{tf}"] = {
            "status": "SUCCESS",
            "records": len(df),
            "file": fname
        }
        print(f"   ✓ {len(df)} candles guardadas")
    except Exception as e:
        results[f"{symbol}_{tf}"] = {"status": "ERROR", "error": str(e)}
        print(f"   ✗ Error: {e}")

with open("download_batch_result.json", "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "="*60)
print("RESUMEN")
print("="*60)
for key, res in results.items():
    if res["status"] == "SUCCESS":
        print(f"✓ {key:20} → {res['records']:,} records")
    else:
        print(f"✗ {key:20} → ERROR")
