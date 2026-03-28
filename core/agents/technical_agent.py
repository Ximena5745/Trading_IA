"""
Module: core/agents/technical_agent.py
Responsibility: LightGBM model over technical features with SHAP explanations
Dependencies: lightgbm, shap, base_agent, models, logger
"""
from __future__ import annotations

import os
import pickle
from datetime import datetime
from typing import Optional

import numpy as np

from core.agents.base_agent import AbcAgent
from core.exceptions import AgentPredictionError
from core.models import AgentOutput, FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)

FEATURE_ORDER = [
    "rsi_14", "rsi_7",
    "ema_9", "ema_21", "ema_50", "ema_200",
    "macd_line", "macd_signal", "macd_histogram",
    "atr_14", "bb_upper", "bb_lower", "bb_width",
    "vwap", "volume_sma_20", "volume_ratio", "obv",
]

SCORE_THRESHOLD = 0.30


class TechnicalAgent(AbcAgent):
    """
    LightGBM trained on technical features.
    Target: sign of next candle return.
    Score range: -1.0 (strong sell) to +1.0 (strong buy).
    """

    agent_id = "technical_v1"
    model_version = "v1.0.0"

    def __init__(self, model_path: str = "data/models/technical_agent_v1.pkl"):
        self._model_path = model_path
        self._model = None
        self._explainer = None
        self._load_model()

    def _load_model(self) -> None:
        if os.path.exists(self._model_path):
            try:
                with open(self._model_path, "rb") as f:
                    payload = pickle.load(f)
                    self._model = payload.get("model")
                    self._explainer = payload.get("explainer")
                logger.info("technical_agent_loaded", path=self._model_path)
            except Exception as e:
                logger.warning("technical_agent_load_failed", error=str(e))

    def is_ready(self) -> bool:
        return self._model is not None

    def predict(self, features: FeatureSet) -> AgentOutput:
        try:
            feature_vector = self._features_to_array(features)

            if self._model is not None:
                score = self._predict_with_model(feature_vector)
                shap_values = self._compute_shap(feature_vector)
            else:
                # Fallback: rule-based score when model not trained yet
                score = self._rule_based_score(features)
                shap_values = self._rule_based_shap(features)

            direction = self._score_to_direction(score)
            confidence = min(abs(score) * 1.5, 1.0)

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=features.timestamp,
                symbol=features.symbol,
                direction=direction,
                score=round(score, 4),
                confidence=round(confidence, 4),
                features_used=FEATURE_ORDER,
                shap_values=shap_values,
                model_version=self.model_version,
            )
        except Exception as e:
            raise AgentPredictionError(f"TechnicalAgent prediction failed: {e}") from e

    def _features_to_array(self, features: FeatureSet) -> np.ndarray:
        return np.array([[getattr(features, f) for f in FEATURE_ORDER]], dtype=np.float32)

    def _predict_with_model(self, X: np.ndarray) -> float:
        proba = self._model.predict_proba(X)[0]
        # Class 0 = SELL, Class 1 = BUY → score in [-1, 1]
        return float(proba[1] - proba[0])

    def _compute_shap(self, X: np.ndarray) -> dict[str, float]:
        if self._explainer is None:
            return {f: 0.0 for f in FEATURE_ORDER}
        try:
            shap_vals = self._explainer.shap_values(X)
            values = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]
            return {f: round(float(v), 6) for f, v in zip(FEATURE_ORDER, values)}
        except Exception:
            return {f: 0.0 for f in FEATURE_ORDER}

    def _rule_based_score(self, features: FeatureSet) -> float:
        """Simple rule-based fallback when model is not trained."""
        score = 0.0
        # RSI signals
        if features.rsi_14 < 30:
            score += 0.4
        elif features.rsi_14 > 70:
            score -= 0.4
        # Trend
        if features.trend_direction == "bullish":
            score += 0.3
        elif features.trend_direction == "bearish":
            score -= 0.3
        # MACD
        if features.macd_histogram > 0:
            score += 0.2
        else:
            score -= 0.2
        # Volume confirmation
        if features.volume_ratio > 1.5:
            score *= 1.2
        return max(-1.0, min(1.0, score))

    def _rule_based_shap(self, features: FeatureSet) -> dict[str, float]:
        rsi_contrib = 0.4 if features.rsi_14 < 30 else (-0.4 if features.rsi_14 > 70 else 0.0)
        macd_contrib = 0.2 if features.macd_histogram > 0 else -0.2
        return {
            "rsi_14": round(rsi_contrib, 6),
            "macd_histogram": round(macd_contrib, 6),
            **{f: 0.0 for f in FEATURE_ORDER if f not in ("rsi_14", "macd_histogram")},
        }

    @staticmethod
    def _score_to_direction(score: float) -> str:
        if score >= SCORE_THRESHOLD:
            return "BUY"
        if score <= -SCORE_THRESHOLD:
            return "SELL"
        return "NEUTRAL"

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        """Train a new LightGBM model. Called by AdaptationEngine."""
        try:
            import lightgbm as lgb
            import shap

            self._model = lgb.LGBMClassifier(
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                min_child_samples=20,
                random_state=42,
            )
            self._model.fit(X, y)
            self._explainer = shap.TreeExplainer(self._model)

            os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
            with open(self._model_path, "wb") as f:
                pickle.dump({"model": self._model, "explainer": self._explainer}, f)
            logger.info("technical_agent_trained", samples=len(X), path=self._model_path)
        except Exception as e:
            raise AgentPredictionError(f"TechnicalAgent training failed: {e}") from e
