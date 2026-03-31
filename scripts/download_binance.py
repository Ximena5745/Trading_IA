"""
FASE 1 — Descarga de Datos Reales desde Binance API

Script para descargar datos históricos OHLCV de Binance.
Usa API pública (sin API key requerida).

Uso:
    python scripts/download_binance.py --symbol BTCUSDT --timeframe 1h --years 2
    python scripts/download_binance.py --symbol ETHUSDT --timeframe 4h --years 2
    python scripts/download_binance.py --all --years 2

Datos guardados en: data/raw/{symbol}_{timeframe}.parquet
"""

import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import requests
from tqdm import tqdm

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/download_binance.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Crear directorio de logs
Path('logs').mkdir(exist_ok=True)


# ============================================================
# CONFIGURACIÓN
# ============================================================

BINANCE_API_BASE = "https://api.binance.com/api/v3/klines"

# Timeframes soportados y su equivalente en milisegundos
TIMEFRAME_MS = {
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
}

# Datos a descargar: (símbolo, timeframes)
DEFAULT_SYMBOLS = {
    "BTCUSDT": ["1h", "4h"],
    "ETHUSDT": ["1h", "4h"],
}

# Rate limiting
MAX_REQUESTS_PER_MINUTE = 1200
MIN_DELAY_BETWEEN_REQUESTS = 60 / MAX_REQUESTS_PER_MINUTE  # ~0.05 segundos


# ============================================================
# DESCARGA
# ============================================================

def download_binance(
    symbol: str,
    timeframe: str = "1h",
    years: int = 2,
    max_retries: int = 3,
) -> Optional[pd.DataFrame]:
    """
    Descarga datos históricos OHLCV de Binance.
    
    Args:
        symbol: Par de trading (ej: 'BTCUSDT')
        timeframe: Intervalo de tiempo (ej: '1h', '4h')
        years: Años de histórico a descargar
        max_retries: Intentos máximos por vela
        
    Returns:
        DataFrame con columnas [timestamp, open, high, low, close, volume]
        o None si falla la descarga
    """
    
    if timeframe not in TIMEFRAME_MS:
        logger.error(f"Timeframe no soportado: {timeframe}")
        return None
    
    logger.info(f"Iniciando descarga: {symbol} {timeframe} ({years} años)")
    
    # Calcular cantidad de velas necesarias
    timeframe_ms = TIMEFRAME_MS[timeframe]
    total_ms = years * 365 * 24 * 60 * 60 * 1000  # ms en N años
    total_candles = total_ms // timeframe_ms
    
    logger.info(f"Total de velas a descargar: {total_candles:,}")
    
    # Paginación: máximo 1000 por request
    chunk_size = 1000
    total_chunks = (total_candles + chunk_size - 1) // chunk_size
    
    logger.info(f"Total de requests: {total_chunks}")
    
    all_candles = []
    current_time = int(datetime.utcnow().timestamp() * 1000)  # Ahora en ms
    
    # Iterar hacia atrás en el tiempo
    for chunk_idx in tqdm(range(total_chunks), desc=f"{symbol} {timeframe}"):
        # Tiempo final de este chunk (startTime <= t < endTime)
        end_time = current_time - (chunk_idx * chunk_size * timeframe_ms)
        start_time = end_time - (chunk_size * timeframe_ms)
        
        # Intents con backoff exponencial
        retry_count = 0
        chunk_data = None
        
        while retry_count < max_retries and chunk_data is None:
            try:
                params = {
                    "symbol": symbol,
                    "interval": timeframe,
                    "startTime": start_time,
                    "endTime": end_time,
                    "limit": chunk_size,
                }
                
                response = requests.get(
                    BINANCE_API_BASE,
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                
                if response.status_code == 200:
                    chunk_data = response.json()
                    if not chunk_data:
                        logger.warning(f"Chunk {chunk_idx} vacío (posible fin de datos)")
                        break
                    
                    # Pequeña pausa para respetar rate limit
                    import time
                    time.sleep(MIN_DELAY_BETWEEN_REQUESTS)
                    
            except requests.exceptions.RequestException as e:
                retry_count += 1
                wait_time = 2 ** (retry_count - 1)  # Backoff: 1, 2, 4, 8...
                logger.warning(
                    f"Error en chunk {chunk_idx} (intento {retry_count}/{max_retries}): {e}. "
                    f"Esperando {wait_time}s..."
                )
                import time
                time.sleep(wait_time)
        
        if chunk_data is None:
            logger.error(f"Chunk {chunk_idx} falló después de {max_retries} intentos")
            continue
        
        # Parsear datos del chunk
        for candle in chunk_data:
            # Formato de Binance:
            # [time, open, high, low, close, volume, ...]
            all_candles.append({
                'timestamp': pd.to_datetime(candle[0], unit='ms', utc=True),
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5]),
            })
    
    if not all_candles:
        logger.error(f"No se descargó datos para {symbol} {timeframe}")
        return None
    
    # Crear DataFrame
    df = pd.DataFrame(all_candles)
    df = df.sort_values('timestamp').reset_index(drop=True)
    
    logger.info(f"Descargadas {len(df):,} velas")
    logger.info(f"Período: {df['timestamp'].min()} a {df['timestamp'].max()}")
    
    # Validación rápida
    if (df['high'] >= df[['open', 'close']].max(axis=1)).sum() == len(df):
        logger.info("✓ Validación: High >= OHLC (100%)")
    else:
        logger.warning("⚠ Validación: Algunas filas tienen high < OHLC")
    
    if (df['low'] <= df[['open', 'close']].min(axis=1)).sum() == len(df):
        logger.info("✓ Validación: Low <= OHLC (100%)")
    else:
        logger.warning("⚠ Validación: Algunas filas tienen low > OHLC")
    
    return df


