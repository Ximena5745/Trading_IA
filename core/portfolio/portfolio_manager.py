"""
Module: core/portfolio/portfolio_manager.py
Responsibility: Capital allocation across strategies with Kelly criterion
Dependencies: models, settings, logger
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import uuid4

from core.config.constants import HARD_LIMITS
from core.config.settings import Settings
from core.models import Portfolio, Position, Signal
from core.observability.logger import get_logger

logger = get_logger(__name__)


class PortfolioManager:
    def __init__(self, settings: Settings, initial_capital: float = 10000.0):
        self._settings = settings
        self._portfolio = Portfolio(
            id=str(uuid4()),
            total_capital=initial_capital,
            available_capital=initial_capital,
            positions=[],
            risk_exposure=0.0,
            daily_pnl=0.0,
            daily_pnl_pct=0.0,
            total_pnl=0.0,
            drawdown_current=0.0,
            drawdown_max=0.0,
            updated_at=datetime.utcnow(),
        )
        self._peak_capital = initial_capital
        self._daily_start_capital = initial_capital

    def get_portfolio(self) -> Portfolio:
        return self._portfolio

    def get_available_capital(self) -> float:
        return self._portfolio.available_capital

    def open_position(self, signal: Signal, quantity: float, fill_price: float) -> Position:
        position = Position(
            symbol=signal.symbol,
            quantity=quantity,
            entry_price=fill_price,
            current_price=fill_price,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            strategy_id=signal.strategy_id,
            opened_at=datetime.utcnow(),
        )
        cost = fill_price * quantity
        self._portfolio.available_capital -= cost
        self._portfolio.positions.append(position)
        self._update_risk_exposure()
        self._portfolio.updated_at = datetime.utcnow()
        logger.info("position_opened", symbol=signal.symbol, qty=quantity, price=fill_price, cost=cost)
        return position

    def close_position(self, symbol: str, exit_price: float, strategy_id: str) -> Optional[float]:
        for i, pos in enumerate(self._portfolio.positions):
            if pos.symbol == symbol and pos.strategy_id == strategy_id:
                pnl = (exit_price - pos.entry_price) * pos.quantity
                proceeds = exit_price * pos.quantity
                self._portfolio.available_capital += proceeds
                self._portfolio.total_pnl += pnl
                self._portfolio.daily_pnl += pnl
                self._portfolio.positions.pop(i)
                self._update_metrics()
                logger.info("position_closed", symbol=symbol, pnl=round(pnl, 4), exit_price=exit_price)
                return pnl
        logger.warning("close_position_not_found", symbol=symbol, strategy_id=strategy_id)
        return None

    def update_prices(self, prices: dict[str, float]) -> None:
        for pos in self._portfolio.positions:
            if pos.symbol in prices:
                pos.current_price = prices[pos.symbol]
                pos.unrealized_pnl = (pos.current_price - pos.entry_price) * pos.quantity
                pos.unrealized_pnl_pct = pos.unrealized_pnl / (pos.entry_price * pos.quantity)
        self._update_metrics()

    def kelly_fraction(self, win_rate: float, avg_win: float, avg_loss: float) -> float:
        """
        Full Kelly criterion: f* = (p * b - q) / b
        where b = avg_win/avg_loss, p = win_rate, q = 1 - p
        Capped at MAX_RISK_PER_TRADE_PCT hard limit.
        """
        if avg_loss == 0:
            return 0.0
        b = avg_win / avg_loss
        q = 1.0 - win_rate
        kelly = (win_rate * b - q) / b
        kelly = max(0.0, kelly * 0.5)  # half-Kelly for safety
        return min(kelly, HARD_LIMITS["max_risk_per_trade_pct"])

    def allocate_to_strategies(self, strategy_ids: list[str]) -> dict[str, float]:
        """Equal-weight allocation across active strategies, capped per strategy."""
        if not strategy_ids:
            return {}
        per_strategy = self._portfolio.total_capital / len(strategy_ids)
        max_per = self._portfolio.total_capital * 0.30  # max 30% per strategy
        allocation = min(per_strategy, max_per)
        return {sid: round(allocation, 2) for sid in strategy_ids}

    def reset_daily(self) -> None:
        self._daily_start_capital = self._portfolio.total_capital
        self._portfolio.daily_pnl = 0.0
        self._portfolio.daily_pnl_pct = 0.0
        logger.info("portfolio_daily_reset", capital=self._portfolio.total_capital)

    def _update_risk_exposure(self) -> None:
        total_at_risk = sum(
            abs(pos.entry_price - 0) * pos.quantity
            for pos in self._portfolio.positions
        )
        self._portfolio.risk_exposure = (
            total_at_risk / self._portfolio.total_capital
            if self._portfolio.total_capital > 0 else 0.0
        )

    def _update_metrics(self) -> None:
        unrealized = sum(pos.unrealized_pnl for pos in self._portfolio.positions)
        self._portfolio.total_capital = (
            self._portfolio.available_capital
            + sum(pos.current_price * pos.quantity for pos in self._portfolio.positions)
        )
        if self._portfolio.total_capital > self._peak_capital:
            self._peak_capital = self._portfolio.total_capital

        self._portfolio.drawdown_current = (
            (self._peak_capital - self._portfolio.total_capital) / self._peak_capital
            if self._peak_capital > 0 else 0.0
        )
        self._portfolio.drawdown_max = max(
            self._portfolio.drawdown_max, self._portfolio.drawdown_current
        )
        if self._daily_start_capital > 0:
            self._portfolio.daily_pnl_pct = (
                self._portfolio.daily_pnl / self._daily_start_capital
            )
        self._portfolio.updated_at = datetime.utcnow()
