"""
Module: core/monitoring/performance_tracker.py
Responsibility: Real-time P&L tracking per strategy
Dependencies: models, logger
"""

from __future__ import annotations

from datetime import datetime

from core.observability.logger import get_logger

logger = get_logger(__name__)


class PerformanceTracker:
    def __init__(self):
        self._trades: dict[str, list[dict]] = {}  # strategy_id → trades
        self._snapshots: list[dict] = []

    def record_trade(self, strategy_id: str, trade: dict) -> None:
        if strategy_id not in self._trades:
            self._trades[strategy_id] = []
        self._trades[strategy_id].append(
            {**trade, "recorded_at": datetime.utcnow().isoformat()}
        )
        logger.info(
            "trade_recorded",
            strategy_id=strategy_id,
            net_pnl=trade.get("net_pnl"),
            symbol=trade.get("symbol"),
        )

    def get_strategy_metrics(self, strategy_id: str) -> dict:
        trades = self._trades.get(strategy_id, [])
        if not trades:
            return {"strategy_id": strategy_id, "total_trades": 0}
        pnls = [t.get("net_pnl", 0) for t in trades]
        wins = [p for p in pnls if p > 0]
        return {
            "strategy_id": strategy_id,
            "total_trades": len(trades),
            "total_pnl": round(sum(pnls), 4),
            "win_rate": round(len(wins) / len(pnls), 4),
            "avg_pnl": round(sum(pnls) / len(pnls), 4),
            "best_trade": round(max(pnls), 4),
            "worst_trade": round(min(pnls), 4),
        }

    def get_all_metrics(self) -> list[dict]:
        return [self.get_strategy_metrics(sid) for sid in self._trades]

    def take_snapshot(self, portfolio: dict) -> None:
        self._snapshots.append(
            {
                "timestamp": datetime.utcnow().isoformat(),
                "total_capital": portfolio.get("total_capital"),
                "daily_pnl_pct": portfolio.get("daily_pnl_pct"),
                "drawdown_current": portfolio.get("drawdown_current"),
            }
        )

    def get_snapshots(self, limit: int = 100) -> list[dict]:
        return self._snapshots[-limit:]
