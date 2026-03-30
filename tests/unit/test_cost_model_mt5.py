"""
Tests for CostModel — MT5 multi-asset costs (FASE E).
Covers: spread cost, swap cost, crypto fallback, net_pnl reduction.
"""
from __future__ import annotations


from core.backtesting.costs import CostModel
from core.models import AssetClass, InstrumentConfig


def make_instrument(
    symbol: str = "EURUSD",
    asset_class: AssetClass = AssetClass.FOREX,
    pip_value: float = 10.0,
    lot_size: float = 100_000,
    spread_pips: float = 0.6,
    swap_long: float = -0.5,
    swap_short: float = -0.3,
    point: float = 0.00001,
) -> InstrumentConfig:
    return InstrumentConfig(
        symbol=symbol,
        mt5_symbol=symbol,
        asset_class=asset_class,
        pip_value=pip_value,
        lot_size=lot_size,
        spread_pips=spread_pips,
        swap_long=swap_long,
        swap_short=swap_short,
        point=point,
    )


class TestSpreadCost:
    """get_spread_cost = spread_pips × pip_value × lots."""

    def test_eurusd_spread_cost(self):
        """EURUSD 0.6 pip spread, 0.01 lots → 0.6 × 10.0 × 0.01 = 0.06 USD."""
        model = CostModel()
        inst = make_instrument("EURUSD", spread_pips=0.6, pip_value=10.0)
        cost = model.get_spread_cost("EURUSD", lots=0.01, instrument=inst)
        assert abs(cost - 0.06) < 1e-4

    def test_spread_cost_scales_with_lots(self):
        """Spread cost doubles when lots double."""
        model = CostModel()
        inst = make_instrument("GBPUSD", spread_pips=0.9, pip_value=10.0)
        cost_1 = model.get_spread_cost("GBPUSD", lots=0.01, instrument=inst)
        cost_2 = model.get_spread_cost("GBPUSD", lots=0.02, instrument=inst)
        assert abs(cost_2 - 2 * cost_1) < 1e-6

    def test_xauusd_spread_cost(self):
        """XAUUSD 0.25 pip spread, pip_value=1.0, 0.1 lots → 0.025 USD."""
        model = CostModel()
        inst = make_instrument(
            "XAUUSD",
            asset_class=AssetClass.COMMODITIES,
            spread_pips=0.25,
            pip_value=1.0,
            lot_size=100,
        )
        cost = model.get_spread_cost("XAUUSD", lots=0.1, instrument=inst)
        assert abs(cost - 0.025) < 1e-4

    def test_unknown_symbol_returns_zero(self):
        """Symbol not in INSTRUMENT_CONFIGS and no instrument passed → 0.0."""
        model = CostModel()
        cost = model.get_spread_cost("UNKNWN", lots=1.0)
        assert cost == 0.0


class TestSwapCost:
    """get_swap_cost = abs(rate) × lots × nights."""

    def test_buy_uses_swap_long(self):
        """BUY side uses swap_long rate."""
        model = CostModel()
        inst = make_instrument("EURUSD", swap_long=-0.5, swap_short=-0.3)
        cost = model.get_swap_cost(
            "EURUSD", nights=1, side="BUY", lots=1.0, instrument=inst
        )
        assert abs(cost - 0.5) < 1e-6

    def test_sell_uses_swap_short(self):
        """SELL side uses swap_short rate."""
        model = CostModel()
        inst = make_instrument("EURUSD", swap_long=-0.5, swap_short=-0.3)
        cost = model.get_swap_cost(
            "EURUSD", nights=1, side="SELL", lots=1.0, instrument=inst
        )
        assert abs(cost - 0.3) < 1e-6

    def test_swap_scales_with_nights(self):
        """Holding 3 nights triples the swap cost."""
        model = CostModel()
        inst = make_instrument("GBPUSD", swap_long=-1.0, swap_short=-0.8)
        cost_1 = model.get_swap_cost(
            "GBPUSD", nights=1, side="BUY", lots=1.0, instrument=inst
        )
        cost_3 = model.get_swap_cost(
            "GBPUSD", nights=3, side="BUY", lots=1.0, instrument=inst
        )
        assert abs(cost_3 - 3 * cost_1) < 1e-6

    def test_zero_nights_returns_zero(self):
        """Same-day close → no swap."""
        model = CostModel()
        inst = make_instrument("EURUSD", swap_long=-1.0)
        cost = model.get_swap_cost(
            "EURUSD", nights=0, side="BUY", lots=1.0, instrument=inst
        )
        assert cost == 0.0

    def test_swap_is_always_positive(self):
        """Swap cost must always be non-negative (reduces P&L)."""
        model = CostModel()
        inst = make_instrument("EURUSD", swap_long=-0.5, swap_short=-0.3)
        for side in ("BUY", "SELL"):
            cost = model.get_swap_cost(
                "EURUSD", nights=2, side=side, lots=0.5, instrument=inst
            )
            assert cost >= 0.0

    def test_unknown_symbol_returns_zero(self):
        model = CostModel()
        cost = model.get_swap_cost("UNKNWN", nights=5, side="BUY", lots=1.0)
        assert cost == 0.0


