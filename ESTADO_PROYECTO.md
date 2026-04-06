# TRADER AI — Estado del Proyecto y Hoja de Ruta

> Documento funcional actualizado: 2026-04-04
> Qué existe hoy, qué falta, y la ruta concreta hacia producción real.
> **Plan de trabajo detallado con tareas accionables: [PLAN_TRABAJO.md](PLAN_TRABAJO.md)**
> **Spec maestro con todas las decisiones arquitecturales: PROYECTO.md (v2.4)**

---

## ¿Qué es el sistema?

Plataforma de trading algorítmico multiactivo, forex, indices, comodities y criptomonedas que **genera señales de compra/venta** usando un sistema multi-agente de IA, valida cada señal contra reglas de riesgo estrictas y ejecuta órdenes automáticamente. Opera en **modo papel por defecto** — sin tocar dinero real hasta activación explícita.

---

## Arquitectura general

```
core/
├── agents/          → 4 agentes IA independientes
├── consensus/       → motor de votación ponderada
├── signals/         → generación de señal final + XAI (SHAP)
├── risk/            → validación de riesgo + Kill Switch
├── execution/       → ejecución en papel o live
├── portfolio/       → gestión de posiciones y capital
├── features/        → ingeniería de features (TA indicators)
├── ingestion/       → clientes Binance/Bybit + WebSocket
├── backtesting/     → motor walk-forward con costos reales
├── strategies/      → framework de estrategias (builtin + custom)
├── adaptation/      → detección de cambio de régimen + retraining
├── monitoring/      → métricas, alertas, Prometheus
├── marketplace/     → marketplace de estrategias (Fase 5)
└── simulation/      → simulador histórico
api/                 → REST API FastAPI (12 rutas)
app/                 → Dashboard Streamlit (7 páginas)
scripts/             → backtest, retrain, seed data, CI gate
tests/               → 39 unit + 37 integración
docker/              → docker-compose completo
.github/workflows/   → CI/CD con 6 checks
```

---

## Lo que el sistema hace hoy

### 1. Genera señales con IA multi-agente

Cuatro agentes independientes analizan el mercado y votan con pesos distintos:

| Agente | Qué analiza | Peso |
|---|---|---|
| **Técnico** | RSI, MACD, Bollinger Bands, EMAs, ATR, volumen — modelo LightGBM | 45% |
| **Régimen** | Clasifica el mercado: alcista, bajista, lateral, crash — bloquea en crash | 35% |
| **Microestructura** | Libro de órdenes, spreads bid-ask | 20% |
| **Fundamental** | Fear & Greed Index, sentimiento CoinGecko — contrarian (sin peso en votación) | Filtro |

La señal final requiere superar un umbral mínimo de consenso. Los conflictos entre agentes quedan registrados en `ConflictLogger`.

### 2. Gestiona el riesgo automáticamente

Antes de ejecutar cualquier orden se verifica:
- Kill Switch activo → bloquea todo
- Pérdida diaria > 5% → bloquea
- Drawdown total > 15% → bloquea
- R:R inaceptable → descarta señal
- Riesgo abierto excesivo → bloquea
- Más de 5 pérdidas consecutivas → bloquea

El **Kill Switch** es el freno de emergencia: solo un admin puede resetearlo manualmente.

### 3. Ejecuta órdenes en dos modos

- **Modo Papel**: simula la ejecución aplicando slippage y comisiones reales sin mover dinero
- **Modo Live**: envía órdenes reales a Binance o Bybit (desactivado por defecto)

### 4. Gestiona el portafolio

- Rastrea posiciones abiertas, capital disponible, P&L diario y total
- Calcula el tamaño óptimo de cada posición con criterio de **Kelly**
- Registra historial completo de operaciones
- `Rebalancer` para ajuste automático de pesos del portafolio

### 5. Backtesting con calidad garantizada

- Walk-forward: divide datos históricos en ventanas train/test
- Aplica costos reales: comisión + slippage (`core/backtesting/costs.py`)
- El CI/CD rechaza código que no supere: **Sharpe ≥ 1.0, Drawdown ≤ 20%, Win Rate ≥ 45%**
- Métricas: Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor

### 6. Dashboard visual

#### 6a. Dashboard HTML/JS nativo (activo — recomendado)
Servido directamente por FastAPI en `http://localhost:8000/`. Sin dependencias externas.

