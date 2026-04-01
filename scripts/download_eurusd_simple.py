import yfinance as yf
import pandas as pd
from pathlib import Path

print("Descargando EURUSD...")

try:
    # Descargar EURUSD
    df = yf.download("EURUSD=X", period="2y", interval="1h", progress=False)
    print(f"Datos descargados: {len(df)} filas")

    # Procesar
    df = df.reset_index()
    df = df.rename(columns={
        'Date': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    out_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

    # Guardar
    Path("data/raw").mkdir(parents=True, exist_ok=True)
    out_df.to_parquet("data/raw/eurusd_1h.parquet", index=False)
    print("Guardado en data/raw/eurusd_1h.parquet")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()