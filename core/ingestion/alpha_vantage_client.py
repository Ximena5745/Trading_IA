"""
Module: core/ingestion/alpha_vantage_client.py
Responsibility: Alpha Vantage API client for market data
M2.12: Alpha Vantage Client (Data Only)
Dependencies: requests, logger
Note: Alpha Vantage is a data provider only - no execution capability
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

import requests

from core.ingestion.exchange_adapter import ExchangeAdapter
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

AV_BASE_URL = "https://www.alphavantage.co/query"


class AlphaVantageClient(ExchangeAdapter):
    """Alpha Vantage API client for market data.

    Supports: Stocks, Forex, Crypto, Commodities, Indices
    Status: Full implementation (data only, no execution)

    Note: Alpha Vantage has rate limits (5 calls/minute free, 75/min premium)
    """

    exchange_id = "alpha_vantage"
    supported_asset_classes = ("stocks", "forex", "crypto", "commodities", "indices")

    def __init__(
        self,
        api_key: str,
        timeout: int = 30,
    ):
        self._api_key = api_key
        self._timeout = timeout
        self._session = requests.Session()
        self._connected = False
        self._rate_limit_calls = 5
        self._rate_limit_period = 60

    async def connect(self) -> None:
        test_url = f"{AV_BASE_URL}?function=TIME_SERIES_INTRADAY&symbol=IBM&interval=5min&apikey={self._api_key}"
        try:
            response = self._session.get(test_url, timeout=self._timeout)
            if response.status_code == 200:
                self._connected = True
                logger.info("alpha_vantage_connected")
            else:
                logger.warning("alpha_vantage_connect_failed", status=response.status_code)
        except Exception as e:
            logger.error("alpha_vantage_connection_error", error=str(e))

    async def disconnect(self) -> None:
        self._session.close()
        self._connected = False
        logger.info("alpha_vantage_disconnected")

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
    ) -> list[MarketData]:
        """Get historical klines from Alpha Vantage.

        Supports:
        - TIME_SERIES_INTRADAY (1m, 5m, 15m, 30m, 60m)
        - TIME_SERIES_DAILY
        - TIME_SERIES_DAILY_ADJUSTED
        - TIME_SERIES_WEEKLY
        - TIME_SERIES_MONTHLY

        `limit` maps to Alpha Vantage's coarse `outputsize` param: <=100 -> "compact"
        (~100 most recent points), otherwise "full" (full history available).
        """
        output_size = "compact" if limit <= 100 else "full"
        function = self._map_interval_to_function(interval)

        params = {
            "function": function,
            "symbol": symbol,
            "apikey": self._api_key,
        }

        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = interval
            params["outputsize"] = output_size
        elif function == "TIME_SERIES_DAILY_ADJUSTED":
            params["outputsize"] = output_size

        try:
            response = self._session.get(AV_BASE_URL, params=params, timeout=self._timeout)
            data = response.json()

            time_series_key = self._get_time_series_key(function, interval)

            if "Error Message" in data or "Note" in data:
                raise RuntimeError(f"Alpha Vantage error: {data}")

            time_series = data.get(time_series_key, {})

            klines = []
            for timestamp_str, values in time_series.items():
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

                md = MarketData(
                    timestamp=timestamp,
                    symbol=symbol,
                    open=Decimal(values.get("1. open", "0")),
                    high=Decimal(values.get("2. high", "0")),
                    low=Decimal(values.get("3. low", "0")),
                    close=Decimal(values.get("4. close", "0")),
                    volume=Decimal(values.get("5. volume", "0")),
                    source="alpha_vantage",
                )
                klines.append(md)

            return klines

        except Exception as e:
            logger.error("alpha_vantage_klines_failed", symbol=symbol, error=str(e))
            raise

    async def get_quote(self, symbol: str) -> dict:
        """Get real-time quote for a symbol."""
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": symbol,
            "apikey": self._api_key,
        }

        try:
            response = self._session.get(AV_BASE_URL, params=params, timeout=self._timeout)
            data = response.json()

            quote = data.get("Global Quote", {})

            if not quote:
                return {}

            return {
                "symbol": quote.get("01. symbol", symbol),
                "price": float(quote.get("05. price", 0)),
                "volume": int(quote.get("06. volume", 0)),
                "change": float(quote.get("09. change", 0)),
                "change_percent": float(quote.get("10. change percent", "0").replace("%", "")),
            }

        except Exception as e:
            logger.error("alpha_vantage_quote_failed", symbol=symbol, error=str(e))
            return {}

    async def get_fx_rate(self, from_currency: str, to_currency: str) -> float:
        """Get forex exchange rate."""
        params = {
            "function": "CURRENCY_EXCHANGE_RATE",
            "from_currency": from_currency,
            "to_currency": to_currency,
            "apikey": self._api_key,
        }

        try:
            response = self._session.get(AV_BASE_URL, params=params, timeout=self._timeout)
            data = response.json()

            rate_data = data.get("Realtime Currency Exchange Rate", {})

            if not rate_data:
                return 0.0

            return float(rate_data.get("5. Exchange Rate", 0))

        except Exception as e:
            logger.error("alpha_vantage_fx_failed", error=str(e))
            return 0.0

    async def get_crypto_daily(self, symbol: str, market: str = "USD") -> list[MarketData]:
        """Get daily crypto data."""
        params = {
            "function": "DIGITAL_CURRENCY_DAILY",
            "symbol": symbol,
            "market": market,
            "apikey": self._api_key,
        }

        try:
            response = self._session.get(AV_BASE_URL, params=params, timeout=self._timeout)
            data = response.json()

            time_series = data.get("Time Series (Digital Currency Daily)", {})

            klines = []
            for timestamp_str, values in time_series.items():
                timestamp = datetime.fromisoformat(timestamp_str)

                md = MarketData(
                    timestamp=timestamp,
                    symbol=f"{symbol}/{market}",
                    open=Decimal(values.get("1a. open ({})".format(market), "0")),
                    high=Decimal(values.get("2a. high ({})".format(market), "0")),
                    low=Decimal(values.get("3a. low ({})".format(market), "0")),
                    close=Decimal(values.get("4a. close ({})".format(market), "0")),
                    volume=Decimal(values.get("5. volume", "0")),
                    source="alpha_vantage",
                    asset_class="crypto",
                )
                klines.append(md)

            return klines

        except Exception as e:
            logger.error("alpha_vantage_crypto_failed", symbol=symbol, error=str(e))
            return []

    def _map_interval_to_function(self, interval: str) -> str:
        intraday_intervals = ("1m", "5m", "15m", "30m", "60m")
        if interval in intraday_intervals:
            return "TIME_SERIES_INTRADAY"
        elif interval == "1d":
            return "TIME_SERIES_DAILY_ADJUSTED"
        elif interval == "1w":
            return "TIME_SERIES_WEEKLY"
        elif interval == "1M":
            return "TIME_SERIES_MONTHLY"
        return "TIME_SERIES_DAILY"

    def _get_time_series_key(self, function: str, interval: str) -> str:
        if function == "TIME_SERIES_INTRADAY":
            return f"Time Series ({interval})"
        elif function == "TIME_SERIES_DAILY":
            return "Time Series (Daily)"
        elif function == "TIME_SERIES_DAILY_ADJUSTED":
            return "Time Series (Daily)"
        elif function == "TIME_SERIES_WEEKLY":
            return "Weekly Time Series"
        elif function == "TIME_SERIES_MONTHLY":
            return "Monthly Time Series"
        return "Time Series (Daily)"

    async def get_order_book(self, symbol: str, depth: int = 20) -> dict:
        raise NotImplementedError("Alpha Vantage is data-only")

    async def get_balance(self, asset: str = "USD") -> float:
        raise NotImplementedError("Alpha Vantage is data-only")

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        client_order_id: Optional[str] = None,
    ) -> dict:
        raise NotImplementedError("Alpha Vantage is data-only")

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        raise NotImplementedError("Alpha Vantage is data-only")

    async def get_order_status(self, symbol: str, order_id: str) -> dict:
        raise NotImplementedError("Alpha Vantage is data-only")

    def is_connected(self) -> bool:
        return self._connected


async def create_alpha_vantage_client(
    api_key: str,
    timeout: int = 30,
) -> AlphaVantageClient:
    client = AlphaVantageClient(api_key, timeout)
    await client.connect()
    return client