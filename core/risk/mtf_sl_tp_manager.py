"""
Module: core/risk/mtf_sl_tp_manager.py
Responsibility: Dynamic Stop Loss and Take Profit calculation based on Multi-TimeFrame analysis
Dependencies: numpy, pandas, dataclasses

Sistema de SL/TP Dinámico Basado en MTF:
- Calcula SL/TP adaptativos combinando volatilidad multi-timeframe y niveles de Fibonacci
- Específico por tipo de activo (CRYPTO, FOREX, INDICES, COMMODITIES)
- Ajusta multiplicadores según timeframe de origen de la señal
- Incluye filtros de calidad de señal
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

import numpy as np
import pandas as pd

from core.models import AssetClass, detect_asset_class
from core.observability.logger import get_logger

logger = get_logger(__name__)


class Timeframe(str, Enum):
    """Timeframes soportados para análisis MTF."""
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


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


@dataclass
class ATRMultiTimeframe:
    """ATR calculado en múltiples timeframes."""
    atr_15m: float = 0.0
    atr_1h: float = 0.0
    atr_4h: float = 0.0
    atr_1d: float = 0.0
    
    @property
    def volatility_regime(self) -> str:
        """Determina el régimen de volatilidad basado en ratios."""
        if self.atr_4h > 0 and self.atr_1h > 0:
            ratio = self.atr_4h / self.atr_1h
            if ratio > 3.0:
                return "EXTREME"
            elif ratio > 2.0:
                return "HIGH"
            elif ratio > 1.5:
                return "ELEVATED"
            else:
                return "NORMAL"
        return "UNKNOWN"
    
    def get_atr_for_timeframe(self, tf: Timeframe) -> float:
        """Obtiene el ATR correspondiente al timeframe."""
        mapping = {
            Timeframe.M15: self.atr_15m,
            Timeframe.H1: self.atr_1h,
            Timeframe.H4: self.atr_4h,
            Timeframe.D1: self.atr_1d,
        }
        return mapping.get(tf, self.atr_1h)


@dataclass
class SLTPConfig:
    """Configuración de SL/TP para un activo y timeframe específico."""
    # Multiplicadores de ATR para SL y TP
    atr_sl_multiplier: float = 2.0
    atr_tp_multiplier: float = 3.0
    
    # Mínimo R:R ratio permitido
    min_rr_ratio: float = 1.5
    
    # Ajuste por régimen de volatilidad
    volatility_expansion_factor: float = 1.05  # Expandir SL 5% en volatilidad alta
    volatility_contraction_factor: float = 0.95  # Contraer SL 5% en volatilidad baja
    
    # Preferencia entre ATR y Fibonacci (0-1)
    # 0 = solo Fibonacci, 1 = solo ATR, 0.5 = promedio
    atr_fib_weight: float = 0.5
    
    # Límites máximos de SL como % del precio
    max_sl_pct: float = 0.02  # 2% por defecto
    
    def adjust_for_volatility_regime(self, regime: str) -> tuple[float, float]:
        """Ajusta multiplicadores según régimen de volatilidad."""
        if regime == "EXTREME":
            return self.atr_sl_multiplier * 1.2, self.atr_tp_multiplier * 1.1
        elif regime == "HIGH":
            return self.atr_sl_multiplier * self.volatility_expansion_factor, self.atr_tp_multiplier
        elif regime == "NORMAL":
            return self.atr_sl_multiplier, self.atr_tp_multiplier
        else:
            return self.atr_sl_multiplier * self.volatility_contraction_factor, self.atr_tp_multiplier * 0.9


# Configuraciones específicas por tipo de activo y timeframe
ASSET_SLTP_CONFIGS: dict[tuple[AssetClass, Timeframe], SLTPConfig] = {
    # CRYPTO - Alta volatilidad
    (AssetClass.CRYPTO, Timeframe.M15): SLTPConfig(
        atr_sl_multiplier=1.5, atr_tp_multiplier=2.5,
        min_rr_ratio=1.5, max_sl_pct=0.015,
        atr_fib_weight=0.7,  # Más peso a ATR en crypto corto plazo
    ),
    (AssetClass.CRYPTO, Timeframe.H1): SLTPConfig(
        atr_sl_multiplier=2.0, atr_tp_multiplier=3.5,
        min_rr_ratio=1.5, max_sl_pct=0.025,
        atr_fib_weight=0.6,
    ),
    (AssetClass.CRYPTO, Timeframe.H4): SLTPConfig(
        atr_sl_multiplier=2.5, atr_tp_multiplier=4.0,
        min_rr_ratio=1.5, max_sl_pct=0.035,
        atr_fib_weight=0.5,
    ),
    (AssetClass.CRYPTO, Timeframe.D1): SLTPConfig(
        atr_sl_multiplier=3.0, atr_tp_multiplier=5.0,
        min_rr_ratio=2.0, max_sl_pct=0.05,
        atr_fib_weight=0.4,  # Más peso a Fibonacci en largo plazo
    ),
    
    # FOREX - Volatilidad media, mean reversion
    (AssetClass.FOREX, Timeframe.M15): SLTPConfig(
        atr_sl_multiplier=1.5, atr_tp_multiplier=2.0,
        min_rr_ratio=1.5, max_sl_pct=0.008,
        atr_fib_weight=0.5,
    ),
    (AssetClass.FOREX, Timeframe.H1): SLTPConfig(
        atr_sl_multiplier=2.0, atr_tp_multiplier=3.0,
        min_rr_ratio=1.5, max_sl_pct=0.012,
        atr_fib_weight=0.5,
    ),
    (AssetClass.FOREX, Timeframe.H4): SLTPConfig(
        atr_sl_multiplier=2.5, atr_tp_multiplier=3.5,
        min_rr_ratio=1.5, max_sl_pct=0.018,
        atr_fib_weight=0.4,
    ),
    (AssetClass.FOREX, Timeframe.D1): SLTPConfig(
        atr_sl_multiplier=3.0, atr_tp_multiplier=4.5,
        min_rr_ratio=1.5, max_sl_pct=0.025,
        atr_fib_weight=0.3,
    ),
    
    # INDICES - Tendencias limpias
    (AssetClass.INDICES, Timeframe.M15): SLTPConfig(
        atr_sl_multiplier=1.5, atr_tp_multiplier=2.5,
        min_rr_ratio=1.5, max_sl_pct=0.008,
        atr_fib_weight=0.6,
    ),
    (AssetClass.INDICES, Timeframe.H1): SLTPConfig(
        atr_sl_multiplier=2.0, atr_tp_multiplier=3.5,
        min_rr_ratio=1.5, max_sl_pct=0.012,
        atr_fib_weight=0.5,
    ),
    (AssetClass.INDICES, Timeframe.H4): SLTPConfig(
        atr_sl_multiplier=2.5, atr_tp_multiplier=4.0,
        min_rr_ratio=1.5, max_sl_pct=0.018,
        atr_fib_weight=0.4,
    ),
    (AssetClass.INDICES, Timeframe.D1): SLTPConfig(
        atr_sl_multiplier=3.0, atr_tp_multiplier=5.0,
        min_rr_ratio=2.0, max_sl_pct=0.025,
        atr_fib_weight=0.3,
    ),
    
    # COMMODITIES (GOLD) - Macro driven
    (AssetClass.COMMODITIES, Timeframe.M15): SLTPConfig(
        atr_sl_multiplier=1.5, atr_tp_multiplier=2.0,
        min_rr_ratio=1.5, max_sl_pct=0.006,
        atr_fib_weight=0.5,
    ),
    (AssetClass.COMMODITIES, Timeframe.H1): SLTPConfig(
        atr_sl_multiplier=2.0, atr_tp_multiplier=3.0,
        min_rr_ratio=1.5, max_sl_pct=0.010,
        atr_fib_weight=0.4,
    ),
    (AssetClass.COMMODITIES, Timeframe.H4): SLTPConfig(
        atr_sl_multiplier=2.5, atr_tp_multiplier=3.5,
        min_rr_ratio=1.5, max_sl_pct=0.015,
        atr_fib_weight=0.3,
    ),
    (AssetClass.COMMODITIES, Timeframe.D1): SLTPConfig(
        atr_sl_multiplier=3.0, atr_tp_multiplier=4.0,
        min_rr_ratio=1.5, max_sl_pct=0.020,
        atr_fib_weight=0.25,
    ),
}


def get_sltp_config(asset_class: AssetClass, timeframe: Timeframe) -> SLTPConfig:
    """Obtiene la configuración de SL/TP para un activo y timeframe."""
    key = (asset_class, timeframe)
    if key in ASSET_SLTP_CONFIGS:
        return ASSET_SLTP_CONFIGS[key]
    
    # Fallback a config por defecto según clase de activo
    if asset_class == AssetClass.CRYPTO:
        return ASSET_SLTP_CONFIGS.get((AssetClass.CRYPTO, Timeframe.H1), SLTPConfig())
    elif asset_class == AssetClass.FOREX:
        return ASSET_SLTP_CONFIGS.get((AssetClass.FOREX, Timeframe.H1), SLTPConfig())
    elif asset_class == AssetClass.INDICES:
        return ASSET_SLTP_CONFIGS.get((AssetClass.INDICES, Timeframe.H1), SLTPConfig())
    else:
        return ASSET_SLTP_CONFIGS.get((AssetClass.COMMODITIES, Timeframe.H1), SLTPConfig())


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
            atr_mtf = self._calculate_atr_mtf(df_1h, df_4h, df_1d, df_15m)
            
            # Calcular niveles de Fibonacci desde swing en 1D
            fib_levels = self._calculate_fibonacci_levels(df_1d if df_1d is not None else df_1h)
            
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
    
    def _calculate_atr_mtf(
        self,
        df_1h: pd.DataFrame,
        df_4h: Optional[pd.DataFrame],
        df_1d: Optional[pd.DataFrame],
        df_15m: Optional[pd.DataFrame],
    ) -> ATRMultiTimeframe:
        """Calcula ATR en múltiples timeframes."""
        atr_1h = self._calculate_atr(df_1h, 14)
        atr_4h = self._calculate_atr(df_4h, 14) if df_4h is not None else atr_1h * 2
        atr_1d = self._calculate_atr(df_1d, 14) if df_1d is not None else atr_1h * 4
        atr_15m = self._calculate_atr(df_15m, 14) if df_15m is not None else atr_1h / 4
        
        return ATRMultiTimeframe(
            atr_15m=atr_15m,
            atr_1h=atr_1h,
            atr_4h=atr_4h,
            atr_1d=atr_1d,
        )
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calcula el ATR promedio."""
        if df is None or len(df) < period:
            return 0.0
        
        high = df['high']
        low = df['low']
        close = df['close']
        
        # True Range
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return float(atr) if not np.isnan(atr) else 0.0
    
    def _calculate_fibonacci_levels(self, df: pd.DataFrame) -> FibonacciLevels:
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


# Funciones de utilidad para integración
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


def create_signal_quality_filter() -> SignalQualityFilter:
    """Factory para crear el filtro de calidad de señal."""
    return SignalQualityFilter()


__all__ = [
    "MTFSLTPManager",
    "SignalQualityFilter",
    "SLTPResult",
    "SLTPConfig",
    "FibonacciLevels",
    "ATRMultiTimeframe",
    "Timeframe",
    "get_sltp_config",
    "calculate_trend_direction",
    "create_mtf_sltp_manager",
    "create_signal_quality_filter",
    "ASSET_SLTP_CONFIGS",
]
