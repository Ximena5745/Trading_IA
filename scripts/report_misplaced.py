#!/usr/bin/env python3
"""Reporte detallado de archivos mal colocados por timeframe."""
from pathlib import Path
import re
from collections import defaultdict

base = Path("data/raw/parquet")

print("=" * 80)
print("REPORTE DETALLADO: ARCHIVOS MAL COLOCADOS EN data/raw/parquet/")
print("=" * 80)

# Buscar TODOS los .parquet en raíz
all_files = list(base.glob("*.parquet"))

if not all_files:
    print("\n✅ No hay archivos en raíz, estructura OK")
else:
    print(f"\n🔴 {len(all_files)} archivos encontrados en raíz:\n")
    
    # Agrupar por timeframe
    by_timeframe = defaultdict(list)
    invalid = []
    
    for f in all_files:
        # Extraer timeframe: _1h, _4h, _1d, _6mo, _1y, etc.
        match = re.search(r'_([0-9]{1,2}[mhd]|[0-9]y)\.parquet$', f.name)
        
        if match:
            timeframe = match.group(1)
            by_timeframe[timeframe].append(f.name)
        else:
            invalid.append(f.name)
    
    # Mostrar por timeframe
    for tf in sorted(by_timeframe.keys()):
        files = by_timeframe[tf]
        target_dir = base / tf
        existing_count = len(list(target_dir.glob("*.parquet")))
        
        print(f"\n  ⏱️  TIMEFRAME: {tf}")
        print(f"     En raíz: {len(files)} archivos")
        print(f"     En {tf}/: {existing_count} archivos")
        
        for fname in sorted(files):
            print(f"        - {fname}")
    
    if invalid:
        print(f"\n  ⚠️  INVÁLIDOS (no se puede extraer timeframe):")
        for fname in invalid:
            print(f"        - {fname}")

# Mostrar estrutura esperada
print("\n" + "=" * 80)
print("ESTRUCTURA ESPERADA:")
print("=" * 80)
print("""
data/raw/parquet/
    ├── 1h/     (eurusd_1h.parquet, gbpusd_1h.parquet, ...)
    ├── 4h/     (eurusd_4h.parquet, ...)
    ├── 1d/     (eurusd_1d.parquet, gbpusd_1d.parquet, ...)
    ├── 1wk/    (...)
    ├── 1mo/    (...)
    ├── 6mo/    (...)
    └── 1y/     (...)
    
    (NO debe haber .parquet files acá en raíz)
""")

# Contar total en subdirectorios
print("VALIDACIÓN DE SUBDIRECTORIOS:")
print("=" * 80)
total_in_subdirs = 0
for tf in ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]:
    tf_dir = base / tf
    if tf_dir.exists():
        count = len(list(tf_dir.glob("*.parquet")))
        total_in_subdirs += count
        status = "✅" if count == 6 else "⚠️" if count > 0 else "❌"
        print(f"  {status} {tf:5s}: {count} archivos (esperado: 6)")
    else:
        print(f"  ❌ {tf:5s}: DIRECTORIO NO EXISTE")

print(f"\n  TOTAL en subdirectorios: {total_in_subdirs} archivos")
print("=" * 80)
