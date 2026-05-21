"""
Value Object: RiskLevel
Responsibility: Represent risk tolerance levels.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, field_validator


class RiskLevel(str, Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"

    @property
    def max_risk_per_trade(self) -> float:
        return {
            RiskLevel.CONSERVATIVE: 0.005,  # 0.5%
            RiskLevel.MODERATE: 0.01,       # 1.0%
            RiskLevel.AGGRESSIVE: 0.02,     # 2.0%
        }[self]

    @property
    def max_portfolio_risk(self) -> float:
        return {
            RiskLevel.CONSERVATIVE: 0.05,   # 5%
            RiskLevel.MODERATE: 0.10,      # 10%
            RiskLevel.AGGRESSIVE: 0.20,    # 20%
        }[self]

    @property
    def min_risk_reward(self) -> float:
        return {
            RiskLevel.CONSERVATIVE: 2.5,
            RiskLevel.MODERATE: 1.5,
            RiskLevel.AGGRESSIVE: 1.0,
        }[self]


class RiskProfile(BaseModel):
    """Complete risk profile configuration."""

    level: RiskLevel
    max_risk_per_trade: float
    max_portfolio_risk: float
    max_drawdown: float
    min_risk_reward: float
    max_consecutive_losses: int

    @field_validator("max_risk_per_trade")
    @classmethod
    def validate_risk_per_trade(cls, v: float) -> float:
        if not 0.001 <= v <= 0.05:
            raise ValueError("Max risk per trade must be between 0.1% and 5%")
        return v

    @field_validator("max_drawdown")
    @classmethod
    def validate_drawdown(cls, v: float) -> float:
        if not 0.01 <= v <= 0.50:
            raise ValueError("Max drawdown must be between 1% and 50%")
        return v

    @classmethod
    def from_level(cls, level: RiskLevel) -> "RiskProfile":
        return cls(
            level=level,
            max_risk_per_trade=level.max_risk_per_trade,
            max_portfolio_risk=level.max_portfolio_risk,
            max_drawdown={
                RiskLevel.CONSERVATIVE: 0.05,
                RiskLevel.MODERATE: 0.12,
                RiskLevel.AGGRESSIVE: 0.25,
            }[level],
            min_risk_reward=level.min_risk_reward,
            max_consecutive_losses={
                RiskLevel.CONSERVATIVE: 3,
                RiskLevel.MODERATE: 5,
                RiskLevel.AGGRESSIVE: 8,
            }[level],
        )


# Predefined profiles
RISK_PROFILES = {
    "scalper": RiskProfile.from_level(RiskLevel.AGGRESSIVE),
    "day_trader": RiskProfile.from_level(RiskLevel.MODERATE),
    "swing": RiskProfile.from_level(RiskLevel.MODERATE),
    "position": RiskProfile.from_level(RiskLevel.CONSERVATIVE),
    "conservative": RiskProfile.from_level(RiskLevel.CONSERVATIVE),
}