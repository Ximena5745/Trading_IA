# Script de descarga minimalista (DEBUG)
import requests
import pandas as pd
import json

try:
    # Step 1: Download
    response = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1h", "limit": 10},
        timeout=10
    )
    
    data = response.json()
    
    # Step 2: Convert to DataFrame
    df_data = [
        {
            'timestamp': pd.to_datetime(c[0], unit='ms', utc=True),
            'open': float(c[1]),
            'high': float(c[2]),
            'low': float(c[3]),
            'close': float(c[4]),
            'volume': float(c[5]),
        }
        for c in data
    ]
    
    df = pd.DataFrame(df_data)
    
    # Step 3: Save
    import pathlib
    pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)
    df.to_parquet("data/raw/btcusdt_1h.parquet")
    
    # Log result
    with open("download_result.json", "w") as f:
        json.dump({
            "status": "SUCCESS",
            "records": len(df),
            "columns": list(df.columns),
            "file": "data/raw/btcusdt_1h.parquet"
        }, f, indent=2)

except Exception as e:
    with open("download_result.json", "w") as f:
        json.dump({
            "status": "ERROR",
            "error": str(e),
            "type": type(e).__name__
        }, f, indent=2)
