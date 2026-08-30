"""
Module: core/portfolio/portfolio_manager_redis.py
Responsibility: PortfolioManager con persistencia Redis para multi-worker deployments
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Optional

import redis

from core.config.settings import get_settings
from core.models import Portfolio, Position
from core.observability.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

PORTFOLIO_KEY = "trader:portfolio:state"
CLOSED_TRADES_KEY = "trader:portfolio:closed_trades"
CLOSED_TRADES_MAX = 200


class PortfolioManagerRedis:
    """
    PortfolioManager persistido en Redis.
    Permite múltiples workers sin race conditions.
    """

    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._default_capital = 10000.0

    def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    def _load_portfolio(self) -> dict:
        """Carga portfolio desde Redis."""
        try:
            data = self._get_redis().get(PORTFOLIO_KEY)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning("portfolio_load_error", error=str(e))

        return {
            "id": "default",
            "total_capital": self._default_capital,
            "available_capital": self._default_capital,
            "positions": [],
            "risk_exposure": 0.0,
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "total_pnl": 0.0,
            "drawdown_current": 0.0,
            "drawdown_max": 0.0,
            "updated_at": datetime.utcnow().isoformat(),
        }

    def _save_portfolio(self, portfolio: dict) -> None:
        """Guarda portfolio en Redis."""
        try:
            portfolio["updated_at"] = datetime.utcnow().isoformat()
            self._get_redis().set(PORTFOLIO_KEY, json.dumps(portfolio, default=str))
        except Exception as e:
            logger.error("portfolio_save_error", error=str(e))

    def get_portfolio(self) -> Portfolio:
        """Retorna el portfolio actual como objeto Portfolio."""
        data = self._load_portfolio()
        positions = []
        for p in data.get("positions", []):
            positions.append(Position(**p))
        return Portfolio(
            id=data.get("id", "default"),
            total_capital=data.get("total_capital", self._default_capital),
            available_capital=data.get("available_capital", self._default_capital),
            positions=positions,
            risk_exposure=data.get("risk_exposure", 0.0),
            daily_pnl=data.get("daily_pnl", 0.0),
            daily_pnl_pct=data.get("daily_pnl_pct", 0.0),
            total_pnl=data.get("total_pnl", 0.0),
            drawdown_current=data.get("drawdown_current", 0.0),
            drawdown_max=data.get("drawdown_max", 0.0),
            updated_at=datetime.utcnow(),
        )

    def open_position(self, signal: dict, quantity: float, fill_price: float) -> None:
        """Abre una nueva posición."""
        portfolio = self._load_portfolio()

        position = {
            "symbol": signal.get("symbol"),
            "asset_class": signal.get("asset_class", "crypto"),
            "quantity": quantity,
            "entry_price": fill_price,
            "current_price": fill_price,
            "unrealized_pnl": 0.0,
            "unrealized_pnl_pct": 0.0,
            "strategy_id": signal.get("strategy_id", "manual"),
            "opened_at": datetime.utcnow().isoformat(),
            "stop_loss": signal.get("stop_loss"),
            "take_profit": signal.get("take_profit"),
        }

        portfolio["positions"].append(position)

        position_value = quantity * fill_price
        portfolio["available_capital"] -= position_value

        self._save_portfolio(portfolio)
        logger.info("position_opened_redis", symbol=signal.get("symbol"), quantity=quantity)

    def close_position(self, symbol: str, exit_price: float) -> dict:
        """Cierra una posición por símbolo."""
        portfolio = self._load_portfolio()
        closed_position = None

        for i, pos in enumerate(portfolio.get("positions", [])):
            if pos.get("symbol") == symbol:
                closed_position = pos
                entry_price = pos.get("entry_price", 0)
                quantity = pos.get("quantity", 0)

                pnl = (exit_price - entry_price) * quantity
                portfolio["total_pnl"] += pnl
                portfolio["daily_pnl"] += pnl

                recovered_value = quantity * exit_price
                portfolio["available_capital"] += recovered_value

                portfolio["positions"].pop(i)
                self._record_closed_trade(
                    {
                        "symbol": symbol,
                        "strategy_id": pos.get("strategy_id"),
                        "net_pnl": round(pnl, 8),
                        "exit_price": exit_price,
                        "closed_at": datetime.utcnow().isoformat(),
                    }
                )
                break

        self._save_portfolio(portfolio)

        if closed_position:
            logger.info("position_closed_redis", symbol=symbol, pnl=closed_position.get("unrealized_pnl"))

        return closed_position or {}

    def _record_closed_trade(self, trade: dict) -> None:
        try:
            r = self._get_redis()
            r.rpush(CLOSED_TRADES_KEY, json.dumps(trade, default=str))
            r.ltrim(CLOSED_TRADES_KEY, -CLOSED_TRADES_MAX, -1)
        except Exception as e:  # noqa: BLE001
            logger.warning("closed_trade_record_error", error=str(e))

    def get_recent_trades(self, limit: int = 20) -> list[dict]:
        """Most recent closed trades, oldest→newest, each with ``net_pnl``."""
        try:
            raw = self._get_redis().lrange(CLOSED_TRADES_KEY, -limit, -1)
            return [json.loads(x) for x in raw]
        except Exception as e:  # noqa: BLE001
            logger.warning("recent_trades_load_error", error=str(e))
            return []

    def update_positions_prices(self, prices: dict) -> None:
        """Actualiza precios de posiciones abiertas y calcula PnL."""
        portfolio = self._load_portfolio()

        for pos in portfolio.get("positions", []):
            symbol = pos.get("symbol")
            if symbol in prices:
                current_price = prices[symbol]
                entry_price = pos.get("entry_price", 0)
                quantity = pos.get("quantity", 0)

                pos["current_price"] = current_price
                pnl = (current_price - entry_price) * quantity
                pos["unrealized_pnl"] = pnl
                pos["unrealized_pnl_pct"] = (pnl / (entry_price * quantity)) if entry_price * quantity > 0 else 0

        self._save_portfolio(portfolio)

    def get_position(self, symbol: str) -> Optional[dict]:
        """Obtiene una posición por símbolo."""
        portfolio = self._load_portfolio()
        for pos in portfolio.get("positions", []):
            if pos.get("symbol") == symbol:
                return pos
        return None

    def reset(self) -> None:
        """Resetea el portfolio a valores iniciales."""
        self._save_portfolio({
            "id": "default",
            "total_capital": self._default_capital,
            "available_capital": self._default_capital,
            "positions": [],
            "risk_exposure": 0.0,
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "total_pnl": 0.0,
            "drawdown_current": 0.0,
            "drawdown_max": 0.0,
            "updated_at": datetime.utcnow().isoformat(),
        })
        logger.warning("portfolio_reset_redis")


def get_portfolio_manager_redis() -> PortfolioManagerRedis:
    """Factory function for PortfolioManagerRedis."""
    return PortfolioManagerRedis()