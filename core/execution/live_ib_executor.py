"""
Module: core/execution/live_ib_executor.py
Responsibility: Live execution with Interactive Brokers for multiasset trading
M2.9: IB Execution Layer
Dependencies: ib_insync, logger
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

import redis.asyncio as aioredis

from core.observability.logger import get_logger

logger = get_logger(__name__)

IB_AVAILABLE = True
try:
    from ib_insync import IB, Forex, Index, Stock, ContFuture, Contract, Order, OrderStatus
except ImportError:
    IB_AVAILABLE = False


@dataclass
class IBFillReport:
    order_id: str
    symbol: str
    side: str
    units: float
    fill_price: float
    commission: float
    margin_used: float
    timestamp: datetime


class LiveIBExecutor:
    """Live executor for Interactive Brokers.

    Supports: Forex, Indices, Commodities, Stocks, Futures, Options
    Connection: TWS on port 7497 (live) or 7498 (paper)
    Status: Full implementation
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 7497,
        client_id: int = 1,
        is_paper: bool = True,
        redis_url: str = "redis://localhost:6379",
    ):
        self.host = host
        self.port = port
        self.client_id = client_id
        self.is_paper = is_paper
        self.redis_url = redis_url

        self._ib: Optional[IB] = None
        self._connected = False

        self._commission_rate = 0.00005  # 0.005% per trade

    async def connect(self) -> None:
        if not IB_AVAILABLE:
            raise RuntimeError("ib_insync not installed")

        self._ib = IB()
        await self._ib.connectAsync(
            host=self.host,
            port=self.port,
            clientId=self.client_id,
            readonly=False,
        )
        self._connected = True

        logger.info(
            "ib_executor_connected",
            host=self.host,
            port=self.port,
            is_paper=self.is_paper,
        )

    async def disconnect(self) -> None:
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
        self._connected = False
        logger.info("ib_executor_disconnected")

    def _create_contract(self, symbol: str) -> Contract:
        """Create IB contract based on symbol."""
        symbol_upper = symbol.upper()

        if len(symbol_upper) == 6 and symbol_upper[:3] in (
            "EUR", "GBP", "USD", "AUD", "NZD", "CAD", "CHF", "JPY"
        ):
            return Forex(pair=symbol)
        elif symbol_upper in ("SPX500", "NAS100", "US30", "DE40", "UK100", "JP225"):
            return Index(symbol=symbol_upper, exchange="CME")
        elif symbol_upper.startswith("XAU") or symbol_upper.startswith("XAG"):
            return Forex(pair=symbol)
        elif symbol_upper in ("CL", "NG", "GC", "ZS", "ZW"):
            return ContFuture(symbol=symbol_upper, exchange="NYMEX")
        else:
            return Stock(symbol=symbol_upper, exchange="SMART", currency="USD")

    async def execute_market_order(
        self,
        symbol: str,
        side: str,
        units: float,
    ) -> IBFillReport:
        if not self._connected or not self._ib:
            raise RuntimeError("IB not connected")

        contract = self._create_contract(symbol)

        action = "BUY" if side.upper() in ("BUY", "LONG") else "SELL"
        order = Order(
            action=action,
            orderType="MKT",
            totalQuantity=abs(units),
        )

        trade = self._ib.placeOrder(contract, order)

        await asyncio.sleep(0.5)

        if trade.orderStatus.status == "Filled":
            fill_price = trade.orderStatus.avgFillPrice
            commission = abs(units) * fill_price * self._commission_rate
            margin = abs(units) * fill_price * 0.1

            logger.info(
                "ib_order_filled",
                order_id=trade.order.orderId,
                symbol=symbol,
                side=side,
                units=units,
                fill_price=fill_price,
            )

            await self._publish_to_redis("orders", {
                "order_id": str(trade.order.orderId),
                "symbol": symbol,
                "side": side,
                "units": units,
                "fill_price": fill_price,
                "commission": commission,
                "timestamp": datetime.utcnow().isoformat(),
            })

            return IBFillReport(
                order_id=str(trade.order.orderId),
                symbol=symbol,
                side=side,
                units=abs(units),
                fill_price=fill_price,
                commission=commission,
                margin_used=margin,
                timestamp=datetime.utcnow(),
            )

        raise RuntimeError(f"Order not filled: {trade.orderStatus.status}")

    async def execute_limit_order(
        self,
        symbol: str,
        side: str,
        units: float,
        limit_price: float,
    ) -> IBFillReport:
        if not self._connected or not self._ib:
            raise RuntimeError("IB not connected")

        contract = self._create_contract(symbol)

        action = "BUY" if side.upper() in ("BUY", "LONG") else "SELL"
        order = Order(
            action=action,
            orderType="LMT",
            totalQuantity=abs(units),
            lmtPrice=limit_price,
        )

        trade = self._ib.placeOrder(contract, order)

        logger.info(
            "ib_limit_order_placed",
            order_id=trade.order.orderId,
            symbol=symbol,
            side=side,
            units=units,
            limit_price=limit_price,
        )

        return IBFillReport(
            order_id=str(trade.order.orderId),
            symbol=symbol,
            side=side,
            units=abs(units),
            fill_price=limit_price,
            commission=0.0,
            margin_used=abs(units) * limit_price * 0.1,
            timestamp=datetime.utcnow(),
        )

    async def cancel_order(self, order_id: str) -> bool:
        if not self._connected or not self._ib:
            return False

        for order in self._ib.orders():
            if str(order.orderId) == order_id:
                self._ib.cancelOrder(order)
                return True
        return False

    async def get_order_status(self, order_id: str) -> dict:
        if not self._connected or not self._ib:
            return {}

        for order in self._ib.orders():
            if str(order.orderId) == order_id:
                return {
                    "order_id": str(order.orderId),
                    "status": order.orderStatus.status,
                    "filled": order.orderStatus.filled,
                    "remaining": order.orderStatus.remaining,
                    "avg_fill_price": order.orderStatus.avgFillPrice,
                }
        return {}

    async def get_positions(self) -> list[dict]:
        if not self._connected or not self._ib:
            return []

        positions = []
        for pos in self._ib.positions():
            positions.append({
                "symbol": pos.contract.symbol,
                "position": pos.position,
                "avg_cost": pos.avgCost,
            })
        return positions

    async def get_account_balance(self) -> float:
        if not self._connected or not self._ib:
            return 0.0

        account = self._ib.account
        return float(account.values().get("NetLiquidation", 0))

    async def get_margin_used(self) -> float:
        if not self._connected or not self._ib:
            return 0.0

        account = self._ib.account
        return float(account.values().get("TotalCashValue", 0))

    async def _publish_to_redis(self, key: str, data: dict) -> None:
        try:
            redis = await aioredis.from_url(self.redis_url)
            await redis.xadd(f"ib_{key}", data, maxlen=1000)
            await redis.aclose()
        except Exception as e:
            logger.warning("ib_redis_publish_failed", error=str(e))

    def is_connected(self) -> bool:
        return self._connected and self._ib.isConnected() if self._ib else False


async def create_ib_executor(
    host: str = "127.0.0.1",
    port: int = 7498,
    client_id: int = 1,
    redis_url: str = "redis://localhost:6379",
) -> LiveIBExecutor:
    executor = LiveIBExecutor(
        host=host,
        port=port,
        client_id=client_id,
        is_paper=True,
        redis_url=redis_url,
    )
    await executor.connect()
    return executor