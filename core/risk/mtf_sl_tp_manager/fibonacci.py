"""
Module: core/risk/mtf_sl_tp_manager/fibonacci.py
Responsibility: Fibonacci retracement levels from a recent swing
Dependencies: pandas
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class FibonacciLevels:
    """Niveles de Fibonacci calculados desde un swing."""
    fib_0: float      # 0% - Origen
    fib_236: float    # 23.6%
    fib_382: float    # 38.2%
    fib_500: float    # 50%
    fib_618: float    # 61.8% - Golden ratio
    fib_786: float    # 78.6%
    fib_100: float    # 100% - Extensión

    def get_nearest_support(self, price: float, direction: str) -> float:
        """Obtiene el nivel de soporte más cercano por debajo del precio."""
        levels = [self.fib_0, self.fib_236, self.fib_382, self.fib_500,
                  self.fib_618, self.fib_786, self.fib_100]

        if direction == "BUY":
            # Para BUY, buscar soporte por debajo
            supports = [l for l in levels if l < price]
            return max(supports) if supports else self.fib_618
        else:
            # Para SELL, buscar resistencia por encima
            resistances = [l for l in levels if l > price]
            return min(resistances) if resistances else self.fib_382

    def get_nearest_resistance(self, price: float, direction: str) -> float:
        """Obtiene el nivel de resistencia más cercano por encima del precio."""
        levels = [self.fib_0, self.fib_236, self.fib_382, self.fib_500,
                  self.fib_618, self.fib_786, self.fib_100]

        if direction == "BUY":
            # Para BUY, buscar resistencia por encima
            resistances = [l for l in levels if l > price]
            return min(resistances) if resistances else self.fib_382
        else:
            # Para SELL, buscar soporte por debajo
            supports = [l for l in levels if l < price]
            return max(supports) if supports else self.fib_618


def calculate_fibonacci_levels(df: Optional[pd.DataFrame]) -> FibonacciLevels:
    """Calcula niveles de Fibonacci desde el swing más reciente."""
    if df is None or len(df) < 20:
        # Fallback: crear niveles simétricos alrededor del precio actual
        last_close = df['close'].iloc[-1] if df is not None else 100.0
        return FibonacciLevels(
            fib_0=last_close * 1.05,
            fib_236=last_close * 1.03,
            fib_382=last_close * 1.02,
            fib_500=last_close,
            fib_618=last_close * 0.98,
            fib_786=last_close * 0.97,
            fib_100=last_close * 0.95,
        )

    # Encontrar swing high/low recientes
    swing_high = df['high'].rolling(window=20).max().iloc[-1]
    swing_low = df['low'].rolling(window=20).min().iloc[-1]

    diff = swing_high - swing_low

    return FibonacciLevels(
        fib_0=swing_high,
        fib_236=swing_high - diff * 0.236,
        fib_382=swing_high - diff * 0.382,
        fib_500=swing_high - diff * 0.500,
        fib_618=swing_high - diff * 0.618,
        fib_786=swing_high - diff * 0.786,
        fib_100=swing_low,
    )
