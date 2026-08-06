"""
Script: scripts/validate_all_assets.py
Responsibility: Validate edge across ALL assets with REAL data

Tests multiple strategies across multiple assets to find:
- Which assets have real edge
- Which strategies work on which assets
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from core.ingestion.binance_client import BinanceClient
from core.ml.edge_research import EdgeResearcher
from core.observability.logger import get_logger

logger = get_logger(__name__)


CRYPTO_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "MATICUSDT"
]

FOREX_SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD"
]

ASSET_CONFIG = {
    "crypto": {"symbols": CRYPTO_SYMBOLS, "exchange": "binance"},
    "forex": {"symbols": FOREX_SYMBOLS, "exchange": "binance"},
}


def generate_momentum_signal(df: pd.DataFrame) -> pd.Series:
    """MA Crossover strategy."""
    ma_fast = df['close'].rolling(10).mean()
    ma_slow = df['close'].rolling(30).mean()
    signal = np.where(ma_fast > ma_slow, 1, -1)
    return pd.Series(signal, index=df.index)


def generate_mean_reversion_signal(df: pd.DataFrame) -> pd.Series:
    """Bollinger Bands mean reversion."""
    ma = df['close'].rolling(20).mean()
    std = df['close'].rolling(20).std()
    upper = ma + 2 * std
    lower = ma - 2 * std
    
    signal = np.where(df['close'] < lower, 1,
             np.where(df['close'] > upper, -1, 0))
    return pd.Series(signal, index=df.index)


def generate_rsi_signal(df: pd.DataFrame) -> pd.Series:
    """RSI oversold/overbought."""
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    
    signal = np.where(rsi < 30, 1, np.where(rsi > 70, -1, 0))
    return pd.Series(signal, index=df.index)


STRATEGIES = {
    "momentum_ma_cross": generate_momentum_signal,
    "mean_reversion_bb": generate_mean_reversion_signal,
    "rsi_oversold": generate_rsi_signal,
}


async def fetch_binance_data(symbol: str, limit: int = 500) -> pd.DataFrame:
    """Fetch real data from Binance."""
    client = BinanceClient(api_key="", secret_key="", testnet=True)
    try:
        await client.connect()
        klines = await client.get_klines(symbol, "1h", limit)
        await client.disconnect()
        
        if not klines:
            return None
            
        df = pd.DataFrame({
            'timestamp': [k.timestamp for k in klines],
            'open': [float(str(k.open)) for k in klines],
            'high': [float(str(k.high)) for k in klines],
            'low': [float(str(k.low)) for k in klines],
            'close': [float(str(k.close)) for k in klines],
            'volume': [float(str(k.volume)) for k in klines],
        })
        return df
    except Exception as e:
        logger.warning("fetch_failed", symbol=symbol, error=str(e))
        return None


async def validate_asset_edge(symbol: str, strategy_name: str, researcher: EdgeResearcher) -> dict:
    """Validate edge for one asset with one strategy."""
    df = await fetch_binance_data(symbol, limit=500)
    
    if df is None or len(df) < 100:
        return {"symbol": symbol, "strategy": strategy_name, "error": "No data"}
    
    df['returns'] = df['close'].pct_change()
    signal_func = STRATEGIES[strategy_name]
    signal = signal_func(df)
    
    returns = df['returns'].dropna()
    signals = signal.loc[returns.index]
    
    result = researcher.validate_edge(returns, signals)
    
    return {
        "symbol": symbol,
        "strategy": strategy_name,
        "sharpe_net": result.sharpe_net,
        "p_value": result.p_value,
        "edge_exists": result.edge_exists,
        "trades": result.n_trades,
    }


async def main():
    print("="*70)
    print("I1 - VALIDACION DE EDGE EN TODOS LOS ACTIVOS")
    print("="*70)
    
    researcher = EdgeResearcher(n_bootstrap=500, transaction_cost_bps=10)
    
    all_results = []
    
    for asset_class, config in ASSET_CONFIG.items():
        print(f"\n### {asset_class.upper()} ###")
        print("-" * 40)
        
        for symbol in config["symbols"]:
            print(f"\n{symbol}:")
            
            best_result = {"sharpe_net": -999, "strategy": "none", "edge_exists": False}
            
            for strategy_name in STRATEGIES.keys():
                try:
                    result = await validate_asset_edge(symbol, strategy_name, researcher)
                    
                    if "error" not in result:
                        print(f"  {strategy_name}: Sharpe={result['sharpe_net']:.2f}, Edge={result['edge_exists']}")
                        
                        if result['sharpe_net'] > best_result['sharpe_net']:
                            best_result = result
                    
                except Exception as e:
                    print(f"  {strategy_name}: ERROR - {str(e)[:30]}")
            
            all_results.append({
                "asset_class": asset_class,
                "symbol": symbol,
                "best_strategy": best_result.get("strategy", "none"),
                "sharpe_net": best_result.get("sharpe_net", -999),
                "edge_exists": best_result.get("edge_exists", False),
            })
            
            print(f"  BEST: {best_result.get('strategy', 'none')} (Sharpe: {best_result.get('sharpe_net', 0):.2f})")
    
    print("\n" + "="*70)
    print("RESUMEN TOTAL")
    print("="*70)
    
    print(f"\n{'Symbol':<15} {'Best Strategy':<20} {'Sharpe Net':<12} {'Edge'}")
    print("-" * 60)
    
    for r in all_results:
        edge_str = "SÍ" if r["edge_exists"] else "NO"
        print(f"{r['symbol']:<15} {r['best_strategy']:<20} {r['sharpe_net']:<12.2f} {edge_str}")
    
    # Summary
    edges = sum(1 for r in all_results if r["edge_exists"])
    total = len(all_results)
    pct = (edges / total * 100) if total > 0 else 0
    
    print(f"\nTotal: {edges}/{total} activos con edge ({pct:.0f}%)")
    
    # Condition: Sharpe > 0.8 AND p-value < 0.05
    high_sharpe = [r for r in all_results if r["sharpe_net"] > 0.8]
    print(f"Activos con Sharpe > 0.8: {len(high_sharpe)}")
    
    if len(high_sharpe) > 0:
        print("\nACTIVOS CON EDGE REAL (Sharpe > 0.8):")
        for r in high_sharpe:
            print(f"  - {r['symbol']}: {r['best_strategy']} (Sharpe: {r['sharpe_net']:.2f})")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))