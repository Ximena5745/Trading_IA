"""
Script: scripts/i1_iterate_failed.py
Responsibility: Batch Optuna optimization for symbols that failed I1 gate (Phase C).
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ml.i1_gate_validator import PIPELINE_SYMBOLS

# symbol -> list of (strategy_id,) to optimize
ROUND1_JOBS: list[tuple[str, str]] = [
    ("EURUSD", "mean_rev_v1"),
    ("EURUSD", "BB_ZScore"),
    ("BTCUSDT", "tsmom_v1"),
    ("BTCUSDT", "vol_breakout_v1"),
    ("ETHUSDT", "tsmom_v1"),
    ("ETHUSDT", "vol_breakout_v1"),
]

ROUND2_JOBS: list[tuple[str, str]] = [
    ("US500", "vol_breakout_v1"),
    ("US500", "tsmom_v1"),
    ("US30", "vol_breakout_v1"),
    ("US30", "tsmom_v1"),
]

ROUNDS = {
    "1": ROUND1_JOBS,
    "2": ROUND2_JOBS,
    "all": ROUND1_JOBS + ROUND2_JOBS,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch I1 Optuna for failed assets")
    parser.add_argument(
        "--round",
        choices=["1", "2", "all"],
        default="all",
        help="Optimization round (1=EUR+crypto, 2=indices)",
    )
    parser.add_argument("--n-trials", type=int, default=50)
    parser.add_argument(
        "--run-gate",
        action="store_true",
        help="Run full gate report after optimization",
    )
    parser.add_argument("--bootstrap", type=int, default=1000)
    parser.add_argument(
        "--train-ml-failed",
        action="store_true",
        help="After gate, train ML models for symbols still failing",
    )
    args = parser.parse_args()

    root = Path(__file__).parent.parent
    optimize_script = root / "scripts" / "i1_optimize_strategy.py"
    jobs = ROUNDS[args.round]

    for symbol, strategy in jobs:
        cmd = [
            sys.executable,
            str(optimize_script),
            "--symbol",
            symbol,
            "--strategy",
            strategy,
            "--optuna",
            "--n-trials",
            str(args.n_trials),
        ]
        print(f"\n>>> {' '.join(cmd)}")
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"WARNING: optimization failed for {symbol}/{strategy} (rc={rc})")

    if args.run_gate:
        gate_cmd = [
            sys.executable,
            str(root / "scripts" / "run_i1_edge_research.py"),
            "--bootstrap",
            str(args.bootstrap),
        ]
        print(f"\n>>> {' '.join(gate_cmd)}")
        subprocess.call(gate_cmd)

        if args.train_ml_failed:
            import json

            report_path = root / "data" / "reports" / "i1_gate_report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                failed = [
                    a["symbol"]
                    for a in report.get("assets", [])
                    if not a.get("passed")
                ]
                train_script = root / "scripts" / "i1_train_ml_symbol.py"
                for sym in failed:
                    cmd = [sys.executable, str(train_script), "--symbol", sym]
                    print(f"\n>>> ML train: {' '.join(cmd)}")
                    subprocess.call(cmd)
                print(f"\n>>> Re-run gate after ML training")
                subprocess.call(gate_cmd)


if __name__ == "__main__":
    main()
