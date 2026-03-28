"""
Module: core/backtesting/costs.py
Responsibility: Apply realistic trading costs to backtest trades
Dependencies: constants
"""
from __future__ import annotations

from core.config.constants import PAPER_COMMISSION_PCT, PAPER_SLIPPAGE_PCT


class CostModel:
    def __init__(
        self,
        commission_pct: float = PAPER_COMMISSION_PCT,
        slippage_pct: float = PAPER_SLIPPAGE_PCT,
    ):
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    def apply(self, trade: dict) -> dict:
        value = trade.get("value", 0.0)
        commission = value * self.commission_pct
        slippage = value * self.slippage_pct
        gross_pnl = trade.get("gross_pnl", 0.0)
        trade["net_pnl"] = gross_pnl - commission - slippage
        trade["commission"] = commission
        trade["slippage"] = slippage
        return trade

    def apply_fill_slippage(self, price: float, side: str) -> float:
        """Apply slippage to a fill price."""
        slip = price * self.slippage_pct
        return price + slip if side == "BUY" else price - slip
