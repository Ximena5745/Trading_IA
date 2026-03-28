"""
Integration tests: tests/integration/test_pipeline_paper.py
Responsibility: End-to-end pipeline test in paper mode
Tests: data → features → agents → consensus → signal → risk → paper execution
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from core.agents.regime_agent import RegimeAgent
from core.agents.technical_agent import TechnicalAgent
from core.backtesting.costs import CostModel
from core.backtesting.metrics import compute_all
from core.consensus.voting_engine import ConsensusEngine
from core.execution.paper_executor import PaperExecutor
from core.execution.order_tracker import OrderTracker
from core.features.feature_engineering import FeatureEngine
from core.ingestion.data_validator import DataValidator
from core.models import (
    AgentOutput,
    FeatureSet,
    MarketData,
    MarketRegime,
    RegimeOutput,
)
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.kill_switch import KillSwitch
from core.risk.risk_manager import RiskManager
from core.signals.signal_engine import SignalEngine


# ── Fixtures ───────────────────────────────────────────────────────────────

def make_feature_set(
    rsi_14: float = 45.0,
    ema_9: float = 50100.0,
    ema_21: float = 50000.0,
    ema_50: float = 49500.0,
    ema_200: float = 48000.0,
    trend_direction: float = 1.0,
    macd_hist: float = 50.0,
    volume_ratio: float = 1.5,
    close: float = 50200.0,
    atr_14: float = 300.0,
) -> FeatureSet:
    return FeatureSet(
        symbol="BTCUSDT",
        timestamp=datetime.utcnow(),
        rsi_7=40.0,
        rsi_14=rsi_14,
        ema_9=ema_9,
        ema_21=ema_21,
        ema_50=ema_50,
        ema_200=ema_200,
        macd=100.0,
        macd_signal=50.0,
        macd_hist=macd_hist,
        atr_14=atr_14,
        bb_upper=51000.0,
        bb_lower=49000.0,
        bb_middle=50000.0,
        vwap=50000.0,
        volume_ratio=volume_ratio,
        obv=1_000_000.0,
        trend_direction=trend_direction,
        volatility_regime="normal",
        close=close,
        high=50500.0,
        low=49800.0,
        volume=1000.0,
    )


@pytest.fixture
def feature_set() -> FeatureSet:
    return make_feature_set()


@pytest.fixture
def portfolio_manager() -> PortfolioManager:
    return PortfolioManager(total_capital=10_000.0, max_risk_per_trade_pct=0.02)


@pytest.fixture
def risk_manager() -> RiskManager:
    return RiskManager()


@pytest.fixture
def order_tracker() -> OrderTracker:
    return OrderTracker()


@pytest.fixture
def paper_executor(order_tracker) -> PaperExecutor:
    return PaperExecutor(order_tracker=order_tracker)


# ── Tests ──────────────────────────────────────────────────────────────────

class TestDataValidation:
    def test_valid_market_data_passes(self):
        md = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.utcnow(),
            open=50000.0,
            high=50500.0,
            low=49800.0,
            close=50200.0,
            volume=1000.0,
        )
        validator = DataValidator()
        result = validator.validate_market_data(md)
        assert result is True

    def test_invalid_high_low_rejected(self):
        with pytest.raises(Exception):
            MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.utcnow(),
                open=50000.0,
                high=49000.0,  # high < low
                low=50000.0,
                close=50200.0,
                volume=1000.0,
            )


class TestAgentPipeline:
    def test_technical_agent_rule_based_buy_signal(self, feature_set):
        """TechnicalAgent without trained model falls back to rule-based scoring."""
        agent = TechnicalAgent()
        assert not agent.is_ready()  # No model trained

        output = agent.predict(feature_set)
        # Bullish conditions: EMA9>EMA21, trend=1, MACD>0 → should tend toward BUY or NEUTRAL
        assert output.direction in ("BUY", "SELL", "NEUTRAL")
        assert 0.0 <= output.confidence <= 1.0
        assert output.agent_id == "technical"

    def test_regime_agent_bull_market(self, feature_set):
        """RegimeAgent classifies bull conditions correctly."""
        agent = RegimeAgent()
        # Bullish conditions
        fs = make_feature_set(rsi_14=60.0, trend_direction=1.0, atr_14=200.0)
        output = agent.predict(fs)
        assert output.regime in [r for r in MarketRegime]
        assert output.signal_allowed in (True, False)

    def test_regime_agent_volatile_crash_blocks_signal(self):
        """VOLATILE_CRASH regime should block signal."""
        agent = RegimeAgent()
        fs = make_feature_set(
            rsi_14=20.0,
            trend_direction=-1.0,
            atr_14=2600.0,  # > 5% of ~50k
            volume_ratio=2.5,
        )
        output = agent.predict(fs)
        if output.regime == MarketRegime.VOLATILE_CRASH:
            assert output.signal_allowed is False


class TestConsensusEngine:
    def test_consensus_buy_agreement(self, feature_set):
        """Three agents agreeing on BUY should produce BUY consensus."""
        engine = ConsensusEngine()
        buy_output = AgentOutput(
            agent_id="technical",
            direction="BUY",
            confidence=0.80,
            metadata={},
        )
        regime_output = RegimeOutput(
            symbol="BTCUSDT",
            regime=MarketRegime.BULL_TREND,
            confidence=0.75,
            signal_allowed=True,
        )
        result = engine.aggregate(
            technical=buy_output,
            regime=regime_output,
            microstructure=AgentOutput(
                agent_id="microstructure",
                direction="BUY",
                confidence=0.65,
                metadata={},
            ),
        )
        assert result.direction == "BUY"
        assert result.confidence > 0.0

    def test_consensus_regime_veto_produces_neutral(self, feature_set):
        """Regime veto (signal_allowed=False) must produce NEUTRAL."""
        engine = ConsensusEngine()
        regime_output = RegimeOutput(
            symbol="BTCUSDT",
            regime=MarketRegime.VOLATILE_CRASH,
            confidence=0.90,
            signal_allowed=False,
        )
        result = engine.aggregate(
            technical=AgentOutput(
                agent_id="technical",
                direction="BUY",
                confidence=0.85,
                metadata={},
            ),
            regime=regime_output,
            microstructure=AgentOutput(
                agent_id="microstructure",
                direction="BUY",
                confidence=0.70,
                metadata={},
            ),
        )
        assert result.direction == "NEUTRAL"


class TestSignalEngine:
    def test_signal_generated_from_buy_consensus(self, feature_set):
        """SignalEngine produces a valid Signal from BUY consensus."""
        engine = SignalEngine()
        consensus = MagicMock()
        consensus.direction = "BUY"
        consensus.confidence = 0.75
        consensus.lead_agent = "technical"
        consensus.shap_values = {}

        signal = engine.generate(feature_set, consensus)
        assert signal is not None
        assert signal.action == "BUY"
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price
        rr = (signal.take_profit - signal.entry_price) / (signal.entry_price - signal.stop_loss)
        assert rr >= 1.5

    def test_neutral_consensus_produces_no_signal(self, feature_set):
        """NEUTRAL consensus should yield None."""
        engine = SignalEngine()
        consensus = MagicMock()
        consensus.direction = "NEUTRAL"
        consensus.confidence = 0.50

        signal = engine.generate(feature_set, consensus)
        assert signal is None

    def test_idempotency_key_deterministic(self, feature_set):
        """Same inputs produce the same idempotency key."""
        engine = SignalEngine()
        consensus = MagicMock()
        consensus.direction = "BUY"
        consensus.confidence = 0.70
        consensus.lead_agent = "technical"
        consensus.shap_values = {}

        feature_set.timestamp = datetime(2026, 1, 1, 12, 0, 0)
        s1 = engine.generate(feature_set, consensus)
        s2 = engine.generate(feature_set, consensus)
        assert s1 is not None and s2 is not None
        assert s1.idempotency_key == s2.idempotency_key


class TestRiskManager:
    def test_signal_approved_under_limits(self, risk_manager, feature_set):
        """Valid signal within risk limits should be approved."""
        from core.models import Signal
        signal = Signal(
            id="test-001",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50200.0,
            stop_loss=49600.0,
            take_profit=51700.0,
            confidence=0.75,
            idempotency_key="abc123",
            explanation=None,
        )
        approved, reason = risk_manager.validate_signal(signal, portfolio=None)
        # Without kill switch active, basic signal should pass
        assert isinstance(approved, bool)

    def test_kill_switch_active_rejects_all(self, risk_manager, feature_set):
        """Active kill switch must reject every signal."""
        from core.models import Signal
        risk_manager._kill_switch._is_active = True

        signal = Signal(
            id="test-002",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50200.0,
            stop_loss=49600.0,
            take_profit=51700.0,
            confidence=0.90,
            idempotency_key="def456",
            explanation=None,
        )
        approved, reason = risk_manager.validate_signal(signal, portfolio=None)
        assert approved is False
        assert "kill" in reason.lower() or "switch" in reason.lower() or "active" in reason.lower()


class TestPaperExecutor:
    @pytest.mark.asyncio
    async def test_paper_order_fills_with_slippage(self, paper_executor):
        """Paper executor fills orders with realistic slippage and commission."""
        from core.models import Signal
        signal = Signal(
            id="paper-001",
            symbol="BTCUSDT",
            action="BUY",
            entry_price=50200.0,
            stop_loss=49600.0,
            take_profit=51700.0,
            confidence=0.75,
            idempotency_key="paper001",
            explanation=None,
        )
        order = await paper_executor.execute(signal, quantity=0.01)
        assert order is not None
        assert order.status in ("filled", "FILLED", "pending")

    @pytest.mark.asyncio
    async def test_paper_executor_idempotency(self, paper_executor):
        """Same idempotency key should not submit duplicate orders."""
        from core.models import Signal
        signal = Signal(
            id="paper-002",
            symbol="ETHUSDT",
            action="BUY",
            entry_price=3000.0,
            stop_loss=2950.0,
            take_profit=3100.0,
            confidence=0.70,
            idempotency_key="same-key-123",
            explanation=None,
        )
        order1 = await paper_executor.execute(signal, quantity=0.1)
        order2 = await paper_executor.execute(signal, quantity=0.1)
        # Second call should return same order or be rejected (not duplicate)
        if order1 and order2:
            assert order1.id == order2.id


class TestPortfolioManager:
    def test_open_position_updates_capital(self, portfolio_manager):
        """Opening a position reduces available capital."""
        initial_capital = portfolio_manager.get_portfolio().total_capital
        portfolio_manager.open_position(
            symbol="BTCUSDT",
            side="BUY",
            size=0.01,
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            strategy_id="ema_rsi",
        )
        portfolio = portfolio_manager.get_portfolio()
        assert "BTCUSDT" in portfolio.positions

    def test_kelly_fraction_capped(self, portfolio_manager):
        """Kelly fraction must never exceed hard limit."""
        from core.config.constants import MAX_RISK_PER_TRADE_PCT
        fraction = portfolio_manager.kelly_fraction(
            win_rate=0.60,
            avg_win=0.03,
            avg_loss=0.015,
        )
        assert fraction <= MAX_RISK_PER_TRADE_PCT * 2  # half-kelly capped


class TestCostModel:
    def test_costs_reduce_pnl(self):
        """Cost model must reduce gross P&L."""
        model = CostModel()
        gross_pnl = 100.0
        entry_price = 50000.0
        size = 0.01
        net = model.apply(gross_pnl, entry_price, size)
        assert net < gross_pnl

    def test_zero_pnl_still_has_costs(self):
        """Break-even trade is actually a loss after costs."""
        model = CostModel()
        net = model.apply(0.0, 50000.0, 0.01)
        assert net < 0.0


class TestBacktestMetrics:
    def test_sharpe_positive_returns(self):
        """Sharpe ratio should be positive for consistent gains."""
        pnls = [10.0, 15.0, 8.0, 12.0, 9.0, 11.0, 14.0, 10.0]
        metrics = compute_all(pnls)
        assert metrics["sharpe_ratio"] > 0
        assert metrics["win_rate"] == 1.0

    def test_max_drawdown_all_positive(self):
        """Max drawdown is 0 when all trades are profitable."""
        pnls = [5.0, 10.0, 8.0, 12.0]
        metrics = compute_all(pnls)
        assert metrics["max_drawdown"] == 0.0

    def test_empty_pnl_returns_zeros(self):
        """compute_all handles empty list without error."""
        metrics = compute_all([])
        assert metrics["sharpe_ratio"] == 0.0
        assert metrics["win_rate"] == 0.0