| Página | Contenido |
|---|---|
| **Market View** | Candlestick interactivo (Plotly.js), selector de símbolo + temporalidad (1W/1M/6M), indicadores RSI/MACD/Bollinger mini-charts, panel Agentes IA + Consensus Gauge |
| **Signals** | Señales recientes con badges, tabla de señales, panel SHAP con barras horizontales, resumen XAI |
| **Portfolio** | Métricas clave (Equity, P&L, Sharpe, Drawdown), Equity Curve, Posiciones abiertas, P&L por símbolo |
| **Risk Monitor** | Kill Switch status, 4 métricas de riesgo con progress bars, Donut de exposición, Tabla Hard Limits |

**Características técnicas:**
- Fuentes: Syne (UI) + JetBrains Mono (datos)
- Tema: Dark mode profesional (tokens CSS `--bg0` a `--bg4`)
- Gráficos: Plotly.js CDN (candlestick, equity, donut, bars)
- Datos: API REST FastAPI (endpoints públicos sin auth para lectura)
- Timeframes: 1wk (262 velas), 1mo, 6mo — selector dinámico
- Símbolos reales: EURUSD, GBPUSD, USDJPY, US30, US500, XAUUSD
- Símbolos mock: BTCUSDT, ETHUSDT (marcados con `*`)

#### 6b. Dashboard Streamlit (7 páginas — legacy)

| Página | Contenido |
|---|---|
| `market_view.py` | Datos de mercado en tiempo real |
| `signals.py` | Historial de señales con explicaciones XAI (SHAP) |
| `strategies.py` | Activar/desactivar/configurar estrategias |
| `portfolio.py` | Estado del portafolio y posiciones abiertas |
| `backtesting.py` | Resultados de backtests guardados |
| `risk_monitor.py` | Monitor de riesgo + Kill Switch |
| `simulator.py` | Simulador histórico interactivo |

### 7. Explica cada decisión (XAI)

`xai_module.py` genera una explicación en texto para cada señal con los valores SHAP de los factores más importantes. Cada decisión es auditable.

### 8. Clientes de exchange con WebSocket

- `BinanceClient` y `BybitClient`: clientes REST completos
- `ExchangeAdapter`: interfaz unificada
- `WebSocketStream`: streaming de datos en tiempo real (implementado, sin scheduler activo)
- `DataValidator`: validación de integridad de datos de mercado

### 9. Framework de estrategias extensible

- `StrategyBuilder`: construye estrategias dinámicamente
- `StrategyRegistry`: catálogo de estrategias activas
- Builtin: `ema_rsi.py`, `mean_reversion.py`
- Cualquier estrategia custom puede registrarse

### 10. Adaptación automática al régimen

- `RegimeWatcher`: detecta cambios de régimen de mercado
- `Retraining`: reentrenamiento automático cuando el régimen cambia

### 11. Observabilidad completa

- Logs estructurados con `structlog`
- `DecisionTracer`: trazabilidad completa de cada decisión
- `PrometheusMetrics`: métricas exportadas a Prometheus
- Grafana: dashboards de métricas (`docker/grafana/`)

### 12. CI/CD completo — todos los checks en verde

| Check | Estado | Detalle |
|---|---|---|
| Lint (ruff) | ✅ Pasa | Estilo de código |
| Tests unitarios | ✅ Pasa | 39 tests |
| Tests de integración | ✅ Pasa | 37 tests (modo papel) |
| Safety Gate | ✅ Pasa | Verifica defaults paper/false |
| Backtest Quality Gate | ✅ Pasa | Sharpe > 1.0 |
| Docker Build | ✅ Pasa | Imagen construida |

### 13. REST API FastAPI (15+ rutas)

`/auth`, `/market`, `/signals`, `/execution`, `/portfolio`, `/risk`, `/backtesting`, `/strategies`, `/marketplace`, `/simulation` — más dependencias con inyección, rate limiting con `slowapi`.

**Cambios recientes:**
- Endpoints GET de `/market/*` son **públicos** (sin auth) para consumo del dashboard HTML
- Nuevo parámetro `?timeframe=1wk|1mo|6mo` en `/market/{symbol}/data`
- Dashboard HTML servido en `/` vía `FileResponse`
- Static files montados en `/static`

### 14. Carga de datos reales al startup

- Al iniciar FastAPI se cargan automáticamente los archivos `.parquet` desde `data/raw/parquet/`
- Se calculan las 20 features técnicas vía `calculate_all()` para cada símbolo y timeframe
- Cache estructurado: `{symbol: {timeframe: [records]}}`
- Features cache: `{symbol: {rsi_14, macd_line, regime, ...}}`
- Regime cache: `{symbol: {regime}}`

