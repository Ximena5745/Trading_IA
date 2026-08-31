"""
Script: scripts/check_reproducibility.py  (Fase 2, entregable 2.2)

Prueba de reproducibilidad del core de decisión.

H2.2 exige que dos corridas del pipeline sobre el mismo conjunto de datos
produzcan exactamente el mismo output (señales, órdenes, snapshots). El stack
completo (Redis + Postgres + testnet) se valida en 2.1/2.3; aquí se verifica la
parte que es ejecutable de forma aislada y que concentra el no-determinismo
peligroso: la **cadena de decisión cuantitativa** (indicadores -> señal cruda ->
filtros de régimen/min-hold/cooldown -> P&L neto -> métricas).

Dos partes:

  1. Digest determinista. Para cada (activo, estrategia) se calcula un digest
     SHA-256 canónico de la serie de señales redondeada + métricas clave. Se
     repite el cálculo en dos pasadas independientes (lecturas frescas del
     parquet) y se comparan byte a byte.

  2. Escaneo de fuentes de no-determinismo. Se rastrean los módulos de la ruta
     de decisión en busca de `uuid4`, `datetime.now/utcnow`, `time.time`, y uso
     de RNG sin semilla. Cada hallazgo se clasifica como:
       - metadata  : afecta solo a identificadores/timestamps, no a la decisión
       - decision  : puede alterar la señal/orden -> debe estar mitigado (semilla)

Salidas:
  data/reports/reproducibility_report.json
  data/reports/reproducibility_report.md

Exit code:
  0  -> los digests de las dos pasadas coinciden y no hay no-determinismo
        de decisión sin mitigar
  1  -> divergencia entre pasadas, o RNG de decisión sin semilla

Usage:
  python scripts/check_reproducibility.py [--symbols XAUUSD ...] [--out data/reports]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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

REPO = Path(__file__).parent.parent
RAW_1H = Path("data/raw/parquet/1h")

# Modules on the decision path — kept in sync with the F1 audit scope.
_DECISION_MODULES = [
    "scripts/run_pipeline.py",
    "core/signals",
    "core/consensus",
    "core/strategies",
    "core/risk/risk_manager.py",
    "core/ml/i1_strategies.py",
    "core/ml/i1_gate_validator",
    "core/adaptation/hmm_regime_detector.py",
]

_METADATA_PATTERNS = {
    "uuid4": re.compile(r"\buuid4\s*\("),
    "uuid1": re.compile(r"\buuid1\s*\("),
    "datetime_now": re.compile(r"datetime\.now\s*\(|datetime\.utcnow\s*\("),
    "timestamp_now": re.compile(r"Timestamp\.now\s*\(|pd\.Timestamp\.now"),
    "time_time": re.compile(r"\btime\.time\s*\(|time\.monotonic\s*\("),
}
_RNG_PATTERN = re.compile(
    r"np\.random\.(?!default_rng|seed|Generator)"
    r"|numpy\.random\.(?!default_rng|seed|Generator)"
    r"|(?<![\w.])random\.(random|choice|shuffle|sample|randint|uniform|gauss)\s*\("
)
_SEED_PATTERN = re.compile(r"np\.random\.seed\s*\(|default_rng\s*\(|random_state\s*=|\.seed\s*\(")


# ── digest ───────────────────────────────────────────────────────────────
def _series_sha(sig: pd.Series) -> str:
    arr = np.round(sig.to_numpy(dtype=float), 8)
    return hashlib.sha256(arr.tobytes()).hexdigest()


def _decision_digest(symbol: str) -> dict[str, Any]:
    """Recompute the quant decision chain for `symbol` from scratch."""
    path = RAW_1H / f"{symbol.lower()}_1h.parquet"
    if not path.exists():
        return {"symbol": symbol, "data_available": False, "strategies": {}}

    df = pd.read_parquet(path).sort_index()
    if "close" not in df.columns:
        return {"symbol": symbol, "data_available": False, "strategies": {}}
    df = _ensure_indicators(df)
    returns = df["close"].pct_change().dropna()
    ref_price = float(df["close"].median())
    cost_model = CostModel()

    n = len(df)
    holdout_start = int(n * (1 - HOLDOUT_FRACTION))
    ho_idx = df.index[holdout_start:]

    asset_cfg = get_asset_config(symbol)
    sig_kw = signal_kwargs(asset_cfg)
    allowed = asset_cfg.get("strategies") or list(strategies_for_symbol(symbol).keys())

    out: dict[str, Any] = {}
    for sid in sorted(allowed):
        spec = I1_STRATEGY_REGISTRY.get(sid)
        if spec is None:
            continue
        params = dict(spec.defaults)
        if sid == "ml_lgb_v1":
            params["symbol"] = symbol
        sig = prepare_signals(df, spec, params, **sig_kw).reindex(returns.index).fillna(0)

        ho_r = returns.reindex(ho_idx).dropna()
        ho_s = sig.reindex(ho_r.index).fillna(0)
        ho_net = net_returns(ho_r, ho_s, symbol, cost_model, ref_price)
        ho_gross = gross_returns(ho_r, ho_s).reindex(ho_net.index).fillna(0)
        equity = (1.0 + ho_net).cumprod().tolist()

        out[sid] = {
            "signal_sha256": _series_sha(sig),
            "last_action": int(np.sign(sig.iloc[-1])) if len(sig) else 0,
            "n_bars": int(len(sig)),
            "nonzero_bars": int((sig != 0).sum()),
            "turnover": round(signal_turnover(sig), 10),
            "holdout_sharpe_net": round(
                sharpe_ratio(ho_net.tolist(), periods_per_year=PERIODS_PER_YEAR_1H), 10
            ),
            "holdout_sharpe_gross": round(
                sharpe_ratio(ho_gross.tolist(), periods_per_year=PERIODS_PER_YEAR_1H), 10
            ),
            "holdout_max_dd": round(max_drawdown(equity), 10),
            "holdout_total_return": round(float(ho_net.sum()), 10),
        }
    return {"symbol": symbol, "data_available": True, "n_bars": n, "strategies": out}


def _digest_sha(digest: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(digest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


# ── non-determinism scan ─────────────────────────────────────────────────
def _iter_py_files() -> list[Path]:
    files: list[Path] = []
    for entry in _DECISION_MODULES:
        p = REPO / entry
        if p.is_file():
            files.append(p)
        elif p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
    return files


def _scan_nondeterminism() -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for f in _iter_py_files():
        try:
            text = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(REPO).as_posix()
        lines = text.splitlines()
        file_has_seed = bool(_SEED_PATTERN.search(text))
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            for name, pat in _METADATA_PATTERNS.items():
                if pat.search(line):
                    findings.append(
                        {
                            "file": rel,
                            "line": i,
                            "kind": name,
                            "severity": "metadata",
                            "mitigated": True,
                            "code": stripped[:120],
                        }
                    )
            if _RNG_PATTERN.search(line):
                findings.append(
                    {
                        "file": rel,
                        "line": i,
                        "kind": "rng_call",
                        "severity": "decision",
                        "mitigated": file_has_seed,
                        "code": stripped[:120],
                    }
                )
    return findings


# ── report ───────────────────────────────────────────────────────────────
def _markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# Reproducibility Report — {report['generated_at']}",
        "",
        f"Verdict: **{report['verdict']}**",
        "",
        "## 1. Digest determinista (2 pasadas)",
        "",
        "| Symbol | Strategies | Pass 1 digest | Pass 2 digest | Match |",
        "|---|--:|---|---|:--:|",
    ]
    for r in report["digest_check"]["per_symbol"]:
        lines.append(
            f"| {r['symbol']} | {r['n_strategies']} | `{r['sha_pass1'][:16]}` "
            f"| `{r['sha_pass2'][:16]}` | {'✓' if r['match'] else '✗'} |"
        )
    lines += [
        "",
        f"Combined pass-1 SHA: `{report['digest_check']['combined_sha_pass1']}`",
        "",
        f"Combined pass-2 SHA: `{report['digest_check']['combined_sha_pass2']}`",
        "",
        "## 2. Fuentes de no-determinismo (ruta de decisión)",
        "",
        "| File | Line | Kind | Severity | Mitigated | Code |",
        "|---|--:|---|---|:--:|---|",
    ]
    for f in report["nondeterminism_scan"]["findings"]:
        lines.append(
            f"| {f['file']} | {f['line']} | {f['kind']} | {f['severity']} "
            f"| {'✓' if f['mitigated'] else '✗'} | `{f['code']}` |"
        )
    lines += [
        "",
        "**Clasificación.** `metadata` = afecta solo a `correlation_id`/timestamps "
        "(no altera la decisión). `decision` = uso de RNG; debe estar sembrado "
        "(`mitigated = ✓`).",
        "",
        f"- metadata: {report['nondeterminism_scan']['n_metadata']}",
        f"- decision sin mitigar: {report['nondeterminism_scan']['n_decision_unmitigated']}",
        "",
        "_Generated by scripts/check_reproducibility.py — F2.2._",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Reproducibility check (F2.2)")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--out", default="data/reports")
    args = ap.parse_args()

    symbols = args.symbols or list(TRADED_UNIVERSE)

    pass1 = [_decision_digest(s) for s in symbols]
    pass2 = [_decision_digest(s) for s in symbols]

    per_symbol = []
    all_match = True
    for d1, d2 in zip(pass1, pass2):
        s1, s2 = _digest_sha(d1), _digest_sha(d2)
        match = s1 == s2
        all_match &= match
        per_symbol.append(
            {
                "symbol": d1["symbol"],
                "data_available": d1["data_available"],
                "n_strategies": len(d1.get("strategies", {})),
                "sha_pass1": s1,
                "sha_pass2": s2,
                "match": match,
            }
        )

    combined1 = hashlib.sha256(
        "".join(_digest_sha(d) for d in pass1).encode()
    ).hexdigest()
    combined2 = hashlib.sha256(
        "".join(_digest_sha(d) for d in pass2).encode()
    ).hexdigest()

    findings = _scan_nondeterminism()
    n_meta = sum(1 for f in findings if f["severity"] == "metadata")
    n_dec_unmit = sum(
        1 for f in findings if f["severity"] == "decision" and not f["mitigated"]
    )

    deterministic = all_match and combined1 == combined2
    verdict = "REPRODUCIBLE" if deterministic and n_dec_unmit == 0 else "NON-DETERMINISTIC"

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "scope": "quant decision chain (indicators -> signal -> filters -> net P&L -> metrics)",
        "note": (
            "Full-stack pipeline equivalence (Redis/DB/testnet order & snapshot "
            "persistence) is validated in F2.1/F2.3 with the running stack."
        ),
        "digest_check": {
            "deterministic": deterministic,
            "combined_sha_pass1": combined1,
            "combined_sha_pass2": combined2,
            "per_symbol": per_symbol,
            "pass1_digests": pass1,
        },
        "nondeterminism_scan": {
            "modules": _DECISION_MODULES,
            "n_metadata": n_meta,
            "n_decision_unmitigated": n_dec_unmit,
            "findings": findings,
        },
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "reproducibility_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    (out / "reproducibility_report.md").write_text(_markdown(report), encoding="utf-8")

    n_data = sum(1 for r in per_symbol if r["data_available"])
    print(
        f"reproducibility: {n_data}/{len(per_symbol)} symbols with data | "
        f"digests {'MATCH' if deterministic else 'DIFFER'} | "
        f"decision RNG unmitigated: {n_dec_unmit} -> verdict {verdict}"
    )
    print(f"  {out}/reproducibility_report.json, {out}/reproducibility_report.md")
    sys.exit(0 if verdict == "REPRODUCIBLE" else 1)


if __name__ == "__main__":
    main()
