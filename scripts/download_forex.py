"""
FASE 1 — Descarga de Forex/Commodities/Índices usando yfinance (fallback)

Uso:
    python scripts/download_forex.py --years 2 --interval 1h
    python scripts/download_forex.py --symbols EURUSD GBPUSD USDJPY --years 2
"""

import argparse
from pathlib import Path
import logging

import pandas as pd
import yfinance as yf

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_SYMBOLS = {
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "XAUUSD": "XAUUSD=X",
    "US500": "SPY",   # proxy SPY
    "US30": "DIA",    # proxy DIA
}


def download_symbol(ticker_symbol: str, yf_symbol: str, years: int, interval: str):
    logger.info(f"Descargando {ticker_symbol} ({yf_symbol}) {years}y {interval}...")
    period = f"{years}y"

    df = yf.download(
        tickers=yf_symbol,
        period=period,
        interval=interval,
        progress=False,
        auto_adjust=False,
        threads=True,
        actions=False,
    )

    if df.empty:
        raise RuntimeError(f"No hay datos para {yf_symbol} (interval={interval}, period={period})")

    # Estandarizar OHLCV y timestamp
    if isinstance(df.index, pd.DatetimeIndex):
        df = df.reset_index()
    else:
        df = df.reset_index()

    df = df.rename(columns={
        'Date': 'timestamp',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Adj Close': 'adj_close',
        'Volume': 'volume'
    })

    # Guardar formato común
    out = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']].copy()
    out['timestamp'] = pd.to_datetime(out['timestamp'], utc=True)

    out_path = Path('data/raw') / f"{ticker_symbol.lower()}_{interval}.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(out_path, index=False, engine='pyarrow')

    logger.info(f"Guardado en {out_path} ({len(out)} filas)")
    return out_path


def main():
    parser = argparse.ArgumentParser(description='Descarga Forex/Commodities/Indices via yfinance')
    parser.add_argument('--years', type=int, default=2, help='Años de histórico')
    parser.add_argument('--interval', type=str, choices=['1h','4h','1d'], default='1h', help='Timeframe')
    parser.add_argument('--symbols', nargs='*', help='Símbolos de destino (EURUSD GBPUSD ...). Por defecto todos')
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else list(DEFAULT_SYMBOLS.keys())

    results = {}
    for symbol in symbols:
        symbol = symbol.upper()
        if symbol not in DEFAULT_SYMBOLS:
            logger.warning(f"Símbolo no configurado: {symbol}. Se omite.")
            continue

        try:
            path = download_symbol(symbol, DEFAULT_SYMBOLS[symbol], args.years, args.interval)
            results[symbol] = {'status': 'OK', 'path': str(path)}
        except Exception as e:
            logger.error(f"Error al descargar {symbol}: {e}")
            results[symbol] = {'status': 'ERROR', 'error': str(e)}

    print('\nRESULTADO')
    for symbol, info in results.items():
        state = info.get('status')
        if state == 'OK':
            print(f"✓ {symbol}: {info['path']}")
        else:
            print(f"✗ {symbol}: {info.get('error')}")


if __name__ == '__main__':
    main()
