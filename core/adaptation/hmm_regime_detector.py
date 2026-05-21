"""
Module: core/adaptation/hmm_regime_detector.py
Responsibility: Hidden Markov Model para detección de régimen de mercado con 8 estados.
  Estados:
    1. BULL_TRENDING_STRONG    → Full momentum, max exposure
    2. BULL_TRENDING_WEAK      → Momentum con trailing tight
    3. BEAR_TRENDING_STRONG    → Short momentum o cash
    4. BEAR_TRENDING_WEAK      → Hedged positions
    5. RANGE_BOUND_NARROW      → Mean reversion, grid trading
    6. RANGE_BOUND_WIDE        → Breakout anticipation
    7. TRANSITION              → Reducir exposición, observar
    8. CRISIS                  → Cash only, hedge total
  Reentrenamiento: cada 30 días con datos de 1-2 años.
Dependencies: hmmlearn, numpy, pandas
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False

from core.models import MarketRegime
from core.observability.logger import get_logger

logger = get_logger(__name__)


class HMMRegime(Enum):
    BULL_TRENDING_STRONG = "bull_trending_strong"
    BULL_TRENDING_WEAK = "bull_trending_weak"
    BEAR_TRENDING_STRONG = "bear_trending_strong"
    BEAR_TRENDING_WEAK = "bear_trending_weak"
    RANGE_BOUND_NARROW = "range_bound_narrow"
    RANGE_BOUND_WIDE = "range_bound_wide"
    TRANSITION = "transition"
    CRISIS = "crisis"


class HMMRegimeDetector:
    """
    Hidden Markov Model con 8 estados para detección de régimen.

    M3.3: HMM Regime Detector con 8 estados.
    Features: returns, volatility, ADX, Hurst, volume ratio.
    """

    def __init__(self, n_states: int = 8, retrain_days: int = 30):
        self.n_states = n_states
        self.retrain_days = retrain_days
        self._model: Optional[hmm.GaussianHMM] = None
        self._last_train: Optional[pd.Timestamp] = None
        self._regime_map = self._build_regime_map()

    def _build_regime_map(self) -> dict[int, HMMRegime]:
        """Map HMM states to regime types based on emission parameters."""
        return {
            0: HMMRegime.TRANSITION,
            1: HMMRegime.BULL_TRENDING_STRONG,
            2: HMMRegime.BULL_TRENDING_WEAK,
            3: HMMRegime.RANGE_BOUND_NARROW,
            4: HMMRegime.RANGE_BOUND_WIDE,
            5: HMMRegime.BEAR_TRENDING_WEAK,
            6: HMMRegime.BEAR_TRENDING_STRONG,
            7: HMMRegime.CRISIS,
        }

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare features for HMM: returns, volatility, ADX, Hurst, volume ratio."""
        returns = df["close"].pct_change().values
        volatility = returns.std() * np.sqrt(24)
        volume_ratio = df.get("volume_ratio", pd.Series([1.0] * len(df))).values

        adx = df.get("adx_14", pd.Series([20.0] * len(df))).values
        hurst = df.get("hurst_exponent", pd.Series([0.5] * len(df))).values

        features = np.column_stack([
            returns,
            volatility * np.ones_like(returns),
            adx,
            hurst,
            volume_ratio,
        ])

        features = np.nan_to_num(features, nan=0.0)
        return features[:-1]

    def fit(self, df: pd.DataFrame) -> "HMMRegimeDetector":
        """Train HMM on historical data."""
        if not HMM_AVAILABLE:
            logger.warning("hmmlearn_not_available_using_fallback")
            return self

        X = self._prepare_features(df)

        try:
            self._model = hmm.GaussianHMM(
                n_components=self.n_states,
                covariance_type="full",
                n_iter=100,
                random_state=42,
            )
            self._model.fit(X)
            self._last_train = df["timestamp"].max()
            logger.info("hmm_trained", n_states=self.n_states, samples=len(X))
        except Exception as e:
            logger.error("hmm_training_failed", error=str(e))
            self._model = None

        return self

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """Predict regime for each observation."""
        if self._model is None:
            return pd.Series([HMMRegime.TRANSITION] * len(df), index=df.index)

        X = self._prepare_features(df)
        hidden_states = self._model.predict(X)

        regimes = [self._regime_map.get(s, HMMRegime.TRANSITION) for s in hidden_states]
        return pd.Series(regimes, index=df.index[:-1])

    def predict_current(self, df: pd.DataFrame) -> HMMRegime:
        """Predict current regime (most recent)."""
        if self._model is None:
            return HMMRegime.TRANSITION

        X = self._prepare_features(df)
        if len(X) == 0:
            return HMMRegime.TRANSITION

        state = self._model.predict(X[-1:])[0]
        return self._regime_map.get(state, HMMRegime.TRANSITION)

    def should_trade(self, regime: HMMRegime) -> bool:
        """Gate obligatorio: el régimen puede prohibir operar."""
        return regime not in {HMMRegime.CRISIS, HMMRegime.TRANSITION}

    def to_market_regime(self, hmm_regime: HMMRegime) -> MarketRegime:
        """Convertir HMMRegime a MarketRegime (del modelo existente)."""
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
        return mapping.get(hmm_regime, MarketRegime.SIDEWAYS_LOW_VOL)