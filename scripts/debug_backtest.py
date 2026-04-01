#!/usr/bin/env python3
"""Debug individual backtest para EURUSD para ver qué falla."""
import sys
from pathlib import Path
sys.path.insert(0, ".")

import pandas as pd
from core.agents.technical_agent import TechnicalAgent
from core.backtesting.engine import BacktestEngine

symbol = "EURUSD"
interval = "1d"
data_path = Path("data/raw/parquet") / interval / f"{symbol.lower()}_{interval}.parquet"

print(f"\n📁 Verificando datos para {symbol}...")
if not data_path.exists():
    print(f"❌ Archivo no existe: {data_path}")
    sys.exit(1)

df = pd.read_parquet(data_path)
print(f"   ✅ Archivo existe: {len(df)} filas")

if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

df = df.sort_values("timestamp").reset_index(drop=True)
df["symbol"] = symbol

print(f"   📊 Datos: {df['open'].min():.2f} - {df['close'].max():.2f}")
print(f"   📅 Rango: {df['timestamp'].min()} a {df['timestamp'].max()}")

if len(df) < 1000:
    print(f"⚠️  ADVERTENCIA: Solo {len(df)} < 1000 filas necesarias")
    print(f"   Aumentando a 1000 dias...")

# Load agent
model_file = "data/models/technical_forex_v1.pkl"
agent = TechnicalAgent(model_path=model_file)

def strategy_fn(features):
    out = agent.predict(features)
    score = out.score
    
    if score >= 0.15:  # BUY signal
        entry = features.close
        return {
            "action": "BUY",
            "entry_price": entry,
            "stop_loss": entry * 0.97,
            "take_profit": entry * 1.03,
        }
    if score <= -0.15:  # SELL signal
        entry = features.close
        return {
            "action": "SELL",
            "entry_price": entry,
            "stop_loss": entry * 1.03,
            "take_profit": entry * 0.97,
        }
    return None

print(f"\n🔧 Corriendo backtest with 700/200/100 windows...")
engine = BacktestEngine()
results = engine.run_walk_forward(
    df,
    strategy_fn,
    train_size=700,
    test_size=200,
    step_size=100,
    initial_capital=10_000.0,
)

print(f"   Windows: {len(results.get('windows', []))}")
print(f"   Total trades: {results.get('total_trades', 0)}")
print(f"   Sharpe: {results.get('sharpe_ratio', 0):.2f}")
print(f"   Win Rate: {results.get('win_rate', 0)*100:.1f}%")
print(f"   Final Capital: ${results.get('final_capital', 0):.2f}")

if len(results.get('windows', [])) == 0:
    print("\n⚠️  NO WINDOWS GENERADAS!")
    print("   Esto significa que el walk-forward no encontró datos suficientes")
