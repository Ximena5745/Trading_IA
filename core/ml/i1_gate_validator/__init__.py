"""
Package: core/ml/i1_gate_validator
Responsibility: I1 Phase-5 gate — walk-forward OOS + purged k-fold param search + holdout 20%.

Antes un único archivo de 730 líneas con 6+ responsabilidades mezcladas
(auditoría técnica 2026-07-25, hallazgo de calidad SRP): ventaneo WF,
costos/PnL, filtros de señal, estadística (bootstrap p-value), optimización
(grid/purged-CV + Optuna), y orquestación/reportes. Dividido en submódulos:
  - config.py: constantes del gate, thresholds, overrides por activo
  - params_io.py: persistencia de parámetros optimizados (JSON)
  - windows.py: tamaño de ventanas walk-forward adaptado a la longitud de la serie
  - costs.py: P&L neto/bruto por costos de transacción (gross/net returns, turnover)
  - signal_filters.py: post-procesado de señales (min-hold, cooldown, filtro de régimen)
  - statistics.py: bootstrap p-value sobre retornos OOS
  - optimization.py: búsqueda de parámetros (purged CV, grid, Optuna)
  - walk_forward.py: evaluación walk-forward de una estrategia
  - report.py: I1AssetResult / I1GateReport
  - gate_validator.py: I1GateValidator (orquestación: WF + holdout + veredicto)

El import path público `core.ml.i1_gate_validator` no cambia.
"""
from core.ml.i1_gate_validator.config import (
    DEFAULT_I1_PARAMS_DIR,
    GATE_P_VALUE,
    GATE_SHARPE_HOLDOUT,
    GATE_SHARPE_NET,
    HOLDOUT_FRACTION,
    I1_ASSET_OVERRIDES,
    PERIODS_PER_YEAR_1H,
    PIPELINE_SYMBOLS,
    get_asset_config,
)
from core.ml.i1_gate_validator.costs import (
    cost_drag,
    count_trades,
    gross_returns,
    half_side_cost_pct,
    net_returns,
    signal_turnover,
)
from core.ml.i1_gate_validator.gate_validator import I1GateValidator
from core.ml.i1_gate_validator.optimization import (
    optimize_params,
    optimize_params_optuna,
    purged_cv_score,
)
from core.ml.i1_gate_validator.params_io import load_saved_params, save_params
from core.ml.i1_gate_validator.report import I1AssetResult, I1GateReport
from core.ml.i1_gate_validator.signal_filters import (
    apply_cooldown,
    apply_min_holding,
    apply_regime_filter,
    prepare_signals,
)
from core.ml.i1_gate_validator.statistics import bootstrap_pvalue_wf
from core.ml.i1_gate_validator.walk_forward import evaluate_strategy_wf

__all__ = [
    "PERIODS_PER_YEAR_1H",
    "GATE_SHARPE_NET",
    "GATE_P_VALUE",
    "GATE_SHARPE_HOLDOUT",
    "HOLDOUT_FRACTION",
    "PIPELINE_SYMBOLS",
    "DEFAULT_I1_PARAMS_DIR",
    "I1_ASSET_OVERRIDES",
    "get_asset_config",
    "load_saved_params",
    "save_params",
    "I1AssetResult",
    "I1GateReport",
    "apply_min_holding",
    "apply_cooldown",
    "apply_regime_filter",
    "prepare_signals",
    "gross_returns",
    "net_returns",
    "count_trades",
    "signal_turnover",
    "cost_drag",
    "half_side_cost_pct",
    "bootstrap_pvalue_wf",
    "purged_cv_score",
    "optimize_params",
    "optimize_params_optuna",
    "evaluate_strategy_wf",
    "I1GateValidator",
]
