"""
Ejemplo de uso del Sistema de SL/TP Dinámico Basado en MTF

Este script muestra cómo usar el MTFSLTPManager para calcular
Stop Loss y Take Profit adaptativos basados en:
- Volatilidad multi-timeframe (ATR)
- Niveles técnicos de Fibonacci
- Configuración específica por activo y timeframe
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Importar el gestor de SL/TP MTF
from core.risk import (
    MTFSLTPManager,
    SignalQualityFilter,
    Timeframe,
    calculate_trend_direction,
    create_mtf_sltp_manager,
    create_signal_quality_filter,
)


def generate_sample_data(symbol: str, periods: int = 500) -> pd.DataFrame:
    """Genera datos de ejemplo para demostración."""
    np.random.seed(42)
    
    # Generar precios sintéticos con tendencia
    dates = pd.date_range(end=datetime.now(), periods=periods, freq='1h')
    
    # Tendencia alcista con ruido
    trend = np.linspace(100, 120, periods)
    noise = np.random.normal(0, 1, periods)
    close = trend + noise
    
    # Generar OHLC
    df = pd.DataFrame({
        'open': close - np.random.uniform(0.1, 0.5, periods),
        'high': close + np.random.uniform(0.2, 1.0, periods),
        'low': close - np.random.uniform(0.2, 1.0, periods),
        'close': close,
        'volume': np.random.uniform(1000, 5000, periods),
    }, index=dates)
    
    return df


def example_basic_usage():
    """Ejemplo básico de uso del MTF SL/TP Manager."""
    print("=" * 70)
    print("EJEMPLO 1: Uso Básico del MTF SL/TP Manager")
    print("=" * 70)
    
    # Crear gestor
    manager = create_mtf_sltp_manager()
    
    # Generar datos de ejemplo
    df_1h = generate_sample_data("EURUSD", 500)
    df_4h = df_1h.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_1d = df_1h.resample('1d').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Precio de entrada simulado
    entry_price = df_1h['close'].iloc[-1]
    
    # Calcular SL/TP para señal BUY en timeframe 1h
    result = manager.calculate_sl_tp(
        entry_price=entry_price,
        direction="BUY",
        symbol="EURUSD",
        signal_timeframe=Timeframe.H1,
        df_1h=df_1h,
        df_4h=df_4h,
        df_1d=df_1d,
    )
    
    print(f"\nSímbolo: EURUSD")
    print(f"Dirección: BUY")
    print(f"Precio de Entrada: {result.entry_price:.5f}")
    print(f"Stop Loss: {result.stop_loss:.5f}")
    print(f"Take Profit: {result.take_profit:.5f}")
    print(f"R:R Ratio: {result.rr_ratio:.2f}")
    print(f"Riesgo: {result.risk_pct:.2%}")
    print(f"Régimen de Volatilidad: {result.volatility_regime}")
    print(f"ATR 1h: {result.atr_1h:.5f}")
    print(f"ATR 4h: {result.atr_4h:.5f}")
    print(f"ATR 1d: {result.atr_1d:.5f}")
    print(f"SL Source: {result.sl_source}")
    print(f"TP Source: {result.tp_source}")
    print(f"Nivel Fib SL: {result.fib_level_sl}")
    print(f"Nivel Fib TP: {result.fib_level_tp}")
    print(f"Válido: {result.is_valid}")
    if result.rejection_reason:
        print(f"Razón de rechazo: {result.rejection_reason}")


def example_crypto_configuration():
    """Ejemplo de configuración específica para CRYPTO."""
    print("\n" + "=" * 70)
    print("EJEMPLO 2: Configuración Específica para CRYPTO (BTCUSD)")
    print("=" * 70)
    
    manager = create_mtf_sltp_manager()
    
    # Generar datos de crypto (más volátiles)
    np.random.seed(123)
    dates = pd.date_range(end=datetime.now(), periods=500, freq='1h')
    
    # Crypto con mayor volatilidad
    trend = np.linspace(40000, 45000, 500)
    noise = np.random.normal(0, 500, 500)
    close = trend + noise
    
    df_1h = pd.DataFrame({
        'open': close - np.random.uniform(50, 200, 500),
        'high': close + np.random.uniform(100, 500, 500),
        'low': close - np.random.uniform(100, 500, 500),
        'close': close,
        'volume': np.random.uniform(100, 1000, 500),
    }, index=dates)
    
    df_4h = df_1h.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    df_1d = df_1h.resample('1d').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    entry_price = df_1h['close'].iloc[-1]
    
    # Comparar diferentes timeframes
    for tf in [Timeframe.H1, Timeframe.H4, Timeframe.D1]:
        result = manager.calculate_sl_tp(
            entry_price=entry_price,
            direction="BUY",
            symbol="BTCUSD",
            signal_timeframe=tf,
            df_1h=df_1h,
            df_4h=df_4h,
            df_1d=df_1d,
        )
        
        print(f"\n--- Timeframe: {tf.value} ---")
        print(f"  SL: {result.stop_loss:.2f}")
        print(f"  TP: {result.take_profit:.2f}")
        print(f"  R:R: {result.rr_ratio:.2f}")
        print(f"  Riesgo: {result.risk_pct:.2%}")


def example_signal_quality_filters():
    """Ejemplo de filtros de calidad de señal."""
    print("\n" + "=" * 70)
    print("EJEMPLO 3: Filtros de Calidad de Señal")
    print("=" * 70)
    
    filter_mgr = create_signal_quality_filter()
    
    # Ejemplo 1: Alineación perfecta
    print("\n--- Caso 1: Alineación Perfecta ---")
    passed, reason = filter_mgr.check_temporal_alignment(
        trend_1h=1, trend_4h=1, trend_1d=1, direction="BUY"
    )
    print(f"Dirección: BUY, Trends: H1=+, H4=+, D1=+")
    print(f"Resultado: {'✓ PASA' if passed else '✗ BLOQUEADA'} - {reason}")
    
    # Ejemplo 2: Conflicto temporal
    print("\n--- Caso 2: Conflicto Temporal ---")
    passed, reason = filter_mgr.check_temporal_alignment(
        trend_1h=1, trend_4h=-1, trend_1d=-1, direction="BUY"
    )
    print(f"Dirección: BUY, Trends: H1=+, H4=-, D1=-")
    print(f"Resultado: {'✓ PASA' if passed else '✗ BLOQUEADA'} - {reason}")
    
    # Ejemplo 3: Alineación parcial
    print("\n--- Caso 3: Alineación Parcial ---")
    passed, reason = filter_mgr.check_temporal_alignment(
        trend_1h=1, trend_4h=1, trend_1d=-1, direction="BUY"
    )
    print(f"Dirección: BUY, Trends: H1=+, H4=+, D1=-")
    print(f"Resultado: {'✓ PASA' if passed else '✗ BLOQUEADA'} - {reason}")
    
    # Ejemplo 4: Volatilidad extrema
    print("\n--- Caso 4: Volatilidad Extrema ---")
    passed, reason = filter_mgr.check_volatility_extreme(
        atr_4h=0.015, atr_1h=0.004, threshold=3.0
    )
    print(f"ATR 4h: 0.015, ATR 1h: 0.004, Ratio: {0.015/0.004:.2f}")
    print(f"Resultado: {'✓ PASA' if passed else '✗ BLOQUEADA'} - {reason}")
    
    # Ejemplo 5: R:R insuficiente
    print("\n--- Caso 5: R:R Insuficiente ---")
    passed, reason = filter_mgr.check_minimum_rr(rr_ratio=1.2, min_rr=1.5)
    print(f"R:R: 1.2, Mínimo requerido: 1.5")
    print(f"Resultado: {'✓ PASA' if passed else '✗ BLOQUEADA'} - {reason}")


def example_complete_workflow():
    """Ejemplo de flujo completo con validación de señal."""
    print("\n" + "=" * 70)
    print("EJEMPLO 4: Flujo Completo con Validación de Señal")
    print("=" * 70)
    
    # Crear managers
    sltp_mgr = create_mtf_sltp_manager()
    filter_mgr = create_signal_quality_filter()
    
    # Generar datos
    df_1h = generate_sample_data("EURUSD", 500)
    df_4h = df_1h.resample('4h').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    df_1d = df_1h.resample('1d').agg({
        'open': 'first',
        'high': 'max',
        'low': 'min',
        'close': 'last',
        'volume': 'sum'
    }).dropna()
    
    # Calcular tendencias
    trend_1h = calculate_trend_direction(df_1h, 9, 21)
    trend_4h = calculate_trend_direction(df_4h, 9, 21)
    trend_1d = calculate_trend_direction(df_1d, 50, 200)
    
    entry_price = df_1h['close'].iloc[-1]
    direction = "BUY"
    
    print(f"\n--- Análisis de Señal ---")
    print(f"Símbolo: EURUSD")
    print(f"Dirección: {direction}")
    print(f"Precio de Entrada: {entry_price:.5f}")
    print(f"Tendencia H1: {'Alcista' if trend_1h > 0 else 'Bajista' if trend_1h < 0 else 'Neutral'}")
    print(f"Tendencia H4: {'Alcista' if trend_4h > 0 else 'Bajista' if trend_4h < 0 else 'Neutral'}")
    print(f"Tendencia D1: {'Alcista' if trend_1d > 0 else 'Bajista' if trend_1d < 0 else 'Neutral'}")
    
    # Calcular SL/TP
    sltp_result = sltp_mgr.calculate_sl_tp(
        entry_price=entry_price,
        direction=direction,
        symbol="EURUSD",
        signal_timeframe=Timeframe.H1,
        df_1h=df_1h,
        df_4h=df_4h,
        df_1d=df_1d,
    )
    
    print(f"\n--- Cálculo SL/TP ---")
    print(f"Stop Loss: {sltp_result.stop_loss:.5f}")
    print(f"Take Profit: {sltp_result.take_profit:.5f}")
    print(f"R:R Ratio: {sltp_result.rr_ratio:.2f}")
    print(f"Régimen de Volatilidad: {sltp_result.volatility_regime}")
    
    # Validar señal con todos los filtros
    from core.risk.mtf_sl_tp_manager import FibonacciLevels
    
    # Crear niveles de Fibonacci para validación
    fib = FibonacciLevels(
        fib_0=entry_price * 1.05,
        fib_236=entry_price * 1.03,
        fib_382=entry_price * 1.02,
        fib_500=entry_price,
        fib_618=entry_price * 0.98,
        fib_786=entry_price * 0.97,
        fib_100=entry_price * 0.95,
    )
    
    validation = filter_mgr.validate_signal(
        direction=direction,
        entry_price=entry_price,
        sl=sltp_result.stop_loss,
        tp=sltp_result.take_profit,
        trend_1h=trend_1h,
        trend_4h=trend_4h,
        trend_1d=trend_1d,
        fib_levels=fib,
        atr_4h=sltp_result.atr_4h,
        atr_1h=sltp_result.atr_1h,
        min_rr=1.5,
    )
    
    print(f"\n--- Validación de Señal ---")
    for filter_name, result in validation["filters"].items():
        status = "✓" if result["passed"] else "✗"
        print(f"{status} {filter_name}: {result['reason']}")
    
    print(f"\n--- Decisión Final ---")
    if validation["passed"]:
        print("✓ SEÑAL APROBADA - Ejecutar operación")
    else:
        print("✗ SEÑAL RECHAZADA")
        for reason in validation["rejection_reasons"]:
            print(f"  - {reason}")


def example_comparison_assets():
    """Compara configuraciones entre diferentes activos."""
    print("\n" + "=" * 70)
    print("EJEMPLO 5: Comparación de Configuraciones por Activo")
    print("=" * 70)
    
    from core.risk import get_sltp_config
    from core.models import AssetClass
    
    assets = [
        ("BTCUSD", AssetClass.CRYPTO),
        ("EURUSD", AssetClass.FOREX),
        ("US500", AssetClass.INDICES),
        ("XAUUSD", AssetClass.COMMODITIES),
    ]
    
    timeframes = [Timeframe.H1, Timeframe.H4, Timeframe.D1]
    
    print(f"\n{'Activo':<10} {'TF':<5} {'SL Mult':<8} {'TP Mult':<8} {'Min R:R':<8} {'Max SL%':<8} {'ATR/Fib':<8}")
    print("-" * 70)
    
    for symbol, asset_class in assets:
        for tf in timeframes:
            config = get_sltp_config(asset_class, tf)
            print(f"{symbol:<10} {tf.value:<5} {config.atr_sl_multiplier:<8.1f} "
                  f"{config.atr_tp_multiplier:<8.1f} {config.min_rr_ratio:<8.1f} "
                  f"{config.max_sl_pct:<8.2%} {config.atr_fib_weight:<8.1f}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("SISTEMA DE SL/TP DINÁMICO BASADO EN MTF - DEMOSTRACIÓN")
    print("=" * 70)
    
    # Ejecutar todos los ejemplos
    example_basic_usage()
    example_crypto_configuration()
    example_signal_quality_filters()
    example_complete_workflow()
    example_comparison_assets()
    
    print("\n" + "=" * 70)
    print("DEMOSTRACIÓN COMPLETADA")
    print("=" * 70)
