import argparse
import yfinance as yf
import pandas as pd
from pathlib import Path

symbols = [
    ("EURUSD", "EURUSD=X"),
    ("GBPUSD", "GBPUSD=X"),
    ("USDJPY", "USDJPY=X"),
    ("XAUUSD", "GC=F"),
    ("US500", "SPY"),
    ("US30", "DIA"),
]


def normalize_df(df):
    if isinstance(df.columns, pd.MultiIndex):
        df = df.copy()
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    original_index_name = df.index.name or 'index'
    df = df.reset_index()

    # Si el reset deja multiindex en columnas (poco probable), aplanar igual
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

    candidate_names = ['timestamp', 'Date', 'Datetime', original_index_name, 'index']
    timestamp_col = next((c for c in candidate_names if c in df.columns), None)
    if timestamp_col is None:
        raise ValueError('No se pudo encontrar una columna de timestamp después de reset_index()')

    if timestamp_col != 'timestamp':
        df = df.rename(columns={timestamp_col: 'timestamp'})

    df = df.rename(columns={
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })

    if 'volume' not in df.columns:
        df['volume'] = 0

    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    out_df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    return out_df


def save_output(df, symbol, timeframe, parquet_path, csv_path):
    target_parquet = parquet_path / timeframe / f"{symbol.lower()}_{timeframe}.parquet"
    target_csv = csv_path / timeframe / f"{symbol.lower()}_{timeframe}.csv"
    target_parquet.parent.mkdir(parents=True, exist_ok=True)
    target_csv.parent.mkdir(parents=True, exist_ok=True)

    # Guardado principal por timeframe
    df.to_parquet(target_parquet, index=False)
    df.to_csv(target_csv, index=False)

    # Compatibilidad con scripts existentes, ruta histórica plana en data/raw
    fallback_parquet = Path('data/raw') / f"{symbol.upper()}_{timeframe}.parquet"
    fallback_csv = Path('data/raw') / f"{symbol.upper()}_{timeframe}.csv"
    df.to_parquet(fallback_parquet, index=False)
    df.to_csv(fallback_csv, index=False)

    print(f"  [OK] Guardado en {target_parquet}, {target_csv}, {fallback_parquet}, {fallback_csv}")


def download_symbol(symbol, yf_symbol, timeframe, period, parquet_path, csv_path):
    if timeframe in ['6mo', '1y']:
        raise ValueError('Resample no debe llamarse directamente para timeframe 6mo o 1y')

    print(f"Descargando {symbol} ({yf_symbol}) en {timeframe}...")
    df = yf.download(yf_symbol, period=period, interval=timeframe, progress=False)
    print(f"  Descargadas {len(df)} filas")

    if len(df) == 0:
        print(f"  ✗ No se descargaron datos para {symbol} {timeframe}")
        return None

    out_df = normalize_df(df)
    save_output(out_df, symbol, timeframe, parquet_path, csv_path)
    return out_df


def resample_df(df, symbol, timeframe, parquet_path, csv_path):
    if timeframe == '6mo':
        rule = '6ME'
    elif timeframe == '1y':
        rule = '1YE'
    else:
        raise ValueError(f'Temporalidad de resample no soportada: {timeframe}')

    # Normalizar columnas si vienen en mayúsculas accidentalmente
    if 'open' not in df.columns and 'Open' in df.columns:
        df = df.rename(columns={'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})

    required_cols = {'open', 'high', 'low', 'close', 'volume'}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f'Columnas faltantes en daily_df para resampling: {sorted(missing)}. Columnas disponibles: {sorted(df.columns)}')

    if 'volume' not in df.columns:
        df['volume'] = 0

    df = df.set_index('timestamp')
    df_resampled = df.resample(rule).agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna().reset_index()

    save_output(df_resampled, symbol, timeframe, parquet_path, csv_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Descarga datos de forex/commodities/índices en múltiples temporalidades')
    parser.add_argument('--period', default='5y', help='Periodo de descarga (e.g. 2y, 5y)')
    parser.add_argument('--timeframes', default='1h,4h,1d,1wk,1mo,6mo,1y', help='Temporalidades separadas por coma (e.g. 15m,1h,4h,1d,1wk,1mo,6mo,1y)')
    args = parser.parse_args()

    requested_timeframes = [tf.strip() for tf in args.timeframes.split(',') if tf.strip()]

    yfinance_timeframes = [tf for tf in requested_timeframes if tf not in ['6mo', '1y']]
    if any(tf in ['6mo', '1y'] for tf in requested_timeframes) and '1d' not in yfinance_timeframes:
        yfinance_timeframes.append('1d')

    # Para intradía y 4h Yahoo sólo ofrece los últimos 730 días
    intraday_timeframes = {'15m', '30m', '1h', '2h', '4h'}

    raw_path = Path('data/raw')
    parquet_path = raw_path / 'parquet'
    csv_path = raw_path / 'csv'

    raw_path.mkdir(parents=True, exist_ok=True)
    parquet_path.mkdir(parents=True, exist_ok=True)
    csv_path.mkdir(parents=True, exist_ok=True)

    for symbol, yf_symbol in symbols:
        daily_df = None
        for timeframe in yfinance_timeframes:
            try:
                uso_period = args.period
                if timeframe in intraday_timeframes:
                    uso_period = '730d'
                out_df = download_symbol(symbol, yf_symbol, timeframe, uso_period, parquet_path, csv_path)
                if timeframe == '1d':
                    daily_df = out_df
            except Exception as e:
                print(f"  [ERROR] {symbol} {timeframe}: {e}")

        for timeframe in requested_timeframes:
            if timeframe in ['6mo', '1y']:
                try:
                    if daily_df is None:
                        print(f"  ✗ No hay base diaria para {symbol} al generar {timeframe}")
                        continue
                    resample_df(daily_df, symbol, timeframe, parquet_path, csv_path)
                except Exception as e:
                    print(f"  [ERROR] {symbol} {timeframe}: {e}")

    print('Descarga de Forex completada.')