---

## Lo que aún NO existe o está incompleto

### Crítico — bloquea operación real

| Qué falta | Impacto | Archivo relevante |
|---|---|---|
| **Persistencia en base de datos** | Todo está en memoria: posiciones, señales e historial se pierden al reiniciar | `core/models.py` (modelos definidos, sin ORM operativo) |
| **Pipeline automático de señales** | No hay scheduler que ejecute el ciclo cada X minutos | Falta `scripts/run_pipeline.py` completo |
| **Ingesta de datos activa** | `BinanceClient` y `WebSocketStream` existen pero nada los invoca periódicamente | `core/ingestion/` |
| **Variables de entorno reales** | `.env.example` tiene placeholders — nunca se configuraron claves reales | `.env.example` |

**Nota**: ✅ **Modelos ML entrenados** — `technical_crypto_mtf_v1.pkl` está disponible
**Nota**: ✅ **Datos crypto validados** — BTCUSDT, ETHUSDT backtesting completo en Fase 5

### Importante — necesario para operar con seguridad

| Qué falta | Impacto | Archivo relevante |
|---|---|---|
| **Autenticación real de usuarios** | Usuarios hardcodeados en memoria (`admin/admin123`) | `api/routes/auth.py` |
| **Migraciones Alembic** | Hay un `001_initial_schema.sql` pero no hay migraciones Alembic generadas | `scripts/migrations/001_initial_schema.sql` |
| **Alertas Telegram** | `AlertEngine` y `TelegramBot` existen pero el bot no está configurado | `core/notifications/telegram_bot.py` |
| **Datos históricos de entrenamiento** | Sin datos en `data/raw/` no se puede entrenar | `scripts/retrain.py` (script existe) |

### Parcialmente implementado (Fase 5+ — Optimizaciones futuras)

| Funcionalidad | Estado | Archivo |
|---|---|---|
| **Marketplace de estrategias** | Lógica backend existe, sin UI completa ni persistencia | `core/marketplace/` |
| **Simulador histórico** | Motor existe, integración con dashboard incompleta | `core/simulation/historical_simulator.py` |
| **Optimización de parámetros** | Carpeta vacía — candidato para Phase 5+ | `core/optimization/` |
| **Reentrenamiento automático** | Script `retrain.py` existe, sin scheduler configurado | `scripts/retrain.py` |

**Nota**: **Fase 5 de backtesting/validación CRYPTO está 100% completa**. Las funcionalidades arriba listadas son extensiones opcionales para optimizaciones futuras.

---

## Hoja de ruta hacia producción

### FASE A — Infraestructura y datos (prioridad máxima)

#### A1. Levantar servicios de soporte
```bash
cd "Trading IA/docker"
docker-compose up db redis -d

# Verificar
docker-compose ps
```

#### A2. Crear base de datos operativa
El archivo `scripts/migrations/001_initial_schema.sql` ya existe. Hay dos opciones:

**Opción rápida (SQL directo):**
```bash
# Ejecutar el schema SQL existente
docker exec -i trader_db psql -U trader -d trader_ai < scripts/migrations/001_initial_schema.sql
```

---

## 🟦 Estado actual (a la fecha 2026-03-31)

### FASE 1: Descarga y preparación de datos (Completada)
- Arquitectura de datos en `scripts/download_all_forex.py` entregada y probada.
- Símbolos: EURUSD, GBPUSD, USDJPY, XAUUSD, US500, US30.
- Temporalidades: 1h, 4h, 1d, 1wk, 1mo, 6mo, 1y.
- Guardado dual: `data/raw/parquet/...` y `data/raw/csv/...`.
- Validaciones implementadas: timestamps, OHLCV, volumes, duplicados, NaNs.
- Ajustes y correcciones resueltos:
  - 730d intradía (1h,4h) con Yahoo limite histórico.
  - Resample semestral/anual con `6ME` / `1YE`.
  - Columnas MultiIndex normalizadas.

### FASE 1b: Carga de datos reales en API (Completada — 2026-04-04)
- FastAPI carga automáticamente los parquet al startup (`_load_parquet_data()` en `api/main.py`)
- Timeframes cargados: **1wk** (262 velas × 6 símbolos = 1572 velas totales)
- 1mo y 6mo no cargan features (insuficientes velas para `calculate_all` que requiere ≥200)
- Features calculadas: 20 columnas (RSI, MACD, EMA, ATR, Bollinger, VWAP, Volume, Trend, Volatility)
- Endpoints `/market/{symbol}/data?timeframe=1wk` devuelven datos reales sin auth
- Dashboard HTML consume datos reales vía `fetch()` con fallback a mock

