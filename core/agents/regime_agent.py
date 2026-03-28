"""
Module: core/agents/regime_agent.py
Responsibility: Market regime classification (5 states) using HMM or Random Forest
Dependencies: hmmlearn/sklearn, base_agent, models, logger
"""

from __future__ import annotations

import os
import pickle

import numpy as np

from core.agents.base_agent import AbcAgent
from core.exceptions import AgentPredictionError
from core.models import AgentOutput, FeatureSet, MarketRegime, RegimeOutput
from core.observability.logger import get_logger

logger = get_logger(__name__)

REGIME_FEATURES = ["atr_14", "bb_width", "volume_ratio", "rsi_14", "macd_histogram"]
MIN_CONFIDENCE = 0.50


class RegimeAgent(AbcAgent):
    """
    5-state market regime classifier.
    When confidence < 0.5 or VOLATILE_CRASH → signal_allowed = False.
    """

    agent_id = "regime_v1"
    model_version = "v1.0.0"

    def __init__(self, model_path: str = "data/models/regime_agent_v1.pkl"):
        self._model_path = model_path
        self._model = None
        self._load_model()
        self._regime_history: list[MarketRegime] = []

    def _load_model(self) -> None:
        if os.path.exists(self._model_path):
            try:
                with open(self._model_path, "rb") as f:
                    self._model = pickle.load(f)
                logger.info("regime_agent_loaded", path=self._model_path)
            except Exception as e:
                logger.warning("regime_agent_load_failed", error=str(e))

    def is_ready(self) -> bool:
        return True  # rule-based fallback always available

    def predict(self, features: FeatureSet) -> AgentOutput:
        try:
            regime_output = self.classify_regime(features)
            score = self._regime_to_score(regime_output.regime)
            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=features.timestamp,
                symbol=features.symbol,
                direction=(
                    "NEUTRAL"
                    if not regime_output.signal_allowed
                    else self._regime_direction(regime_output.regime)
                ),
                score=score,
                confidence=regime_output.confidence,
                features_used=REGIME_FEATURES,
                shap_values={f: 0.0 for f in REGIME_FEATURES},
                model_version=self.model_version,
            )
        except Exception as e:
            raise AgentPredictionError(f"RegimeAgent prediction failed: {e}") from e

    def classify_regime(self, features: FeatureSet) -> RegimeOutput:
        if self._model is not None:
            return self._classify_with_model(features)
        return self._classify_rule_based(features)

    def _classify_rule_based(self, features: FeatureSet) -> RegimeOutput:
        """Rule-based regime classification as fallback."""
        atr_pct = features.atr_14 / features.close if features.close > 0 else 0
        prev = self._regime_history[-1] if self._regime_history else None

        if atr_pct > 0.05 and features.volume_ratio > 2.0:
            regime = MarketRegime.VOLATILE_CRASH
            confidence = 0.85
        elif features.trend_direction == "bullish" and features.rsi_14 > 50:
            regime = MarketRegime.BULL_TRENDING
            confidence = 0.70
        elif features.trend_direction == "bearish" and features.rsi_14 < 50:
            regime = MarketRegime.BEAR_TRENDING
            confidence = 0.70
        elif features.volatility_regime in ("high", "extreme"):
            regime = MarketRegime.SIDEWAYS_HIGH_VOL
            confidence = 0.60
        else:
            regime = MarketRegime.SIDEWAYS_LOW_VOL
            confidence = 0.60

        # Count duration
        duration = 1
        for r in reversed(self._regime_history):
            if r == regime:
                duration += 1
            else:
                break

        self._regime_history.append(regime)
        if len(self._regime_history) > 100:
            self._regime_history.pop(0)

        signal_allowed = (
            regime != MarketRegime.VOLATILE_CRASH and confidence >= MIN_CONFIDENCE
        )

        return RegimeOutput(
            timestamp=features.timestamp,
            symbol=features.symbol,
            regime=regime,
            confidence=confidence,
            regime_duration_bars=duration,
            previous_regime=prev,
            signal_allowed=signal_allowed,
        )

    def _classify_with_model(self, features: FeatureSet) -> RegimeOutput:
        X = np.array([[getattr(features, f) for f in REGIME_FEATURES]])
        pred = self._model.predict(X)[0]
        proba = self._model.predict_proba(X)[0]
        regime = MarketRegime(pred)
        confidence = float(max(proba))
        signal_allowed = (
            regime != MarketRegime.VOLATILE_CRASH and confidence >= MIN_CONFIDENCE
        )
        prev = self._regime_history[-1] if self._regime_history else None
        self._regime_history.append(regime)
        return RegimeOutput(
            timestamp=features.timestamp,
            symbol=features.symbol,
            regime=regime,
            confidence=confidence,
            regime_duration_bars=1,
            previous_regime=prev,
            signal_allowed=signal_allowed,
        )

    @staticmethod
    def _regime_to_score(regime: MarketRegime) -> float:
        scores = {
            MarketRegime.BULL_TRENDING: 0.7,
            MarketRegime.BEAR_TRENDING: -0.7,
            MarketRegime.SIDEWAYS_LOW_VOL: 0.0,
            MarketRegime.SIDEWAYS_HIGH_VOL: -0.2,
            MarketRegime.VOLATILE_CRASH: -1.0,
        }
        return scores.get(regime, 0.0)

    @staticmethod
    def _regime_direction(regime: MarketRegime) -> str:
        if regime == MarketRegime.BULL_TRENDING:
            return "BUY"
        if regime == MarketRegime.BEAR_TRENDING:
            return "SELL"
        return "NEUTRAL"
