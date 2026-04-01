# TRADER AI — Estado del Proyecto y Hoja de Ruta

> Documento funcional actualizado: 2026-03-29
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

### 6. Dashboard visual (Streamlit — 7 páginas)

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

### 13. REST API FastAPI (12 rutas)

`/auth`, `/market`, `/signals`, `/execution`, `/portfolio`, `/risk`, `/backtesting`, `/strategies`, `/marketplace`, `/simulation` — más dependencias con inyección, rate limiting con `slowapi`.

---

## Lo que aún NO existe o está incompleto

### Crítico — bloquea operación real

| Qué falta | Impacto | Archivo relevante |
|---|---|---|
| **Persistencia en base de datos** | Todo está en memoria: posiciones, señales e historial se pierden al reiniciar | `core/models.py` (modelos definidos, sin ORM operativo) |
| **Pipeline automático de señales** | No hay scheduler que ejecute el ciclo cada X minutos | Falta `scripts/run_pipeline.py` |
| **Modelos ML entrenados** | `TechnicalAgent` tiene estructura LightGBM pero no hay archivos `.joblib` en `data/models/` | `core/agents/technical_agent.py` |
| **Ingesta de datos activa** | `BinanceClient` y `WebSocketStream` existen pero nada los invoca periódicamente | `core/ingestion/` |
| **Variables de entorno reales** | `.env.example` tiene placeholders — nunca se configuraron claves reales | `.env.example` |

### Importante — necesario para operar con seguridad

| Qué falta | Impacto | Archivo relevante |
|---|---|---|
| **Autenticación real de usuarios** | Usuarios hardcodeados en memoria (`admin/admin123`) | `api/routes/auth.py` |
| **Migraciones Alembic** | Hay un `001_initial_schema.sql` pero no hay migraciones Alembic generadas | `scripts/migrations/001_initial_schema.sql` |
| **Alertas Telegram** | `AlertEngine` y `TelegramBot` existen pero el bot no está configurado | `core/notifications/telegram_bot.py` |
| **Datos históricos de entrenamiento** | Sin datos en `data/raw/` no se puede entrenar | `scripts/retrain.py` (script existe) |

### Parcialmente implementado (Fase 5)

| Funcionalidad | Estado | Archivo |
|---|---|---|
| **Marketplace de estrategias** | Lógica backend existe, sin UI completa ni persistencia | `core/marketplace/` |
| **Simulador histórico** | Motor existe, integración con dashboard incompleta | `core/simulation/historical_simulator.py` |
| **Optimización de parámetros** | Carpeta `core/optimization/` vacía | — |

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

---

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
| Dashboard Streamlit (7 páginas) | ✅ Completo | `app/` |
| REST API FastAPI (12 rutas) | ✅ Completo | `api/` |
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
| Marketplace (Fase 5) | ⚠️ Parcial | `core/marketplace/` |
| Simulador dashboard | ⚠️ Parcial | `core/simulation/` |
| Optimización de parámetros | ⚠️ Vacío | `core/optimization/` |
