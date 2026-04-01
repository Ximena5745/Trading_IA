#!/usr/bin/env python3
"""Análisis completo de dónde están los archivos y qué está mal colocado."""
from pathlib import Path
import re
from collections import defaultdict

print("=" * 90)
print("ANÁLISIS COMPLETO DE ESTRUCTURA DE ARCHIVOS")
print("=" * 90)

base_raw = Path("data/raw")
base_parquet = base_raw / "parquet"
base_csv = base_raw / "csv"

# PARTE 1: Archivos en raíz de data/raw/
print("\n1️⃣  ARCHIVOS EN data/raw/ (LEGACY - HISTÓRICOS)")
print("-" * 90)

legacy_parquets = list(base_raw.glob("*.parquet"))
legacy_csvs = list(base_raw.glob("*.csv"))

legacy_by_tf = defaultdict(list)
for f in legacy_parquets:
    match = re.search(r'_([0-9]{1,2}[mhd]|[0-9]y)\.parquet$', f.name)
    if match:
        tf = match.group(1)
        legacy_by_tf[tf].append(f.name)

if legacy_parquets:
    print(f"   ✅ {len(legacy_parquets)} .parquet archivos")
    for tf in sorted(legacy_by_tf.keys()):
        print(f"      {tf}: {len(legacy_by_tf[tf])} archivos")
else:
    print("   ❌ No hay archivos legacy")

# PARTE 2: Archivos en parquet/subdir
print("\n2️⃣  ARCHIVOS EN data/raw/parquet/{timeframe}/")
print("-" * 90)

subdir_summary = {}
for tf in ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]:
    tf_dir = base_parquet / tf
    if tf_dir.exists():
        files = list(tf_dir.glob("*.parquet"))
        subdir_summary[tf] = len(files)
        if files:
            print(f"   ✅ {tf:5s}: {len(files):2d} archivos → ", end="")
            print(", ".join([f.stem for f in sorted(files)]))
    else:
        subdir_summary[tf] = 0
        print(f"   ❌ {tf:5s}: NO EXISTE")

# PARTE 3: Archivos en RAÍZ parquet/ (problema)
print("\n3️⃣  ARCHIVOS EN data/raw/parquet/ (RAÍZ - PROBLEMA)")
print("-" * 90)

root_parquets = list(base_parquet.glob("*.parquet"))
if root_parquets:
    print(f"   🔴 {len(root_parquets)} archivos mal ubicados en RAÍZ:")
    root_by_tf = defaultdict(list)
    for f in root_parquets:
        match = re.search(r'_([0-9]{1,2}[mhd]|[0-9]y)\.parquet$', f.name)
        if match:
            tf = match.group(1)
            root_by_tf[tf].append(f.name)
    
    for tf in sorted(root_by_tf.keys()):
        print(f"      {tf}: {', '.join(root_by_tf[tf])}")
else:
    print("   ✅ RAÍZ está limpia (no hay archivos mal colocados)")

# PARTE 4: Resumen
print("\n" + "=" * 90)
print("RESUMEN Y RECOMENDACIONES")
print("=" * 90)

total_legacy = len(legacy_parquets)
total_subdirs = sum(subdir_summary.values())
total_root = len(root_parquets)

print(f"\n   Legacy en data/raw/          : {total_legacy:3d} archivos")
print(f"   En subdirectorios data/raw/parquet/{{}}/: {total_subdirs:3d} archivos")
print(f"   En raíz data/raw/parquet/    : {total_root:3d} archivos ← ⚠️  PROBLEMA")
print(f"   {'─' * 40}")
print(f"   TOTAL                        : {total_legacy + total_subdirs + total_root:3d} archivos")

if total_root > 0:
    print(f"\n   🔧 ACCIÓN REQUERIDA:")
    print(f"      Ejecuta: python scripts/cleanup_parquets.py")
    print(f"      Esto moverá los {total_root} archivos a sus carpetas correctas")
else:
    print(f"\n   ✅ ESTRUCTURA OK - No hay archivos mal colocados")

print("\n" + "=" * 90)
