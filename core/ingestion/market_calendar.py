"""
Module: core/ingestion/market_calendar.py
Responsibility: Determine if a market is open and detect high-impact macro events.
  - Forex/indices: session-based (Sydney, Tokyo, London, New York — UTC)
  - High-impact events: ForexFactory RSS feed (free, no key required)
  - Crypto: always open — is_market_open() returns True for CRYPTO assets
  - Decision v2.4: LOW_LIQUIDITY (Asian session) logs warning, does NOT block

Event blocking window: ±30 minutes around NFP, CPI, rate decisions (impact=3)
Cache TTL: 4 hours (ForexFactory feed is slow-changing during the day)
"""
from __future__ import annotations

import asyncio
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Optional

from core.models import AssetClass, detect_asset_class
from core.observability.logger import get_logger

logger = get_logger(__name__)

# ── ForexFactory RSS (free, no key) ─────────────────────────────────────────
FOREX_FACTORY_RSS = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
EVENT_BLOCK_MINUTES = 30  # block ± this many minutes around high-impact events
HIGH_IMPACT_MARKER = "High"
CACHE_TTL_SECONDS = 4 * 3600

# ── Forex / Index market sessions (UTC) ─────────────────────────────────────
# Each session: (open_hour, open_min, close_hour, close_min)
# Overlapping sessions are the most liquid periods
SESSIONS_UTC: dict[str, tuple[int, int, int, int]] = {
    "sydney": (21, 0, 6, 0),  # Sun 21:00 – Fri 06:00 UTC
    "tokyo": (0, 0, 9, 0),  # 00:00 – 09:00 UTC
    "london": (7, 0, 16, 0),  # 07:00 – 16:00 UTC
    "new_york": (12, 0, 21, 0),  # 12:00 – 21:00 UTC
}

# Symbols that follow equity/index sessions (closed weekends + specific hours)
INDEX_SYMBOLS = {"US500", "US30", "UK100", "NAS100", "SPX500", "DE40", "JP225"}

# US equity-like hours (UTC): 13:30 – 20:00 (09:30–16:00 ET)
US_INDEX_OPEN_UTC = (13, 30)
US_INDEX_CLOSE_UTC = (20, 0)

# UK index hours (UTC): 08:00 – 16:30
UK_INDEX_OPEN_UTC = (8, 0)
UK_INDEX_CLOSE_UTC = (16, 30)


