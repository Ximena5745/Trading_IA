"""
Module: core/adaptation/retraining.py
Responsibility: AdaptationEngine — trigger and orchestrate agent retraining
Dependencies: technical_agent, regime_watcher, feature_store, logger
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from core.adaptation.regime_watcher import RegimeWatcher
from core.agents.technical_agent import TechnicalAgent
from core.features.feature_store import FeatureStore
from core.models import RegimeOutput
from core.observability.logger import get_logger

logger = get_logger(__name__)

MIN_SAMPLES_FOR_TRAINING = 200
RETRAIN_COOLDOWN_SECONDS = 3600  # 1 hour between retrains


class AdaptationEngine:
    def __init__(
        self,
        technical_agent: TechnicalAgent,
        feature_store: FeatureStore,
        regime_watcher: Optional[RegimeWatcher] = None,
    ):
        self._agent = technical_agent
        self._feature_store = feature_store
        self._regime_watcher = regime_watcher or RegimeWatcher()
        self._last_retrain_at: Optional[datetime] = None
        self._retrain_count: int = 0
        self._is_retraining: bool = False

    async def on_regime_update(self, regime: RegimeOutput) -> bool:
        """Process regime update; returns True if retraining was triggered."""
        changed = self._regime_watcher.update(regime)
        if changed:
            logger.info(
                "adaptation_regime_change_detected",
                symbol=regime.symbol,
                new_regime=regime.regime,
            )
            return await self.maybe_retrain(
                symbol=regime.symbol, reason="regime_change"
            )
        return False

    async def maybe_retrain(self, symbol: str, reason: str = "manual") -> bool:
        """Retrain the technical agent if conditions allow."""
        if self._is_retraining:
            logger.warning("adaptation_retrain_skipped", reason="already_retraining")
            return False

        if not self._cooldown_elapsed():
            elapsed = self._seconds_since_last_retrain()
            logger.info(
                "adaptation_retrain_skipped",
                reason="cooldown",
                seconds_remaining=RETRAIN_COOLDOWN_SECONDS - (elapsed or 0),
            )
            return False

        history = self._feature_store.get_history(symbol, limit=500)
        if len(history) < MIN_SAMPLES_FOR_TRAINING:
            logger.warning(
                "adaptation_retrain_skipped",
                reason="insufficient_samples",
                available=len(history),
                required=MIN_SAMPLES_FOR_TRAINING,
            )
            return False

        self._is_retraining = True
        try:
            logger.info(
                "adaptation_retrain_started",
                symbol=symbol,
                reason=reason,
                samples=len(history),
            )
            await asyncio.get_event_loop().run_in_executor(
                None, self._agent.train, history
            )
            self._last_retrain_at = datetime.utcnow()
            self._retrain_count += 1
            logger.info(
                "adaptation_retrain_completed",
                symbol=symbol,
                retrain_count=self._retrain_count,
                version=self._agent.model_version,
            )
            return True
        except Exception as exc:
            logger.error("adaptation_retrain_failed", error=str(exc), symbol=symbol)
            return False
        finally:
            self._is_retraining = False

    def _cooldown_elapsed(self) -> bool:
        if self._last_retrain_at is None:
            return True
        elapsed = (datetime.utcnow() - self._last_retrain_at).total_seconds()
        return elapsed >= RETRAIN_COOLDOWN_SECONDS

    def _seconds_since_last_retrain(self) -> Optional[float]:
        if self._last_retrain_at is None:
            return None
        return (datetime.utcnow() - self._last_retrain_at).total_seconds()

    def get_status(self) -> dict:
        return {
            "is_retraining": self._is_retraining,
            "retrain_count": self._retrain_count,
            "last_retrain_at": self._last_retrain_at.isoformat()
            if self._last_retrain_at
            else None,
            "cooldown_seconds": RETRAIN_COOLDOWN_SECONDS,
            "seconds_since_last_retrain": self._seconds_since_last_retrain(),
            "current_regime": self._regime_watcher.get_current_regime(),
            "time_since_regime_change": self._regime_watcher.time_since_last_change(),
            "agent_version": self._agent.model_version,
            "agent_ready": self._agent.is_ready(),
        }
