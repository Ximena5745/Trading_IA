"""
Module: core/execution/mt5_executor.py
Responsibility: Live order execution via MetaTrader 5.
  Implements AbcExecutor for MT5 symbols (forex, indices, commodities, crypto CFD).
  Only active after FASE E paper validation is complete.

CRITICAL safety rules (same as LiveExecutor):
  1. EXECUTION_MODE must be 'live'
  2. TRADING_ENABLED must be True
  3. Kill switch must be inactive
  4. idempotency_key checked before every order

Broker: IC Markets (preferred), Pepperstone (fallback), Tickmill.
All symbol names must match InstrumentConfig.mt5_symbol (IC Markets exact names).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from core.config.settings import Settings
from core.exceptions import ExecutionError, KillSwitchActiveError
from core.execution.base_executor import AbcExecutor
from core.ingestion.providers.mt5_client import MT5Client
from core.models import get_instrument
from core.observability.logger import get_logger
from core.risk.kill_switch import KillSwitch

logger = get_logger(__name__)


class MT5Executor(AbcExecutor):
    """
    Live executor for MT5 instruments.
    Requires an already-connected MT5Client instance.

    Usage:
        client = MT5Client(server=..., login=..., password=...)
        await client.connect()
        executor = MT5Executor(settings, kill_switch, client)
        order = await executor.execute(signal_dict, lots)
    """

    def __init__(
        self,
        settings: Settings,
        kill_switch: KillSwitch,
        mt5_client: MT5Client,
    ) -> None:
        self._settings    = settings
        self._kill_switch = kill_switch
        self._client      = mt5_client
        self._submitted_keys: set[str] = set()

    async def execute(self, signal: dict, quantity: float) -> dict:
        """
        Execute a market order on MT5.
        `quantity` is in lots for MT5 instruments.
        """
        self._safety_checks(signal)

        idempotency_key = signal.get("idempotency_key", "")
        if idempotency_key and idempotency_key in self._submitted_keys:
            raise ExecutionError(f"Duplicate MT5 order detected: {idempotency_key}")

        symbol = signal["symbol"]
        side   = signal["action"]   # "BUY" | "SELL"

        # Resolve mt5_symbol from InstrumentConfig (IC Markets exact name)
        instrument = get_instrument(symbol)
        mt5_symbol = instrument.mt5_symbol if instrument else symbol

        sl = signal.get("stop_loss", 0.0)
        tp = signal.get("take_profit", 0.0)

        try:
            raw = await self._client.place_order(
                symbol=mt5_symbol,
                side=side,
                volume=round(quantity, 2),
                sl=sl or 0.0,
                tp=tp or 0.0,
                idempotency_key=idempotency_key[:31] if idempotency_key else "TRADER_AI",
            )
        except RuntimeError as e:
            logger.error("mt5_order_failed", symbol=mt5_symbol, side=side, error=str(e))
            raise ExecutionError(f"MT5 order failed: {e}") from e

        if idempotency_key:
            self._submitted_keys.add(idempotency_key)

        fill_price = raw.get("fill_price", signal.get("entry_price", 0.0))
        now = datetime.now(timezone.utc)

        order = {
            "id":               str(uuid.uuid4()),
            "exchange_order_id": raw.get("exchange_order_id"),
            "idempotency_key":  idempotency_key,
            "signal_id":        signal.get("id", ""),
            "symbol":           symbol,
            "mt5_symbol":       mt5_symbol,
            "side":             side,
            "order_type":       "MARKET",
            "quantity":         quantity,
            "fill_price":       round(fill_price, 8),
            "fill_quantity":    quantity,
            "commission":       0.0,    # IC Markets Raw: spread-based, no separate commission
            "slippage":         round(fill_price - signal.get("entry_price", fill_price), 8),
            "stop_loss":        sl,
            "take_profit":      tp,
            "status":           "filled",
            "execution_mode":   "live",
            "provider":         "mt5",
            "created_at":       now.isoformat(),
            "updated_at":       now.isoformat(),
            "error_message":    None,
        }

        logger.info(
            "mt5_trade_executed",
            symbol=mt5_symbol,
            side=side,
            lots=quantity,
            fill_price=fill_price,
            exchange_order_id=raw.get("exchange_order_id"),
        )
        return order

    async def cancel_order(self, order_id: str) -> dict:
        raise NotImplementedError(
            "MT5 order cancellation not implemented — use MT5 terminal or pending order management"
        )

    async def get_order_status(self, order_id: str) -> dict:
        raise NotImplementedError("MT5 order status lookup not implemented in this phase")

    # ── Safety guards ─────────────────────────────────────────────────────────

    def _safety_checks(self, signal: dict) -> None:
        if self._settings.EXECUTION_MODE != "live":
            raise ExecutionError(
                f"MT5Executor requires EXECUTION_MODE=live, got '{self._settings.EXECUTION_MODE}'"
            )
        if not self._settings.TRADING_ENABLED:
            raise ExecutionError(
                "TRADING_ENABLED is False — set to True to allow live MT5 trading"
            )
        if self._kill_switch.is_active():
            raise KillSwitchActiveError(
                f"Kill switch active: {self._kill_switch.state.triggered_by}"
            )
