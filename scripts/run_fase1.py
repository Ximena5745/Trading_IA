"""Ejecuta secuencia completa FASE 1 y valida resultados"""
import subprocess
import sys
from pathlib import Path

steps = [
    {
        "name": "Binance - descargar cripto",
        "cmd": [sys.executable, "scripts/download_binance.py", "--all", "--years", "2"],
    },
    {
        "name": "Forex/Commodities/Indices - descargar con yfinance",
        "cmd": [sys.executable, "scripts/download_forex.py", "--years", "2", "--interval", "1h"],
    },
    {
        "name": "Validación total de data/raw y data/processed",
        "cmd": [sys.executable, "scripts/validate_data.py", "--all", "--verbose"],
    },
]


def run_cmd(step):
    print("\n" + "=" * 70)
    print(f" EJECUTANDO: {step['name']}")
    print("=" * 70)
    try:
        sp = subprocess.run(step["cmd"], capture_output=True, text=True, check=True)
        print(sp.stdout)
        if sp.stderr:
            print("STDERR:", sp.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error en paso {step['name']} (exit {e.returncode})")
        print("stdout:\n", e.stdout)
        print("stderr:\n", e.stderr)
        return False


def main():
    results = []

    for step in steps:
        ok = run_cmd(step)
        results.append((step["name"], ok))
        if not ok:
            print("Deteniendo ejecución porque un paso falló.")
            break

    print("\n" + "#" * 70)
    print("Resumen FASE 1")
    for name, ok in results:
        status = "OK" if ok else "FAIL"
        print(f"- {name}: {status}")
    print("#" * 70)

    # Verificar archivos base
    raw_files = list(Path("data/raw").glob("*.parquet"))
    print(f"Archivos en data/raw: {len(raw_files)}")
    for f in sorted(raw_files):
        print("  -", f.name)

    print("\nFase 1 terminada (ejecución completa).")


if __name__ == '__main__':
    main()
