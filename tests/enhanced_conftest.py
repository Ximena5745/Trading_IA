"""
Enhanced test configuration with better fixtures and utilities.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any

from core.config.settings import Settings
from core.models import (
    MarketData, FeatureSet, AgentOutput, Signal, 
    Portfolio, Position, Order, MarketRegime
)
from core.agents.technical_agent import TechnicalAgent
from core.agents.fundamental_agent import FundamentalAgent
from core.risk.risk_manager import RiskManager
from core.risk.kill_switch import KillSwitch
from core.portfolio.portfolio_manager import PortfolioManager
from core.execution.paper_executor import PaperExecutor
from core.execution.order_tracker import OrderTracker


@pytest.fixture
def mock_settings() -> Settings:
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.EXECUTION_MODE = "paper"
    settings.TRADING_ENABLED = False
    settings.MAX_RISK_PER_TRADE_PCT = 0.01
    settings.MAX_PORTFOLIO_RISK_PCT = 0.10
    settings.DAILY_LOSS_LIMIT_PCT = 0.05
    settings.MAX_CONSECUTIVE_LOSSES = 5
    settings.MAX_DRAWDOWN_PCT = 0.15
    settings.JWT_SECRET_KEY = "test-secret-key"
    settings.JWT_ALGORITHM = "HS256"
    settings.JWT_EXPIRE_MINUTES = 60
    settings.BINANCE_API_KEY = "test-key"
    settings.BINANCE_SECRET_KEY = "test-secret"
    settings.BINANCE_TESTNET = True
    settings.DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5432/test"
    settings.REDIS_URL = "redis://localhost:6379"
    return settings


@pytest.fixture
def sample_market_data() -> MarketData:
    """Sample market data for testing."""
    return MarketData(
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        open=Decimal("50000.0"),
        high=Decimal("50500.0"),
        low=Decimal("49800.0"),
        close=Decimal("50200.0"),
        volume=Decimal("1000.0"),
        quote_volume=Decimal("50000000.0"),
        trades_count=5000,
        taker_buy_volume=Decimal("600.0"),
        source="binance",
        feature_version="v1",
    )


@pytest.fixture
def sample_feature_set() -> FeatureSet:
    """Sample feature set for testing."""
    return FeatureSet(
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        version="v1",
        rsi_14=45.0,
        rsi_7=40.0,
        macd_line=100.0,
        macd_signal=50.0,
        macd_histogram=50.0,
        ema_9=50100.0,
        ema_21=50000.0,
        ema_50=49500.0,
        ema_200=48000.0,
        trend_direction="bullish",
        atr_14=300.0,
        bb_upper=51000.0,
        bb_lower=49000.0,
        bb_width=2000.0,
        volatility_regime="medium",
        vwap=50000.0,
        volume_sma_20=800.0,
        volume_ratio=1.25,
        obv=1000000.0,
        bid_ask_spread=10.0,
        order_book_imbalance=0.1,
        close=50200.0,
    )


@pytest.fixture
def sample_agent_output() -> AgentOutput:
    """Sample agent output for testing."""
    return AgentOutput(
        agent_id="technical_v1",
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        direction="BUY",
        score=0.75,
        confidence=0.80,
        features_used=["rsi_14", "macd_histogram", "ema_9"],
        shap_values={"rsi_14": 0.3, "macd_histogram": 0.2, "ema_9": 0.25},
        model_version="v1.0.0",
    )


@pytest.fixture
def sample_signal() -> Signal:
    """Sample signal for testing."""
    return Signal(
        id="test-signal-001",
        idempotency_key="abc123",
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        action="BUY",
        entry_price=50200.0,
        stop_loss=49600.0,
        take_profit=51700.0,
        risk_reward_ratio=2.0,
        confidence=0.75,
        explanation=[],
        summary="Strong buy signal with good risk/reward",
        regime=MarketRegime.BULL_TRENDING,
        strategy_id="technical_v1",
        status="pending",
    )


@pytest.fixture
def sample_portfolio() -> Portfolio:
    """Sample portfolio for testing."""
    return Portfolio(
        id="test-portfolio",
        total_capital=10000.0,
        available_capital=9000.0,
        positions=[
            Position(
                symbol="BTCUSDT",
                quantity=0.02,
                entry_price=50000.0,
                current_price=50200.0,
                unrealized_pnl=4.0,
                unrealized_pnl_pct=0.004,
                strategy_id="technical_v1",
                opened_at=datetime.utcnow(),
            )
        ],
        risk_exposure=0.02,
        daily_pnl=4.0,
        daily_pnl_pct=0.0004,
        total_pnl=4.0,
        drawdown_current=0.0,
        drawdown_max=0.0,
        updated_at=datetime.utcnow(),
    )


@pytest.fixture
def mock_kill_switch() -> KillSwitch:
    """Mock kill switch for testing."""
    ks = MagicMock(spec=KillSwitch)
    ks.is_active.return_value = False
    ks.state.triggered_by = None
    ks.state.active = False
    return ks


@pytest.fixture
def risk_manager(mock_settings, mock_kill_switch) -> RiskManager:
    """Risk manager fixture for testing."""
    return RiskManager(mock_settings, mock_kill_switch)


@pytest.fixture
def portfolio_manager(mock_settings) -> PortfolioManager:
    """Portfolio manager fixture for testing."""
    return PortfolioManager(
        settings=mock_settings,
        initial_capital=mock_settings.INITIAL_CAPITAL if hasattr(mock_settings, 'INITIAL_CAPITAL') else 10000.0
    )


@pytest.fixture
def order_tracker() -> OrderTracker:
    """Order tracker fixture for testing."""
    return OrderTracker()


@pytest.fixture
def paper_executor(order_tracker) -> PaperExecutor:
    """Paper executor fixture for testing."""
    return PaperExecutor(order_tracker=order_tracker)


@pytest.fixture
def technical_agent() -> TechnicalAgent:
    """Technical agent fixture for testing."""
    return TechnicalAgent(model_path="test_model.pkl")  # Non-existent path for rule-based mode


@pytest.fixture
def fundamental_agent() -> FundamentalAgent:
    """Fundamental agent fixture for testing."""
    return FundamentalAgent()


class AsyncContextManagerMock:
    """Mock for async context managers."""
    
    def __init__(self, return_value=None, side_effect=None):
        self.return_value = return_value
        self.side_effect = side_effect
        self.enter_called = False
        self.exit_called = False
    
    async def __aenter__(self):
        self.enter_called = True
        if self.side_effect:
            raise self.side_effect
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.exit_called = True
        return False


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for testing API calls."""
    client = AsyncMock()
    client.get = AsyncMock()
    client.post = AsyncMock()
    client.put = AsyncMock()
    client.delete = AsyncMock()
    return client


