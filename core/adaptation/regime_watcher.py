"""
Module: core/adaptation/regime_watcher.py
Responsibility: Detect regime changes that trigger retraining
Dependencies: models, logger
"""

from __future__ import annotations

from collections import deque
from datetime import datetime

from core.models import MarketRegime, RegimeOutput
from core.observability.logger import get_logger

logger = get_logger(__name__)

CHANGE_WINDOW = 5  # consecutive bars in new regime to confirm change


class RegimeWatcher:
    def __init__(self):
        self._history: deque[RegimeOutput] = deque(maxlen=100)
        self._last_confirmed_regime: MarketRegime | None = None
        self._change_detected_at: datetime | None = None

    def update(self, regime: RegimeOutput) -> bool:
        """Returns True if a confirmed regime change is detected."""
        self._history.append(regime)

        if len(self._history) < CHANGE_WINDOW:
            return False

        recent = list(self._history)[-CHANGE_WINDOW:]
        dominant = recent[-1].regime
        all_same = all(r.regime == dominant for r in recent)

        if all_same and dominant != self._last_confirmed_regime:
            prev = self._last_confirmed_regime
            self._last_confirmed_regime = dominant
            self._change_detected_at = datetime.utcnow()
            logger.warning(
                "regime_change_confirmed",
                previous=prev,
                new=dominant,
                symbol=regime.symbol,
                duration_bars=CHANGE_WINDOW,
            )
            return True
        return False

    def get_current_regime(self) -> MarketRegime | None:
        return self._last_confirmed_regime

    def time_since_last_change(self) -> float | None:
        if not self._change_detected_at:
            return None
        return (datetime.utcnow() - self._change_detected_at).total_seconds()
