"""
Value Object: Price
Responsibility: Represent price with precision and validation.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, field_validator


class Price(BaseModel):
    """Immutable price representation with precision control."""

    value: Decimal
    symbol: str
    precision: int = 8  # decimal places

    @field_validator("value")
    @classmethod
    def validate_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be positive")
        return v

    @field_validator("precision")
    @classmethod
    def validate_precision(cls, v: int) -> int:
        if v < 0 or v > 18:
            raise ValueError("Precision must be between 0 and 18")
        return v

    def rounded(self) -> Decimal:
        """Return price rounded to precision."""
        quantizer = Decimal(10) ** -self.precision
        return self.value.quantize(quantizer)

    def __str__(self) -> str:
        return f"{self.rounded()} {self.symbol}"

    def __repr__(self) -> str:
        return f"Price(value={self.value}, symbol={self.symbol}, precision={self.precision})"

    def __add__(self, other: "Price") -> "Price":
        if self.symbol != other.symbol:
            raise ValueError(f"Cannot add prices of different symbols: {self.symbol} and {other.symbol}")
        return Price(value=self.value + other.value, symbol=self.symbol, precision=self.precision)

    def __mul__(self, multiplier: float) -> "Price":
        return Price(value=self.value * Decimal(str(multiplier)), symbol=self.symbol, precision=self.precision)