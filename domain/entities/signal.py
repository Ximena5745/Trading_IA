"""
Domain Entity: Signal
Responsibility: Represent a trading signal with validation rules.
Invariant: stop_loss < entry_price (BUY), take_profit > entry_price (BUY), confidence in [0,1]
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class SignalExplanationFactor(BaseModel):
    factor: str
    weight: float
    direction: str
    description: str


class Signal(BaseModel):
    id: str
    idempotency_key: str
    timestamp: Optional[datetime] = None
    symbol: str
    asset_class: str = "crypto"
    action: str  # "BUY" | "SELL" | "HOLD"
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence: float
    explanation: Optional[list[SignalExplanationFactor]] = None
    summary: str = ""
    regime: Optional[str] = None
    strategy_id: str = "manual"
    status: str = "pending"

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @field_validator("entry_price")
    @classmethod
    def validate_prices(cls, v: float, info) -> float:
        if v <= 0:
            raise ValueError("Entry price must be positive")
        return v

    def is_valid_for_buy(self) -> bool:
        """Invariant: stop_loss < entry_price < take_profit for BUY signals."""
        if self.action != "BUY":
            return True
        return self.stop_loss < self.entry_price < self.take_profit

    def is_valid_for_sell(self) -> bool:
        """Invariant: take_profit < entry_price < stop_loss for SELL signals."""
        if self.action != "SELL":
            return True
        return self.take_profit < self.entry_price < self.stop_loss