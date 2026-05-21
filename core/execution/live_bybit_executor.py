"""
Module: core/execution/live_bybit_executor.py
Responsibility: Live execution with Bybit API for crypto
M2.7: Bybit Full Integration - Executor
Dependencies: httpx, bybit_client, logger
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import redis.asyncio as aioredis

from core.observability.logger import get_logger

logger = get_logger(__name__)

BYBIT_REST_BASE = "https://api.bybit.com"
BYBIT_TESTNET_BASE = "https://api-testnet.bybit.com"


@dataclass
class BybitFillReport:
    order_id: str
    symbol: str
    side: str
    units: float
    fill_price: float
    commission: float
    slippage: float
    timestamp: datetime


class LiveBybitExecutor:
    """Live executor for Bybit exchange.

    Supports: Spot and Futures trading
    Status: Full implementation
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        testnet: bool = True,
        redis_url: str = "redis://localhost:6379",
    ):
        self._api_key = api_key
        self._secret_key = secret_key
        self._base_url = BYBIT_TESTNET_BASE if testnet else BYBIT_REST_BASE
        self._testnet = testnet
        self._redis_url = redis_url
        self._session = None
        self._connected = False

        self._maker_fee = 0.001  # 0.1%
        self._taker_fee = 0.001  # 0.1%

    async def connect(self) -> None:
        import httpx
        self._session = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)
        self._connected = True
        logger.info("bybit_executor_connected", testnet=self._testnet)

    async def disconnect(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None
        self._connected = False
        logger.info("bybit_executor_disconnected")

    def _sign(self, method: str, endpoint: str, params: dict) -> dict:
        ts = str(int(time.time() * 1000))
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        sign_str = f"{ts}{method}{endpoint}{param_str}"
        signature = hmac.new(
            self._secret_key.encode(),
            sign_str.encode(),
            hashlib.sha256,
        ).hexdigest()
        return {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": ts,
        }

    async def execute_market_order(
        self,
        symbol: str,
        side: str,
        units: float,
        category: str = "spot",
    ) -> BybitFillReport:
        if not self._connected or not self._session:
            raise RuntimeError("Bybit not connected")

        endpoint = "/v5/order/replace" if category == "linear" else "/v5/order/create"
        params = {
            "category": category,
            "symbol": symbol.upper(),
            "side": side.upper(),
            "orderType": "Market",
            "qty": str(int(units)),
            "timeInForce": "GTC",
        }

        headers = self._sign("POST", endpoint, params)

        try:
            response = await self._session.post(endpoint, json=params, headers=headers)
            data = response.json()

            if data.get("retCode") != 0:
                raise RuntimeError(f"Bybit order failed: {data.get('retMsg')}")

            result = data.get("result", {})
            order_id = result.get("orderId", "")

            fill_price = float(result.get("avgPrice", 0))
            commission = units * fill_price * self._taker_fee

            logger.info(
                "bybit_order_filled",
                order_id=order_id,
                symbol=symbol,
                side=side,
                units=units,
                fill_price=fill_price,
            )

            await self._publish_to_redis("orders", {
                "order_id": order_id,
                "symbol": symbol,
                "side": side,
                "units": units,
                "fill_price": fill_price,
                "commission": commission,
                "timestamp": datetime.utcnow().isoformat(),
            })

            return BybitFillReport(
                order_id=order_id,
                symbol=symbol,
                side=side,
                units=units,
                fill_price=fill_price,
                commission=commission,
                slippage=0.0,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error("bybit_order_failed", error=str(e))
            raise

    async def execute_limit_order(
        self,
        symbol: str,
        side: str,
        units: float,
        limit_price: float,
        category: str = "spot",
    ) -> BybitFillReport:
        if not self._connected or not self._session:
            raise RuntimeError("Bybit not connected")

        endpoint = "/v5/order/create"
        params = {
            "category": category,
            "symbol": symbol.upper(),
            "side": side.upper(),
            "orderType": "Limit",
            "qty": str(int(units)),
            "price": str(limit_price),
            "timeInForce": "GTC",
        }

        headers = self._sign("POST", endpoint, params)

        try:
            response = await self._session.post(endpoint, json=params, headers=headers)
            data = response.json()

            if data.get("retCode") != 0:
                raise RuntimeError(f"Bybit order failed: {data.get('retMsg')}")

            result = data.get("result", {})
            order_id = result.get("orderId", "")

            logger.info(
                "bybit_limit_order_placed",
                order_id=order_id,
                symbol=symbol,
                side=side,
                units=units,
                limit_price=limit_price,
            )

            return BybitFillReport(
                order_id=order_id,
                symbol=symbol,
                side=side,
                units=units,
                fill_price=limit_price,
                commission=0.0,
                slippage=0.0,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error("bybit_limit_order_failed", error=str(e))
            raise

    async def cancel_order(self, symbol: str, order_id: str, category: str = "spot") -> bool:
        if not self._connected or not self._session:
            return False

        endpoint = "/v5/order/cancel"
        params = {
            "category": category,
            "symbol": symbol.upper(),
            "orderId": order_id,
        }

        headers = self._sign("POST", endpoint, params)

        try:
            response = await self._session.post(endpoint, json=params, headers=headers)
            data = response.json()
            return data.get("retCode") == 0
        except Exception:
            return False

    async def get_order_status(self, symbol: str, order_id: str, category: str = "spot") -> dict:
        if not self._connected or not self._session:
            return {}

        endpoint = "/v5/order/realtime"
        params = {
            "category": category,
            "symbol": symbol.upper(),
            "orderId": order_id,
        }

        headers = self._sign("GET", endpoint, params, str(int(time.time() * 1000)))

        try:
            response = await self._session.get(endpoint, params=params, headers=headers)
            data = response.json()
            if data.get("retCode") == 0:
                return data.get("result", {}).get("list", [{}])[0]
        except Exception:
            pass
        return {}

    async def get_positions(self, category: str = "spot") -> list[dict]:
        if not self._connected or not self._session:
            return []

        endpoint = "/v5/position/closed-pnl"
        params = {"category": category}

        headers = self._sign("GET", endpoint, params, str(int(time.time() * 1000)))

        try:
            response = await self._session.get(endpoint, params=params, headers=headers)
            data = response.json()
            if data.get("retCode") == 0:
                return data.get("result", {}).get("list", [])
        except Exception:
            pass
        return []

    async def get_balance(self, account_type: str = "UNIFIED") -> float:
        if not self._connected or not self._session:
            return 0.0

        endpoint = "/v5/account/wallet-balance"
        params = {"accountType": account_type}

        headers = self._sign("GET", endpoint, params, str(int(time.time() * 1000)))

        try:
            response = await self._session.get(endpoint, params=params, headers=headers)
            data = response.json()
            if data.get("retCode") == 0:
                result = data.get("result", {}).get("list", [{}])[0]
                return float(result.get("totalEquity", 0))
        except Exception:
            pass
        return 0.0

    async def _publish_to_redis(self, key: str, data: dict) -> None:
        try:
            redis = await aioredis.from_url(self._redis_url)
            await redis.xadd(f"bybit_{key}", data, maxlen=1000)
            await redis.aclose()
        except Exception as e:
            logger.warning("bybit_redis_publish_failed", error=str(e))

    def is_connected(self) -> bool:
        return self._connected

    def get_fee_rates(self) -> dict:
        return {
            "maker_fee": self._maker_fee,
            "taker_fee": self._taker_fee,
        }


async def create_bybit_executor(
    api_key: str,
    secret_key: str,
    testnet: bool = True,
    redis_url: str = "redis://localhost:6379",
) -> LiveBybitExecutor:
    executor = LiveBybitExecutor(api_key, secret_key, testnet, redis_url)
    await executor.connect()
    return executor