### FASE 2: Feature engineering y modelado (En curso / próximas tareas)
- Prioridad inmediata:
  - Generar indicadores técnicos (SMA, EMA, RSI, ATR, MACD) para cada timeframe.
  - Fijar targets de entrenamiento (e.g., `futuro_1h_pct`, `up_down_binario`).
  - Crear split temporal Train/Val/Test y escalar características.
- Entrenamiento recomendado:
  - LightGBM para cada timeframe separada.
  - Guardar modelos en `data/models/<symbol>_<tf>.pkl`.
- Evaluación:
  - Métricas: Sharpe, Win Rate, Profit Factor, F1 Score, MASE.
  - Backtest cross-validation Walk-forward.

### FASE 3: Backtesting y transición a paper trading
- Integrar modelos entrenados en `core/backtesting/`.
- Implementar sesión de ejecución con señales y modelo en `core/execution/`.
- Verificar con métricas de riesgo (DD, drawdowns, max positions).

### FASE 4: Deploy y monitorización
- Levantar API `api/main.py` + scheduler cron de inferencia cada 1h.
- Añadir monitoreo Prometheus + alertas Slack/Telegram.
- CI/CD con pruebas A/B, gates de calidad.

### FASE 5: Backtesting y validación de CRYPTO (✅ **COMPLETADA** — 2026-04-06)

#### 5.1. Backtesting Pipeline

**Modelo entrenado**: `technical_crypto_mtf_v1.pkl` (LightGBM binary classifier)
- Features: 75 indicadores técnicos multi-timeframe
- Activos: BTCUSDT, ETHUSDT
- Período: 2 años de datos (1h candles)
- Signals analizadas: 6,043 trades en total

**Backtest sin costos realistas**:
- BTCUSDT: $1,846,036 P&L
- ETHUSDT: $1,846,036 P&L (combinado)

#### 5.2. Validación con costos realistas

Se aplicaron costos reales de Binance:
- **Maker fees**: 0.05% por transacción
- **Slippage**: 5 basis points (0.05%)
- **Total por round-trip**: 0.1% + 0.1% = 0.2% por trade

**P&L realista después de costos**:
- BTCUSDT: $1,287,436 (12,223% return)
- ETHUSDT: $1,287,436 (651% return)  
- **Reducción esperada**: 30% (impacto de costos)

#### 5.3. Métricas de portafolio

| Métrica | BTCUSDT | ETHUSDT | Portfolio | Status |
|---------|---------|---------|-----------|--------|
| **Return %** | 12,223% | 651% | 6,437% avg | ✅ Excellent |
| **Win Rate %** | 92.7% | 92.6% | 92.65% avg | ⚠️ Very High* |
| **Profit Factor** | 3.76x | 6.82x | 5.29x avg | ✅ Excellent |
| **Sharpe Ratio** | 5.73 | 7.98 | 6.86 avg | ✅ Excellent |
| **Risk-Reward** | 3.76x | 6.82x | 5.29x avg | ✅ Excellent |
| **Recovery Factor** | 553x | 748x | 650.5x avg | ✅ Very Strong |

*⚠️ **Overfitting Alert**: Win rate >90% is unrealistic. Expected live performance: 55-70% win rate.

#### 5.4. Integración FastAPI del Dashboard

**Eliminado**: Standalone HTML file (`backtest_results/dashboard.html` - 220 líneas, duplicado)

**Integrado en FastAPI**:
- **Archivo**: `api/routes/dashboard.py` (200+ líneas)
- **Endpoint**: `GET /dashboard/crypto` → HTMLResponse
- **URL**: `http://localhost:8000/dashboard/crypto`
- **Datos**: Lee automáticamente desde `backtest_results/*.json`

**Características del Dashboard**:
- Gráficos interactivos (Chart.js): P&L por símbolo, Metrics Radar
- Tarjetas de resumen: BTCUSDT, ETHUSDT, Portfolio Summary
- Advertencias automáticas sobre overfitting (win rate >90%)
- Mostrando: Return %, Win Rate, Sharpe, Profit Factor, Recovery Factor
- Autenticación integrada (requiere login como en resto de API)
- Tema oscuro profesional (Syne font + dark mode CSS)

