"""
Tests for HMM Regime Detector.
M3.3: Hidden Markov Model con 8 estados.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from core.adaptation.hmm_regime_detector import (
    HMMRegime,
    HMMRegimeDetector,
    HMM_AVAILABLE,
)


class TestHMMRegimeDetector:
    """Test suite for HMMRegimeDetector."""

    @pytest.fixture
    def sample_data(self):
        """Generate synthetic market data."""
        np.random.seed(42)
        n_samples = 200

        timestamps = pd.date_range(start='2024-01-01', periods=n_samples, freq='1h')
        close = 50000 + np.cumsum(np.random.randn(n_samples) * 100)
        volume = np.random.randint(1000, 10000, n_samples)

        df = pd.DataFrame({
            'timestamp': timestamps,
            'close': close,
            'volume': volume,
            'volume_ratio': np.random.uniform(0.5, 2.0, n_samples),
            'adx_14': np.random.uniform(10, 40, n_samples),
            'hurst_exponent': np.random.uniform(0.3, 0.7, n_samples),
        })

        df['atr_14'] = df['close'].pct_change().abs().rolling(14).mean() * 100
        df['bb_upper'] = df['close'] * 1.02
        df['bb_lower'] = df['close'] * 0.98
        df['bb_middle'] = df['close']

        return df

    @pytest.fixture
    def detector(self):
        """Create HMM detector."""
        return HMMRegimeDetector(n_states=8, retrain_days=30)

    def test_init(self, detector):
        """Test detector initialization."""
        assert detector.n_states == 8
        assert detector.retrain_days == 30
        assert detector._model is None

    def test_regime_map(self, detector):
        """Test regime mapping."""
        assert len(detector._regime_map) == 8
        assert HMMRegime.TRANSITION in detector._regime_map.values()
        assert HMMRegime.CRISIS in detector._regime_map.values()

    @pytest.mark.skipif(not HMM_AVAILABLE, reason="hmmlearn not available")
    def test_prepare_features(self, detector, sample_data):
        """Test feature preparation."""
        X = detector._prepare_features(sample_data)

        assert X.shape[1] == 5
        assert len(X) == len(sample_data) - 1

    @pytest.mark.skipif(not HMM_AVAILABLE, reason="hmmlearn not available")
    def test_fit(self, detector, sample_data):
        """Test HMM fitting."""
        detector.fit(sample_data)

        assert detector._model is not None
        assert detector._last_train is not None

    @pytest.mark.skipif(not HMM_AVAILABLE, reason="hmmlearn not available")
    def test_predict(self, detector, sample_data):
        """Test regime prediction."""
        detector.fit(sample_data)
        predictions = detector.predict(sample_data)

        assert len(predictions) == len(sample_data) - 1
        assert all(isinstance(r, HMMRegime) for r in predictions)

    @pytest.mark.skipif(not HMM_AVAILABLE, reason="hmmlearn not available")
    def test_predict_current(self, detector, sample_data):
        """Test current regime prediction."""
        detector.fit(sample_data)
        current_regime = detector.predict_current(sample_data)

        assert isinstance(current_regime, HMMRegime)

    def test_should_trade_gate(self, detector):
        """Test should_trade gate - blocks CRISIS and TRANSITION."""
        assert detector.should_trade(HMMRegime.CRISIS) is False
        assert detector.should_trade(HMMRegime.TRANSITION) is False
        assert detector.should_trade(HMMRegime.BULL_TRENDING_STRONG) is True
        assert detector.should_trade(HMMRegime.BEAR_TRENDING_STRONG) is True
        assert detector.should_trade(HMMRegime.RANGE_BOUND_NARROW) is True

    def test_to_market_regime(self, detector):
        """Test conversion to MarketRegime."""
        from core.models import MarketRegime

        mapping = {
            HMMRegime.BULL_TRENDING_STRONG: MarketRegime.BULL_TRENDING,
            HMMRegime.BULL_TRENDING_WEAK: MarketRegime.BULL_TRENDING,
            HMMRegime.BEAR_TRENDING_STRONG: MarketRegime.BEAR_TRENDING,
            HMMRegime.BEAR_TRENDING_WEAK: MarketRegime.BEAR_TRENDING,
            HMMRegime.RANGE_BOUND_NARROW: MarketRegime.SIDEWAYS_LOW_VOL,
            HMMRegime.RANGE_BOUND_WIDE: MarketRegime.SIDEWAYS_HIGH_VOL,
            HMMRegime.TRANSITION: MarketRegime.SIDEWAYS_LOW_VOL,
            HMMRegime.CRISIS: MarketRegime.VOLATILE_CRASH,
        }

        for hmm_regime, expected in mapping.items():
            result = detector.to_market_regime(hmm_regime)
            assert result == expected

    @pytest.mark.skipif(not HMM_AVAILABLE, reason="hmmlearn not available")
    def test_fit_handles_nan(self, detector):
        """Test that fit handles NaN values gracefully."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=100, freq='1h'),
            'close': np.random.randn(100) * 100 + 50000,
            'volume': np.random.randint(1000, 10000, 100),
            'volume_ratio': np.random.uniform(0.5, 2.0, 100),
            'adx_14': np.random.uniform(10, 40, 100),
            'hurst_exponent': np.random.uniform(0.3, 0.7, 100),
            'atr_14': np.random.uniform(100, 500, 100),
            'bb_upper': np.random.uniform(51000, 52000, 100),
            'bb_lower': np.random.uniform(48000, 49000, 100),
            'bb_middle': np.random.uniform(49000, 51000, 100),
        })

        df.loc[50:55, 'close'] = np.nan

        detector.fit(df)

        assert detector._model is not None

    @pytest.mark.skipif(not HMM_AVAILABLE, reason="hmmlearn not available")
    def test_predict_with_insufficient_data(self, detector):
        """Test prediction with very small dataset."""
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=10, freq='1h'),
            'close': np.random.randn(10) * 100 + 50000,
            'volume': np.random.randint(1000, 10000, 10),
            'volume_ratio': np.random.uniform(0.5, 2.0, 10),
            'adx_14': np.random.uniform(10, 40, 10),
            'hurst_exponent': np.random.uniform(0.3, 0.7, 10),
            'atr_14': np.random.uniform(100, 500, 10),
            'bb_upper': np.random.uniform(51000, 52000, 10),
            'bb_lower': np.random.uniform(48000, 49000, 10),
            'bb_middle': np.random.uniform(49000, 51000, 10),
        })

        detector.fit(df)
        current = detector.predict_current(df)

        assert isinstance(current, HMMRegime)

    def test_fallback_when_hmm_unavailable(self):
        """Test fallback behavior when hmmlearn not available."""
        if HMM_AVAILABLE:
            pytest.skip("hmmlearn is available")

        detector = HMMRegimeDetector()
        assert detector._model is None

        df = pd.DataFrame({'timestamp': [], 'close': []})
        result = detector.predict_current(df)

        assert result == HMMRegime.TRANSITION


class TestHMMRegimeEnum:
    """Test suite for HMMRegime enum."""

    def test_all_regimes_defined(self):
        """Test all 8 regimes are defined."""
        expected_regimes = [
            'BULL_TRENDING_STRONG',
            'BULL_TRENDING_WEAK',
            'BEAR_TRENDING_STRONG',
            'BEAR_TRENDING_WEAK',
            'RANGE_BOUND_NARROW',
            'RANGE_BOUND_WIDE',
            'TRANSITION',
            'CRISIS',
        ]

        for name in expected_regimes:
            assert hasattr(HMMRegime, name)

    def test_regime_values(self):
        """Test regime enum values."""
        assert HMMRegime.BULL_TRENDING_STRONG.value == 'bull_trending_strong'
        assert HMMRegime.CRISIS.value == 'crisis'