def create_mock_market_data_batch(count: int, base_price: float = 50000.0) -> list[MarketData]:
    """Create a batch of market data for testing."""
    data = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        price_variation = (i - count/2) * 10  # Small price variations
        data.append(MarketData(
            timestamp=base_time.replace(minute=i % 60, second=i % 60),
            symbol="BTCUSDT",
            open=Decimal(str(base_price + price_variation)),
            high=Decimal(str(base_price + price_variation + 100)),
            low=Decimal(str(base_price + price_variation - 100)),
            close=Decimal(str(base_price + price_variation + 50)),
            volume=Decimal("1000.0"),
            quote_volume=Decimal("50000000.0"),
            trades_count=5000,
            taker_buy_volume=Decimal("600.0"),
            source="binance",
            feature_version="v1",
        ))
    
    return data


def create_mock_feature_set_batch(count: int, trend: str = "bullish") -> list[FeatureSet]:
    """Create a batch of feature sets for testing."""
    features = []
    base_time = datetime.utcnow()
    
    for i in range(count):
        rsi = 45 + (10 if trend == "bullish" else -10) + (i % 10)
        features.append(FeatureSet(
            timestamp=base_time.replace(minute=i % 60, second=i % 60),
            symbol="BTCUSDT",
            version="v1",
            rsi_14=rsi,
            rsi_7=rsi - 5,
            macd_line=100.0 + i,
            macd_signal=50.0 + i/2,
            macd_histogram=50.0 + i/2,
            ema_9=50100.0 + i,
            ema_21=50000.0 + i,
            ema_50=49500.0 + i,
            ema_200=48000.0 + i,
            trend_direction=trend,
            atr_14=300.0,
            bb_upper=51000.0 + i,
            bb_lower=49000.0 + i,
            bb_width=2000.0,
            volatility_regime="medium",
            vwap=50000.0 + i,
            volume_sma_20=800.0,
            volume_ratio=1.25 + (i % 5) * 0.1,
            obv=1000000.0,
            close=50200.0 + i,
        ))
    
    return features
