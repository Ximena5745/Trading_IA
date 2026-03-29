"""
Module: core/backtesting/costs.py
Responsibility: Realistic multi-asset cost model for backtesting and paper trading.
  - Crypto spot: commission_pct + slippage_pct
  - Forex/Indices/Commodities: spread_pips + swap overnight (from broker)
  - Swap source: mt5.symbol_info().swap_long / swap_short (decision v2.4)

FASE E: multi-asset cost model with InstrumentConfig integration.
"""
from __future__ import annotations

from typing import Optional

from core.config.constants import PAPER_COMMISSION_PCT, PAPER_SLIPPAGE_PCT
from core.models import AssetClass, InstrumentConfig, detect_asset_class, get_instrument
from core.observability.logger import get_logger

logger = get_logger(__name__)


class CostModel:
    """
    Unified cost model for all asset classes.

    For crypto (Binance spot):
      - commission = trade_value × commission_pct
      - slippage   = trade_value × slippage_pct

    For forex / indices / commodities (MT5):
      - spread_cost = spread_pips × pip_value × lots
      - swap_cost   = nights_held × (swap_long or swap_short) × lots
      - No commission (IC Markets Raw account — spread-only)
    """

    def __init__(
        self,
        commission_pct: float = PAPER_COMMISSION_PCT,
        slippage_pct: float = PAPER_SLIPPAGE_PCT,
    ):
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct

    # ── Crypto (backward-compatible with existing backtesting engine) ──────

    def apply(self, trade: dict) -> dict:
        """Apply costs to a trade dict. Routes by asset_class if available."""
        symbol = trade.get("symbol", "")
        asset_class = detect_asset_class(symbol)

        if asset_class == AssetClass.CRYPTO:
            return self._apply_crypto(trade)

        instrument = get_instrument(symbol)
        if instrument is not None:
            return self._apply_mt5(trade, instrument)

        return self._apply_crypto(trade)   # fallback

    def apply_fill_slippage(self, price: float, side: str) -> float:
        """Apply slippage to a crypto fill price (backward-compatible)."""
        slip = price * self.slippage_pct
        return price + slip if side == "BUY" else price - slip

    # ── MT5 instruments ────────────────────────────────────────────────────

    def get_swap_cost(
        self,
        symbol: str,
        nights: int,
        side: str,
        lots: float,
        instrument: Optional[InstrumentConfig] = None,
    ) -> float:
        """
        Calculate swap (rollover) cost for holding `lots` for `nights` nights.
        Rates come from InstrumentConfig (refreshed at runtime from MT5).

        Returns positive value = cost (reduces P&L).
        swap_long/swap_short are broker values in currency per lot per night.
        """
        if nights <= 0:
            return 0.0
        inst = instrument or get_instrument(symbol)
        if inst is None:
            return 0.0
        rate = inst.swap_long if side == "BUY" else inst.swap_short
        cost = abs(rate) * lots * nights
        logger.debug("swap_cost_calculated", symbol=symbol, nights=nights, side=side,
                     lots=lots, rate=rate, cost=round(cost, 4))
        return round(cost, 4)

    def get_spread_cost(
        self,
        symbol: str,
        lots: float,
        instrument: Optional[InstrumentConfig] = None,
    ) -> float:
        """
        Cost of crossing the spread: spread_pips × pip_value × lots.
        Applies on entry (bid/ask crossing) — no commission for IC Markets Raw.
        """
        inst = instrument or get_instrument(symbol)
        if inst is None:
            return 0.0
        cost = inst.spread_pips * inst.pip_value * lots
        return round(cost, 4)

    # ── Private ────────────────────────────────────────────────────────────

    def _apply_crypto(self, trade: dict) -> dict:
        value = trade.get("value", 0.0)
        commission = value * self.commission_pct
        slippage   = value * self.slippage_pct
        gross_pnl  = trade.get("gross_pnl", 0.0)
        trade["net_pnl"]    = gross_pnl - commission - slippage
        trade["commission"] = commission
        trade["slippage"]   = slippage
        trade["cost_model"] = "crypto"
        return trade

    def _apply_mt5(self, trade: dict, instrument: InstrumentConfig) -> dict:
        lots   = trade.get("quantity", 0.0)
        side   = trade.get("side", "BUY")
        nights = trade.get("nights_held", 0)

        spread_cost = self.get_spread_cost(instrument.symbol, lots, instrument)
        swap_cost   = self.get_swap_cost(instrument.symbol, nights, side, lots, instrument)
        total_cost  = spread_cost + swap_cost

        gross_pnl = trade.get("gross_pnl", 0.0)
        trade["net_pnl"]       = gross_pnl - total_cost
        trade["spread_cost"]   = spread_cost
        trade["swap_cost"]     = swap_cost
        trade["commission"]    = 0.0
        trade["slippage"]      = spread_cost   # spread IS the effective slippage for MT5
        trade["cost_model"]    = "mt5"
        return trade
