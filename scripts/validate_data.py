"""
FASE 1 — Validación de Datos Descargados

Script para validar integridad y completitud de datos OHLCV.

Uso:
    python scripts/validate_data.py --file data/raw/btcusdt_1h.parquet
    python scripts/validate_data.py --folder data/raw/
    python scripts/validate_data.py --all
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, List

import pandas as pd

# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
)
logger = logging.getLogger(__name__)


# ============================================================
# VALIDACIONES
# ============================================================

def validate_ohlcv(
    df: pd.DataFrame,
    symbol: str = "UNKNOWN"
) -> Dict:
    """
    Valida integridad de datos OHLCV.
    
    Args:
        df: DataFrame con columnas [timestamp, open, high, low, close, volume]
        symbol: Identificador del símbolo
        
    Returns:
        Dict con resultados de validación
    """
    
    result = {
        "symbol": symbol,
        "status": "OK",
        "errors": [],
        "warnings": [],
    }
    
    # ── 1. Estructura básica ─────────────────────────────────
    required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
    missing_cols = required_cols - set(df.columns)
    
    if missing_cols:
        result["status"] = "ERROR"
        result["errors"].append(f"Columnas faltantes: {missing_cols}")
        return result
    
    # ── 2. Conteo de filas ───────────────────────────────────
    result["total_candles"] = len(df)
    
    if len(df) == 0:
        result["status"] = "ERROR"
        result["errors"].append("DataFrame vacío")
        return result
    
    # ── 3. Rango de fechas ───────────────────────────────────
    result["date_range"] = {
        "start": str(df['timestamp'].min()),
        "end": str(df['timestamp'].max()),
        "span_days": (df['timestamp'].max() - df['timestamp'].min()).days,
    }
    
    # ── 4. Validación de timestamps ──────────────────────────
    # Asegurar que timestamp es numérico/datetime
    df_copy = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df_copy['timestamp']):
        try:
            df_copy['timestamp'] = pd.to_datetime(df_copy['timestamp'])
        except Exception as e:
            result["status"] = "ERROR"
            result["errors"].append(f"No se pudo convertir timestamp a datetime: {e}")
            return result
    
    # Verificar que están ordenados
    if not (df_copy['timestamp'].diff().dropna() > pd.Timedelta(0)).all():
        result["status"] = "ERROR"
        result["errors"].append("Timestamps no están en orden creciente")
    
    # ── 5. Gaps de timestamps ────────────────────────────────
    time_diffs = df_copy['timestamp'].diff()
    gaps = time_diffs[time_diffs > pd.Timedelta('2h')]  # Asumiendo máximo gap de 1h
    
    if len(gaps) > 0:
        gap_count = len(gaps)
        result["warnings"].append(f"Gaps detectados: {gap_count}")
    
    result["missing_timestamps"] = len(gaps)
    
    # ── 6. Validación de OHLC consistency ────────────────────
    # High debe ser >= max(open, close)
    high_valid = (df['high'] >= df[['open', 'close']].max(axis=1)).all()
    result["high_gte_ohlc"] = high_valid
    if not high_valid:
        invalid_count = (~(df['high'] >= df[['open', 'close']].max(axis=1))).sum()
        result["status"] = "ERROR"
        result["errors"].append(
            f"High < max(OHLC) en {invalid_count} filas"
        )
    
    # Low debe ser <= min(open, close)
    low_valid = (df['low'] <= df[['open', 'close']].min(axis=1)).all()
    result["low_lte_ohlc"] = low_valid
    if not low_valid:
        invalid_count = (~(df['low'] <= df[['open', 'close']].min(axis=1))).sum()
        result["status"] = "ERROR"
        result["errors"].append(
            f"Low > min(OHLC) en {invalid_count} filas"
        )
    
    # High >= Low
    hl_valid = (df['high'] >= df['low']).all()
    result["high_gte_low"] = hl_valid
    if not hl_valid:
        invalid_count = (~(df['high'] >= df['low'])).sum()
        result["status"] = "ERROR"
        result["errors"].append(
            f"High < Low en {invalid_count} filas"
        )
    
    # ── 7. Validación de valores numéricos ───────────────────
    # No debe haber NaN
    nan_counts = df[['open', 'high', 'low', 'close', 'volume']].isna().sum()
    if nan_counts.sum() > 0:
        result["status"] = "ERROR"
        result["errors"].append(f"NaN encontrados: {nan_counts.to_dict()}")
    result["nan_count"] = nan_counts.to_dict()
    
    # Precios deben ser positivos
    negative_prices = (df[['open', 'high', 'low', 'close']] <= 0).sum().sum()
    if negative_prices > 0:
        result["status"] = "ERROR"
        result["errors"].append(f"Precios negativos/cero: {negative_prices}")
    
    # Volume debe ser no-negativo
    negative_volume = (df['volume'] < 0).sum()
    if negative_volume > 0:
        result["status"] = "ERROR"
        result["errors"].append(f"Volúmenes negativos: {negative_volume}")
    
    result["price_stats"] = {
        "open": {"min": float(df['open'].min()), "max": float(df['open'].max())},
        "high": {"min": float(df['high'].min()), "max": float(df['high'].max())},
        "low": {"min": float(df['low'].min()), "max": float(df['low'].max())},
        "close": {"min": float(df['close'].min()), "max": float(df['close'].max())},
        "volume": {"min": float(df['volume'].min()), "max": float(df['volume'].max())},
    }
    
    # ── 8. Duplicados ────────────────────────────────────────
    duplicates = df['timestamp'].duplicated().sum()
    if duplicates > 0:
        result["status"] = "ERROR"
        result["errors"].append(f"Timestamps duplicados: {duplicates}")
    result["duplicate_timestamps"] = duplicates
    
    return result


def print_validation_result(result: Dict, verbose: bool = False):
    """
    Imprime resultado de validación de forma legible.
    
    Args:
        result: Dict con resultados de validación
        verbose: Mostrar detalles completos
    """
    
    symbol = result.get("symbol", "UNKNOWN")
    status = result.get("status", "UNKNOWN")
    
    # Color de estado
    status_icon = "✓" if status == "OK" else "✗"
    
    print(f"\n{status_icon} {symbol:12} | Status: {status}")
    
    # Información básica
    candles = result.get("total_candles", 0)
    print(f"  └─ Candles: {candles:,}")
    
    date_range = result.get("date_range", {})
    if date_range:
        start = date_range.get("start", "N/A")
        end = date_range.get("end", "N/A")
        days = date_range.get("span_days", "N/A")
        print(f"  └─ Período: {start} a {end} ({days} días)")
    
    # Gaps
    missing = result.get("missing_timestamps", 0)
    if missing > 0:
        print(f"  └─ ⚠ Gaps: {missing}")
    
    # Errores
    errors = result.get("errors", [])
    if errors:
        for i, error in enumerate(errors, 1):
            print(f"  └─ ✗ Error {i}: {error}")
    
    # Advertencias
    warnings = result.get("warnings", [])
    if warnings and verbose:
        for i, warning in enumerate(warnings, 1):
            print(f"  └─ ⚠ Aviso {i}: {warning}")
    
    # Stats de precios (si es verbose)
    if verbose:
        stats = result.get("price_stats", {})
        if stats:
            print(f"  └─ Price Stats:")
            for ohlc, vals in stats.items():
                print(f"      {ohlc:6}: min={vals['min']:>12.2f}, max={vals['max']:>12.2f}")


def validate_file(file_path: Path) -> Dict:
    """
    Valida un archivo Parquet específico.
    
    Args:
        file_path: Path al archivo .parquet
        
    Returns:
        Dict con resultados de validación
    """
    
    if not file_path.exists():
        logger.error(f"Archivo no encontrado: {file_path}")
        return {"status": "ERROR", "error": "File not found"}
    
    try:
        df = pd.read_parquet(file_path)
        symbol = file_path.stem.split('_')[0].upper()
        result = validate_ohlcv(df, symbol)
        return result
    except Exception as e:
        logger.error(f"Error al leer {file_path}: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
            "file": str(file_path),
        }


def validate_folder(folder_path: Path) -> Dict[str, Dict]:
    """
    Valida todos los archivos .parquet en una carpeta.
    
    Args:
        folder_path: Path a la carpeta
        
    Returns:
        Dict con resultados para cada archivo
    """
    
    results = {}
    parquet_files = sorted(folder_path.glob("*.parquet"))
    
    if not parquet_files:
        logger.warning(f"No se encontraron archivos .parquet en {folder_path}")
        return results
    
    logger.info(f"Validando {len(parquet_files)} archivos en {folder_path}")
    
    for file_path in parquet_files:
        result = validate_file(file_path)
        results[file_path.name] = result
    
    return results


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Valida datos OHLCV descargados"
    )
    parser.add_argument(
        "--file",
        type=Path,
        help="Validar archivo específico"
    )
    parser.add_argument(
        "--folder",
        type=Path,
        help="Validar todos los archivos en carpeta"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Validar data/raw/ y data/processed/"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Mostrar detalles completos"
    )
    
    args = parser.parse_args()
    
    logger.info("="*60)
    logger.info("FASE 1 — Validación de Datos")
    logger.info("="*60)
    
    all_results = {}
    
    if args.file:
        logger.info(f"Modo: Un archivo ({args.file})")
        result = validate_file(args.file)
        all_results[args.file.name] = result
        
    elif args.folder:
        logger.info(f"Modo: Carpeta ({args.folder})")
        all_results = validate_folder(args.folder)
        
    elif args.all:
        logger.info("Modo: Todos (data/raw/ y data/processed/)")
        raw_path = Path("data/raw")
        processed_path = Path("data/processed")
        
        if raw_path.exists():
            logger.info(f"\n  Validando {raw_path}...")
            all_results.update(validate_folder(raw_path))
        
        if processed_path.exists():
            logger.info(f"\n  Validando {processed_path}...")
            all_results.update(validate_folder(processed_path))
    
    else:
        parser.print_help()
        sys.exit(1)
    
    # ── Resumen ──────────────────────────────────────────────
    logger.info(f"\n{'='*60}")
    logger.info("RESUMEN DE VALIDACIÓN")
    logger.info(f"{'='*60}")
    
    ok_count = 0
    error_count = 0
    
    for filename, result in sorted(all_results.items()):
        print_validation_result(result, args.verbose)
        
        status = result.get("status", "UNKNOWN")
        if status == "OK":
            ok_count += 1
        else:
            error_count += 1
    
    logger.info(f"\n{'─'*60}")
    logger.info(f"Total: {len(all_results)} archivos")
    logger.info(f"  ✓ OK: {ok_count}")
    logger.info(f"  ✗ ERROR: {error_count}")
    logger.info(f"{'─'*60}\n")
    
    # Exit code
    sys.exit(0 if error_count == 0 else 1)


if __name__ == "__main__":
    main()
