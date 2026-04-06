"""Test the trained MTF model predictions"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.technical_agent import TechnicalAgent
from core.features.feature_engineering import FeatureEngine
import pandas as pd

print("Testing Trained MTF Model Predictions...")

# Load model
model_path = "data/models/technical_forex_v1.pkl"
agent = TechnicalAgent(model_path=model_path)

print(f"Model loaded: {agent.is_ready()}")
print(f"Using 3-class: {agent._use_three_class}")
print(f"Feature count: {len(agent._feature_names)}")

# Load data and predict (need at least 200 candles for indicators)
df = pd.read_parquet('data/raw/EURUSD_1h.parquet')
engine = FeatureEngine()
# Use last 300 candles to ensure we have enough for indicators
features = engine.calculate(df.tail(300), symbol='EURUSD')

# Get prediction
output = agent.predict(features)

print(f"\nPrediction for EURUSD (last candle):")
print(f"  Direction: {output.direction}")
print(f"  Score: {output.score}")
print(f"  Confidence: {output.confidence}")
print(f"  Agent ID: {output.agent_id}")

# Test on a few more candles (need 200+ for indicators)
print(f"\nTesting last 5 candles:")
for i in range(5):
    subset = df.tail(300 - i)
    feat = engine.calculate(subset, symbol='EURUSD')
    out = agent.predict(feat)
    print(f"  [{i}] Direction: {out.direction:6} | Score: {out.score:+.3f} | Confidence: {out.confidence:.2%}")

print("\n✅ Model prediction test complete!")
