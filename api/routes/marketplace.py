"""
Module: api/routes/marketplace.py
Responsibility: Strategy marketplace endpoints — publish, discover, subscribe, review
Dependencies: strategy_marketplace, auth dependencies
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_current_user, require_admin, require_trader
from core.marketplace.models import SubscriptionTier
from core.marketplace.strategy_marketplace import StrategyMarketplace
from core.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/marketplace", tags=["marketplace"])

_marketplace: StrategyMarketplace | None = None


def set_marketplace(mp: StrategyMarketplace) -> None:
    global _marketplace
    _marketplace = mp


def _get_mp() -> StrategyMarketplace:
    if _marketplace is None:
        raise RuntimeError("StrategyMarketplace not initialized")
    return _marketplace


# ── Request models ─────────────────────────────────────────────────────────


class PublishRequest(BaseModel):
    strategy_id: str
    name: str
    description: str
    tags: list[str] = Field(default_factory=list)
    tier: SubscriptionTier = SubscriptionTier.FREE
    price_usd_monthly: float = 0.0


class ReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""


class SubscribeRequest(BaseModel):
    tier: SubscriptionTier = SubscriptionTier.FREE


# ── Endpoints ──────────────────────────────────────────────────────────────


@router.get("")
async def list_listings(
    tag: str | None = None,
    tier: SubscriptionTier | None = None,
    sort_by: str = "subscriber_count",
    limit: int = 50,
    user=Depends(get_current_user),
):
    """List active marketplace listings with optional filters."""
    mp = _get_mp()
    listings = mp.list_active(tag=tag, tier=tier, sort_by=sort_by, limit=limit)
    return {"listings": listings, "total": len(listings)}


@router.get("/stats")
async def get_marketplace_stats(user=Depends(get_current_user)):
    """Return aggregate marketplace statistics."""
    mp = _get_mp()
    return mp.get_stats().model_dump()


@router.get("/{listing_id}")
async def get_listing(listing_id: str, user=Depends(get_current_user)):
    """Get listing details. Subscribers see full config."""
    mp = _get_mp()
    try:
        return mp.get_listing(listing_id, requester_id=user.get("sub"))
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")


@router.post(
    "", dependencies=[Depends(require_trader)], status_code=status.HTTP_201_CREATED
)
async def publish_strategy(body: PublishRequest, user=Depends(get_current_user)):
    """Publish a registered strategy to the marketplace."""
    mp = _get_mp()
    listing = mp.publish(
        strategy_id=body.strategy_id,
        author_id=user.get("sub", "unknown"),
        name=body.name,
        description=body.description,
        tags=body.tags,
        tier=body.tier,
        price_usd_monthly=body.price_usd_monthly,
    )
    return {"status": "pending_review", "listing_id": listing.listing_id}


@router.post("/{listing_id}/approve", dependencies=[Depends(require_admin)])
async def approve_listing(listing_id: str, user=Depends(get_current_user)):
    """Admin: approve a pending listing."""
    mp = _get_mp()
    try:
        listing = mp.approve(listing_id)
        return {"status": "approved", "listing_id": listing.listing_id}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")


@router.post("/{listing_id}/reject", dependencies=[Depends(require_admin)])
async def reject_listing(
    listing_id: str, reason: str = "", user=Depends(get_current_user)
):
    """Admin: reject a pending listing."""
    mp = _get_mp()
    try:
        mp.reject(listing_id, reason=reason)
        return {"status": "rejected", "listing_id": listing_id}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")


@router.post("/{listing_id}/subscribe")
async def subscribe(
    listing_id: str, body: SubscribeRequest, user=Depends(get_current_user)
):
    """Subscribe to a marketplace listing."""
    mp = _get_mp()
    try:
        sub = mp.subscribe(
            user_id=user.get("sub", "unknown"),
            listing_id=listing_id,
            tier=body.tier,
        )
        return {"status": "subscribed", "subscription_id": sub.subscription_id}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{listing_id}/subscribe")
async def unsubscribe(listing_id: str, user=Depends(get_current_user)):
    """Cancel subscription to a listing."""
    mp = _get_mp()
    try:
        mp.unsubscribe(user_id=user.get("sub", "unknown"), listing_id=listing_id)
        return {"status": "unsubscribed", "listing_id": listing_id}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/me/subscriptions")
async def my_subscriptions(user=Depends(get_current_user)):
    """Return the current user's active subscriptions."""
    mp = _get_mp()
    subs = mp.get_user_subscriptions(user.get("sub", "unknown"))
    return {"subscriptions": subs, "total": len(subs)}


@router.post("/{listing_id}/reviews", status_code=status.HTTP_201_CREATED)
async def add_review(
    listing_id: str, body: ReviewRequest, user=Depends(get_current_user)
):
    """Submit a rating and review for a listing."""
    mp = _get_mp()
    try:
        review = mp.add_review(
            listing_id=listing_id,
            reviewer_id=user.get("sub", "unknown"),
            rating=body.rating,
            comment=body.comment,
        )
        return {"status": "created", "review_id": review.review_id}
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Listing {listing_id} not found")


@router.get("/{listing_id}/reviews")
async def get_reviews(listing_id: str, user=Depends(get_current_user)):
    """Get all reviews for a listing."""
    mp = _get_mp()
    reviews = mp.get_reviews(listing_id)
    avg = mp.average_rating(listing_id)
    return {"reviews": reviews, "average_rating": avg, "total": len(reviews)}
