"""
Module: core/risk/factory.py
Responsibility: Factory para elegir implementación Redis o in-memory
"""
from typing import Optional

from core.config.settings import get_settings
from core.risk.kill_switch import KillSwitch
from core.risk.kill_switch_redis import KillSwitchRedis


def get_kill_switch(use_redis: bool = True):
    """
    Factory para obtener KillSwitch.
    Args:
        use_redis: Si True, usa la versión con persistencia Redis.
                   Si False, usa la versión in-memory.
    """
    if use_redis:
        try:
            return KillSwitchRedis()
        except Exception:
            # Fallback to in-memory if Redis not available
            settings = get_settings()
            return KillSwitch(settings)
    else:
        settings = get_settings()
        return KillSwitch(settings)


def get_kill_switch_redis_fallback():
    """Obtiene KillSwitchRedis con fallback a in-memory."""
    try:
        return KillSwitchRedis()
    except Exception:
        settings = get_settings()
        return KillSwitch(settings)