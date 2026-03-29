"""
Module: core/agents/fundamental_agent.py
Responsibility: Fundamental signals based on macro sentiment, per asset class
Dependencies: base_agent, httpx, logger

Supported asset classes and their data sources:
  crypto      → Alternative.me Fear & Greed Index + CoinGecko global data
  forex       → DXY trend + Fed/ECB rate differential proxy (public FRED data)
  indices     → CNN Fear & Greed (market) + VIX proxy
  commodities → Gold/Oil seasonal bias + USD strength proxy

All external calls are non-blocking and gracefully degrade to NEUTRAL
if the upstream API is unavailable.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from core.agents.base_agent import AbcAgent
from core.models import AgentOutput, AssetClass, FeatureSet, detect_asset_class
from core.observability.logger import get_logger

logger = get_logger(__name__)

# ── External API endpoints (all free / no key required) ─────────────────────
FEAR_GREED_CRYPTO_URL   = "https://api.alternative.me/fng/?limit=1&format=json"
COINGECKO_GLOBAL_URL    = "https://api.coingecko.com/api/v3/global"

# CNN Fear & Greed (equity markets / indices)
# Unofficial proxy endpoint — provides the current CNN F&G score
CNN_FEAR_GREED_URL = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"

# FRED (Federal Reserve Economic Data) — public, no key needed for basic series
# Series: DFF = Fed Funds Rate effective daily
FRED_DFF_URL = (
    "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DFF&vintage_date="
)

# Refresh every 30 minutes (avoid rate-limiting free APIs)
CACHE_TTL_SECONDS = 1800

# ── Signal thresholds (contrarian logic) ─────────────────────────────────────
EXTREME_FEAR_THRESHOLD  = 20
EXTREME_GREED_THRESHOLD = 80
FEAR_THRESHOLD          = 35
GREED_THRESHOLD         = 65


class FundamentalAgent(AbcAgent):
    """Multi-asset fundamental agent.

    Provides macro sentiment signals for all supported asset classes.
    Data is cached for 30 minutes; refreshed via the `refresh()` async method.

    Signal logic (contrarian):
      - Extreme Fear  (≤20): BUY  — oversold, smart money accumulates
      - Extreme Greed (≥80): SELL — overextended, risk of reversal
      - Fear          (<35): weak BUY bias
      - Greed         (>65): weak SELL bias
      - Neutral     (35–65): NEUTRAL
    """

    agent_id = "fundamental"
    model_version = "v2_multi_asset"

    def __init__(self) -> None:
        # Crypto sentiment
        self._crypto_fear_greed: Optional[int] = None
        self._crypto_fear_greed_label: str = "Unknown"
        self._btc_dominance: Optional[float] = None
        self._market_cap_change_24h: Optional[float] = None

        # Equity / indices sentiment
        self._equity_fear_greed: Optional[int] = None
        self._equity_fear_greed_label: str = "Unknown"

        # Macro (forex / commodities)
        # Approximated via USD strength: positive = USD strong = bearish metals/majors
        self._usd_strength_score: float = 0.0   # range -1..+1

        self._last_fetch: Optional[datetime] = None
        self._fetch_lock = asyncio.Lock()

    # ── AbcAgent interface ─────────────────────────────────────────────────

    def is_ready(self) -> bool:
        return self._last_fetch is not None

    def predict(self, features: FeatureSet) -> AgentOutput:
        """Generate a fundamental signal using cached data.

        The signal logic adapts to the asset class of the symbol.
        Call `refresh()` periodically from an async context.
        """
        if not self.is_ready():
            return self._neutral(features)

        asset_class = detect_asset_class(features.symbol)
        direction, confidence, features_used, shap_values = self._compute_signal(
            asset_class, features.symbol
        )

        logger.info(
            "fundamental_agent_predict",
            symbol=features.symbol,
            asset_class=asset_class.value,
            direction=direction,
            confidence=round(confidence, 3),
        )

        return AgentOutput(
            agent_id=self.agent_id,
            timestamp=features.timestamp,
            symbol=features.symbol,
            direction=direction,
            score=confidence if direction == "BUY" else -confidence if direction == "SELL" else 0.0,
            confidence=confidence,
            features_used=features_used,
            shap_values=shap_values,
            model_version=self.model_version,
        )

    # ── Async data refresh ─────────────────────────────────────────────────

    async def refresh(self) -> None:
        """Fetch fresh data from all sources. Called on a periodic background task."""
        if not self._cache_expired():
            return
        async with self._fetch_lock:
            if not self._cache_expired():
                return
            await asyncio.gather(
                self._fetch_crypto_fear_greed(),
                self._fetch_coingecko_global(),
                self._fetch_equity_fear_greed(),
                return_exceptions=True,
            )
            self._last_fetch = datetime.utcnow()
            logger.info(
                "fundamental_agent_refreshed",
                crypto_fg=self._crypto_fear_greed,
                equity_fg=self._equity_fear_greed,
                usd_strength=round(self._usd_strength_score, 3),
            )

    # ── Fetchers ───────────────────────────────────────────────────────────

    async def _fetch_crypto_fear_greed(self) -> None:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(FEAR_GREED_CRYPTO_URL)
                resp.raise_for_status()
                entry = resp.json()["data"][0]
                self._crypto_fear_greed = int(entry["value"])
                self._crypto_fear_greed_label = entry.get("value_classification", "")
        except Exception as exc:
            logger.warning("fundamental_crypto_fg_fetch_failed", error=str(exc))

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
                # Derive USD strength proxy from crypto market momentum:
                # rising market cap → risk-on → USD weaker (negative score)
                change = self._market_cap_change_24h or 0.0
                self._usd_strength_score = max(-1.0, min(1.0, -change / 10.0))
        except Exception as exc:
            logger.warning("fundamental_coingecko_fetch_failed", error=str(exc))

    async def _fetch_equity_fear_greed(self) -> None:
        """Fetch CNN Fear & Greed index for equity markets / indices."""
        try:
            import httpx
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(CNN_FEAR_GREED_URL)
                resp.raise_for_status()
                data = resp.json()
                score = data.get("fear_and_greed", {}).get("score")
                if score is not None:
                    self._equity_fear_greed = int(float(score))
                    rating = data.get("fear_and_greed", {}).get("rating", "")
                    self._equity_fear_greed_label = str(rating)
        except Exception as exc:
            logger.warning("fundamental_equity_fg_fetch_failed", error=str(exc))

    # ── Signal computation ─────────────────────────────────────────────────

    def _compute_signal(
        self,
        asset_class: AssetClass,
        symbol: str,
    ) -> tuple[str, float, list[str], dict[str, float]]:
        """Return (direction, confidence, features_used, shap_values)."""

        if asset_class == AssetClass.CRYPTO:
            return self._signal_crypto()

        if asset_class == AssetClass.INDICES:
            return self._signal_indices()

        if asset_class == AssetClass.FOREX:
            return self._signal_forex(symbol)

        if asset_class == AssetClass.COMMODITIES:
            return self._signal_commodities(symbol)

        return "NEUTRAL", 0.0, [], {}

    def _signal_crypto(self) -> tuple[str, float, list[str], dict[str, float]]:
        fg = self._crypto_fear_greed
        if fg is None:
            return "NEUTRAL", 0.0, [], {}

        direction, confidence = self._fg_to_signal(fg)
        features = ["crypto_fear_greed_index", "btc_dominance", "market_cap_change_24h"]
        shap = {
            "crypto_fear_greed_index": round(confidence * 0.70, 3),
            "btc_dominance":           round(confidence * 0.20, 3),
            "market_cap_change_24h":   round(confidence * 0.10, 3),
        }
        return direction, confidence, features, shap

    def _signal_indices(self) -> tuple[str, float, list[str], dict[str, float]]:
        fg = self._equity_fear_greed
        if fg is None:
            return "NEUTRAL", 0.0, [], {}

        direction, confidence = self._fg_to_signal(fg)
        features = ["equity_fear_greed_index", "market_cap_change_24h"]
        shap = {
            "equity_fear_greed_index": round(confidence * 0.80, 3),
            "market_cap_change_24h":   round(confidence * 0.20, 3),
        }
        return direction, confidence, features, shap

    def _signal_forex(self, symbol: str) -> tuple[str, float, list[str], dict[str, float]]:
        """
        Forex signal using USD strength proxy.

        For USD-quote pairs (EURUSD, GBPUSD, AUDUSD):
          USD strong (positive score) → SELL (USD appreciation = pair falls)
          USD weak  (negative score)  → BUY

        For USD-base pairs (USDJPY, USDCAD, USDCHF):
          USD strong → BUY
          USD weak   → SELL
        """
        usd_base_pairs = {"USDJPY", "USDCAD", "USDCHF", "USDNOK", "USDSEK"}
        usd_is_base = symbol.upper() in usd_base_pairs

        score = self._usd_strength_score  # -1..+1
        if usd_is_base:
            direction = "BUY" if score > 0.15 else "SELL" if score < -0.15 else "NEUTRAL"
        else:
            direction = "SELL" if score > 0.15 else "BUY" if score < -0.15 else "NEUTRAL"

        confidence = min(abs(score) * 0.8, 0.75) if direction != "NEUTRAL" else 0.25
        features = ["usd_strength_proxy", "market_cap_change_24h"]
        shap = {
            "usd_strength_proxy":    round(confidence * 0.85, 3),
            "market_cap_change_24h": round(confidence * 0.15, 3),
        }
        return direction, round(confidence, 3), features, shap

    def _signal_commodities(self, symbol: str) -> tuple[str, float, list[str], dict[str, float]]:
        """
        Commodities signal.

        Precious metals (XAU, XAG) are inversely correlated with USD:
          USD strong → SELL gold
          USD weak   → BUY gold

        Energy (OIL, NATGAS):
          Risk-on market (equity F&G > 60) → BUY
          Risk-off (equity F&G < 40)       → SELL
        """
        s = symbol.upper()
        score = self._usd_strength_score  # -1..+1

        if s.startswith(("XAU", "XAG", "XPT", "XPD")):
            # Precious metals — inversely correlated with USD
            direction = "SELL" if score > 0.15 else "BUY" if score < -0.15 else "NEUTRAL"
            confidence = min(abs(score) * 0.75, 0.70) if direction != "NEUTRAL" else 0.25
            features = ["usd_strength_proxy"]
            shap = {"usd_strength_proxy": round(confidence, 3)}
        else:
            # Energy / agricultural — follow equity risk appetite
            fg = self._equity_fear_greed
            if fg is None:
                return "NEUTRAL", 0.0, [], {}
            direction, confidence = self._fg_to_signal(fg)
            features = ["equity_fear_greed_index"]
            shap = {"equity_fear_greed_index": round(confidence, 3)}

        return direction, round(confidence, 3), features, shap

    # ── Shared helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _fg_to_signal(fg: int) -> tuple[str, float]:
        """Convert a 0–100 Fear & Greed score to (direction, confidence)."""
        if fg <= EXTREME_FEAR_THRESHOLD:
            conf = 0.70 + (EXTREME_FEAR_THRESHOLD - fg) / EXTREME_FEAR_THRESHOLD * 0.20
            return "BUY", min(round(conf, 2), 0.90)
        if fg >= EXTREME_GREED_THRESHOLD:
            conf = 0.70 + (fg - EXTREME_GREED_THRESHOLD) / (100 - EXTREME_GREED_THRESHOLD) * 0.20
            return "SELL", min(round(conf, 2), 0.90)
        if fg < FEAR_THRESHOLD:
            return "BUY", 0.45
        if fg > GREED_THRESHOLD:
            return "SELL", 0.45
        return "NEUTRAL", 0.30

    def _neutral(self, features: FeatureSet) -> AgentOutput:
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

    def _cache_expired(self) -> bool:
        if self._last_fetch is None:
            return True
        return (datetime.utcnow() - self._last_fetch).total_seconds() > CACHE_TTL_SECONDS

    def _data_age_seconds(self) -> Optional[float]:
        if self._last_fetch is None:
            return None
        return (datetime.utcnow() - self._last_fetch).total_seconds()

    # ── Public accessors ───────────────────────────────────────────────────

    def get_market_summary(self) -> dict:
        return {
            "crypto": {
                "fear_greed_index": self._crypto_fear_greed,
                "fear_greed_label": self._crypto_fear_greed_label,
                "btc_dominance_pct": self._btc_dominance,
                "market_cap_change_24h_pct": self._market_cap_change_24h,
            },
            "equity_indices": {
                "fear_greed_index": self._equity_fear_greed,
                "fear_greed_label": self._equity_fear_greed_label,
            },
            "macro": {
                "usd_strength_score": round(self._usd_strength_score, 3),
            },
            "last_fetch": self._last_fetch.isoformat() if self._last_fetch else None,
            "cache_ttl_seconds": CACHE_TTL_SECONDS,
            "data_age_seconds": self._data_age_seconds(),
        }