class MarketCalendar:
    """
    Single shared instance per process.
    Call `await refresh_events()` periodically (every 4h) or at startup.
    """

    def __init__(self) -> None:
        self._high_impact_events: list[
            dict
        ] = []  # [{time: datetime, currency: str, title: str}]
        self._last_fetch: Optional[datetime] = None
        self._lock = asyncio.Lock()

    # ── Public API ────────────────────────────────────────────────────────────

    def is_market_open(self, symbol: str, dt: Optional[datetime] = None) -> bool:
        """Return True if the market for `symbol` is open at `dt` (UTC now if None)."""
        now = dt or datetime.now(timezone.utc)
        asset_class = detect_asset_class(symbol)

        # Crypto: 24/7
        if asset_class == AssetClass.CRYPTO:
            return True

        # All markets closed on weekends (Sat/Sun UTC)
        weekday = now.weekday()  # 0=Mon … 6=Sun
        if weekday == 6:  # Sunday before Sydney open
            return now.hour >= 21
        if weekday == 5:  # Saturday — all closed
            return False

        sym_upper = symbol.upper()
        if sym_upper in INDEX_SYMBOLS:
            return self._is_index_open(sym_upper, now)

        # Forex: open if any session is active
        return self._any_session_open(now)

    def is_low_liquidity(self, symbol: str, dt: Optional[datetime] = None) -> bool:
        """
        True if only the Asian session is active (no London/NY overlap).
        Decision v2.4: this is a WARNING condition — does NOT block signals.
        """
        now = dt or datetime.now(timezone.utc)
        if detect_asset_class(symbol) == AssetClass.CRYPTO:
            return False
        london_open = self._session_active("london", now)
        ny_open = self._session_active("new_york", now)
        tokyo_open = self._session_active("tokyo", now)
        return tokyo_open and not london_open and not ny_open

    def is_high_impact_event_window(
        self, currency: str, dt: Optional[datetime] = None
    ) -> bool:
        """
        True if `currency` has a high-impact event within EVENT_BLOCK_MINUTES.
        Uses the cached ForexFactory RSS feed.
        """
        now = dt or datetime.now(timezone.utc)
        window = timedelta(minutes=EVENT_BLOCK_MINUTES)
        for event in self._high_impact_events:
            if event["currency"].upper() != currency.upper():
                continue
            event_time = event["time"]
            if abs((now - event_time).total_seconds()) <= window.total_seconds():
                logger.info(
                    "high_impact_event_window",
                    currency=currency,
                    event_title=event["title"],
                    event_time=event_time.isoformat(),
                )
                return True
        return False

    def affected_currencies(self, symbol: str) -> list[str]:
        """
        Return the currencies that a symbol is sensitive to for event filtering.
        EURUSD → ["EUR", "USD"],  XAUUSD → ["USD"],  US500 → ["USD"]
        """
        s = symbol.upper()
        if s in ("XAUUSD", "XAGUSD"):
            return ["USD"]
        if len(s) == 6 and s.isalpha():
            return [s[:3], s[3:]]
        if s in ("US500", "US30", "NAS100"):
            return ["USD"]
        if s == "UK100":
            return ["GBP"]
        if s == "DE40":
            return ["EUR"]
        return []

    async def refresh_events(self) -> None:
        """Fetch this week's ForexFactory calendar. Call at startup and every 4h."""
        if not self._cache_expired():
            return
        async with self._lock:
            if not self._cache_expired():
                return
            try:
                import httpx

                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(FOREX_FACTORY_RSS)
                    resp.raise_for_status()
                    self._parse_rss(resp.text)
                self._last_fetch = datetime.now(timezone.utc)
                logger.info(
                    "forex_factory_refreshed",
                    events=len(self._high_impact_events),
                )
            except Exception as exc:
                logger.warning("forex_factory_fetch_failed", error=str(exc))

    # ── Private helpers ───────────────────────────────────────────────────────

    def _parse_rss(self, xml_text: str) -> None:
        events: list[dict] = []
        try:
            root = ET.fromstring(xml_text)
            for item in root.iter("event"):
                impact = item.findtext("impact", "")
                if impact != HIGH_IMPACT_MARKER:
                    continue
                date_str = item.findtext("date", "")
                time_str = item.findtext("time", "")
                currency = item.findtext("currency", "")
                title = item.findtext("title", "")
                try:
                    dt = datetime.strptime(
                        f"{date_str} {time_str}", "%m-%d-%Y %I:%M%p"
                    ).replace(tzinfo=timezone.utc)
                    events.append({"time": dt, "currency": currency, "title": title})
                except ValueError:
                    continue
        except ET.ParseError as exc:
            logger.warning("forex_factory_parse_error", error=str(exc))
        self._high_impact_events = events

    def _cache_expired(self) -> bool:
        if self._last_fetch is None:
            return True
        return (
            datetime.now(timezone.utc) - self._last_fetch
        ).total_seconds() > CACHE_TTL_SECONDS

    def _any_session_open(self, now: datetime) -> bool:
        return any(self._session_active(name, now) for name in SESSIONS_UTC)

    def _session_active(self, session: str, now: datetime) -> bool:
        oh, om, ch, cm = SESSIONS_UTC[session]
        open_min = oh * 60 + om
        close_min = ch * 60 + cm
        current = now.hour * 60 + now.minute

        if open_min < close_min:
            return open_min <= current < close_min
        else:
            # Wraps midnight (e.g. Sydney 21:00 – 06:00)
            return current >= open_min or current < close_min

    def _is_index_open(self, symbol: str, now: datetime) -> bool:
        if symbol == "UK100":
            oh, om = UK_INDEX_OPEN_UTC
            ch, cm = UK_INDEX_CLOSE_UTC
        else:
            oh, om = US_INDEX_OPEN_UTC
            ch, cm = US_INDEX_CLOSE_UTC
        open_min = oh * 60 + om
        close_min = ch * 60 + cm
        current = now.hour * 60 + now.minute
        return open_min <= current < close_min


# ── Module-level singleton ────────────────────────────────────────────────────
_calendar: Optional[MarketCalendar] = None


def get_calendar() -> MarketCalendar:
    global _calendar
    if _calendar is None:
        _calendar = MarketCalendar()
    return _calendar
