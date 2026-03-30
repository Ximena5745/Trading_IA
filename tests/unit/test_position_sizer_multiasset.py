"""
Tests for PositionSizer — multi-asset sizing (FASE E).
Covers Forex, Indices/CFD, and Crypto sizing with InstrumentConfig.
"""
from __future__ import annotations

from unittest.mock import MagicMock


from core.config.settings import Settings
from core.models import AssetClass, InstrumentConfig
from core.risk.position_sizer import PositionSizer


def make_settings(max_risk_pct: float = 0.01) -> Settings:
    s = MagicMock(spec=Settings)
    s.MAX_RISK_PER_TRADE_PCT = max_risk_pct
    return s


def make_instrument(
    symbol: str = "EURUSD",
    asset_class: AssetClass = AssetClass.FOREX,
    pip_value: float = 10.0,
    lot_size: float = 100_000,
    min_lots: float = 0.01,
    lot_step: float = 0.01,
    spread_pips: float = 0.6,
    point: float = 0.00001,
) -> InstrumentConfig:
    return InstrumentConfig(
        symbol=symbol,
        mt5_symbol=symbol,
        asset_class=asset_class,
        pip_value=pip_value,
        lot_size=lot_size,
        min_lots=min_lots,
        lot_step=lot_step,
        spread_pips=spread_pips,
        point=point,
    )


class TestForexSizing:
    """Lot sizing for Forex pairs (EURUSD, GBPUSD, etc.)."""

    def test_eurusd_basic_sizing(self):
        """With 10k capital, 1% risk, 50-pip SL → ≤ 0.2 lots."""
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        instrument = make_instrument("EURUSD")
        # 50 pips stop = 0.0050 distance on 1.1000 entry
        lots = sizer.calculate(
            symbol="EURUSD",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=1.1000,
            stop_loss=1.0950,
            instrument=instrument,
        )
        # risk_capital = 100; stop_pips = 50; lots = 100 / (50 × 10) = 0.20
        assert lots > 0.0
        assert lots <= 0.20 + 1e-6

    def test_forex_sizing_minimum_lots_floor(self):
        """Even if math gives < min_lots, result must be ≥ min_lots."""
        sizer = PositionSizer(make_settings(max_risk_pct=0.001))  # 0.1% risk
        instrument = make_instrument("EURUSD")
        lots = sizer.calculate(
            symbol="EURUSD",
            available_capital=100.0,
            total_capital=100.0,
            entry_price=1.1000,
            stop_loss=1.0900,  # 100-pip stop
            instrument=instrument,
        )
        assert lots >= instrument.min_lots

    def test_forex_zero_stop_returns_zero(self):
        """SL == entry_price → price_risk = 0 → return 0."""
        sizer = PositionSizer(make_settings())
        instrument = make_instrument("EURUSD")
        qty = sizer.calculate(
            symbol="EURUSD",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=1.1000,
            stop_loss=1.1000,
            instrument=instrument,
        )
        assert qty == 0.0

    def test_usdjpy_uses_pip_value(self):
        """USDJPY has pip_value ≈ 9.09 (not 10) — sizing should reflect that."""
        jpy_instrument = make_instrument(
            "USDJPY",
            pip_value=9.09,
            lot_size=100_000,
            point=0.001,
        )
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        lots = sizer.calculate(
            symbol="USDJPY",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=150.00,
            stop_loss=149.50,  # 50 pips (0.50 / 0.001 = 500 pips... wait, JPY point=0.001 so 0.50/0.001=500 pips)
            instrument=jpy_instrument,
        )
        # 100 / (500 × 9.09) = 0.022 → rounds to 0.02 lots
        assert lots >= jpy_instrument.min_lots

    def test_forex_lots_are_rounded_to_lot_step(self):
        """Result must be a multiple of lot_step."""
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        instrument = make_instrument("GBPUSD", lot_step=0.01)
        lots = sizer.calculate(
            symbol="GBPUSD",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=1.2500,
            stop_loss=1.2450,
            instrument=instrument,
        )
        # Check it's a multiple of lot_step (within float precision)
        assert (
            abs(lots % instrument.lot_step) < 1e-9
            or abs(lots % instrument.lot_step - instrument.lot_step) < 1e-9
        )


class TestCFDIndexSizing:
    """Contract sizing for Indices and Commodities."""

    def test_us500_basic_sizing(self):
        """US500 CFD: 1% risk on 10k, 20-point SL → small number of contracts."""
        us500 = make_instrument(
            "US500",
            asset_class=AssetClass.INDICES,
            pip_value=1.0,
            lot_size=1,
            min_lots=0.01,
            lot_step=0.01,
            point=0.1,
        )
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        contracts = sizer.calculate(
            symbol="US500",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=5000.0,
            stop_loss=4980.0,  # 20-point stop → 200 points (0.1 per point)
            instrument=us500,
        )
        # risk = 100; stop_points = 200; contracts = 100 / (200 × 1.0) = 0.5
        assert contracts > 0.0
        assert contracts <= 0.5 + 1e-6

    def test_xauusd_commodity_sizing(self):
        """XAUUSD: commodity sizing formula (same logic as CFD)."""
        xau = make_instrument(
            "XAUUSD",
            asset_class=AssetClass.COMMODITIES,
            pip_value=1.0,
            lot_size=100,
            min_lots=0.01,
            lot_step=0.01,
            point=0.01,
        )
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        lots = sizer.calculate(
            symbol="XAUUSD",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=2000.0,
            stop_loss=1990.0,  # $10 stop = 1000 pips (0.01 per point)
            instrument=xau,
        )
        assert lots > 0.0
        assert lots >= xau.min_lots


class TestCryptoSizing:
    """Crypto sizing (no instrument config needed — Binance native)."""

    def test_btcusdt_sizing(self):
        """1% risk, $1000 available, $2500 price risk → 0.004 BTC."""
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        qty = sizer.calculate(
            symbol="BTCUSDT",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=50_000.0,
            stop_loss=47_500.0,  # $2500 stop
        )
        # risk_capital = 100; price_risk = 2500; qty = 100/2500 = 0.04
        assert abs(qty - 0.04) < 1e-5

    def test_crypto_zero_stop_returns_zero(self):
        sizer = PositionSizer(make_settings())
        qty = sizer.calculate(
            symbol="BTCUSDT",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=50_000.0,
            stop_loss=50_000.0,
        )
        assert qty == 0.0


class TestPositionCap:
    """apply_symbol_cap must prevent oversized positions."""

    def test_crypto_position_capped_when_oversized(self):
        """If computed quantity exceeds % of capital, it gets capped."""
        sizer = PositionSizer(
            make_settings(max_risk_pct=0.50)
        )  # huge risk % to force cap
        qty = sizer.calculate(
            symbol="BTCUSDT",
            available_capital=10_000.0,
            total_capital=10_000.0,
            entry_price=50_000.0,
            stop_loss=49_000.0,
        )
        # Without cap: 5000 / 1000 = 5.0 BTC = $250,000 (way above capital)
        # Cap: max_position_single_symbol_pct × 10,000 / 50,000
        assert (
            qty * 50_000.0 <= 10_000.0 * 0.25 + 1
        )  # HARD_LIMITS["max_position_single_symbol_pct"] = 0.20-0.25 range

    def test_backward_compatible_fixed_fractional(self):
        """fixed_fractional() still works as before."""
        sizer = PositionSizer(make_settings(max_risk_pct=0.01))
        qty = sizer.fixed_fractional(
            available_capital=10_000.0,
            entry_price=50_000.0,
            stop_loss=47_500.0,
        )
        assert qty > 0.0
