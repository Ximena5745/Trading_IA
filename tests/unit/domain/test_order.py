"""
Tests for domain/entities/order.py
CA-3: Order quantity > 0 siempre
"""
import pytest
from datetime import datetime
from domain.entities.order import Order, OrderStatus


class TestOrderInvariants:
    """Tests for Order entity invariants."""

    def test_quantity_positive_valid(self):
        """CA-3: Positive quantity should be valid."""
        order = Order(
            id="order-1",
            idempotency_key="key-1",
            signal_id="signal-1",
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.5,
            stop_loss=49000.0,
            take_profit=52000.0,
            status=OrderStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert order.quantity == 0.5

    def test_quantity_zero_invalid(self):
        """CA-3: Quantity = 0 should raise ValidationError."""
        with pytest.raises(ValueError, match="Quantity must be greater than 0"):
            Order(
                id="order-2",
                idempotency_key="key-2",
                signal_id="signal-2",
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

    def test_quantity_negative_invalid(self):
        """CA-3: Negative quantity should raise ValidationError."""
        with pytest.raises(ValueError, match="Quantity must be greater than 0"):
            Order(
                id="order-3",
                idempotency_key="key-3",
                signal_id="signal-3",
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=-1.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                status=OrderStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

    def test_fill_price_non_negative_valid(self):
        """Fill price = 0 should be valid."""
        order = Order(
            id="order-4",
            idempotency_key="key-4",
            signal_id="signal-4",
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.5,
            stop_loss=49000.0,
            take_profit=52000.0,
            status=OrderStatus.FILLED,
            fill_price=0.0,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert order.fill_price == 0.0

    def test_fill_price_negative_invalid(self):
        """Negative fill_price should raise ValidationError."""
        with pytest.raises(ValueError, match="Fill price must be non-negative"):
            Order(
                id="order-5",
                idempotency_key="key-5",
                signal_id="signal-5",
                symbol="BTCUSDT",
                side="BUY",
                order_type="MARKET",
                quantity=0.5,
                stop_loss=49000.0,
                take_profit=52000.0,
                status=OrderStatus.FILLED,
                fill_price=-100.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

    def test_is_filled_method(self):
        """is_filled() should return True when status is FILLED."""
        order = Order(
            id="order-6",
            idempotency_key="key-6",
            signal_id="signal-6",
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.5,
            stop_loss=49000.0,
            take_profit=52000.0,
            status=OrderStatus.FILLED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert order.is_filled() is True

    def test_is_cancelled_method(self):
        """is_cancelled() should return True when status is CANCELLED."""
        order = Order(
            id="order-7",
            idempotency_key="key-7",
            signal_id="signal-7",
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=0.5,
            stop_loss=49000.0,
            take_profit=52000.0,
            status=OrderStatus.CANCELLED,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        assert order.is_cancelled() is True

    def test_total_cost_with_commission(self):
        """total_cost() should include commission."""
        order = Order(
            id="order-8",
            idempotency_key="key-8",
            signal_id="signal-8",
            symbol="BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=1.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            status=OrderStatus.FILLED,
            fill_price=50000.0,
            fill_quantity=1.0,
            commission=50.0,  # 0.1%
            slippage=0.0005,  # 0.05%
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        cost = order.total_cost()
        expected_base = 50000.0 * 1.0
        expected_slippage = expected_base * 0.0005
        expected_total = expected_base + 50.0 + expected_slippage
        assert abs(cost - expected_total) < 0.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])