"""
Module: core/agents/regime_agent.py
Responsibility: Market regime classification (5-8 states) using HMM or Random Forest
M3.3: Integrated HMM with 8 states for regime detection
Dependencies: hmmlearn/sklearn, base_agent, models, logger
"""
from __future__ import annotations

import os
import pickle
from collections import deque
from datetime import datetime

import numpy as np
import pandas as pd

from core.agents.base_agent import AbcAgent
from core.exceptions import AgentPredictionError
from core.models import AgentOutput, FeatureSet, MarketRegime, RegimeOutput
from core.observability.logger import get_logger
from core.adaptation.hmm_regime_detector import HMMRegimeDetector, HMM_AVAILABLE

logger = get_logger(__name__)

REGIME_FEATURES = ["atr_14", "bb_width", "volume_ratio", "rsi_14", "macd_histogram"]
MIN_CONFIDENCE = 0.50
HMM_MIN_SAMPLES = 100


class RegimeAgent(AbcAgent):
    """
    5-8 state market regime classifier using HMM.
    M3.3: Uses HMMRegimeDetector with 8 states when available.
    When confidence < 0.5 or CRISIS/TRANSITION → signal_allowed = False.
    """

    agent_id = "regime_v1"
    model_version = "v2.0.0"

    def __init__(self, model_path: str = "data/models/regime_agent_v1.pkl"):
        self._model_path = model_path
        self._model = None
        self._load_model()
        self._regime_history: list[MarketRegime] = []
        self._hmm_detector: HMMRegimeDetector | None = None
        self._hmm_buffer: deque = deque(maxlen=500)
        self._hmm_ready = False
        if HMM_AVAILABLE:
            self._hmm_detector = HMMRegimeDetector(n_states=8)
            logger.info("hmm_regime_detector_initialized", n_states=8)

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

            # FASE E — LOW_LIQUIDITY: log warning, do NOT block (decision v2.4)
            self._check_low_liquidity(features.symbol)

            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=features.timestamp,
                symbol=features.symbol,
                direction="NEUTRAL"
                if not regime_output.signal_allowed
                else self._regime_direction(regime_output.regime),
                score=score,
                confidence=regime_output.confidence,
                features_used=REGIME_FEATURES,
                shap_values={f: 0.0 for f in REGIME_FEATURES},
                model_version=self.model_version,
            )
        except Exception as e:
            raise AgentPredictionError(f"RegimeAgent prediction failed: {e}") from e

    def _check_low_liquidity(self, symbol: str) -> None:
        """Log warning if Asian session only (LOW_LIQUIDITY) — does NOT block."""
        try:
            from core.ingestion.market_calendar import get_calendar

            calendar = get_calendar()
            if calendar.is_low_liquidity(symbol):
                logger.warning(
                    "LOW_LIQUIDITY",
                    symbol=symbol,
                    session="asian",
                    note="signals allowed per decision v2.4 — monitor spread widening",
                )
        except Exception:
            pass  # calendar not available in crypto-only mode

    def classify_regime(self, features: FeatureSet) -> RegimeOutput:
        self._update_hmm_buffer(features)
        if self._hmm_detector is not None and self._hmm_ready:
            return self._classify_with_hmm(features)
        if self._model is not None:
            return self._classify_with_model(features)
        return self._classify_rule_based(features)

    def _update_hmm_buffer(self, features: FeatureSet) -> None:
        """Add feature to HMM buffer and train if enough samples."""
        self._hmm_buffer.append({
            "timestamp": features.timestamp,
            "close": features.close,
            "atr_14": features.atr_14,
            "bb_width": features.bb_width,
            "volume_ratio": features.volume_ratio,
            "rsi_14": features.rsi_14,
            "macd_histogram": features.macd_histogram,
        })
        if len(self._hmm_buffer) >= HMM_MIN_SAMPLES and not self._hmm_ready:
            self._train_hmm()

    def _train_hmm(self) -> None:
        """Train HMM on buffered data."""
        if self._hmm_detector is None or len(self._hmm_buffer) < HMM_MIN_SAMPLES:
            return
        try:
            df = pd.DataFrame(list(self._hmm_buffer))
            if "timestamp" in df.columns and "close" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                df = df.set_index("timestamp").sort_index()
                df["close"] = pd.to_numeric(df["close"], errors="coerce")
                df["atr_14"] = pd.to_numeric(df["atr_14"], errors="coerce")
                df["bb_width"] = pd.to_numeric(df["bb_width"], errors="coerce")
                df["volume_ratio"] = pd.to_numeric(df["volume_ratio"], errors="coerce")
                df["rsi_14"] = pd.to_numeric(df["rsi_14"], errors="coerce")
                df["macd_histogram"] = pd.to_numeric(df["macd_histogram"], errors="coerce")
                df = df.dropna()
                if len(df) >= HMM_MIN_SAMPLES:
                    df["adx_14"] = 20.0
                    df["hurst_exponent"] = 0.5
                    self._hmm_detector.fit(df)
                    self._hmm_ready = True
                    logger.info("hmm_trained_in_regime_agent", samples=len(df))
        except Exception as e:
            logger.warning("hmm_training_failed_in_agent", error=str(e))

    def _classify_with_hmm(self, features: FeatureSet) -> RegimeOutput:
        """Classify using HMM when available and trained."""
        try:
            df = pd.DataFrame([{
                "timestamp": features.timestamp,
                "close": features.close,
                "atr_14": features.atr_14,
                "bb_width": features.bb_width,
                "volume_ratio": features.volume_ratio,
                "rsi_14": features.rsi_14,
                "macd_histogram": features.macd_histogram,
                "adx_14": 20.0,
                "hurst_exponent": 0.5,
            }])
            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.set_index("timestamp").sort_index()
            for col in ["close", "atr_14", "bb_width", "volume_ratio", "rsi_14", "macd_histogram"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            hmm_regime = self._hmm_detector.predict_current(df)
            market_regime = self._hmm_regime_to_market_regime(hmm_regime)
            confidence = 0.75 if self._hmm_ready else 0.50
            should_trade = self._hmm_detector.should_trade(hmm_regime)
            prev = self._regime_history[-1] if self._regime_history else None
            self._regime_history.append(market_regime)
            if len(self._regime_history) > 100:
                self._regime_history.pop(0)
            return RegimeOutput(
                timestamp=features.timestamp,
                symbol=features.symbol,
                regime=market_regime,
                confidence=confidence,
                regime_duration_bars=self._count_regime_duration(market_regime),
                previous_regime=prev,
                signal_allowed=should_trade and confidence >= MIN_CONFIDENCE,
            )
        except Exception as e:
            logger.warning("hmm_classification_failed_using_fallback", error=str(e))
            return self._classify_rule_based(features)

    def _hmm_regime_to_market_regime(self, hmm_regime) -> MarketRegime:
        """Convert HMMRegime to MarketRegime."""
        from core.adaptation.hmm_regime_detector import HMMRegime as HMMRegimeEnum
        mapping = {
            HMMRegimeEnum.BULL_TRENDING_STRONG: MarketRegime.BULL_TRENDING,
            HMMRegimeEnum.BULL_TRENDING_WEAK: MarketRegime.BULL_TRENDING,
            HMMRegimeEnum.BEAR_TRENDING_STRONG: MarketRegime.BEAR_TRENDING,
            HMMRegimeEnum.BEAR_TRENDING_WEAK: MarketRegime.BEAR_TRENDING,
            HMMRegimeEnum.RANGE_BOUND_NARROW: MarketRegime.SIDEWAYS_LOW_VOL,
            HMMRegimeEnum.RANGE_BOUND_WIDE: MarketRegime.SIDEWAYS_HIGH_VOL,
            HMMRegimeEnum.TRANSITION: MarketRegime.SIDEWAYS_LOW_VOL,
            HMMRegimeEnum.CRISIS: MarketRegime.VOLATILE_CRASH,
        }
        return mapping.get(hmm_regime, MarketRegime.SIDEWAYS_LOW_VOL)

    def _count_regime_duration(self, regime: MarketRegime) -> int:
        """Count consecutive bars in current regime."""
        duration = 1
        for r in reversed(self._regime_history):
            if r == regime:
                duration += 1
            else:
                break
        return duration

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
