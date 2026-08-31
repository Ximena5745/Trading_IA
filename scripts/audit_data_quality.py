"""
Script: scripts/audit_data_quality.py  (Fase 2, entregable 2.4 — saneamiento)

Auditoría de higiene del histórico 1h del universo. Verifica lo que el plan pide
para los datos ("timestamps UTC, gaps/outliers marcados") sobre los parquet que
ya existen en data/raw/parquet/1h/. NO descarga datos nuevos.

Chequeos por archivo:
  - timestamp tz-aware en UTC, monotónico creciente, sin duplicados
  - integridad OHLC: high >= low, high >= max(open,close), low <= min(open,close),
    precios > 0, sin NaN en OHLCV
  - cadencia: delta modal entre barras; huecos > 2× la mediana, separando los de
    fin de semana (viernes->lunes) de los intradía
  - outliers de retorno: |log-return| por barra sobre umbral por clase de activo
    y |z-score| > 10 sobre ventana móvil de 500

Salidas:
  data/reports/data_quality_report.json
  data/reports/data_quality_report.md

Exit code:
  0  -> sin violaciones duras (OHLC / tz / orden / duplicados)
  1  -> alguna violación dura en algún archivo

Usage:
  python scripts/audit_data_quality.py [--dir data/raw/parquet/1h] [--out data/reports]
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

from core.models import detect_asset_class

RAW_1H = Path("data/raw/parquet/1h")
_OHLCV = ["open", "high", "low", "close", "volume"]
# per-bar |log return| considered implausible for a 1h bar, keyed by AssetClass.name
_RET_LIMIT = {"CRYPTO": 0.20, "FOREX": 0.10, "INDICES": 0.12, "COMMODITIES": 0.12}
_RET_LIMIT_DEFAULT = 0.12
_Z_LIMIT = 10.0
_Z_WINDOW = 500


def _symbol_from_path(p: Path) -> str:
    return p.stem.replace("_1h", "").upper()


def _ret_limit(symbol: str) -> float:
    try:
        return _RET_LIMIT.get(detect_asset_class(symbol).name, _RET_LIMIT_DEFAULT)
    except Exception:
        return _RET_LIMIT_DEFAULT


def _check_ohlc(df: pd.DataFrame) -> dict[str, Any]:
    issues: dict[str, int] = {}
    o, h, l, c, v = (df[k] for k in _OHLCV)
    issues["high_lt_low"] = int((h < l).sum())
    issues["high_lt_open_or_close"] = int((h < o).sum() + (h < c).sum())
    issues["low_gt_open_or_close"] = int((l > o).sum() + (l > c).sum())
    issues["nonpositive_price"] = int((df[["open", "high", "low", "close"]] <= 0).any(axis=1).sum())
    issues["negative_volume"] = int((v < 0).sum())
    issues["nan_ohlcv"] = int(df[_OHLCV].isna().any(axis=1).sum())
    total = sum(issues.values())
    return {"violations": issues, "total": total}


def _check_cadence(ts: pd.Series) -> dict[str, Any]:
    deltas = ts.diff().dropna()
    if deltas.empty:
        return {"status": "empty"}
    secs = deltas.dt.total_seconds()
    modal = float(secs.mode().iloc[0])
    median = float(secs.median())
    big = deltas[secs > 2 * median]
    # weekend gap: previous bar on Friday, next on Monday
    prev_dow = ts.shift(1).dt.dayofweek
    is_weekend_gap = (secs > 2 * median) & (prev_dow == 4)
    intraday_gaps = int(((secs > 2 * median) & ~is_weekend_gap.fillna(False)).sum())
    return {
        "modal_delta_seconds": modal,
        "median_delta_seconds": median,
        "n_gaps_over_2x_median": int(len(big)),
        "n_weekend_gaps": int(is_weekend_gap.fillna(False).sum()),
        "n_intraday_gaps": intraday_gaps,
        "max_gap_hours": round(float(secs.max()) / 3600, 2),
    }


def _check_outliers(close: pd.Series, symbol: str) -> dict[str, Any]:
    logret = np.log(close / close.shift(1)).dropna()
    limit = _ret_limit(symbol)
    over_limit = logret[logret.abs() > limit]
    roll_mean = logret.rolling(_Z_WINDOW, min_periods=50).mean()
    roll_std = logret.rolling(_Z_WINDOW, min_periods=50).std()
    z = ((logret - roll_mean) / roll_std.replace(0, np.nan)).abs()
    over_z = z[z > _Z_LIMIT]
    return {
        "abs_logret_limit": limit,
        "n_bars_over_limit": int(len(over_limit)),
        "max_abs_logret": round(float(logret.abs().max()), 5),
        "n_bars_z_gt_10": int(over_z.notna().sum()),
    }


def _audit_file(path: Path) -> dict[str, Any]:
    symbol = _symbol_from_path(path)
    df = pd.read_parquet(path)
    out: dict[str, Any] = {"symbol": symbol, "file": path.name, "rows": int(len(df))}

    if "timestamp" not in df.columns:
        out["hard_violation"] = True
        out["error"] = "no timestamp column"
        return out

    ts = df["timestamp"]
    tz_aware_utc = getattr(ts.dt, "tz", None) is not None and str(ts.dt.tz) == "UTC"
    monotonic = bool(ts.is_monotonic_increasing)
    n_dups = int(ts.duplicated().sum())

    ohlc = _check_ohlc(df) if set(_OHLCV).issubset(df.columns) else {"total": 0, "violations": {"missing_columns": 1}}
    cadence = _check_cadence(ts)
    outliers = _check_outliers(df["close"], symbol) if "close" in df.columns else {}

    hard = (not tz_aware_utc) or (not monotonic) or (n_dups > 0) or (ohlc["total"] > 0)
    out.update(
        {
            "date_start": ts.iloc[0].isoformat(),
            "date_end": ts.iloc[-1].isoformat(),
            "span_days": round((ts.iloc[-1] - ts.iloc[0]).total_seconds() / 86400, 1),
            "timestamp_tz_aware_utc": tz_aware_utc,
            "timestamp_monotonic": monotonic,
            "duplicate_timestamps": n_dups,
            "ohlc_integrity": ohlc,
            "cadence": cadence,
            "return_outliers": outliers,
            "hard_violation": hard,
        }
    )
    return out


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Data Quality — 1h universe — {report['generated_at']}",
        "",
        f"Dir: `{report['dir']}` · files: {len(report['files'])} · "
        f"hard violations: **{report['n_hard_violations']}**",
        "",
        "| Symbol | Rows | Span (d) | UTC | Mono | Dups | OHLC bad | Intraday gaps | Wknd gaps | Max gap (h) | Ret>lim | z>10 |",
        "|---|--:|--:|:--:|:--:|--:|--:|--:|--:|--:|--:|--:|",
    ]
    for f in report["files"]:
        if f.get("error"):
            lines.append(f"| {f['symbol']} | {f['rows']} | — | ✗ | | | | | | | | |")
            continue
        c, o = f["cadence"], f["return_outliers"]
        lines.append(
            f"| {f['symbol']} | {f['rows']} | {f['span_days']:.0f} "
            f"| {'✓' if f['timestamp_tz_aware_utc'] else '✗'} "
            f"| {'✓' if f['timestamp_monotonic'] else '✗'} | {f['duplicate_timestamps']} "
            f"| {f['ohlc_integrity']['total']} "
            f"| {c.get('n_intraday_gaps', '-')} | {c.get('n_weekend_gaps', '-')} "
            f"| {c.get('max_gap_hours', '-')} "
            f"| {o.get('n_bars_over_limit', '-')} | {o.get('n_bars_z_gt_10', '-')} |"
        )
    lines += [
        "",
        "**Duras** (fallan el exit code): timestamp no-UTC, no monotónico, "
        "duplicados, o violación de integridad OHLC.",
        "**Blandas** (informativas): huecos intradía y de fin de semana, "
        "outliers de retorno — se marcan, no se corrigen aquí.",
        "",
        "_Generated by scripts/audit_data_quality.py — F2.4._",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="1h data hygiene audit (F2.4)")
    ap.add_argument("--dir", default=str(RAW_1H))
    ap.add_argument("--out", default="data/reports")
    args = ap.parse_args()

    d = Path(args.dir)
    files = sorted(d.glob("*_1h.parquet"))
    audits = [_audit_file(p) for p in files]
    n_hard = sum(1 for a in audits if a.get("hard_violation"))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dir": str(d),
        "n_files": len(files),
        "n_hard_violations": n_hard,
        "return_limits_by_class": _RET_LIMIT,
        "files": audits,
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "data_quality_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / "data_quality_report.md").write_text(_markdown(report), encoding="utf-8")

    for a in audits:
        tag = "HARD-VIOLATION" if a.get("hard_violation") else "ok"
        print(f"{a['symbol']:9s} rows={a['rows']:<6} -> {tag}")
    print(f"  {out}/data_quality_report.json, {out}/data_quality_report.md")
    sys.exit(1 if n_hard else 0)


if __name__ == "__main__":
    main()
