"""
Module: core/strategies/meta_agent.py
Responsibility: ML model que selecciona la mejor estrategia para cada condición de mercado.
  Features del meta-modelo:
    - Régimen actual (HMM state probabilities)
    - Volatilidad realizada (20d, 60d)
    - Hurst exponent actual
    - Hora del día, día de la semana
    - Performance reciente de cada sub-modelo (rolling Sharpe 20 trades)
    - Correlación cross-asset (últimas 20 barras)
  Target: qué estrategia/modelo tuvo mejor Sharpe en las próximas 24 barras
  Validación: purged k-fold con embargo de 10 barras
Dependencies: sklearn, numpy, pandas
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from core.models import MarketRegime
from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class MetaAgentOutput:
    best_strategy: str
    best_model: Optional[str]
    risk_multiplier: float
    should_trade: bool
    confidence: float
    reasoning: str


class MetaAgentOrchestrator:
    """
    Meta-Agent que selecciona estrategia óptima basándose en condiciones de mercado.

    M4.2: Meta-Agente Selector.
    """

    def __init__(
        self,
        strategies: list[str],
        min_confidence: float = 0.5,
        risk_multiplier_range: tuple[float, float] = (0.5, 1.0),
    ):
        self._strategies = strategies
        self._min_confidence = min_confidence
        self._risk_min, self._risk_max = risk_multiplier_range
        self._strategy_sharpe_history: dict[str, list[float]] = {s: [] for s in strategies}

    def select_strategy(
        self,
        regime: MarketRegime,
        volatility_20d: float,
        volatility_60d: float,
        hurst: float,
        hour: int,
        day_of_week: int,
        strategy_sharpes: dict[str, float],
    ) -> MetaAgentOutput:
        """Seleccionar mejor estrategia basada en features de mercado."""
        should_trade = True
        reasoning_parts = []

        if regime == MarketRegime.VOLATILE_CRASH:
            should_trade = False
            reasoning_parts.append("CRISIS regime - no trading")

        if hurst > 0.6:
            best_strategy = "TSMOM"
            reasoning_parts.append(f"Hurst {hurst:.2f} > 0.6 → trending")
        elif hurst < 0.4:
            best_strategy = "StatisticalArbitrage"
            reasoning_parts.append(f"Hurst {hurst:.2f} < 0.4 → mean-reverting")
        else:
            best_strategy = self._select_by_sharpe(strategy_sharpes)
            reasoning_parts.append(f"Random walk - usar mejor sharpe")

        vol_ratio = volatility_20d / volatility_60d if volatility_60d > 0 else 1.0
        if vol_ratio > 1.5:
            risk_mult = self._risk_min
            reasoning_parts.append(f"Volatilidad en aumento - reducir riesgo")
        elif vol_ratio < 0.7:
            risk_mult = self._risk_max
            reasoning_parts.append(f"Volatilidad decreciendo - aumentar riesgo")
        else:
            risk_mult = (self._risk_min + self._risk_max) / 2
            reasoning_parts.append(f"Volatilidad estable - riesgo medio")

        if hour in [0, 1, 2, 3, 4, 5]:
            risk_mult *= 0.7
            reasoning_parts.append("Asian session - reducir exposición")

        confidence = self._calculate_confidence(regime, vol_ratio, hurst)

        return MetaAgentOutput(
            best_strategy=best_strategy,
            best_model=None,
            risk_multiplier=risk_mult,
            should_trade=should_trade and confidence >= self._min_confidence,
            confidence=confidence,
            reasoning=" | ".join(reasoning_parts),
        )

    def _select_by_sharpe(self, strategy_sharpes: dict[str, float]) -> str:
        """Seleccionar estrategia con mejor Sharpe reciente."""
        if not strategy_sharpes:
            return "TSMOM"
        return max(strategy_sharpes.items(), key=lambda x: x[1])[0]

    def _calculate_confidence(
        self, regime: MarketRegime, vol_ratio: float, hurst: float
    ) -> float:
        """Calcular confianza en la selección."""
        base_confidence = 0.5

        if regime in [MarketRegime.BULL_TRENDING, MarketRegime.BEAR_TRENDING]:
            base_confidence += 0.2

        if 0.4 <= hurst <= 0.6:
            base_confidence += 0.1

        if 0.8 <= vol_ratio <= 1.2:
            base_confidence += 0.1

        return min(1.0, base_confidence)

    def record_trade_result(self, strategy_id: str, sharpe: float) -> None:
        """Registrar resultado de trade para actualizar performance."""
        if strategy_id not in self._strategy_sharpe_history:
            self._strategy_sharpe_history[strategy_id] = []
        self._strategy_sharpe_history[strategy_id].append(sharpe)
        if len(self._strategy_sharpe_history[strategy_id]) > 20:
            self._strategy_sharpe_history[strategy_id] = self._strategy_sharpe_history[strategy_id][-20:]

    def get_strategy_sharpes(self) -> dict[str, float]:
        """Obtener Sharpe promedio reciente por estrategia."""
        result = {}
        for strategy, history in self._strategy_sharpe_history.items():
            if history:
                result[strategy] = np.mean(history)
        return result


class MetaAgentML(MetaAgentOrchestrator):
    """
    M4.2: Meta-agente con modelo ML (LogisticRegression) y fallback heurístico.
    """

    STRATEGY_LABELS = [
        "tsmom_v1",
        "vol_breakout_v1",
        "mean_rev_v1",
        "cross_sectional_v1",
    ]

    def __init__(self, **kwargs):
        super().__init__(
            strategies=kwargs.pop("strategies", self.STRATEGY_LABELS),
            **kwargs,
        )
        self._model = None
        self._label_to_id = {i: s for i, s in enumerate(self.STRATEGY_LABELS)}

    def _feature_vector(
        self,
        regime: MarketRegime,
        volatility_20d: float,
        volatility_60d: float,
        hurst: float,
        hour: int,
        day_of_week: int,
        strategy_sharpes: dict[str, float],
    ) -> np.ndarray:
        regime_code = list(MarketRegime).index(regime) if regime in MarketRegime else 0
        sharpes = [strategy_sharpes.get(s, 0.0) for s in self._strategies]
        vol_ratio = volatility_20d / volatility_60d if volatility_60d > 0 else 1.0
        return np.array(
            [regime_code, volatility_20d, volatility_60d, vol_ratio, hurst, hour, day_of_week]
            + sharpes,
            dtype=np.float32,
        )

    def train(self, X: np.ndarray, y: np.ndarray) -> None:
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler

        self._scaler = StandardScaler()
        Xs = self._scaler.fit_transform(X)
        self._model = LogisticRegression(max_iter=1000, multi_class="multinomial")
        self._model.fit(Xs, y)
        logger.info("meta_agent_ml_trained", samples=len(y))

    def select_strategy(
        self,
        regime: MarketRegime,
        volatility_20d: float,
        volatility_60d: float,
        hurst: float,
        hour: int,
        day_of_week: int,
        strategy_sharpes: dict[str, float],
    ) -> MetaAgentOutput:
        if self._model is None:
            return super().select_strategy(
                regime,
                volatility_20d,
                volatility_60d,
                hurst,
                hour,
                day_of_week,
                strategy_sharpes,
            )

        vec = self._feature_vector(
            regime,
            volatility_20d,
            volatility_60d,
            hurst,
            hour,
            day_of_week,
            strategy_sharpes,
        ).reshape(1, -1)
        Xs = self._scaler.transform(vec)
        pred = int(self._model.predict(Xs)[0])
        proba = float(np.max(self._model.predict_proba(Xs)))
        best_strategy = self._label_to_id.get(pred, self._strategies[0])

        base = super().select_strategy(
            regime,
            volatility_20d,
            volatility_60d,
            hurst,
            hour,
            day_of_week,
            strategy_sharpes,
        )
        return MetaAgentOutput(
            best_strategy=best_strategy,
            best_model="meta_logistic_v1",
            risk_multiplier=base.risk_multiplier,
            should_trade=base.should_trade and proba >= self._min_confidence,
            confidence=proba,
            reasoning=f"ML selection ({best_strategy}) | {base.reasoning}",
        )