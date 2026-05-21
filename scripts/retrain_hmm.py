"""
Script: HMM Retraining
M3.3: Reentrenamiento automático del HMM cada 30 días.

Usage:
    python scripts/retrain_hmm.py --symbol BTCUSDT
    python scripts/retrain_hmm.py --all-symbols  # reentrenar todos
"""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_historical_data(symbol: str, lookback_days: int = 365) -> pd.DataFrame:
    """Load historical data for HMM training."""
    data_dir = PROJECT_ROOT / "data" / "raw"
    symbol_file = data_dir / f"{symbol}_1h.parquet"

    if not symbol_file.exists():
        raise FileNotFoundError(f"Data not found for {symbol}")

    df = pd.read_parquet(symbol_file)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    cutoff = datetime.now() - timedelta(days=lookback_days)
    df = df[df['timestamp'] >= cutoff]

    return df


def prepare_hmm_features(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare features for HMM training."""
    df = df.copy()

    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['returns'].rolling(24).std() * np.sqrt(24)

    df['adx_14'] = 20.0
    df['hurst_exponent'] = 0.5

    df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()

    high = df['high']
    low = df['low']
    close = df['close']
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    df['atr_14'] = tr.rolling(14).mean()

    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']

    df = df.dropna()
    df = df.reset_index(drop=True)

    return df


def train_hmm_model(df: pd.DataFrame, n_states: int = 8) -> tuple:
    """Train HMM model on prepared data."""
    from core.adaptation.hmm_regime_detector import HMMRegimeDetector, HMM_AVAILABLE

    if not HMM_AVAILABLE:
        raise ImportError("hmmlearn not available")

    detector = HMMRegimeDetector(n_states=n_states, retrain_days=30)
    detector.fit(df)

    return detector


def save_hmm_model(detector, symbol: str, output_dir: Path = None) -> Path:
    """Save trained HMM model."""
    import pickle

    if output_dir is None:
        output_dir = PROJECT_ROOT / "data" / "models" / "hmm"

    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = output_dir / f"hmm_{symbol}_{timestamp}.pkl"

    with open(model_path, 'wb') as f:
        pickle.dump({
            'detector': detector,
            'trained_at': timestamp,
            'symbol': symbol,
        }, f)

    latest_link = output_dir / f"hmm_{symbol}_latest.pkl"
    with open(latest_link, 'wb') as f:
        pickle.dump({
            'detector': detector,
            'trained_at': timestamp,
            'symbol': symbol,
        }, f)

    return model_path


def run_hmm_retraining(symbol: str, lookback_days: int = 365) -> dict:
    """Run HMM retraining for a symbol."""
    print(f"Loading historical data for {symbol} (last {lookback_days} days)...")
    df = load_historical_data(symbol, lookback_days)
    print(f"Loaded {len(df)} samples")

    print("Preparing features...")
    df_features = prepare_hmm_features(df)
    print(f"Features prepared: {len(df_features)} samples")

    print("Training HMM model with 8 states...")
    detector = train_hmm_model(df_features, n_states=8)

    print("Saving model...")
    model_path = save_hmm_model(detector, symbol)

    print(f"\n=== HMM Retraining Complete ===")
    print(f"Symbol: {symbol}")
    print(f"Model saved: {model_path}")
    print(f"Last training: {detector._last_train}")

    return {
        'symbol': symbol,
        'model_path': str(model_path),
        'n_samples': len(df_features),
        'last_train': str(detector._last_train),
    }


def main():
    parser = argparse.ArgumentParser(description='HMM Model Retraining')
    parser.add_argument('--symbol', type=str, default='BTCUSDT', help='Symbol to retrain')
    parser.add_argument('--all-symbols', action='store_true', help='Retrain all available symbols')
    parser.add_argument('--lookback-days', type=int, default=365, help='Lookback period in days')

    args = parser.parse_args()

    if args.all_symbols:
        data_dir = PROJECT_ROOT / "data" / "raw"
        symbols = [f.stem.replace('_1h', '') for f in data_dir.glob('*_1h.parquet')]
        print(f"Found {len(symbols)} symbols: {symbols}")

        results = []
        for symbol in symbols:
            try:
                result = run_hmm_retraining(symbol, args.lookback_days)
                results.append(result)
            except Exception as e:
                print(f"Failed to retrain {symbol}: {e}")

        print(f"\n=== Summary ===")
        print(f"Successfully retrained: {len(results)}/{len(symbols)}")
    else:
        result = run_hmm_retraining(args.symbol, args.lookback_days)
        print(f"\nModel ready for: {result['symbol']}")


if __name__ == '__main__':
    main()