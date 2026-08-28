"""
Module: core/ml/i1_gate_validator/report.py
Responsibility: Result/report dataclasses for the I1 gate
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class I1AssetResult:
    symbol: str
    best_strategy: str
    best_params: dict[str, Any]
    sharpe_gross_full: float
    sharpe_net_full: float
    sharpe_gross_wf: float
    sharpe_net_wf: float
    p_value_wf: float
    sharpe_gross_holdout: float
    sharpe_net_holdout: float
    wf_windows: list[dict[str, Any]] = field(default_factory=list)
    n_trades_wf: int = 0
    cost_drag_wf: float = 0.0
    turnover_wf: float = 0.0
    passed: bool = False
    diagnosis: str = ""


@dataclass
class I1GateReport:
    generated_at: str
    methodology: dict[str, Any]
    assets: list[I1AssetResult]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "methodology": self.methodology,
            "assets": [asdict(a) for a in self.assets],
            "summary": self.summary,
        }
