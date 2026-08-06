"""
Package: core/risk/mtf_sl_tp_manager
Responsibility: Dynamic Stop Loss and Take Profit calculation based on Multi-TimeFrame analysis

Sistema de SL/TP Dinámico Basado en MTF:
- Calcula SL/TP adaptativos combinando volatilidad multi-timeframe y niveles de Fibonacci
- Específico por tipo de activo (CRYPTO, FOREX, INDICES, COMMODITIES)
- Ajusta multiplicadores según timeframe de origen de la señal
- Incluye filtros de calidad de señal

Antes un único archivo de 810 líneas con 5+ responsabilidades (auditoría
técnica 2026-07-25, hallazgo de calidad SRP); dividido en submódulos:
  - config.py: Timeframe, SLTPConfig, tabla de multiplicadores por activo
  - fibonacci.py: niveles de retroceso de Fibonacci desde un swing
  - atr.py: ATR multi-timeframe y régimen de volatilidad
  - manager.py: MTFSLTPManager (orquestación) + SLTPResult
  - quality_filter.py: SignalQualityFilter (alineación temporal, zona Fib,
    volatilidad extrema, R:R mínimo)

El import path público `core.risk.mtf_sl_tp_manager` no cambia.
"""
from core.risk.mtf_sl_tp_manager.atr import ATRMultiTimeframe, calculate_atr_mtf
from core.risk.mtf_sl_tp_manager.config import (
    ASSET_SLTP_CONFIGS,
    SLTPConfig,
    Timeframe,
    get_sltp_config,
)
from core.risk.mtf_sl_tp_manager.fibonacci import FibonacciLevels, calculate_fibonacci_levels
from core.risk.mtf_sl_tp_manager.manager import (
    MTFSLTPManager,
    SLTPResult,
    calculate_trend_direction,
    create_mtf_sltp_manager,
)
from core.risk.mtf_sl_tp_manager.quality_filter import (
    SignalQualityFilter,
    create_signal_quality_filter,
)

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
    "calculate_atr_mtf",
    "calculate_fibonacci_levels",
]
