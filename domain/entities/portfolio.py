"""
Domain Entity: Portfolio and Position
Responsibility: Represent portfolio state and open positions.
Invariant: available_capital <= total_capital, Position must have stop_loss and take_profit
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class Position(BaseModel):
    symbol: str
    asset_class: str = "crypto"
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    strategy_id: str
    opened_at: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Position quantity must be greater than 0")
        return v

    @field_validator("entry_price")
    @classmethod
    def validate_entry_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Entry price must be positive")
        return v

    def has_risk_levels(self) -> bool:
        """Invariant: Position must have stop_loss and take_profit."""
        return self.stop_loss is not None and self.take_profit is not None


class Portfolio(BaseModel):
    id: str
    total_capital: float
    available_capital: float
    positions: list[Position] = []
    risk_exposure: float = 0.0
    daily_pnl: float = 0.0
    daily_pnl_pct: float = 0.0
    total_pnl: float = 0.0
    drawdown_current: float = 0.0
    drawdown_max: float = 0.0
    updated_at: datetime

    @field_validator("available_capital")
    @classmethod
    def validate_available_capital(cls, v: float, info) -> float:
        total = info.data.get("total_capital", float("inf"))
        if v > total:
            raise ValueError("Available capital cannot exceed total capital")
        return v

    @field_validator("total_capital")
    @classmethod
    def validate_total_capital(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Total capital must be positive")
        return v

    def total_position_value(self) -> float:
        """Calculate total value of all open positions."""
        return sum(p.quantity * p.current_price for p in self.positions)

    def used_capital(self) -> float:
        """Calculate capital used in positions."""
        return self.total_capital - self.available_capital

    def exposure_percentage(self) -> float:
        """Calculate portfolio exposure as percentage."""
        if self.total_capital == 0:
            return 0.0
        return self.total_position_value() / self.total_capital