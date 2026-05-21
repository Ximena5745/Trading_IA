"""
Module: core/ml/stress_testing.py
Responsibility: Engine de stress testing con escenarios históricos y sintéticos.
  Escenarios históricos:
    - COVID crash (Marzo 2020): BTC -50% en 2 días
    - Crypto winter (Nov 2022-Ene 2023): BTC -75% en 60 días
    - Flash crash genérico: -20% en 1 hora
    - EURUSD SNB (Enero 2015): 15% en 1 minuto
  Escenarios sintéticos (Monte Carlo):
    - t-distribution con df=3 (fat tails)
    - Volatility clustering (GARCH simulado)
    - Correlation breakdown
  Criterio aceptación: sistema sobrevive con DD < 25%
Dependencies: numpy, pandas, scipy
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StressTestResult:
    scenario_name: str
    max_drawdown: float
    min_equity: float
    survived: bool
    details: dict


class StressTestEngine:
    """
    Engine de stress testing.

    M6.4: Stress Testing Engine.
    """

    HISTORICAL_SCENARIOS = {
        "covid_crash": {
            "description": "COVID crash -50% en 2 días",
            "returns": [-0.25, -0.25],
            "duration_days": 2,
        },
        "crypto_winter": {
            "description": "Crypto winter 2022 -75% en 60 días",
            "returns": [np.random.uniform(-0.02, -0.03) for _ in range(60)],
            "duration_days": 60,
        },
        "flash_crash": {
            "description": "Flash crash -20% en 1 hora",
            "returns": [-0.20],
            "duration_hours": 1,
        },
        "snb_eurusd": {
            "description": "SNB EURUSD +15% en 1 minuto",
            "returns": [0.15],
            "duration_minutes": 1,
        },
    }

    def __init__(
        self,
        max_acceptable_dd: float = 0.25,
        initial_capital: float = 10000.0,
    ):
        self._max_dd = max_acceptable_dd
        self._initial_capital = initial_capital

    def run_historical_scenario(
        self,
        scenario_name: str,
        position_size: float = 0.1,
    ) -> StressTestResult:
        """Ejecutar escenario histórico."""
        if scenario_name not in self.HISTORICAL_SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario_name}")

        scenario = self.HISTORICAL_SCENARIOS[scenario_name]
        returns = scenario["returns"]

        equity = self._initial_capital
        equity_curve = [equity]

        for ret in returns:
            pnl = equity * position_size * ret
            equity += pnl
            equity_curve.append(equity)

        eq_arr = np.array(equity_curve)
        running_max = np.maximum.accumulate(eq_arr)
        drawdowns = (eq_arr - running_max) / running_max
        max_dd = abs(drawdowns.min())

        survived = max_dd < self._max_dd

        logger.info(
            "stress_test_result",
            scenario=scenario_name,
            max_dd=max_dd,
            survived=survived,
        )

        return StressTestResult(
            scenario_name=scenario_name,
            max_drawdown=max_dd,
            min_equity=eq_arr.min(),
            survived=survived,
            details={
                "description": scenario["description"],
                "final_equity": equity,
                "returns": returns,
            },
        )

    def run_monte_carlo(
        self,
        n_simulations: int = 1000,
        n_steps: int = 252,
        position_size: float = 0.1,
        distribution: str = "t_distribution",
    ) -> dict:
        """Ejecutar simulación Monte Carlo con diferentes distribuciones."""
        results = []

        for _ in range(n_simulations):
            if distribution == "t_distribution":
                returns = np.random.standard_t(df=3, size=n_steps) * 0.02
            elif distribution == "normal":
                returns = np.random.normal(0, 0.01, n_steps)
            elif distribution == "garch":
                returns = self._simulate_garch(n_steps)
            else:
                returns = np.random.normal(0, 0.01, n_steps)

            equity = self._initial_capital
            for ret in returns:
                pnl = equity * position_size * ret
                equity += pnl
            results.append(equity)

        results = np.array(results)
        dd_results = []

        for sim_results in [results]:
            eq_arr = np.array([self._initial_capital] + list(sim_results))
            running_max = np.maximum.accumulate(eq_arr)
            drawdowns = (eq_arr - running_max) / running_max
            dd_results.append(abs(drawdowns.min()))

        return {
            "n_simulations": n_simulations,
            "mean_final_equity": float(np.mean(results)),
            "median_final_equity": float(np.median(results)),
            "percentile_5": float(np.percentile(results, 5)),
            "max_drawdown_avg": float(np.mean(dd_results)),
            "max_drawdown_p99": float(np.percentile(dd_results, 99)),
            "survival_rate": float(np.mean(np.array(dd_results) < self._max_dd)),
        }

    def _simulate_garch(self, n_steps: int) -> np.ndarray:
        """Simular retornos con proceso GARCH(1,1)."""
        returns = np.zeros(n_steps)
        vol = 0.01

        for i in range(n_steps):
            vol = np.sqrt(0.01 + 0.1 * returns[max(0, i-1)]**2 + 0.8 * vol**2)
            returns[i] = np.random.normal(0, vol)

        return returns

    def run_correlation_breakdown(
        self,
        correlations: dict[str, float],
        position_size: float = 0.1,
    ) -> dict:
        """Simular breakdown de correlaciones entre activos."""
        base_equity = self._initial_capital

        for symbol, corr in correlations.items():
            if corr > 0.9:
                shock = np.random.uniform(-0.10, -0.05)
            else:
                shock = np.random.uniform(-0.03, 0.03)

            pnl = base_equity * position_size * shock
            base_equity += pnl

        final_equity = base_equity
        dd = (final_equity - self._initial_capital) / self._initial_capital

        return {
            "scenario": "correlation_breakdown",
            "final_equity": final_equity,
            "drawdown": abs(dd),
            "survived": abs(dd) < self._max_dd,
        }

    def run_all_scenarios(self, position_size: float = 0.1) -> dict:
        """Ejecutar todos los escenarios y resumir resultados."""
        results = {}

        for scenario_name in self.HISTORICAL_SCENARIOS:
            result = self.run_historical_scenario(scenario_name, position_size)
            results[scenario_name] = {
                "max_drawdown": result.max_drawdown,
                "survived": result.survived,
            }

        mc_result = self.run_monte_carlo(position_size=position_size)
        results["monte_carlo"] = {
            "survival_rate": mc_result["survival_rate"],
            "max_drawdown_avg": mc_result["max_drawdown_avg"],
        }

        survived_count = sum(1 for r in results.values() if r.get("survived", False))
        total_count = len([r for r in results.values() if "survived" in r])

        return {
            "results": results,
            "overall_survival_rate": survived_count / total_count if total_count > 0 else 0,
            "meets_criteria": survived_count / total_count >= 0.8,
        }