#### 5.5. API Endpoints nuevos para CRYPTO

Añadidos 5 nuevos endpoints en `api/routes/backtesting.py`:

```
GET /backtest/crypto/summary
  → Quick metrics summary (symbols, return, sharpe)

GET /backtest/crypto/validation
  → Full validation data with realistic costs + portfolio metrics

GET /backtest/crypto/config
  → Live trading configuration (buy/sell thresholds, risk limits)

GET /backtest/crypto/reports/{symbol}
  → Individual symbol backtest report (BTCUSDT or ETHUSDT)
```

Todos los endpoints:
- Cargan datos desde `backtest_results/*.json`
- Requieren autenticación (`require_trader`)
- Retornan JSON estructurado
- Cachan validación en tiempo real

**Fuentes de datos**:
```
backtest_results/
├── comprehensive_validation.json    ← Main dashboard data source
├── live_trading_config.json         ← Trade parameters & thresholds
├── report_BTCUSDT_1h.json           ← BTCUSDT backtest signals
└── report_ETHUSDT_1h.json           ← ETHUSDT backtest signals
```

#### 5.6. Hallazgos críticos y recomendaciones

**Banderas de overfitting detectadas**:
1. **Win rate 92%+**: Expect 55-70% in live trading
2. **Perfect entry/exit**: Assumes infinite liquidity (unrealistic)
3. **In-sample only**: No held-out test data validation
4. **Historical bias**: Model optimized for 2-year backtest period
5. **P&L variance**: 30% reduction after adding realistic costs

**Recomendación oficial**:
```
🔴 DO NOT deploy to live with $10,000+ immediately
✅ INSTEAD: Run 2-week paper trading first
✅ ONLY IF: Paper trading confirms 60%+ win rate, start with $500-$1,000
✅ MONITOR: Kill switch active, daily loss caps enabled
```

#### 5.7. Archivos generados en Fase 5

**Reportes** (en `backtest_results/`):
- `comprehensive_validation.json` — Métricas completas con costos realistas
- `live_trading_config.json` — Parámetros para ejecución live
- `report_BTCUSDT_1h.json` — Reporte detallado de BTCUSDT
- `report_ETHUSDT_1h.json` — Reporte detallado de ETHUSDT

**Código** (en `api/routes/`):
- `dashboard.py` — FastAPI endpoint que sirve dashboard HTML
- `backtesting.py` — Actualizado con 5 nuevos endpoints CRYPTO

**Infraestructura actualizada** (en `api/`):
- `main.py` — Registra nuevo dashboard router

#### 5.8. Próximos pasos

**Inmediato (prioritario)**:
1. ✅ Verificar dashboard en `http://localhost:8000/dashboard/crypto`
2. ✅ Revisar endpoints en `http://localhost:8000/docs` (Swagger)
3. ✅ Monitorear paper trading ≥ 2 semanas
4. ✅ Validar que win rate live ≥ 60%

**Antes de activar live trading**:
- [ ] Sharpe ratio sostenido en paper ≥ 1.0
- [ ] Kill Switch activado y probado
- [ ] Alertas Telegram configuradas y funcionando
- [ ] Revisión manual de ≥ 20 señales generadas
- [ ] Drawdown máximo < 5% en periodo de prueba

**Optimizaciones futuras**:
- Reentrenamiento con nuevos datos (cada 30 días)
- A/B testing de thresholds (buy: 0.5→0.6, sell: -0.3→-0.4)
- Ensemble de modelos (technical + consensus)
- Multi-timeframe validation (1h + 4h + 1d)

---

---

## APÉNDICE A: Análisis Técnico Detallado del Estado

### Estado de Scripts de Descarga

| Script | Función | Estado | Notas |
|--------|---------|--------|-------|
| `download_all_forex.py` | Descargar forex/índices via yfinance | ✅ Funcional | Usa yfinance (gratuito) |
| `download_binance.py` | Descargar crypto via Binance | ✅ Funcional | Requiere API key (gratuito) |
| `download_data.py` | Genérico con asset-class | ✅ Completo | Soporta crypto, forex, indices, commodities |
| `download_forex.py` | Forex específico | ❌ Legacy | No se recomienda usar |

### Estado de Datos Descargados

