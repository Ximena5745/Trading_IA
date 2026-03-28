"""
Module: core/notifications/telegram_bot.py
Responsibility: Send Telegram alerts with signal + XAI explanation
Dependencies: python-telegram-bot, models, logger
"""

from __future__ import annotations

from core.models import Signal
from core.observability.logger import get_logger

logger = get_logger(__name__)


class TelegramBot:
    def __init__(self, token: str, chat_id: str):
        self._token = token
        self._chat_id = chat_id
        self._bot = None
        if token:
            self._init_bot()

    def _init_bot(self) -> None:
        try:
            from telegram import Bot

            self._bot = Bot(token=self._token)
            logger.info("telegram_bot_initialized")
        except Exception as e:
            logger.warning("telegram_bot_init_failed", error=str(e))

    async def send_signal_alert(self, signal: Signal) -> None:
        if not self._bot or not self._chat_id:
            return
        msg = self._format_signal(signal)
        await self._send(msg)

    async def send_kill_switch_alert(self, reason: str, daily_pnl: float) -> None:
        msg = (
            f"🚨 *KILL SWITCH ACTIVADO*\n"
            f"Motivo: `{reason}`\n"
            f"P&L diario: `{daily_pnl:.2%}`\n"
            f"⛔ Todos los trades bloqueados hasta reset manual."
        )
        await self._send(msg, priority=True)

    async def send_reconnect_alert(self, symbol: str, attempt: int) -> None:
        msg = f"⚠️ WebSocket reconectando — {symbol} (intento {attempt})"
        await self._send(msg)

    async def _send(self, text: str, priority: bool = False) -> None:
        try:
            await self._bot.send_message(
                chat_id=self._chat_id,
                text=text,
                parse_mode="Markdown",
            )
            logger.info("telegram_sent", priority=priority)
        except Exception as e:
            logger.error("telegram_send_failed", error=str(e))

    @staticmethod
    def _format_signal(signal: Signal) -> str:
        emoji = "🟢" if signal.action == "BUY" else "🔴"
        factors = "\n".join(f"  • {f.description}" for f in signal.explanation[:3])
        return (
            f"{emoji} *{signal.action} — {signal.symbol}*\n"
            f"💰 Entrada: `{signal.entry_price:.2f}`\n"
            f"🛡️ Stop Loss: `{signal.stop_loss:.2f}`\n"
            f"🎯 Take Profit: `{signal.take_profit:.2f}`\n"
            f"📊 R:R: `{signal.risk_reward_ratio:.1f}x` | Confianza: `{signal.confidence:.0%}`\n\n"
            f"🔍 *Por qué:*\n{factors}\n\n"
            f"_{signal.summary}_"
        )
