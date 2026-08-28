"""
Module: core/ml/i1_gate_validator/costs.py
Responsibility: Transaction-cost-aware P&L from signals (gross/net returns, turnover)
"""
from __future__ import annotations

import pandas as pd

from core.backtesting.costs import CostModel
from core.models import AssetClass, detect_asset_class, get_instrument


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
