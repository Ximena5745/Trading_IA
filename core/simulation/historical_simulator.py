"""
Module: core/simulation/historical_simulator.py
Responsibility: Interactive "what if" historical simulator
             — run any strategy on any date range with real costs
Dependencies: backtesting, feature_engineering, models, logger
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from core.backtesting.costs import CostModel
from core.backtesting.metrics import compute_all
from core.features.feature_engineering import FeatureEngine
from core.models import FeatureSet
from core.observability.logger import get_logger
from core.strategies.base_strategy import AbcStrategy

logger = get_logger(__name__)


class SimulationConfig:
    """Configuration for a historical simulation run."""

    def __init__(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
        initial_capital: float = 10_000.0,
        risk_per_trade_pct: float = 0.02,
        commission_pct: float = 0.001,
        slippage_pct: float = 0.0005,
        strategy_id: Optional[str] = None,
    ):
        self.symbol = symbol
        self.start = start
        self.end = end
        self.initial_capital = initial_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.commission_pct = commission_pct
        self.slippage_pct = slippage_pct
        self.strategy_id = strategy_id

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "initial_capital": self.initial_capital,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "commission_pct": self.commission_pct,
            "slippage_pct": self.slippage_pct,
            "strategy_id": self.strategy_id,
        }


class SimulationResult:
    """Output of a historical simulation."""

    def __init__(
        self,
        simulation_id: str,
        config: SimulationConfig,
        trades: list[dict],
        equity_curve: list[dict],
        metrics: dict,
        run_at: datetime,
    ):
        self.simulation_id = simulation_id
        self.config = config
        self.trades = trades
        self.equity_curve = equity_curve
        self.metrics = metrics
        self.run_at = run_at

    def to_dict(self) -> dict:
        return {
            "simulation_id": self.simulation_id,
            "config": self.config.to_dict(),
            "trades": self.trades,
            "equity_curve": self.equity_curve,
            "metrics": self.metrics,
            "run_at": self.run_at.isoformat(),
            "trade_count": len(self.trades),
        }


class HistoricalSimulator:
    """Runs a strategy against historical feature data and returns detailed results.

    Supports:
    - Custom date ranges
    - Custom commission and slippage (overrides defaults)
    - Equity curve generation (capital at each candle)
    - Full trade log with entry/exit prices
    - All standard backtest metrics
    """

    def __init__(self, cost_model: Optional[CostModel] = None):
        self._cost_model = cost_model or CostModel()
        self._results: dict[str, SimulationResult] = {}

    def run(
        self,
        strategy: AbcStrategy,
        features: list[FeatureSet],
        config: SimulationConfig,
    ) -> SimulationResult:
        """Run a full simulation and return a SimulationResult."""
        sim_id = str(uuid.uuid4())[:8]
        logger.info(
            "simulation_started",
            simulation_id=sim_id,
            symbol=config.symbol,
            strategy=strategy.strategy_id,
            candles=len(features),
            start=config.start.isoformat(),
            end=config.end.isoformat(),
        )

        # Filter features to date range
        in_range = [
            f for f in features
            if config.start <= f.timestamp <= config.end
        ]

        if len(in_range) < 50:
            logger.warning("simulation_insufficient_data", available=len(in_range))
            result = SimulationResult(
                simulation_id=sim_id,
                config=config,
                trades=[],
                equity_curve=[],
                metrics={"error": "insufficient_data", "candles": len(in_range)},
                run_at=datetime.utcnow(),
            )
            self._results[sim_id] = result
            return result

        # ── Simulation loop ────────────────────────────────────────────────
        capital = config.initial_capital
        equity_curve: list[dict] = []
        trades: list[dict] = []
        position: Optional[dict] = None

        for i, fs in enumerate(in_range):
            # Check exit first (if in position)
            if position:
                should_exit = strategy.should_exit(fs, position)
                if should_exit or i == len(in_range) - 1:
                    exit_price = fs.close
                    raw_pnl = (exit_price - position["entry_price"]) * position["size"]
                    if position["side"] == "SELL":
                        raw_pnl = -raw_pnl
                    net_pnl = self._cost_model.apply(
                        raw_pnl,
                        entry_price=position["entry_price"],
                        size=position["size"],
                    )
                    capital += net_pnl
                    trades.append({
                        "entry_ts": position["entry_ts"],
                        "exit_ts": fs.timestamp.isoformat(),
                        "symbol": config.symbol,
                        "side": position["side"],
                        "entry_price": position["entry_price"],
                        "exit_price": exit_price,
                        "size": position["size"],
                        "raw_pnl": round(raw_pnl, 4),
                        "net_pnl": round(net_pnl, 4),
                        "bars_held": i - position["bar_idx"],
                    })
                    position = None

            # Check entry (if flat)
            if not position:
                entry_signal = strategy.should_enter(fs)
                if entry_signal:
                    risk_amount = capital * config.risk_per_trade_pct
                    stop_dist = abs(fs.close - entry_signal.get("stop_loss", fs.close * 0.98))
                    size = (risk_amount / stop_dist) if stop_dist > 0 else 0.01
                    position = {
                        "side": entry_signal.get("direction", "BUY"),
                        "entry_price": fs.close,
                        "entry_ts": fs.timestamp.isoformat(),
                        "stop_loss": entry_signal.get("stop_loss", fs.close * 0.98),
                        "take_profit": entry_signal.get("take_profit", fs.close * 1.04),
                        "size": round(size, 6),
                        "bar_idx": i,
                    }

            equity_curve.append({
                "timestamp": fs.timestamp.isoformat(),
                "capital": round(capital, 2),
                "in_position": position is not None,
            })

        # ── Metrics ────────────────────────────────────────────────────────
        pnls = [t["net_pnl"] for t in trades]
        metrics = compute_all(pnls) if pnls else {k: 0.0 for k in [
            "sharpe_ratio", "sortino_ratio", "max_drawdown", "calmar_ratio",
            "win_rate", "profit_factor", "expectancy",
        ]}
        metrics["total_return_pct"] = round(
            (capital - config.initial_capital) / config.initial_capital * 100, 2
        )
        metrics["final_capital"] = round(capital, 2)
        metrics["total_trades"] = len(trades)

        result = SimulationResult(
            simulation_id=sim_id,
            config=config,
            trades=trades,
            equity_curve=equity_curve,
            metrics=metrics,
            run_at=datetime.utcnow(),
        )
        self._results[sim_id] = result

        logger.info(
            "simulation_completed",
            simulation_id=sim_id,
            trades=len(trades),
            total_return_pct=metrics["total_return_pct"],
            sharpe=round(metrics.get("sharpe_ratio", 0), 3),
        )
        return result

    def get_result(self, simulation_id: str) -> Optional[SimulationResult]:
        return self._results.get(simulation_id)

    def list_results(self, limit: int = 20) -> list[dict]:
        results = sorted(
            self._results.values(), key=lambda r: r.run_at, reverse=True
        )
        return [r.to_dict() for r in results[:limit]]
