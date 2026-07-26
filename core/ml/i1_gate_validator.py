"""
Module: core/ml/i1_gate_validator.py
Responsibility: I1 Phase-5 gate — walk-forward OOS + purged k-fold param search + holdout 20%.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from core.backtesting.costs import CostModel
from core.backtesting.metrics import sharpe_ratio
from core.ml.i1_strategies import (
    I1_STRATEGY_REGISTRY,
    I1StrategySpec,
    _ensure_indicators,
    iter_param_combinations,
    strategies_for_symbol,
)
from core.ml.validation import PurgedKFold
from core.models import AssetClass, detect_asset_class, get_instrument

PERIODS_PER_YEAR_1H = 252 * 24
GATE_SHARPE_NET = 0.8
GATE_P_VALUE = 0.05
GATE_SHARPE_HOLDOUT = 0.8
HOLDOUT_FRACTION = 0.2

PIPELINE_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "US500",
    "US30",
    "XAUUSD",
]

DEFAULT_I1_PARAMS_DIR = Path("data/models/i1_params")

_DEFAULT_ASSET_CFG: dict[str, Any] = {
    "cooldown": 3,
    "min_hold_bars": 0,
    "min_adx": 20.0,
    "strategies": None,
}

I1_ASSET_OVERRIDES: dict[str, dict[str, Any]] = {
    "BTCUSDT": {
        "cooldown": 6,
        "min_hold_bars": 4,
        "min_adx": 22.0,
        "strategies": ["tsmom_v1", "vol_breakout_v1", "Momentum"],
    },
    "ETHUSDT": {
        "cooldown": 6,
        "min_hold_bars": 4,
        "min_adx": 22.0,
        "strategies": ["tsmom_v1", "vol_breakout_v1", "Momentum"],
    },
    "EURUSD": {
        "cooldown": 4,
        "min_hold_bars": 2,
        "min_adx": 18.0,
        "strategies": ["mean_rev_v1", "ema_rsi_v1", "BB_ZScore"],
    },
    "US500": {
        "cooldown": 5,
        "min_hold_bars": 3,
        "min_adx": 20.0,
        "strategies": ["vol_breakout_v1", "tsmom_v1"],
    },
    "US30": {
        "cooldown": 12,
        "min_hold_bars": 8,
        "min_adx": 24.0,
        "strategies": ["vol_breakout_v1", "tsmom_v1", "BB_ZScore", "mean_rev_v1"],
    },
}


def get_asset_config(symbol: str) -> dict[str, Any]:
    cfg = dict(_DEFAULT_ASSET_CFG)
    cfg.update(I1_ASSET_OVERRIDES.get(symbol.upper(), {}))
    return cfg


def load_saved_params(
    symbol: str,
    strategy_id: str,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    base = base_dir or DEFAULT_I1_PARAMS_DIR
    path = base / f"{symbol.upper()}_{strategy_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return dict(data.get("params", {}))
    except (json.JSONDecodeError, OSError):
        return None


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


def _wf_params(n_bars: int) -> tuple[int, int, int]:
    """Return (train_window, test_window, step) adapted to series length."""
    if n_bars >= 12000:
        return 252 * 24 * 2, 30 * 24, 7 * 24
    if n_bars >= 8000:
        return 252 * 24, 60 * 24, 30 * 24
    # ~5k bars (indices): shorter windows per I1 plan
    train = min(252 * 24, int(n_bars * 0.55))
    test = min(60 * 24, max(int(n_bars * 0.10), 120))
    step = max(test // 2, 30 * 12)
    if train + test > n_bars:
        train = int(n_bars * 0.5)
        test = int(n_bars * 0.15)
        step = max(test // 2, 60)
    return max(train, 400), max(test, 100), max(step, 50)


def _iter_wf_windows(n_bars: int) -> list[dict[str, int]]:
    train_w, test_w, step = _wf_params(n_bars)
    windows: list[dict[str, int]] = []
    i = 0
    while i + train_w + test_w <= n_bars:
        windows.append(
            {
                "train_start": i,
                "train_end": i + train_w,
                "test_start": i + train_w,
                "test_end": i + train_w + test_w,
            }
        )
        i += step
    return windows


def half_side_cost_pct(symbol: str, cost_model: CostModel, ref_price: float = 1.0) -> float:
    """Cost of one side (half round-trip) as fraction of notional."""
    asset_class = detect_asset_class(symbol)
    if asset_class == AssetClass.CRYPTO:
        return cost_model.commission_pct + cost_model.slippage_pct

    inst = get_instrument(symbol)
    if inst is None:
        return 0.0005

    spread_dollars = inst.spread_pips * inst.pip_value * 1.0
    notional = max(inst.lot_size * ref_price, 1.0)
    return spread_dollars / notional


def apply_min_holding(signals: pd.Series, min_bars: int = 0) -> pd.Series:
    """Enforce minimum bars in each non-zero position before allowing exit/flip."""
    if min_bars <= 0:
        return signals
    arr = signals.fillna(0).astype(float).values.copy()
    current = 0.0
    bars_in_position = 0
    for i in range(len(arr)):
        desired = float(arr[i])
        if desired == current:
            if current != 0:
                bars_in_position += 1
            continue
        if current == 0:
            current = desired
            bars_in_position = 1
        elif bars_in_position >= min_bars:
            current = desired
            bars_in_position = 1 if desired != 0 else 0
        arr[i] = current
    return pd.Series(arr, index=signals.index)


def apply_cooldown(signals: pd.Series, cooldown_bars: int = 3) -> pd.Series:
    arr = signals.fillna(0).astype(float).values.copy()
    current = 0.0
    last_change = -cooldown_bars - 1
    for i in range(len(arr)):
        desired = float(arr[i])
        if desired != current:
            if i - last_change >= cooldown_bars:
                current = desired
                last_change = i
        arr[i] = current
    return pd.Series(arr, index=signals.index)


def apply_regime_filter(signals: pd.Series, df: pd.DataFrame, min_adx: float = 20.0) -> pd.Series:
    df = _ensure_indicators(df)
    if "adx_14" not in df.columns:
        return signals
    tradable = df["adx_14"] >= min_adx
    return signals.where(tradable.reindex(signals.index).fillna(False), 0)


def prepare_signals(
    df: pd.DataFrame,
    spec: I1StrategySpec,
    params: dict[str, Any],
    *,
    cooldown: int = 3,
    min_hold_bars: int = 0,
    min_adx: float = 20.0,
    regime_filter: bool = True,
    raw_override: pd.Series | None = None,
) -> pd.Series:
    if raw_override is not None:
        raw = raw_override
    else:
        merged = {**spec.defaults, **params}
        raw = spec.signal_fn(df, merged)
    if regime_filter:
        raw = apply_regime_filter(raw, df, min_adx=min_adx)
    if min_hold_bars > 0:
        raw = apply_min_holding(raw, min_hold_bars)
    if cooldown > 0:
        raw = apply_cooldown(raw, cooldown)
    return raw.fillna(0)


def gross_returns(returns: pd.Series, signals: pd.Series) -> pd.Series:
    aligned = returns.align(signals.shift(1), join="inner")
    return (aligned[0] * aligned[1]).dropna()


def net_returns(
    returns: pd.Series,
    signals: pd.Series,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
) -> pd.Series:
    gross = gross_returns(returns, signals)
    if gross.empty:
        return gross
    sig = signals.reindex(gross.index).fillna(0)
    unit_cost = half_side_cost_pct(symbol, cost_model, ref_price)
    trade_intensity = sig.diff().abs().fillna(0)
    costs = trade_intensity * unit_cost
    return gross - costs


def count_trades(signals: pd.Series) -> int:
    return int((signals.diff().abs().fillna(0) > 0).sum())


def signal_turnover(signals: pd.Series) -> float:
    return float(signals.diff().abs().fillna(0).sum())


def cost_drag(sharpe_gross: float, sharpe_net: float) -> float:
    return round(sharpe_gross - sharpe_net, 4)


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


def _signal_kwargs(asset_cfg: dict[str, Any]) -> dict[str, Any]:
    return {
        "cooldown": int(asset_cfg.get("cooldown", 3)),
        "min_hold_bars": int(asset_cfg.get("min_hold_bars", 0)),
        "min_adx": float(asset_cfg.get("min_adx", 20.0)),
    }


def purged_cv_score(
    train_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    params: dict[str, Any],
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
) -> float:
    asset_cfg = asset_cfg or get_asset_config(symbol)
    sig_kw = _signal_kwargs(asset_cfg)
    pkf = PurgedKFold(n_splits=5, embargo_bars=5)
    scores: list[float] = []
    n = len(train_df)
    if n < 500:
        return -999.0

    for train_idx, test_idx in pkf.split(np.arange(n)):
        test_df = train_df.iloc[test_idx]
        hist_df = train_df.iloc[: test_idx[-1] + 1]
        sig = prepare_signals(hist_df, spec, params, **sig_kw)
        sig_test = sig.reindex(test_df.index).fillna(0)
        ret = returns.reindex(test_df.index).dropna()
        net = net_returns(ret, sig_test, symbol, cost_model, ref_price)
        if len(net) < 20:
            continue
        scores.append(sharpe_ratio(net.tolist(), periods_per_year=PERIODS_PER_YEAR_1H))
    return float(np.mean(scores)) if scores else -999.0


def optimize_params(
    train_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
    params_dir: Path | None = None,
) -> dict[str, Any]:
    asset_cfg = asset_cfg or get_asset_config(symbol)
    if spec.strategy_id == "ml_lgb_v1":
        p = dict(spec.defaults)
        p["symbol"] = symbol
        return p

    best_params = dict(spec.defaults)
    best_score = -999.0

    saved = load_saved_params(symbol, spec.strategy_id, params_dir)
    candidates: list[dict[str, Any]] = list(iter_param_combinations(spec))
    if saved:
        candidates.insert(0, saved)

    seen: set[str] = set()
    for params in candidates:
        key = json.dumps(params, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        score = purged_cv_score(
            train_df, returns, spec, params, symbol, cost_model, ref_price, asset_cfg
        )
        if score > best_score:
            best_score = score
            best_params = params
    return best_params


def evaluate_strategy_wf(
    wf_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
    params_dir: Path | None = None,
) -> tuple[pd.Series, pd.Series, list[dict[str, Any]], dict[str, Any]]:
    asset_cfg = asset_cfg or get_asset_config(symbol)
    sig_kw = _signal_kwargs(asset_cfg)
    windows = _iter_wf_windows(len(wf_df))
    oos_gross_parts: list[pd.Series] = []
    oos_net_parts: list[pd.Series] = []
    window_meta: list[dict[str, Any]] = []
    last_params: dict[str, Any] = dict(spec.defaults)

    for w in windows:
        train_df = wf_df.iloc[w["train_start"] : w["train_end"]]
        test_df = wf_df.iloc[w["test_start"] : w["test_end"]]
        train_ret = returns.reindex(train_df.index)
        hist = wf_df.iloc[: w["test_end"]]

        if spec.strategy_id == "ml_lgb_v1":
            # Genuine walk-forward: retrain per window on train_df only (never
            # on test_df) instead of reusing one model fit on the whole WF
            # slice — otherwise every WF test window is in-sample for the model.
            from core.ml.i1_ml_signal import fit_model_in_memory, predict_signals_from_bundle

            forward_bars = int(spec.defaults.get("forward_bars", 6))
            bundle = fit_model_in_memory(train_df, forward_bars=forward_bars)
            last_params = {"symbol": symbol, "forward_bars": forward_bars}
            if bundle is None:
                continue
            raw_sig = predict_signals_from_bundle(hist, bundle)
            sig = prepare_signals(hist, spec, last_params, **sig_kw, raw_override=raw_sig)
        else:
            last_params = optimize_params(
                train_df,
                train_ret,
                spec,
                symbol,
                cost_model,
                ref_price,
                asset_cfg,
                params_dir,
            )
            sig = prepare_signals(hist, spec, last_params, **sig_kw)

        sig_test = sig.reindex(test_df.index).fillna(0)
        ret_test = returns.reindex(test_df.index).dropna()

        g = gross_returns(ret_test, sig_test)
        n = net_returns(ret_test, sig_test, symbol, cost_model, ref_price)
        oos_gross_parts.append(g)
        oos_net_parts.append(n)
        window_meta.append(
            {
                **w,
                "params": dict(last_params),
                "sharpe_net": sharpe_ratio(n.tolist(), periods_per_year=PERIODS_PER_YEAR_1H),
            }
        )

    if not oos_net_parts:
        return pd.Series(dtype=float), pd.Series(dtype=float), window_meta, last_params

    gross_concat = pd.concat(oos_gross_parts)
    net_concat = pd.concat(oos_net_parts)
    return gross_concat, net_concat, window_meta, last_params


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
        sig_kw = _signal_kwargs(asset_cfg)

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


def optimize_params_optuna(
    train_df: pd.DataFrame,
    returns: pd.Series,
    spec: I1StrategySpec,
    symbol: str,
    cost_model: CostModel,
    ref_price: float,
    asset_cfg: dict[str, Any] | None = None,
    n_trials: int = 50,
) -> dict[str, Any]:
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    asset_cfg = asset_cfg or get_asset_config(symbol)

    def objective(trial: optuna.Trial) -> float:
        params: dict[str, Any] = {}
        for key, values in spec.param_grid.items():
            if not values:
                continue
            if all(isinstance(v, bool) for v in values):
                params[key] = trial.suggest_categorical(key, values)
            elif all(isinstance(v, int) for v in values) and not isinstance(values[0], bool):
                params[key] = trial.suggest_int(key, int(min(values)), int(max(values)))
            elif all(isinstance(v, (int, float)) for v in values):
                lo, hi = float(min(values)), float(max(values))
                if lo == hi:
                    params[key] = lo
                else:
                    params[key] = trial.suggest_float(key, lo, hi)
            else:
                params[key] = trial.suggest_categorical(key, values)
        return purged_cv_score(
            train_df, returns, spec, params, symbol, cost_model, ref_price, asset_cfg
        )

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    if study.best_trial is not None:
        return dict(study.best_params)
    return dict(spec.defaults)


def save_params(symbol: str, strategy_id: str, params: dict[str, Any], base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"{symbol.upper()}_{strategy_id}.json"
    path.write_text(
        json.dumps({"symbol": symbol.upper(), "strategy": strategy_id, "params": params}, indent=2),
        encoding="utf-8",
    )
    return path
