"""
Script: scripts/research_edge.py
Responsibility: I1 - Investigación de edge real

Usage:
    python scripts/research_edge.py --symbol BTCUSDT
    python scripts/research_edge.py --symbol EURUSD --asset-class forex
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from core.ingestion.binance_client import BinanceClient
from core.ingestion.providers.mt5_client import MT5Client
from core.features.indicators import calculate_all
from core.ml.edge_research import EdgeResearcher, FeatureEdgeAnalyzer, run_edge_validation
from core.observability.logger import get_logger

logger = get_logger(__name__)


async def fetch_data(symbol: str, asset_class: str, limit: int = 500) -> pd.DataFrame:
    """Fetch OHLCV data for symbol."""
    if asset_class == "crypto":
        client = BinanceClient(api_key="", secret_key="", testnet=True)
        await client.connect()
        df = await client.get_klines(symbol, "1h", limit)
        await client.disconnect()
    else:
        logger.warning("Using mock data for non-crypto")
        dates = pd.date_range(end=datetime.now(timezone.utc), periods=limit, freq="h")
        df = pd.DataFrame({
            "timestamp": dates,
            "open": 1.1000 + np.random.randn(limit) * 0.001,
            "high": 1.1010 + np.random.randn(limit) * 0.001,
            "low": 1.0990 + np.random.randn(limit) * 0.001,
            "close": 1.1000 + np.random.randn(limit) * 0.001,
            "volume": 10000 + np.random.randn(limit) * 1000,
        })

    return df


async def main():
    parser = argparse.ArgumentParser(description="I1 - Research real edge")
    parser.add_argument("--symbol", default="BTCUSDT", help="Symbol to analyze")
    parser.add_argument("--asset-class", default="crypto", help="Asset class: crypto, forex, indices")
    parser.add_argument("--bootstrap", type=int, default=1000, help="Number of bootstrap iterations")
    parser.add_argument("--cost-bps", type=int, default=10, help="Transaction cost in basis points")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"I1 - INVESTIGACIÓN DE EDGE REAL")
    print(f"{'='*60}")
    print(f"Symbol: {args.symbol}")
    print(f"Asset Class: {args.asset_class}")
    print(f"Bootstrap iterations: {args.bootstrap}")
    print(f"Transaction cost: {args.cost_bps} bps")
    print(f"{'='*60}\n")

    logger.info("i1_started", symbol=args.symbol)

    df = await fetch_data(args.symbol, args.asset_class)
    print(f"Fetched {len(df)} candles")

    print("\nCalculating features...")
    df_features = calculate_all(df)
    print(f"Calculated {len(df_features.columns)} features")

    target = (df_features["close"].shift(-1) / df_features["close"] - 1) > 0
    df_features["target"] = target.astype(int)
    df_features = df_features.dropna()

    print(f"\nAnalyzing edge with {args.bootstrap} bootstrap iterations...")
    researcher = EdgeResearcher(
        n_bootstrap=args.bootstrap,
        transaction_cost_bps=args.cost_bps
    )

    signals = df_features["close"].pct_change().shift(-1).apply(lambda x: 1 if x > 0 else -1)
    returns = df_features["close"].pct_change()

    result = researcher.validate_edge(returns, signals)

    print(f"\n{'='*60}")
    print(f"RESULTADOS")
    print(f"{'='*60}")
    print(f"Trades analyzed: {result.n_trades}")
    print(f"Sharpe (gross): {result.sharpe_oos:.4f}")
    print(f"Sharpe (net): {result.sharpe_net:.4f}")
    print(f"Max Drawdown: {result.max_drawdown:.4f}")
    print(f"Win Rate: {result.win_rate:.4f}")
    print(f"Profit Factor: {result.profit_factor:.4f}")
    print(f"P-value: {result.p_value:.4f}")
    print(f"\nEdge exists: {'YES' if result.edge_exists else 'NO'}")
    print(f"Recommendation: {result.recommendation}")
    print(f"{'='*60}\n")

    print("\nAnalyzing feature edge...")
    feature_cols = [
        "rsi_14", "macd_histogram", "adx_14", "atr_14",
        "bb_width", "volume_ratio", "vol_adj_ret",
        "hurst_exponent", "rolling_kurtosis", "z_score_vs_ma20"
    ]

    feature_results = await run_edge_validation(
        df_features,
        feature_cols,
        "target"
    )

    print(f"\nFeature Analysis:")
    print(f"{'Feature':<25} {'IC':<10} {'Edge':<10}")
    print(f"{'-'*45}")
    for feat in feature_results.get("features", {}).values():
        if "error" not in feat:
            print(f"{feat['feature']:<25} {feat.get('ic', 0):.4f}     {'YES' if feat.get('edge_exists') else 'NO'}")

    top = feature_results.get("overall", {}).get("top_features", [])
    if top:
        print(f"\nTop features: {[f['feature'] for f in top[:5]]}")

    logger.info("i1_completed", edge_exists=result.edge_exists, sharpe_net=result.sharpe_net)

    return 0 if result.edge_exists else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))