"""
Script: scripts/retrain.py
Responsibility: Train TechnicalAgent on historical OHLCV data from parquet files.
  - Loads data/raw/{symbol}_{timeframe}.parquet
  - Calculates features via FeatureEngine
  - Creates labels: 1 = next candle close > current close, 0 = otherwise
  - Trains LightGBM model and saves to data/models/technical_{asset_class}_v1.pkl

Usage:
  python scripts/retrain.py --asset-class forex --timeframe 1h
  python scripts/retrain.py --asset-class forex --symbol EURUSD --mtf
  python scripts/retrain.py --asset-class forex --symbol EURUSD GBPUSD --mtf --three-class
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

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
MODELS_DIR = Path(__file__).parent.parent / "data" / "models"

ASSET_CLASS_SYMBOLS: dict[str, list[str]] = {
    "crypto": ["BTCUSDT", "ETHUSDT"],
    "forex": ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"],
    "index": ["US500", "US30", "UK100"],
    "commodity": ["XAUUSD"],
}

# Base model paths (for backwards compatibility)
MODEL_PATHS: dict[str, str] = {
    "crypto": "data/models/technical_crypto_v1.pkl",
    "forex": "data/models/technical_forex_v1.pkl",
    "index": "data/models/technical_index_v1.pkl",
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


def _get_feature_columns(df_features: pd.DataFrame) -> list[str]:
    """Get list of feature columns, excluding non-numeric and target columns."""
    exclude_cols = {'timestamp', 'symbol', 'trend_direction', 'volatility_regime'}
    numeric_cols = []
    for c in df_features.columns:
        if c in exclude_cols:
            continue
        # Check if column is numeric
        if df_features[c].dtype in ['float64', 'float32', 'int64', 'int32']:
            numeric_cols.append(c)
        else:
            logger.warning(f"Excluding non-numeric column: {c}")
    return numeric_cols


def _build_features_and_labels(
    df: pd.DataFrame,
    symbol: str,
    use_mtf: bool = False,
    use_three_class: bool = False,
    threshold: float = 0.0003,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Returns (X, y, feature_names) where:
      X: feature matrix [n_samples, n_features]
      y: label array
        - Binary (use_three_class=False): 1 if next candle close > current close, else 0
        - Three class (use_three_class=True): 0=SELL, 1=HOLD, 2=BUY
      feature_names: list of feature column names used
    """
    engine = FeatureEngine()
    
    if use_mtf:
        # Multi-timeframe features
        df_features = engine.calculate_mtf_features(df, symbol)
        feature_names = _get_feature_columns(df_features)
        X = df_features[feature_names].values.astype(np.float32)
    else:
        # Standard single-timeframe features
        feature_sets = engine.calculate_batch(df, symbol=symbol)
        feature_names = FEATURE_ORDER
        X = np.array(
            [[getattr(fs, f) for f in FEATURE_ORDER] for fs in feature_sets],
            dtype=np.float32,
        )

    if len(X) < 2:
        raise ValueError("Insufficient data for training (need at least 2 rows)")

    # Create labels
    if use_three_class:
        # Three-class: SELL (0), HOLD (1), BUY (2)
        # Based on return threshold
        returns = np.diff(df['close'].values, prepend=np.nan)
        # We need closes aligned with features (X has n rows, closes has n+1)
        closes = df['close'].values[:-1] if len(df) > len(X) else df['close'].values
        
        # Calculate returns for the next period
        next_returns = []
        for i in range(len(closes) - 1):
            ret = (closes[i + 1] - closes[i]) / closes[i]
            next_returns.append(ret)
        next_returns = np.array(next_returns)
        
        # Create 3-class labels
        y = np.zeros(len(next_returns), dtype=np.int32)
        y[next_returns > threshold] = 2   # BUY
        y[np.abs(next_returns) <= threshold] = 1  # HOLD
        # SELL remains 0
        
        # Adjust X to match y length (X has n rows, y has n-1 rows from next_returns)
        if len(X) > len(y):
            X = X[:-1]
    else:
        # Binary: 1 if next close > current close
        closes = df['close'].values
        y = np.array(
            [1 if closes[i + 1] > closes[i] else 0 for i in range(len(closes) - 1)],
            dtype=np.int32,
        )
        if len(X) > len(y):
            X = X[:-1]
    
    return X, y, feature_names


