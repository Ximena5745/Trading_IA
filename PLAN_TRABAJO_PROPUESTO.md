# TRADER IA — Plan de Trabajo Propuesto v4.0

> **Versión:** 4.0.0 | **Fecha:** Marzo 2026 | **Horizonte:** 12 semanas
> 
> **Enfoque:** Entorno de pruebas → Descarga datos reales → Pruebas de modelos → Producción

---

## Tabla de Contenidos

1. [Análisis del Plan Anterior](#1-análisis-del-plan-anterior)
2. [Nueva Estrategia por Fases](#2-nueva-estrategia-por-fases)
3. [FASE 0 — Entorno de Desarrollo Local](#3-fase-0--entorno-de-desarrollo-local)
4. [FASE 1 — Descarga de Datos Reales](#4-fase-1--descarga-de-datos-reales)
5. [FASE 2 — Entrenamiento de Modelos](#5-fase-2--entrenamiento-de-modelos)
6. [FASE 3 — Pipeline Automático Funcional](#6-fase-3--pipeline-automático-funcional)
7. [FASE 4 — Validación Paper Trading](#7-fase-4--validación-paper-trading)
8. [FASE 5 — Mejoras y Optimización](#8-fase-5--mejoras-y-optimización)
9. [FASE 6 — Producción Controlada](#9-fase-6--producción-controlada)
10. [Checklist Maestro](#10-checklist-maestro)

---

## 1. Análisis del Plan Anterior

### Problemas Identificados

| Problema | Impacto | Propuesta |
|----------|---------|-----------|
| Plan muy ambicioso (16 semanas) | Se pierde momentum | Reducir a 12 semanas |
| Fase 0 muy teórica | No genera avances tangibles | Enfoque práctico inmediato |
| RL y Meta-aprendizaje muy pronto | El sistema no tiene datos suficientes | Mover a Fase 6+ |
| UI antes que funcionalidad | Prioridades invertidas | UI al final |
| Falta énfasis en datos reales | Sin datos = sin modelos | Fase 1 dedicada a datos |

### Ventajas del Nuevo Plan

1. **Enfoque incremental:** Cada fase produce algo útil y testeable
2. **Datos primero:** Sin datos reales no hay ML real
3. **Entorno de pruebas:** Prioridad #1 para iterar rápidamente
4. **Realista:** Considera el estado actual del código (completo pero sin datos)

---

## 2. Nueva Estrategia por Fases

### Mapa Visual

```
SEMANA →    1     2     3     4     5     6     7     8     9    10    11    12
            │     │     │     │     │     │     │     │     │     │     │     │
FASE 0      ██████│     │     │     │     │     │     │     │     │     │     │
            Entorno│    │     │     │     │     │     │     │     │     │     │
            Local  │    │     │     │     │     │     │     │     │     │     │
                   │    │     │     │     │     │     │     │     │     │     │
FASE 1            │██████│██████│    │     │     │     │     │     │     │     │
                  │Descarga│Datos│   │     │     │     │     │     │     │     │
                  │Binance │ MT5 │   │     │     │     │     │     │     │     │
                  │        │     │   │     │     │     │     │     │     │     │
FASE 2                  │██████│██████│    │     │     │     │     │     │     │
                        │Train │Modelos│   │     │     │     │     │     │     │
                        │LightGBM │ML │   │     │     │     │     │     │     │
                              │     │   │     │     │     │     │     │     │
FASE 3                        │██████│██████│██████│    │     │     │     │     │
                              │Pipeline│Auto-│Valid│    │     │     │     │     │
                              │  mático │mático│ación│   │     │     │     │     │
                                       │     │    │     │     │     │     │
FASE 4                                    │██████│██████│    │     │     │     │
                                          │Paper │Trading│   │     │     │     │
                                          │2-4 sem│    │   │     │     │     │
                                                    │    │   │     │     │
FASE 5                                              │██████│██████│    │     │
                                                    │Mejoras│Optim│    │     │
                                                    │      │     │   │     │
FASE 6                                                        │██████│██████│██████
                                                              │Staging│Prod │Live│
                                                                    │     │    │
            ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
            ←────────────── DATOS REALES EN TODAS LAS FASES ──────────────────→
            │     │     │     │     │     │     │     │     │     │     │     │
```

### Resumen por Fase

| Fase | Duración | Objetivo Principal | Entregable |
|------|----------|-------------------|------------|
| **FASE 0** | 3-4 días | Entorno funcional | Docker + DB + API corriendo |
| **FASE 1** | 2 semanas | Datos reales históricos | 2 años de OHLCV por símbolo |
| **FASE 2** | 1 semana | Modelos entrenados | .pkl files con LightGBM |
| **FASE 3** | 2 semanas | Pipeline automático | Scheduler ejecutando 12 símbolos |
| **FASE 4** | 2-4 semanas | Validación | Métricas paper trading reales |
| **FASE 5** | 2 semanas | Optimización | Pesos dinámicos, mejoras |
| **FASE 6** | 2 semanas | Producción | Staging → Live controlado |

---

## 3. FASE 0 — Entorno de Desarrollo Local

**Duración:** 3-4 días  
**Objetivo:** Tener el sistema corriendo localmente con datos de prueba  
**Branch:** `feature/dev-env`

### 3.1 Problema Actual

El proyecto tiene todo el código pero:
- No hay datos reales en `data/`
- No hay modelos entrenados en `data/models/`
- La base de datos no está configurada
- El pipeline no puede ejecutarse end-to-end

### 3.2 Tareas

#### Día 1: Configuración base

- [ ] Verificar que Docker Desktop está instalado y corriendo
- [ ] Ejecutar `docker-compose up -d db redis` para levantar servicios
- [ ] Crear `.env` desde `.env.example` con valores mínimos
- [ ] Verificar conectividad: `docker-compose exec db psql -U trader -d trader_ai -c "SELECT 1"`
- [ ] Ejecutar schema SQL: `docker exec -i trader_db psql -U trader -d trader_ai < scripts/migrations/001_initial_schema.sql`

```bash
# Comandos rápidos
docker-compose up -d db redis
sleep 5
docker-compose exec db psql -U trader -c "CREATE DATABASE trader_ai;"
docker exec -i trader_db psql -U trader -d trader_ai < scripts/migrations/001_initial_schema.sql
```

#### Día 2: API y Dashboard

- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Iniciar API: `uvicorn api.main:app --reload --port 8000`
- [ ] Verificar health: `curl http://localhost:8000/health`
- [ ] Iniciar Dashboard: `streamlit run app/dashboard.py --server.port 8501`
- [ ] Verificar que ambas interfaces cargan sin errores

#### Día 3: Test del sistema completo

- [ ] Ejecutar tests unitarios: `pytest tests/unit/ -v`
- [ ] Ejecutar tests de integración: `pytest tests/integration/ -v`
- [ ] Probar un pipeline manual con datos mock:
  ```bash
  python scripts/run_pipeline.py --once BTCUSDT
  ```
- [ ] Verificar logs y identificar errores conocidos

#### Día 4: Fix de errores críticos

- [ ] Resolver cualquier error de importación
- [ ] Verificar que FeatureEngine calcula indicadores correctamente
- [ ] Verificar que TechnicalAgent hace fallback a rule-based sin modelo
- [ ] Documentar cualquier bloqueante en `PLAN_BLOQUEANTES.md`

### 3.3 Deliverables

```
✅ docker-compose.yml funcionando (db + redis)
✅ .env configurado para desarrollo
✅ API corriendo en :8000
✅ Dashboard corriendo en :8501
✅ Tests pasando (unit + integration)
✅ Pipeline manual ejecutable
✅ Lista de errores conocidos documentados
```

---

## 4. FASE 1 — Descarga de Datos Reales

**Duración:** 2 semanas  
**Objetivo:** Obtener 2+ años de datos OHLCV para todos los símbolos  
**Branch:** `feature/data-download`

### 4.1 ¿Por qué es prioridad?

Los modelos LightGBM necesitan datos históricos para entrenar. Sin datos:
- Los agentes operan en mode rule-based (menor precisión)
- No se puede validar backtesting con datos reales
- No se puede entrenar ningún modelo ML

### 4.2 Datos a Descargar

| Símbolo | Clase | Exchange | Período | Timeframes |
|---------|-------|----------|---------|------------|
| BTCUSDT | Crypto | Binance | 2 años | 1h, 4h |
| ETHUSDT | Crypto | Binance | 2 años | 1h, 4h |
| EURUSD | Forex | MT5/OANDA | 2 años | 1h |
| GBPUSD | Forex | MT5/OANDA | 2 años | 1h |
| USDJPY | Forex | MT5/OANDA | 2 años | 1h |
| XAUUSD | Commodities | MT5 | 2 años | 1h |
| US500 | Indices | MT5 | 2 años | 1h |
| US30 | Indices | MT5 | 2 años | 1h |

### 4.3 Scripts a Crear

#### Script principal: `scripts/download_data.py`

```python
"""
Script para descargar datos históricos de Binance y MT5.

Uso:
    python scripts/download_data.py --symbol BTCUSDT --exchange binance --years 2
    python scripts/download_data.py --symbol EURUSD --exchange mt5 --years 2
    python scripts/download_data.py --all --years 2
"""
```

**Funcionalidades requeridas:**

```python
# 1. Descarga desde Binance (gratuito, sin API key para klines públicos)
def download_binance(symbol: str, timeframe: str, years: int) -> pd.DataFrame:
    """
    Usa API pública de Binance:
    GET /api/v3/klines?symbol={symbol}&interval={timeframe}&limit=1000
    
    Paginación: descargar en chunks de 1000 velas
    Guardar en data/raw/{symbol}_{timeframe}.parquet
    """

# 2. Descarga desde OANDA (gratuito para datos históricos)
def download_oanda(symbol: str, timeframe: str, years: int) -> pd.DataFrame:
    """
    Usa OANDA API (requiere cuenta demo gratuita):
    GET /v3/instruments/{instrument}/candles
    
    O alternativa: usar datos de Alpha Vantage (gratuito)
    """

# 3. Alternativa: Yahoo Finance (gratis, sin API key)
def download_yfinance(symbol: str, timeframe: str, years: int) -> pd.DataFrame:
    """
    Usa yfinance library:
    yf.download(symbol, period="2y", interval="1h")
    
    Limitaciones: sin datos tick-level, pero suficiente para entrenamiento
    """
```

#### Dependencias necesarias

```txt
# requirements-data.txt
yfinance>=0.2.31
pandas>=2.0.0
pyarrow>=14.0.0  # Para parquet
tqdm>=4.65.0     # Barra de progreso
```

### 4.4 Implementación Día a Día

#### Semana 1: Crypto (Binance)

**Día 1-2: Script de descarga Binance**

- [ ] Crear `scripts/download_data.py` con función `download_binance()`
- [ ] Implementar paginación (1000 velas por request, 2 años ≈ 17520 velas 1h)
- [ ] Descargar BTCUSDT 1h y 4h
- [ ] Descargar ETHUSDT 1h y 4h
- [ ] Guardar en `data/raw/btcusdt_1h.parquet`, etc.
- [ ] Verificar integridad de datos (sin gaps, timestamps secuenciales)

**Día 3: Validación de datos**

- [ ] Crear script `scripts/validate_data.py` para verificar:
  ```python
  def validate_ohlcv(df: pd.DataFrame) -> dict:
      return {
          "total_candles": len(df),
          "date_range": (df['timestamp'].min(), df['timestamp'].max()),
          "missing_timestamps": count_gaps(df),
          "nan_count": df.isna().sum().to_dict(),
          "ohlc_consistency": validate_ohlc(df),  # high >= open,close; low <= open,close
      }
  ```
- [ ] Ejecutar validación en todos los archivos descargados
- [ ] Corregir cualquier problema de datos

**Día 4-5: Feature Engineering test**

- [ ] Probar `FeatureEngine.calculate()` en datos reales descargados
- [ ] Verificar que todos los 17 indicadores se calculan sin errores
- [ ] Guardar features calculados en `data/processed/`
- [ ] Documentar cualquier issue de cálculo

#### Semana 2: Forex/Indices (MT5 o alternativa)

**Día 1-3: Datos Forex**

Opción A (MT5 disponible):
- [ ] Configurar credenciales MT5 en `.env`
- [ ] Usar `MT5Client` existente para descargar datos
- [ ] Descargar EURUSD, GBPUSD, USDJPY (1h, 2 años)

Opción B (Sin MT5 - usar alternativas):
```python
# Opción B1: OANDA API (cuenta demo gratuita)
# Opción B2: Yahoo Finance (gratuito)
# Opción B3: Alpha Vantage (gratuito con API key)
```

- [ ] Implementar `download_oanda()` o `download_yfinance()` para Forex
- [ ] Descargar EURUSD, GBPUSD, USDJPY (1h, 2 años)
- [ ] Guardar en `data/raw/eurusd_1h.parquet`, etc.

**Día 4-5: Commodities e Indices**

- [ ] Descargar XAUUSD (Gold) - OANDA o Yahoo Finance
- [ ] Descargar US500, US30 - Yahoo Finance (SPY, DIA como proxy)
- [ ] Validar todos los datos
- [ ] Probar FeatureEngine en datos Forex

### 4.5 Estructura de Datos Final

```
data/
├── raw/                          # Datos OHLCV crudos
│   ├── btcusdt_1h.parquet        # ~17,520 velas (2 años)
│   ├── btcusdt_4h.parquet        # ~4,380 velas
│   ├── ethusdt_1h.parquet
│   ├── ethusdt_4h.parquet
│   ├── eurusd_1h.parquet
│   ├── gbpusd_1h.parquet
│   ├── usdjpy_1h.parquet
│   ├── xauusd_1h.parquet
│   ├── us500_1h.parquet
│   └── us30_1h.parquet
│
├── processed/                    # Features calculados
│   ├── btcusdt_features_1h.parquet
│   ├── ethusdt_features_1h.parquet
│   └── ...
│
├── splits/                       # Train/Test splits para ML
│   ├── btcusdt_train.parquet     # Primeros 80%
│   └── btcusdt_test.parquet      # Últimos 20%
│
└── models/                       # Modelos entrenados (Fase 2)
    └── (vacío por ahora)
```

### 4.6 Deliverables FASE 1

```
✅ scripts/download_data.py funcional
✅ 8+ símbolos descargados (2 años cada uno)
✅ Validación de datos pasando para todos
✅ FeatureEngine funcionando en datos reales
✅ data/raw/ con archivos .parquet
✅ data/processed/ con features calculados
✅ Documentación de fuentes de datos usadas
```

---

## 5. FASE 2 — Entrenamiento de Modelos

**Duración:** 1 semana  
**Objetivo:** Entrenar LightGBM para TechnicalAgent con datos reales  
**Branch:** `feature/model-training`

### 5.1 Modelos a Entrenar

| Modelo | Datos | Target | Output |
|--------|-------|--------|--------|
| `technical_crypto_v1.pkl` | BTC + ETH features | Signo retorno siguiente vela | Score -1 a +1 |
| `technical_forex_v1.pkl` | EUR, GBP, JPY features | Signo retorno siguiente vela | Score -1 a +1 |
| `technical_commodities_v1.pkl` | XAU features | Signo retorno siguiente vela | Score -1 a +1 |

### 5.2 Script de Entrenamiento

#### `scripts/train_models.py`

```python
"""
Entrena modelos LightGBM para TechnicalAgent.

Uso:
    python scripts/train_models.py --asset crypto --symbols BTCUSDT ETHUSDT
    python scripts/train_models.py --asset forex --symbols EURUSD GBPUSD USDJPY
    python scripts/train_models.py --all
"""

import lightgbm as lgb
import shap
import pickle
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

def prepare_training_data(features_df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """
    Prepara datos para entrenamiento:
    1. Features: todas las columnas de indicadores
    2. Target: signo del retorno de la siguiente vela
    
    X = features[:-1]  # Todas las velas excepto la última
    y = sign(close[1:] / close[:-1] - 1)  # +1 si subió, -1 si bajó
    """
    feature_cols = [
        "rsi_14", "rsi_7", "macd_line", "macd_signal", "macd_histogram",
        "ema_9", "ema_21", "ema_50", "ema_200", "atr_14",
        "bb_upper", "bb_lower", "bb_width", "vwap", "volume_ratio", "obv"
    ]
    
    X = features_df[feature_cols].values[:-1]
    y_returns = (features_df["close"].pct_change().shift(-1)[:-1])
    y = (y_returns > 0).astype(int)  # 1 = subió, 0 = bajó
    
    return X, y

def train_lightgbm(X: np.ndarray, y: np.ndarray) -> lgb.LGBMClassifier:
    """
    Entrena LightGBM con validación walk-forward.
    """
    model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        max_depth=7,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        n_jobs=-1,
        verbose=-1
    )
    
    # Walk-forward validation (5 splits)
    tscv = TimeSeriesSplit(n_splits=5)
    scores = []
    
    for train_idx, val_idx in tscv.split(X):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        
        model.fit(X_train, y_train)
        y_pred = model.predict(X_val)
        scores.append(f1_score(y_val, y_pred))
    
    # Entrenar en todos los datos
    model.fit(X, y)
    
    return model, scores

def create_shap_explainer(model: lgb.LGBMClassifier) -> shap.TreeExplainer:
    """
    Crea explainer SHAP para el modelo entrenado.
    """
    return shap.TreeExplainer(model)

def save_model(model, explainer, path: str):
    """
    Guarda modelo + explainer en archivo .pkl
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump({"model": model, "explainer": explainer}, f)
    print(f"Model saved to {path}")
```

### 5.3 Implementación Día a Día

#### Día 1: Script base y entrenamiento Crypto

- [ ] Crear `scripts/train_models.py` con estructura completa
- [ ] Cargar datos de `data/raw/btcusdt_1h.parquet`
- [ ] Calcular features con `FeatureEngine`
- [ ] Preparar datos de entrenamiento (X, y)
- [ ] Entrenar LightGBM con validación walk-forward
- [ ] Evaluar métricas: accuracy, F1, precision, recall
- [ ] Crear SHAP explainer
- [ ] Guardar en `data/models/technical_crypto_v1.pkl`

#### Día 2: Entrenamiento Forex y Commodities

- [ ] Entrenar modelo Forex (EURUSD + GBPUSD + USDJPY combinados)
- [ ] Entrenar modelo Commodities (XAUUSD)
- [ ] Guardar en `data/models/technical_forex_v1.pkl` y `technical_commodities_v1.pkl`
- [ ] Comparar métricas entre modelos (Crypto vs Forex)

#### Día 3: Evaluación y ajustes

- [ ] Analizar feature importance con SHAP
- [ ] Identificar features más predictivos por asset class
- [ ] Ajustar hiperparámetros si F1 < 0.55
- [ ] Documentar resultados en `docs/model-training-results.md`

#### Día 4: Integración con TechnicalAgent

- [ ] Verificar que `TechnicalAgent._load_model()` carga los .pkl
- [ ] Probar predicción con modelo real vs rule-based
- [ ] Comparar outputs (score, confidence, shap_values)
- [ ] Test end-to-end: datos → features → modelo → predicción

#### Día 5: Tests y validación

- [ ] Crear tests unitarios para entrenamiento
- [ ] Test: modelo produce outputs en rango correcto (-1 a +1)
- [ ] Test: SHAP explainer funciona correctamente
- [ ] Test: modelo保存y carga correctamente
- [ ] Documentar pipeline de reentrenamiento

### 5.4 Métricas Objetivo

| Métrica | Mínimo | Objetivo | Crypto | Forex |
|---------|--------|----------|--------|-------|
| Accuracy | 52% | 58% | ? | ? |
| F1 Score | 0.52 | 0.58 | ? | ? |
| Precision | 52% | 58% | ? | ? |
| Sharpe (backtest) | 1.0 | 1.5 | ? | ? |

### 5.5 Deliverables FASE 2

```
✅ scripts/train_models.py funcional
✅ technical_crypto_v1.pkl entrenado (BTC + ETH)
✅ technical_forex_v1.pkl entrenado (EUR, GBP, JPY)
✅ technical_commodities_v1.pkl entrenado (XAU)
✅ Métricas de evaluación documentadas
✅ Feature importance analizado con SHAP
✅ TechnicalAgent cargando modelos correctamente
✅ Tests de integración pasando
```

---

## 6. FASE 3 — Pipeline Automático Funcional

**Duración:** 2 semanas  
**Objetivo:** Pipeline ejecutándose automáticamente cada hora  
**Branch:** `feature/pipeline-functional`

### 6.1 Lo que falta para pipeline funcional

| Componente | Estado Actual | Necesita |
|------------|---------------|----------|
| run_pipeline.py | Código existe | Conectar con DB, scheduler real |
| APScheduler | Código existe | Verificar integración |
| PostgreSQL | docker-compose | Schema inicializado con datos |
| Redis | docker-compose | FeatureStore conectado |
| FundamentalAgent | Código existe | Datos ForexFactory/CoinGecko |

### 6.2 Implementación Semana 1

#### Día 1-2: Configuración del scheduler

- [ ] Verificar APScheduler está instalado: `pip show apscheduler`
- [ ] Modificar `scripts/run_pipeline.py` para usar configuración real
- [ ] Crear función `_build_components()` que conecte todo
- [ ] Probar un ciclo manual con datos reales:
  ```bash
  python scripts/run_pipeline.py --once BTCUSDT
  ```
- [ ] Verificar que el ciclo completa sin errores

#### Día 3-4: Integración con base de datos

- [ ] Verificar conexión PostgreSQL en `core/db/session.py`
- [ ] Crear tablas necesarias si no existen
- [ ] Implementar `TradingRepository` para guardar señales/órdenes
- [ ] Implementar `FeatureStore` con Redis
- [ ] Probar persistencia de datos end-to-end

#### Día 5: Testing completo

- [ ] Ejecutar pipeline para BTCUSDT (ciclo completo)
- [ ] Verificar que se genera señal (o se registra por qué no)
- [ ] Verificar que se guarda en PostgreSQL
- [ ] Verificar que features se cachean en Redis
- [ ] Revisar logs para errores

### 6.3 Implementación Semana 2

#### Día 1-2: Scheduler multi-símbolo

- [ ] Configurar schedule para 12 símbolos (staggered)
- [ ] Probar que scheduler ejecuta múltiples jobs
- [ ] Implementar manejo de errores (no crash si un símbolo falla)
- [ ] Verificar que cada job independiente funciona

```python
SCHEDULE = [
    ("BTCUSDT", 0),    # :00
    ("ETHUSDT", 5),    # :05
    ("EURUSD", 10),    # :10
    # ... etc
]
```

#### Día 3-4: FundamentalAgent - Eventos macro

- [ ] Integrar ForexFactory calendar (web scraping o API)
- [ ] Implementar `is_blocked_by_event()` funcional
- [ ] Verificar que bloquea Forex durante NFP, FOMC, etc.
- [ ] No bloquear Crypto por eventos macro

#### Día 5: Monitoreo básico

- [ ] Agregar métricas Prometheus básicas (cycles, signals, errors)
- [ ] Verificar que endpoint `/metrics` funciona
- [ ] Crear health check que verifique DB + Redis + Exchange

### 6.4 Deliverables FASE 3

```
✅ Pipeline ejecutándose cada hora (APScheduler)
✅ 12 símbolos programados con stagger
✅ FundametalAgent con calendario de eventos macro
✅ Persistencia funcionando (PostgreSQL + Redis)
✅ Métricas Prometheus habilitadas
✅ Logs estructurados con información útil
✅ Manejo de errores (un fallo no detiene todo)
✅ Documentación de troubleshooting
```

---

## 7. FASE 4 — Validación Paper Trading

**Duración:** 2-4 semanas  
**Objetivo:** Recolectar datos reales de trading simulado  
**Branch:** `feature/paper-validation`

### 7.1 ¿Por qué 2-4 semanas?

Para validar cualquier estrategia necesitamos:
- Mínimo 100 operaciones para estadísticas significativas
- Múltiples ciclos de mercado (días de alta/baja volatilidad)
- Al menos 1 evento macro importante para probar filtros

### 7.2 Métricas a Recolectar

#### Métricas diarias

```python
daily_metrics = {
    "date": "2026-04-01",
    "total_signals": 15,
    "buy_signals": 8,
    "sell_signals": 7,
    "executed_trades": 12,
    "winning_trades": 7,
    "losing_trades": 5,
    "daily_pnl": 245.50,
    "daily_pnl_pct": 0.024,
    "equity": 10245.50,
}
```

#### Métricas acumuladas

```python
cumulative_metrics = {
    "total_trades": 120,
    "win_rate": 0.58,
    "profit_factor": 1.65,
    "sharpe_ratio": 1.42,
    "sortino_ratio": 1.95,
    "max_drawdown": -0.082,
    "avg_risk_reward": 2.1,
    "total_pnl": 2450.00,
    "total_return_pct": 0.245,
}
```

### 7.3 Dashboard de Monitoreo

Crear `scripts/monitor_paper_trading.py` que muestre:

```
┌─────────────────────────────────────────────────────────────┐
│           PAPER TRADING DASHBOARD - Día 7                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Equity: $10,245.50 (+2.46%)    │  Trades: 120            │
│  Daily PnL: +$145.20            │  Win Rate: 58.3%        │
│  Drawdown: -3.2%                │  Sharpe: 1.42           │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Equity Curve (últimos 7 días)                      │   │
│  │  $10,400 ┤                          ╭───╮           │   │
│  │  $10,200 ┤                 ╭───╮╭───╯    ╰──        │   │
│  │  $10,000 ┼─────╭───╮╭──────╯   ╰╯                   │   │
│  │   $9,800 ┤     ╰───╯                                 │   │
│  │          └──┬──┬──┬──┬──┬──┬──┬──                    │   │
│  │            Lun Mar Mié Jue Vie Sáb Dom              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Top Símbolos:                                              │
│  BTCUSDT: +$450 (12 trades, 6W/6L)  │ Sharpe: 1.2        │
│  EURUSD:  +$180 (25 trades, 15W/10L)│ Sharpe: 1.8        │
│  XAUUSD:  -$80 (8 trades, 3W/5L)    │ Sharpe: -0.5       │
│                                                             │
│  Señales bloqueadas por riesgo: 8                          │
│  Kill Switch activaciones: 0                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 7.4 Análisis Semanal

Cada semana revisar:

| Pregunta | Acción si NO |
|----------|--------------|
| Win rate > 50%? | Revisar condiciones de entrada |
| Sharpe > 1.0? | Revisar position sizing |
| Drawdown < 15%? | Revisar stop losses |
| Profit factor > 1.3? | Revisar R:R mínimo |
| Algun símbolo con Sharpe < 0? | Pausar ese símbolo |

### 7.5 Deliverables FASE 4

```
✅ Paper trading corriendo 2-4 semanas sin interrupciones
✅ 100+ operaciones registradas
✅ Dashboard de métricas funcionando
✅ Reportes semanales de análisis
✅ Documentación de issues encontrados
✅ Baseline de métricas reales documentado
✅ Lista de mejoras identificadas priorizada
```

---

## 8. FASE 5 — Mejoras y Optimización

**Duración:** 2 semanas  
**Objetivo:** Mejorar el sistema basado en datos reales de paper trading  
**Branch:** `feature/optimizations`

### 8.1 Mejoras Basadas en Datos

Después de 2-4 semanas de paper trading, sabremos:
- Qué símbolos funcionan mejor
- Qué indicadores son más predictivos
- Qué agentes tienen mejor Sharpe
- Qué filtros de riesgo son necesarios

### 8.2 Mejoras Prioritarias

#### Pesos Dinámicos por Régimen (2-3 días)

```python
# Basado en datos reales, ajustar pesos:
DYNAMIC_WEIGHTS = {
    "BULL_TRENDING": {"technical": 0.55, "regime": 0.30, "microstructure": 0.15},
    "BEAR_TRENDING": {"technical": 0.45, "regime": 0.40, "microstructure": 0.15},
    "SIDEWAYS": {"technical": 0.35, "regime": 0.25, "microstructure": 0.40},
    "VOLATILE": {"technical": 0.25, "regime": 0.55, "microstructure": 0.20},
}
```

- [ ] Analizar Sharpe por régimen en datos paper
- [ ] Implementar `get_dynamic_weights()` basado en datos reales
- [ ] Test A/B: pesos estáticos vs dinámicos

#### Filtro de Calidad de Señal (2 días)

```python
# Solo ejecutar señales con:
MINIMUM_SIGNAL_QUALITY = {
    "confidence": 0.65,      # Mínimo 65% confidence
    "risk_reward": 1.8,      # Mínimo R:R 1.8
    "agents_agreement": 0.7, # Mínimo 70% acuerdo
    "volume_ratio": 1.3,     # Volumen 30% sobre promedio
}
```

- [ ] Implementar filtros basados en datos paper
- [ ] Verificar mejora en win rate

#### Position Sizing Óptimo (2 días)

- [ ] Analizar Kelly criterion real vs configuración actual
- [ ] Ajustar `max_risk_per_trade_pct` basado en datos
- [ ] Implementar half-Kelly si no está activo

#### Otras Mejoras (1 semana)

- [ ] Correlación de posiciones (evitar BTC+ETH simultáneo si corr > 0.9)
- [ ] Filtro por sesión (Forex más activo en London/NY)
- [ ] Mejora de exit conditions basada en datos

### 8.3 Deliverables FASE 5

```
✅ Pesos dinámicos implementados y validados
✅ Filtros de calidad de señal optimizados
✅ Position sizing ajustado basado en datos reales
✅ A/B tests documentando mejoras
✅ Nuevo Sharpe baseline (objetivo: +0.2 vs FASE 4)
✅ Código listo para staging
```

---

## 9. FASE 6 — Producción Controlada

**Duración:** 2 semanas  
**Objetivo:** Mover de paper a live con capital mínimo  
**Branch:** `feature/production`

### 9.1 Checklist Pre-Producción

Antes de activar live trading:

```
☐ Paper trading ≥ 2 semanas sin interrupciones
☐ Sharpe sostenido ≥ 1.2
☐ Max drawdown ≤ 15%
☐ Kill switch probado (activa y resetea correctamente)
☐ 200+ operaciones en paper
☐ Todos los modelos entrenados con datos reales
☐ Tests unitarios + integración pasando
☐ Entorno staging desplegado y validado
☐ API keys de Binance configuradas (testnet PRIMERO)
☐ Telegram alerts configurados (opcional)
```

### 9.2 Despliegue en Staging

- [ ] Crear `docker-compose.staging.yml` (puertos 8100, 8502)
- [ ] Desplegar en servidor/staging local
- [ ] Ejecutar pipeline completo por 24 horas
- [ ] Verificar que todo funciona igual que local
- [ ] Probar Binance testnet en staging

### 9.3 Activación Live (Gradual)

#### Semana 1: Testnet → Capital mínimo

```env
# .env.live - Semana 1
EXECUTION_MODE=live
TRADING_ENABLED=true
BINANCE_TESTNET=true              # PRIMERO TESTNET
CAPITAL_ALLOCATED=1000             # Solo $1000 inicial
```

- [ ] Configurar Binance testnet
- [ ] Ejecutar 1 ciclo en testnet live
- [ ] Verificar que órdenes llegan correctamente
- [ ] Monitorear por 24 horas

#### Semana 2: Real (5% capital)

```env
# .env.live - Semana 2
EXECUTION_MODE=live
TRADING_ENABLED=true
BINANCE_TESTNET=false              # Live real
CAPITAL_ALLOCATED=500              # 5% de $10,000
```

- [ ] Configurar Binance real con API keys
- [ ] Activar con capital mínimo (5%)
- [ ] Monitorear cada operación
- [ ] Verificar que SL/TP se ejecutan

### 9.4 Monitoreo en Producción

```
┌─────────────────────────────────────────────────────────────┐
│              LIVE MONITORING - Semana 1                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Mode: 🔴 LIVE        Capital: $500 (5%)                   │
│  Kill Switch: 🟢 INACTIVE                                   │
│                                                             │
│  Today: +$12.50 (+2.5%)    │ Trades: 3                    │
│  Open Positions: 1         │ Signals: 8 (3 executed)       │
│                                                             │
│  ⚠️ ALERT: Drawdown > 5% en XAUUSD                         │
│  ⚠️ ALERT: Kill switch triggers: 0                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 9.5 Deliverables FASE 6

```
✅ Staging desplegado y funcionando
✅ Binance testnet probado exitosamente
✅ Live trading activado con capital mínimo
✅ 1 semana de datos live reales
✅ Sistema de monitoreo funcionando
✅ Playbook de emergencia documentado
✅ Plan de escalamiento de capital
```

---

## 10. Checklist Maestro

### FASE 0 — Entorno Desarrollo (Semana 1)

- [ ] Docker corriendo (db + redis)
- [ ] .env configurado
- [ ] API corriendo en :8000
- [ ] Dashboard en :8501
- [ ] Tests pasando
- [ ] Pipeline manual ejecutable

### FASE 1 — Datos Reales (Semanas 2-3)

- [ ] Script download_data.py
- [ ] 8+ símbolos descargados (2 años)
- [ ] Validación de datos OK
- [ ] FeatureEngine funcionando
- [ ] data/raw/ con .parquet files
- [ ] data/processed/ con features

### FASE 2 — Modelos (Semana 4)

- [ ] Script train_models.py
- [ ] technical_crypto_v1.pkl
- [ ] technical_forex_v1.pkl
- [ ] Métricas documentadas
- [ ] TechnicalAgent cargando modelos

### FASE 3 — Pipeline (Semanas 5-6)

- [ ] APScheduler funcionando
- [ ] 12 símbolos programados
- [ ] FundamentalAgent con eventos
- [ ] PostgreSQL + Redis funcionando
- [ ] Prometheus metrics

### FASE 4 — Paper Trading (Semanas 7-10)

- [ ] Paper trading 2-4 semanas
- [ ] 100+ operaciones
- [ ] Métricas recolectadas
- [ ] Issues documentados

### FASE 5 — Optimización (Semanas 11-12)

- [ ] Pesos dinámicos
- [ ] Filtros optimizados
- [ ] A/B tests completados
- [ ] Nuevo baseline documentado

### FASE 6 — Producción (Semana 13+)

- [ ] Staging desplegado
- [ ] Testnet probado
- [ ] Live con capital mínimo
- [ ] Monitoreo activo

---

## Cronograma Resumido

| Semana | Fase | Objetivo Principal |
|--------|------|-------------------|
| 1 | FASE 0 | Entorno funcional |
| 2-3 | FASE 1 | Datos reales históricos |
| 4 | FASE 2 | Modelos entrenados |
| 5-6 | FASE 3 | Pipeline automático |
| 7-10 | FASE 4 | Paper trading validación |
| 11-12 | FASE 5 | Optimización |
| 13+ | FASE 6 | Producción |

---

## Riesgos y Mitigación

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Datos Forex no disponibles | Media | Usar Yahoo Finance como fallback |
| Modelos no alcanzan Sharpe 1.0 | Alta | Ajustar hiperparámetros, más features |
| Pipeline falla frecuentemente | Media | Logs detallados, alerts |
| Drawdown > 20% en paper | Baja | Kill switch automático |
| Errores en Binance API | Baja | Reintentos, fallback a testnet |

---

**Documento generado:** 30 de Marzo, 2026  
**Versión:** 4.0.0  
**Próxima revisión:** Al completar FASE 1
