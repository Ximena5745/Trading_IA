"""
Module: core/marketplace/models.py
Responsibility: Pydantic models for the strategy marketplace
Dependencies: pydantic
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class ListingStatus(str, Enum):
    PENDING = "pending"  # awaiting review
    ACTIVE = "active"  # live in marketplace
    SUSPENDED = "suspended"  # temporarily hidden
    REJECTED = "rejected"  # failed review


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class StrategyListing(BaseModel):
    """A strategy published to the marketplace."""

    listing_id: str
    strategy_id: str
    author_id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    tier: SubscriptionTier = SubscriptionTier.FREE
    price_usd_monthly: float = 0.0
    status: ListingStatus = ListingStatus.PENDING

    # Performance snapshot (updated periodically)
    backtest_sharpe: float | None = None
    backtest_win_rate: float | None = None
    backtest_max_drawdown: float | None = None
    backtest_profit_factor: float | None = None
    live_sharpe: float | None = None
    live_win_rate: float | None = None
    subscriber_count: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Strategy JSON config (stored but only exposed to subscribers)
    strategy_config: dict[str, Any] | None = None

    @field_validator("price_usd_monthly")
    @classmethod
    def price_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Price cannot be negative")
        return v

    def public_view(self) -> dict:
        """Return a safe public dict without the strategy config."""
        d = self.model_dump(exclude={"strategy_config"})
        return d

    def subscriber_view(self) -> dict:
        """Return full details including config (for subscribers)."""
        return self.model_dump()


class MarketplaceReview(BaseModel):
    """User review for a marketplace listing."""

    review_id: str
    listing_id: str
    reviewer_id: str
    rating: int = Field(ge=1, le=5)
    comment: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Subscription(BaseModel):
    """A user's active subscription to a marketplace listing."""

    subscription_id: str
    user_id: str
    listing_id: str
    tier: SubscriptionTier
    active: bool = True
    subscribed_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class MarketplaceStats(BaseModel):
    """Aggregate stats for the marketplace."""

    total_listings: int = 0
    active_listings: int = 0
    total_subscribers: int = 0
    top_strategy_id: str | None = None
    avg_sharpe: float | None = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)
