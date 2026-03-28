"""Shared pytest fixtures."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from core.config.settings import Settings


@pytest.fixture
def mock_settings() -> Settings:
    s = MagicMock(spec=Settings)
    s.EXECUTION_MODE = "paper"
    s.TRADING_ENABLED = False
    s.MAX_RISK_PER_TRADE_PCT = 0.01
    s.MAX_PORTFOLIO_RISK_PCT = 0.10
    s.DAILY_LOSS_LIMIT_PCT = 0.05
    s.MAX_CONSECUTIVE_LOSSES = 5
    s.MAX_DRAWDOWN_PCT = 0.15
    s.JWT_SECRET_KEY = "test-secret"
    s.JWT_ALGORITHM = "HS256"
    s.JWT_EXPIRE_MINUTES = 60
    return s


@pytest.fixture
def sample_signal() -> dict:
    return {
        "id": "test-signal-001",
        "idempotency_key": "abc123",
        "symbol": "BTCUSDT",
        "action": "BUY",
        "entry_price": 50000.0,
        "stop_loss": 47500.0,
        "take_profit": 57500.0,
        "risk_reward_ratio": 3.0,
        "confidence": 0.78,
    }


@pytest.fixture
def sample_portfolio() -> dict:
    return {
        "total_capital": 10000.0,
        "available_capital": 9000.0,
        "risk_exposure": 0.05,
        "daily_pnl_pct": 0.0,
        "drawdown_current": 0.02,
    }
