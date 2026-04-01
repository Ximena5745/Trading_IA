#!/usr/bin/env python3
"""
Diagnóstico y limpieza definitiva de data/raw y subcarpetas:
- Lista TODO archivo no clasificado (no .parquet/.csv, o con nombre raro, o en subcarpetas inesperadas)
- Mueve todo lo que pueda a la estructura correcta (parquet/{tf}/, csv/{tf}/)
- Reporta archivos huérfanos, desconocidos o corruptos
"""
from pathlib import Path
import shutil
import re

base = Path("data/raw")
parquet_base = base / "parquet"
csv_base = base / "csv"
valid_timeframes = ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]

print("="*120)
print("DIAGNÓSTICO Y LIMPIEZA TOTAL DE data/raw Y SUBCARPETAS")
print("="*120)

# 1. Recorrer TODO data/raw recursivamente
all_files = list(base.rglob("*"))
classified = 0
moved = 0
skipped = 0
orphans = []

for f in all_files:
    if f.is_dir():
        continue
    rel = f.relative_to(base)
    # Saltar archivos ya bien ubicados en subcarpetas correctas
    if len(rel.parts) == 3 and rel.parts[0] in ("parquet", "csv"):
        tf = rel.parts[1]
        fname = rel.parts[2]
        match = re.match(r"([A-Za-z0-9]+)_([0-9]{1,2}[mhd]|[0-9]y)\.(parquet|csv)$", fname, re.I)
        if tf in valid_timeframes and match:
            continue
    # Intentar clasificar por nombre
    # Solo mover archivos que están en la raíz de data/raw o en subcarpetas inesperadas
    if len(rel.parts) == 1:
        match = re.match(r"([A-Za-z0-9]+)_([0-9]{1,2}[mhd]|[0-9]y)\.(parquet|csv)$", f.name, re.I)
        if match:
            symbol, tf, ext = match.groups()
            tf = tf.lower()
            ext = ext.lower()
            norm_name = f"{symbol.lower()}_{tf}.{ext}"
            if tf in valid_timeframes:
                if ext == "parquet":
                    target = parquet_base / tf / norm_name
                else:
                    target = csv_base / tf / norm_name
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    print(f"⏭️  {f} → {target} (DUP: eliminando)")
                    f.unlink()
                    skipped += 1
                else:
                    print(f"✅ {f} → {target}")
                    shutil.move(str(f), str(target))
                    moved += 1
                continue
    # Si no se pudo clasificar, es huérfano
    orphans.append(f)

print("\n" + "-"*80)
print(f"Archivos movidos: {moved}")
print(f"Duplicados eliminados: {skipped}")
print(f"Archivos huérfanos/no clasificados: {len(orphans)}")
if orphans:
    print("\nLISTADO DE ARCHIVOS HUÉRFANOS O NO CLASIFICADOS:")
    for f in orphans:
        print(f"   - {f.relative_to(base)}")
    print("\nPuedes revisar estos archivos manualmente o renombrarlos para que el script los clasifique.")
else:
    print("\nNo quedan archivos huérfanos. Estructura limpia.")

print("\n" + "="*120)
print("ESTRUCTURA FINAL:")
for tf in valid_timeframes:
    pq = len(list((parquet_base/tf).glob("*.parquet")))
    csv = len(list((csv_base/tf).glob("*.csv")))
    print(f"  {tf:5s}: {pq:2d} .parquet, {csv:2d} .csv")
print("="*120)
