from pathlib import Path
import shutil
import re

base = Path("data/raw")
parquet_base = base / "parquet"
csv_base = base / "csv"
valid_timeframes = ["1h", "4h", "1d", "1wk", "1mo", "6mo", "1y"]

moved = 0
skipped = 0

for f in base.glob("*"):
    if not f.is_file():
        continue
    match = re.match(r"([A-Za-z0-9]+)_([0-9]{1,2}[mhd]|[0-9]y)\.(parquet|csv)$", f.name, re.I)
    if match:
        symbol, tf, ext = match.groups()
        tf = tf.lower()
        ext = ext.lower()
        norm_name = f"{symbol.upper()}_{tf}.{ext}"
        if tf in valid_timeframes:
            if ext == "parquet":
                target = parquet_base / tf / norm_name
            else:
                target = csv_base / tf / norm_name
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                print(f"Eliminando duplicado: {f} (ya existe en {target})")
                f.unlink()
                skipped += 1
            else:
                print(f"Moviendo {f} -> {target}")
                shutil.move(str(f), str(target))
                moved += 1

print(f"Archivos movidos: {moved}")
print(f"Duplicados eliminados: {skipped}")
print("¡Clasificación completada!")
