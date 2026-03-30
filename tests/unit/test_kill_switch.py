"""
Tests for KillSwitch — property-based with Hypothesis.
Every circuit breaker must trigger without exception when its threshold is crossed.
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from unittest.mock import MagicMock

from core.config.settings import Settings
from core.risk.kill_switch import KillSwitch


def make_settings(
    daily_loss_limit: float = 0.05, max_consecutive: int = 5, max_drawdown: float = 0.15
) -> Settings:
    s = MagicMock(spec=Settings)
    s.DAILY_LOSS_LIMIT_PCT = daily_loss_limit
    s.MAX_CONSECUTIVE_LOSSES = max_consecutive
    s.MAX_DRAWDOWN_PCT = max_drawdown
    return s


class TestKillSwitchDailyLoss:
    @given(
        daily_pnl_pct=st.floats(min_value=-1.0, max_value=0.0, allow_nan=False),
        limit=st.floats(min_value=0.01, max_value=0.10, allow_nan=False),
    )
    def test_triggers_when_loss_exceeds_limit(self, daily_pnl_pct: float, limit: float):
        ks = KillSwitch(make_settings(daily_loss_limit=limit))
        ks.check_and_trigger(daily_pnl_pct, drawdown_current=0.0, recent_trades=[])
        if daily_pnl_pct <= -limit:
            assert (
                ks.is_active()
            ), f"Should be active: pnl={daily_pnl_pct}, limit={limit}"
            assert ks.state.triggered_by == "daily_loss_limit"
        else:
            assert not ks.is_active()

    def test_trigger_reason_is_daily_loss_limit(self):
        ks = KillSwitch(make_settings(daily_loss_limit=0.05))
        ks.check_and_trigger(-0.06, 0.0, [])
        assert ks.state.triggered_by == "daily_loss_limit"
        assert ks.state.triggered_at is not None


class TestKillSwitchDrawdown:
    @given(
        drawdown=st.floats(min_value=0.0, max_value=0.5, allow_nan=False),
        limit=st.floats(min_value=0.05, max_value=0.20, allow_nan=False),
    )
    def test_triggers_when_drawdown_exceeds_limit(self, drawdown: float, limit: float):
        ks = KillSwitch(make_settings(max_drawdown=limit))
        ks.check_and_trigger(0.0, drawdown_current=drawdown, recent_trades=[])
        if drawdown >= limit:
            assert ks.is_active()
        else:
            assert not ks.is_active()


class TestKillSwitchConsecutiveLosses:
    def _make_trades(self, losses: int) -> list:
        return [{"net_pnl": -10.0}] * losses

    @given(n_losses=st.integers(min_value=0, max_value=10))
    def test_triggers_on_consecutive_losses(self, n_losses: int):
        max_c = 5
        ks = KillSwitch(make_settings(max_consecutive=max_c))
        trades = self._make_trades(n_losses)
        ks.check_and_trigger(0.0, 0.0, trades)
        if n_losses >= max_c:
            assert ks.is_active()
        else:
            assert not ks.is_active()

    def test_non_consecutive_losses_do_not_trigger(self):
        ks = KillSwitch(make_settings(max_consecutive=3))
        trades = [
            {"net_pnl": -10},
            {"net_pnl": 5},
            {"net_pnl": -10},
            {"net_pnl": -10},
        ]
        ks.check_and_trigger(0.0, 0.0, trades)
        assert not ks.is_active()


class TestKillSwitchReset:
    def test_only_resets_when_active(self):
        ks = KillSwitch(make_settings())
        ks.check_and_trigger(-0.10, 0.0, [])
        assert ks.is_active()
        ks.reset(admin_token="admin")
        assert not ks.is_active()

    def test_reset_clears_trigger_info(self):
        ks = KillSwitch(make_settings())
        ks.check_and_trigger(-0.10, 0.0, [])
        ks.reset(admin_token="admin")
        assert ks.state.triggered_by is None
        assert ks.state.triggered_at is None
        assert ks.state.reset_at is not None

    def test_does_not_retrigger_if_already_active(self):
        ks = KillSwitch(make_settings())
        ks.check_and_trigger(-0.10, 0.0, [])
        first_trigger = ks.state.triggered_at
        ks.check_and_trigger(-0.20, 0.5, [{"net_pnl": -1}] * 10)
        assert ks.state.triggered_at == first_trigger
