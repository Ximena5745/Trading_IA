#!/usr/bin/env python3
"""Analizar datos descargados en data/raw/parquet"""

import pandas as pd
from pathlib import Path

parquet_dir = Path('data/raw/parquet')
parquet_files = sorted(parquet_dir.glob('*.parquet'))

print('=' * 70)
print('ANÁLISIS DE DATOS DESCARGADOS EN data/raw/parquet')
print('=' * 70)
print()

total_files = len(parquet_files)
print(f'Total archivos encontrados: {total_files}\n')

for i, file in enumerate(parquet_files[:10], 1):
    try:
        df = pd.read_parquet(file)
        n_records = len(df)
        date_min = df['timestamp'].min()
        date_max = df['timestamp'].max()
        date_range_days = (date_max - date_min).days
        
        print(f'{i}. {file.name}')
        print(f'   Registros: {n_records}')
        print(f'   Rango: {date_min} a {date_max}')
        print(f'   Período: {date_range_days} días')
        print()
    except Exception as e:
        print(f'{i}. {file.name}: ERROR - {e}')
        print()

print('\n' + '=' * 70)
print('RESUMEN')
print('=' * 70)
print(f'Total de archivos parquet: {total_files}')
print('\nOBSERVACIONES:')
print('- Los archivos presentes son de timeframes largos (1mo, 1wk, 6mo)')
print('- Para entrenamiento de modelos se necesitan timeframes cortos (1h, 4h)')
print('- Los datos descargados parecen ser limitados (pocos registros)')
print('- ACCIÓN REQUERIDA: Ejecutar scripts/download_all_forex.py con timeframes 1h y 4h')
