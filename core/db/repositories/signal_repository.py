"""
Module: core/db/repositories/signal_repository.py
Responsibility: Persistence layer for trading signals.
"""
from __future__ import annotations

from uuid import UUID

from core.db.repository import TradingRepository
from core.db.session import get_pool
from core.models import Signal
from core.observability.logger import get_logger

logger = get_logger(__name__)


class SignalRepository:
    def __init__(self, trading_repo: TradingRepository | None = None) -> None:
        self._repo = trading_repo or TradingRepository()

    async def create(self, signal: Signal) -> str:
        await self._repo.save_signal(signal)
        return signal.id

    async def get_by_id(self, signal_id: str) -> dict | None:
        sql = """
            SELECT id, symbol, action, entry_price, stop_loss, take_profit,
                   confidence, risk_reward_ratio, status, created_at, summary, regime
            FROM signals WHERE id = $1
        """
        try:
            row = await get_pool().fetchrow(sql, signal_id)
            return dict(row) if row else None
        except Exception as exc:
            logger.error("signal_get_failed", signal_id=signal_id, error=str(exc))
            return None

    async def get_recent_by_symbol(self, symbol: str, limit: int = 50) -> list[dict]:
        return await self._repo.get_recent_signals(symbol, limit)

    async def update_status(self, signal_id: str | UUID, status: str) -> bool:
        sql = "UPDATE signals SET status = $2 WHERE id = $1"
        try:
            result = await get_pool().execute(sql, str(signal_id), status)
            return result.endswith("1")
        except Exception as exc:
            logger.error("signal_status_update_failed", signal_id=signal_id, error=str(exc))
            return False