def save_parquet(df: pd.DataFrame, symbol: str, timeframe: str) -> Path:
    """
    Guarda DataFrame en Parquet.
    
    Args:
        df: DataFrame con datos OHLCV
        symbol: Símbolo (ej: 'BTCUSDT')
        timeframe: Intervalo (ej: '1h')
        
    Returns:
        Path del archivo guardado
    """
    
    output_path = Path("data/raw") / f"{symbol.lower()}_{timeframe}.parquet"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_parquet(output_path, index=False, engine='pyarrow')
    logger.info(f"Guardado: {output_path}")
    
    return output_path


def download_all_symbols(years: int = 2) -> dict:
    """
    Descarga todos los símbolos configurados.
    
    Args:
        years: Años de histórico
        
    Returns:
        Dict con símbolo:timeframes como claves y resultados como valores
    """
    
    results = {}
    
    for symbol, timeframes in DEFAULT_SYMBOLS.items():
        logger.info(f"\n{'='*60}")
        logger.info(f"Símbolo: {symbol}")
        logger.info(f"{'='*60}")
        
        results[symbol] = {}
        
        for timeframe in timeframes:
            try:
                df = download_binance(symbol, timeframe, years)
                
                if df is not None and len(df) > 0:
                    path = save_parquet(df, symbol, timeframe)
                    results[symbol][timeframe] = {
                        "status": "OK",
                        "candles": len(df),
                        "path": str(path),
                    }
                else:
                    results[symbol][timeframe] = {
                        "status": "ERROR",
                        "error": "No data downloaded"
                    }
                    
            except Exception as e:
                logger.error(f"Excepción: {e}", exc_info=True)
                results[symbol][timeframe] = {
                    "status": "ERROR",
                    "error": str(e)
                }
    
    return results


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Descarga datos históricos de Binance"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        help="Símbolo a descargar (ej: BTCUSDT)"
    )
    parser.add_argument(
        "--timeframe",
        type=str,
        default="1h",
        choices=list(TIMEFRAME_MS.keys()),
        help="Timeframe (default: 1h)"
    )
    parser.add_argument(
        "--years",
        type=int,
        default=2,
        help="Años de histórico (default: 2)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Descargar todos los símbolos configurados"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("FASE 1 — Descarga de Datos Reales (Binance)")
    logger.info("="*60)
    
    if args.all:
        logger.info(f"Modo: Descargar TODOS los símbolos ({len(DEFAULT_SYMBOLS)})")
        results = download_all_symbols(args.years)
        
        # Resumen
        logger.info(f"\n{'='*60}")
        logger.info("RESUMEN")
        logger.info(f"{'='*60}")
        for symbol, timeframes_data in results.items():
            for timeframe, data in timeframes_data.items():
                status = data.get("status")
                if status == "OK":
                    candles = data.get("candles", 0)
                    logger.info(f"✓ {symbol:8} {timeframe:4} → {candles:,} candles")
                else:
                    error = data.get("error", "Unknown error")
                    logger.info(f"✗ {symbol:8} {timeframe:4} → ERROR: {error}")
    
    elif args.symbol:
        logger.info(f"Modo: Descargar un símbolo específico ({args.symbol})")
        df = download_binance(args.symbol, args.timeframe, args.years)
        
        if df is not None and len(df) > 0:
            path = save_parquet(df, args.symbol, args.timeframe)
            logger.info(f"✓ Éxito: {len(df):,} candles guardadas en {path}")
        else:
            logger.error("✗ Fallo: No se descargó datos")
            sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
