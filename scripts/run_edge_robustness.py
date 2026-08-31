"""
Script: scripts/run_edge_robustness.py  (SPEC-C02 / Fase 2, entregable 2.6)

Robustez del edge, por activo que pase el gate I1 (archivo aprobado en
data/models/i1_params/<SYMBOL>.json). Cuatro análisis:

  1. Monte Carlo block-bootstrap (1000 paths) sobre los retornos netos holdout
     -> intervalo de confianza del Sharpe anualizado. Criterio (gate F2-b):
     límite inferior del CI 95 % > 0.

  2. Barrido de costos ×1..×3 -> Sharpe neto por factor y factor de anulación
     (primer múltiplo con Sharpe neto ≤ 0 y con Sharpe neto < GATE_SHARPE_NET).
     Criterio: sobrevive a ×2 (Sharpe neto > 0 en factor 2.0).

  3. Descomposición por régimen: ADX alto/bajo (vs min_adx del activo) y
     volatilidad alta/baja (ATR% vs mediana de muestra). Sharpe neto por bucket.
     Criterio: no depende de un único régimen (≥ 2 buckets con Sharpe > 0 y
     ningún bucket concentra > 85 % del P&L con el resto negativo).

  4. Walk-forward anclado con re-optimización trimestral: ventana de train
     expansiva; cada ~trimestre (2160 barras 1h) se re-elige el mejor punto de
     la grilla por Sharpe neto in-sample y se aplica OOS al trimestre siguiente.
     Criterio: Sharpe neto OOS concatenado > 0 y ≥ 50 % de folds positivos.

Veredicto: EDGE_ROBUST si los 4 criterios pasan; si no, FRAGILE + motivos.

Salidas:
  data/reports/edge_robustness.json
  data/reports/edge_robustness.md

Usage:
  python scripts/run_edge_robustness.py [--symbols XAUUSD] [--paths 1000]
                                        [--block 24] [--seed 42] [--out data/reports]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.backtesting.costs import CostModel
from core.backtesting.metrics import max_drawdown, sharpe_ratio
from core.config.constants import TRADED_UNIVERSE
from core.ml.i1_gate_validator.config import (
    GATE_SHARPE_NET,
    HOLDOUT_FRACTION,
    PERIODS_PER_YEAR_1H,
    get_asset_config,
    signal_kwargs,
)
from core.ml.i1_gate_validator.costs import (
    gross_returns,
    half_side_cost_pct,
    net_returns,
    signal_turnover,
)
from core.ml.i1_gate_validator.signal_filters import prepare_signals
from core.ml.i1_strategies import (
    I1_STRATEGY_REGISTRY,
    _ensure_indicators,
    iter_param_combinations,
)
from core.strategies.approved_params import approved_symbols, load_approved_strategy

RAW_1H = Path("data/raw/parquet/1h")
_COST_FACTORS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0]
_QUARTER_BARS = 90 * 24          # ~1 trimestre de barras 1h
_MIN_TRAIN_BARS = 2 * _QUARTER_BARS
_PNL_CONCENTRATION_LIMIT = 0.85
_TF = "1h"

# timeframe -> (periods_per_year, quarter_bars, default MC block).
# Rama 2 sweeps 4h / 1d with the same battery; main() rebinds the globals below.
_TF_PROFILES: dict[str, tuple[int, int, int]] = {
    "1h": (PERIODS_PER_YEAR_1H, 90 * 24, 24),
    "4h": (252 * 6, 90 * 6, 12),
    "1d": (252, 63, 5),
}


# ── helpers ──────────────────────────────────────────────────────────────
def _sharpe(series: pd.Series | list[float]) -> float:
    vals = series.tolist() if isinstance(series, pd.Series) else list(series)
    return sharpe_ratio(vals, periods_per_year=PERIODS_PER_YEAR_1H)


def _net_with_cost_mult(
    r: pd.Series, s: pd.Series, symbol: str, cost_model: CostModel,
    ref_price: float, mult: float,
) -> pd.Series:
    gross = gross_returns(r, s)
    if gross.empty:
        return gross
    sig = s.reindex(gross.index).fillna(0)
    unit_cost = half_side_cost_pct(symbol, cost_model, ref_price) * mult
    intensity = sig.diff().abs().fillna(0)
    return gross - intensity * unit_cost


def _block_bootstrap_sharpe(
    net: np.ndarray, n_paths: int, block: int, seed: int,
) -> dict[str, Any]:
    n = len(net)
    if n < max(3 * block, 60):
        return {"status": "insufficient_data", "n_bars": int(n)}
    rng = np.random.default_rng(seed)
    n_blocks = math.ceil(n / block)
    max_start = n - block
    sharpes = np.empty(n_paths, dtype=float)
    for i in range(n_paths):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        path = np.concatenate([net[st : st + block] for st in starts])[:n]
        sharpes[i] = sharpe_ratio(path.tolist(), periods_per_year=PERIODS_PER_YEAR_1H)
    pct = {p: float(np.percentile(sharpes, p)) for p in (2.5, 5, 25, 50, 75, 95, 97.5)}
    ci_lower = round(pct[2.5], 4)
    return {
        "status": "ok",
        "n_paths": n_paths,
        "block_bars": block,
        "n_bars": int(n),
        "point_sharpe": round(sharpe_ratio(net.tolist(), periods_per_year=PERIODS_PER_YEAR_1H), 4),
        "mean": round(float(sharpes.mean()), 4),
        "std": round(float(sharpes.std(ddof=1)), 4),
        "percentiles": {str(k): round(v, 4) for k, v in pct.items()},
        "ci95_lower": ci_lower,
        "ci95_upper": round(pct[97.5], 4),
        "prob_positive": round(float((sharpes > 0).mean()), 4),
        "pass": ci_lower > 0.0,
    }


def _cost_sweep(
    r: pd.Series, s: pd.Series, symbol: str, cost_model: CostModel, ref_price: float,
) -> dict[str, Any]:
    rows = []
    null_zero = None
    null_gate = None
    for f in _COST_FACTORS:
        net = _net_with_cost_mult(r, s, symbol, cost_model, ref_price, f)
        sn = round(_sharpe(net), 4)
        rows.append({"factor": f, "sharpe_net": sn, "total_return": round(float(net.sum()), 6)})
        if null_zero is None and sn <= 0.0:
            null_zero = f
        if null_gate is None and sn < GATE_SHARPE_NET:
            null_gate = f
    s_x2 = next(row["sharpe_net"] for row in rows if row["factor"] == 2.0)
    return {
        "by_factor": rows,
        "nullification_factor_zero": null_zero,
        "nullification_factor_gate": null_gate,
        "sharpe_net_x2": s_x2,
        "pass": s_x2 > 0.0,
    }


def _regime_decomposition(
    df: pd.DataFrame, r: pd.Series, s: pd.Series, symbol: str,
    cost_model: CostModel, ref_price: float, min_adx: float,
) -> dict[str, Any]:
    net_all = net_returns(r, s, symbol, cost_model, ref_price)
    idx = net_all.index
    adx = df["adx_14"].reindex(idx) if "adx_14" in df.columns else pd.Series(np.nan, index=idx)
    if "atr_14" in df.columns:
        atr_pct = (df["atr_14"] / df["close"]).reindex(idx)
    else:
        atr_pct = r.abs().rolling(24).mean().reindex(idx)
    vol_median = float(atr_pct.median())

    buckets = {
        "adx_high": adx >= min_adx,
        "adx_low": adx < min_adx,
        "vol_high": atr_pct >= vol_median,
        "vol_low": atr_pct < vol_median,
    }
    total_pnl = float(net_all.sum())
    out: dict[str, Any] = {"vol_median_atr_pct": round(vol_median, 6), "buckets": {}}
    positive = 0
    concentrated = False
    for name, mask in buckets.items():
        m = mask.fillna(False)
        seg = net_all[m]
        pnl = float(seg.sum())
        share = round(pnl / total_pnl, 4) if abs(total_pnl) > 1e-12 else 0.0
        sn = round(_sharpe(seg), 4)
        out["buckets"][name] = {
            "n_bars": int(m.sum()),
            "sharpe_net": sn,
            "total_return": round(pnl, 6),
            "pnl_share": share,
        }
        if not name.startswith("vol_"):  # count ADX buckets for the "not one regime" test
            if sn > 0:
                positive += 1
        if share > _PNL_CONCENTRATION_LIMIT:
            others_negative = any(
                float(net_all[buckets[o].fillna(False)].sum()) < 0
                for o in buckets
                if o != name and o.split("_")[0] == name.split("_")[0]
            )
            concentrated = concentrated or others_negative
    vol_positive = sum(
        1 for b in ("vol_high", "vol_low") if out["buckets"][b]["sharpe_net"] > 0
    )
    single_regime_dependent = (positive < 2) or (vol_positive < 2) or concentrated
    out["adx_buckets_positive"] = positive
    out["vol_buckets_positive"] = vol_positive
    out["single_regime_dependent"] = single_regime_dependent
    out["pass"] = not single_regime_dependent
    return out


def _anchored_walk_forward(
    df: pd.DataFrame, returns: pd.Series, spec, sig_kw: dict[str, Any],
    symbol: str, cost_model: CostModel, ref_price: float,
) -> dict[str, Any]:
    combos = iter_param_combinations(spec)
    # precompute the signal series for every grid point once (lookahead-free fns)
    sig_by_combo = {
        json.dumps(c, sort_keys=True): prepare_signals(df, spec, c, **sig_kw)
        .reindex(returns.index)
        .fillna(0)
        for c in combos
    }
    n = len(returns)
    if n < _MIN_TRAIN_BARS + _QUARTER_BARS:
        return {"status": "insufficient_data", "n_bars": int(n)}

    folds = []
    oos_chunks: list[pd.Series] = []
    anchor = _MIN_TRAIN_BARS
    while anchor + _QUARTER_BARS <= n:
        train_idx = returns.index[:anchor]
        test_idx = returns.index[anchor : anchor + _QUARTER_BARS]
        best_key, best_sharpe = None, -1e9
        for key, sig in sig_by_combo.items():
            tr = returns.reindex(train_idx).dropna()
            ts = sig.reindex(tr.index).fillna(0)
            sn = _sharpe(net_returns(tr, ts, symbol, cost_model, ref_price))
            if sn > best_sharpe:
                best_key, best_sharpe = key, sn
        sig = sig_by_combo[best_key]
        te = returns.reindex(test_idx).dropna()
        tsig = sig.reindex(te.index).fillna(0)
        oos_net = net_returns(te, tsig, symbol, cost_model, ref_price)
        oos_chunks.append(oos_net)
        folds.append(
            {
                "fold": len(folds) + 1,
                "train_bars": int(anchor),
                "test_bars": int(len(test_idx)),
                "best_params": json.loads(best_key),
                "in_sample_sharpe_net": round(best_sharpe, 4),
                "oos_sharpe_net": round(_sharpe(oos_net), 4),
                "oos_return": round(float(oos_net.sum()), 6),
            }
        )
        anchor += _QUARTER_BARS

    oos_all = pd.concat(oos_chunks) if oos_chunks else pd.Series(dtype=float)
    oos_sharpe = round(_sharpe(oos_all), 4)
    n_pos = sum(1 for f in folds if f["oos_sharpe_net"] > 0)
    equity = (1.0 + oos_all).cumprod().tolist()
    return {
        "status": "ok",
        "quarter_bars": _QUARTER_BARS,
        "min_train_bars": _MIN_TRAIN_BARS,
        "n_folds": len(folds),
        "folds_positive": n_pos,
        "oos_sharpe_net": oos_sharpe,
        "oos_total_return": round(float(oos_all.sum()), 6),
        "oos_max_drawdown": round(max_drawdown(equity), 4),
        "folds": folds,
        "pass": oos_sharpe > 0.0 and n_pos >= math.ceil(len(folds) / 2),
    }


def _evaluate_symbol(
    symbol: str,
    n_paths: int,
    block: int,
    seed: int,
    strategy_override: str | None = None,
    params_override: dict[str, Any] | None = None,
    data_file: str | None = None,
) -> dict[str, Any]:
    """Run the 2.6 battery.

    Default: use the I1-approved (strategy, params) for `symbol`.
    Exploratory (Rama 1): pass `strategy_override` (+ optional `params_override`)
    to stress a non-approved candidate — e.g. XAUUSD/tsmom_v1. The approved
    Sharpe is still reported as a reference when it matches the same strategy.
    `data_file` overrides the 1h parquet path while keeping `symbol`'s cost model
    and asset config — e.g. re-test XAUUSD on an extended history parquet.
    """
    approved = load_approved_strategy(symbol)
    strategy_id = strategy_override or (approved.strategy_id if approved else None)
    if strategy_id is None:
        return {"symbol": symbol, "status": "no_approved_strategy"}
    path = Path(data_file) if data_file else RAW_1H / f"{symbol.lower()}_{_TF}.parquet"
    if not path.exists():
        return {"symbol": symbol, "status": "no_data", "strategy_id": strategy_id}

    df = pd.read_parquet(path).sort_index()
    df = _ensure_indicators(df)
    returns = df["close"].pct_change().dropna()
    ref_price = float(df["close"].median())
    cost_model = CostModel()

    spec = I1_STRATEGY_REGISTRY.get(strategy_id)
    if spec is None:
        return {"symbol": symbol, "status": "unknown_strategy",
                "strategy_id": strategy_id}

    asset_cfg = get_asset_config(symbol)
    sig_kw = signal_kwargs(asset_cfg)
    min_adx = float(asset_cfg.get("min_adx", 20.0))
    if params_override:
        params = dict(params_override)
    elif approved and approved.strategy_id == strategy_id:
        params = dict(approved.params)
    else:
        params = dict(getattr(spec, "defaults", {}) or {})
    approved_ref = (
        approved.sharpe_net_holdout
        if approved and approved.strategy_id == strategy_id
        else None
    )

    sig_full = prepare_signals(df, spec, params, **sig_kw).reindex(returns.index).fillna(0)

    n = len(df)
    holdout_start = int(n * (1 - HOLDOUT_FRACTION))
    ho_idx = df.index[holdout_start:]
    ho_r = returns.reindex(ho_idx).dropna()
    ho_s = sig_full.reindex(ho_r.index).fillna(0)
    ho_net = net_returns(ho_r, ho_s, symbol, cost_model, ref_price)

    mc = _block_bootstrap_sharpe(ho_net.to_numpy(dtype=float), n_paths, block, seed)
    # secondary, non-gating: full-sample bootstrap (more data -> tighter CI)
    full_r = returns
    full_s = sig_full.reindex(full_r.index).fillna(0)
    full_net = net_returns(full_r, full_s, symbol, cost_model, ref_price)
    mc_full = _block_bootstrap_sharpe(
        full_net.to_numpy(dtype=float), n_paths, block, seed
    )
    sweep = _cost_sweep(ho_r, ho_s, symbol, cost_model, ref_price)
    regime = _regime_decomposition(
        df, returns, sig_full, symbol, cost_model, ref_price, min_adx
    )
    wf = _anchored_walk_forward(
        df, returns, spec, sig_kw, symbol, cost_model, ref_price
    )

    checks = {
        "monte_carlo_ci_lower_gt_0": bool(mc.get("pass", False)),
        "survives_cost_x2": bool(sweep.get("pass", False)),
        "not_single_regime": bool(regime.get("pass", False)),
        "anchored_wf_positive": bool(wf.get("pass", False)),
    }
    verdict = "EDGE_ROBUST" if all(checks.values()) else "FRAGILE"
    reasons = [k for k, v in checks.items() if not v]

    return {
        "symbol": symbol,
        "status": "ok",
        "strategy_id": strategy_id,
        "params": params,
        "is_approved_strategy": bool(approved and approved.strategy_id == strategy_id),
        "sharpe_net_holdout_approved": approved_ref,
        "recomputed_holdout_sharpe_net": round(_sharpe(ho_net), 4),
        "holdout_bars": int(len(ho_net)),
        "holdout_turnover": round(signal_turnover(ho_s), 4),
        "holdout_cost_drag": round(_sharpe(gross_returns(ho_r, ho_s)) - _sharpe(ho_net), 4),
        "verdict": verdict,
        "failed_checks": reasons,
        "checks": checks,
        "monte_carlo": mc,
        "monte_carlo_full_sample": mc_full,
        "cost_sweep": sweep,
        "regime_decomposition": regime,
        "anchored_walk_forward": wf,
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Edge Robustness — {report['generated_at']}",
        "",
        f"Gate F2-(b) criteria · timeframe: {report['params'].get('timeframe', '1h')} · "
        f"periods/year: {PERIODS_PER_YEAR_1H} · "
        f"paths: {report['params']['paths']} · block: {report['params']['block']} bars",
        "",
    ]
    for a in report["assets"]:
        if a.get("status") != "ok":
            lines += [f"## {a['symbol']} — _{a.get('status')}_", ""]
            continue
        mc, mcf, sw, rg, wf = (
            a["monte_carlo"], a["monte_carlo_full_sample"], a["cost_sweep"],
            a["regime_decomposition"], a["anchored_walk_forward"],
        )
        lines += [
            f"## {a['symbol']} — {a['strategy_id']} {a['params']} — **{a['verdict']}**",
            "",
            f"- Holdout Sharpe neto (recalculado): **{a['recomputed_holdout_sharpe_net']}** "
            f"(aprobado: {a['sharpe_net_holdout_approved']}) · "
            f"holdout bars = {a['holdout_bars']} · turnover = {a['holdout_turnover']} · "
            f"cost drag = {a['holdout_cost_drag']}",
            f"- **Monte Carlo (holdout)** {mc.get('n_paths', '-')} paths: "
            f"CI95 = [{mc.get('ci95_lower', '-')}, {mc.get('ci95_upper', '-')}], "
            f"P(Sharpe>0) = {mc.get('prob_positive', '-')} -> "
            f"{'PASS' if mc.get('pass') else 'FAIL'}",
            f"- Monte Carlo (full sample, contexto): "
            f"CI95 = [{mcf.get('ci95_lower', '-')}, {mcf.get('ci95_upper', '-')}], "
            f"P(Sharpe>0) = {mcf.get('prob_positive', '-')}",
            f"- **Cost sweep**: Sharpe neto ×2 = {sw.get('sharpe_net_x2', '-')}; "
            f"anulación (≤0) en ×{sw.get('nullification_factor_zero')}; "
            f"< gate {GATE_SHARPE_NET} en ×{sw.get('nullification_factor_gate')} -> "
            f"{'PASS' if sw.get('pass') else 'FAIL'}",
            f"- **Regime**: ADX+ buckets = {rg.get('adx_buckets_positive')}/2, "
            f"vol+ buckets = {rg.get('vol_buckets_positive')}/2, "
            f"single-regime = {rg.get('single_regime_dependent')} -> "
            f"{'PASS' if rg.get('pass') else 'FAIL'}",
            f"- **Anchored WF**: {wf.get('n_folds', '-')} folds, "
            f"{wf.get('folds_positive', '-')} positivos, "
            f"OOS Sharpe neto = {wf.get('oos_sharpe_net', '-')} -> "
            f"{'PASS' if wf.get('pass') else 'FAIL'}",
            "",
            "| Cost × | Sharpe net |",
            "|--:|--:|",
        ]
        for row in sw["by_factor"]:
            lines.append(f"| {row['factor']} | {row['sharpe_net']} |")
        lines.append("")
        if wf.get("status") == "ok":
            lines += ["| Fold | train bars | best params | IS Sharpe | OOS Sharpe |",
                      "|--:|--:|---|--:|--:|"]
            for f in wf["folds"]:
                lines.append(
                    f"| {f['fold']} | {f['train_bars']} | {f['best_params']} "
                    f"| {f['in_sample_sharpe_net']} | {f['oos_sharpe_net']} |"
                )
            lines.append("")
    lines += ["_Generated by scripts/run_edge_robustness.py — SPEC-C02._"]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Edge robustness battery (SPEC-C02)")
    ap.add_argument("--symbols", nargs="*", default=None,
                    help="default: symbols with an approved I1 params file")
    ap.add_argument("--strategy", default=None,
                    help="Rama 1 exploratory: stress this strategy_id instead of "
                         "the I1-approved one (applies to every --symbols entry)")
    ap.add_argument("--params", default=None,
                    help="JSON dict of params for --strategy (default: spec.defaults)")
    ap.add_argument("--data-file", default=None,
                    help="override the 1h parquet path (keeps the symbol's cost "
                         "model / asset config); use with a single --symbols entry")
    ap.add_argument("--timeframe", choices=list(_TF_PROFILES), default="1h",
                    help="Rama 2: run the battery at 4h / 1d (reads "
                         "data/raw/parquet/<tf>/<sym>_<tf>.parquet)")
    ap.add_argument("--paths", type=int, default=1000)
    ap.add_argument("--block", type=int, default=None,
                    help="MC block size in bars (default: per-timeframe)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/reports")
    ap.add_argument("--out-name", default="edge_robustness",
                    help="basename for the .json/.md outputs (use a distinct name "
                         "for exploratory runs so the canonical report is kept)")
    args = ap.parse_args()

    # rebind timeframe-coupled globals (single-run script, no concurrency)
    global PERIODS_PER_YEAR_1H, _QUARTER_BARS, _MIN_TRAIN_BARS, _TF, RAW_1H
    ppy, qbars, def_block = _TF_PROFILES[args.timeframe]
    PERIODS_PER_YEAR_1H = ppy
    _QUARTER_BARS = qbars
    _MIN_TRAIN_BARS = 2 * qbars
    _TF = args.timeframe
    RAW_1H = Path(f"data/raw/parquet/{args.timeframe}")
    if args.block is None:
        args.block = def_block

    params_override = json.loads(args.params) if args.params else None

    symbols = args.symbols or sorted(approved_symbols())
    if not symbols:
        print("no approved symbols (data/models/i1_params/<SYMBOL>.json) — nothing to do")
        sys.exit(0)
    if not args.strategy and not args.symbols:
        symbols = [s for s in symbols if s in set(TRADED_UNIVERSE)]

    assets = [
        _evaluate_symbol(s, args.paths, args.block, args.seed,
                         strategy_override=args.strategy,
                         params_override=params_override,
                         data_file=args.data_file)
        for s in symbols
    ]
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "params": {"timeframe": args.timeframe, "periods_per_year": PERIODS_PER_YEAR_1H,
                   "paths": args.paths, "block": args.block, "seed": args.seed,
                   "cost_factors": _COST_FACTORS, "quarter_bars": _QUARTER_BARS,
                   "strategy_override": args.strategy,
                   "params_override": params_override},
        "methodology": {
            "monte_carlo": "block bootstrap of holdout net returns; annualized Sharpe per path",
            "cost_sweep": "half-side unit cost × factor; net = gross - trade_intensity·unit·factor",
            "regime": "ADX vs min_adx; ATR% vs sample median; net Sharpe per bucket",
            "anchored_wf": "expanding train, quarterly grid re-optimization by in-sample net Sharpe",
            "pass_criteria": {
                "monte_carlo": "CI95 lower bound > 0",
                "cost_sweep": "net Sharpe > 0 at cost ×2",
                "regime": ">=2 ADX & >=2 vol buckets positive; no >85% pnl concentration with others negative",
                "anchored_wf": "concatenated OOS net Sharpe > 0 and >=50% folds positive",
            },
        },
        "assets": assets,
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{args.out_name}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / f"{args.out_name}.md").write_text(_markdown(report), encoding="utf-8")

    for a in assets:
        if a.get("status") == "ok":
            print(
                f"{a['symbol']:9s} {a['strategy_id']:14s} -> {a['verdict']}"
                + (f"  (fail: {', '.join(a['failed_checks'])})" if a["failed_checks"] else "")
            )
        else:
            print(f"{a['symbol']:9s} -> {a.get('status')}")
    print(f"  {out}/{args.out_name}.json, {out}/{args.out_name}.md")


if __name__ == "__main__":
    main()