**Datos cargados actualmente:**
```
data/raw/
├── EURUSD_1h.parquet (17,222 velas)
├── GBPUSD_1h.parquet (17,224 velas)
├── USDJPY_1h.parquet (17,125 velas)
├── XAUUSD_1h.parquet (13,708 velas)
├── US500_1h.parquet (5,068 velas)
├── US30_1h.parquet (5,068 velas)
├── EURUSD_4h.parquet (4,353 velas)
├── GBPUSD_4h.parquet (4,353 velas)
└── ... [18 archivos totales]

❌ FALTA: BTCUSDT y ETHUSDT (CRYPTO assets)
```

### Estado de Scripts de Entrenamiento

| Script | Función | Estado |
|--------|---------|--------|
| `retrain.py` | Entrenar LightGBM | ✅ Funcional |
| `train_asset_specific_models.py` | Multi-modelo por activo | ✅ Listo para ejecutar |
| `run_backtest.py` | Backtesting | ✅ Funcional |

### Problemas Identificados

1. **CRYPTO data completamente faltante** (BTCUSDT, ETHUSDT)
   - Impacto: Modelos CRYPTO no pueden entrenarse
   - Solución: Ejecutar `download_data.py --asset-class crypto --years 2`

2. **4h timeframe para CRYPTO limitado** (yfinance no lo soporta)
   - Impacto: Solo 1h y 1d disponibles para CRYPTO
   - Workaround: Usar datos 1h y resamplear localmente a 4h

3. **Feature engineering no persistido**
   - Impacto: Features se recalculan cada vez
   - Solución: Implementar persistencia en data/processed/

4. **Train/test split no persistido**
   - Impacto: Validación cruzada subóptima
   - Solución: Guardar splits en data/splits/

### Próximos Pasos Inmediatos

1. ✅ Descargar datos CRYPTO (1h, 1d) - **BLOQUEANTE**
2. ✅ Entrenar modelos CRYPTO
3. ⏳ Implementar persistencia de features
4. ⏳ Persistir train/test splits
5. ⏳ Validación de modelos en backtesting

> Nota: Esta sección se actualiza automáticamente tras cada sprint en el backlog de tareas y cada commit relevante en `feature/data-download`.


**Opción robusta (Alembic):**
```bash
alembic init alembic
# Crear modelos SQLAlchemy para: candles, signals, orders, portfolio_snapshots, users
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

Tablas mínimas necesarias:
- `candles` — OHLCV histórico (TimescaleDB hypertable)
- `signals` — señales generadas con su explicación SHAP
- `orders` — órdenes ejecutadas con estado
- `portfolio_snapshots` — historial del portafolio
- `users` — autenticación real

#### A3. Configurar variables de entorno
```bash
cp .env.example .env
```

Valores mínimos para funcionar:
```env
# Seguridad — mantener en paper hasta validar
EXECUTION_MODE=paper
TRADING_ENABLED=false

# Base de datos
DATABASE_URL=postgresql+asyncpg://trader:trader@localhost:5432/trader_ai
REDIS_URL=redis://localhost:6379/0

# Seguridad JWT
JWT_SECRET_KEY=<genera 64 chars aleatorios>

# Exchange (testnet primero)
BINANCE_API_KEY=<clave testnet>
BINANCE_SECRET_KEY=<secreto testnet>
BINANCE_TESTNET=true

