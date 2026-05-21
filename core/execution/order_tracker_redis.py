"""
Module: core/execution/order_tracker_redis.py
Responsibility: OrderTracker con persistencia Redis para multi-worker deployments
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Optional

import redis

from core.config.settings import get_settings
from core.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

ORDERS_KEY = "trader:orders:"
OPEN_ORDERS_KEY = "trader:orders:open"


class OrderTrackerRedis:
    """
    OrderTracker persistido en Redis.
    Permite múltiples workers sin race conditions.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def add(self, order: dict) -> None:
        """Añade una orden al tracker."""
        order_id = order.get("id")
        if not order_id:
            return

        try:
            self._get_redis().hset(
                f"{ORDERS_KEY}{order_id}",
                mapping={
                    "data": json.dumps(order, default=str),
                    "created_at": datetime.utcnow().isoformat(),
                }
            )
            logger.debug("order_tracked_redis", order_id=order_id)
        except Exception as e:
            logger.error("order_track_error", order_id=order_id, error=str(e))

    def get(self, order_id: str) -> dict:
        """Obtiene una orden por ID."""
        try:
            data = self._get_redis().hget(f"{ORDERS_KEY}{order_id}", "data")
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error("order_get_error", order_id=order_id, error=str(e))
        raise KeyError(f"Order {order_id} not found")

    def update_status(self, order_id: str, status: str) -> None:
        """Actualiza el estado de una orden."""
        try:
            order = self.get(order_id)
            order["status"] = status
            order["updated_at"] = datetime.utcnow().isoformat()
            self._get_redis().hset(
                f"{ORDERS_KEY}{order_id}",
                "data",
                json.dumps(order, default=str),
            )
            logger.debug("order_status_updated", order_id=order_id, status=status)
        except KeyError:
            logger.warning("order_not_found_for_update", order_id=order_id)

    def get_open_orders(self) -> list[dict]:
        """Retorna lista de órdenes abiertas."""
        open_orders = []
        try:
            keys = self._get_redis().keys(f"{ORDERS_KEY}*")
            for key in keys:
                data = self._get_redis().hget(key, "data")
                if data:
                    order = json.loads(data)
                    if order.get("status") in ("pending", "submitted", "partial"):
                        open_orders.append(order)
        except Exception as e:
            logger.error("get_open_orders_error", error=str(e))
        return open_orders

    def remove(self, order_id: str) -> None:
        """Elimina una orden del tracker."""
        try:
            self._get_redis().delete(f"{ORDERS_KEY}{order_id}")
            logger.debug("order_removed_redis", order_id=order_id)
        except Exception as e:
            logger.error("order_remove_error", order_id=order_id, error=str(e))

    def get_by_symbol(self, symbol: str) -> list[dict]:
        """Retorna órdenes de un símbolo."""
        orders = []
        try:
            keys = self._get_redis().keys(f"{ORDERS_KEY}*")
            for key in keys:
                data = self._get_redis().hget(key, "data")
                if data:
                    order = json.loads(data)
                    if order.get("symbol") == symbol:
                        orders.append(order)
        except Exception as e:
            logger.error("get_by_symbol_error", symbol=symbol, error=str(e))
        return orders


def get_order_tracker_redis() -> OrderTrackerRedis:
    """Factory function for OrderTrackerRedis."""
    return OrderTrackerRedis()