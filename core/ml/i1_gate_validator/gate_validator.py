"""
Module: core/ml/i1_gate_validator/gate_validator.py
Responsibility: Orchestrate walk-forward + purged CV + holdout into a pass/fail gate per asset
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from core.backtesting.costs import CostModel
from core.backtesting.metrics import sharpe_ratio
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
    signal_kwargs,
)
from core.ml.i1_gate_validator.costs import (
    cost_drag,
    count_trades,
    gross_returns,
    net_returns,
    signal_turnover,
)
from core.ml.i1_gate_validator.optimization import optimize_params
from core.ml.i1_gate_validator.report import I1AssetResult, I1GateReport
from core.ml.i1_gate_validator.signal_filters import prepare_signals
from core.ml.i1_gate_validator.statistics import bootstrap_pvalue_wf
from core.ml.i1_gate_validator.walk_forward import evaluate_strategy_wf
from core.ml.i1_strategies import I1_STRATEGY_REGISTRY, _ensure_indicators, strategies_for_symbol


class I1GateValidator:
    """Walk-forward + purged CV gate validator for Phase 5."""

    def __init__(
        self,
        n_bootstrap: int = 1000,
        cooldown_bars: int = 3,
        regime_filter: bool = True,
        cost_model: CostModel | None = None,
        params_dir: Path | None = None,
    ):
        self.n_bootstrap = n_bootstrap
        self.cooldown_bars = cooldown_bars
        self.regime_filter = regime_filter
        self.cost_model = cost_model or CostModel()
        self.params_dir = params_dir or DEFAULT_I1_PARAMS_DIR

    def validate_asset(
        self,
        symbol: str,
        df: pd.DataFrame,
        *,
        strategy_id: str | None = None,
    ) -> I1AssetResult:
        df = df.sort_index()
        if "close" not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")

        df = _ensure_indicators(df)
        returns = df["close"].pct_change().dropna()
        ref_price = float(df["close"].median())

        holdout_start = int(len(df) * (1 - HOLDOUT_FRACTION))
        wf_df = df.iloc[:holdout_start]
        holdout_df = df.iloc[holdout_start:]
        wf_returns = returns.reindex(wf_df.index).dropna()
        holdout_returns = returns.reindex(holdout_df.index).dropna()

        asset_cfg = get_asset_config(symbol)
        sig_kw = signal_kwargs(asset_cfg)

        if strategy_id:
            strategies = {strategy_id: I1_STRATEGY_REGISTRY[strategy_id]}
        else:
            allowed = asset_cfg.get("strategies")
            strategies = strategies_for_symbol(symbol, allowed)

        best_result: I1AssetResult | None = None

        for sid, spec in strategies.items():
            run_params = dict(spec.defaults)
            if sid == "ml_lgb_v1":
                run_params["symbol"] = symbol
            gross_wf, net_wf, wf_windows, wf_params = evaluate_strategy_wf(
                wf_df,
                wf_returns,
                spec,
                symbol,
                self.cost_model,
                ref_price,
                asset_cfg,
                self.params_dir,
            )
            params = optimize_params(
                wf_df,
                wf_returns,
                spec,
                symbol,
                self.cost_model,
                ref_price,
                asset_cfg,
                self.params_dir,
            )
            if wf_params:
                params = wf_params

            if len(net_wf) < 30:
                continue

            eval_params = {**params, "symbol": symbol} if sid == "ml_lgb_v1" else params
            sig_hold = prepare_signals(df, spec, eval_params, **sig_kw)
            sig_h = sig_hold.reindex(holdout_df.index).fillna(0)
            gross_h = gross_returns(holdout_returns, sig_h)
            net_h = net_returns(
                holdout_returns, sig_h, symbol, self.cost_model, ref_price
            )

            sig_full = prepare_signals(df, spec, eval_params, **sig_kw)
            sig_full = sig_full.reindex(returns.index).fillna(0)
            gross_full = gross_returns(returns, sig_full)
            net_full = net_returns(returns, sig_full, symbol, self.cost_model, ref_price)

            p_val = bootstrap_pvalue_wf(net_wf, self.n_bootstrap)
            sharpe_gross_wf = sharpe_ratio(
                gross_wf.tolist(), periods_per_year=PERIODS_PER_YEAR_1H
            )
            sharpe_net_wf = sharpe_ratio(
                net_wf.tolist(), periods_per_year=PERIODS_PER_YEAR_1H
            )
            sig_wf = sig_full.reindex(wf_df.index).fillna(0)
            n_trades = count_trades(sig_wf)
            turnover = signal_turnover(sig_wf)
            drag = cost_drag(sharpe_gross_wf, sharpe_net_wf)

            sharpe_net_holdout = (
                sharpe_ratio(net_h.tolist(), periods_per_year=PERIODS_PER_YEAR_1H)
                if len(net_h) > 1
                else 0.0
            )

            passed = (
                sharpe_net_wf >= GATE_SHARPE_NET
                and p_val < GATE_P_VALUE
                and sharpe_net_holdout >= GATE_SHARPE_HOLDOUT
            )
            diagnosis = ""
            if not passed:
                if sharpe_net_wf < GATE_SHARPE_NET:
                    diagnosis = f"sharpe_net_wf={sharpe_net_wf:.3f}<{GATE_SHARPE_NET}"
                if p_val >= GATE_P_VALUE:
                    diagnosis += f"; p_value={p_val:.3f}>={GATE_P_VALUE}"
                if sharpe_net_holdout < GATE_SHARPE_HOLDOUT:
                    diagnosis += (
                        f"; sharpe_net_holdout={sharpe_net_holdout:.3f}<{GATE_SHARPE_HOLDOUT}"
                    )

            candidate = I1AssetResult(
                symbol=symbol,
                best_strategy=sid,
                best_params=params,
                sharpe_gross_full=round(
                    sharpe_ratio(gross_full.tolist(), periods_per_year=PERIODS_PER_YEAR_1H),
                    4,
                ),
                sharpe_net_full=round(
                    sharpe_ratio(net_full.tolist(), periods_per_year=PERIODS_PER_YEAR_1H),
                    4,
                ),
                sharpe_gross_wf=round(sharpe_gross_wf, 4),
                sharpe_net_wf=round(sharpe_net_wf, 4),
                p_value_wf=round(p_val, 4),
                wf_windows=wf_windows,
                sharpe_gross_holdout=round(
                    sharpe_ratio(gross_h.tolist(), periods_per_year=PERIODS_PER_YEAR_1H),
                    4,
                )
                if len(gross_h) > 1
                else 0.0,
                sharpe_net_holdout=round(sharpe_net_holdout, 4),
                n_trades_wf=n_trades,
                cost_drag_wf=drag,
                turnover_wf=round(turnover, 2),
                passed=passed,
                diagnosis=diagnosis.strip("; "),
            )

            if best_result is None or candidate.sharpe_net_wf > best_result.sharpe_net_wf:
                best_result = candidate

        if best_result is None:
            return I1AssetResult(
                symbol=symbol,
                best_strategy="none",
                best_params={},
                sharpe_gross_full=0.0,
                sharpe_net_full=0.0,
                sharpe_gross_wf=0.0,
                sharpe_net_wf=0.0,
                p_value_wf=1.0,
                sharpe_gross_holdout=0.0,
                sharpe_net_holdout=0.0,
                passed=False,
                diagnosis="insufficient_wf_windows",
            )
        return best_result

    def validate_all(
        self,
        data_dir: Path,
        symbols: list[str] | None = None,
    ) -> I1GateReport:
        from datetime import datetime, timezone

        symbols = symbols or PIPELINE_SYMBOLS
        assets: list[I1AssetResult] = []

        for symbol in symbols:
            path = data_dir / f"{symbol}_1h.parquet"
            if not path.exists():
                alt = data_dir / "parquet" / "1h" / f"{symbol.lower()}_1h.parquet"
                path = alt if alt.exists() else path
            if not path.exists():
                assets.append(
                    I1AssetResult(
                        symbol=symbol,
                        best_strategy="none",
                        best_params={},
                        sharpe_gross_full=0.0,
                        sharpe_net_full=0.0,
                        sharpe_gross_wf=0.0,
                        sharpe_net_wf=0.0,
                        p_value_wf=1.0,
                        sharpe_gross_holdout=0.0,
                        sharpe_net_holdout=0.0,
                        passed=False,
                        diagnosis="no_data",
                    )
                )
                continue
            df = pd.read_parquet(path)
            assets.append(self.validate_asset(symbol, df))

        passed_count = sum(1 for a in assets if a.passed)
        return I1GateReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            methodology={
                "walk_forward_fraction": 1 - HOLDOUT_FRACTION,
                "holdout_fraction": HOLDOUT_FRACTION,
                "purged_kfold": {"n_splits": 5, "embargo_bars": 5},
                "wf_windows": "adaptive by series length",
                "signal_lag": "1 bar",
                "cost_model": "CostModel per asset_class",
                "cooldown_bars": self.cooldown_bars,
                "regime_filter": "ADX>=20",
                "asset_overrides": list(I1_ASSET_OVERRIDES.keys()),
                "params_dir": str(self.params_dir),
                "bootstrap": self.n_bootstrap,
                "gate": (
                    f"sharpe_net_wf>={GATE_SHARPE_NET} AND p_value_wf<{GATE_P_VALUE} "
                    f"AND sharpe_net_holdout>={GATE_SHARPE_HOLDOUT}"
                ),
                "strategies": list(I1_STRATEGY_REGISTRY.keys()),
            },
            assets=assets,
            summary={
                "symbols_tested": len(assets),
                "symbols_passed": passed_count,
                "gate_approved": passed_count == len(symbols),
                "fraction_passed": passed_count / len(symbols) if symbols else 0.0,
            },
        )
