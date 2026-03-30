"""
Module: core/risk/position_sizer.py
Responsibility: Calculate position size by asset class.
  - Crypto spot (Binance): units of base asset
  - Forex: standard lots via pip value formula
  - Indices/CFD: contracts via point value formula
  - Commodities: lots via pip value (same as forex logic)

FASE E additions: _forex_sizing(), _cfd_sizing() using InstrumentConfig.
"""
from __future__ import annotations

from typing import Optional

from core.config.constants import HARD_LIMITS
from core.config.settings import Settings
from core.models import AssetClass, InstrumentConfig, detect_asset_class
from core.observability.logger import get_logger

logger = get_logger(__name__)


class PositionSizer:
    def __init__(self, settings: Settings):
        self._settings = settings

    # ── Public entry point ─────────────────────────────────────────────────

    def calculate(
        self,
        symbol: str,
        available_capital: float,
        total_capital: float,
        entry_price: float,
        stop_loss: float,
        instrument: Optional[InstrumentConfig] = None,
    ) -> float:
        """
        Route sizing to the correct formula based on asset class.
        Returns quantity in native units:
          - Crypto: base asset units (e.g. 0.001 BTC)
          - Forex:  standard lots (e.g. 0.05)
          - Indices: contracts (e.g. 0.1)
          - Commodities: lots (e.g. 0.01)
        """
        asset_class = detect_asset_class(symbol)
        risk_capital = available_capital * min(
            self._settings.MAX_RISK_PER_TRADE_PCT,
            HARD_LIMITS["max_risk_per_trade_pct"],
        )

        if asset_class == AssetClass.CRYPTO and instrument is None:
            qty = self._crypto_sizing(risk_capital, entry_price, stop_loss)
        elif instrument is not None and asset_class == AssetClass.FOREX:
            qty = self._forex_sizing(risk_capital, stop_loss, entry_price, instrument)
        elif instrument is not None and asset_class in (AssetClass.INDICES, AssetClass.COMMODITIES):
            qty = self._cfd_sizing(risk_capital, stop_loss, entry_price, instrument)
        else:
            qty = self._crypto_sizing(risk_capital, entry_price, stop_loss)

        qty = self._apply_symbol_cap(qty, entry_price, total_capital, instrument)
        logger.info(
            "position_sized",
            symbol=symbol,
            asset_class=asset_class.value,
            quantity=round(qty, 6),
            risk_capital=round(risk_capital, 2),
        )
        return qty

    # ── Legacy interface (backward-compatible with FASE C pipeline) ────────

    def fixed_fractional(
        self, available_capital: float, entry_price: float, stop_loss: float
    ) -> float:
        """Crypto-only sizing. Kept for backward compatibility."""
        return self._crypto_sizing(
            available_capital * min(
                self._settings.MAX_RISK_PER_TRADE_PCT,
                HARD_LIMITS["max_risk_per_trade_pct"],
            ),
            entry_price,
            stop_loss,
        )

    def apply_symbol_cap(
        self, quantity: float, entry_price: float, total_capital: float
    ) -> float:
        return self._apply_symbol_cap(quantity, entry_price, total_capital, None)

    # ── Sizing formulas ────────────────────────────────────────────────────

    @staticmethod
    def _crypto_sizing(risk_capital: float, entry_price: float, stop_loss: float) -> float:
        """qty = capital_at_risk / price_risk_per_unit"""
        price_risk = abs(entry_price - stop_loss)
        if price_risk == 0:
            logger.warning("position_sizer_zero_price_risk", entry=entry_price, sl=stop_loss)
            return 0.0
        return round(risk_capital / price_risk, 6)

    @staticmethod
    def _forex_sizing(
        risk_capital: float,
        stop_loss: float,
        entry_price: float,
        instrument: InstrumentConfig,
    ) -> float:
        """
        lots = capital_at_risk / (stop_pips × pip_value_per_lot)
        stop_pips = abs(entry - sl) / point_size
        pip_value is already in USD per standard lot.
        """
        point = instrument.point
        pip_value = instrument.pip_value     # USD per pip per standard lot
        stop_pips = abs(entry_price - stop_loss) / point
        if stop_pips == 0 or pip_value == 0:
            return 0.0
        lots = risk_capital / (stop_pips * pip_value)
        lots = max(instrument.min_lots, round(lots / instrument.lot_step) * instrument.lot_step)
        return round(lots, 2)

    @staticmethod
    def _cfd_sizing(
        risk_capital: float,
        stop_loss: float,
        entry_price: float,
        instrument: InstrumentConfig,
    ) -> float:
        """
        contracts = capital_at_risk / (stop_points × point_value_per_contract)
        For indices/commodities where pip_value = USD per point per contract.
        """
        point = instrument.point
        point_value = instrument.pip_value   # USD per index point per contract
        stop_points = abs(entry_price - stop_loss) / point
        if stop_points == 0 or point_value == 0:
            return 0.0
        contracts = risk_capital / (stop_points * point_value)
        contracts = max(instrument.min_lots, round(contracts / instrument.lot_step) * instrument.lot_step)
        return round(contracts, 2)

    def _apply_symbol_cap(
        self,
        quantity: float,
        entry_price: float,
        total_capital: float,
        instrument: Optional[InstrumentConfig],
    ) -> float:
        """Ensure no single position exceeds max_position_single_symbol_pct of capital."""
        max_value = total_capital * HARD_LIMITS["max_position_single_symbol_pct"]
        # For MT5 instruments, position value = lots × lot_size × price
        if instrument is not None:
            position_value = quantity * instrument.lot_size * entry_price
        else:
            position_value = quantity * entry_price

        if position_value > max_value and entry_price > 0:
            if instrument is not None:
                capped = max_value / (instrument.lot_size * entry_price)
                capped = max(instrument.min_lots, round(capped / instrument.lot_step) * instrument.lot_step)
            else:
                capped = max_value / entry_price
            logger.warning("position_capped", original=quantity, capped=round(capped, 6))
            return round(capped, 6)
        return quantity
