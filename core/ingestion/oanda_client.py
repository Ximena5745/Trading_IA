"""
Module: core/ingestion/oanda_client.py
Responsibility: OANDA REST API client for forex/CFD/indices data
Dependencies: oandapyV20, logger
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from core.ingestion.exchange_adapter import ExchangeAdapter, to_oanda_symbol
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

OANDA_AVAILABLE = True
try:
    from oandapyV20 import API
    import oandapyV20.endpoints.instruments as instruments
    import oandapyV20.endpoints.pricing as pricing
except ImportError:
    OANDA_AVAILABLE = False


class OandaClient(ExchangeAdapter):
    """OANDA REST API client.

    Supports: Forex, Indices, Commodities
    Status: Full implementation
    """

    exchange_id = "oanda"
    supported_asset_classes = ("forex", "indices", "commodities")

    def __init__(
        self,
        api_key: str,
        account_id: str,
        environment: str = "practice",
    ):
        self._api_key = api_key
        self._account_id = account_id
        self._environment = environment
        self._client: Optional[API] = None
        self._connected = False

    async def connect(self) -> None:
        if not OANDA_AVAILABLE:
            raise RuntimeError("oandapyV20 not installed")

        try:
            self._client = API(access_token=self._api_key, environment=self._environment)
            response = self._client.request(
                instruments.Instruments(accountID=self._account_id)
            )
            self._connected = True
            logger.info("oanda_client_connected", account_id=self._account_id)
        except Exception as e:
            logger.error("oanda_connect_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        self._client = None
        self._connected = False
        logger.info("oanda_client_disconnected")

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 500,
    ) -> list[MarketData]:
        """Get historical klines/candles."""
        if not self._connected or not self._client:
            raise RuntimeError("OANDA not connected")

        oanda_symbol = to_oanda_symbol(symbol)
        granularity = _interval_to_oanda_granularity(interval)

        params = {
            "granularity": granularity,
            "count": limit,
        }

        try:
            response = self._client.request(
                instruments.InstrumentsCandles(instrument=oanda_symbol, params=params)
            )

            candles = response.get("candles", [])
            market_data_list = []

            for c in candles:
                md = MarketData(
                    timestamp=datetime.fromisoformat(c["time"].replace("Z", "+00:00")),
                    symbol=symbol,
                    open=Decimal(c["mid"]["o"]),
                    high=Decimal(c["mid"]["h"]),
                    low=Decimal(c["mid"]["l"]),
                    close=Decimal(c["mid"]["c"]),
                    volume=Decimal(c["volume"]),
                    source="oanda",
                    asset_class="forex",
                )
                market_data_list.append(md)

            return market_data_list

        except Exception as e:
            logger.error("oanda_klines_failed", symbol=symbol, error=str(e))
            raise

    async def get_order_book(self, symbol: str, depth: int = 20) -> dict:
        """Get current price (OANDA does not provide L2 depth; `depth` is ignored)."""
        if not self._connected or not self._client:
            raise RuntimeError("OANDA not connected")

        oanda_symbol = to_oanda_symbol(symbol)

        try:
            response = self._client.request(
                pricing.PricingInfo(accountID=self._account_id, params={"instruments": oanda_symbol})
            )
            return response.get("prices", [{}])[0]
        except Exception as e:
            logger.error("oanda_order_book_failed", symbol=symbol, error=str(e))
            return {}

    async def get_balance(self, asset: str = "USD") -> float:
        """Get account balance (OANDA accounts hold a single home currency; `asset` is ignored)."""
        if not self._connected or not self._client:
            return 0.0

        try:
            from oandapyV20.endpoints import trading
            response = self._client.request(
                trading.AccountDetails(accountID=self._account_id)
            )
            return float(response["account"]["balance"])
        except Exception:
            return 0.0

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        client_order_id: Optional[str] = None,
    ) -> dict:
        raise NotImplementedError("Use LiveOandaExecutor for order placement")

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        raise NotImplementedError("Use LiveOandaExecutor for order cancellation")

    async def get_order_status(self, symbol: str, order_id: str) -> dict:
        raise NotImplementedError("Use LiveOandaExecutor for order status lookup")

    def is_connected(self) -> bool:
        return self._connected


def _interval_to_oanda_granularity(interval: str) -> str:
    mapping = {
        "1m": "M5",
        "5m": "M5",
        "15m": "M15",
        "30m": "M30",
        "1h": "H1",
        "4h": "H4",
        "1d": "D",
        "1w": "W",
    }
    return mapping.get(interval, "H1")


async def create_oanda_client(
    api_key: str,
    account_id: str,
    environment: str = "practice",
) -> OandaClient:
    client = OandaClient(api_key, account_id, environment)
    await client.connect()
    return client