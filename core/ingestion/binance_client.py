"""
Module: core/ingestion/binance_client.py
Responsibility: Binance REST API client
Dependencies: python-binance, base_client, models, logger
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from binance.client import AsyncClient
from binance.exceptions import BinanceAPIException

from core.exceptions import DataValidationError, ExecutionError
from core.ingestion.base_client import ExchangeClient
from core.ingestion.data_validator import DataValidator
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

INTERVAL_MAP = {
    "1m": AsyncClient.KLINE_INTERVAL_1MINUTE,
    "5m": AsyncClient.KLINE_INTERVAL_5MINUTE,
    "15m": AsyncClient.KLINE_INTERVAL_15MINUTE,
    "1h": AsyncClient.KLINE_INTERVAL_1HOUR,
    "4h": AsyncClient.KLINE_INTERVAL_4HOUR,
    "1d": AsyncClient.KLINE_INTERVAL_1DAY,
}


class BinanceClient(ExchangeClient):
    def __init__(self, api_key: str, secret_key: str, testnet: bool = True):
        self._api_key = api_key
        self._secret_key = secret_key
        self._testnet = testnet
        self._client: AsyncClient | None = None
        self._validator = DataValidator()

    async def connect(self) -> None:
        self._client = await AsyncClient.create(
            api_key=self._api_key,
            api_secret=self._secret_key,
            testnet=self._testnet,
        )
        logger.info("binance_client_connected", testnet=self._testnet)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close_connection()
            logger.info("binance_client_disconnected")

    async def get_historical_klines(
        self, symbol: str, interval: str, limit: int = 500
    ) -> list[MarketData]:
        if not self._client:
            raise ExecutionError("BinanceClient not connected")

        binance_interval = INTERVAL_MAP.get(interval)
        if not binance_interval:
            raise DataValidationError(f"Unsupported interval: {interval}")

        try:
            raw = await self._client.get_klines(
                symbol=symbol, interval=binance_interval, limit=limit
            )
        except BinanceAPIException as e:
            logger.error("binance_klines_error", symbol=symbol, error=str(e))
            raise ExecutionError(f"Binance API error: {e}") from e

        records = [self._parse_kline(symbol, k) for k in raw]
        validated = self._validator.validate_batch(records)
        logger.info("historical_klines_fetched", symbol=symbol, count=len(validated))
        return validated

    async def get_order_book(self, symbol: str, depth: int = 20) -> dict:
        if not self._client:
            raise ExecutionError("BinanceClient not connected")
        try:
            book = await self._client.get_order_book(symbol=symbol, limit=depth)
            return book
        except BinanceAPIException as e:
            logger.error("binance_order_book_error", symbol=symbol, error=str(e))
            raise ExecutionError(f"Binance API error: {e}") from e

    async def place_order(self, symbol: str, side: str, quantity: float, **kwargs):
        raise NotImplementedError("Use LiveExecutor for order placement")

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        raise NotImplementedError("Use LiveExecutor for order cancellation")

    async def get_account_balance(self) -> dict:
        if not self._client:
            raise ExecutionError("BinanceClient not connected")
        try:
            account = await self._client.get_account()
            return {
                b["asset"]: float(b["free"])
                for b in account["balances"]
                if float(b["free"]) > 0
            }
        except BinanceAPIException as e:
            raise ExecutionError(f"Binance API error: {e}") from e

    @staticmethod
    def _parse_kline(symbol: str, k: list) -> MarketData:
        return MarketData(
            timestamp=datetime.utcfromtimestamp(k[0] / 1000),
            symbol=symbol,
            open=Decimal(k[1]),
            high=Decimal(k[2]),
            low=Decimal(k[3]),
            close=Decimal(k[4]),
            volume=Decimal(k[5]),
            quote_volume=Decimal(k[7]),
            trades_count=int(k[8]),
            taker_buy_volume=Decimal(k[9]),
        )
