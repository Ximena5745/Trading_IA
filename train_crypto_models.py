#!/usr/bin/env python3
"""
Script: train_crypto_models.py
Train LightGBM models for CRYPTO asset class (BTCUSDT, ETHUSDT)
"""
import sys
import subprocess
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("=" * 70)
    print("🚀 ENTRENANDO MODELOS CRYPTO")
    print("=" * 70)
    
    # Train crypto model with single-timeframe features
    print("\n[1/2] Entrenando modelo CRYPTO (single-timeframe)...")
    print("-" * 70)
    
    cmd1 = 'python scripts/retrain.py --asset-class crypto --timeframe 1h'
    result1 = subprocess.run(cmd1, shell=True)
    
    if result1.returncode == 0:
        print("✅ Modelo CRYPTO entrenado exitosamente")
    else:
        print("⚠️  Error entrenando modelo CRYPTO (single-timeframe)")
    
    # Train crypto model with multi-timeframe features
    print("\n[2/2] Entrenando modelo CRYPTO (multi-timeframe)...")
    print("-" * 70)
    
    cmd2 = 'python scripts/retrain.py --asset-class crypto --timeframe 1h --mtf'
    result2 = subprocess.run(cmd2, shell=True)
    
    if result2.returncode == 0:
        print("✅ Modelo CRYPTO MTF entrenado exitosamente")
    else:
        print("⚠️  Error entrenando modelo CRYPTO (multi-timeframe)")
    
    print("\n" + "=" * 70)
    print("✨ ENTRENAMIENTO COMPLETADO")
    print("=" * 70)
    
    # Check results
    models_dir = Path("data/models")
    if models_dir.exists():
        models = list(models_dir.glob("technical_crypto*.pkl"))
        if models:
            print("\n📊 Modelos generados:")
            for model_file in sorted(models):
                print(f"  ✓ {model_file.name}")
    
    return 0 if (result1.returncode == 0 and result2.returncode == 0) else 1

if __name__ == "__main__":
    sys.exit(main())
