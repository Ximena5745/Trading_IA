"""
Module: core/execution/paper_executor.py
Responsibility: Realistic paper trading simulation
Dependencies: base_executor, settings, constants, logger
"""
from __future__ import annotations

import asyncio
import random
import uuid
from datetime import datetime
from typing import Optional

from core.config.constants import (
    PAPER_COMMISSION_PCT,
    PAPER_LATENCY_MS_MAX,
    PAPER_LATENCY_MS_MIN,
    PAPER_SLIPPAGE_PCT,
)
from core.execution.base_executor import AbcExecutor
from core.exceptions import ExecutionError
from core.observability.logger import get_logger

logger = get_logger(__name__)

_orders: dict[str, dict] = {}  # in-memory store for paper orders


class PaperExecutor(AbcExecutor):
    """
    Simulates realistic fills:
    - MARKET orders: fill at signal price + slippage
    - Commission applied on each fill
    - Idempotency: same key returns existing order
    """

    async def execute(self, signal: dict, quantity: float) -> dict:
        idempotency_key = signal.get("idempotency_key", "")
        if idempotency_key and idempotency_key in _orders:
            logger.info("paper_executor_idempotent_hit", idempotency_key=idempotency_key)
            return _orders[idempotency_key]

        await self._simulate_latency()

        entry_price = signal.get("entry_price", 0.0)
        action = signal.get("action", "BUY")
        slippage = entry_price * PAPER_SLIPPAGE_PCT
        fill_price = entry_price + slippage if action == "BUY" else entry_price - slippage
        commission = fill_price * quantity * PAPER_COMMISSION_PCT

        order = {
            "id": str(uuid.uuid4()),
            "idempotency_key": idempotency_key,
            "signal_id": signal.get("id", ""),
            "symbol": signal.get("symbol", ""),
            "side": action,
            "order_type": "MARKET",
            "quantity": quantity,
            "fill_price": round(fill_price, 8),
            "fill_quantity": quantity,
            "commission": round(commission, 8),
            "slippage": round(slippage, 8),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
            "status": "filled",
            "execution_mode": "paper",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": None,
        }

        if idempotency_key:
            _orders[idempotency_key] = order

        logger.info(
            "paper_trade_executed",
            symbol=order["symbol"],
            side=order["side"],
            quantity=quantity,
            fill_price=fill_price,
            commission=commission,
        )
        return order

    async def cancel_order(self, order_id: str) -> dict:
        for order in _orders.values():
            if order["id"] == order_id:
                if order["status"] in ("filled", "cancelled"):
                    raise ExecutionError(f"Cannot cancel order in status: {order['status']}")
                order["status"] = "cancelled"
                order["updated_at"] = datetime.utcnow().isoformat()
                return order
        raise ExecutionError(f"Order not found: {order_id}")

    async def get_order_status(self, order_id: str) -> dict:
        for order in _orders.values():
            if order["id"] == order_id:
                return order
        raise ExecutionError(f"Order not found: {order_id}")

    def simulate_sl_tp(self, position: dict, current_price: float) -> Optional[str]:
        """Check if stop loss or take profit was hit. Returns 'sl', 'tp', or None."""
        sl = position.get("stop_loss")
        tp = position.get("take_profit")
        side = position.get("side", "BUY")

        if side == "BUY":
            if sl and current_price <= sl:
                return "sl"
            if tp and current_price >= tp:
                return "tp"
        else:
            if sl and current_price >= sl:
                return "sl"
            if tp and current_price <= tp:
                return "tp"
        return None

    async def _simulate_latency(self) -> None:
        ms = random.randint(PAPER_LATENCY_MS_MIN, PAPER_LATENCY_MS_MAX)
        await asyncio.sleep(ms / 1000)
