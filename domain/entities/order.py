"""
Domain Entity: Order
Responsibility: Represent a trading order with validation rules.
Invariant: quantity > 0, fill_price >= 0
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class Order(BaseModel):
    id: str
    exchange_order_id: Optional[str] = None
    idempotency_key: str
    signal_id: str
    symbol: str
    asset_class: str = "crypto"
    side: str
    order_type: str
    quantity: float
    price: Optional[float] = None
    stop_loss: float
    take_profit: float
    status: OrderStatus
    fill_price: Optional[float] = None
    fill_quantity: Optional[float] = None
    commission: Optional[float] = None
    slippage: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    execution_mode: str = "paper"
    error_message: Optional[str] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Quantity must be greater than 0")
        return v

    @field_validator("fill_price")
    @classmethod
    def validate_fill_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("Fill price must be non-negative")
        return v

    def is_filled(self) -> bool:
        return self.status == OrderStatus.FILLED

    def is_cancelled(self) -> bool:
        return self.status == OrderStatus.CANCELLED

    def total_cost(self) -> float:
        """Calculate total cost including commission and slippage."""
        if not self.fill_price or not self.fill_quantity:
            return 0.0
        base_cost = self.fill_price * self.fill_quantity
        commission = self.commission or 0.0
        slippage_cost = (self.slippage or 0.0) * base_cost
        return base_cost + commission + slippage_cost