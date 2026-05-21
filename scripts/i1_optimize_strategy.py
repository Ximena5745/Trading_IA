"""
Script: scripts/i1_optimize_strategy.py
Responsibility: Optimize I1 strategy params via purged k-fold or Optuna (Sharpe net objective).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.backtesting.costs import CostModel
from core.ml.i1_gate_validator import (
    get_asset_config,
    optimize_params,
    optimize_params_optuna,
    purged_cv_score,
    save_params,
)
from core.ml.i1_strategies import I1_STRATEGY_REGISTRY
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("i1_optimize")

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
PARAMS_DIR = Path(__file__).parent.parent / "data" / "models" / "i1_params"


def _load_ohlcv(symbol: str) -> pd.DataFrame | None:
    path = DATA_DIR / f"{symbol}_1h.parquet"
    if not path.exists():
        alt = DATA_DIR / "parquet" / "1h" / f"{symbol.lower()}_1h.parquet"
        path = alt if alt.exists() else path
    if not path.exists():
        return None
    return pd.read_parquet(path)


def main() -> None:
    parser = argparse.ArgumentParser(description="I1 purged-CV strategy optimization")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", required=True, choices=list(I1_STRATEGY_REGISTRY.keys()))
    parser.add_argument(
        "--wf-fraction",
        type=float,
        default=0.8,
        help="Fraction of data used for optimization (exclude holdout)",
    )
    parser.add_argument(
        "--optuna",
        action="store_true",
        help="Use Optuna TPE instead of grid search",
    )
    parser.add_argument("--n-trials", type=int, default=50, help="Optuna trials")
    args = parser.parse_args()

    df = _load_ohlcv(args.symbol)
    if df is None or len(df) < 500:
        logger.error("no_data", symbol=args.symbol)
        sys.exit(1)

    spec = I1_STRATEGY_REGISTRY[args.strategy]
    holdout_start = int(len(df) * args.wf_fraction)
    train_df = df.iloc[:holdout_start]
    returns = train_df["close"].pct_change().dropna()
    ref_price = float(train_df["close"].median())
    cost_model = CostModel()
    asset_cfg = get_asset_config(args.symbol)

    if args.optuna:
        best_params = optimize_params_optuna(
            train_df,
            returns,
            spec,
            args.symbol,
            cost_model,
            ref_price,
            asset_cfg,
            n_trials=args.n_trials,
        )
    else:
        best_params = optimize_params(
            train_df,
            returns,
            spec,
            args.symbol,
            cost_model,
            ref_price,
            asset_cfg,
            PARAMS_DIR,
        )

    score = purged_cv_score(
        train_df,
        returns,
        spec,
        best_params,
        args.symbol,
        cost_model,
        ref_price,
        asset_cfg,
    )

    out = save_params(args.symbol, args.strategy, best_params, PARAMS_DIR)
    result = {
        "symbol": args.symbol,
        "strategy": args.strategy,
        "params": best_params,
        "purged_cv_sharpe_net": round(score, 4),
        "optimizer": "optuna" if args.optuna else "grid",
        "params_file": str(out),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