class TestApplyMT5:
    """apply() routes MT5 symbols through spread + swap logic."""

    def _make_trade(
        self,
        symbol: str = "EURUSD",
        gross_pnl: float = 100.0,
        quantity: float = 0.01,
        side: str = "BUY",
        nights: int = 0,
    ) -> dict:
        return {
            "symbol": symbol,
            "gross_pnl": gross_pnl,
            "net_pnl": gross_pnl,
            "quantity": quantity,
            "value": quantity * 1.1 * 100_000,
            "side": side,
            "nights_held": nights,
        }

    def test_mt5_costs_reduce_pnl(self):
        """MT5 trade net_pnl must be less than gross_pnl."""
        model = CostModel()
        trade = self._make_trade("EURUSD", gross_pnl=100.0, quantity=0.01)
        result = model.apply(trade)
        assert result["net_pnl"] < 100.0

    def test_mt5_has_no_commission(self):
        """IC Markets Raw account: commission = 0, cost = spread."""
        model = CostModel()
        trade = self._make_trade("EURUSD", gross_pnl=100.0, quantity=0.1)
        result = model.apply(trade)
        assert result["commission"] == 0.0
        assert result.get("spread_cost", 0.0) > 0.0

    def test_mt5_cost_model_label(self):
        """Trade tagged as mt5 cost model."""
        model = CostModel()
        trade = self._make_trade("EURUSD")
        result = model.apply(trade)
        assert result["cost_model"] == "mt5"

    def test_overnight_swap_increases_total_cost(self):
        """A trade held overnight costs more than intraday."""
        model = CostModel()
        intraday = self._make_trade("EURUSD", nights=0)
        overnight = self._make_trade("EURUSD", nights=1)
        r1 = model.apply(intraday)
        r2 = model.apply(overnight)
        assert r2["net_pnl"] < r1["net_pnl"]

    def test_zero_pnl_trade_is_still_a_loss(self):
        """Break-even gross P&L becomes negative after spread."""
        model = CostModel()
        trade = self._make_trade("EURUSD", gross_pnl=0.0, quantity=0.1)
        result = model.apply(trade)
        assert result["net_pnl"] < 0.0


class TestApplyCrypto:
    """apply() uses commission_pct + slippage_pct for crypto."""

    def _make_crypto_trade(self, gross_pnl: float = 100.0) -> dict:
        return {
            "symbol": "BTCUSDT",
            "gross_pnl": gross_pnl,
            "net_pnl": gross_pnl,
            "entry_price": 50000.0,
            "quantity": 0.01,
            "value": 500.0,
            "side": "BUY",
        }

    def test_crypto_reduces_pnl(self):
        model = CostModel()
        result = model.apply(self._make_crypto_trade(gross_pnl=100.0))
        assert result["net_pnl"] < 100.0

    def test_crypto_cost_model_label(self):
        model = CostModel()
        result = model.apply(self._make_crypto_trade())
        assert result["cost_model"] == "crypto"

    def test_crypto_zero_pnl_is_loss(self):
        model = CostModel()
        result = model.apply(self._make_crypto_trade(gross_pnl=0.0))
        assert result["net_pnl"] < 0.0
