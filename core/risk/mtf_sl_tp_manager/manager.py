"""
Module: core/risk/mtf_sl_tp_manager/manager.py
Responsibility: Orchestrate ATR + Fibonacci + per-asset config into a final SL/TP decision
Dependencies: pandas, atr.py, fibonacci.py, config.py
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from core.models import detect_asset_class
from core.observability.logger import get_logger
from core.risk.mtf_sl_tp_manager.atr import ATRMultiTimeframe, calculate_atr_mtf
from core.risk.mtf_sl_tp_manager.config import Timeframe, get_sltp_config
from core.risk.mtf_sl_tp_manager.fibonacci import FibonacciLevels, calculate_fibonacci_levels

logger = get_logger(__name__)


@dataclass
class SLTPResult:
    """Resultado del cálculo de SL/TP."""
    entry_price: float
    stop_loss: float
    take_profit: float
    direction: str
    rr_ratio: float
    risk_pct: float

    # Metadatos del cálculo
    sl_source: str  # 'atr', 'fibonacci', 'mixed'
    tp_source: str
    atr_used: float
    fib_level_sl: Optional[str]
    fib_level_tp: Optional[str]

    # Información de volatilidad
    volatility_regime: str
    atr_1h: float
    atr_4h: float
    atr_1d: float

    # Validación
    is_valid: bool
    rejection_reason: Optional[str] = None


class MTFSLTPManager:
    """
    Gestor de Stop Loss y Take Profit basado en Multi-TimeFrame.

    Combina:
    - ATR multi-timeframe para volatilidad adaptativa
    - Niveles de Fibonacci para soportes/resistencias técnicos
    - Configuración específica por activo y timeframe
    - Filtros de calidad de señal
    """

    def __init__(self):
        self._cache_fib: dict[str, FibonacciLevels] = {}
        self._cache_atr: dict[str, ATRMultiTimeframe] = {}

    def calculate_sl_tp(
        self,
        entry_price: float,
        direction: str,
        symbol: str,
        signal_timeframe: Timeframe,
        df_1h: pd.DataFrame,
        df_4h: Optional[pd.DataFrame] = None,
        df_1d: Optional[pd.DataFrame] = None,
        df_15m: Optional[pd.DataFrame] = None,
    ) -> SLTPResult:
        """
        Calcula SL y TP dinámicos basados en MTF.

        Args:
            entry_price: Precio de entrada
            direction: 'BUY' o 'SELL'
            symbol: Símbolo del activo
            signal_timeframe: Timeframe que originó la señal
            df_1h: DataFrame de 1h con OHLCV
            df_4h: DataFrame de 4h (opcional)
            df_1d: DataFrame diario (opcional)
            df_15m: DataFrame de 15m (opcional)

        Returns:
            SLTPResult con SL, TP y metadatos
        """
        try:
            # Detectar clase de activo
            asset_class = detect_asset_class(symbol)

            # Obtener configuración
            config = get_sltp_config(asset_class, signal_timeframe)

            # Calcular ATR multi-timeframe
            atr_mtf = calculate_atr_mtf(df_1h, df_4h, df_1d, df_15m)

            # Calcular niveles de Fibonacci desde swing en 1D
            fib_levels = calculate_fibonacci_levels(df_1d if df_1d is not None else df_1h)

            # Ajustar multiplicadores por régimen de volatilidad
            sl_mult, tp_mult = config.adjust_for_volatility_regime(atr_mtf.volatility_regime)

            # Calcular SL basado en ATR
            atr_for_tf = atr_mtf.get_atr_for_timeframe(signal_timeframe)
            sl_atr_distance = atr_for_tf * sl_mult

            # Calcular SL basado en Fibonacci
            if direction == "BUY":
                sl_fib = fib_levels.get_nearest_support(entry_price, direction)
                sl_atr = entry_price - sl_atr_distance
                # Tomar el más conservador (más lejano) entre ATR y Fibonacci
                sl_candidates = [sl_atr, sl_fib]
                sl_final = min(sl_candidates) if direction == "BUY" else max(sl_candidates)
                sl_source = self._determine_sl_source(sl_atr, sl_fib, sl_final, config.atr_fib_weight)

                # Calcular TP
                tp_fib = fib_levels.get_nearest_resistance(entry_price, direction)
                min_tp_distance = abs(entry_price - sl_final) * config.min_rr_ratio
                tp_atr = entry_price + (atr_for_tf * tp_mult)
                tp_min_rr = entry_price + min_tp_distance

                # Tomar el más cercano que cumpla con R:R mínimo
                tp_candidates = [tp_fib, tp_atr]
                tp_valid = [tp for tp in tp_candidates if tp - entry_price >= min_tp_distance]
                tp_final = min(tp_valid) if tp_valid else max(tp_candidates)
                tp_source = self._determine_tp_source(tp_atr, tp_fib, tp_final)

            else:  # SELL
                sl_fib = fib_levels.get_nearest_resistance(entry_price, direction)
                sl_atr = entry_price + sl_atr_distance
                sl_candidates = [sl_atr, sl_fib]
                sl_final = max(sl_candidates)
                sl_source = self._determine_sl_source(sl_atr, sl_fib, sl_final, config.atr_fib_weight)

                # Calcular TP
                tp_fib = fib_levels.get_nearest_support(entry_price, direction)
                min_tp_distance = abs(entry_price - sl_final) * config.min_rr_ratio
                tp_atr = entry_price - (atr_for_tf * tp_mult)
                tp_min_rr = entry_price - min_tp_distance

                tp_candidates = [tp_fib, tp_atr]
                tp_valid = [tp for tp in tp_candidates if entry_price - tp >= min_tp_distance]
                tp_final = max(tp_valid) if tp_valid else min(tp_candidates)
                tp_source = self._determine_tp_source(tp_atr, tp_fib, tp_final)

            # Calcular métricas
            risk = abs(entry_price - sl_final)
            reward = abs(tp_final - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0.0
            risk_pct = risk / entry_price if entry_price > 0 else 0.0

            # Validar límites
            is_valid = True
            rejection_reason = None

            if risk_pct > config.max_sl_pct:
                is_valid = False
                rejection_reason = f"SL too large: {risk_pct:.2%} > {config.max_sl_pct:.2%}"
            elif rr_ratio < config.min_rr_ratio:
                is_valid = False
                rejection_reason = f"R:R too low: {rr_ratio:.2f} < {config.min_rr_ratio}"

            # Identificar niveles Fibonacci usados
            fib_level_sl = self._identify_fib_level(sl_final, fib_levels)
            fib_level_tp = self._identify_fib_level(tp_final, fib_levels)

            logger.info(
                "sltp_calculated",
                symbol=symbol,
                direction=direction,
                entry=entry_price,
                sl=sl_final,
                tp=tp_final,
                rr=round(rr_ratio, 2),
                regime=atr_mtf.volatility_regime,
            )

            return SLTPResult(
                entry_price=entry_price,
                stop_loss=sl_final,
                take_profit=tp_final,
                direction=direction,
                rr_ratio=rr_ratio,
                risk_pct=risk_pct,
                sl_source=sl_source,
                tp_source=tp_source,
                atr_used=atr_for_tf,
                fib_level_sl=fib_level_sl,
                fib_level_tp=fib_level_tp,
                volatility_regime=atr_mtf.volatility_regime,
                atr_1h=atr_mtf.atr_1h,
                atr_4h=atr_mtf.atr_4h,
                atr_1d=atr_mtf.atr_1d,
                is_valid=is_valid,
                rejection_reason=rejection_reason,
            )

        except Exception as e:
            logger.error("sltp_calculation_failed", symbol=symbol, error=str(e))
            return SLTPResult(
                entry_price=entry_price,
                stop_loss=entry_price * 0.98 if direction == "BUY" else entry_price * 1.02,
                take_profit=entry_price * 1.03 if direction == "BUY" else entry_price * 0.97,
                direction=direction,
                rr_ratio=1.5,
                risk_pct=0.02,
                sl_source="error_fallback",
                tp_source="error_fallback",
                atr_used=0.0,
                fib_level_sl=None,
                fib_level_tp=None,
                volatility_regime="UNKNOWN",
                atr_1h=0.0,
                atr_4h=0.0,
                atr_1d=0.0,
                is_valid=False,
                rejection_reason=f"Calculation error: {str(e)}",
            )

    def _determine_sl_source(self, sl_atr: float, sl_fib: float, sl_final: float, weight: float) -> str:
        """Determina si el SL final viene de ATR, Fibonacci o mixto."""
        diff_atr = abs(sl_final - sl_atr)
        diff_fib = abs(sl_final - sl_fib)

        if diff_atr < diff_fib * 0.1:
            return "atr"
        elif diff_fib < diff_atr * 0.1:
            return "fibonacci"
        else:
            return "mixed"

    def _determine_tp_source(self, tp_atr: float, tp_fib: float, tp_final: float) -> str:
        """Determina si el TP final viene de ATR o Fibonacci."""
        diff_atr = abs(tp_final - tp_atr)
        diff_fib = abs(tp_final - tp_fib)

        if diff_atr < diff_fib * 0.1:
            return "atr"
        elif diff_fib < diff_atr * 0.1:
            return "fibonacci"
        else:
            return "mixed"

    def _identify_fib_level(self, price: float, fib: FibonacciLevels) -> Optional[str]:
        """Identifica qué nivel de Fibonacci corresponde al precio."""
        levels = {
            "0%": fib.fib_0,
            "23.6%": fib.fib_236,
            "38.2%": fib.fib_382,
            "50%": fib.fib_500,
            "61.8%": fib.fib_618,
            "78.6%": fib.fib_786,
            "100%": fib.fib_100,
        }

        # Encontrar el nivel más cercano
        closest = min(levels.items(), key=lambda x: abs(x[1] - price))

        # Solo retornar si está suficientemente cerca (1% de tolerancia)
        if abs(closest[1] - price) / price < 0.01:
            return closest[0]
        return None


def calculate_trend_direction(df: pd.DataFrame, fast_ema: int = 9, slow_ema: int = 21) -> int:
    """
    Calcula la dirección de la tendencia basada en EMAs.

    Returns:
        +1: Alcista (fast > slow)
        -1: Bajista (fast < slow)
        0: Neutral
    """
    if len(df) < slow_ema:
        return 0

    ema_fast = df['close'].ewm(span=fast_ema, adjust=False).mean().iloc[-1]
    ema_slow = df['close'].ewm(span=slow_ema, adjust=False).mean().iloc[-1]

    if ema_fast > ema_slow:
        return 1
    elif ema_fast < ema_slow:
        return -1
    return 0


def create_mtf_sltp_manager() -> MTFSLTPManager:
    """Factory para crear el gestor de SL/TP MTF."""
    return MTFSLTPManager()
