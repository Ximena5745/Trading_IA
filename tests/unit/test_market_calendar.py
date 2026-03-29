"""
Tests for MarketCalendar (FASE E).
Covers: session detection, weekend closure, LOW_LIQUIDITY (Asian-only),
high-impact event blocking, affected_currencies, and RSS parsing.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.ingestion.market_calendar import MarketCalendar


def utc(year: int, month: int, day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class TestIsMarketOpen:
    """Market open/closed detection by session and asset type."""

    def test_crypto_always_open(self):
        cal = MarketCalendar()
        # Saturday — all non-crypto closed
        saturday = utc(2024, 6, 1, 14, 0)  # Saturday
        assert cal.is_market_open("BTCUSDT", saturday) is True
        assert cal.is_market_open("ETHUSDT", saturday) is True

    def test_forex_closed_saturday(self):
        cal = MarketCalendar()
        saturday_noon = utc(2024, 6, 1, 12, 0)  # Saturday
        assert cal.is_market_open("EURUSD", saturday_noon) is False

    def test_forex_closed_sunday_before_sydney(self):
        cal = MarketCalendar()
        sunday_early = utc(2024, 6, 2, 10, 0)  # Sunday 10:00 UTC (before Sydney 21:00)
        assert cal.is_market_open("EURUSD", sunday_early) is False

    def test_forex_open_during_london_session(self):
        cal = MarketCalendar()
        # London: 07:00 – 16:00 UTC; use a Tuesday
        tuesday_london = utc(2024, 6, 4, 10, 0)  # Tuesday 10:00 UTC
        assert cal.is_market_open("EURUSD", tuesday_london) is True
        assert cal.is_market_open("GBPUSD", tuesday_london) is True

    def test_forex_open_during_new_york_session(self):
        cal = MarketCalendar()
        tuesday_ny = utc(2024, 6, 4, 15, 0)  # Tuesday 15:00 UTC
        assert cal.is_market_open("USDJPY", tuesday_ny) is True

    def test_us500_open_during_us_session(self):
        cal = MarketCalendar()
        # US indices: 13:30 – 20:00 UTC
        tuesday_us = utc(2024, 6, 4, 16, 0)
        assert cal.is_market_open("US500", tuesday_us) is True

    def test_us500_closed_outside_us_session(self):
        cal = MarketCalendar()
        tuesday_london = utc(2024, 6, 4, 10, 0)  # 10:00 UTC — before 13:30 open
        assert cal.is_market_open("US500", tuesday_london) is False

    def test_uk100_open_during_uk_session(self):
        cal = MarketCalendar()
        # UK100: 08:00 – 16:30 UTC
        tuesday_uk = utc(2024, 6, 4, 12, 0)
        assert cal.is_market_open("UK100", tuesday_uk) is True

    def test_uk100_closed_before_uk_open(self):
        cal = MarketCalendar()
        tuesday_early = utc(2024, 6, 4, 7, 0)  # 07:00 UTC — before UK100 opens at 08:00
        assert cal.is_market_open("UK100", tuesday_early) is False


class TestIsLowLiquidity:
    """Asian session only = low liquidity (warning, not block)."""

    def test_crypto_never_low_liquidity(self):
        cal = MarketCalendar()
        # During Asian-only hours
        asian_hour = utc(2024, 6, 4, 3, 0)  # Tokyo open, London/NY closed
        assert cal.is_low_liquidity("BTCUSDT", asian_hour) is False

    def test_forex_low_liquidity_during_asian_only(self):
        cal = MarketCalendar()
        # Tokyo: 00:00–09:00 UTC; London opens 07:00; NY opens 12:00
        # At 03:00 UTC: only Tokyo is active
        asian_only = utc(2024, 6, 4, 3, 0)  # Tuesday 03:00 UTC
        assert cal.is_low_liquidity("EURUSD", asian_only) is True

    def test_forex_not_low_liquidity_during_london_overlap(self):
        cal = MarketCalendar()
        # Tokyo (00:00-09:00) overlaps London (07:00-16:00) at 08:00
        overlap = utc(2024, 6, 4, 8, 0)
        assert cal.is_low_liquidity("EURUSD", overlap) is False

    def test_forex_not_low_liquidity_during_ny_session(self):
        cal = MarketCalendar()
        ny_hour = utc(2024, 6, 4, 15, 0)
        assert cal.is_low_liquidity("EURUSD", ny_hour) is False


class TestHighImpactEventWindow:
    """ForexFactory high-impact event blocking (±30 min)."""

    def _calendar_with_event(self, currency: str, event_dt: datetime) -> MarketCalendar:
        cal = MarketCalendar()
        cal._high_impact_events = [
            {"time": event_dt, "currency": currency, "title": "NFP"},
        ]
        return cal

    def test_blocks_within_window(self):
        event_time = utc(2024, 6, 7, 12, 30)  # NFP at 12:30
        cal = self._calendar_with_event("USD", event_time)
        # 10 minutes before event
        check_time = utc(2024, 6, 7, 12, 20)
        assert cal.is_high_impact_event_window("USD", check_time) is True

    def test_blocks_after_event(self):
        event_time = utc(2024, 6, 7, 12, 30)
        cal = self._calendar_with_event("USD", event_time)
        # 20 minutes after event
        check_time = utc(2024, 6, 7, 12, 50)
        assert cal.is_high_impact_event_window("USD", check_time) is True

    def test_no_block_outside_window(self):
        event_time = utc(2024, 6, 7, 12, 30)
        cal = self._calendar_with_event("USD", event_time)
        # 2 hours before event
        check_time = utc(2024, 6, 7, 10, 30)
        assert cal.is_high_impact_event_window("USD", check_time) is False

    def test_currency_filter(self):
        """EUR event does not block USD."""
        event_time = utc(2024, 6, 7, 12, 30)
        cal = self._calendar_with_event("EUR", event_time)
        check_time = utc(2024, 6, 7, 12, 30)
        assert cal.is_high_impact_event_window("USD", check_time) is False
        assert cal.is_high_impact_event_window("EUR", check_time) is True

    def test_exact_event_time_is_blocked(self):
        event_time = utc(2024, 6, 7, 12, 30)
        cal = self._calendar_with_event("USD", event_time)
        assert cal.is_high_impact_event_window("USD", event_time) is True

    def test_empty_events_never_blocked(self):
        cal = MarketCalendar()
        assert cal.is_high_impact_event_window("USD", utc(2024, 6, 7, 12, 30)) is False


class TestAffectedCurrencies:
    """Currency extraction for event filtering."""

    def test_eurusd_returns_both(self):
        cal = MarketCalendar()
        assert cal.affected_currencies("EURUSD") == ["EUR", "USD"]

    def test_xauusd_returns_usd(self):
        cal = MarketCalendar()
        assert cal.affected_currencies("XAUUSD") == ["USD"]

    def test_us500_returns_usd(self):
        cal = MarketCalendar()
        assert cal.affected_currencies("US500") == ["USD"]

    def test_uk100_returns_gbp(self):
        cal = MarketCalendar()
        assert cal.affected_currencies("UK100") == ["GBP"]

    def test_de40_returns_eur(self):
        cal = MarketCalendar()
        assert cal.affected_currencies("DE40") == ["EUR"]

    def test_unknown_symbol_returns_empty(self):
        cal = MarketCalendar()
        assert cal.affected_currencies("BTCUSDT") == []


class TestRSSParsing:
    """_parse_rss correctly extracts High impact events only."""

    SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<events>
  <event>
    <date>06-07-2024</date>
    <time>08:30am</time>
    <currency>USD</currency>
    <title>Non-Farm Payrolls</title>
    <impact>High</impact>
  </event>
  <event>
    <date>06-07-2024</date>
    <time>10:00am</time>
    <currency>USD</currency>
    <title>ISM Manufacturing</title>
    <impact>Medium</impact>
  </event>
  <event>
    <date>06-07-2024</date>
    <time>07:00am</time>
    <currency>EUR</currency>
    <title>ECB Rate Decision</title>
    <impact>High</impact>
  </event>
</events>"""

    def test_only_high_impact_events_stored(self):
        cal = MarketCalendar()
        cal._parse_rss(self.SAMPLE_RSS)
        assert len(cal._high_impact_events) == 2  # NFP + ECB, not ISM

    def test_event_currencies_parsed_correctly(self):
        cal = MarketCalendar()
        cal._parse_rss(self.SAMPLE_RSS)
        currencies = {e["currency"] for e in cal._high_impact_events}
        assert "USD" in currencies
        assert "EUR" in currencies

    def test_invalid_xml_does_not_raise(self):
        cal = MarketCalendar()
        cal._parse_rss("<<invalid xml>>")
        assert cal._high_impact_events == []
