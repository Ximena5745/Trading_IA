"""
Module: core/ml/i1_gate_validator/costs.py
Responsibility: Transaction-cost-aware P&L from signals (gross/net returns, turnover)
"""
from __future__ import annotations

import pandas as pd

from core.backtesting.costs import CostModel
from core.models import AssetClass, detect_asset_class, get_instrument


def half_side_cost_pct(symbol: str, cost_model: CostModel, ref_price: float = 1.0) -> float:
    """Cost of **one side** (half a round-trip) as a fraction of notional.

    Callers charge this per unit of `signals.diff().abs()`, which sums to 2 over a
    round-trip — so this MUST be a per-side figure, symmetric with the crypto
    branch (commission + slippage are per fill). See M-1 in
    docs/audits/AUDIT_F2_QUANT_INDEPENDENT_BRIEF.md.
    """
    asset_class = detect_asset_class(symbol)
    if asset_class == AssetClass.CRYPTO:
        return cost_model.commission_pct + cost_model.slippage_pct

    inst = get_instrument(symbol)
    if inst is None:
        return 0.0005

    # spread_pips is the FULL quoted bid-ask spread; crossing it once = one
    # round-trip, so one side costs half of it.
    #
    # The identity (spread_pips * pip_value / (lot_size * ref_price)) only
    # collapses to spread_in_price / price when pip_value == pip_size * lot_size,
    # which holds for USD-quoted forex majors, XAUUSD and the index CFDs. For
    # JPY-quoted pairs (USDJPY, ...) pip_value is already FX-converted, so
    # dividing by the JPY notional double-counts the rate and understates the
    # cost by ~100x. Those pairs are not gate-relevant today; fix before relying
    # on their net Sharpe. See docs/CORE_VALIDATION_RAMA1_2026-08-30.md.
    #
    # Broker commission (IC Markets Raw ~$3.5/lot round-turn) is still unmodeled
    # for MT5 instruments; the cost sweep x1..x3 in run_edge_robustness covers it.
    spread_dollars = inst.spread_pips * inst.pip_value * 1.0
    notional = max(inst.lot_size * ref_price, 1.0)
    return (spread_dollars / notional) / 2.0


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
