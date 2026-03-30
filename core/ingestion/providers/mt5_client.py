"""
Module: core/ingestion/providers/mt5_client.py
Responsibility: MetaTrader 5 adapter for multiasset trading
Dependencies: MetaTrader5, exchange_adapter, models, logger

Supported asset classes (depends on broker):
  - forex    → EURUSD, GBPUSD, USDJPY, etc.
  - indices  → SPX500, NAS100, FTSE, DAX, JP225, etc.
  - commodities → XAUUSD, XAGUSD, USOIL, NATGAS, WHEAT, etc.
  - stocks   → AAPL, MSFT, GOOGL, TSLA, etc. (if offered by broker)
  - futures  → ES, NQ, GC, CL, NG, ZW (if offered by broker)

Installation:
  pip install MetaTrader5==5.0.5640 (Windows only)

Connection:
  1. Install MetaTrader 5 from your broker
  2. Ensure MT5 is running (daemon mode)
  3. Specify account number and server name

Example brokers supporting MT5:
  - ICMarkets
  - Pepperstone
  - Admiral Markets
  - IG Markets
  - XM Group
  - Axiory
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from core.ingestion.exchange_adapter import ExchangeAdapter
from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)

# MT5 timeframe mapping
MT5_TIMEFRAME_MAP: dict[str, int] = {}  # populated lazily on first import of MetaTrader5

# Maximum retries on connection failure
MAX_CONNECT_RETRIES = 5


def _get_mt5():
    """Lazy import so the module loads on non-Windows without crashing."""
    try:
        import MetaTrader5 as mt5
        return mt5
    except ImportError:
        raise RuntimeError(
            "MetaTrader5 package not installed or not available on this OS. "
            "Install with: pip install MetaTrader5==5.0.5640 (Windows only)"
        )


def _build_timeframe_map() -> dict[str, int]:
    mt5 = _get_mt5()
    return {
        "1m":  mt5.TIMEFRAME_M1,
        "5m":  mt5.TIMEFRAME_M5,
        "15m": mt5.TIMEFRAME_M15,
        "30m": mt5.TIMEFRAME_M30,
        "1h":  mt5.TIMEFRAME_H1,
        "4h":  mt5.TIMEFRAME_H4,
        "1d":  mt5.TIMEFRAME_D1,
        "1w":  mt5.TIMEFRAME_W1,
    }


class MT5Client(ExchangeAdapter):
    """MetaTrader 5 adapter via MetaTrader5 library.

    Status: production-ready for paper and live trading.
    Supports any asset class offered by the broker.
    Windows-only (MetaTrader5 library limitation).

    Usage:
        client = MT5Client(server="ICMarketsSC-Demo04", account_number=12345678, password="secret")
        await client.connect()
        candles = await client.get_klines("EURUSD", "1h", 500)
        await client.disconnect()
    """

    exchange_id = "mt5"
    supported_asset_classes = ("forex", "indices", "commodities", "stocks", "futures")

    def __init__(self, server: str, account_number: int, password: str):
        self._server = server
        self._account_number = account_number
        self._password = password
        self._connected = False
        self._timeframe_map: dict[str, int] = {}

    async def connect(self) -> None:
        """Initialize MT5 terminal connection with exponential backoff."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._connect_sync)

    def _connect_sync(self) -> None:
        mt5 = _get_mt5()
        self._timeframe_map = _build_timeframe_map()

        for attempt in range(1, MAX_CONNECT_RETRIES + 1):
            if not mt5.initialize():
                logger.warning("mt5_init_failed", attempt=attempt, error=mt5.last_error())
                import time; time.sleep(2 ** attempt)
                continue

            authorized = mt5.login(
                login=self._account_number,
                password=self._password,
                server=self._server,
            )
            if not authorized:
                mt5.shutdown()
                raise RuntimeError(
                    f"MT5 login failed — server={self._server}, login={self._login}, "
                    f"error={mt5.last_error()}"
                )

            info = mt5.account_info()
            self._connected = True
            logger.info(
                "mt5_connected",
                server=self._server,
                account_number=self._account_number,
                balance=info.balance if info else None,
                currency=info.currency if info else None,
            )
            return

        raise RuntimeError(f"MT5 connection failed after {MAX_CONNECT_RETRIES} attempts")

    async def disconnect(self) -> None:
        if self._connected:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, _get_mt5().shutdown)
            self._connected = False
            logger.info("mt5_disconnected")

    async def get_klines(
        self,
        symbol: str,
        interval: str,
        limit: int = 500,
    ) -> list[MarketData]:
        """Fetch the last `limit` candles for `symbol` at `interval` timeframe."""
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_klines_sync, symbol, interval, limit
        )

    def _get_klines_sync(self, symbol: str, interval: str, limit: int) -> list[MarketData]:
        mt5 = _get_mt5()
        tf = self._timeframe_map.get(interval)
        if tf is None:
            raise ValueError(f"Unsupported MT5 interval: {interval}. Supported: {list(self._timeframe_map)}")

        rates = mt5.copy_rates_from_pos(symbol, tf, 0, limit)
        if rates is None or len(rates) == 0:
            error = mt5.last_error()
            logger.warning("mt5_no_rates", symbol=symbol, interval=interval, error=error)
            return []

        candles = [self._parse_rate(symbol, r) for r in rates]
        logger.info("mt5_klines_fetched", symbol=symbol, interval=interval, count=len(candles))
        return candles

    @staticmethod
    def _parse_rate(symbol: str, r) -> MarketData:
        return MarketData(
            timestamp=datetime.fromtimestamp(r["time"], tz=timezone.utc),
            symbol=symbol,
            open=Decimal(str(r["open"])),
            high=Decimal(str(r["high"])),
            low=Decimal(str(r["low"])),
            close=Decimal(str(r["close"])),
            volume=Decimal(str(r["tick_volume"])),
            source="mt5",
        )

    async def get_tick(self, symbol: str) -> Optional[dict]:
        """Return latest bid/ask for a symbol."""
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_tick_sync, symbol)

    def _get_tick_sync(self, symbol: str) -> Optional[dict]:
        mt5 = _get_mt5()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        return {"bid": tick.bid, "ask": tick.ask, "time": tick.time, "symbol": symbol}

    async def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Return symbol metadata including pip_value, lot_size, swap rates."""
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_symbol_info_sync, symbol)

    def _get_symbol_info_sync(self, symbol: str) -> Optional[dict]:
        mt5 = _get_mt5()
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        return {
            "symbol":       info.name,
            "description":  info.description,
            "trade_contract_size": info.trade_contract_size,
            "point":        info.point,           # smallest price change
            "digits":       info.digits,
            "lot_size":     info.trade_contract_size,
            "lot_step":     info.volume_step,
            "min_lots":     info.volume_min,
            "max_lots":     info.volume_max,
            "swap_long":    info.swap_long,       # swap per lot per night (long)
            "swap_short":   info.swap_short,      # swap per lot per night (short)
            "currency_profit": info.currency_profit,
            "spread":       info.spread,          # in points
        }

    async def place_order(
        self,
        symbol: str,
        side: str,
        volume: float,
        sl: float = 0.0,
        tp: float = 0.0,
        idempotency_key: str = "",
        **kwargs,
    ) -> dict:
        """
        Submit a market order to MT5.
        Only callable when EXECUTION_MODE=live and TRADING_ENABLED=True
        — guard is enforced by MT5Executor, not here.
        """
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._place_order_sync, symbol, side, volume, sl, tp, idempotency_key
        )

    def _place_order_sync(
        self, symbol: str, side: str, volume: float, sl: float, tp: float, comment: str
    ) -> dict:
        mt5 = _get_mt5()
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise RuntimeError(f"No tick data for {symbol}")

        action = mt5.TRADE_ACTION_DEAL
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        price = tick.ask if side == "BUY" else tick.bid

        request = {
            "action":    action,
            "symbol":    symbol,
            "volume":    round(volume, 2),
            "type":      order_type,
            "price":     price,
            "sl":        sl,
            "tp":        tp,
            "deviation": 10,
            "magic":     202400,      # magic number to identify TRADER AI orders
            "comment":   comment[:31] if comment else "TRADER_AI",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = result.retcode if result else "None"
            comment_err = result.comment if result else mt5.last_error()
            raise RuntimeError(
                f"MT5 order_send failed: retcode={retcode}, comment={comment_err}"
            )

        logger.info(
            "mt5_order_placed",
            symbol=symbol, side=side, volume=volume,
            price=price, order_id=result.order,
        )
        return {
            "exchange_order_id": str(result.order),
            "symbol":     symbol,
            "side":       side,
            "volume":     volume,
            "fill_price": result.price,
            "retcode":    result.retcode,
        }

    # ── Order book (MT5 does not expose L2) ─────────────────────────────────

    async def get_order_book(
        self,
        symbol: str,
        depth: int = 20,
    ) -> dict:
        """MT5 does not expose L2 order book.
        Returns best bid/ask from tick data instead.
        """
        return await self.get_tick(symbol)

    # ── Balance ─────────────────────────────────────────────────────────────

    async def get_balance(self, asset: str = "USD") -> float:
        """Fetch account balance in account currency."""
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        loop = asyncio.get_event_loop()
        balance_info = await loop.run_in_executor(None, self._get_balance_sync)
        return float(balance_info.get("balance", 0.0))

    def _get_balance_sync(self) -> dict:
        mt5 = _get_mt5()
        info = mt5.account_info()
        if info is None:
            return {}
        return {
            "balance":  info.balance,
            "equity":   info.equity,
            "margin":   info.margin,
            "free_margin": info.margin_free,
            "currency": info.currency,
            "leverage": info.leverage,
        }

    # ── Order cancellation ──────────────────────────────────────────────────

    async def cancel_order(self, symbol: str, order_id: str) -> dict:
        """Close/cancel an open position (not fully supported in MT5 in this version)."""
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        logger.warning(
            "mt5_cancel_order_limited",
            note="MT5 order cancellation has limited support; use close_position instead",
        )
        return {"order_id": order_id, "status": "NOT_IMPLEMENTED"}

    # ── Order status ────────────────────────────────────────────────────────

    async def get_order_status(self, symbol: str, order_id: str) -> dict:
        """Get status of an order."""
        if not self._connected:
            raise RuntimeError("MT5Client not connected")
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._get_order_status_sync, symbol, order_id
        )

    def _get_order_status_sync(self, symbol: str, order_id: str) -> dict:
        mt5 = _get_mt5()
        # Check open positions
        positions = mt5.positions_get(symbol=symbol)
        if not positions:
            return {"order_id": order_id, "status": "NOT_FOUND"}

        for position in positions:
            if str(position.ticket) == order_id:
                return {
                    "order_id": str(position.ticket),
                    "symbol": symbol,
                    "status": "OPEN",
                    "type": "BUY" if position.type == mt5.ORDER_TYPE_BUY else "SELL",
                    "volume": float(position.volume),
                    "price_open": float(position.price_open),
                    "price_current": float(position.price_current),
                    "profit": float(position.profit),
                    "time": position.time,
                }
        return {"order_id": order_id, "status": "NOT_FOUND"}
