#!/usr/bin/env python3
"""Script de orquestación FASE 2 (entrenamiento + evaluación).

Uso:
  python scripts/start_phase2.py
"""
from __future__ import annotations

import subprocess
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent

def run(cmd: str):
    print(f"\n> {cmd}")
    result = subprocess.run(cmd, shell=True, check=False, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Comando falló ({result.returncode}): {cmd}")


def main():
    # 1) Asegurar que los datos de FASE 1 están listos
    run('python scripts/download_all_forex.py --period 5y --timeframes "1h,4h,1d,1wk,1mo,6mo,1y"')

    # 2) Entrenamiento de TechnicalAgent por clase de activo
    # (les sirve la ruta data/raw/<SYMBOL>_<TF>.parquet que ahora genera download_all_forex.py)
    run('python scripts/retrain.py --asset-class forex --timeframe 1d --symbols EURUSD GBPUSD USDJPY')
    run('python scripts/retrain.py --asset-class commodity --timeframe 1d --symbols XAUUSD')
    run('python scripts/retrain.py --asset-class index --timeframe 1d --symbols US500 US30')

    # 3) (Opcional) Evaluación futura
    # run_backtest.py acepta --symbol, --interval y --days, no --timeframe/--symbols
    backtest_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'XAUUSD', 'US500', 'US30']
    for symbol in backtest_symbols:
        run(f'python scripts/run_backtest.py --symbol {symbol} --interval 1d --days 1300 --output data/backtest/{symbol}_1d_backtest.json')

    print('\nFASE 2 completada (entrenamiento y backtest inicial).')


if __name__ == '__main__':
    main()
