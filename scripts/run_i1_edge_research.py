"""
Script: scripts/run_i1_edge_research.py
Responsibility: I1 gate research — walk-forward + purged CV + holdout reports.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ml.i1_gate_validator import (
    GATE_P_VALUE,
    GATE_SHARPE_NET,
    I1GateValidator,
    PIPELINE_SYMBOLS,
)
from core.observability.logger import configure_logging, get_logger

configure_logging()
logger = get_logger("i1_gate_research")

DATA_DIR = Path(__file__).parent.parent / "data" / "raw"
REPORT_DIR = Path(__file__).parent.parent / "data" / "reports"


def _write_markdown(report_dict: dict, path: Path) -> None:
    lines = [
        "# I1 Gate Report — Sharpe OOS Walk-Forward",
        "",
        f"Generated: {report_dict['generated_at']}",
        "",
        "## Gate criteria",
        f"- `sharpe_net_wf >= {GATE_SHARPE_NET}`",
        f"- `p_value_wf < {GATE_P_VALUE}`",
        "",
        "| Symbol | Strategy | Sharpe gross WF | Sharpe net WF | Cost drag | Turnover | "
        "p-value WF | Trades | PASS |",
        "|--------|----------|-----------------|---------------|-----------|----------|"
        "-----------|--------|------|",
    ]
    for a in report_dict["assets"]:
        status = "PASS" if a["passed"] else "FAIL"
        drag = a.get("cost_drag_wf", a["sharpe_gross_wf"] - a["sharpe_net_wf"])
        turnover = a.get("turnover_wf", 0)
        lines.append(
            f"| {a['symbol']} | {a['best_strategy']} | {a['sharpe_gross_wf']:.3f} | "
            f"{a['sharpe_net_wf']:.3f} | {drag:.3f} | {turnover:.1f} | "
            f"{a['p_value_wf']:.4f} | {a['n_trades_wf']} | {status} |"
        )
    summary = report_dict["summary"]
    gate = "APPROVED" if summary.get("gate_approved") else "BLOCKED"
    lines.extend(
        [
            "",
            f"**GATE FASE 5:** {gate} ({summary['symbols_passed']}/{summary['symbols_tested']})",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_matrix_csv(report_dict: dict, path: Path) -> None:
    fieldnames = [
        "symbol",
        "strategy",
        "sharpe_gross_full",
        "sharpe_net_full",
        "sharpe_gross_wf",
        "sharpe_net_wf",
        "sharpe_gross_holdout",
        "sharpe_net_holdout",
        "p_value_wf",
        "n_trades_wf",
        "cost_drag_wf",
        "turnover_wf",
        "passed",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for a in report_dict["assets"]:
            writer.writerow(
                {
                    "symbol": a["symbol"],
                    "strategy": a["best_strategy"],
                    "sharpe_gross_full": a["sharpe_gross_full"],
                    "sharpe_net_full": a["sharpe_net_full"],
                    "sharpe_gross_wf": a["sharpe_gross_wf"],
                    "sharpe_net_wf": a["sharpe_net_wf"],
                    "sharpe_gross_holdout": a["sharpe_gross_holdout"],
                    "sharpe_net_holdout": a["sharpe_net_holdout"],
                    "p_value_wf": a["p_value_wf"],
                    "n_trades_wf": a["n_trades_wf"],
                    "cost_drag_wf": a.get("cost_drag_wf", 0),
                    "turnover_wf": a.get("turnover_wf", 0),
                    "passed": a["passed"],
                }
            )


def _write_phase5_gate(report_dict: dict, path: Path) -> None:
    summary = report_dict["summary"]
    gate = "APPROVED" if summary.get("gate_approved") else "BLOCKED"
    lines = [
        "# I1 Phase 5 Gate — Official Sign-off",
        "",
        f"Date: {report_dict['generated_at']}",
        "",
        "| Symbol | sharpe_net_wf | p_value | PASS |",
        "|--------|---------------|---------|------|",
    ]
    for a in report_dict["assets"]:
        status = "YES" if a["passed"] else "NO"
        lines.append(
            f"| {a['symbol']} | {a['sharpe_net_wf']:.4f} | {a['p_value_wf']:.4f} | {status} |"
        )
    lines.append("")
    lines.append(
        f"**GATE FASE 5: {gate} ({summary['symbols_passed']}/{summary['symbols_tested']})**"
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="I1 gate walk-forward edge research")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if not all pipeline symbols pass the gate",
    )
    parser.add_argument(
        "--symbols",
        nargs="*",
        default=None,
        help="Override symbol list (default: 8 pipeline symbols)",
    )
    parser.add_argument(
        "--bootstrap",
        type=int,
        default=1000,
        help="Bootstrap iterations for p-value",
    )
    args = parser.parse_args()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    symbols = args.symbols or PIPELINE_SYMBOLS
    validator = I1GateValidator(n_bootstrap=args.bootstrap)
    report = validator.validate_all(DATA_DIR, symbols)
    report_dict = report.to_dict()

    json_path = REPORT_DIR / "i1_gate_report.json"
    json_path.write_text(json.dumps(report_dict, indent=2), encoding="utf-8")
    _write_markdown(report_dict, REPORT_DIR / "i1_gate_report.md")
    _write_matrix_csv(report_dict, REPORT_DIR / "i1_gate_matrix.csv")
    _write_phase5_gate(report_dict, REPORT_DIR / "I1_PHASE5_GATE.md")

    print(f"{'Symbol':<10} {'Strategy':<16} {'Net WF':>8} {'p-val':>8} {'PASS'}")
    print("-" * 50)
    for a in report.assets:
        status = "YES" if a.passed else "NO"
        print(
            f"{a.symbol:<10} {a.best_strategy:<16} {a.sharpe_net_wf:>8.3f} "
            f"{a.p_value_wf:>8.4f} {status}"
        )

    passed = report.summary["symbols_passed"]
    total = report.summary["symbols_tested"]
    print(f"\nGate: {passed}/{total} passed")
    print(f"Reports: {REPORT_DIR}")

    if args.strict and not report.summary.get("gate_approved"):
        logger.error("i1_gate_failed", passed=passed, total=total)
        sys.exit(1)


if __name__ == "__main__":
    main()