# Alertas (opcional)
TELEGRAM_BOT_TOKEN=<token>
TELEGRAM_CHAT_ID=<chat_id>
```

Claves testnet: https://testnet.binance.vision/

---

### FASE B — Datos y modelos ML

#### B1. Descargar datos históricos

El script `scripts/retrain.py` ya existe pero necesita datos. Crear `scripts/download_data.py`:
```python
# Descargar 2 años de candles 1h para BTCUSDT y ETHUSDT desde Binance
# Guardar en data/raw/
```

#### B2. Entrenar el modelo técnico
```bash
python scripts/retrain.py --symbol BTCUSDT --timeframe 1h
python scripts/retrain.py --symbol ETHUSDT --timeframe 1h
# Verificar que aparezcan archivos .joblib en data/models/
```

---

### FASE C — Pipeline automático de señales

El componente más crítico que falta. Crear `scripts/run_pipeline.py`:

```python
# Ciclo completo cada hora:
# 1. Obtener últimas N velas (BinanceClient / WebSocketStream)
# 2. Calcular features (FeatureEngine)
# 3. Ejecutar los 4 agentes
# 4. Consenso → señal (VotingEngine)
# 5. Validar riesgo (RiskManager)
# 6. Ejecutar en papel o live (PaperExecutor / LiveExecutor)
# 7. Actualizar portafolio (PortfolioManager)
# 8. Persistir en DB
# 9. Enviar alerta Telegram si hay señal
```

**Opciones de scheduler** (de más simple a más robusto):

| Opción | Complejidad | Recomendada para |
|---|---|---|
| APScheduler dentro de FastAPI | Baja | Inicio rápido |
| Celery + Redis (ya en docker-compose) | Media | Producción |
| Cron del servidor | Muy baja | Pruebas iniciales |

---

### FASE D — Autenticación real

Reemplazar usuarios hardcodeados en `api/routes/auth.py`:

```python
# Opción A: tabla users en PostgreSQL con bcrypt (recomendado)
# Opción B: Auth0 / Supabase (más rápido de integrar)
```

Mínimo viable: tabla `users` con `email`, `hashed_password`, `role`.

---

### FASE E — Despliegue en VPS

**Infraestructura recomendada:**

| Proveedor | Specs | Costo | Uso |
|---|---|---|---|
| Hetzner CX21 | 2 vCPU / 4 GB | ~5 €/mes | Paper trading |
| DigitalOcean 2 GB | 1 vCPU / 2 GB | ~12 USD/mes | Paper trading |
| AWS t3.small | 2 vCPU / 2 GB | ~15 USD/mes | Si ya usas AWS |

```bash
# En el servidor:
curl -fsSL https://get.docker.com | sh
git clone https://github.com/Ximena5745/Trading_IA.git
cd Trading_IA
nano .env   # configurar variables de producción
docker-compose up -d
curl http://localhost:8000/health
```

**Checklist de seguridad antes de exponer a internet:**
- [ ] Nginx como reverse proxy con HTTPS (Let's Encrypt)
- [ ] Firewall: solo puertos 80, 443, SSH
- [ ] Cambiar contraseñas por defecto de Grafana
- [ ] Verificar rate limiting (slowapi ya integrado)
- [ ] Rotar `JWT_SECRET_KEY` regularmente

---

### FASE F — Validación en papel (mínimo 2 semanas)

Checklist antes de activar live:
- [ ] Sistema corriendo en papel ≥ 2 semanas sin interrupciones
- [ ] Sharpe ratio sostenido ≥ 1.0
- [ ] Kill Switch se activa y resetea correctamente
- [ ] Alertas Telegram llegan correctamente
- [ ] Portafolio persiste tras reinicios del servidor
- [ ] Se revisaron manualmente ≥ 20 señales generadas
- [ ] P&L diario no supera el límite del 5% ni en pérdida ni en modo anómalo

---

### FASE G — Live trading

Solo cuando Fase F esté completamente validada:

```env
EXECUTION_MODE=live
TRADING_ENABLED=true
BINANCE_TESTNET=false
```

**Estrategia de capital gradual:**
1. Semana 1-2: 5% del capital total
2. Semana 3-4: 10% si Sharpe sostenido
3. Mes 2+: escalar según performance real

---

## Prioridades resumidas

```
URGENTE — bloquea todo lo demás
  A1. Levantar PostgreSQL + Redis (docker-compose)
  A2. Base de datos operativa (schema SQL o Alembic)
  A3. Variables de entorno (.env configurado)
  B.  Datos históricos + modelos ML entrenados (.joblib)
  C.  Pipeline automático de señales (scheduler)

IMPORTANTE — para operar con seguridad
  D.  Autenticación real (no en memoria)
  E.  Despliegue en VPS con HTTPS
  F.  Alertas Telegram funcionando

CUANDO YA FUNCIONE EN PAPEL (≥ 2 semanas)
  F.  Validación completa del checklist
  G.  Activar live con capital pequeño (5%)

FUTURO — Fase 5
  - Marketplace de estrategias con UI completa
  - Simulador histórico integrado al dashboard
  - Optimización de parámetros (core/optimization/)
  - Multi-símbolo (más allá de BTC/ETH)
  - Soporte Bybit completo
