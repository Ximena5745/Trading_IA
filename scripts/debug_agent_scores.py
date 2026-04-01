#!/usr/bin/env python3
"""Debug de scores del agente técnico para ver por qué no genera señales."""
import sys
from pathlib import Path
sys.path.insert(0, ".")

import pandas as pd
from core.agents.technical_agent import TechnicalAgent
from core.features.feature_engineering import FeatureEngine

symbols = {
    "EURUSD": "data/models/technical_forex_v1.pkl",
    "GBPUSD": "data/models/technical_forex_v1.pkl",
    "USDJPY": "data/models/technical_forex_v1.pkl",
    "XAUUSD": "data/models/technical_commodity_v1.pkl",
    "US500": "data/models/technical_index_v1.pkl",
    "US30": "data/models/technical_index_v1.pkl",
}

print("=" * 80)
print("DEBUG: SCORES DEL AGENTE TÉCNICO (primeras 50 candles de test)")
print("=" * 80)

for symbol, model_path in symbols.items():
    data_path = Path("data/raw/parquet/1d") / f"{symbol.lower()}_1d.parquet"
    
    if not data_path.exists():
        print(f"\n❌ {symbol:10s} - ARCHIVO NO EXISTE")
        continue
    
    df = pd.read_parquet(data_path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["symbol"] = symbol
    
    # Aislar últimas 250 filas para simular ventana de test
    test_df = df.tail(250).reset_index(drop=True)
    
    agent = TechnicalAgent(model_path=model_path)
    engine = FeatureEngine()
    
    try:
        features_list = engine.calculate_batch(test_df, symbol=symbol)
    except Exception as e:
        print(f"\n⚠️  {symbol:10s} - Feature error: {e}")
        continue
    
    scores = []
    for i, fs in enumerate(features_list):
        out = agent.predict(fs)
        scores.append(out.score)
    
    scores_array = pd.Series(scores)
    
    # Contar cuántos scores caen en rango de operación
    buy_signals = (scores_array >= 0.15).sum()
    sell_signals = (scores_array <= -0.15).sum()
    neutral = len(scores_array) - buy_signals - sell_signals
    
    print(f"\n✅ {symbol:10s}")
    print(f"   Scores:  min={scores_array.min():7.3f}, max={scores_array.max():7.3f}, mean={scores_array.mean():7.3f}")
    print(f"   BUY (≥0.15):   {buy_signals:3d}/250 ({buy_signals/250*100:5.1f}%)")
    print(f"   SELL (≤-0.15): {sell_signals:3d}/250 ({sell_signals/250*100:5.1f}%)")
    print(f"   NEUTRAL:       {neutral:3d}/250 ({neutral/250*100:5.1f}%)")
    
    # Mostrar distribución
    print(f"   Distribución: ", end="")
    for q in [0.1, 0.25, 0.5, 0.75, 0.9]:
        print(f"Q{int(q*100)}={scores_array.quantile(q):.3f} ", end="")
    print()

print("\n" + "=" * 80)
