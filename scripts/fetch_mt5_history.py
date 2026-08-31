"""
Script: scripts/fetch_mt5_history.py

Pull deep OHLCV history for the traded universe from a local MetaTrader 5 terminal
(IC Markets by default — see docs/CORE_VALIDATION_RAMA1_2026-08-30.md) and persist
it as the standard project parquet layout:

    data/raw/<SYM>_<tf>_mt5.parquet            raw OHLCV archive
    data/raw/parquet/<tf>/<sym>_<tf>.parquet   enriched (standard indicator set)

The enriched file carries adx_14 + rsi_14 so core.ml.i1_strategies._ensure_indicators
short-circuits (skips calculate_advanced_features, which is O(n) per row).

Rama 2 of the pivote uses this for the 4h / 1d sweep.

Usage:
  python scripts/fetch_mt5_history.py --timeframes 1h 4h 1d
  python scripts/fetch_mt5_history.py --symbols XAUUSD EURUSD --timeframes 1d
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.features.indicators import (  # noqa: E402
    _calc_adx, _calc_atr, _calc_bollinger, _calc_ema, _calc_macd, _calc_returns,
    _calc_rsi, _calc_temporal_features, _calc_trend_direction,
    _calc_vol_adj_returns, _calc_volatility_regime, _calc_volume_indicators,
)

DEFAULT_TERMINAL = r"C:\Program Files\MetaTrader 5 IC Markets Global\terminal64.exe"

# canonical symbol -> MT5 symbol on IC Markets (verified 2026-08-31)
MT5_SYMBOL = {
    "XAUUSD": "XAUUSD", "XAGUSD": "XAGUSD",
    "EURUSD": "EURUSD", "GBPUSD": "GBPUSD", "USDJPY": "USDJPY",
    "USDCHF": "USDCHF", "AUDUSD": "AUDUSD", "USDCAD": "USDCAD",
    "US500": "US500", "US30": "US30", "NAS100": "USTEC",
    # crypto CFDs (proxy for the Binance spot pairs)
    "BTCUSDT": "BTCUSD", "ETHUSDT": "ETHUSD",
}

_ENRICH = (
    _calc_rsi, _calc_ema, _calc_macd, _calc_atr, _calc_bollinger,
    _calc_volume_indicators, _calc_trend_direction, _calc_volatility_regime,
    _calc_returns, _calc_adx, _calc_vol_adj_returns, _calc_temporal_features,
)


def _tf_const(mt5, tf: str):
    return {"1h": mt5.TIMEFRAME_H1, "4h": mt5.TIMEFRAME_H4, "1d": mt5.TIMEFRAME_D1}[tf]


def _deep_pull(mt5, sym: str, tf_const):
    """copy_rates_from_pos does NOT clamp: n > cached bar count -> Invalid params.
    Step n downward until it returns rows."""
    for n in (200_000, 120_000, 90_000, 70_000, 50_000, 30_000, 15_000, 5_000):
        r = mt5.copy_rates_from_pos(sym, tf_const, 0, n)
        if r is not None and len(r):
            return r
    return None


def _enrich(df: pd.DataFrame) -> pd.DataFrame:
    e = df.copy()
    for c in ("open", "high", "low", "close", "volume"):
        e[c] = e[c].astype(float)
    for fn in _ENRICH:
        e = fn(e)
    return e


def main() -> None:
    import MetaTrader5 as mt5

    ap = argparse.ArgumentParser(description="Pull MT5 OHLCV history for the universe")
    ap.add_argument("--symbols", nargs="*", default=None,
                    help="canonical symbols (default: everything MT5 can serve)")
    ap.add_argument("--timeframes", nargs="*", default=["1h", "4h", "1d"])
    ap.add_argument("--terminal", default=DEFAULT_TERMINAL)
    args = ap.parse_args()

    symbols = args.symbols or list(MT5_SYMBOL)
    unknown = [s for s in symbols if s not in MT5_SYMBOL]
    if unknown:
        print(f"no MT5 mapping for: {unknown} (add to MT5_SYMBOL)")
        symbols = [s for s in symbols if s in MT5_SYMBOL]

    if not mt5.initialize(path=args.terminal):
        print(f"mt5.initialize failed: {mt5.last_error()}")
        sys.exit(1)
    ai = mt5.account_info()
    print(f"terminal: {mt5.terminal_info().company} | account {ai.login} {ai.server}")

    raw_dir = Path("data/raw")
    for tf in args.timeframes:
        tfc = _tf_const(mt5, tf)
        out_dir = Path(f"data/raw/parquet/{tf}")
        out_dir.mkdir(parents=True, exist_ok=True)
        for canon in symbols:
            msym = MT5_SYMBOL[canon]
            mt5.symbol_select(msym, True)
            t0 = time.time()
            rates = _deep_pull(mt5, msym, tfc)
            if rates is None:
                print(f"  {canon:8} {tf:3} -> no data ({mt5.last_error()})")
                continue
            df = pd.DataFrame(rates)
            df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
            df = df.rename(columns={"tick_volume": "volume"})
            df = df[["timestamp", "open", "high", "low", "close", "volume"]]
            df = df.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
            df.to_parquet(raw_dir / f"{canon}_{tf}_mt5.parquet")
            enr = _enrich(df)
            enr.to_parquet(out_dir / f"{canon.lower()}_{tf}.parquet")
            yrs = (df.timestamp.max() - df.timestamp.min()).days / 365
            print(f"  {canon:8} {tf:3} -> {len(df):>7} bars  "
                  f"{df.timestamp.min().date()}..{df.timestamp.max().date()}  "
                  f"(~{yrs:4.1f}y)  {time.time()-t0:4.1f}s")

    mt5.shutdown()


if __name__ == "__main__":
    main()