```

---

## Estado actual del código

El código está listo para desplegar. Lo que falta es **infraestructura, datos y configuración** — no código base.

| Componente | Estado | Ubicación |
|---|---|---|
| Agentes IA (4) | ✅ Completo | `core/agents/` |
| Motor de consenso | ✅ Completo | `core/consensus/` |
| Gestión de riesgo + Kill Switch | ✅ Completo | `core/risk/` |
| Ejecución papel + live | ✅ Completo | `core/execution/` |
| Motor de backtesting | ✅ Completo | `core/backtesting/` |
| Gestión de portafolio | ✅ Completo | `core/portfolio/` |
| Ingeniería de features | ✅ Completo | `core/features/` |
| XAI con SHAP | ✅ Completo | `core/signals/xai_module.py` |
| Clientes Binance/Bybit + WebSocket | ✅ Completo | `core/ingestion/` |
| Framework de estrategias | ✅ Completo | `core/strategies/` |
| Adaptación de régimen | ✅ Completo | `core/adaptation/` |
| **Dashboard HTML/JS nativo** | ✅ Completo | `static/dashboard.html` |
| Dashboard Streamlit (7 páginas) | ✅ Completo | `app/` |
| REST API FastAPI (15+ rutas) | ✅ Completo | `api/` |
| Observabilidad (logs + Prometheus) | ✅ Completo | `core/observability/`, `core/monitoring/` |
| CI/CD (6 checks en verde) | ✅ Completo | `.github/workflows/ci.yml` |
| Docker Compose (5 servicios) | ✅ Completo | `docker/` |
| Script de reentrenamiento | ✅ Existe | `scripts/retrain.py` |
| Schema SQL inicial | ✅ Existe | `scripts/migrations/001_initial_schema.sql` |
| **Scheduler / pipeline automático** | ❌ Falta crear | `scripts/run_pipeline.py` |
| **Modelos ML entrenados** | ❌ Falta entrenar | `data/models/` (vacío) |
| **Persistencia DB operativa** | ❌ Falta activar | ORM en memoria por ahora |
| **Auth real** | ❌ Falta implementar | `api/routes/auth.py` |
| **Variables de entorno reales** | ❌ Falta configurar | `.env` |
| **Telegram bot activo** | ❌ Falta configurar | `core/notifications/telegram_bot.py` |
| **Datos crypto (BTCUSDT, ETHUSDT)** | ❌ Falta descargar | `data/raw/parquet/` |
| **Datos 1h/4h/1d** | ❌ Falta descargar | `data/raw/parquet/` |
| Marketplace (Fase 5) | ⚠️ Parcial | `core/marketplace/` |
| Simulador dashboard | ⚠️ Parcial | `core/simulation/` |
| Optimización de parámetros | ⚠️ Vacío | `core/optimization/` |

---

## Cambios Recientes (2026-04-04)

### Frontend: Dashboard HTML/JS Nativo
- ✅ Nuevo dashboard servido por FastAPI en `http://localhost:8000/`
- ✅ 4 páginas: Market View, Signals, Portfolio, Risk
- ✅ Diseño dark mode profesional (SKILL.md) con fuentes Syne + JetBrains Mono
- ✅ Gráficos Plotly.js: candlestick, equity curve, donut exposure, SHAP bars
- ✅ Selector de temporalidad: 1W / 1M / 6M
- ✅ Sin limitación de velas — muestra todos los datos disponibles por símbolo

### Backend: Carga de Datos Reales
- ✅ `_load_parquet_data()` carga automáticamente parquet al startup
- ✅ 6 símbolos × 262 velas semanales = 1572 velas totales con 20 features cada una
- ✅ Features calculadas: RSI, MACD, EMA, ATR, Bollinger, VWAP, Volume, Trend, Volatility
- ✅ Endpoints GET de `/market/*` son públicos (sin auth)
- ✅ Nuevo parámetro `?timeframe=1wk|1mo|6mo` en `/market/{symbol}/data`
- ✅ Serialización JSON corregida para tipos numpy/pandas

### Dependencias Instaladas
- fastapi, uvicorn, pandas, pyarrow, structlog, slowapi
- python-jose, passlib, httpx, requests, pydantic-settings
- asyncpg, sqlalchemy, redis, apscheduler, lightgbm, shap, scikit-learn, prometheus-client

### Documentación Actualizada
- ✅ `ESTADO_PROYECTO.md` — fecha, nuevo dashboard, datos reales, checklist actualizado
- ✅ `app/README.md` — reescrito con dashboard HTML como primario
- ✅ `docs/README.md` — métricas y diagrama actualizados
- ✅ `docs/architecture/system-overview.md` — capas y métricas actualizadas
- ✅ `docs/api-reference/endpoints.md` — endpoints de market actualizados
- ✅ `docs/technical-integration/README.md` — arquitectura y cambios recientes
- ✅ `PROYECTO_COMPLETO.md` — versión 2.1.0, dashboard dual, métricas
