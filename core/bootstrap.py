"""
Module: core/bootstrap.py
Responsibility: Wire distributed state (Redis) and in-memory fallbacks for the API.
"""
from __future__ import annotations

from core.config.settings import Settings
from core.execution.order_tracker_factory import get_order_tracker
from core.portfolio.portfolio_factory import get_portfolio_manager
from core.risk.kill_switch_factory import get_kill_switch_redis_fallback


def create_kill_switch(settings: Settings):
    return get_kill_switch_redis_fallback()


def create_order_tracker(use_redis: bool = True):
    return get_order_tracker(use_redis=use_redis)


def create_portfolio_manager(settings: Settings, use_redis: bool = True):
    pm = get_portfolio_manager(use_redis=use_redis)
    if hasattr(pm, "_settings"):
        return pm
    if not use_redis or not hasattr(pm, "get_portfolio"):
        from core.portfolio.portfolio_manager import PortfolioManager

        return PortfolioManager(settings=settings, initial_capital=10_000.0)
    return pm
