"""
Module: core/strategies/strategy_rotation.py
Responsibility: Desactiva estrategias con Sharpe rolling < 0.5 y reactiva según régimen.
  - Desactivar si Sharpe rolling (30 trades) < 0.5
  - Reactivar cuando el régimen de mercado es óptimo para esa estrategia
  - Registro en audit log de cada activación/desactivación
Dependencies: logger
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime

from core.models import MarketRegime
from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StrategyState:
    status: str
    sharpe_rolling: float
    last_activation: datetime
    regime_at_activation: MarketRegime


class StrategyRotationEngine:
    """
    Motor de rotación de estrategias basado en performance.

    M4.3: Strategy Rotation Engine.
    """

    def __init__(
        self,
        min_sharpe_rolling: float = 0.5,
        min_trades_for_eval: int = 30,
    ):
        self._min_sharpe = min_sharpe_rolling
        self._min_trades = min_trades_for_eval
        self._strategy_trades: dict[str, deque] = {}
        self._strategy_states: dict[str, StrategyState] = {}

    def record_trade(self, strategy_id: str, pnl: float) -> None:
        """Registrar resultado de trade para una estrategia."""
        if strategy_id not in self._strategy_trades:
            self._strategy_trades[strategy_id] = deque(maxlen=100)
        self._strategy_trades[strategy_id].append(pnl)

    def check_rotation(
        self, strategy_id: str, current_regime: MarketRegime
    ) -> tuple[bool, str]:
        """
        Verificar si una estrategia debe ser activada/desactivada.
        Retorna (should_change, reason).
        """
        if strategy_id not in self._strategy_trades:
            return True, "NEW_STRATEGY"

        trades = list(self._strategy_trades[strategy_id])
        if len(trades) < self._min_trades:
            return False, "INSUFFICIENT_TRADES"

        recent_pnls = trades[-self._min_trades:]
        sharpe = self._calculate_sharpe(recent_pnls)

        current_state = self._strategy_states.get(strategy_id)
        is_active = current_state.status == "active" if current_state else False

        if is_active and sharpe < self._min_sharpe:
            self._strategy_states[strategy_id] = StrategyState(
                status="inactive",
                sharpe_rolling=sharpe,
                last_activation=datetime.utcnow(),
                regime_at_activation=current_regime,
            )
            logger.warning(
                "strategy_deactivated_poor_performance",
                strategy_id=strategy_id,
                sharpe=sharpe,
                threshold=self._min_sharpe,
            )
            return True, f"DEACTIVATED: Sharpe {sharpe:.2f} < {self._min_sharpe}"

        if not is_active and sharpe >= self._min_sharpe:
            optimal_regimes = self._get_optimal_regimes(strategy_id)
            if current_regime in optimal_regimes:
                self._strategy_states[strategy_id] = StrategyState(
                    status="active",
                    sharpe_rolling=sharpe,
                    last_activation=datetime.utcnow(),
                    regime_at_activation=current_regime,
                )
                logger.info(
                    "strategy_activated",
                    strategy_id=strategy_id,
                    sharpe=sharpe,
                    regime=current_regime.value,
                )
                return True, f"ACTIVATED: Sharpe {sharpe:.2f} >= {self._min_sharpe}"

        return False, "NO_CHANGE"

    def _calculate_sharpe(self, pnl_list: list[float]) -> float:
        """Calculate Sharpe ratio from P&L list."""
        if not pnl_list or len(pnl_list) < 2:
            return 0.0
        arr = list(pnl_list)
        mean_pnl = sum(arr) / len(arr)
        std_pnl = (sum((x - mean_pnl) ** 2 for x in arr) / len(arr)) ** 0.5
        if std_pnl == 0:
            return 0.0
        return mean_pnl / std_pnl

    def _get_optimal_regimes(self, strategy_id: str) -> set[MarketRegime]:
        """Obtener regímenes óptimos para cada estrategia."""
        regime_map = {
            "TSMOM": {MarketRegime.BULL_TRENDING, MarketRegime.BEAR_TRENDING},
            "StatisticalArbitrage": {MarketRegime.SIDEWAYS_LOW_VOL, MarketRegime.SIDEWAYS_HIGH_VOL},
            "MeanReversion": {MarketRegime.SIDEWAYS_LOW_VOL},
            "Breakout": {MarketRegime.SIDEWAYS_HIGH_VOL, MarketRegime.BULL_TRENDING},
        }
        return regime_map.get(strategy_id, {MarketRegime.BULL_TRENDING, MarketRegime.BEAR_TRENDING})

    def get_active_strategies(self) -> list[str]:
        """Obtener lista de estrategias actualmente activas."""
        return [
            sid for sid, state in self._strategy_states.items()
            if state.status == "active"
        ]