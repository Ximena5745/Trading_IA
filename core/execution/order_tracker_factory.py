"""
Module: core/execution/order_tracker_factory.py
Responsibility: Factory para elegir implementación Redis o in-memory
"""
from core.execution.order_tracker import OrderTracker
from core.execution.order_tracker_redis import OrderTrackerRedis


def get_order_tracker(use_redis: bool = True):
    """
    Factory para obtener OrderTracker.
    Args:
        use_redis: Si True, usa la versión con persistencia Redis.
                   Si False, usa la versión in-memory.
    """
    if use_redis:
        try:
            return OrderTrackerRedis()
        except Exception:
            return OrderTracker()
    else:
        return OrderTracker()