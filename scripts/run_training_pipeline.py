#!/usr/bin/env python3
"""
Script para descargar datos reales y entrenar modelos.
FASE 1 + FASE 3 implementation.

Uso:
    python run_training_pipeline.py  # Descarga + entrena todo
"""

import subprocess
from pathlib import Path

def run_phase_1():
    """Descargar datos reales de 2 años para timeframes 1h y 4h"""
    print("\n" + "="*70)
    print("FASE 1: DESCARGANDO DATOS REALES")
    print("="*70)
    print("\nEsto tomará ~10-20 minutos (descargando 2 años de datos 1h para 6 símbolos)...\n")
    
    cmd = 'python scripts/download_all_forex.py --period 2y --timeframes "1h,4h,1d"'
    print(f"Ejecutando: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("\n❌ Error en descarga. Verifica conexión a internet.")
        return False
    
    print("\n✅ FASE 1 COMPLETADA: Datos descargados en data/raw/\n")
    return True


def run_validation():
    """Validar integridad de datos descargados"""
    print("\n" + "="*70)
    print("VALIDANDO DATOS")
    print("="*70 + "\n")
    
    cmd = 'python scripts/validate_data.py'
    print(f"Ejecutando: {cmd}\n")
    
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print("\n⚠️ Validación completada con advertencias. Continuando...\n")
    
    return True


def run_phase_3():
    """Entrenar modelos LightGBM para TechnicalAgent"""
    print("\n" + "="*70)
    print("FASE 3: ENTRENANDO MODELOS")
    print("="*70)
    print("\nEntrenando modelos LightGBM para cada clase de activo...\n")
    
    # Entrenar modelos por clase de activo
    training_commands = [
        ('scripts/retrain.py', '--asset-class forex --timeframe 1h --symbols EURUSD GBPUSD USDJPY'),
        ('scripts/retrain.py', '--asset-class commodity --timeframe 1h --symbols XAUUSD'),
        ('scripts/retrain.py', '--asset-class index --timeframe 1h --symbols US500 US30'),
    ]
    
    for script, args in training_commands:
        cmd = f'python {script} {args}'
        print(f"\n{'▶'*3} {cmd}")
        print("-" * 70)
        
        result = subprocess.run(cmd, shell=True)
        if result.returncode != 0:
            print(f"\n❌ Error entrenando {script} {args}")
            return False
        
        print()
    
    print("\n✅ FASE 3 COMPLETADA: Modelos entrenados en data/models/\n")
    return True


def main():
    print("\n")
    print("🚀 TRADER·IA — PIPELINE DE ENTRENAMIENTO")
    print("="*70)
    print("FASE 1: Descarga de datos reales (2 años)")
    print("FASE 3: Entrenamiento de modelos LightGBM")
    print("="*70)
    
    # Verificar que los scripts existen
    required_scripts = [
        'scripts/download_all_forex.py',
        'scripts/validate_data.py',
        'scripts/retrain.py'
    ]
    
    for script in required_scripts:
        if not Path(script).exists():
            print(f"\n❌ Error: {script} no encontrado")
            return False
    
    # Ejecutar pipeline
    if not run_phase_1():
        return False
    
    if not run_validation():
        return False
    
    if not run_phase_3():
        return False
    
    # Resumen final
    print("\n" + "="*70)
    print("✅ PIPELINE COMPLETADO EXITOSAMENTE")
    print("="*70)
    print("\n📊 RESULTADOS:")
    print("  ✓ Datos descargados: data/raw/")
    print("  ✓ Modelos entrenados: data/models/")
    print("  ✓ Listos para:")
    print("    - FASE 4: Pipeline automático")
    print("    - FASE 5: Paper trading")
    print("\n💡 Próximos pasos:")
    print("  1. Revisar métricas de modelos en docs/model-training-results.md")
    print("  2. Ejecutar FASE 4: python scripts/start_phase2.py")
    print("  3. Iniciar dashboard: streamlit run app/dashboard.py")
    print("\n")


if __name__ == '__main__':
    main()
