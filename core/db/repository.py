"""
Module: core/db/repository.py
Responsibility: CRUD operations for signals, orders, and portfolio snapshots.
  Uses raw asyncpg — no ORM.
Dependencies: asyncpg, session, models
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from core.db.session import get_pool
from core.models import Order, Portfolio, Signal
from core.observability.logger import get_logger

logger = get_logger(__name__)


class TradingRepository:
    """Handles all DB writes for the trading pipeline."""

    async def save_signal(self, signal: Signal) -> None:
        sql = """
            INSERT INTO signals (
                id, idempotency_key, created_at, symbol, action,
                entry_price, stop_loss, take_profit, risk_reward_ratio,
                confidence, explanation, summary, status, strategy_id, regime
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9,
                $10, $11, $12, $13, $14, $15
            )
            ON CONFLICT (idempotency_key) DO NOTHING
        """
        try:
            await get_pool().execute(
                sql,
                signal.id,
                signal.idempotency_key,
                signal.timestamp,
                signal.symbol,
                signal.action,
                signal.entry_price,
                signal.stop_loss,
                signal.take_profit,
                signal.risk_reward_ratio,
                signal.confidence,
                json.dumps([f.model_dump() for f in signal.explanation]),
                signal.summary,
                signal.status,
                signal.strategy_id,
                signal.regime.value if signal.regime else None,
            )
            logger.debug("signal_saved", signal_id=signal.id, symbol=signal.symbol)
        except Exception as e:
            logger.error("signal_save_failed", signal_id=signal.id, error=str(e))

    async def save_order(self, order: dict) -> None:
        sql = """
            INSERT INTO orders (
                id, idempotency_key, signal_id, symbol, side,
                order_type, quantity, fill_price, fill_quantity,
                commission, slippage, status, execution_mode,
                error_message, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8, $9,
                $10, $11, $12, $13,
                $14, $15, $16
            )
            ON CONFLICT (idempotency_key) DO NOTHING
        """
        try:
            now = datetime.now(timezone.utc)
            await get_pool().execute(
                sql,
                order.get("id"),
                order.get("idempotency_key"),
                order.get("signal_id"),
                order.get("symbol"),
                order.get("side"),
                order.get("order_type", "MARKET"),
                order.get("quantity"),
                order.get("fill_price"),
                order.get("fill_quantity"),
                order.get("commission"),
                order.get("slippage"),
                order.get("status", "filled"),
                order.get("execution_mode", "paper"),
                order.get("error_message"),
                now,
                now,
            )
            logger.debug("order_saved", order_id=order.get("id"))
        except Exception as e:
            logger.error("order_save_failed", order_id=order.get("id"), error=str(e))

    async def save_portfolio_snapshot(self, portfolio: Portfolio) -> None:
        sql = """
            INSERT INTO portfolio_snapshots (
                captured_at, capital_total, capital_available,
                unrealized_pnl, realized_pnl, daily_pnl, daily_pnl_pct,
                total_pnl_pct, max_drawdown_pct, open_positions,
                positions, base_currency
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """
        try:
            unrealized = sum(p.unrealized_pnl for p in portfolio.positions)
            positions_json = json.dumps([p.model_dump() for p in portfolio.positions], default=str)
            total_pnl_pct = (
                portfolio.total_pnl / (portfolio.total_capital - portfolio.total_pnl)
                if (portfolio.total_capital - portfolio.total_pnl) > 0 else 0.0
            )
            await get_pool().execute(
                sql,
                datetime.now(timezone.utc),
                portfolio.total_capital,
                portfolio.available_capital,
                unrealized,
                portfolio.total_pnl,
                portfolio.daily_pnl,
                portfolio.daily_pnl_pct,
                total_pnl_pct,
                portfolio.drawdown_max,
                len(portfolio.positions),
                positions_json,
                "USD",
            )
            logger.debug("portfolio_snapshot_saved", capital=portfolio.total_capital)
        except Exception as e:
            logger.error("portfolio_snapshot_failed", error=str(e))

    async def get_recent_signals(self, symbol: str, limit: int = 50) -> list[dict]:
        sql = """
            SELECT id, symbol, action, entry_price, confidence,
                   risk_reward_ratio, status, created_at, summary
            FROM signals
            WHERE symbol = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        try:
            rows = await get_pool().fetch(sql, symbol, limit)
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("get_signals_failed", symbol=symbol, error=str(e))
            return []

    async def get_recent_orders(self, symbol: str, limit: int = 50) -> list[dict]:
        sql = """
            SELECT id, symbol, side, quantity, fill_price,
                   commission, status, execution_mode, created_at
            FROM orders
            WHERE symbol = $1
            ORDER BY created_at DESC
            LIMIT $2
        """
        try:
            rows = await get_pool().fetch(sql, symbol, limit)
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error("get_orders_failed", symbol=symbol, error=str(e))
            return []

    async def save_backtest_result(
        self,
        strategy_id: str,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        metrics: dict,
    ) -> None:
        sql = """
            INSERT INTO backtest_results (
                strategy_id, symbol, timeframe, start_date, end_date,
                sharpe_ratio, sortino_ratio, max_drawdown_pct, win_rate,
                total_return_pct, total_trades, profit_factor, metrics,
                passed_quality_gate
            ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
        """
        try:
            passed = (
                metrics.get("sharpe", 0) >= 1.0
                and metrics.get("max_drawdown", 1) <= 0.20
                and metrics.get("win_rate", 0) >= 0.45
            )
            await get_pool().execute(
                sql,
                strategy_id, symbol, timeframe, start_date, end_date,
                metrics.get("sharpe"), metrics.get("sortino"),
                metrics.get("max_drawdown"), metrics.get("win_rate"),
                metrics.get("total_return"), metrics.get("total_trades"),
                metrics.get("profit_factor"),
                json.dumps(metrics),
                passed,
            )
            logger.info("backtest_result_saved", strategy_id=strategy_id, symbol=symbol,
                        passed=passed)
        except Exception as e:
            logger.error("backtest_result_save_failed", strategy_id=strategy_id, error=str(e))