def retrain(
    asset_class: str,
    timeframe: str,
    symbols: list[str],
    use_mtf: bool = False,
    use_three_class: bool = False,
) -> None:
    """
    Train models for specified symbols.
    
    Args:
        asset_class: Asset class (forex, index, commodity, crypto)
        timeframe: Data timeframe (1h, 4h, 1d)
        symbols: List of symbols to train on
        use_mtf: Whether to use multi-timeframe features
        use_three_class: Whether to use 3-class classification (BUY/HOLD/SELL)
    """
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Determine model path
    # If single symbol specified, save as per-symbol model
    if len(symbols) == 1 and use_mtf:
        model_path = f"data/models/technical_{symbols[0].lower()}_mtf_v1.pkl"
    elif len(symbols) == 1 and use_three_class:
        model_path = f"data/models/technical_{symbols[0].lower()}_3c_v1.pkl"
    elif use_mtf:
        model_path = f"data/models/technical_{asset_class}_mtf_v1.pkl"
    else:
        model_path = MODEL_PATHS.get(asset_class, f"data/models/technical_{asset_class}_v1.pkl")

    # Determine label type for display
    label_type = "3-class (BUY/HOLD/SELL)" if use_three_class else "binary (BUY/SELL)"
    
    print("\n🤖 TRADER AI — Retraining TechnicalAgent")
    print(f"   Asset class : {asset_class}")
    print(f"   Timeframe   : {timeframe}")
    print(f"   Symbols     : {symbols}")
    print(f"   Label type  : {label_type}")
    print(f"   MTF         : {'Yes (1h+4h+1d)' if use_mtf else 'No'}")
    print(f"   Model output: {model_path}\n")

    all_X: list[np.ndarray] = []
    all_y: list[np.ndarray] = []
    feature_names: list[str] = []

    for symbol in symbols:
        df = _load_parquet(symbol, timeframe)
        if df is None:
            print(f"⚠️  {symbol}: parquet not found — run download_data.py first. Skipping.")
            continue
        try:
            X, y, feat_names = _build_features_and_labels(
                df, symbol, use_mtf=use_mtf, use_three_class=use_three_class
            )
            all_X.append(X)
            all_y.append(y)
            if not feature_names:
                feature_names = feat_names
            
            if use_three_class:
                buy_pct = (y == 2).mean() * 100
                hold_pct = (y == 1).mean() * 100
                sell_pct = (y == 0).mean() * 100
                print(f"   {symbol}: {len(X):,} samples, BUY={buy_pct:.1f}% HOLD={hold_pct:.1f}% SELL={sell_pct:.1f}%")
            else:
                buy_pct = y.mean() * 100
                print(f"   {symbol}: {len(X):,} samples, BUY={buy_pct:.2f}%")
        except Exception as e:
            print(f"❌ {symbol}: feature calculation failed — {e}")
            logger.error("feature_build_failed", symbol=symbol, error=str(e))
            continue

    if not all_X:
        print("\n❌ No data available for training. Aborting.")
        sys.exit(1)

    X_train = np.vstack(all_X)
    y_train = np.concatenate(all_y)
    
    if use_three_class:
        print(f"\n📦 Training on {len(X_train):,} samples (BUY={ (y_train == 2).mean():.2%}, HOLD={ (y_train == 1).mean():.2%}, SELL={ (y_train == 0).mean():.2%})")
    else:
        print(f"\n📦 Training on {len(X_train):,} samples ({y_train.mean():.2%} BUY)")

    # Store feature names with model for later use
    agent = TechnicalAgent(model_path=model_path)
    agent._feature_names = feature_names  # Store for reference
    
    try:
        agent.train(X_train, y_train, use_three_class=use_three_class)
    except Exception as e:
        print(f"\n❌ Training failed: {e}")
        logger.error("training_failed", error=str(e))
        sys.exit(1)

    print(f"\n✅ Model saved to {model_path}")
    print(f"   Features: {len(feature_names)}")
    print("   Run the pipeline to verify it generates signals correctly.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train TechnicalAgent from parquet data"
    )
    parser.add_argument(
        "--asset-class",
        default="crypto",
        choices=list(ASSET_CLASS_SYMBOLS.keys()),
        help="Asset class to train on",
    )
    parser.add_argument(
        "--timeframe", default="1h", help="Candle interval (must match downloaded data)"
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        help="Override default symbols for this asset class (optional)",
    )
    parser.add_argument(
        "--mtf",
        action="store_true",
        help="Use multi-timeframe features (1h + 4h + 1d)",
    )
    parser.add_argument(
        "--three-class",
        action="store_true",
        help="Use 3-class classification (BUY/HOLD/SELL) instead of binary",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0003,
        help="Return threshold for HOLD class (default: 0.0003 = 0.03%%)",
    )
    args = parser.parse_args()

    symbols = args.symbols if args.symbols else ASSET_CLASS_SYMBOLS[args.asset_class]
    retrain(
        args.asset_class,
        args.timeframe,
        symbols,
        use_mtf=args.mtf,
        use_three_class=args.three_class,
    )


if __name__ == "__main__":
    main()
