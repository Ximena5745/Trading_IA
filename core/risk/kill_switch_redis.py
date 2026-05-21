"""
Module: core/risk/kill_switch_redis.py
Responsibility: KillSwitch with Redis persistence for multi-worker deployments
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import redis

from core.config.settings import get_settings
from core.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

KILLSWITCH_KEY = "trader:kill_switch:state"


class KillSwitchRedis:
    """
    KillSwitch con estado persistido en Redis.
    Permite múltiples workers sin race conditions.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._default_daily_loss = settings.DAILY_LOSS_LIMIT_PCT
        self._default_max_losses = settings.MAX_CONSECUTIVE_LOSSES
        self._default_max_dd = settings.MAX_DRAWDOWN_PCT

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _load_state(self) -> dict:
        """Carga estado desde Redis."""
        try:
            data = self._get_redis().get(KILLSWITCH_KEY)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("kill_switch_redis_load_error", error=str(e))

        return {
            "active": False,
            "triggered_at": None,
            "triggered_by": None,
            "daily_loss_current": 0.0,
            "daily_loss_limit": self._default_daily_loss,
            "consecutive_losses": 0,
            "max_consecutive_losses": self._default_max_losses,
            "max_drawdown": self._default_max_dd,
            "reset_at": None,
        }

    def _save_state(self, state: dict) -> None:
        """Guarda estado en Redis."""
        try:
            self._get_redis().set(KILLSWITCH_KEY, json.dumps(state, default=str))
        except Exception as e:
            logger.error("kill_switch_redis_save_error", error=str(e))

    def is_active(self) -> bool:
        """Retorna True si el kill switch está activo."""
        state = self._load_state()
        return state.get("active", False)

    def check_and_trigger(
        self,
        daily_pnl_pct: float,
        drawdown_current: float,
        recent_trades: list,
    ) -> None:
        """Evalúa condiciones y activa el kill switch si es necesario."""
        state = self._load_state()

        # Si ya está activo, no volver a activar
        if state.get("active"):
            return

        state["daily_loss_current"] = daily_pnl_pct

        # Trigger: Daily loss
        if daily_pnl_pct <= -self._default_daily_loss:
            state["active"] = True
            state["triggered_by"] = "daily_loss_limit"
            state["triggered_at"] = datetime.utcnow().isoformat()
            self._save_state(state)
            logger.critical("kill_switch_triggered_redis", reason="daily_loss_limit")
            return

        # Trigger: Max drawdown
        if drawdown_current >= self._default_max_dd:
            state["active"] = True
            state["triggered_by"] = "max_drawdown"
            state["triggered_at"] = datetime.utcnow().isoformat()
            self._save_state(state)
            logger.critical("kill_switch_triggered_redis", reason="max_drawdown")
            return

        # Trigger: Consecutive losses
        consecutive = self._count_consecutive_losses(recent_trades)
        state["consecutive_losses"] = consecutive
        if consecutive >= self._default_max_losses:
            state["active"] = True
            state["triggered_by"] = "consecutive_losses"
            state["triggered_at"] = datetime.utcnow().isoformat()
            self._save_state(state)
            logger.critical("kill_switch_triggered_redis", reason="consecutive_losses")
            return

        self._save_state(state)

    def _count_consecutive_losses(self, recent_trades: list) -> int:
        """Cuenta pérdidas consecutivas."""
        count = 0
        for trade in reversed(recent_trades):
            pnl = trade.get("net_pnl", 0) if isinstance(trade, dict) else getattr(trade, "net_pnl", 0)
            if pnl < 0:
                count += 1
            else:
                break
        return count

    def activate(self, reason: str = "manual") -> None:
        """Activación manual del kill switch."""
        state = self._load_state()
        if state.get("active"):
            return
        state["active"] = True
        state["triggered_by"] = reason
        state["triggered_at"] = datetime.utcnow().isoformat()
        self._save_state(state)
        logger.critical("kill_switch_activated_redis", reason=reason)

    def reset(self, admin_token: str) -> None:
        """Reinicia el kill switch (solo admin)."""
        state = self._load_state()
        state["active"] = False
        state["triggered_by"] = None
        state["triggered_at"] = None
        state["reset_at"] = datetime.utcnow().isoformat()
        self._save_state(state)
        logger.warning("kill_switch_reset_redis", triggered_by=state.get("triggered_by"))

    @property
    def state(self) -> dict:
        """Retorna estado actual."""
        return self._load_state()


def get_kill_switch_redis() -> KillSwitchRedis:
    """Factory function for KillSwitchRedis."""
    return KillSwitchRedis()