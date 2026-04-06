#!/usr/bin/env python3
"""
Script: download_crypto_data.py
Quick script to download CRYPTO data (BTCUSDT, ETHUSDT) using the fixed download_data.py
"""
import sys
from pathlib import Path
from scripts.download_data import download

# Configure path
sys.path.insert(0, str(Path(__file__).parent))

# Symbols and timeframes to download
SYMBOLS = ["BTCUSDT", "ETHUSDT"]
TIMEFRAMES = ["1m", "5m", "15m", "1h", "1d"]
YEARS = 2

def main():
    print("=" * 70)
    print("📊 DESCARGANDO DATOS CRYPTO")
    print("=" * 70)
    
    total = len(SYMBOLS) * len(TIMEFRAMES)
    completed = 0
    
    for symbol in SYMBOLS:
        print(f"\n🔷 {symbol}")
        print("-" * 70)
        
        for timeframe in TIMEFRAMES:
            completed += 1
            progress = f"[{completed}/{total}]"
            print(f"\n{progress} Descargando {symbol} {timeframe} (últimos {YEARS} años)...")
            
            try:
                download(symbol, timeframe, YEARS)
                print(f"✅ {symbol} {timeframe}: Completado")
            except Exception as e:
                print(f"❌ {symbol} {timeframe}: Error - {e}")
    
    print("\n" + "=" * 70)
    print("✨ DESCARGA COMPLETADA")
    print("=" * 70)

if __name__ == "__main__":
    main()
