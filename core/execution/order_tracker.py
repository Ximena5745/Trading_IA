"""
Module: core/execution/order_tracker.py
Responsibility: Track and update order states
Dependencies: logger
"""

from __future__ import annotations

from datetime import datetime

from core.observability.logger import get_logger

logger = get_logger(__name__)


class OrderTracker:
    def __init__(self):
        self._orders: dict[str, dict] = {}

    def register(self, order: dict) -> None:
        self._orders[order["id"]] = order
        logger.info("order_registered", order_id=order["id"], status=order["status"])

    def update_status(self, order_id: str, status: str, **kwargs) -> dict:
        order = self._orders.get(order_id)
        if not order:
            raise KeyError(f"Order not found: {order_id}")
        order["status"] = status
        order["updated_at"] = datetime.utcnow().isoformat()
        order.update(kwargs)
        logger.info("order_status_updated", order_id=order_id, status=status)
        return order

    def get(self, order_id: str) -> dict:
        order = self._orders.get(order_id)
        if not order:
            raise KeyError(f"Order not found: {order_id}")
        return order

    def get_open_orders(self) -> list[dict]:
        return [
            o
            for o in self._orders.values()
            if o["status"] in ("pending", "submitted", "partial")
        ]

    def get_all(self) -> list[dict]:
        return list(self._orders.values())
