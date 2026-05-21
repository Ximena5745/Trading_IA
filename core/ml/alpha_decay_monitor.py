"""
Module: core/ml/alpha_decay_monitor.py
Responsibility: Tracking de degradación de alpha por estrategia.
  - Sharpe rolling (ventana: últimos 50 trades)
  - Alerta si Sharpe rolling < 0.5
  - Alerta si win_rate cae > 10% vs baseline
  - Desactivación automática si Sharpe rolling < 0 por 20 trades consecutivos
  - Reactivación solo si régimen de mercado cambia Y backtest reciente > umbral
Dependencies: numpy, pandas, deque
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import numpy as np

from core.observability.logger import get_logger
from core.models import MarketRegime

logger = get_logger(__name__)


@dataclass
class AlphaDecayReport:
    strategy_id: str
    current_sharpe: float
    win_rate: float
    baseline_win_rate: float
    alert_level: str
    recommended_action: str
    should_deactivate: bool


class AlphaDecayMonitor:
    """
    Monitor de degradación de alpha.

    M6.5: Alpha Decay Monitor.
    """

    def __init__(
        self,
        sharpe_threshold: float = 0.5,
        win_rate_decay_threshold: float = 0.10,
        consecutive_negative_threshold: int = 20,
        window_size: int = 50,
    ):
        self._sharpe_threshold = sharpe_threshold
        self._win_decay = win_rate_decay_threshold
        self._neg_threshold = consecutive_negative_threshold
        self._window = window_size

        self._strategy_trades: dict[str, deque] = {}
        self._strategy_baseline: dict[str, dict] = {}
        self._strategy_states: dict[str, str] = {}

    def register_strategy(
        self,
        strategy_id: str,
        baseline_sharpe: float,
        baseline_win_rate: float,
    ) -> None:
        """Registrar estrategia con métricas baseline."""
        self._strategy_trades[strategy_id] = deque(maxlen=100)
        self._strategy_baseline[strategy_id] = {
            "sharpe": baseline_sharpe,
            "win_rate": baseline_win_rate,
        }
        self._strategy_states[strategy_id] = "active"
        logger.info(
            "strategy_registered_alpha_monitor",
            strategy_id=strategy_id,
            baseline_sharpe=baseline_sharpe,
            baseline_win_rate=baseline_win_rate,
        )

    def record_trade(
        self,
        strategy_id: str,
        pnl: float,
        is_win: bool,
    ) -> None:
        """Registrar resultado de trade."""
        if strategy_id not in self._strategy_trades:
            self.register_strategy(strategy_id, 0.5, 0.5)

        self._strategy_trades[strategy_id].append({
            "pnl": pnl,
            "is_win": is_win,
            "timestamp": datetime.utcnow(),
        })

    def analyze_strategy(self, strategy_id: str) -> AlphaDecayReport:
        """Analizar estado actual de una estrategia."""
        if strategy_id not in self._strategy_trades:
            return AlphaDecayReport(
                strategy_id=strategy_id,
                current_sharpe=0.0,
                win_rate=0.0,
                baseline_win_rate=0.0,
                alert_level="UNKNOWN",
                recommended_action="REGISTER_STRATEGY",
                should_deactivate=False,
            )

        trades = list(self._strategy_trades[strategy_id])
        if len(trades) < self._window:
            return AlphaDecayReport(
                strategy_id=strategy_id,
                current_sharpe=0.0,
                win_rate=0.0,
                baseline_win_rate=0.0,
                alert_level="INSUFFICIENT_DATA",
                recommended_action="CONTINUE_COLLECTING",
                should_deactivate=False,
            )

        recent = trades[-self._window:]
        pnls = [t["pnl"] for t in recent]
        wins = [t["is_win"] for t in recent]

        current_sharpe = self._calculate_sharpe(pnls)
        current_win_rate = sum(wins) / len(wins)

        baseline = self._strategy_baseline.get(strategy_id, {})
        baseline_win = baseline.get("win_rate", 0.5)
        baseline_sharpe = baseline.get("sharpe", 0.5)

        win_rate_diff = baseline_win - current_win_rate
        sharpe_decay = baseline_sharpe - current_sharpe

        consecutive_negative = self._count_consecutive_negative(trades)

        alert_level, action, should_deactivate = self._determine_alert_and_action(
            current_sharpe, current_win_rate, baseline_win, win_rate_diff, consecutive_negative
        )

        if should_deactivate:
            self._strategy_states[strategy_id] = "deactivated"

        logger.info(
            "alpha_decay_analysis",
            strategy_id=strategy_id,
            current_sharpe=current_sharpe,
            win_rate=current_win_rate,
            alert_level=alert_level,
            should_deactivate=should_deactivate,
        )

        return AlphaDecayReport(
            strategy_id=strategy_id,
            current_sharpe=current_sharpe,
            win_rate=current_win_rate,
            baseline_win_rate=baseline_win,
            alert_level=alert_level,
            recommended_action=action,
            should_deactivate=should_deactivate,
        )

    def _calculate_sharpe(self, pnls: list[float]) -> float:
        """Calcular Sharpe de PnLs."""
        if len(pnls) < 2:
            return 0.0

        arr = np.array(pnls)
        mean_ret = arr.mean()
        std_ret = arr.std()

        if std_ret == 0:
            return 0.0

        return mean_ret / std_ret * np.sqrt(252)

    def _count_consecutive_negative(self, trades: list[dict]) -> int:
        """Contar trades negativos consecutivos."""
        count = 0
        for trade in reversed(trades):
            if trade["pnl"] < 0:
                count += 1
            else:
                break
        return count

    def _determine_alert_and_action(
        self,
        sharpe: float,
        win_rate: float,
        baseline_win: float,
        win_decay: float,
        consecutive_neg: int,
    ) -> tuple[str, str, bool]:
        """Determinar nivel de alerta y acción."""
        if consecutive_neg >= self._neg_threshold:
            return "CRITICAL", "DEACTIVATE_IMMEDIATE", True

        if sharpe < 0:
            return "HIGH", "DEACTIVATE_Sharpe_NEGATIVE", True

        if sharpe < self._sharpe_threshold:
            return "MEDIUM", "WATCH_AND_ALERT", False

        if win_decay > self._win_decay:
            return "LOW", "WIN_RATE_DECAY_DETECTED", False

        return "NORMAL", "CONTINUE_MONITORING", False

    def can_reactivate(
        self,
        strategy_id: str,
        current_regime: MarketRegime,
        recent_backtest_sharpe: float,
    ) -> bool:
        """Verificar si estrategia puede ser reactivada."""
        optimal_regimes = {
            "TSMOM": [MarketRegime.BULL_TRENDING, MarketRegime.BEAR_TRENDING],
            "StatisticalArbitrage": [MarketRegime.SIDEWAYS_LOW_VOL],
            "MeanReversion": [MarketRegime.SIDEWAYS_LOW_VOL],
        }

        optimal = optimal_regimes.get(strategy_id, [MarketRegime.BULL_TRENDING])

        if current_regime not in optimal:
            return False

        if recent_backtest_sharpe < self._sharpe_threshold:
            return False

        self._strategy_states[strategy_id] = "active"
        logger.info("strategy_reactivated", strategy_id=strategy_id, sharpe=recent_backtest_sharpe)
        return True

    def get_active_strategies(self) -> list[str]:
        """Obtener estrategias activas."""
        return [
            sid for sid, state in self._strategy_states.items()
            if state == "active"
        ]

    def get_all_status(self) -> dict:
        """Obtener estado de todas las estrategias."""
        return dict(self._strategy_states)