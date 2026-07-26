"""
Tests for improved TechnicalAgent with M3.1 enhancements.
M3.1: Bayesian HP search, early stopping by Sharpe, SHAP integration.
"""
from __future__ import annotations

import os
import pickle
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from core.agents.technical_agent import TechnicalAgent


class TestTechnicalAgentImproved:
    """Test suite for improved TechnicalAgent."""

    @pytest.fixture
    def sample_data(self):
        """Generate synthetic training data."""
        np.random.seed(42)
        n_samples = 500
        n_features = 17

        X = np.random.randn(n_samples, n_features)
        y = np.random.choice([0, 1, 2], n_samples)

        return X, y

    @pytest.fixture
    def agent(self, tmp_path):
        """Create TechnicalAgent with temporary model path."""
        model_path = tmp_path / "test_model.pkl"
        agent = TechnicalAgent(model_path=str(model_path))
        return agent

    def test_train_with_default_params(self, agent, sample_data):
        """Test basic training with default parameters."""
        X, y = sample_data

        result = agent.train(X, y, use_three_class=True, use_sharpe_early_stopping=False)

        assert agent._model is not None
        assert agent._explainer is not None
        assert result['n_samples'] == len(X)
        assert result['n_classes'] == 3

    def test_train_with_best_params(self, agent, sample_data):
        """Test training with Optuna-optimized parameters."""
        X, y = sample_data

        best_params = {
            'n_estimators': 200,
            'max_depth': 7,
            'learning_rate': 0.03,
            'num_leaves': 31,
            'min_child_samples': 30,
            'reg_alpha': 0.1,
            'reg_lambda': 0.1,
        }

        result = agent.train(
            X, y,
            use_three_class=True,
            best_params=best_params,
            use_sharpe_early_stopping=False,
        )

        assert agent._model is not None
        assert result['best_params'] == best_params
        assert result['shap_saved'] is True

    def test_train_with_sharpe_early_stopping(self, agent, sample_data):
        """Test training with Sharpe-based early stopping."""
        X, y = sample_data

        result = agent.train(
            X, y,
            use_three_class=True,
            use_sharpe_early_stopping=True,
        )

        assert agent._model is not None
        assert hasattr(agent._model, 'best_iteration_')

    def test_train_saves_model_and_explainer(self, agent, sample_data, tmp_path):
        """Test that model and explainer are saved to disk."""
        X, y = sample_data

        agent.train(X, y, use_sharpe_early_stopping=False)

        assert os.path.exists(agent._model_path)

        with open(agent._model_path, 'rb') as f:
            payload = pickle.load(f)

        assert 'model' in payload
        assert 'explainer' in payload
        assert 'best_params' in payload

    def test_predict_after_training(self, agent, sample_data):
        """Test prediction after training."""
        X, y = sample_data
        agent.train(X, y, use_sharpe_early_stopping=False)

        from core.models import FeatureSet
        from datetime import datetime

        features = FeatureSet(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            rsi_14=50.0,
            rsi_7=50.0,
            ema_9=50000.0,
            ema_21=50000.0,
            ema_50=50000.0,
            ema_200=50000.0,
            macd_line=0.0,
            macd_signal=0.0,
            macd_histogram=0.0,
            atr_14=500.0,
            bb_upper=51000.0,
            bb_lower=49000.0,
            bb_width=0.04,
            vwap=50000.0,
            volume_sma_20=1000.0,
            volume_ratio=1.0,
            obv=0.0,
            trend_direction="neutral",
            volatility_regime="medium",
        )

        output = agent.predict(features)

        assert output.agent_id == "technical_v1"
        assert output.direction in ["BUY", "SELL", "NEUTRAL"]
        assert 0 <= output.confidence <= 1
        assert output.score is not None

    def test_validate_with_purged_kfold(self, agent, sample_data):
        """Test PurgedKFold validation."""
        X, y = sample_data

        result = agent.validate_with_purged_kfold(X, y, n_splits=3)

        assert 'mean_accuracy' in result
        assert 'std_accuracy' in result
        assert 'per_fold' in result
        assert len(result['per_fold']) == 3

    def test_explain_prediction(self, agent, sample_data):
        """Test SHAP explanation generation."""
        X, y = sample_data
        agent.train(X, y, use_sharpe_early_stopping=False)

        X_sample = X[:5]
        explanation = agent.explain_prediction(X_sample)

        assert 'feature_importance' in explanation or 'error' in explanation

    def test_train_with_binary_class(self, agent, sample_data):
        """Test training with binary classification."""
        X, y = sample_data

        y_binary = (y > 0).astype(int)

        result = agent.train(
            X, y_binary,
            use_three_class=False,
            use_sharpe_early_stopping=False,
        )

        assert result['n_classes'] == 2

    def test_fallback_when_model_not_loaded(self, tmp_path):
        """Test fallback rule-based prediction when no model."""
        model_path = tmp_path / "nonexistent.pkl"
        agent = TechnicalAgent(model_path=str(model_path))

        from core.models import FeatureSet
        from datetime import datetime

        features = FeatureSet(
            timestamp=datetime.now(),
            symbol="BTCUSDT",
            rsi_14=20.0,
            rsi_7=20.0,
            ema_9=49000.0,
            ema_21=49000.0,
            ema_50=49000.0,
            ema_200=49000.0,
            macd_line=0.0,
            macd_signal=0.0,
            macd_histogram=100.0,
            atr_14=500.0,
            bb_upper=51000.0,
            bb_lower=49000.0,
            bb_width=0.04,
            vwap=50000.0,
            volume_sma_20=1000.0,
            volume_ratio=2.0,
            obv=0.0,
            trend_direction="bullish",
            volatility_regime="medium",
        )

        output = agent.predict(features)

        assert output.direction == "BUY"
        assert output.score > 0

    def test_is_ready_method(self, agent, sample_data):
        """Test is_ready() method."""
        assert agent.is_ready() is False

        X, y = sample_data
        agent.train(X, y, use_sharpe_early_stopping=False)

        assert agent.is_ready() is True

    def test_calculate_sharpe_internal(self, agent):
        """Test internal Sharpe calculation."""
        y_true = np.array([1, -1, 1, -1, 1])
        y_pred = np.array([0.8, -0.6, 0.9, -0.7, 0.5])

        sharpe = agent._calculate_sharpe(y_true, y_pred)

        assert isinstance(sharpe, float)
        assert not np.isnan(sharpe)

    def test_train_invalid_params(self, agent, sample_data):
        """Test training with invalid params handles gracefully."""
        X, y = sample_data

        invalid_params = {
            'n_estimators': -1,
            'learning_rate': 0.0,
        }

        with pytest.raises(Exception):
            agent.train(
                X, y,
                best_params=invalid_params,
                use_sharpe_early_stopping=False,
            )