#!/usr/bin/env python3
"""Limpiar y reorganizar TODOS los archivos (.parquet y .csv)."""
from pathlib import Path
import shutil
import re

base = Path("data/raw")
parquet_base = base / "parquet"
csv_base = base / "csv"

print("=" * 100)
print("LIMPIEZA COMPLETA: Archivos .parquet Y .csv de TODAS las períodicidades")
print("=" * 100)

# Timeframes válidos
valid_timeframes = ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]

# DESCUBRIR TODOS LOS ARCHIVOS
print("\n🔍 FASE 1: Descubriendo archivos en TODAS las ubicaciones...\n")

# archivos .parquet en data/raw/parquet/ (raíz)
parquet_root = list(parquet_base.glob("*.parquet"))
print(f"   📦 data/raw/parquet/: {len(parquet_root)} .parquet")

# archivos legacy .parquet en data/raw/
legacy_parquets = list(base.glob("*.parquet"))
print(f"   📦 data/raw/: {len(legacy_parquets)} .parquet")

# archivos legacy .csv en data/raw/
legacy_csvs = list(base.glob("*.csv"))
print(f"   📦 data/raw/: {len(legacy_csvs)} .csv")

total_to_move = len(parquet_root) + len(legacy_parquets) + len(legacy_csvs)
print(f"\n   ➜ TOTAL: {total_to_move} archivos a organizar\n")

if total_to_move == 0:
    print("✅ No hay archivos para organizar")
else:
    print("=" * 100)
    print("🔧 FASE 2: Reorganizando archivos...\n")
    
    moved = 0
    skipped = 0
    errors = 0
    
    # PROCESAR .parquet en data/raw/parquet/ (raíz)
    if parquet_root:
        print("   ▸ Archivos en data/raw/parquet/ (raíz):")
        for f in parquet_root:
            match = re.search(r'_([0-9]{1,2}[mhd]|[0-9]y)\.parquet$', f.name)
            if match:
                timeframe = match.group(1)
                if timeframe in valid_timeframes:
                    target_dir = parquet_base / timeframe
                    target_file = target_dir / f.name
                    
                    if target_file.exists():
                        print(f"      ⏭️  {f.name:35s} → {timeframe}/ (DUP: eliminando)")
                        try:
                            f.unlink()
                            skipped += 1
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                            errors += 1
                    else:
                        print(f"      ✅ {f.name:35s} → {timeframe}/")
                        try:
                            shutil.move(str(f), str(target_file))
                            moved += 1
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                            errors += 1
    
    # PROCESAR .parquet legacy en data/raw/
    if legacy_parquets:
        print("\n   ▸ Archivos legacy en data/raw/ (.parquet):")
        for f in legacy_parquets:
            match = re.search(r'_([0-9]{1,2}[mhd]|[0-9]y)\.parquet$', f.name)
            if match:
                timeframe = match.group(1)
                if timeframe in valid_timeframes:
                    target_dir = parquet_base / timeframe
                    target_file = target_dir / f.name
                    
                    if target_file.exists():
                        print(f"      ⏭️  {f.name:35s} → {timeframe}/ (DUP: eliminando)")
                        try:
                            f.unlink()
                            skipped += 1
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                            errors += 1
                    else:
                        print(f"      ✅ {f.name:35s} → {timeframe}/")
                        try:
                            shutil.move(str(f), str(target_file))
                            moved += 1
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                            errors += 1
    
    # PROCESAR .csv legacy en data/raw/
    if legacy_csvs:
        print("\n   ▸ Archivos legacy en data/raw/ (.csv):")
        for f in legacy_csvs:
            match = re.search(r'_([0-9]{1,2}[mhd]|[0-9]y)\.csv$', f.name)
            if match:
                timeframe = match.group(1)
                if timeframe in valid_timeframes:
                    target_dir = csv_base / timeframe
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_file = target_dir / f.name
                    
                    if target_file.exists():
                        print(f"      ⏭️  {f.name:35s} → csv/{timeframe}/ (DUP: eliminando)")
                        try:
                            f.unlink()
                            skipped += 1
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                            errors += 1
                    else:
                        print(f"      ✅ {f.name:35s} → csv/{timeframe}/")
                        try:
                            shutil.move(str(f), str(target_file))
                            moved += 1
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                            errors += 1
    
    # RESUMEN
    print(f"\n   📊 RESULTADO:")
    print(f"      ✅ {moved} archivos movidos")
    print(f"      ⏭️  {skipped} duplicados eliminados")
    if errors > 0:
        print(f"      ❌ {errors} errores")

# VALIDAR ESTRUCTURA FINAL
print("\n" + "=" * 100)
print("📂 VALIDACIÓN FINAL - data/raw/parquet/:") 
print("=" * 100)
for timeframe in valid_timeframes:
    pq_count = len(list((parquet_base / timeframe).glob("*.parquet")))
    print(f"   {timeframe:5s}: {pq_count:2d} .parquet")

print("\n" + "=" * 100)
print("📂 VALIDACIÓN FINAL - data/raw/csv/:")
print("=" * 100)
for timeframe in valid_timeframes:
    csv_count = len(list((csv_base / timeframe).glob("*.csv")))
    print(f"   {timeframe:5s}: {csv_count:2d} .csv")

print("\n" + "=" * 100)
print("✅ Limpieza completada\n")
