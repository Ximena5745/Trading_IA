import pandas as pd
from pathlib import Path

print("Iniciando validación simple...")

# Listar archivos
files = list(Path('data/raw').glob('*.parquet'))
print(f"Archivos encontrados: {len(files)}")

for f in files:
    print(f"Procesando {f.name}...")
    try:
        df = pd.read_parquet(f)
        print(f"  Filas: {len(df)}")
        print(f"  Columnas: {list(df.columns)}")
        print(f"  Rango: {df['timestamp'].min()} a {df['timestamp'].max()}")

        # Validaciones básicas
        if len(df) == 0:
            print("  ERROR: DataFrame vacío")
            continue

        # Check OHLC consistency
        high_ok = (df['high'] >= df[['open', 'close']].max(axis=1)).all()
        low_ok = (df['low'] <= df[['open', 'close']].min(axis=1)).all()

        print(f"  High >= OHLC: {high_ok}")
        print(f"  Low <= OHLC: {low_ok}")

        if high_ok and low_ok:
            print("  ✓ Validación básica PASSED")
        else:
            print("  ✗ Validación básica FAILED")

    except Exception as e:
        print(f"  ERROR: {e}")

print("Validación completada.")