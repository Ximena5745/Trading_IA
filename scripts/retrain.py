"""
Script: scripts/retrain.py
Responsibility: Train TechnicalAgent on historical OHLCV data from parquet files.
  - Loads data/raw/{symbol}_{timeframe}.parquet
  - Calculates features via FeatureEngine
  - Creates labels: 1 = next candle close > current close, 0 = otherwise
  - Trains LightGBM model and saves to data/models/technical_{asset_class}_v1.pkl

Usage:
  python scripts/retrain.py --asset-class crypto --timeframe 1h
  python scripts/retrain.py --asset-class crypto --timeframe 1h --symbols BTCUSDT ETHUSDT
  python scripts/retrain.py --asset-class forex  --timeframe 1h   (FASE E)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.agents.technical_agent import FEATURE_ORDER, TechnicalAgent
from core.features.feature_engineering import FeatureEngine
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("retrain")

DATA_DIR   = Path(__file__).parent.parent / "data" / "raw"
MODELS_DIR = Path(__file__).parent.parent / "data" / "models"

ASSET_CLASS_SYMBOLS: dict[str, list[str]] = {
    "crypto": ["BTCUSDT", "ETHUSDT"],
    "forex":  ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"],
    "index":  ["US500", "US30", "UK100"],
    "commodity": ["XAUUSD"],
}

MODEL_PATHS: dict[str, str] = {
    "crypto":    "data/models/technical_crypto_v1.pkl",
    "forex":     "data/models/technical_forex_v1.pkl",
    "index":     "data/models/technical_index_v1.pkl",
    "commodity": "data/models/technical_commodity_v1.pkl",
}


def _load_parquet(symbol: str, timeframe: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{symbol}_{timeframe}.parquet"
    if not path.exists():
        logger.warning("parquet_not_found", path=str(path))
        return None
    df = pd.read_parquet(path)
    logger.info("parquet_loaded", symbol=symbol, rows=len(df))
    return df


def _build_features_and_labels(
    df: pd.DataFrame,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Returns (X, y) where:
      X: feature matrix [n_samples, n_features]
      y: binary label — 1 if next candle close > current close, else 0
    """
    engine = FeatureEngine()
    feature_sets = engine.calculate_batch(df)

    if len(feature_sets) < 2:
        raise ValueError("Insufficient data for training (need at least 2 rows)")

    # y[i] = direction of candle i+1
    closes = [float(fs.close) for fs in feature_sets]
    y = np.array(
        [1 if closes[i + 1] > closes[i] else 0 for i in range(len(closes) - 1)],
        dtype=np.int32,
    )
    # X excludes the last row (no label for it)
    X = np.array(
        [[getattr(fs, f) for f in FEATURE_ORDER] for fs in feature_sets[:-1]],
        dtype=np.float32,
    )
    return X, y


def retrain(asset_class: str, timeframe: str, symbols: list[str]) -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = MODEL_PATHS[asset_class]

    print("\n🤖 TRADER AI — Retraining TechnicalAgent")
    print(f"   Asset class : {asset_class}")
    print(f"   Timeframe   : {timeframe}")
    print(f"   Symbols     : {symbols}")
    print(f"   Model output: {model_path}\n")

    all_X: list[np.ndarray] = []
    all_y: list[np.ndarray] = []

    for symbol in symbols:
        df = _load_parquet(symbol, timeframe)
        if df is None:
            print(f"⚠️  {symbol}: parquet not found — run download_data.py first. Skipping.")
            continue
        try:
            X, y = _build_features_and_labels(df)
            all_X.append(X)
            all_y.append(y)
            print(f"   {symbol}: {len(X):,} samples, class balance {y.mean():.2%} BUY")
        except Exception as e:
            print(f"❌ {symbol}: feature calculation failed — {e}")
            logger.error("feature_build_failed", symbol=symbol, error=str(e))
            continue

    if not all_X:
        print("\n❌ No data available for training. Aborting.")
        sys.exit(1)

    X_train = np.vstack(all_X)
    y_train = np.concatenate(all_y)
    print(f"\n📦 Training on {len(X_train):,} samples ({y_train.mean():.2%} BUY)")

    agent = TechnicalAgent(model_path=model_path)
    try:
        agent.train(X_train, y_train)
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        logger.error("training_failed", error=str(e))
        sys.exit(1)

    print(f"\n✅ Model saved to {model_path}")
    print("   Run the pipeline to verify it generates signals correctly.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train TechnicalAgent from parquet data")
    parser.add_argument(
        "--asset-class",
        default="crypto",
        choices=list(ASSET_CLASS_SYMBOLS.keys()),
        help="Asset class to train on",
    )
    parser.add_argument("--timeframe", default="1h", help="Candle interval (must match downloaded data)")
    parser.add_argument(
        "--symbols",
        nargs="*",
        help="Override default symbols for this asset class (optional)",
    )
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else ASSET_CLASS_SYMBOLS[args.asset_class]
    retrain(args.asset_class, args.timeframe, symbols)


if __name__ == "__main__":
    main()
