"""
Module: core/risk/mtf_sl_tp_manager/config.py
Responsibility: SL/TP multiplier configuration per asset class and timeframe
Dependencies: core.models
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from core.models import AssetClass


class Timeframe(str, Enum):
    """Timeframes soportados para análisis MTF."""
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


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
