"""Quick test script for MTF features"""
from core.features.feature_engineering import FeatureEngine
import pandas as pd

df = pd.read_parquet('data/raw/EURUSD_1h.parquet')
print(f'Loaded {len(df)} rows')

engine = FeatureEngine()
features = engine.calculate_mtf_features(df, 'EURUSD')

print(f'\nShape: {features.shape}')
print(f'Total columns: {len(features.columns)}')

# Check alignment features
alignment_cols = [c for c in features.columns if 'alignment' in c or 'divergence' in c]
print(f'\nAlignment/Divergence columns: {alignment_cols}')

# Check sample values
print(f'\ntrend_alignment values: {features["trend_alignment"].dropna().head()}')
print(f'\nrsi_divergence_4h values: {features["rsi_divergence_4h"].dropna().head()}')

# Summary
print('\n✅ MTF Feature Generation Summary:')
print(f'  - 1h features: {len([c for c in features.columns if not c.endswith(("_4h", "_1d"))])}')
print(f'  - 4h features: {len([c for c in features.columns if c.endswith("_4h")])}')
print(f'  - 1d features: {len([c for c in features.columns if c.endswith("_1d")])}')
print(f'  - Alignment features: {len(alignment_cols)}')
