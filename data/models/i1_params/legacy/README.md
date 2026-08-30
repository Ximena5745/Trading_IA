# Legacy i1_params (pre-holdout-criterion)

These `<symbol>_<strategy>.json` files predate the F1.4 canonical contract
(ADR-003) and the holdout-inclusive I1 gate criterion. They are **not**
gate-approved: the current `data/reports/i1_gate_report.json` passes only XAUUSD.

Kept for reference only. The pipeline ignores this directory — it loads
`data/models/i1_params/<SYMBOL>.json` and nothing else. Do not restore a file
here to `../` without re-running the I1 gate.
