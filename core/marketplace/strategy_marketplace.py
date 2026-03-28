"""
Module: core/marketplace/strategy_marketplace.py
Responsibility: Strategy marketplace — publish, discover, subscribe and review
Dependencies: marketplace.models, strategy_registry, backtesting, logger
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from core.marketplace.models import (
    ListingStatus,
    MarketplaceReview,
    MarketplaceStats,
    StrategyListing,
    Subscription,
    SubscriptionTier,
)
from core.observability.logger import get_logger

logger = get_logger(__name__)


class StrategyMarketplace:
    """In-memory marketplace store.

    In production this maps to a PostgreSQL table.  The interface is designed
    so that swapping the backing store requires only changes inside this class.
    """

    def __init__(self):
        self._listings: dict[str, StrategyListing] = {}
        self._reviews: dict[str, list[MarketplaceReview]] = {}   # listing_id → reviews
        self._subscriptions: dict[str, list[Subscription]] = {}  # user_id → subs

    # ── Publishing ─────────────────────────────────────────────────────────

    def publish(
        self,
        strategy_id: str,
        author_id: str,
        name: str,
        description: str,
        tags: list[str] | None = None,
        tier: SubscriptionTier = SubscriptionTier.FREE,
        price_usd_monthly: float = 0.0,
        strategy_config: dict | None = None,
    ) -> StrategyListing:
        listing = StrategyListing(
            listing_id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            author_id=author_id,
            name=name,
            description=description,
            tags=tags or [],
            tier=tier,
            price_usd_monthly=price_usd_monthly,
            status=ListingStatus.PENDING,
            strategy_config=strategy_config,
        )
        self._listings[listing.listing_id] = listing
        logger.info(
            "marketplace_listing_published",
            listing_id=listing.listing_id,
            strategy_id=strategy_id,
            author_id=author_id,
        )
        return listing

    def approve(self, listing_id: str) -> StrategyListing:
        listing = self._get_or_raise(listing_id)
        listing.status = ListingStatus.ACTIVE
        listing.updated_at = datetime.utcnow()
        logger.info("marketplace_listing_approved", listing_id=listing_id)
        return listing

    def reject(self, listing_id: str, reason: str = "") -> StrategyListing:
        listing = self._get_or_raise(listing_id)
        listing.status = ListingStatus.REJECTED
        listing.updated_at = datetime.utcnow()
        logger.warning("marketplace_listing_rejected", listing_id=listing_id, reason=reason)
        return listing

    def suspend(self, listing_id: str) -> StrategyListing:
        listing = self._get_or_raise(listing_id)
        listing.status = ListingStatus.SUSPENDED
        listing.updated_at = datetime.utcnow()
        logger.warning("marketplace_listing_suspended", listing_id=listing_id)
        return listing

    # ── Discovery ──────────────────────────────────────────────────────────

    def list_active(
        self,
        tag: Optional[str] = None,
        tier: Optional[SubscriptionTier] = None,
        sort_by: str = "subscriber_count",
        limit: int = 50,
    ) -> list[dict]:
        active = [
            l for l in self._listings.values()
            if l.status == ListingStatus.ACTIVE
        ]
        if tag:
            active = [l for l in active if tag.lower() in [t.lower() for t in l.tags]]
        if tier:
            active = [l for l in active if l.tier == tier]

        sort_key = {
            "subscriber_count": lambda l: l.subscriber_count,
            "sharpe": lambda l: l.backtest_sharpe or 0.0,
            "win_rate": lambda l: l.backtest_win_rate or 0.0,
        }.get(sort_by, lambda l: l.subscriber_count)

        active.sort(key=sort_key, reverse=True)
        return [l.public_view() for l in active[:limit]]

    def get_listing(self, listing_id: str, requester_id: Optional[str] = None) -> dict:
        listing = self._get_or_raise(listing_id)
        is_subscribed = self._is_subscribed(requester_id, listing_id) if requester_id else False
        return listing.subscriber_view() if is_subscribed else listing.public_view()

    # ── Reviews ────────────────────────────────────────────────────────────

    def add_review(
        self,
        listing_id: str,
        reviewer_id: str,
        rating: int,
        comment: str = "",
    ) -> MarketplaceReview:
        self._get_or_raise(listing_id)  # validates listing exists
        review = MarketplaceReview(
            review_id=str(uuid.uuid4()),
            listing_id=listing_id,
            reviewer_id=reviewer_id,
            rating=rating,
            comment=comment,
        )
        self._reviews.setdefault(listing_id, []).append(review)
        logger.info(
            "marketplace_review_added",
            listing_id=listing_id,
            reviewer_id=reviewer_id,
            rating=rating,
        )
        return review

    def get_reviews(self, listing_id: str) -> list[dict]:
        return [r.model_dump() for r in self._reviews.get(listing_id, [])]

    def average_rating(self, listing_id: str) -> Optional[float]:
        reviews = self._reviews.get(listing_id, [])
        if not reviews:
            return None
        return round(sum(r.rating for r in reviews) / len(reviews), 2)

    # ── Subscriptions ──────────────────────────────────────────────────────

    def subscribe(
        self,
        user_id: str,
        listing_id: str,
        tier: SubscriptionTier = SubscriptionTier.FREE,
    ) -> Subscription:
        listing = self._get_or_raise(listing_id)
        if listing.status != ListingStatus.ACTIVE:
            raise ValueError(f"Listing {listing_id} is not active")

        sub = Subscription(
            subscription_id=str(uuid.uuid4()),
            user_id=user_id,
            listing_id=listing_id,
            tier=tier,
        )
        self._subscriptions.setdefault(user_id, []).append(sub)
        listing.subscriber_count += 1
        listing.updated_at = datetime.utcnow()

        logger.info(
            "marketplace_subscription_created",
            user_id=user_id,
            listing_id=listing_id,
            tier=tier,
        )
        return sub

    def unsubscribe(self, user_id: str, listing_id: str) -> None:
        subs = self._subscriptions.get(user_id, [])
        for sub in subs:
            if sub.listing_id == listing_id and sub.active:
                sub.active = False
                listing = self._listings.get(listing_id)
                if listing:
                    listing.subscriber_count = max(0, listing.subscriber_count - 1)
                logger.info(
                    "marketplace_subscription_cancelled",
                    user_id=user_id,
                    listing_id=listing_id,
                )
                return
        raise KeyError(f"Active subscription not found for user {user_id}, listing {listing_id}")

    def get_user_subscriptions(self, user_id: str) -> list[dict]:
        return [
            s.model_dump()
            for s in self._subscriptions.get(user_id, [])
            if s.active
        ]

    # ── Stats ──────────────────────────────────────────────────────────────

    def get_stats(self) -> MarketplaceStats:
        active = [l for l in self._listings.values() if l.status == ListingStatus.ACTIVE]
        sharpe_values = [l.backtest_sharpe for l in active if l.backtest_sharpe is not None]
        top = max(active, key=lambda l: l.subscriber_count, default=None)

        return MarketplaceStats(
            total_listings=len(self._listings),
            active_listings=len(active),
            total_subscribers=sum(l.subscriber_count for l in active),
            top_strategy_id=top.strategy_id if top else None,
            avg_sharpe=round(sum(sharpe_values) / len(sharpe_values), 3) if sharpe_values else None,
        )

    def update_performance(
        self,
        listing_id: str,
        backtest_sharpe: Optional[float] = None,
        backtest_win_rate: Optional[float] = None,
        backtest_max_drawdown: Optional[float] = None,
        backtest_profit_factor: Optional[float] = None,
    ) -> None:
        listing = self._get_or_raise(listing_id)
        if backtest_sharpe is not None:
            listing.backtest_sharpe = backtest_sharpe
        if backtest_win_rate is not None:
            listing.backtest_win_rate = backtest_win_rate
        if backtest_max_drawdown is not None:
            listing.backtest_max_drawdown = backtest_max_drawdown
        if backtest_profit_factor is not None:
            listing.backtest_profit_factor = backtest_profit_factor
        listing.updated_at = datetime.utcnow()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _get_or_raise(self, listing_id: str) -> StrategyListing:
        listing = self._listings.get(listing_id)
        if not listing:
            raise KeyError(f"Listing not found: {listing_id}")
        return listing

    def _is_subscribed(self, user_id: str, listing_id: str) -> bool:
        return any(
            s.listing_id == listing_id and s.active
            for s in self._subscriptions.get(user_id, [])
        )
