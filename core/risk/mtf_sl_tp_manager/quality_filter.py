"""
Module: core/risk/mtf_sl_tp_manager/quality_filter.py
Responsibility: Signal quality gates (temporal alignment, Fibonacci zone,
  extreme volatility, minimum R:R) applied on top of an MTF SL/TP calculation
Dependencies: manager.py, fibonacci.py
"""
from __future__ import annotations

from typing import Any

from core.risk.mtf_sl_tp_manager.fibonacci import FibonacciLevels
from core.risk.mtf_sl_tp_manager.manager import MTFSLTPManager


class SignalQualityFilter:
    """
    Filtros de calidad de señal basados en análisis MTF.

    Implementa las reglas de filtrado de las propuestas de mejora:
    - Alineación de tendencias
    - Zona Fibonacci neutral
    - Volatilidad extrema
    - R:R mínimo
    """

    def __init__(self):
        self._mtf_manager = MTFSLTPManager()

    def check_temporal_alignment(
        self,
        trend_1h: int,
        trend_4h: int,
        trend_1d: int,
        direction: str,
    ) -> tuple[bool, str]:
        """
        Verifica alineación de tendencias entre timeframes.

        Args:
            trend_1h: +1 (alcista), -1 (bajista), 0 (neutral)
            trend_4h: +1 (alcista), -1 (bajista), 0 (neutral)
            trend_1d: +1 (alcista), -1 (bajista), 0 (neutral)
            direction: 'BUY' o 'SELL'

        Returns:
            (passed, reason)
        """
        signal_val = 1 if direction == "BUY" else -1

        # Regla dura: si D1 y H4 apuntan en dirección contraria, bloquear
        if signal_val > 0:  # BUY
            if trend_1d < 0 and trend_4h < 0:
                return False, "Señal BUY bloqueada: D1 y H4 bajistas"
            if trend_1d < 0 and trend_1h < 0:
                return False, "Señal BUY bloqueada: D1 y H1 bajistas"
        else:  # SELL
            if trend_1d > 0 and trend_4h > 0:
                return False, "Señal SELL bloqueada: D1 y H4 alcistas"
            if trend_1d > 0 and trend_1h > 0:
                return False, "Señal SELL bloqueada: D1 y H1 alcistas"

        # Regla suave: requiere mínimo 2 de 3 TF alineados
        aligned = sum([
            (trend_1h == signal_val),
            (trend_4h == signal_val),
            (trend_1d == signal_val),
        ])

        if aligned < 2:
            return False, f"Solo {aligned}/3 TF alineados (mínimo 2)"

        # Calcular score de alineación
        alignment_score = trend_1h + trend_4h + trend_1d
        if direction == "SELL":
            alignment_score = -alignment_score

        if alignment_score >= 3:
            return True, "Alineación perfecta (3/3)"
        elif alignment_score >= 2:
            return True, "Alineación fuerte (2/3)"
        else:
            return True, "Alineación débil pero aceptable"

    def check_fibonacci_zone(
        self,
        price: float,
        fib_levels: FibonacciLevels,
    ) -> tuple[bool, str]:
        """
        Verifica si el precio está en zona neutral de Fibonacci.
        Evita operar en 'no man's land' (45%-55% del rango).
        """
        swing_high = fib_levels.fib_0
        swing_low = fib_levels.fib_100

        if swing_high == swing_low:
            return True, "No se puede calcular zona"

        # Calcular posición en el rango (0-1)
        position = (price - swing_low) / (swing_high - swing_low)

        # Zona neutral: 45% - 55%
        if 0.45 <= position <= 0.55:
            return False, f"Precio en zona neutral ({position:.1%}) - No operar"

        # Identificar zona
        if position < 0.382:
            zone = "zona de sobreventa (< 38.2%)"
        elif position < 0.618:
            zone = "zona de tendencia (38.2% - 61.8%)"
        else:
            zone = "zona de sobrecompra (> 61.8%)"

        return True, f"Precio en {zone}"

    def check_volatility_extreme(
        self,
        atr_4h: float,
        atr_1h: float,
        threshold: float = 3.0,
    ) -> tuple[bool, str]:
        """
        Verifica si la volatilidad está en niveles extremos.
        Protege durante eventos macro de alto impacto.
        """
        if atr_1h <= 0:
            return True, "No se puede calcular volatilidad"

        ratio = atr_4h / atr_1h

        if ratio > threshold:
            return False, f"Volatilidad extrema (ratio {ratio:.2f} > {threshold})"
        elif ratio > 2.0:
            return True, f"Volatilidad elevada (ratio {ratio:.2f}) - Precaución"
        else:
            return True, f"Volatilidad normal (ratio {ratio:.2f})"

    def check_minimum_rr(
        self,
        rr_ratio: float,
        min_rr: float = 1.5,
    ) -> tuple[bool, str]:
        """Verifica si el R:R ratio cumple el mínimo requerido."""
        if rr_ratio < min_rr:
            return False, f"R:R insuficiente ({rr_ratio:.2f} < {min_rr})"
        return True, f"R:R aceptable ({rr_ratio:.2f})"

    def validate_signal(
        self,
        direction: str,
        entry_price: float,
        sl: float,
        tp: float,
        trend_1h: int,
        trend_4h: int,
        trend_1d: int,
        fib_levels: FibonacciLevels,
        atr_4h: float,
        atr_1h: float,
        min_rr: float = 1.5,
    ) -> dict[str, Any]:
        """
        Ejecuta todos los filtros de calidad de señal.

        Returns:
            Dict con resultado de cada filtro y decisión final
        """
        results = {
            "filters": {},
            "passed": True,
            "rejection_reasons": [],
        }

        # Filtro 1: Alineación temporal
        passed, reason = self.check_temporal_alignment(trend_1h, trend_4h, trend_1d, direction)
        results["filters"]["temporal_alignment"] = {"passed": passed, "reason": reason}
        if not passed:
            results["passed"] = False
            results["rejection_reasons"].append(reason)

        # Filtro 2: Zona Fibonacci
        passed, reason = self.check_fibonacci_zone(entry_price, fib_levels)
        results["filters"]["fibonacci_zone"] = {"passed": passed, "reason": reason}
        if not passed:
            results["passed"] = False
            results["rejection_reasons"].append(reason)

        # Filtro 3: Volatilidad extrema
        passed, reason = self.check_volatility_extreme(atr_4h, atr_1h)
        results["filters"]["volatility"] = {"passed": passed, "reason": reason}
        if not passed:
            results["passed"] = False
            results["rejection_reasons"].append(reason)

        # Filtro 4: R:R mínimo
        risk = abs(entry_price - sl)
        reward = abs(tp - entry_price)
        rr_ratio = reward / risk if risk > 0 else 0
        passed, reason = self.check_minimum_rr(rr_ratio, min_rr)
        results["filters"]["risk_reward"] = {"passed": passed, "reason": reason, "rr_ratio": rr_ratio}
        if not passed:
            results["passed"] = False
            results["rejection_reasons"].append(reason)

        return results


def create_signal_quality_filter() -> SignalQualityFilter:
    """Factory para crear el filtro de calidad de señal."""
    return SignalQualityFilter()
