"""
Module: core/ingestion/bybit_client.py
Responsibility: Bybit exchange adapter (V5 API) — stub ready for activation
Dependencies: exchange_adapter, httpx, logger
"""

from __future__ import annotations

import hashlib
import hmac
import time
from datetime import datetime

from core.ingestion.exchange_adapter import ExchangeAdapter
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

BYBIT_REST_BASE = "https://api.bybit.com"
BYBIT_TESTNET_BASE = "https://api-testnet.bybit.com"

INTERVAL_MAP = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "1h": "60",
    "2h": "120",
    "4h": "240",
    "6h": "360",
    "12h": "720",
    "1d": "D",
    "1w": "W",
}


class BybitClient(ExchangeAdapter):
    """Bybit V5 Unified Account adapter.

    Implements ExchangeAdapter so the rest of the platform treats Bybit
    identically to Binance — just swap the adapter in ExchangeAdapterRegistry.

    Status: functional stub — REST calls are wired; WebSocket stream pending.
    """

    exchange_id = "bybit"

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        testnet: bool = True,
    ):
        self._api_key = api_key
        self._api_secret = api_secret
        self._base_url = BYBIT_TESTNET_BASE if testnet else BYBIT_REST_BASE
        self._testnet = testnet
        self._connected = False
        self._session = None

    # ── Connection lifecycle ───────────────────────────────────────────────

    async def connect(self) -> None:
        try:
            import httpx

            self._session = httpx.AsyncClient(base_url=self._base_url, timeout=10.0)
            self._connected = True
            logger.info("bybit_connected", testnet=self._testnet)
        except ImportError:
            logger.error("bybit_connect_failed", reason="httpx not installed")
            raise

    async def disconnect(self) -> None:
        if self._session:
            await self._session.aclose()
            self._session = None
        self._connected = False
        logger.info("bybit_disconnected")

    def is_connected(self) -> bool:
        return self._connected

    # ── Market data ────────────────────────────────────────────────────────

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
    ) -> list[MarketData]:
        """Fetch OHLCV candles from Bybit V5 /v5/market/kline."""
        if not self._session:
            raise RuntimeError("BybitClient not connected. Call connect() first.")

        bybit_interval = INTERVAL_MAP.get(interval, "60")
        params = {
            "category": "spot",
            "symbol": self.normalise_symbol(symbol),
            "interval": bybit_interval,
            "limit": limit,
        }
        self.log_request("GET", "/v5/market/kline")
        response = await self._session.get("/v5/market/kline", params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {data.get('retMsg')}")

        klines = []
        for row in reversed(data["result"]["list"]):
            # row format: [startTime, open, high, low, close, volume, turnover]
            ts = datetime.utcfromtimestamp(int(row[0]) / 1000)
            klines.append(
                MarketData(
                    symbol=symbol.upper(),
                    timestamp=ts,
                    open=float(row[1]),
                    high=float(row[2]),
                    low=float(row[3]),
                    close=float(row[4]),
                    volume=float(row[5]),
                )
            )
        return klines

    async def get_order_book(self, symbol: str, depth: int = 20) -> dict:
        """Fetch L2 order book snapshot from Bybit."""
        if not self._session:
            raise RuntimeError("BybitClient not connected.")

        params = {
            "category": "spot",
            "symbol": self.normalise_symbol(symbol),
            "limit": depth,
        }
        response = await self._session.get("/v5/market/orderbook", params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {data.get('retMsg')}")

        result = data["result"]
        return {
            "symbol": symbol,
            "bids": [[float(p), float(q)] for p, q in result.get("b", [])],
            "asks": [[float(p), float(q)] for p, q in result.get("a", [])],
            "timestamp": datetime.utcnow().isoformat(),
        }

    # ── Account & trading ─────────────────────────────────────────────────

    async def get_balance(self, asset: str = "USDT") -> float:
        """Get wallet balance for a specific asset."""
        if not self._session:
            raise RuntimeError("BybitClient not connected.")

        ts = str(int(time.time() * 1000))
        params = {"accountType": "UNIFIED", "coin": asset}
        headers = self._auth_headers("GET", "/v5/account/wallet-balance", params, ts)

        response = await self._session.get(
            "/v5/account/wallet-balance", params=params, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error: {data.get('retMsg')}")

        coins = data["result"]["list"][0].get("coin", [])
        for coin in coins:
            if coin["coin"] == asset:
                return float(coin.get("walletBalance", 0))
        return 0.0

    async def place_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        order_type: str = "MARKET",
        client_order_id: str | None = None,
    ) -> dict:
        """Place a spot market or limit order on Bybit."""
        if not self._session:
            raise RuntimeError("BybitClient not connected.")

        payload: dict = {
            "category": "spot",
            "symbol": self.normalise_symbol(symbol),
            "side": side.capitalize(),  # Buy / Sell
            "orderType": order_type.capitalize(),
            "qty": str(quantity),
        }
        if client_order_id:
            payload["orderLinkId"] = client_order_id

        ts = str(int(time.time() * 1000))
        headers = self._auth_headers("POST", "/v5/order/create", payload, ts)

        response = await self._session.post(
            "/v5/order/create", json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit order failed: {data.get('retMsg')}")

        logger.info(
            "bybit_order_placed",
            symbol=symbol,
            side=side,
            qty=quantity,
            order_id=data["result"].get("orderId"),
        )
        return data["result"]

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Cancel an open Bybit order."""
        if not self._session:
            raise RuntimeError("BybitClient not connected.")

        payload = {
            "category": "spot",
            "symbol": self.normalise_symbol(symbol),
            "orderId": order_id,
        }
        ts = str(int(time.time() * 1000))
        headers = self._auth_headers("POST", "/v5/order/cancel", payload, ts)

        response = await self._session.post(
            "/v5/order/cancel", json=payload, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit cancel failed: {data.get('retMsg')}")

        return data["result"]

    async def get_order_status(self, symbol: str, order_id: str) -> dict:
        """Query Bybit order status by orderId."""
        if not self._session:
            raise RuntimeError("BybitClient not connected.")

        params = {
            "category": "spot",
            "symbol": self.normalise_symbol(symbol),
            "orderId": order_id,
        }
        ts = str(int(time.time() * 1000))
        headers = self._auth_headers("GET", "/v5/order/realtime", params, ts)

        response = await self._session.get(
            "/v5/order/realtime", params=params, headers=headers
        )
        response.raise_for_status()
        data = response.json()

        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit status query failed: {data.get('retMsg')}")

        orders = data["result"].get("list", [])
        return orders[0] if orders else {}

    # ── HMAC-SHA256 authentication ────────────────────────────────────────

    def _auth_headers(
        self,
        method: str,
        endpoint: str,
        params: dict,
        timestamp: str,
    ) -> dict:
        recv_window = "5000"
        if method == "GET":
            param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        else:
            import json

            param_str = json.dumps(params, separators=(",", ":"))

        sign_str = timestamp + self._api_key + recv_window + param_str
        signature = hmac.new(
            self._api_secret.encode("utf-8"),
            sign_str.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return {
            "X-BAPI-API-KEY": self._api_key,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2",
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-RECV-WINDOW": recv_window,
            "Content-Type": "application/json",
        }
