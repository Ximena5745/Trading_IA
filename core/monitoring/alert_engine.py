"""
Module: core/monitoring/alert_engine.py
Responsibility: Dispatch alerts to Telegram and webhooks
Dependencies: telegram_bot, logger
"""
from __future__ import annotations

from core.models import Signal
from core.observability.logger import get_logger

logger = get_logger(__name__)


class AlertEngine:
    def __init__(self, telegram_bot=None):
        self._telegram = telegram_bot

    async def on_signal(self, signal: Signal) -> None:
        logger.info(
            "alert_signal",
            symbol=signal.symbol,
            action=signal.action,
            confidence=signal.confidence,
        )
        if self._telegram:
            await self._telegram.send_signal_alert(signal)

    async def on_kill_switch(self, reason: str, daily_pnl: float) -> None:
        logger.critical("alert_kill_switch", reason=reason, daily_pnl=daily_pnl)
        if self._telegram:
            await self._telegram.send_kill_switch_alert(reason, daily_pnl)

    async def on_ws_reconnect(self, symbol: str, attempt: int) -> None:
        logger.warning("alert_ws_reconnect", symbol=symbol, attempt=attempt)
        if self._telegram and attempt >= 3:
            await self._telegram.send_reconnect_alert(symbol, attempt)

    async def on_model_retrained(self, agent_id: str, new_version: str) -> None:
        logger.info("alert_model_retrained", agent_id=agent_id, new_version=new_version)

    async def on_critical_error(self, error_type: str, details: str) -> None:
        logger.critical("alert_critical_error", error_type=error_type, details=details)
        if self._telegram:
            await self._telegram.send_critical_error_alert(error_type, details)

    async def on_system_restart(self, version: str, execution_mode: str) -> None:
        logger.info(
            "alert_system_restart", version=version, execution_mode=execution_mode
        )
        if self._telegram:
            await self._telegram.send_system_restart_alert(version, execution_mode)
