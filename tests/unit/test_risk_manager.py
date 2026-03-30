"""
Tests for RiskManager — property-based with Hypothesis.
"""
from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st
from unittest.mock import MagicMock

from core.config.settings import Settings
from core.risk.risk_manager import RiskManager


def make_risk_manager(
    max_risk_pct: float = 0.01,
    max_portfolio_risk: float = 0.10,
    max_drawdown: float = 0.15,
    kill_switch_active: bool = False,
) -> RiskManager:
    settings = MagicMock(spec=Settings)
    settings.MAX_RISK_PER_TRADE_PCT = max_risk_pct
    settings.MAX_PORTFOLIO_RISK_PCT = max_portfolio_risk
    settings.MAX_DRAWDOWN_PCT = max_drawdown
    settings.DAILY_LOSS_LIMIT_PCT = 0.05
    settings.MAX_CONSECUTIVE_LOSSES = 5

    # No spec= so nested attributes like .state.* are auto-created by MagicMock
    ks = MagicMock()
    ks.is_active.return_value = kill_switch_active
    ks.state.triggered_by = "manual" if kill_switch_active else None

    return RiskManager(settings, ks)


def make_signal(entry: float = 100.0, sl: float = 95.0, tp: float = 115.0) -> dict:
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
    return {
        "entry_price": entry,
        "stop_loss": sl,
        "take_profit": tp,
        "risk_reward_ratio": rr,
    }


def make_portfolio(
    risk_exposure: float = 0.0, drawdown: float = 0.0, available: float = 10000.0
) -> dict:
    return {
        "risk_exposure": risk_exposure,
        "drawdown_current": drawdown,
        "available_capital": available,
        "total_capital": 10000.0,
        "daily_pnl_pct": 0.0,
    }


class TestRiskManagerValidation:
    def test_rejects_when_kill_switch_active(self):
        rm = make_risk_manager(kill_switch_active=True)
        approved, reason = rm.validate_signal(make_signal(), make_portfolio())
        assert not approved
        assert "Kill switch" in reason

    def test_rejects_when_portfolio_risk_at_max(self):
        rm = make_risk_manager(max_portfolio_risk=0.10)
        approved, reason = rm.validate_signal(
            make_signal(), make_portfolio(risk_exposure=0.10)
        )
        assert not approved
        assert "maximum" in reason

    def test_rejects_when_drawdown_at_max(self):
        rm = make_risk_manager(max_drawdown=0.15)
        approved, reason = rm.validate_signal(
            make_signal(), make_portfolio(drawdown=0.15)
        )
        assert not approved
        assert "drawdown" in reason.lower()

    def test_rejects_low_risk_reward(self):
        rm = make_risk_manager()
        signal = {
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "take_profit": 105.0,
            "risk_reward_ratio": 1.0,
        }
        approved, reason = rm.validate_signal(signal, make_portfolio())
        assert not approved
        assert "R:R" in reason

    def test_approves_valid_signal(self):
        rm = make_risk_manager()
        approved, reason = rm.validate_signal(make_signal(), make_portfolio())
        assert approved
        assert reason == ""


class TestPositionSizing:
    @given(
        available=st.floats(min_value=100.0, max_value=100000.0, allow_nan=False),
        entry=st.floats(min_value=1.0, max_value=100000.0, allow_nan=False),
    )
    def test_position_size_never_exceeds_risk_limit(
        self, available: float, entry: float
    ):
        rm = make_risk_manager(max_risk_pct=0.01)
        sl = entry * 0.95
        signal = make_signal(entry=entry, sl=sl, tp=entry * 1.15)
        portfolio = make_portfolio(available=available, risk_exposure=0.0)
        qty = rm.calculate_position_size(signal, portfolio)
        capital_at_risk = qty * abs(entry - sl)
        assert capital_at_risk <= available * 0.02 + 1e-6  # 1% setting + hard limit 2%

    def test_returns_zero_for_zero_price_risk(self):
        rm = make_risk_manager()
        signal = {
            "entry_price": 100.0,
            "stop_loss": 100.0,
            "take_profit": 115.0,
            "risk_reward_ratio": 0,
        }
        qty = rm.calculate_position_size(signal, make_portfolio())
        assert qty == 0.0
