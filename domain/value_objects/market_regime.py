"""
Value Object: MarketRegime
Responsibility: Represent market regime/states for trading decisions.
"""
from __future__ import annotations

from enum import Enum


class MarketRegime(str, Enum):
    # Trending regimes
    BULL_TRENDING_STRONG = "bull_trending_strong"
    BULL_TRENDING_WEAK = "bull_trending_weak"
    BEAR_TRENDING_STRONG = "bear_trending_strong"
    BEAR_TRENDING_WEAK = "bear_trending_weak"

    # Range-bound regimes
    RANGE_BOUND_NARROW = "range_bound_narrow"
    RANGE_BOUND_WIDE = "range_bound_wide"

    # Special regimes
    TRANSITION = "transition"
    CRISIS = "crisis"

    # Legacy aliases for backward compatibility
    BULL_TRENDING = "bull_trending"
    BEAR_TRENDING = "bear_trending"
    SIDEWAYS_LOW_VOL = "sideways_low_vol"
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"

    def is_trending(self) -> bool:
        return self in (
            MarketRegime.BULL_TRENDING_STRONG,
            MarketRegime.BULL_TRENDING_WEAK,
            MarketRegime.BEAR_TRENDING_STRONG,
            MarketRegime.BEAR_TRENDING_WEAK,
            MarketRegime.BULL_TRENDING,
            MarketRegime.BEAR_TRENDING,
        )

    def is_bullish(self) -> bool:
        return self in (
            MarketRegime.BULL_TRENDING_STRONG,
            MarketRegime.BULL_TRENDING_WEAK,
            MarketRegime.BULL_TRENDING,
        )

    def is_bearish(self) -> bool:
        return self in (
            MarketRegime.BEAR_TRENDING_STRONG,
            MarketRegime.BEAR_TRENDING_WEAK,
            MarketRegime.BEAR_TRENDING,
        )

    def is_range_bound(self) -> bool:
        return self in (
            MarketRegime.RANGE_BOUND_NARROW,
            MarketRegime.RANGE_BOUND_WIDE,
            MarketRegime.SIDEWAYS_LOW_VOL,
            MarketRegime.SIDEWAYS_HIGH_VOL,
        )

    def should_trade(self) -> bool:
        """Gate: some regimes should block trading."""
        return self not in (MarketRegime.CRISIS, MarketRegime.TRANSITION)