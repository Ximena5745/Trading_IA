"""
Script: scripts/run_quant_report.py  (SPEC-C01 / Fase 2, entregable 2.5)

Consolidated quant report per (asset, strategy) on walk-forward, holdout and full
splits. Reuses the I1 gate machinery (same signal prep, same cost model, same
holdout fraction) so the numbers are comparable to data/reports/i1_gate_report.json.

Metrics per split: Sharpe (net & gross), Sortino, Calmar, expectancy, profit
factor, win rate, max drawdown, exposure, turnover, cost drag, tail ratio.

Outputs:
  data/reports/quant_report.json   — full detail
  data/reports/quant_report.md     — compact table

Usage:
  python scripts/run_quant_report.py [--symbols BTCUSDT ETHUSDT] [--out data/reports]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.backtesting.costs import CostModel
from core.backtesting.metrics import (
    calmar_ratio,
    expectancy,
    max_drawdown,
    profit_factor,
    sharpe_ratio,
    sortino_ratio,
    win_rate,
)
from core.config.constants import TRADED_UNIVERSE, has_raw_data
from core.ml.i1_gate_validator.config import (
    HOLDOUT_FRACTION,
    PERIODS_PER_YEAR_1H,
    get_asset_config,
    signal_kwargs,
)
from core.ml.i1_gate_validator.costs import gross_returns, net_returns, signal_turnover
from core.ml.i1_gate_validator.signal_filters import prepare_signals
from core.ml.i1_strategies import (
    I1_STRATEGY_REGISTRY,
    _ensure_indicators,
    strategies_for_symbol,
)

RAW_1H = Path("data/raw/parquet/1h")
GATE_REPORT = Path("data/reports/i1_gate_report.json")
_GATE_TOL_ABS = 0.20  # holdout Sharpe cross-check tolerance vs the I1 gate report


# ── helpers ──────────────────────────────────────────────────────────────
def _load_gate_report() -> dict[str, dict]:
    if not GATE_REPORT.exists():
        return {}
    data = json.loads(GATE_REPORT.read_text(encoding="utf-8"))
    return {a["symbol"]: a for a in data.get("assets", [])}


def _split_trades(net: pd.Series, sig: pd.Series) -> list[dict]:
    """Group consecutive same-sign bars into trades; pnl = Σ net returns held."""
    sig = sig.reindex(net.index).fillna(0)
    trades: list[dict] = []
    cur_sign = 0
    acc = 0.0
    for r, s in zip(net.to_numpy(), np.sign(sig.to_numpy())):
        if s != cur_sign:
            if cur_sign != 0:
                trades.append({"net_pnl": float(acc)})
            cur_sign, acc = s, 0.0
        if cur_sign != 0:
            acc += float(r)
    if cur_sign != 0:
        trades.append({"net_pnl": float(acc)})
    return trades


def _tail_ratio(net: pd.Series) -> float:
    if len(net) < 20:
        return 0.0
    hi = float(net.quantile(0.95))
    lo = abs(float(net.quantile(0.05)))
    return round(hi / lo, 4) if lo > 1e-12 else 0.0


def _metrics(net: pd.Series, gross: pd.Series, sig: pd.Series) -> dict[str, Any]:
    if net.empty:
        return {"n_bars": 0}
    net_l = net.tolist()
    equity = (1.0 + net).cumprod().tolist()
    s_net = sharpe_ratio(net_l, periods_per_year=PERIODS_PER_YEAR_1H)
    s_gross = sharpe_ratio(gross.tolist(), periods_per_year=PERIODS_PER_YEAR_1H)
    mdd = max_drawdown(equity)
    ann_ret = float(np.mean(net_l)) * PERIODS_PER_YEAR_1H
    trades = _split_trades(net, sig)
    years = max(len(net) / PERIODS_PER_YEAR_1H, 1e-9)
    return {
        "n_bars": len(net),
        "n_trades": len(trades),
        "sharpe_net": round(s_net, 4),
        "sharpe_gross": round(s_gross, 4),
        "sortino_net": round(sortino_ratio(net_l, periods_per_year=PERIODS_PER_YEAR_1H), 4),
        "calmar": round(calmar_ratio(ann_ret, mdd), 4),
        "expectancy": round(expectancy(trades), 6),
        "profit_factor": round(profit_factor(trades), 4) if trades else 0.0,
        "win_rate": round(win_rate(trades), 4),
        "max_drawdown": round(mdd, 4),
        "exposure": round(float((sig.reindex(net.index).fillna(0) != 0).mean()), 4),
        "turnover_per_year": round(signal_turnover(sig) / years, 2),
        "cost_drag": round(s_gross - s_net, 4),
        "tail_ratio": _tail_ratio(net),
        "ann_return": round(ann_ret, 4),
    }


def _evaluate_symbol(symbol: str, gate_row: dict | None) -> dict[str, Any]:
    path = RAW_1H / f"{symbol.lower()}_1h.parquet"
    if not path.exists():
        return {"symbol": symbol, "data_available": False, "strategies": []}

    df = pd.read_parquet(path).sort_index()
    if "close" not in df.columns:
        return {"symbol": symbol, "data_available": False, "error": "no close column",
                "strategies": []}
    df = _ensure_indicators(df)
    returns = df["close"].pct_change().dropna()
    ref_price = float(df["close"].median())
    cost_model = CostModel()

    n = len(df)
    holdout_start = int(n * (1 - HOLDOUT_FRACTION))
    wf_idx = df.index[:holdout_start]
    ho_idx = df.index[holdout_start:]

    asset_cfg = get_asset_config(symbol)
    sig_kw = signal_kwargs(asset_cfg)
    allowed = asset_cfg.get("strategies") or list(strategies_for_symbol(symbol).keys())

    gate_best = (gate_row or {}).get("best_strategy")
    gate_params = (gate_row or {}).get("best_params") or {}
    gate_ho_sharpe = (gate_row or {}).get("sharpe_net_holdout")

    rows: list[dict] = []
    for sid in allowed:
        spec = I1_STRATEGY_REGISTRY.get(sid)
        if spec is None:
            continue
        use_gate_params = sid == gate_best and bool(gate_params)
        params = dict(gate_params) if use_gate_params else dict(spec.defaults)
        if sid == "ml_lgb_v1":
            params["symbol"] = symbol

        sig_full = prepare_signals(df, spec, params, **sig_kw).reindex(returns.index).fillna(0)

        split_metrics: dict[str, Any] = {}
        for split_name, idx in (("wf", wf_idx), ("holdout", ho_idx), ("full", df.index)):
            r = returns.reindex(idx).dropna()
            s = sig_full.reindex(r.index).fillna(0)
            g = gross_returns(r, s)
            nnet = net_returns(r, s, symbol, cost_model, ref_price)
            g = g.reindex(nnet.index).fillna(0)
            split_metrics[split_name] = _metrics(nnet, g, s)

        row = {
            "strategy": sid,
            "params": params,
            "params_source": "i1_gate" if use_gate_params else "defaults",
            **split_metrics,
        }
        if sid == gate_best and gate_ho_sharpe is not None:
            got = split_metrics["holdout"].get("sharpe_net", 0.0)
            row["gate_holdout_sharpe"] = round(float(gate_ho_sharpe), 4)
            row["matches_gate"] = abs(got - float(gate_ho_sharpe)) <= _GATE_TOL_ABS
        rows.append(row)

    return {
        "symbol": symbol,
        "data_available": True,
        "n_bars": n,
        "holdout_fraction": HOLDOUT_FRACTION,
        "gate_best_strategy": gate_best,
        "strategies": rows,
    }


def _markdown(report: dict) -> str:
    lines = [
        f"# Quant Report — {report['generated_at']}",
        "",
        f"Universe: {', '.join(report['universe'])}  ·  periods/year (1h): {PERIODS_PER_YEAR_1H}",
        "",
        "| Symbol | Strategy | src | WF Sharpe | HO Sharpe | HO Sortino | HO Calmar | HO PF | HO WinRate | HO MaxDD | HO Exp | CostDrag | Tail | gate✓ |",
        "|---|---|---|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|:--:|",
    ]
    for a in report["assets"]:
        if not a.get("data_available"):
            lines.append(f"| {a['symbol']} | — | — | _no data_ |  |  |  |  |  |  |  |  |  |  |")
            continue
        for s in a["strategies"]:
            wf, ho = s.get("wf", {}), s.get("holdout", {})
            gate = s.get("matches_gate")
            gmark = "" if gate is None else ("✓" if gate else "✗")
            lines.append(
                f"| {a['symbol']} | {s['strategy']} | {s['params_source'][:4]} "
                f"| {wf.get('sharpe_net', 0):.2f} | {ho.get('sharpe_net', 0):.2f} "
                f"| {ho.get('sortino_net', 0):.2f} | {ho.get('calmar', 0):.2f} "
                f"| {ho.get('profit_factor', 0):.2f} | {ho.get('win_rate', 0):.2f} "
                f"| {ho.get('max_drawdown', 0):.2f} | {ho.get('exposure', 0):.2f} "
                f"| {ho.get('cost_drag', 0):.2f} | {ho.get('tail_ratio', 0):.2f} | {gmark} |"
            )
    lines += ["", "_Generated by scripts/run_quant_report.py — SPEC-C01._"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Consolidated quant report (SPEC-C01)")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--out", default="data/reports")
    args = ap.parse_args()

    symbols = args.symbols or list(TRADED_UNIVERSE)
    gate = _load_gate_report()

    assets = [_evaluate_symbol(s, gate.get(s)) for s in symbols]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "universe": symbols,
        "methodology": {
            "holdout_fraction": HOLDOUT_FRACTION,
            "periods_per_year_1h": PERIODS_PER_YEAR_1H,
            "signal_prep": "prepare_signals (regime filter + min-hold + cooldown)",
            "cost_model": "CostModel per asset_class (same as I1 gate)",
            "gate_cross_check_tol_abs": _GATE_TOL_ABS,
        },
        "assets": assets,
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "quant_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "quant_report.md").write_text(_markdown(report), encoding="utf-8")

    n_data = sum(1 for a in assets if a.get("data_available"))
    mism = [
        (a["symbol"], s["strategy"])
        for a in assets
        for s in a.get("strategies", [])
        if s.get("matches_gate") is False
    ]
    print(
        f"quant_report: {n_data}/{len(assets)} symbols with data -> "
        f"{out}/quant_report.json, {out}/quant_report.md"
    )
    if mism:
        print(f"WARN gate cross-check mismatch (>{_GATE_TOL_ABS} abs Sharpe): {mism}")
    else:
        print("gate cross-check: OK (best-strategy holdout Sharpe within tolerance)")


if __name__ == "__main__":
    main()
