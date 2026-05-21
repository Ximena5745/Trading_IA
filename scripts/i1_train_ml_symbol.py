"""
Script: scripts/i1_train_ml_symbol.py
Responsibility: Train per-symbol LightGBM I1 fallback model (ternary target).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ml.i1_ml_signal import DEFAULT_ML_MODEL_DIR, model_path_for, train_ml_signal_model
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("i1_train_ml")

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"


def _load_ohlcv(symbol: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{symbol}_1h.parquet"
    if not path.exists():
        alt = DATA_DIR / "parquet" / "1h" / f"{symbol.lower()}_1h.parquet"
        path = alt if alt.exists() else path
    if not path.exists():
        return None
    return pd.read_parquet(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train I1 ML fallback model for one symbol")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--forward-bars", type=int, default=6)
    parser.add_argument(
        "--wf-fraction",
        type=float,
        default=0.8,
        help="Train only on pre-holdout slice (no leakage into holdout)",
    )
    args = parser.parse_args()

    df = _load_ohlcv(args.symbol)
    if df is None or len(df) < 1000:
        logger.error("no_data", symbol=args.symbol)
        sys.exit(1)

    train_end = int(len(df) * args.wf_fraction)
    train_df = df.iloc[:train_end]

    try:
        out = train_ml_signal_model(
            train_df,
            args.symbol,
            forward_bars=args.forward_bars,
            model_dir=DEFAULT_ML_MODEL_DIR,
        )
    except ValueError as e:
        logger.error("train_failed", symbol=args.symbol, error=str(e))
        sys.exit(1)

    print(
        json.dumps(
            {
                "symbol": args.symbol,
                "model_path": str(out),
                "train_rows": train_end,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
