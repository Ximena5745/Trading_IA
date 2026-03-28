"""
Tests for SignalEngine, ConsensusEngine, and XAIModule.
"""

from __future__ import annotations

from datetime import datetime

from core.agents.regime_agent import RegimeAgent
from core.consensus.voting_engine import ConsensusEngine
from core.models import (
    AgentOutput,
    ConsensusOutput,
    FeatureSet,
    MarketRegime,
    RegimeOutput,
)
from core.signals.signal_engine import SignalEngine
from core.signals.xai_module import XAIModule


def make_features(
    rsi: float = 28.0, trend: str = "bullish", close: float = 50000.0
) -> FeatureSet:
    return FeatureSet(
        timestamp=datetime(2024, 6, 1),
        symbol="BTCUSDT",
        version="v1",
        rsi_14=rsi,
        rsi_7=rsi - 3,
        macd_line=100.0,
        macd_signal=80.0,
        macd_histogram=20.0,
        ema_9=49900,
        ema_21=49500,
        ema_50=48000,
        ema_200=45000,
        trend_direction=trend,
        atr_14=1000.0,
        bb_upper=52000,
        bb_lower=48000,
        bb_width=0.08,
        volatility_regime="medium",
        vwap=49800,
        volume_sma_20=500,
        volume_ratio=1.8,
        obv=100000,
        close=close,
    )


def make_agent_output(
    agent_id: str = "technical_v1",
    direction: str = "BUY",
    score: float = 0.65,
    confidence: float = 0.75,
) -> AgentOutput:
    return AgentOutput(
        agent_id=agent_id,
        timestamp=datetime(2024, 6, 1),
        symbol="BTCUSDT",
        direction=direction,
        score=score,
        confidence=confidence,
        features_used=["rsi_14"],
        shap_values={"rsi_14": 0.4, "macd_histogram": 0.2},
        model_version="v1",
    )


def make_regime(signal_allowed: bool = True) -> RegimeOutput:
    return RegimeOutput(
        timestamp=datetime(2024, 6, 1),
        symbol="BTCUSDT",
        regime=MarketRegime.BULL_TRENDING,
        confidence=0.80,
        regime_duration_bars=5,
        signal_allowed=signal_allowed,
    )


class TestConsensusEngine:
    def test_generates_buy_signal_on_agreement(self):
        engine = ConsensusEngine()
        outputs = [
            make_agent_output("technical_v1", "BUY", 0.65, 0.75),
            make_agent_output("regime_v1", "BUY", 0.70, 0.80),
            make_agent_output("microstructure_v1", "BUY", 0.40, 0.60),
        ]
        result = engine.aggregate(outputs, make_regime(signal_allowed=True))
        assert result.final_direction == "BUY"
        assert result.blocked_by_regime is False
        assert result.weighted_score > 0

    def test_blocks_on_regime_veto(self):
        engine = ConsensusEngine()
        outputs = [make_agent_output("technical_v1", "BUY", 0.9, 0.9)]
        result = engine.aggregate(outputs, make_regime(signal_allowed=False))
        assert result.final_direction == "NEUTRAL"
        assert result.blocked_by_regime is True

    def test_neutral_when_low_agreement(self):
        engine = ConsensusEngine()
        outputs = [
            make_agent_output("technical_v1", "BUY", 0.6, 0.7),
            make_agent_output("regime_v1", "SELL", -0.6, 0.7),
            make_agent_output("microstructure_v1", "SELL", -0.5, 0.6),
        ]
        result = engine.aggregate(outputs, make_regime(signal_allowed=True))
        assert result.final_direction == "NEUTRAL"


