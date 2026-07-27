"""
Tests for api/routes/execution.py — order endpoints must not leak/allow
mutation of orders belonging to a different user (IDOR).
"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from api.routes import execution as execution_routes
from core.execution.order_tracker import OrderTracker


def _user(user_id: str, role: str = "trader") -> dict:
    return {"user_id": user_id, "role": role}


@pytest.fixture(autouse=True)
def order_tracker():
    ot = OrderTracker()
    execution_routes.set_order_tracker(ot)
    yield ot


def _register_order(ot: OrderTracker, order_id: str, owner: str | None, **extra) -> dict:
    order = {
        "id": order_id,
        "user_id": owner,
        "symbol": "BTCUSDT",
        "status": "pending",
        **extra,
    }
    ot.register(order)
    return order


class TestOwnershipHelpers:
    def test_owns_order_true_for_owner(self):
        order = {"user_id": "u1"}
        assert execution_routes._owns_order(order, _user("u1")) is True

    def test_owns_order_false_for_other_user(self):
        order = {"user_id": "u1"}
        assert execution_routes._owns_order(order, _user("u2")) is False

    def test_owns_order_false_when_unowned(self):
        """An order with no recorded owner belongs to nobody, not everybody."""
        order = {"user_id": None}
        assert execution_routes._owns_order(order, _user("u2")) is False

    def test_admin_owns_any_order(self):
        order = {"user_id": "u1"}
        assert execution_routes._owns_order(order, _user("u2", role="admin")) is True


class TestGetOrder:
    @pytest.mark.asyncio
    async def test_owner_can_read_own_order(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        result = await execution_routes.get_order("order-1", user=_user("u1"))
        assert result["id"] == "order-1"

    @pytest.mark.asyncio
    async def test_other_user_gets_404_not_the_order(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        with pytest.raises(HTTPException) as exc_info:
            await execution_routes.get_order("order-1", user=_user("u2"))
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_can_read_any_order(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        result = await execution_routes.get_order("order-1", user=_user("admin1", role="admin"))
        assert result["id"] == "order-1"

    @pytest.mark.asyncio
    async def test_nonexistent_order_returns_404(self, order_tracker):
        with pytest.raises(HTTPException) as exc_info:
            await execution_routes.get_order("does-not-exist", user=_user("u1"))
        assert exc_info.value.status_code == 404


class TestCancelOrder:
    @pytest.mark.asyncio
    async def test_owner_can_cancel_own_order(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        result = await execution_routes.cancel_order("order-1", user=_user("u1"))
        assert result["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_other_user_cannot_cancel_returns_404(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        with pytest.raises(HTTPException) as exc_info:
            await execution_routes.cancel_order("order-1", user=_user("u2"))
        assert exc_info.value.status_code == 404
        # Ownership check must run BEFORE mutation -- order stays pending.
        assert order_tracker.get("order-1")["status"] == "pending"

    @pytest.mark.asyncio
    async def test_admin_can_cancel_any_order(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        result = await execution_routes.cancel_order(
            "order-1", user=_user("admin1", role="admin")
        )
        assert result["status"] == "cancelled"


class TestGetOrders:
    @pytest.mark.asyncio
    async def test_non_admin_only_sees_own_orders(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        _register_order(order_tracker, "order-2", owner="u2")

        result = await execution_routes.get_orders(user=_user("u1"))

        ids = {o["id"] for o in result["orders"]}
        assert ids == {"order-1"}

    @pytest.mark.asyncio
    async def test_admin_sees_all_orders(self, order_tracker):
        _register_order(order_tracker, "order-1", owner="u1")
        _register_order(order_tracker, "order-2", owner="u2")

        result = await execution_routes.get_orders(user=_user("admin1", role="admin"))

        ids = {o["id"] for o in result["orders"]}
        assert ids == {"order-1", "order-2"}
