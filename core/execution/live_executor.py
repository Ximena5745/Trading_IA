"""
Module: core/execution/live_executor.py
Responsibility: Live order execution on Binance (testnet or mainnet)
Dependencies: python-binance, base_executor, models, logger
CRITICAL: Only active when EXECUTION_MODE=live AND TRADING_ENABLED=True
"""
from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from core.config.settings import Settings
from core.exceptions import ExecutionError, KillSwitchActiveError
from core.execution.base_executor import AbcExecutor
from core.observability.logger import get_logger
from core.risk.kill_switch import KillSwitch

logger = get_logger(__name__)


class LiveExecutor(AbcExecutor):
    """
    Connects to Binance real (or testnet) and submits real orders.
    Guards:
    1. EXECUTION_MODE must be 'live'
    2. TRADING_ENABLED must be True
    3. Kill switch must be inactive
    4. Idempotency key checked before every order
    """

    def __init__(self, settings: Settings, kill_switch: KillSwitch):
        self._settings = settings
        self._kill_switch = kill_switch
        self._client = None
        self._submitted_keys: set[str] = set()

    async def connect(self) -> None:
        from binance import AsyncClient
        self._client = await AsyncClient.create(
            api_key=self._settings.BINANCE_API_KEY,
            api_secret=self._settings.BINANCE_SECRET_KEY,
            testnet=self._settings.BINANCE_TESTNET,
        )
        logger.info("live_executor_connected", testnet=self._settings.BINANCE_TESTNET)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.close_connection()

    async def execute(self, signal: dict, quantity: float) -> dict:
        self._safety_checks(signal)

        idempotency_key = signal.get("idempotency_key", "")
        if idempotency_key and idempotency_key in self._submitted_keys:
            raise ExecutionError(f"Duplicate order detected: {idempotency_key}")

        if not self._client:
            raise ExecutionError("LiveExecutor not connected")

        symbol = signal["symbol"]
        side = signal["action"]
        try:
            from binance.enums import ORDER_TYPE_MARKET, SIDE_BUY, SIDE_SELL
            binance_side = SIDE_BUY if side == "BUY" else SIDE_SELL
            raw_order = await self._client.create_order(
                symbol=symbol,
                side=binance_side,
                type=ORDER_TYPE_MARKET,
                quantity=round(quantity, 6),
                newClientOrderId=idempotency_key[:36] if idempotency_key else None,
            )
        except Exception as e:
            logger.error("live_order_failed", symbol=symbol, side=side, error=str(e))
            raise ExecutionError(f"Binance order failed: {e}") from e

        if idempotency_key:
            self._submitted_keys.add(idempotency_key)

        fill_price = float(raw_order.get("fills", [{}])[0].get("price", signal["entry_price"]))
        commission = sum(float(f.get("commission", 0)) for f in raw_order.get("fills", []))

        order = {
            "id": str(uuid4()),
            "exchange_order_id": str(raw_order.get("orderId")),
            "idempotency_key": idempotency_key,
            "signal_id": signal.get("id", ""),
            "symbol": symbol,
            "side": side,
            "order_type": "MARKET",
            "quantity": quantity,
            "fill_price": round(fill_price, 8),
            "fill_quantity": float(raw_order.get("executedQty", quantity)),
            "commission": round(commission, 8),
            "slippage": round(fill_price - signal["entry_price"], 8),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
            "status": "filled",
            "execution_mode": "live",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "error_message": None,
        }
        logger.info(
            "live_trade_executed",
            symbol=symbol, side=side, qty=quantity,
            fill_price=fill_price, commission=commission,
            exchange_order_id=order["exchange_order_id"],
        )
        return order

    async def cancel_order(self, order_id: str) -> dict:
        if not self._client:
            raise ExecutionError("LiveExecutor not connected")
        
        try:
            # Get order details to find symbol
            order_info = await self.get_order_status(order_id)
            symbol = order_info.get("symbol")
            if not symbol:
                raise ExecutionError(f"Cannot find symbol for order {order_id}")
            
            from binance.enums import ORDER_TYPE_MARKET
            raw_result = await self._client.cancel_order(
                symbol=symbol,
                orderId=order_info.get("exchange_order_id")
            )
            
            logger.info("live_order_cancelled", order_id=order_id, symbol=symbol)
            return {
                "id": order_id,
                "status": "cancelled",
                "cancelled_at": datetime.utcnow().isoformat(),
                "exchange_response": raw_result,
            }
        except Exception as e:
            logger.error("live_order_cancel_failed", order_id=order_id, error=str(e))
            raise ExecutionError(f"Failed to cancel order {order_id}: {e}") from e

    async def get_order_status(self, order_id: str) -> dict:
        if not self._client:
            raise ExecutionError("LiveExecutor not connected")
        
        # This would require maintaining a mapping of order_id to exchange_order_id and symbol
        # For now, implement a basic lookup
        try:
            # This is a simplified implementation - in production, you'd need
            # proper order tracking with symbol and exchange_order_id mapping
            logger.warning("get_order_status_simplified", order_id=order_id)
            return {
                "id": order_id,
                "status": "unknown",
                "message": "Order status lookup requires full implementation"
            }
        except Exception as e:
            logger.error("get_order_status_failed", order_id=order_id, error=str(e))
            raise ExecutionError(f"Failed to get order status {order_id}: {e}") from e

    def _safety_checks(self, signal: dict) -> None:
        if self._settings.EXECUTION_MODE != "live":
            raise ExecutionError(
                f"LiveExecutor requires EXECUTION_MODE=live, got '{self._settings.EXECUTION_MODE}'"
            )
        if not self._settings.TRADING_ENABLED:
            raise ExecutionError("TRADING_ENABLED is False — set to True to allow live trading")
        if self._kill_switch.is_active():
            raise KillSwitchActiveError(
                f"Kill switch active: {self._kill_switch.state.triggered_by}"
            )
