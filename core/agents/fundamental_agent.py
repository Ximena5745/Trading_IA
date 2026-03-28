"""
Module: core/agents/fundamental_agent.py
Responsibility: Fundamental signals — Fear & Greed index + on-chain data (Fase 5)
Dependencies: base_agent, httpx, logger
"""

from __future__ import annotations

import asyncio
from datetime import datetime

from core.agents.base_agent import AbcAgent
from core.models import AgentOutput, FeatureSet
from core.observability.logger import get_logger

logger = get_logger(__name__)

# alternative.me API — free, no key required
FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1&format=json"

# CoinGecko — free tier
COINGECKO_GLOBAL_URL = "https://api.coingecko.com/api/v3/global"

# Refresh every 30 minutes (avoid rate-limiting free APIs)
CACHE_TTL_SECONDS = 1800

# Signal thresholds (contrarian logic)
EXTREME_FEAR_THRESHOLD = 20
EXTREME_GREED_THRESHOLD = 80
FEAR_THRESHOLD = 35
GREED_THRESHOLD = 65


class FundamentalAgent(AbcAgent):
    """Fundamental agent using macro crypto sentiment data.

    Data sources (all free/public):
      1. Alternative.me Fear & Greed Index (0–100)
      2. CoinGecko global market data (BTC dominance, market cap change 24h)

    Signal logic (contrarian):
      - Extreme Fear  (≤20): BUY  — market oversold, smart money accumulates
      - Extreme Greed (≥80): SELL — market overextended, risk of reversal
      - Fear          (<35): weak BUY bias
      - Greed         (>65): weak SELL bias
      - Neutral     (35–65): NEUTRAL
    """

    agent_id = "fundamental"
    model_version = "v1_fear_greed"

    def __init__(self):
        self._fear_greed: int | None = None
        self._fear_greed_label: str = "Unknown"
        self._btc_dominance: float | None = None
        self._market_cap_change_24h: float | None = None
        self._last_fetch: datetime | None = None
        self._fetch_lock = asyncio.Lock()

    # ── AbcAgent interface ─────────────────────────────────────────────────

    def is_ready(self) -> bool:
        return self._fear_greed is not None

    def predict(self, features: FeatureSet) -> AgentOutput:
        """Generate a fundamental signal using cached data.

        Call `refresh()` periodically from an async context to keep data fresh.
        """
        if not self.is_ready():
            return AgentOutput(
                agent_id=self.agent_id,
                timestamp=features.timestamp,
                symbol=features.symbol,
                direction="NEUTRAL",
                score=0.0,
                confidence=0.0,
                features_used=[],
                shap_values={},
                model_version=self.model_version,
            )

        direction, confidence = self._compute_signal()

        logger.info(
            "fundamental_agent_predict",
            symbol=features.symbol,
            direction=direction,
            confidence=round(confidence, 3),
            fear_greed=self._fear_greed,
            label=self._fear_greed_label,
            btc_dominance=self._btc_dominance,
        )

        return AgentOutput(
            agent_id=self.agent_id,
            timestamp=features.timestamp,
            symbol=features.symbol,
            direction=direction,
            score=(
                confidence
                if direction == "BUY"
                else -confidence if direction == "SELL" else 0.0
            ),
            confidence=confidence,
            features_used=[
                "fear_greed_index",
                "btc_dominance",
                "market_cap_change_24h",
            ],
            shap_values={
                "fear_greed_index": round(confidence * 0.7, 3),
                "btc_dominance": round(confidence * 0.2, 3),
                "market_cap_change_24h": round(confidence * 0.1, 3),
            },
            model_version=self.model_version,
        )

    # ── Data fetching ──────────────────────────────────────────────────────

    async def refresh(self) -> None:
        """Fetch fresh data from all sources. Call on a periodic background task."""
        if not self._cache_expired():
            return

        async with self._fetch_lock:
            if not self._cache_expired():
                return
            await asyncio.gather(
                self._fetch_fear_greed(),
                self._fetch_coingecko_global(),
                return_exceptions=True,
            )
            self._last_fetch = datetime.utcnow()
            logger.info(
                "fundamental_agent_refreshed",
                fear_greed=self._fear_greed,
                label=self._fear_greed_label,
                btc_dominance=self._btc_dominance,
            )

    async def _fetch_fear_greed(self) -> None:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(FEAR_GREED_URL)
                resp.raise_for_status()
                data = resp.json()
                entry = data["data"][0]
                self._fear_greed = int(entry["value"])
                self._fear_greed_label = entry.get("value_classification", "")
        except Exception as exc:
            logger.warning("fundamental_fear_greed_fetch_failed", error=str(exc))

    async def _fetch_coingecko_global(self) -> None:
        try:
            import httpx

            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(COINGECKO_GLOBAL_URL)
                resp.raise_for_status()
                data = resp.json().get("data", {})
                self._btc_dominance = data.get("market_cap_percentage", {}).get("btc")
                self._market_cap_change_24h = data.get(
                    "market_cap_change_percentage_24h_usd"
                )
        except Exception as exc:
            logger.warning("fundamental_coingecko_fetch_failed", error=str(exc))

    # ── Signal computation ─────────────────────────────────────────────────

    def _compute_signal(self) -> tuple[str, float]:
        fg = self._fear_greed
        if fg is None:
            return "NEUTRAL", 0.0

        if fg <= EXTREME_FEAR_THRESHOLD:
            base_conf = (
                0.70 + (EXTREME_FEAR_THRESHOLD - fg) / EXTREME_FEAR_THRESHOLD * 0.20
            )
            return "BUY", min(round(base_conf, 2), 0.90)

        if fg >= EXTREME_GREED_THRESHOLD:
            base_conf = (
                0.70
                + (fg - EXTREME_GREED_THRESHOLD)
                / (100 - EXTREME_GREED_THRESHOLD)
                * 0.20
            )
            return "SELL", min(round(base_conf, 2), 0.90)

        if fg < FEAR_THRESHOLD:
            return "BUY", 0.45

        if fg > GREED_THRESHOLD:
            return "SELL", 0.45

        return "NEUTRAL", 0.30

    def _cache_expired(self) -> bool:
        if self._last_fetch is None:
            return True
        return (
            datetime.utcnow() - self._last_fetch
        ).total_seconds() > CACHE_TTL_SECONDS

    def _data_age_seconds(self) -> float | None:
        if self._last_fetch is None:
            return None
        return (datetime.utcnow() - self._last_fetch).total_seconds()

    # ── Public accessors ───────────────────────────────────────────────────

    def get_fear_greed(self) -> int | None:
        return self._fear_greed

    def get_fear_greed_label(self) -> str:
        return self._fear_greed_label

    def get_market_summary(self) -> dict:
        return {
            "fear_greed_index": self._fear_greed,
            "fear_greed_label": self._fear_greed_label,
            "btc_dominance_pct": self._btc_dominance,
            "market_cap_change_24h_pct": self._market_cap_change_24h,
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "data_age_seconds": self._data_age_seconds(),
        }
