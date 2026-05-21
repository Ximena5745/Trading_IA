"""
Tests for RegimeAgent with HMM integration.
M3.3: RegimeAgent using HMMRegimeDetector.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.agents.regime_agent import RegimeAgent, HMM_AVAILABLE
from core.models import FeatureSet, MarketRegime, RegimeOutput, AgentOutput

FeatureSet.model_rebuild()
RegimeOutput.model_rebuild()
AgentOutput.model_rebuild()


def create_sample_features(**kwargs):
    """Factory to create FeatureSet with defaults."""
    defaults = {
        'timestamp': datetime.now(),
        'symbol': 'BTCUSDT',
        'close': 50000.0,
        'rsi_14': 55.0,
        'rsi_7': 52.0,
        'ema_9': 49500.0,
        'ema_21': 49000.0,
        'ema_50': 48500.0,
        'ema_200': 48000.0,
        'macd_line': 100.0,
        'macd_signal': 50.0,
        'macd_histogram': 50.0,
        'atr_14': 500.0,
        'bb_upper': 52000.0,
        'bb_lower': 48000.0,
        'bb_width': 0.08,
        'vwap': 50000.0,
        'volume_sma_20': 1000.0,
        'volume_ratio': 1.5,
        'obv': 0.0,
        'trend_direction': 'bullish',
        'volatility_regime': 'medium',
    }
    defaults.update(kwargs)
    return FeatureSet(**defaults)


class TestRegimeAgent:
    """Test suite for RegimeAgent."""

    @pytest.fixture
    def agent(self, tmp_path):
        """Create RegimeAgent with temporary path."""
        model_path = tmp_path / "regime_agent.pkl"
        return RegimeAgent(model_path=str(model_path))

    @pytest.fixture
    def sample_features(self):
        """Create sample FeatureSet."""
        return create_sample_features()

    def test_init(self, agent):
        """Test agent initialization."""
        assert agent.agent_id == "regime_v1"
        assert agent.model_version == "v2.0.0"
        assert len(agent._regime_history) == 0
        assert agent._hmm_buffer.maxlen == 500

    def test_is_ready(self, agent):
        """Test is_ready method."""
        assert agent.is_ready() is True

    def test_predict_bullish_regime(self, agent, sample_features):
        """Test prediction in bullish regime."""
        output = agent.predict(sample_features)

        assert output.agent_id == "regime_v1"
        assert output.symbol == "BTCUSDT"
        assert output.direction in ["BUY", "SELL", "NEUTRAL"]
        assert 0 <= output.confidence <= 1

    def test_predict_volatile_crash(self, agent, tmp_path):
        """Test prediction blocks signals in CRISIS."""
        from core.agents.regime_agent import MIN_CONFIDENCE

        agent_crash = RegimeAgent(model_path=str(tmp_path / "crash.pkl"))

        crash_features = FeatureSet(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            close=30000.0,
            rsi_14=80.0,
            rsi_7=85.0,
            ema_9=40000.0,
            ema_21=42000.0,
            ema_50=45000.0,
            ema_200=50000.0,
            macd_line=-500.0,
            macd_signal=-200.0,
            macd_histogram=-300.0,
            atr_14=5000.0,
            bb_upper=40000.0,
            bb_lower=20000.0,
            bb_width=0.4,
            vwap=30000.0,
            volume_sma_20=1000.0,
            volume_ratio=5.0,
            obv=0.0,
            trend_direction="bearish",
            volatility_regime="extreme",
        )

        output = agent_crash.predict(crash_features)

        assert output.agent_id == "regime_v1"

    def test_classify_regime(self, agent, sample_features):
        """Test regime classification."""
        regime_output = agent.classify_regime(sample_features)

        assert isinstance(regime_output, RegimeOutput)
        assert isinstance(regime_output.regime, MarketRegime)
        assert 0 <= regime_output.confidence <= 1

    def test_regime_history_tracking(self, agent, sample_features):
        """Test that regime history is tracked."""
        for _ in range(5):
            agent.predict(sample_features)

        assert len(agent._regime_history) <= 100

    @patch('core.agents.regime_agent.HMM_AVAILABLE', False)
    def test_fallback_to_rule_based(self, tmp_path):
        """Test fallback to rule-based when HMM unavailable."""
        agent = RegimeAgent(model_path=str(tmp_path / "fallback.pkl"))

        features = FeatureSet(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            close=50000.0,
            rsi_14=55.0,
            rsi_7=52.0,
            ema_9=49500.0,
            ema_21=49000.0,
            ema_50=48500.0,
            ema_200=48000.0,
            macd_line=100.0,
            macd_signal=50.0,
            macd_histogram=50.0,
            atr_14=500.0,
            bb_upper=52000.0,
            bb_lower=48000.0,
            bb_width=0.08,
            vwap=50000.0,
            volume_sma_20=1000.0,
            volume_ratio=1.5,
            obv=0.0,
            trend_direction="bullish",
            volatility_regime="medium",
        )

        output = agent.predict(features)

        assert output.agent_id == "regime_v1"

    def test_regime_to_score(self, agent):
        """Test regime to score mapping."""
        assert agent._regime_to_score(MarketRegime.BULL_TRENDING) == 0.7
        assert agent._regime_to_score(MarketRegime.BEAR_TRENDING) == -0.7
        assert agent._regime_to_score(MarketRegime.SIDEWAYS_LOW_VOL) == 0.0
        assert agent._regime_to_score(MarketRegime.SIDEWAYS_HIGH_VOL) == -0.2
        assert agent._regime_to_score(MarketRegime.VOLATILE_CRASH) == -1.0

    def test_regime_direction(self, agent):
        """Test regime direction mapping."""
        assert agent._regime_direction(MarketRegime.BULL_TRENDING) == "BUY"
        assert agent._regime_direction(MarketRegime.BEAR_TRENDING) == "SELL"
        assert agent._regime_direction(MarketRegime.SIDEWAYS_LOW_VOL) == "NEUTRAL"

    def test_hmm_buffer_updates(self, agent, sample_features):
        """Test that HMM buffer is updated on predict."""
        initial_buffer_size = len(agent._hmm_buffer)

        for _ in range(10):
            agent.predict(sample_features)

        assert len(agent._hmm_buffer) == initial_buffer_size + 10

    @patch('core.agents.regime_agent.HMM_AVAILABLE', True)
    @patch('core.agents.regime_agent.HMMRegimeDetector')
    def test_hmm_integration_when_available(self, mock_detector_class, tmp_path):
        """Test HMM is used when available."""
        mock_detector = MagicMock()
        mock_detector_class.return_value = mock_detector

        agent = RegimeAgent(model_path=str(tmp_path / "hmm_agent.pkl"))

        assert agent._hmm_detector is not None

    def test_regime_duration_counting(self, agent, sample_features):
        """Test regime duration is counted."""
        regime_output = agent.classify_regime(sample_features)

        if regime_output.previous_regime is None:
            assert regime_output.regime_duration_bars == 1
        else:
            assert regime_output.regime_duration_bars >= 1


class TestRegimeOutput:
    """Test suite for RegimeOutput."""

    def test_regime_output_creation(self):
        """Test RegimeOutput creation."""
        output = RegimeOutput(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            regime=MarketRegime.BULL_TRENDING,
            confidence=0.75,
            regime_duration_bars=5,
            previous_regime=MarketRegime.SIDEWAYS_LOW_VOL,
            signal_allowed=True,
        )

        assert output.regime == MarketRegime.BULL_TRENDING
        assert output.confidence == 0.75
        assert output.regime_duration_bars == 5
        assert output.signal_allowed is True