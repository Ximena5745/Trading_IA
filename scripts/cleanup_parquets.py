#!/usr/bin/env python3
"""Limpiar y reorganizar archivos mal colocados de TODAS las períodicidades."""
from pathlib import Path
import shutil
import re

base = Path("data/raw/parquet")

print("=" * 80)
print("LIMPIEZA Y REORGANIZACIÓN DE ARCHIVOS (TODAS LAS PERIODICIDADES)")
print("=" * 80)

# Timeframes válidos
valid_timeframes = ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]

# Identificar archivos mal colocados en raíz de parquet/
print("\n🔍 Buscando archivos mal colocados en data/raw/parquet/...")
misplaced = []
for f in base.glob("*.parquet"):
    if f.is_file():
        misplaced.append(f)
        print(f"   ❌ {f.name}")

print(f"\n   Total encontrados: {len(misplaced)}")

if misplaced:
    print(f"\n🔧 Reorganizando {len(misplaced)} archivos...")
    moved_count = 0
    skipped_count = 0
    
    for f in misplaced:
        # Extraer timeframe del nombre: EURUSD_1d, GBPUSD_4h, etc.
        # Patrón: {symbol}_{timeframe}
        match = re.search(r'_([0-9]{1,2}[mhwd]|[0-9]y)\.parquet$', f.name)
        
        if match:
            timeframe = match.group(1)
            
            if timeframe in valid_timeframes:
                target_dir = base / timeframe
                target_file = target_dir / f.name
                
                # Si ya existe exactamente, no duplicar
                if target_file.exists():
                    print(f"   ⏭️  {f.name:30s} ya existe en {timeframe}/ → eliminando duplicado")
                    f.unlink()
                    skipped_count += 1
                else:
                    print(f"   ✅ {f.name:30s} → {timeframe}/")
                    shutil.move(str(f), str(target_file))
                    moved_count += 1
            else:
                print(f"   ⚠️  {f.name:30s} → timeframe inválido '{timeframe}'")
        else:
            print(f"   ⚠️  {f.name:30s} → no se pudo extraer timeframe")
    
    print(f"\n   📊 RESULTADO: {moved_count} movidos, {skipped_count} duplicados eliminados")
else:
    print("   ✅ No hay archivos mal colocados")

# Validar estructura final
print("\n📂 VALIDANDO ESTRUCTURA FINAL:")
for timeframe in valid_timeframes:
    tf_dir = base / timeframe
    files = list(tf_dir.glob("*.parquet"))
    print(f"   {timeframe:5s}: {len(files):2d} archivos")

print("\n" + "=" * 80)
print("LIMPIEZA COMPLETADA")
print("=" * 80)
