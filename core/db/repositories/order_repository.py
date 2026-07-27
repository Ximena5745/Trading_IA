"""
Module: core/db/repositories/order_repository.py
Responsibility: Persistence layer for orders.
"""
from __future__ import annotations

from core.db.repository import TradingRepository
from core.db.session import get_pool
from core.observability.logger import get_logger

logger = get_logger(__name__)


class OrderRepository:
    def __init__(self, trading_repo: TradingRepository | None = None) -> None:
        self._repo = trading_repo or TradingRepository()

    async def create(self, order: dict) -> str:
        await self._repo.save_order(order)
        return order.get("id", "")

    async def get_by_id(self, order_id: str) -> dict | None:
        sql = """
            SELECT id, signal_id, user_id, symbol, side, quantity, fill_price,
                   commission, slippage, status, execution_mode, created_at
            FROM orders WHERE id = $1
        """
        try:
            row = await get_pool().fetchrow(sql, order_id)
            return dict(row) if row else None
        except Exception as exc:
            logger.error("order_get_failed", order_id=order_id, error=str(exc))
            return None

    async def get_open_orders(self) -> list[dict]:
        sql = """
            SELECT id, signal_id, user_id, symbol, side, quantity, fill_price, status, created_at
            FROM orders
            WHERE status IN ('pending', 'submitted', 'partial')
            ORDER BY created_at DESC
        """
        try:
            rows = await get_pool().fetch(sql)
            return [dict(r) for r in rows]
        except Exception as exc:
            logger.error("open_orders_fetch_failed", error=str(exc))
            return []

    async def update_fill(
        self, order_id: str, fill_price: float, commission: float
    ) -> bool:
        sql = """
            UPDATE orders
            SET fill_price = $2, commission = $3, status = 'filled',
                updated_at = NOW()
            WHERE id = $1
        """
        try:
            result = await get_pool().execute(sql, order_id, fill_price, commission)
            return result.endswith("1")
        except Exception as exc:
            logger.error("order_fill_update_failed", order_id=order_id, error=str(exc))
            return False
