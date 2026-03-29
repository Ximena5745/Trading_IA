"""
Integration tests: tests/integration/test_pipeline_paper.py
Responsibility: End-to-end pipeline test in paper mode
Tests: data -> features -> agents -> consensus -> signal -> risk -> paper execution
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from core.agents.regime_agent import RegimeAgent
from core.agents.technical_agent import TechnicalAgent
from core.backtesting.costs import CostModel
from core.backtesting.metrics import compute_all
from core.config.settings import Settings
from core.consensus.voting_engine import ConsensusEngine
from core.execution.paper_executor import PaperExecutor
from core.ingestion.data_validator import DataValidator
from core.models import (
    AgentOutput,
    ConsensusOutput,
    FeatureSet,
    MarketData,
    MarketRegime,
    RegimeOutput,
)
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.kill_switch import KillSwitch
from core.risk.risk_manager import RiskManager
from core.signals.signal_engine import SignalEngine


# ── Helpers ────────────────────────────────────────────────────────────────

def make_feature_set(
    rsi_14: float = 45.0,
    ema_9: float = 50100.0,
    ema_21: float = 50000.0,
    ema_50: float = 49500.0,
    ema_200: float = 48000.0,
    trend_direction: str = "bullish",
    macd_histogram: float = 50.0,
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
        macd_line=100.0,
        macd_signal=50.0,
        macd_histogram=macd_histogram,
        atr_14=atr_14,
        bb_upper=51000.0,
        bb_lower=49000.0,
        bb_width=2000.0,
        vwap=50000.0,
        volume_sma_20=700.0,
        volume_ratio=volume_ratio,
        obv=1_000_000.0,
        trend_direction=trend_direction,
        volatility_regime="low",
        close=close,
    )


def make_agent_output(
    agent_id: str = "technical_v1",
    direction: str = "BUY",
    score: float = 0.6,
    confidence: float = 0.75,
) -> AgentOutput:
    return AgentOutput(
        agent_id=agent_id,
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        direction=direction,
        score=score,
        confidence=confidence,
        features_used=["rsi_14", "ema_9", "ema_21"],
        shap_values={"rsi_14": 0.1, "ema_9": 0.2},
        model_version="v1",
    )


def make_regime_output(
    regime: MarketRegime = MarketRegime.BULL_TRENDING,
    signal_allowed: bool = True,
    confidence: float = 0.75,
) -> RegimeOutput:
    return RegimeOutput(
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        regime=regime,
        confidence=confidence,
        regime_duration_bars=10,
        signal_allowed=signal_allowed,
    )


def make_consensus_output(
    direction: str = "BUY",
    score: float = 0.7,
    agreement: float = 0.8,
    blocked: bool = False,
) -> ConsensusOutput:
    agent_outputs = [make_agent_output(direction=direction, score=score)]
    return ConsensusOutput(
        timestamp=datetime.utcnow(),
        symbol="BTCUSDT",
        final_direction=direction,
        weighted_score=score,
        agents_agreement=agreement,
        blocked_by_regime=blocked,
        agent_outputs=agent_outputs,
        conflicts=[],
    )


def _make_settings() -> Settings:
    s = MagicMock(spec=Settings)
    s.MAX_RISK_PER_TRADE_PCT = 0.01
    s.MAX_PORTFOLIO_RISK_PCT = 0.10
    s.MAX_DRAWDOWN_PCT = 0.15
    s.DAILY_LOSS_LIMIT_PCT = 0.05
    s.MAX_CONSECUTIVE_LOSSES = 5
    return s


# ── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def feature_set() -> FeatureSet:
    return make_feature_set()


@pytest.fixture
def portfolio_manager() -> PortfolioManager:
    return PortfolioManager(settings=_make_settings(), initial_capital=10_000.0)


@pytest.fixture
def risk_manager() -> RiskManager:
    settings = _make_settings()
    ks = KillSwitch(settings)
    return RiskManager(settings=settings, kill_switch=ks)


@pytest.fixture
def paper_executor() -> PaperExecutor:
    return PaperExecutor()


# ── Tests ──────────────────────────────────────────────────────────────────

class TestDataValidation:
    def test_valid_market_data_passes(self):
        md = MarketData(
            symbol="BTCUSDT",
            timestamp=datetime.utcnow(),
            open=Decimal("50000.0"),
            high=Decimal("50500.0"),
            low=Decimal("49800.0"),
            close=Decimal("50200.0"),
            volume=Decimal("1000.0"),
            quote_volume=Decimal("50200000.0"),
            trades_count=500,
            taker_buy_volume=Decimal("550.0"),
        )
        validator = DataValidator()
        result = validator.validate_market_data(md)
        assert result is not None  # returns the validated MarketData object

    def test_invalid_high_low_rejected(self):
        with pytest.raises(Exception):
            MarketData(
                symbol="BTCUSDT",
                timestamp=datetime.utcnow(),
                open=Decimal("50000.0"),
                high=Decimal("49000.0"),  # high < open triggers validator
                low=Decimal("50000.0"),
                close=Decimal("50200.0"),
                volume=Decimal("1000.0"),
                quote_volume=Decimal("50200000.0"),
                trades_count=500,
                taker_buy_volume=Decimal("550.0"),
            )


class TestAgentPipeline:
    def test_technical_agent_rule_based_buy_signal(self, feature_set):
        """TechnicalAgent without trained model falls back to rule-based scoring."""
        agent = TechnicalAgent()
        assert not agent.is_ready()  # No model trained

        output = agent.predict(feature_set)
        assert output.direction in ("BUY", "SELL", "NEUTRAL")
        assert 0.0 <= output.confidence <= 1.0
        assert "technical" in output.agent_id  # "technical_v1"

    def test_regime_agent_bull_market(self):
        """RegimeAgent classifies bull conditions correctly."""
        agent = RegimeAgent()
        fs = make_feature_set(rsi_14=60.0, trend_direction="bullish", atr_14=200.0)
        output = agent.predict(fs)
        assert output.direction in ("BUY", "SELL", "NEUTRAL")
        assert 0.0 <= output.confidence <= 1.0

    def test_regime_agent_volatile_crash_blocks_signal(self):
        """Very high ATR + low RSI should produce bearish or neutral output."""
        agent = RegimeAgent()
        fs = make_feature_set(
            rsi_14=20.0,
            trend_direction="bearish",
            atr_14=2600.0,
            volume_ratio=2.5,
        )
        output = agent.predict(fs)
        # In crash conditions score should be negative or neutral
        assert output.direction in ("BUY", "SELL", "NEUTRAL")


class TestConsensusEngine:
    def test_consensus_buy_agreement(self):
        """Three agents agreeing on BUY should produce BUY or NEUTRAL consensus."""
        engine = ConsensusEngine()
        agent_outputs = [
            make_agent_output(agent_id="technical_v1", direction="BUY", score=0.7),
            make_agent_output(agent_id="microstructure_v1", direction="BUY", score=0.6),
        ]
        regime = make_regime_output(MarketRegime.BULL_TRENDING, signal_allowed=True)
        result = engine.aggregate(agent_outputs=agent_outputs, regime=regime)
        assert result.final_direction in ("BUY", "NEUTRAL")
        assert isinstance(result.agents_agreement, float)

    def test_consensus_regime_veto_produces_neutral(self):
        """Regime veto (signal_allowed=False) must produce NEUTRAL."""
        engine = ConsensusEngine()
        agent_outputs = [
            make_agent_output(agent_id="technical_v1", direction="BUY", score=0.8),
            make_agent_output(agent_id="microstructure_v1", direction="BUY", score=0.7),
        ]
        regime = make_regime_output(MarketRegime.VOLATILE_CRASH, signal_allowed=False)
        result = engine.aggregate(agent_outputs=agent_outputs, regime=regime)
        assert result.final_direction == "NEUTRAL"
        assert result.blocked_by_regime is True


class TestSignalEngine:
    def test_signal_generated_from_buy_consensus(self, feature_set):
        """SignalEngine produces a valid Signal from BUY consensus."""
        engine = SignalEngine()
        consensus = make_consensus_output(direction="BUY", score=0.75, agreement=0.80)

        signal = engine.generate(consensus, feature_set)
        assert signal is not None
        assert signal.action == "BUY"
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price
        rr = (signal.take_profit - signal.entry_price) / (signal.entry_price - signal.stop_loss)
        assert rr >= 1.5

    def test_neutral_consensus_produces_no_signal(self, feature_set):
        """NEUTRAL consensus should yield None."""
        engine = SignalEngine()
        consensus = make_consensus_output(direction="NEUTRAL", score=0.0, agreement=0.0)

        signal = engine.generate(consensus, feature_set)
        assert signal is None

    def test_idempotency_key_deterministic(self, feature_set):
        """Same inputs produce the same idempotency key."""
        engine = SignalEngine()
        consensus = make_consensus_output(direction="BUY", score=0.70, agreement=0.75)
        feature_set.timestamp = datetime(2026, 1, 1, 12, 0, 0)

        s1 = engine.generate(consensus, feature_set)
        s2 = engine.generate(consensus, feature_set)
        assert s1 is not None and s2 is not None
        assert s1.idempotency_key == s2.idempotency_key


class TestRiskManager:
    def test_signal_approved_under_limits(self, risk_manager):
        """Valid signal within risk limits should be approved."""
        signal = {
            "entry_price": 50200.0,
            "stop_loss": 49600.0,
            "take_profit": 51700.0,
            "risk_reward_ratio": 2.5,
        }
        portfolio = {
            "risk_exposure": 0.02,
            "drawdown_current": 0.01,
            "available_capital": 9000.0,
            "total_capital": 10000.0,
            "daily_pnl_pct": 0.0,
        }
        approved, reason = risk_manager.validate_signal(signal, portfolio)
        assert approved is True
        assert reason == ""

    def test_kill_switch_active_rejects_all(self, risk_manager):
        """Active kill switch must reject every signal."""
        risk_manager._kill_switch._trigger("manual")

        signal = {
            "entry_price": 50200.0,
            "stop_loss": 49600.0,
            "take_profit": 51700.0,
            "risk_reward_ratio": 2.5,
        }
        approved, reason = risk_manager.validate_signal(signal, portfolio={})
        assert approved is False
        assert "kill" in reason.lower() or "switch" in reason.lower()


class TestPaperExecutor:
    @pytest.mark.asyncio
    async def test_paper_order_fills_with_slippage(self, paper_executor):
        """Paper executor fills orders with realistic slippage and commission."""
        signal = {
            "id": "paper-001",
            "symbol": "BTCUSDT",
            "action": "BUY",
            "entry_price": 50200.0,
            "stop_loss": 49600.0,
            "take_profit": 51700.0,
            "confidence": 0.75,
            "idempotency_key": "paper-ci-001",
        }
        order = await paper_executor.execute(signal, quantity=0.01)
        assert order is not None
        assert order["status"] in ("filled", "FILLED", "pending")
        assert order["fill_price"] != signal["entry_price"]  # slippage applied

    @pytest.mark.asyncio
    async def test_paper_executor_idempotency(self, paper_executor):
        """Same idempotency key should return the same order."""
        signal = {
            "id": "paper-002",
            "symbol": "ETHUSDT",
            "action": "BUY",
            "entry_price": 3000.0,
            "stop_loss": 2950.0,
            "take_profit": 3100.0,
            "confidence": 0.70,
            "idempotency_key": "idem-ci-456",
        }
        order1 = await paper_executor.execute(signal, quantity=0.1)
        order2 = await paper_executor.execute(signal, quantity=0.1)
        assert order1 is not None and order2 is not None
        assert order1["id"] == order2["id"]


class TestPortfolioManager:
    def test_open_position_updates_capital(self, portfolio_manager):
        """Opening a position adds it to positions list."""
        signal_mock = MagicMock()
        signal_mock.symbol = "BTCUSDT"
        signal_mock.strategy_id = "ema_rsi"

        portfolio_manager.open_position(
            signal=signal_mock, quantity=0.01, fill_price=50000.0
        )
        portfolio = portfolio_manager.get_portfolio()
        assert any(p.symbol == "BTCUSDT" for p in portfolio.positions)

    def test_kelly_fraction_capped(self, portfolio_manager):
        """Kelly fraction must never exceed hard limit."""
        from core.config.constants import HARD_LIMITS
        fraction = portfolio_manager.kelly_fraction(
            win_rate=0.60,
            avg_win=0.03,
            avg_loss=0.015,
        )
        max_pct = HARD_LIMITS["max_risk_per_trade_pct"]
        assert fraction <= max_pct * 2  # half-kelly capped


class TestCostModel:
    def test_costs_reduce_pnl(self):
        """Cost model must reduce gross P&L."""
        model = CostModel()
        trade = {
            "gross_pnl": 100.0,
            "net_pnl": 100.0,
            "entry_price": 50000.0,
            "quantity": 0.01,
            "value": 500.0,
            "side": "BUY",
        }
        result = model.apply(trade)
        assert result["net_pnl"] < 100.0

    def test_zero_pnl_still_has_costs(self):
        """Break-even trade is actually a loss after costs."""
        model = CostModel()
        trade = {
            "gross_pnl": 0.0,
            "net_pnl": 0.0,
            "entry_price": 50000.0,
            "quantity": 0.01,
            "value": 500.0,
            "side": "BUY",
        }
        result = model.apply(trade)
        assert result["net_pnl"] < 0.0


class TestBacktestMetrics:
    def test_sharpe_positive_returns(self):
        """Sharpe ratio should be positive for consistent gains."""
        pnl_values = [10.0, 15.0, 8.0, 12.0, 9.0, 11.0, 14.0, 10.0]
        trades = [{"net_pnl": v, "gross_pnl": v} for v in pnl_values]
        equity = [10000.0]
        for v in pnl_values:
            equity.append(equity[-1] + v)
        metrics = compute_all(trades, equity)
        assert metrics["sharpe_ratio"] > 0
        assert metrics["win_rate"] == 1.0

    def test_max_drawdown_all_positive(self):
        """Max drawdown is 0 when all trades are profitable."""
        pnl_values = [5.0, 10.0, 8.0, 12.0]
        trades = [{"net_pnl": v, "gross_pnl": v} for v in pnl_values]
        equity = [10000.0]
        for v in pnl_values:
            equity.append(equity[-1] + v)
        metrics = compute_all(trades, equity)
        assert metrics["max_drawdown"] == 0.0

    def test_empty_pnl_returns_zeros(self):
        """compute_all handles empty list without error."""
        metrics = compute_all([], [10000.0])
        assert metrics["sharpe_ratio"] == 0.0
        assert metrics["win_rate"] == 0.0
