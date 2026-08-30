"""
Tests for F1.5 — decision correctness (SPEC-A05 fase 1, F-09, D-09):
aggregate portfolio exposure + direct daily-loss check in validate_signal,
and real recent_trades flowing into the kill switch.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.config.settings import Settings
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.risk_manager import RiskManager, aggregate_open_exposure


class _InactiveKillSwitch:
    def is_active(self) -> bool:
        return False

    state = {"triggered_by": None}

    def check_and_trigger(self, **kw):
        self.last_call = kw


def _settings(**over) -> Settings:
    s = Settings()
    for k, v in over.items():
        setattr(s, k, v)
    return s


def _rm(**over) -> RiskManager:
    return RiskManager(settings=_settings(**over), kill_switch=_InactiveKillSwitch())


# ── aggregate exposure ───────────────────────────────────────────────────
def test_aggregate_open_exposure_sums_positions():
    pf = {
        "total_capital": 10_000.0,
        "open_positions": [
            {"entry_price": 100.0, "stop_loss": 96.0, "quantity": 100.0},  # 4%
            {"entry_price": 100.0, "stop_loss": 96.0, "quantity": 100.0},  # 4%
        ],
    }
    assert aggregate_open_exposure(pf, 10_000.0) == pytest.approx(0.08)


def test_risk_portfolio_exposure_aggregation():
    """3 open positions at 4% + a new 4% signal ⇒ rejected (>10%)."""
    rm = _rm(MAX_PORTFOLIO_RISK_PCT=0.10)
    portfolio = {
        "total_capital": 10_000.0,
        "daily_pnl_pct": 0.0,
        "open_positions": [
            {"entry_price": 100.0, "stop_loss": 96.0, "quantity": 100.0}
            for _ in range(3)
        ],
    }
    signal = {
        "entry_price": 100.0,
        "stop_loss": 96.0,
        "quantity": 100.0,  # another 4%
        "risk_reward_ratio": 3.0,
    }
    approved, reason = rm.validate_signal(signal, portfolio)
    assert approved is False
    assert "Portfolio risk at maximum" in reason

    # only 1 open position (4%) + 4% signal = 8% < 10% ⇒ allowed
    portfolio["open_positions"] = portfolio["open_positions"][:1]
    approved, _ = rm.validate_signal(signal, portfolio)
    assert approved is True


def test_daily_loss_limit_blocks_in_validate_signal():
    rm = _rm(DAILY_LOSS_LIMIT_PCT=0.05)
    signal = {
        "entry_price": 100.0,
        "stop_loss": 99.0,
        "quantity": 1.0,
        "risk_reward_ratio": 3.0,
    }
    ok, _ = rm.validate_signal(signal, {"total_capital": 10_000.0, "daily_pnl_pct": -0.02})
    assert ok is True
    blocked, reason = rm.validate_signal(
        signal, {"total_capital": 10_000.0, "daily_pnl_pct": -0.06}
    )
    assert blocked is False
    assert "Daily loss limit" in reason


# ── recent_trades wiring ─────────────────────────────────────────────────
def test_portfolio_manager_records_closed_trades():
    from core.models import Signal

    pm = PortfolioManager(settings=Settings(), initial_capital=10_000.0)
    sig = Signal(
        id="s1", idempotency_key="k1", timestamp=None, symbol="XAUUSD", action="BUY",
        entry_price=100.0, stop_loss=98.0, take_profit=106.0, risk_reward_ratio=3.0,
        confidence=0.7, strategy_id="Momentum", status="pending",
    )
    pm.open_position(sig, quantity=10.0, fill_price=100.0)
    pm.close_position("XAUUSD", exit_price=95.0, strategy_id="Momentum")  # loss
    pm.open_position(sig, quantity=10.0, fill_price=100.0)
    pm.close_position("XAUUSD", exit_price=90.0, strategy_id="Momentum")  # loss

    trades = pm.get_recent_trades()
    assert len(trades) == 2
    assert all(t["net_pnl"] < 0 for t in trades)
    assert [t["symbol"] for t in trades] == ["XAUUSD", "XAUUSD"]


def test_pipeline_passes_recent_trades_to_kill_switch():
    """run_pipeline must forward real trades, not a literal []."""
    src = Path("scripts/run_pipeline.py").read_text(encoding="utf-8")
    assert "risk.update_kill_switch(new_state.model_dump(), [])" not in src
    assert "get_recent_trades" in src
    assert "risk.update_kill_switch(new_state.model_dump(), recent_trades)" in src
