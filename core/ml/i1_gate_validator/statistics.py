"""
Module: core/ml/i1_gate_validator/statistics.py
Responsibility: Significance testing for walk-forward net returns (sign-flip bootstrap)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from core.backtesting.metrics import sharpe_ratio
from core.ml.i1_gate_validator.config import PERIODS_PER_YEAR_1H


def bootstrap_pvalue_wf(
    oos_net: pd.Series,
    n_bootstrap: int = 1000,
    periods_per_year: int = PERIODS_PER_YEAR_1H,
) -> float:
    if len(oos_net) < 30:
        return 1.0
    observed = sharpe_ratio(oos_net.tolist(), periods_per_year=periods_per_year)
    rng = np.random.default_rng(42)
    arr = oos_net.values
    random_sharpes: list[float] = []
    for _ in range(n_bootstrap):
        signs = rng.choice([-1.0, 0.0, 1.0], size=len(arr), p=[0.25, 0.5, 0.25])
        shuffled = arr * signs
        random_sharpes.append(
            sharpe_ratio(shuffled.tolist(), periods_per_year=periods_per_year)
        )
    return float((np.array(random_sharpes) >= observed).mean())