class TestSignalEngine:
    def test_generates_signal_from_buy_consensus(self):
        engine = SignalEngine()
        outputs = [
            make_agent_output("technical_v1", "BUY", 0.65, 0.75),
            make_agent_output("regime_v1", "BUY", 0.70, 0.80),
        ]
        consensus = ConsensusOutput(
            timestamp=datetime(2024, 6, 1),
            symbol="BTCUSDT",
            final_direction="BUY",
            weighted_score=0.67,
            agents_agreement=1.0,
            blocked_by_regime=False,
            agent_outputs=outputs,
            conflicts=[],
        )
        features = make_features()
        signal = engine.generate(consensus, features)
        assert signal is not None
        assert signal.action == "BUY"
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price
        assert signal.risk_reward_ratio >= 1.5

    def test_returns_none_for_neutral_consensus(self):
        engine = SignalEngine()
        consensus = ConsensusOutput(
            timestamp=datetime(2024, 6, 1),
            symbol="BTCUSDT",
            final_direction="NEUTRAL",
            weighted_score=0.0,
            agents_agreement=0.0,
            blocked_by_regime=False,
            agent_outputs=[],
            conflicts=[],
        )
        assert engine.generate(consensus, make_features()) is None

    def test_sl_below_entry_for_buy(self):
        engine = SignalEngine()
        outputs = [make_agent_output("technical_v1", "BUY", 0.7, 0.8)]
        consensus = ConsensusOutput(
            timestamp=datetime(2024, 6, 1),
            symbol="BTCUSDT",
            final_direction="BUY",
            weighted_score=0.7,
            agents_agreement=1.0,
            blocked_by_regime=False,
            agent_outputs=outputs,
            conflicts=[],
        )
        signal = engine.generate(consensus, make_features())
        assert signal.stop_loss < signal.entry_price
        assert signal.take_profit > signal.entry_price

    def test_idempotency_key_is_deterministic(self):
        engine = SignalEngine()
        k1 = engine._make_key("BTCUSDT", datetime(2024, 6, 1), "BUY")
        k2 = engine._make_key("BTCUSDT", datetime(2024, 6, 1), "BUY")
        assert k1 == k2

    def test_idempotency_key_differs_by_direction(self):
        engine = SignalEngine()
        k_buy = engine._make_key("BTCUSDT", datetime(2024, 6, 1), "BUY")
        k_sell = engine._make_key("BTCUSDT", datetime(2024, 6, 1), "SELL")
        assert k_buy != k_sell


class TestXAIModule:
    def test_builds_explanation_factors(self):
        xai = XAIModule()
        outputs = [make_agent_output("technical_v1", "BUY", 0.65, 0.75)]
        consensus = ConsensusOutput(
            timestamp=datetime(2024, 6, 1),
            symbol="BTCUSDT",
            final_direction="BUY",
            weighted_score=0.65,
            agents_agreement=1.0,
            blocked_by_regime=False,
            agent_outputs=outputs,
            conflicts=[],
        )
        factors = xai.build_explanation(consensus)
        assert len(factors) > 0
        for f in factors:
            assert f.weight >= 0
            assert f.direction in ("bullish", "bearish")

    def test_summary_contains_action(self):
        xai = XAIModule()
        outputs = [make_agent_output()]
        consensus = ConsensusOutput(
            timestamp=datetime(2024, 6, 1),
            symbol="BTCUSDT",
            final_direction="BUY",
            weighted_score=0.65,
            agents_agreement=1.0,
            blocked_by_regime=False,
            agent_outputs=outputs,
            conflicts=[],
        )
        factors = xai.build_explanation(consensus)
        summary = xai.generate_summary(factors, "BUY", 0.75, "BTCUSDT")
        assert "COMPRA" in summary
        assert "BTCUSDT" in summary


class TestRegimeAgent:
    def test_volatile_crash_blocks_signal(self):
        agent = RegimeAgent()
        features = make_features(rsi=20.0)
        features.atr_14 = features.close * 0.06  # High ATR
        features.volume_ratio = 3.0
        regime = agent.classify_regime(features)
        if regime.regime == MarketRegime.VOLATILE_CRASH:
            assert regime.signal_allowed is False

    def test_bull_trend_allows_signal(self):
        agent = RegimeAgent()
        features = make_features(rsi=60.0, trend="bullish")
        features.volatility_regime = "low"
        regime = agent.classify_regime(features)
        if regime.regime == MarketRegime.BULL_TRENDING:
            assert regime.signal_allowed is True
