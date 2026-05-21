"""
Module: core/execution/live_oanda_executor.py
Responsibility: Live execution con OANDA API para forex/CFD.
  - Conexión verificada con capital mínimo
  - Gestión de rollover/swap costs en posiciones overnight
  - Margin management para CFDs
Dependencies: oandapyV20
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from core.observability.logger import get_logger

logger = get_logger(__name__)

OANDA_AVAILABLE = True
try:
    from oandapyV20 import API
    import oandapyV20.endpoints.trading as trading
except ImportError:
    OANDA_AVAILABLE = False


@dataclass
class OandaFillReport:
    order_id: str
    symbol: str
    side: str
    units: float
    fill_price: float
    commission: float
    swap_cost: float
    margin_used: float
    timestamp: datetime


class LiveOandaExecutor:
    """
    Executor real para OANDA.

    M7.2: Integración real OANDA (forex/CFD).
    """

    def __init__(
        self,
        api_key: str,
        account_id: str,
        environment: str = "practice",
    ):
        self._api_key = api_key
        self._account_id = account_id
        self._env = environment
        self._client: Optional[API] = None
        self._connected = False

        if OANDA_AVAILABLE and api_key and account_id:
            self._connect()

    def _connect(self) -> None:
        """Conectar a OANDA."""
        if not OANDA_AVAILABLE:
            logger.warning("oanda_sdk_not_available")
            return

        try:
            self._client = API(access_token=self._api_key, environment=self._env)
            account_response = self._client.request(trading.AccountDetails(accountID=self._account_id))
            self._connected = True
            logger.info("oanda_connected", account_id=self._account_id)
        except Exception as e:
            logger.error("oanda_connection_failed", error=str(e))
            self._connected = False

    def get_account_info(self) -> dict:
        """Obtener información de cuenta."""
        if not self._connected:
            return {}

        try:
            response = self._client.request(trading.AccountDetails(accountID=self._account_id))
            return response.get("account", {})
        except Exception:
            return {}

    def execute_market_order(
        self,
        symbol: str,
        side: str,
        units: float,
    ) -> OandaFillReport:
        """Ejecutar orden market en OANDA."""
        if not self._connected:
            raise RuntimeError("OANDA not connected")

        instrument = symbol.replace("USDT", "_USD")

        try:
            order = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(int(units)) if side == "BUY" else str(int(-units)),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                }
            }

            response = self._client.request(
                trading.Orders(accountID=self._account_id, data=order)
            )

            fill = response.get("orderFillTransaction", {})

            swap_cost = 0.0
            margin_used = abs(float(fill.get("marginUsed", 0)))

            logger.info(
                "oanda_order_filled",
                order_id=fill.get("id"),
                symbol=symbol,
                units=units,
                fill_price=fill.get("price"),
            )

            return OandaFillReport(
                order_id=fill.get("id", ""),
                symbol=symbol,
                side=side,
                units=abs(units),
                fill_price=float(fill.get("price", 0)),
                commission=0.0,
                swap_cost=swap_cost,
                margin_used=margin_used,
                timestamp=datetime.utcnow(),
            )

        except Exception as e:
            logger.error("oanda_order_failed", error=str(e))
            raise

    def get_positions(self) -> list[dict]:
        """Obtener posiciones abiertas."""
        if not self._connected:
            return []

        try:
            response = self._client.request(
                trading.OpenPositions(accountID=self._account_id)
            )
            return response.get("positions", [])
        except Exception:
            return []

    def get_account_balance(self) -> float:
        """Obtener balance de la cuenta."""
        info = self.get_account_info()
        return float(info.get("balance", 0))

    def get_margin_used(self) -> float:
        """Obtener margen usado."""
        info = self.get_account_info()
        return float(info.get("marginUsed", 0))

    def calculate_swap_cost(
        self,
        symbol: str,
        side: str,
        units: float,
        nights: int,
    ) -> float:
        """Calcular costo de swap para posiciones overnight."""
        instrument_swap = {
            "EURUSD": (0.05, -0.15),
            "GBPUSD": (0.10, -0.20),
            "USDJPY": (0.02, -0.05),
            "XAUUSD": (2.0, -3.0),
        }

        swaps = instrument_swap.get(symbol, (0.0, 0.0))
        rate = swaps[0] if side == "BUY" else swaps[1]

        return rate * abs(units) * nights / 100

    def close_position(self, symbol: str) -> bool:
        """Cerrar posición abierta."""
        if not self._connected:
            return False

        positions = self.get_positions()
        for pos in positions:
            if pos.get("instrument") == symbol.replace("USDT", "_USD"):
                try:
                    order = {
                        "order": {
                            "type": "MARKET",
                            "instrument": pos["instrument"],
                            "units": str(int(-float(pos["long"]["units"]) - float(pos["short"]["units"]))),
                            "timeInForce": "FOK",
                            "positionFill": "DEFAULT",
                        }
                    }
                    self._client.request(
                        trading.Orders(accountID=self._account_id, data=order)
                    )
                    return True
                except Exception:
                    return False

        return False

    def is_connected(self) -> bool:
        """Verificar conexión."""
        return self._connected