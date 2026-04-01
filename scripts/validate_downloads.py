#!/usr/bin/env python3
"""Validar ubicación de archivos descargados."""
from pathlib import Path
import os

print("=" * 80)
print("VALIDACIÓN DE UBICACIÓN DE ARCHIVOS DESCARGADOS")
print("=" * 80)

base = Path("data/raw")
parquet_base = base / "parquet"
csv_base = base / "csv"

print("\n📁 ESTRUCTURA ESPERADA:")
print("   data/raw/")
print("   ├── parquet/")
print("   │   ├── 1h/")
print("   │   ├── 4h/")
print("   │   ├── 1d/")
print("   │   ├── 1wk/")
print("   │   ├── 1mo/")
print("   │   ├── 6mo/")
print("   │   └── 1y/")
print("   ├── csv/")
print("   │   ├── 1h/")
print("   │   └── ...")
print("   └── (archivos legacy):")
print("       ├── EURUSD_1d.parquet")
print("       └── ...")

print("\n📂 VERIFICANDO DIRECTORIOS:")
for timeframe in ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]:
    pq_dir = parquet_base / timeframe
    csv_dir = csv_base / timeframe
    
    pq_exists = pq_dir.exists()
    csv_exists = csv_dir.exists()
    
    pq_status = "✅" if pq_exists else "❌"
    csv_status = "✅" if csv_exists else "❌"
    
    print(f"   {timeframe:5s}  parquet: {pq_status}  csv: {csv_status}")

print("\n📄 ARCHIVOS EN CARPETAS ORGANIZADAS (parquet/):")
if parquet_base.exists():
    for timeframe_dir in sorted(parquet_base.iterdir()):
        if timeframe_dir.is_dir():
            files = list(timeframe_dir.glob("*.parquet"))
            print(f"\n   {timeframe_dir.name}/ ({len(files)} archivos)")
            for f in sorted(files)[:5]:  # Mostrar primeros 5
                size_mb = f.stat().st_size / 1024 / 1024
                print(f"      - {f.name:30s} ({size_mb:.1f} MB)")
            if len(files) > 5:
                print(f"      ... y {len(files) - 5} más")

print("\n📄 ARCHIVOS LEGACY EN data/raw/:")
legacy_files = list(base.glob("*.parquet"))[:10]
if legacy_files:
    print(f"   Total: {len(list(base.glob('*.parquet')))} archivos")
    for f in legacy_files:
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"      - {f.name:30s} ({size_mb:.1f} MB)")
else:
    print("   ❌ No hay archivos legacy")

print("\n📊 RESUMEN DE CONTEOS:")
parquet_files = list(base.glob("*/parquet/**/*.parquet"))
csv_files = list(base.glob("*/csv/**/*.csv"))
legacy_parquet = list(base.glob("*.parquet"))

print(f"   Archivos en parquet/ subdirs:  {len(parquet_files)}")
print(f"   Archivos en csv/ subdirs:      {len(csv_files)}")
print(f"   Archivos legacy en raw/:       {len(legacy_parquet)}")

print("\n" + "=" * 80)
print("VALIDACIÓN: ", end="")
if len(parquet_files) > 15:
    print(f"✅ ARCHIVOS PRESENTES ({len(parquet_files)} parquets, {len(legacy_parquet)} legacy)")
else:
    print(f"⚠️  POSIBLE PROBLEMA ({len(parquet_files)} parquets esperados > 15)")
print("=" * 80)
