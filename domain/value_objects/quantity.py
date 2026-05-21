"""
Value Object: Quantity
Responsibility: Represent trade quantity with validation.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class Quantity(BaseModel):
    """Immutable quantity representation for trading."""

    value: Decimal
    asset_class: str = "crypto"  # crypto, forex, indices, commodities

    @field_validator("value")
    @classmethod
    def validate_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v

    def rounded(self, decimals: int = 6) -> Decimal:
        """Return quantity rounded to specified decimals."""
        quantizer = Decimal(10) ** -decimals
        return self.value.quantize(quantizer)

    def __str__(self) -> str:
        return f"{self.rounded()}"

    def __repr__(self) -> str:
        return f"Quantity(value={self.value}, asset_class={self.asset_class})"

    def __add__(self, other: "Quantity") -> "Quantity":
        if self.asset_class != other.asset_class:
            raise ValueError(f"Cannot add quantities of different asset classes")
        return Quantity(value=self.value + other.value, asset_class=self.asset_class)

    def __mul__(self, multiplier: float) -> "Quantity":
        return Quantity(value=self.value * Decimal(str(multiplier)), asset_class=self.asset_class)