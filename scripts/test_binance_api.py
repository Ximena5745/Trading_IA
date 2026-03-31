"""
Test de Binance API - con logging a archivo
"""
import requests
import pandas as pd

output_file = "test_output.txt"

def log(msg):
    with open(output_file, "a") as f:
        f.write(msg + "\n")
    print(msg)

# Clear previous output
with open(output_file, "w") as f:
    f.write("")

try:
    log("[1] Iniciando test...")
    
    log("[2] Testando Binance API...")
    response = requests.get(
        "https://api.binance.com/api/v3/klines",
        params={"symbol": "BTCUSDT", "interval": "1h", "limit": 5},
        timeout=10
    )
    log(f"[2] Status: {response.status_code}")
    
    data = response.json()
    log(f"[2] Candles recibidos: {len(data)}")
    
    log("[3] Convirtiendo a DataFrame...")
    df_data = [{
        'timestamp': pd.to_datetime(c[0], unit='ms', utc=True),
        'open': float(c[1]),
        'close': float(c[4]),
    } for c in data]
    
    df = pd.DataFrame(df_data)
    log(f"[3] DataFrame shape: {df.shape}")
    
    log("[4] Creando directorios...")
    import pathlib
    pathlib.Path("data/raw").mkdir(parents=True, exist_ok=True)
    log("[4] Directorio data/raw/ OK")
    
    log("[5] Guardando Parquet...")
    df.to_parquet("data/raw/btcusdt_test.parquet")
    log("[5] ✓ Guardado: data/raw/btcusdt_test.parquet")
    
    log("\n✓✓✓ ÉXITO - Todo funciona correctamente")
    
except Exception as e:
    log(f"\n✗✗✗ ERROR: {type(e).__name__}: {e}")
    import traceback
    log(traceback.format_exc())
