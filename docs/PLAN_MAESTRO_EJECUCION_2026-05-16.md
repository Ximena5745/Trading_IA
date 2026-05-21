# PLAN MAESTRO DE EJECUCIÓN — TRADER AI v2.0 (ESPECIALIZADO)
**Fecha:** 2026-05-16  
**Versión:** 2.1 — Plan específico con exchanges, activos y estrategias reales  
**Basado en:** Auditoría Técnica + Auditoría Cuantitativa + Código fuente actual  
**Estado del sistema:** MVP parcial · Score técnico 5.3/10 · Score cuantitativo 3.85/10  
**EXECUTION_MODE:** paper (nunca cambiar a live sin autorización explícita)

---

## ECOSISTEMA DEL PROYECTO — CONFIGURACIÓN REAL

### Exchanges configurados

| Exchange | Tipo | Estado | Simbolos soportados | Ubicación adaptador |
|----------|------|--------|---------------------|-------------------|
| **Binance** | Crypto spot + Futures | ✅ Implementado | BTC, ETH, SOL, BNB (USDT) | `core/ingestion/binance_client.py` |
| **Bybit** | Crypto Futures/Perps | ✅ Implementado | BTC, ETH, SOL, BNB perpetuos | `core/ingestion/bybit_client.py` |
| **OANDA** | Forex + Indices + Commodities | ✅ Implementado | 40+ pares forex, índices, oro, petróleo | `core/ingestion/oanda_client.py` |
| **MetaTrader 5 (IC Markets)** | Forex + Commodities + Índices | ✅ Implementado | Forex majors/minors, Gold, Oil, índices globales | `core/ingestion/providers/mt5_client.py` |
| **Interactive Brokers** | Multi-asset | ⚠️ Parcial | Acciones, opciones, futuros, forex | `core/ingestion/providers/ib_client.py` |

### Activos por clase

```
CRYPTO (Binance + Bybit)
├── BTCUSDT       (Bitcoin)
├── ETHUSDT       (Ethereum)
├── SOLUSDT       (Solana)
└── BNBUSDT       (BNB)

FOREX (OANDA + MT5)
├── EURUSD        (Euro / USD) — Spread: 0.6 pips MT5, 0.2 pips OANDA
├── GBPUSD        (Pound / USD)
├── USDJPY        (USD / Yen) — Point: 0.001
├── USDCHF        (USD / CHF)
├── AUDUSD        (AUD / USD)
└── USDCAD        (USD / CAD)

INDICES (OANDA + MT5)
├── SPX500        (S&P 500)
├── NAS100        (Nasdaq 100)
├── US30          (Dow Jones 30)
├── DE40          (DAX — Alemania)
├── UK100         (FTSE 100 — Reino Unido)
└── JP225         (Nikkei 225 — Japón)

COMMODITIES (OANDA + MT5)
├── XAUUSD        (Oro / USD)
├── XAGUSD        (Plata / USD)
├── USOIL         (WTI Crude Oil)
├── UKOIL         (Brent Crude Oil)
├── NATGAS        (Gas Natural)
└── WHEAT         (Trigo)
```

Total: **28 activos** configurados · **4 exchanges** operacionales · **6 timeframes** soportados (1m, 5m, 15m, 1h, 4h, 1d)

### Estrategias builtin implementadas

| Estrategia | ID | Símbolos óptimos | Régimen óptimo | Estado | Archivo |
|-----------|----|--------------------|---------------|--------|---------|
| **EMA Crossover + RSI** | `ema_rsi_v1` | Todos (forex, índices) | Trending | ✅ Completa | `core/strategies/builtin/ema_rsi.py` |
| **Mean Reversion** | `mean_rev_v1` | Forex, Indices | Rango/Lateral | ✅ Completa | `core/strategies/builtin/mean_reversion.py` |
| **TSMOM (Time-Series Momentum)** | `tsmom_v1` | Crypto, Forex, Indices | Trending persistente | ✅ Completa | `core/strategies/builtin/tsmom.py` |
| **Volatility Breakout Adaptive** | `vol_breakout_v1` | Crypto, Commodities | Post-consolidación | ✅ Completa | `core/strategies/builtin/volatility_breakout.py` |

### Infraestructura existente

```
Bases de datos:
├── TimescaleDB (PostgreSQL + extensión TS)
├── Redis (caché, streams, estado distribuido)
└── Parquet files (datos históricos por símbolo)

ML/Models:
├── LightGBM (modelo técnico principal)
├── XGBoost (ensemble)
├── CatBoost (alternativo)
├── LSTM (modelo de red neuronal)
├── HMM (detección de régimen — en progreso)
├── River (online learning — backlog)

Observabilidad:
├── structlog (logging estructurado)
├── Prometheus (métricas)
├── Grafana (dashboards — sin configurar)
├── Telegram (alertas)

Validación:
├── pytest + hypothesis (testing)
├── mypy (type checking)
├── ruff (linting)
├── bandit (seguridad)
```

---

## RESUMEN EJECUTIVO DEL PLAN ESPECIALIZADO

El sistema tiene una **arquitectura bien concebida pero con brechas críticas** entre especificación e implementación (~55% de brecha). Los cuatro blockers absolutos para operar son: (1) base de datos nunca inicializada, (2) pipeline automático desactivado, (3) bug bloqueante en ejecución de órdenes, (4) JWT sin validación en producción. En paralelo, el edge cuantitativo es débil por features genéricas, targets ruidosos y validación estadística ausente.

**Este plan integra ambas auditorías en un único roadmap ejecutable con 8 fases, prioridades claras y criterios de aceptación medibles.**

---

## PRINCIPIOS NO NEGOCIABLES (del Prompt Maestro)

| # | Principio | Aplicación inmediata |
|---|-----------|---------------------|
| P1 | Spec-Driven Development | Ningún código sin spec aprobada previa |
| P2 | Quant-First | Edge estadístico > features de UI |
| P3 | SOLID + Clean Architecture | SRP, OCP, LSP, ISP, DIP en cada módulo |
| P4 | Fail-Safe by Default | Kill switch con precedencia absoluta |
| P5 | Robustez sobre velocidad | Validar datos antes de modelos siempre |
| P6 | Evidencia estadística | Sharpe OOS > 1.0 · Max DD < 20% antes de producción |
| P7 | Trazabilidad total | Desde dato de entrada hasta orden ejecutada |

---

## ESTADO ACTUAL — DIAGNÓSTICO CONSOLIDADO

### Scores por área (combinados de ambas auditorías)

| Área | Score Técnico | Score Cuantitativo | Prioridad de mejora |
|------|:---:|:---:|:---:|
| Seguridad / Auth | 3.5/10 | — | 🔴 CRÍTICA |
| Pipeline autónomo | 1/10 | — | 🔴 CRÍTICA |
| Persistencia (DB) | 1/10 | — | 🔴 CRÍTICA |
| Ejecución de órdenes | 3/10 | — | 🔴 CRÍTICA |
| Feature Engineering | 6/10 | 3/10 | 🔴 CRÍTICA |
| Validación estadística | 2/10 | 2.5/10 | 🔴 CRÍTICA |
| Gestión de riesgo | 7/10 | 5.5/10 | 🟡 ALTA |
| Modelos ML / IA | 5.5/10 | 4.5/10 | 🟡 ALTA |
| Detección de régimen | 4/10 | 3/10 | 🟡 ALTA |
| Consensus Engine | 5/10 | 4/10 | 🟡 ALTA |
| Testing / cobertura | 5.5/10 | — | 🟡 ALTA |
| Observabilidad | 5/10 | — | 🟠 MEDIA |
| Arquitectura / SOLID | 6.5/10 | — | 🟠 MEDIA |
| Portfolio Intelligence | 4/10 | 3/10 | 🟠 MEDIA |
| Adaptabilidad | — | 3/10 | 🟠 MEDIA |
| DevOps / CI-CD | 5/10 | — | 🟢 BAJA |

### Los 4 blockers absolutos (sistema no opera sin estos)

```
BLOCKER-1: init_pool nunca llamado → toda la data es volátil
BLOCKER-2: APScheduler comentado → no hay trading autónomo
BLOCKER-3: POST /execution falla → Signal/dict mismatch + explanation=None
BLOCKER-4: JWT secret sin validación → tokens forjables por cualquiera
```

### Deuda técnica total estimada: ~136h · Deuda cuantitativa: ~400h adicionales

---

## QUICK WINS — EJECUTAR EN < 1 SEMANA (antes de cualquier fase)

Estos fixes son de **alto impacto, bajo esfuerzo** y desbloquean el trabajo posterior. Ejecutar en orden estricto.

### QW-TECH — Seguridad crítica (máximo 2-4h cada uno)

| ID | Fix | Archivo | Esfuerzo | Impacto |
|----|-----|---------|----------|---------|
| **QWT-1** 🔴 | Eliminar `and False` en JWT validator (`settings.py:106`) | `core/config/settings.py` | 1h | **BLOCKER**: cierra vulnerabilidad de tokens forjables |
| **QWT-2** 🔴 | Fix `explanation=None` → `explanation=[]` en Signal | `api/routes/execution.py` | 2h | **BLOCKER**: desbloquea `POST /execution` (sistema no puede ejecutar órdenes) |
| **QWT-3** 🔴 | Fix `docker-compose.yml` — eliminar líneas 131-153 (bloques duplicados de `grafana:`, `prometheus:`) | `docker/docker-compose.yml` | 1h | Habilita despliegue Docker completo |
| **QWT-4** | Fix `user.get("sub")` → `user.get("user_id")` en 4 archivos | `api/routes/execution.py`, `marketplace.py`, `simulation.py`, `portfolio.py` | 2h | Corrige auditoría y logging de usuario |
| **QWT-5** | Fix `BINANCE_API_SECRET` vs `BINANCE_SECRET_KEY` en CI y Settings | `.github/workflows/ci.yml:56` + `core/config/settings.py` | 1h | Elimina AttributeError al ejecutar seed_data.py |
| **QWT-6** | Aplicar `@limiter.limit()` en endpoints críticos | `/auth/login` (100/min), `/execution` (50/min), `/risk/kill-switch/activate` (10/min) | 4h | Rate limiting real para prevenir DDoS |
| **QWT-7** | Guardar handle de `_refresh_fundamental()` task para cancelación limpia | `api/main.py` lifespan | 1h | Elimina "Task was destroyed but pending" warning en shutdown |
| **QWT-8** | `_load_parquet_data()` → `asyncio.to_thread()` en startup | `api/main.py:215` | 2h | Libera event loop durante carga de datos parquet |
| **QWT-9** | Agregar `Depends(get_current_user)` en todos los endpoints de drawings e indicators | `api/routes/drawings.py`, `api/routes/indicators.py` | 3h | Cierra endpoints públicos sin autenticación |
| **QWT-10** | Refactorizar `validate_signal()` para aceptar `Signal \| dict` o convertir antes de llamar | `core/risk/risk_manager.py` | 4h | Desacopla tipos entre capas (execution vs risk manager) |

**Tiempo total QW-TECH:** ~21h · **Desbloquea: sistema operativo en paper mode sin errores críticos**

### QW-QUANT — Features e indicadores por activo (máximo 1-3 días cada uno)

Prioridad por impacto X factibilidad. **Ejecutar paralelo a QW-TECH.**

#### QW-QUANT — Fase 1 (Features base — 1 semana)

| ID | Feature | Módulo | Symblos | Esfuerzo | Impacto |
|----|---------|--------|---------|----------|---------|
| **QWQ-1** | Retornos lagged (`ret_1, ret_3, ret_6, ret_12, ret_24`) | `core/features/indicators.py` | **Todos** | 1 día | **Muy alto** — base de todo momentum |
| **QWQ-2** | Target ternario con zona muerta (BUY/SELL/HOLD por ATR%) | `core/agents/technical_agent.py` | **Todos** | 1 día | **Muy alto** — reduce ruido target de `sign(ret)` |
| **QWQ-3** | Embargo temporal en validación (5 barras) + purged k-fold | `core/ml/validation.py` | **Todos** | 2 días | **Muy alto** — detecta overfitting inmediatamente |
| **QWQ-4** | ADX (Average Directional Index) como feature | `core/features/indicators.py` | **Todos** (crítico forex + índices) | 0.5 días | **Alto** — filtra señales en mercados laterales |
| **QWQ-5** | Hurst Exponent rolling (100, 250, 500 barras) | `core/features/hurst_engine.py` (existe) | **Todos** | 1 día | **Alto** — distingue tendencia de ruido |

#### QW-QUANT — Fase 2 (Stop-Loss/Take-Profit adaptativos — 1 semana)

| ID | Feature | Por símbolo | Esfuerzo | Impacto |
|----|---------|------------|----------|---------|
| **QWQ-6** | SL/TP dinámicos por **activo y régimen** (MTF_SL_TP_Manager existe) | `core/risk/mtf_sl_tp_manager.py` (existe) | Todos | 1 día | **Alto** — reemplaza multiplicadores ATR fijos (2.0/3.0) |
| **QWQ-7** | Calibración de SL/TP por percentiles históricos ATR | Por asset en `INSTRUMENT_CONFIGS` | Crypto + Forex + Indices + Commodities | 1 día | **Medio-alto** |

Ejemplos de valores calibrados:
```
# CRYPTO (volatile, wide ranges)
BTCUSDT:    ATR_SL_MULT_BASE = 1.5x ATR  → SL = ATR * 1.5
ETHUSDT:    ATR_SL_MULT_BASE = 1.5x ATR

# FOREX MAJORS (tight spreads, less volatile)
EURUSD:     ATR_SL_MULT_BASE = 2.0x ATR  → SL = ATR * 2.0 (1-2 pips)
GBPUSD:     ATR_SL_MULT_BASE = 2.0x ATR

# FOREX CROSSES (wider spreads)
AUDUSD:     ATR_SL_MULT_BASE = 2.5x ATR

# INDICES (moderate volatility)
SPX500:     ATR_SL_MULT_BASE = 2.0x ATR
NAS100:     ATR_SL_MULT_BASE = 2.0x ATR

# COMMODITIES (very volatile)
XAUUSD:     ATR_SL_MULT_BASE = 2.5x ATR
USOIL:      ATR_SL_MULT_BASE = 3.0x ATR
```

#### QW-QUANT — Fase 3 (Gestión de riesgo — 1 semana)

| ID | Feature | Módulo | Esfuerzo | Impacto |
|----|---------|--------|----------|---------|
| **QWQ-8** | Cooldown mínimo 3 barras entre señales del mismo símbolo | `core/signals/signal_engine.py` | 0.5 días | **Medio** — elimina whipsaw |
| **QWQ-9** | Risk exposure real: `\|entry-SL\|*qty / capital` | `core/risk/risk_manager.py` | 0.5 días | **Alto** — mide riesgo real, no nominal |
| **QWQ-10** | Correlación entre posiciones abiertas (no operar si corr > 0.7 con BTC si tengo ETH) | `core/risk/portfolio_risk_engine.py` (existe) | 1 día | **Alto** — evita duplicar riesgo crypto |

#### QW-QUANT — Fase 4 (Validación de modelos — 2 semanas)

| ID | Investigación | Método | Criterio éxito | Timeline |
|----|-----|--------|--------|-------|
| **I1** 🔴 | ¿Existe edge estadístico real después de costos? | Walk-forward con purged k-fold + 1000 bootstraps | Sharpe neto OOS > 0.8, p-value < 0.05 | Semanas 5-6 |
| **I2** | ¿Cuáles features aportan información predictiva? | Permutation importance + SHAP por régimen | Eliminar features con importance ≤ ruido | Semana 5 |
| **I3** | ¿Por símbolo: cuál es el combo óptimo de estrategias? | Backtesting individual + correlation matrix | Mejor combo = no correlacionadas + Sharpe > 0.8 cada una | Semana 6 |

**Tiempo total QW-QUANT:** ~15 días · **Desbloquea: sistema con edge estadístico verificable**

---

### Cronograma Quick Wins (Semana 1)

```
Lunes-Martes (QW-TECH paralelo a QW-QUANT Fase 1):
├── QWT-1,2,3 en paralelo (3h total bloqueante)
├── QWQ-1,2,3 en paralelo (4 días)
└── Tests CI verde: all PRs

Miércoles (QW-TECH Fase 2):
├── QWT-4,5,6 en paralelo (7h)
└── Autenticación funcional

Jueves (QW-TECH Fase 3):
├── QWT-7,8,9,10 en paralelo (10h)
└── `POST /execution` sin errores

Viernes-Siguiente semana (QW-QUANT Fase 2-4):
├── QWQ-6,7,8,9,10 + I1 investigación iniciada
└── Sistema con features mejoradas
```

---

## FASE 0 — FOUNDATION & GOVERNANCE
**Duración:** Semana 1 · **Prioridad:** BLOQUEANTE (paralelo con Quick Wins)

### Objetivo
Establecer cimientos de gobernanza, estructura de repositorio y calidad de código que garanticen que todo el desarrollo posterior sea coherente, auditable y conforme a Clean Architecture.

### Tareas

**A0.1 — Estructura del repositorio (Clean Architecture)**

```
trader_ai/
├── domain/
│   ├── entities/          # Signal, Order, Portfolio, Position
│   ├── value_objects/     # Price, Quantity, RiskLevel, MarketRegime
│   ├── events/            # SignalGenerated, OrderExecuted, KillSwitchTriggered
│   └── exceptions/
├── application/
│   ├── use_cases/         # GenerateSignal, ExecuteOrder, RunBacktest
│   ├── ports/             # IExchangePort, IFeatureStorePort, IModelPort
│   └── services/
├── infrastructure/
│   ├── adapters/          # BinanceAdapter, TimescaleDBAdapter, RedisAdapter
│   ├── repositories/      # MarketDataRepo, OrderRepo, SignalRepo
│   ├── ml_models/         # LightGBMTechnicalModel, HMMRegimeModel
│   └── external/          # TelegramNotifier, PrometheusExporter
├── interfaces/
│   ├── api/               # FastAPI routes (solo orquestación)
│   ├── dashboard/         # HTML/CSS/JS (solo visualización)
│   └── websocket/         # handlers de ingesta y routing
├── core/                  # config, logging, seguridad transversal
├── tests/
│   ├── unit/domain/
│   ├── unit/application/
│   ├── integration/
│   ├── e2e/
│   └── quant/             # tests de validación estadística
└── specs/                 # specs aprobadas por módulo
```

**A0.2 — pyproject.toml con tooling completo**
- black + ruff + mypy (strict en domain y application) + bandit
- Crear `pre-commit` hooks que bloqueen commits con imports circulares

**A0.3 — CI/CD pipeline base**
```yaml
jobs:
  quality: lint → format → type-check → security-scan
  test: unit (--cov ≥80%) → integration
  architecture: dependency direction check → SOLID scan
  backtest_gate: regression backtest → fail si Sharpe OOS < 0.8
```

**A0.4 — Gestión de configuración**
- `.env.example` con todos los valores requeridos documentados
- `core/config/settings.py` con Pydantic Settings v2 y validadores que fallan en startup
- Passwords por defecto eliminados de `docker-compose.yml` (SEC-002/003/004)

**A0.5 — Sistema de specs**
- Crear `specs/SPEC_TEMPLATE.md`
- Specs iniciales para todos los módulos de Fase 1
- Regla: ningún PR sin referencia a spec aprobada

### Criterios de aceptación (Fase 0)
- [ ] `mypy --strict` pasa en `domain/` y `application/`
- [ ] CI pipeline ejecuta sin errores
- [ ] Pre-commit hooks funcionales
- [ ] Todo el equipo puede levantar entorno en < 5 minutos
- [ ] Todos los Quick Wins técnicos (QWT-1 a QWT-10) completados

---

## FASE 1 — SECURE CORE FOUNDATION (ESPECIALIZADA)
**Duración:** Semanas 2-3 · **Prioridad:** CRÍTICO BLOQUEANTE · **~56h estimadas**

### Objetivo
Convertir el sistema de "servidor de consultas roto" a "plataforma de paper trading operativa y segura" con todos los exchanges y activos. Ninguna funcionalidad de trading sin esta base.

### Bloqueantes que resuelve (crítico)

```
BLOCKER-1: init_pool nunca llamado → BD nunca se inicializa → estado volátil
BLOCKER-2: APScheduler comentado → no hay trading autónomo → es un servidor estático
BLOCKER-3: POST /execution falla → Signal/dict type mismatch + explanation=None
BLOCKER-4: JWT sin validación (`and False`) → tokens forjables por cualquiera
BLOCKER-5: 4 workers uvicorn + estado en memoria → race conditions garantizadas
```

### M1.1 — Database + Persistence (Semana 2, Lunes-Martes)

**Tarea específica:** Activar TimescaleDB como fuente de verdad

```python
# Cambios en api/main.py lifespan:

@asyncio.coroutine
async def lifespan(app: FastAPI):
    logger.info("Starting up TRADER AI")
    
    # 1. ACTIVAR POOL DE DB (semana 2, lunes)
    await init_pool(settings.DATABASE_URL)  # ← DESCOMENTAR
    logger.info("Database pool initialized")
    
    # 2. EJECUTAR MIGRACIONES Alembic (semana 2, lunes)
    from alembic.config import Config
    from alembic.runtime.migration import MigrationContext
    from alembic.operations import Operations
    
    async with get_async_engine().begin() as conn:
        await conn.run_sync(migrate_to_head)
    logger.info("Database migrations completed")
    
    yield
    
    logger.info("Shutting down")
```

**Migraciones Alembic a crear:**

```
migrations/versions/
├── 001_create_signals_table.sql
│   └── Columnas: id (PK), idempotency_key (UNIQUE), timestamp, symbol, action, 
│       entry_price, stop_loss, take_profit, confidence, regime, strategy_id, status
│       Indices: (symbol, timestamp), (status, timestamp)
│
├── 002_create_orders_table.sql
│   └── Columnas: id (PK), signal_id (FK), symbol, side, quantity, price, status,
│       fill_price, slippage, commission, created_at, filled_at
│       Indices: (symbol, created_at), (status, created_at)
│
├── 003_create_portfolio_table.sql
│   └── Columnas: id (PK), total_capital, available_capital, realized_pnl, 
│       unrealized_pnl, max_drawdown, timestamp
│       Indices: (timestamp DESC) para queries de performance reciente
│
├── 004_create_audit_log_table.sql
│   └── Columnas: id (PK), action, user_id, resource_type, changes (JSONB),
│       timestamp, ip_address
│       Índices: (user_id, timestamp), (action, timestamp)
│
└── 005_create_timescale_hypertable_signals.sql
    └── SELECT create_hypertable('signals', 'timestamp', 
        if_not_exists => TRUE) — optimiza queries por rango de tiempo
```

**Repositorios a implementar:**

```python
# core/db/repositories/signal_repository.py
class SignalRepository:
    async def create(self, signal: Signal) -> UUID
    async def get_by_id(self, signal_id: UUID) -> Signal | None
    async def get_recent_by_symbol(self, symbol: str, limit: int = 50) -> list[Signal]
    async def update_status(self, signal_id: UUID, status: str) -> bool

# core/db/repositories/order_repository.py
class OrderRepository:
    async def create(self, order: Order) -> UUID
    async def get_by_id(self, order_id: UUID) -> Order | None
    async def get_open_orders(self) -> list[Order]
    async def update_fill(self, order_id: UUID, fill_price: float, commission: float) -> bool

# core/db/repositories/audit_repository.py
class AuditRepository:
    async def log_action(self, action: str, user_id: str, changes: dict) -> None
    async def get_recent_by_action(self, action: str, limit: int = 100) -> list[AuditLog]
```

**Esfuerzo estimado:** 12h (6h migraciones + 6h repositorios)

---

### M1.2 — Auth JWT con validación real (Semana 2, Martes-Miércoles)

**Tareas específicas:**

1. **Eliminar `and False` (QWT-1)** — 1h
   ```python
   # ANTES (core/config/settings.py:106):
   @field_validator("JWT_SECRET_KEY")
   def validate_jwt_secret(cls, v: str) -> str:
       if v == "change-me-in-production" and False:  # ← BUG
           raise ValueError(...)
       return v
   
   # DESPUÉS:
   @field_validator("JWT_SECRET_KEY")
   def validate_jwt_secret(cls, v: str) -> str:
       if v == "change-me-in-production":  # ← SIN and False
           raise ValueError("JWT_SECRET_KEY must be set in production")
       return v
   ```

2. **Token blacklist con Redis** — 4h
   ```python
   # core/auth/token_blacklist.py (crear)
   class TokenBlacklist:
       def __init__(self, redis_client: aioredis.Redis):
           self.redis = redis_client
       
       async def add_to_blacklist(self, token: str, exp_time: int) -> None:
           """Agrega token a blacklist con TTL = tiempo de expiración."""
           key = f"token_blacklist:{token_hash(token)}"
           await self.redis.setex(key, exp_time, "1")
       
       async def is_blacklisted(self, token: str) -> bool:
           key = f"token_blacklist:{token_hash(token)}"
           return await self.redis.exists(key)
   
   # Usar en POST /auth/logout:
   @router.post("/logout")
   async def logout(token: str = Depends(get_current_token)):
       await token_blacklist.add_to_blacklist(token, exp_time=settings.JWT_EXPIRE_MINUTES*60)
       return {"message": "Logged out successfully"}
   ```

3. **POST /auth/register (documentado pero no implementado)** — 3h
   ```python
   @router.post("/auth/register", response_model=dict)
   async def register(
       username: str,
       password: str,
       role: str = "viewer",  # "admin", "trader", "viewer"
   ):
       # Hash password con bcrypt
       hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
       
       # Verificar que solo admin puede crear traders
       if role == "trader":
           current_user = get_current_user()
           if current_user["role"] != "admin":
               raise HTTPException(403, "Only admins can create traders")
       
       # Guardar en DB
       user = await user_repository.create(username, hashed, role)
       return {"user_id": str(user.id), "role": user.role}
   ```

**Esfuerzo estimado:** 8h

---

### M1.3 — Pipeline Autónomo con APScheduler (Semana 2-3, Miércoles-Viernes)

**Tarea crítica:** Reactivar ciclo de trading automático

```python
# api/main.py — lifespan async context manager

_scheduler = None
_pipeline_task = None

@asyncio.coroutine
async def lifespan(app: FastAPI):
    global _scheduler
    
    # ══════════════════════════════════════════════════════════════
    # INICIALIZACIÓN
    # ══════════════════════════════════════════════════════════════
    
    logger.info("🚀 TRADER AI initialization starting")
    
    # Init database
    await init_pool(settings.DATABASE_URL)
    logger.info("✅ Database pool initialized")
    
    # Init singletons
    _order_tracker = OrderTracker()
    _risk_manager = RiskManager(settings)
    _portfolio_manager = PortfolioManager(settings, _risk_manager)
    logger.info("✅ Core managers initialized")
    
    # ══════════════════════════════════════════════════════════════
    # PIPELINE SCHEDULER
    # ══════════════════════════════════════════════════════════════
    
    try:
        _scheduler = AsyncIOScheduler()
        
        # Job 1: Fetch market data cada 1 minuto
        _scheduler.add_job(
            run_data_ingestion,
            "interval",
            minutes=1,
            args=[],
            id="fetch_market_data",
            name="Fetch market data from all exchanges"
        )
        logger.info("✅ Job added: fetch_market_data (1 min interval)")
        
        # Job 2: Calculate features cada 5 minutos
        _scheduler.add_job(
            run_feature_engineering,
            "interval",
            minutes=5,
            args=[],
            id="calculate_features",
            name="Calculate technical + statistical features"
        )
        logger.info("✅ Job added: calculate_features (5 min interval)")
        
        # Job 3: Run agents (Technical, Regime, Microstructure) cada 1 hora
        _scheduler.add_job(
            run_consensus_engine,
            "interval",
            hours=1,
            args=[],
            id="generate_signals",
            name="Run agents → consensus → signal generation"
        )
        logger.info("✅ Job added: generate_signals (1 hour interval)")
        
        # Job 4: Retrain models cada 24 horas (2 AM UTC)
        _scheduler.add_job(
            run_model_retraining,
            "cron",
            hour=2,
            minute=0,
            args=[],
            id="daily_retraining",
            name="Daily model retraining with walk-forward"
        )
        logger.info("✅ Job added: daily_retraining (2 AM UTC)")
        
        # Job 5: Performance tracking cada 4 horas
        _scheduler.add_job(
            run_performance_tracking,
            "interval",
            hours=4,
            args=[],
            id="track_performance",
            name="Track P&L, Sharpe, drawdown metrics"
        )
        logger.info("✅ Job added: track_performance (4 hour interval)")
        
        _scheduler.start()
        logger.info("✅ APScheduler started — trading pipeline is autonomous")
        
    except Exception as e:
        logger.error(f"❌ Scheduler initialization failed: {e}", exc_info=True)
        raise
    
    # ══════════════════════════════════════════════════════════════
    # GRACEFUL SHUTDOWN
    # ══════════════════════════════════════════════════════════════
    
    yield
    
    logger.info("🛑 TRADER AI shutdown starting")
    
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("✅ Scheduler shutdown gracefully")
    
    await close_pool()
    logger.info("✅ Database pool closed")
```

**Funciones del pipeline a implementar:**

```python
# core/pipeline/pipeline_executor.py

async def run_data_ingestion() -> dict:
    """
    Fetch OHLCV data para todos los símbolos desde todos los exchanges.
    Retorna: {"success": N, "failed": M, "timestamp": ...}
    """
    results = {}
    for symbol in settings.SUPPORTED_SYMBOLS:
        asset_class = SYMBOL_ASSET_CLASS[symbol]
        
        if asset_class == "crypto":
            # Usar Binance client
            klines = await binance_client.get_klines(symbol, "1h", limit=500)
            await market_data_store.save(symbol, "1h", klines)
        
        elif asset_class in ["forex", "indices", "commodities"]:
            # Usar OANDA client
            candles = await oanda_client.get_candles(symbol, "H1", count=500)
            await market_data_store.save(symbol, "1h", candles)
    
    logger.info(f"✅ Data ingestion completed: {results}")
    return results

async def run_feature_engineering() -> dict:
    """
    Calcular features para todos los símbolos con las últimas barras.
    """
    from core.features.feature_engineering import calculate_all
    
    results = {}
    for symbol in settings.SUPPORTED_SYMBOLS:
        try:
            df = await market_data_store.load_latest(symbol, "1h", limit=300)
            features = calculate_all(df)
            await feature_store.save(symbol, features)
            results[symbol] = "✅"
        except Exception as e:
            logger.error(f"Feature engineering failed for {symbol}: {e}")
            results[symbol] = f"❌ {str(e)}"
    
    return results

async def run_consensus_engine() -> list[Signal]:
    """
    Ejecutar agents → consensus engine → generar señales.
    """
    signals_generated = []
    
    for symbol in settings.SUPPORTED_SYMBOLS:
        try:
            features = await feature_store.get_latest(symbol)
            regime = await regime_detector.detect(symbol, features)
            
            # Run all agents
            technical_output = technical_agent.generate_signal(features)
            regime_output = regime_agent.generate_signal(regime)
            microstructure_output = microstructure_agent.generate_signal(features)
            
            # Consensus
            consensus_output = voting_engine.aggregate([
                technical_output,
                regime_output,
                microstructure_output,
            ])
            
            # Generate signal
            if consensus_output.signal_allowed and consensus_output.score > SIGNAL_SCORE_THRESHOLD:
                signal = signal_engine.generate(
                    symbol=symbol,
                    action=consensus_output.action,
                    confidence=consensus_output.confidence,
                    explanation=consensus_output.explanation,
                    regime=regime,
                )
                
                # Validate with risk manager
                approved, reason = risk_manager.validate_signal(signal, portfolio=_portfolio_manager)
                
                if approved:
                    # EXECUTE in paper mode
                    order = await paper_executor.execute(signal)
                    _order_tracker.add(order)
                    
                    # Persist
                    await signal_repository.create(signal)
                    await order_repository.create(order)
                    
                    signals_generated.append(signal)
                    logger.info(f"✅ Signal executed: {symbol} {signal.action} @ {signal.entry_price}")
                else:
                    logger.warning(f"⚠️ Signal rejected: {symbol} → {reason}")
        
        except Exception as e:
            logger.error(f"Consensus engine failed for {symbol}: {e}", exc_info=True)
    
    return signals_generated

async def run_model_retraining() -> dict:
    """
    Daily retraining de modelos con walk-forward validation.
    Hora: 2 AM UTC (después de cierre Tokyo + antes de apertura Londres).
    """
    logger.info("🔄 Starting daily model retraining")
    
    results = {}
    for symbol in settings.SUPPORTED_SYMBOLS:
        try:
            # Load latest 2 years of data
            df = await market_data_store.load_full(symbol, "1h", days=730)
            
            # Walk-forward validation
            backtest_result = backtest_engine.run_walk_forward(
                df=df,
                train_window=252*24,  # 1 year
                test_window=30*24,    # 1 month
                embargo_bars=5,
            )
            
            # Check if new model is better
            if backtest_result.sharpe_oos > model_validation_gate.get_current_sharpe(symbol):
                # Train on full data
                new_model = train_lightgbm(df, target="target_ternary")
                
                # Persist
                await model_store.save(symbol, new_model, version=f"v{date.today()}")
                results[symbol] = f"✅ Retrained (Sharpe: {backtest_result.sharpe_oos:.2f})"
            else:
                results[symbol] = "⏭️ Current model still better"
        
        except Exception as e:
            logger.error(f"Retraining failed for {symbol}: {e}")
            results[symbol] = f"❌ {str(e)}"
    
    logger.info(f"✅ Daily retraining completed: {results}")
    return results

async def run_performance_tracking() -> dict:
    """
    Track P&L, Sharpe, drawdown metrics cada 4 horas.
    """
    portfolio = _portfolio_manager.get_current_portfolio()
    
    metrics = {
        "timestamp": datetime.utcnow(),
        "total_capital": portfolio.total_capital,
        "realized_pnl": portfolio.realized_pnl,
        "unrealized_pnl": portfolio.unrealized_pnl,
        "max_drawdown": portfolio.max_drawdown,
        "sharpe_ratio": calculate_sharpe(portfolio),
        "sortino_ratio": calculate_sortino(portfolio),
        "open_positions": len(portfolio.open_positions),
    }
    
    # Persist to DB
    await portfolio_repository.log_metrics(metrics)
    
    # Send alert if thresholds breached
    if portfolio.max_drawdown > settings.MAX_DRAWDOWN_PCT:
        await alert_engine.send_telegram(
            f"⚠️ ALERT: Drawdown reached {portfolio.max_drawdown:.1%}!"
        )
    
    logger.info(f"✅ Performance tracked: P&L={metrics['realized_pnl']:.2f} Sharpe={metrics['sharpe_ratio']:.2f}")
    return metrics
```

**Esfuerzo estimado:** 16h

---

### M1.4 — Paper Executor multisimbol y multi-exchange (Semana 3, Lunes-Martes)

**Tarea específica:** Simular fills realistas para todos los activos

```python
# core/execution/paper_executor.py

class PaperExecutor(BaseExecutor):
    """
    Simula ejecución de órdenes con:
    - Comisión configurable por asset class
    - Slippage por régimen de mercado
    - Latencia realista (50-200ms)
    - Fill prices realistas (no rellena en precios imposibles)
    """
    
    def __init__(self, settings: Settings):
        self.cost_model = {
            AssetClass.CRYPTO: {
                "commission": 0.001,      # 0.1% Binance
                "slippage": 0.0005,       # 0.05%
                "latency_ms": (50, 200),
            },
            AssetClass.FOREX: {
                "commission": 0.0,        # sin comisión, incluido en spread
                "slippage": 0.0001,       # 1 pips spread
                "latency_ms": (100, 300),
            },
            AssetClass.INDICES: {
                "commission": 0.0002,     # 0.02%
                "slippage": 0.0002,       # 2 pips
                "latency_ms": (80, 250),
            },
            AssetClass.COMMODITIES: {
                "commission": 0.0003,     # 0.03%
                "slippage": 0.0003,       # 3 pips
                "latency_ms": (100, 300),
            },
        }
    
    async def execute(self, signal: Signal) -> Order:
        """
        Ejecutar orden en paper mode con simulación realista.
        """
        asset_class = SYMBOL_ASSET_CLASS[signal.symbol]
        cost = self.cost_model[asset_class]
        
        # 1. Simular latencia
        latency_ms = random.uniform(*cost["latency_ms"])
        await asyncio.sleep(latency_ms / 1000)
        
        # 2. Calcular fill price con slippage
        base_price = signal.entry_price
        slippage_pct = cost["slippage"]
        
        if signal.action == "BUY":
            fill_price = base_price * (1 + slippage_pct)  # compro más caro
        else:  # SELL
            fill_price = base_price * (1 - slippage_pct)  # vendo más barato
        
        # 3. Calcular comisión
        commission = abs(signal.quantity * fill_price * cost["commission"])
        
        # 4. Crear orden
        order = Order(
            signal_id=signal.id,
            symbol=signal.symbol,
            side=signal.action,
            quantity=signal.quantity,
            price=signal.entry_price,
            status="filled",
            fill_price=fill_price,
            slippage=(fill_price - base_price) / base_price,
            commission=commission,
            filled_at=datetime.utcnow(),
        )
        
        logger.info(f"📊 Paper execution: {signal.symbol} {signal.action} "
                    f"@ {fill_price:.5f} (entry: {base_price:.5f}, slippage: {order.slippage:.4%})")
        
        return order
```

**Configuración por asset:**

```python
# Actualizar core/config/constants.py

PAPER_SLIPPAGE_BY_ASSET = {
    # Crypto: volatile, wide spreads
    "BTCUSDT": {"slippage": 0.001, "commission": 0.001},    # 0.1% + 0.1%
    "ETHUSDT": {"slippage": 0.001, "commission": 0.001},
    "SOLUSDT": {"slippage": 0.002, "commission": 0.001},    # menos líquido
    "BNBUSDT": {"slippage": 0.0015, "commission": 0.001},
    
    # Forex majors: tight spreads
    "EURUSD": {"slippage": 0.00005, "commission": 0.0},     # 0.5 pips
    "GBPUSD": {"slippage": 0.00008, "commission": 0.0},     # 0.8 pips
    "USDJPY": {"slippage": 0.0006, "commission": 0.0},      # 0.6 pips (más grande)
    "AUDUSD": {"slippage": 0.0008, "commission": 0.0},
    
    # Indices
    "SPX500": {"slippage": 0.0002, "commission": 0.0002},
    "NAS100": {"slippage": 0.0003, "commission": 0.0002},
    
    # Commodities: volatile
    "XAUUSD": {"slippage": 0.0002, "commission": 0.0003},
    "USOIL": {"slippage": 0.001, "commission": 0.0004},
}
```

**Esfuerzo estimado:** 8h

---

### M1.5 — Redis para estado distribuido (Semana 3, Miércoles-Viernes)

**Tarea crítica:** Evitar race conditions entre múltiples workers

```python
# core/risk/kill_switch_redis.py

class KillSwitchRedis:
    """Kill switch persistente en Redis, no en memoria."""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.state_key = "kill_switch:state"
        self.reason_key = "kill_switch:reason"
        self.timestamp_key = "kill_switch:timestamp"
    
    async def is_active(self) -> bool:
        """Consultar estado actual del kill switch."""
        state = await self.redis.get(self.state_key)
        return state == b"active"
    
    async def activate(self, reason: str = "Manual activation") -> None:
        """Activar kill switch con razón."""
        await self.redis.mset({
            self.state_key: "active",
            self.reason_key: reason,
            self.timestamp_key: datetime.utcnow().isoformat(),
        })
        logger.critical(f"🛑 KILL SWITCH ACTIVATED: {reason}")
        await alert_engine.send_telegram(f"🛑 KILL SWITCH ACTIVATED: {reason}")
    
    async def deactivate(self) -> None:
        """Desactivar kill switch."""
        await self.redis.delete(self.state_key, self.reason_key, self.timestamp_key)
        logger.info("✅ Kill switch deactivated")
    
    async def get_reason(self) -> str | None:
        """Obtener razón de activación."""
        reason = await self.redis.get(self.reason_key)
        return reason.decode() if reason else None
```

**Esfuerzo estimado:** 8h

---

### Criterios de aceptación (Fase 1)

- [ ] `POST /execution` completa sin errores (QWT-2)
- [ ] JWT validación funcional y logout efectivo (QWT-1)
- [ ] Sistema ejecuta ciclo de trading autónomamente en paper mode (APScheduler)
- [ ] Señales y órdenes persisten en TimescaleDB
- [ ] Kill switch activo y verificado bajo carga concurrente (Redis)
- [ ] 0 race conditions: estado consistente entre múltiples workers
- [ ] Backtesting de señales generadas vs S&P500 benchmark
- [ ] All tests CI verde para Fase 1

---

## FASE 2 — DATA & QUANT INFRASTRUCTURE
**Duración:** Semanas 4-6 · **Prioridad:** CRÍTICA · **~90h estimadas**

### Objetivo
Construir la infraestructura de datos y validación estadística que es prerequisito para cualquier modelo con edge real. Sin esta fase, los modelos entrenan y validan sobre datos incorrectos.

### Problemas que resuelve
- CRÍTICO-Q1: Backtesting con sesgo look-ahead (features con datos futuros)
- CRÍTICO-Q2: Sin costos de transacción en backtesting
- CRÍTICO-Q3: Sin validación out-of-sample real
- QWQ-1 a QWQ-10: todos los quick wins cuantitativos formalizados

### Módulos a implementar

**M2.1 — Feature Engineering V2**

Features P0 (implementar primero, impacto máximo):
```python
# Retornos lagged — los predictores más básicos en quant
ret_1, ret_3, ret_6, ret_12, ret_24 = returns sobre N barras anteriores
vol_adj_ret = ret_1 / atr_14  # retorno normalizado por volatilidad

# Estadísticos rolling
rolling_sharpe_20, rolling_sharpe_50, rolling_sharpe_100
adx_14  # fuerza de tendencia independiente de dirección
bb_pct_b, bb_bandwidth  # complementan bb_width existente
```

Features P1 (semana 5-6):
```python
# Estadísticos avanzados
hurst_exponent_rolling  # distingue tendencia de ruido
rolling_skewness, rolling_kurtosis  # asimetría y tail risk
autocorr_lag1_to_lag5  # detecta momentum / mean-reversion
z_score_vs_vwap  # señal de reversión vs VWAP real

# Temporales (críticos para forex)
hour_sin, hour_cos   # features cíclicas de hora del día
day_of_week_sin, day_of_week_cos
is_london_session, is_new_york_session, is_overlap

# Volatilidad
volatility_regime_persistence  # clustering de vol
```

Fix obligatorio:
- VWAP real con reset diario (no SMA ponderada de 20 períodos)
- OBV vectorizado con numpy (eliminar loop Python O(n))
- `volatility_regime` con quantiles rolling (no sobre todo el dataset → look-ahead)
- `trend_direction` con fuerza numérica, no solo categórico

**M2.2 — Feature Store versionado**
```python
class FeatureStore:
    """
    - Hash de configuración de features (versión inmutable)
    - Detección de drift: KL-divergence entre distribuciones
    - Validación de calidad: NaN count, outliers, rango esperado
    - Versionado: cada modelo referencia el hash de features con el que fue entrenado
    """
```

**M2.3 — Validación estadística rigurosa**

```python
class PurgedKFold:
    """Purged K-Fold con embargo temporal."""
    embargo_bars: int = 5  # mínimo 5 barras entre train y test
    n_splits: int = 5
    
    def split(self, X, y, groups=None):
        # Eliminar samples del gap train/test (purging)
        # Aplicar embargo temporal entre folds
        ...

class WalkForwardValidator:
    """Walk-forward con reentrenamiento en cada ventana."""
    train_window: int = 252 * 24  # 1 año en 1h para crypto
    test_window: int = 30 * 24   # 1 mes en 1h
    step_size: int = 7 * 24      # paso de 1 semana
    
    def validate(self, model, X, y):
        # ENTRENA el modelo en train_window
        # EVALÚA en test_window sin data leakage
        # REGISTRA Sharpe OOS por ventana
        ...
```

**M2.4 — Backtesting V2 con costos reales**

```python
class CostModel:
    commission_pct: float        # 0.001 Binance, 0.0 con spread en forex
    spread_pct: float            # 0.0001 EURUSD, 0.001 BTCUSDT
    slippage_pct: float          # 0.0005 estimado
    funding_rate: float = 0.0   # solo crypto perpetuos
    
    def total_cost(self, trade_value: float) -> float:
        return trade_value * (self.commission_pct + self.spread_pct + self.slippage_pct)
```

Métricas correctas a implementar:
- Sharpe con `sqrt(periods_per_year)` dinámico según timeframe
- Sortino ratio con downside deviation
- Omega ratio
- Calmar ratio con annualization correcta
- Max drawdown + duración del drawdown + recovery time
- Bootstrap de 1000 permutaciones → p-value de cada métrica

**M2.5 — Target mejorado para modelos ML**

```python
def build_target(df: pd.DataFrame, forward_bars: int = 6) -> pd.Series:
    """
    Target ternario con zona muerta calibrada por volatilidad del activo.
    
    BUY  si ret_forward > ATR_pct * threshold
    SELL si ret_forward < -ATR_pct * threshold
    HOLD si dentro de la zona muerta
    
    threshold = percentil 30 de |returns| históricos del activo
    """
    atr_pct = df['atr_14'] / df['close']
    threshold = (df['close'].pct_change().abs()).rolling(252).quantile(0.30)
    forward_ret = df['close'].pct_change(forward_bars).shift(-forward_bars)
    
    target = np.where(forward_ret > atr_pct * threshold, 1,
             np.where(forward_ret < -atr_pct * threshold, -1, 0))
    return pd.Series(target, index=df.index, name='target')
```

**M2.6 — WebSocket streaming al frontend**
- Conectar WebSocket a FastAPI (actualmente no montado)
- Streaming de precios en tiempo real al dashboard
- Reconexión automática con exponential backoff

### Criterios de aceptación (Fase 2)
- [ ] `calculate_all()` produce 35+ features sin look-ahead bias
- [ ] VWAP real con reset diario verificado
- [ ] `PurgedKFold` con embargo de 5 barras pasa en CI
- [ ] Walk-forward reentrena el modelo en cada ventana (verificado con logs)
- [ ] Backtesting incluye costos de transacción reales
- [ ] Sharpe calculado con `sqrt(periods_per_year)` correcto
- [ ] Feature Store versiona y detecta drift automáticamente
- [ ] I1 — Investigación de edge real iniciada (¿Sharpe neto > 0 después de costos?)

---

## FASE 3 — QUANTITATIVE INTELLIGENCE
**Duración:** Semanas 7-9 · **Prioridad:** ALTA · **~116h estimadas**

### Objetivo
Elevar la calidad de los modelos ML, la detección de régimen y el consensus engine al nivel necesario para generar señales con edge estadístico verificable.

### Problemas que resuelve
- Overfitting silencioso (LightGBM sin validación temporal)
- Pesos estáticos del consensus engine
- Detección de régimen rule-based simplista
- Sin mecanismo de "no operar"

### Módulos a implementar

**M3.1 — Modelos ML mejorados**

```python
class ImprovedTechnicalAgent:
    """
    LightGBM con validación rigurosa:
    - Purged K-Fold con embargo de 5-10 barras
    - Bayesian hyperparameter search (Optuna)
    - Early stopping basado en Sharpe OOS, no accuracy
    - Feature importance via SHAP en cada reentrenamiento
    - Curvas de complejidad para detectar punto óptimo de n_estimators
    """
    
    target_metric: str = "sharpe_oos"  # no accuracy, no log-loss
    min_sharpe_to_deploy: float = 0.8  # no deploy si no supera esto
```

Investigaciones a ejecutar en paralelo:
- **I2**: Feature importance real con permutation importance + SHAP por régimen
- **I3**: Complejidad óptima de LightGBM (curvas n_estimators vs Sharpe OOS)
- **I4**: Rendimiento por régimen de mercado (en qué regímenes el sistema destruye valor)

**M3.2 — Model Validation Gate**

```python
class ModelValidationGate:
    """
    Antes de desplegar un modelo reentrenado:
    1. Comparar Sharpe OOS con modelo actual
    2. Solo reemplazar si Sharpe_nuevo ≥ Sharpe_actual * 1.10 (mejora ≥10%)
    3. Comparar distribución de predicciones (no todas iguales → error)
    4. Verificar que max drawdown OOS < 20%
    5. Registrar decisión en audit log con métricas comparativas
    """
```

**M3.3 — Detección de régimen V2 (HMM real)**

```python
class HMMRegimeDetector:
    """
    Hidden Markov Model con 6-8 estados entrenado con Baum-Welch.
    
    Estados (expandir de 5 a 8):
    1. BULL_TRENDING_STRONG    → Full momentum, max exposure
    2. BULL_TRENDING_WEAK      → Momentum con trailing tight
    3. BEAR_TRENDING_STRONG    → Short momentum o cash
    4. BEAR_TRENDING_WEAK      → Hedged positions
    5. RANGE_BOUND_NARROW      → Mean reversion, grid trading
    6. RANGE_BOUND_WIDE        → Breakout anticipation
    7. TRANSITION              → Reducir exposición, observar
    8. CRISIS                  → Cash only, hedge total
    
    Features del HMM: returns, volatility, ADX, Hurst, volume ratio
    Reentrenamiento: cada 30 días con datos de 1-2 años
    """
    
    def should_trade(self, regime: MarketRegime) -> bool:
        """Gate obligatorio: el régimen puede prohibir operar."""
        return regime not in {MarketRegime.CRISIS, MarketRegime.TRANSITION}
```

**M3.4 — Consensus Engine V2 (pesos dinámicos)**

```python
class DynamicConsensusEngine:
    """
    Pesos de agentes ajustados automáticamente:
    - EWMA de accuracy de cada agente (ventana: últimos 50 trades)
    - Normalización para que los pesos sumen 1.0
    - Peso mínimo: 0.05 (ningún agente eliminado completamente)
    - Peso máximo: 0.60 (ningún agente dominante)
    - Agreement ponderado por magnitud del score (no binario)
    - Default weight para agentes nuevos: 0.0 (no 0.10 — eliminar ruido)
    - Alpha decay tracking: alertar si consensus_sharpe rolling cae > 20%
    """
```

**M3.5 — Hurst Exponent como feature y selector de estrategia**

```python
class HurstEngine:
    """
    Hurst Exponent rolling por activo:
    - H > 0.55 → trending → activar momentum strategies
    - H < 0.45 → mean-reverting → activar mean reversion strategies
    - 0.45 ≤ H ≤ 0.55 → random walk → reducir exposición
    
    Ventanas: 100, 250, 500 barras (consenso de tres ventanas)
    """
```

**M3.6 — Observabilidad avanzada**
- Grafana dashboards: P&L, signals, risk, latencia de pipeline
- Alertas operacionales con thresholds configurables (Telegram)
- SHAP completo en todos los agentes IA (no solo `# TODO`)
- Decision tracer: log de cada decisión desde dato → orden

### Criterios de aceptación (Fase 3)
- [ ] HMM con 8 estados entrenado y reemplaza reglas if/else
- [ ] `ModelValidationGate` activo: ningún modelo peor entra a producción
- [ ] Consensus weights dinámicos verificados con historial de 100+ trades
- [ ] I1 completada: ¿existe edge estadístico real? (Sharpe neto OOS > 0)
- [ ] I2, I3, I4 completadas (feature importance, complejidad óptima, rendimiento por régimen)
- [ ] Grafana dashboards operativos con alertas configuradas

---

## FASE 4 — STRATEGY INTELLIGENCE SYSTEM
**Duración:** Semanas 10-12 · **Prioridad:** ALTA · **~120h estimadas**

### Prerrequisito
Fase 3 completada Y I1 demuestra Sharpe neto OOS > 0.8. **No avanzar a Fase 4 si el sistema actual no tiene edge real.**

### Objetivo
Implementar un portfolio de estrategias diversificadas con un meta-agente que selecciona la mejor estrategia para cada condición de mercado.

### Nuevas estrategias (por prioridad)

| Estrategia | Activos | Régimen óptimo | Complejidad | Prioridad |
|-----------|---------|---------------|-------------|-----------|
| **Time-Series Momentum (TSMOM)** | Todos | Trending persistente | Baja | P1 |
| **Cross-Sectional Momentum** | Crypto (BTC/ETH/SOL/BNB) | Bull/Bear trending | Media | P1 |
| **Volatility Breakout Adaptive** | Crypto, Commodities | Post-consolidación | Media | P1 |
| **Statistical Arbitrage (Z-Score)** | Forex pairs correlacionados | Sideways, mean-reverting | Media | P2 |
| **VWAP Reversion Intradía** | Índices, Forex | Sideways, rango definido | Baja | P2 |
| **Pairs Trading Crypto** | BTC/ETH, SOL/ETH, BNB/ETH | Cualquiera | Media | P2 |

### Módulos a implementar

**M4.1 — Strategy Registry y Framework**

```python
class StrategyInterface(ABC):
    """Contrato obligatorio para toda estrategia."""
    
    @abstractmethod
    def generate_signal(self, features: FeatureSet, regime: MarketRegime) -> Signal | None:
        ...
    
    @abstractmethod
    def get_required_features(self) -> list[str]:
        """Features que necesita esta estrategia."""
        ...
    
    @abstractmethod
    def get_optimal_regimes(self) -> list[MarketRegime]:
        """Regímenes donde esta estrategia tiene edge."""
        ...
    
    @property
    @abstractmethod
    def min_sharpe_to_activate(self) -> float:
        """Sharpe OOS mínimo para que esta estrategia esté activa."""
        ...
```

**M4.2 — Meta-Agente Selector**

```python
class MetaAgentOrchestrator:
    """
    ML model que dado el estado actual del mercado selecciona:
    - best_strategy: qué estrategia activar
    - best_model: qué modelo usar para esa estrategia
    - risk_multiplier: escalar el riesgo (0.5 a 1.0)
    - should_trade: puede decidir NO operar
    - confidence: confianza en la selección (0 a 1)
    
    Features del meta-modelo:
    - Régimen actual (HMM state probabilities)
    - Volatilidad realizada (20d, 60d)
    - Hurst exponent actual
    - Hora del día, día de la semana
    - Performance reciente de cada sub-modelo (rolling Sharpe 20 trades)
    - Correlación cross-asset (últimas 20 barras)
    
    Target: qué estrategia/modelo tuvo mejor Sharpe en las próximas 24 barras
    Validación: purged k-fold con embargo de 10 barras
    """
```

**M4.3 — Strategy Rotation Engine**

```python
class StrategyRotationEngine:
    """
    Desactiva estrategias con Sharpe rolling < 0.5 (ventana: 30 trades).
    Reactiva cuando el régimen de mercado es óptimo para esa estrategia.
    Registro en audit log de cada activación/desactivación.
    """
    
    min_sharpe_rolling: float = 0.5    # umbral de desactivación
    reactivation_regime_match: bool = True  # requiere régimen óptimo
```

**M4.4 — Portfolio Optimizer**

```python
class PortfolioOptimizer:
    """
    Optimización de allocation entre estrategias activas:
    - Risk Parity: igual contribución al riesgo total
    - Kelly fraction half-Kelly por estrategia
    - Correlación entre estrategias: matrix de 30 barras rolling
    - Anti-correlation guard: reducir tamaño si corr > 0.7 entre posiciones
    - Concentration limit: ninguna estrategia > 40% del capital
    """
```

**M4.5 — A/B Testing Framework para modelos**

```python
class ABTestingFramework:
    """
    Shadow mode: modelo candidato corre en paralelo sin ejecutar órdenes.
    Comparación estadística: Mann-Whitney U test de Sharpe OOS.
    Criterio de graduación: p-value < 0.05 + mejora ≥ 10% en Sharpe.
    Duración mínima del shadow test: 100 predicciones.
    """
```

**M4.6 — Multi-timeframe features**
- Modelos que consumen features de 1h + 4h + 1D simultáneamente
- Feature alignment: resample y merge sin look-ahead

### Criterios de aceptación (Fase 4)
- [ ] Al menos 3 estrategias P1 implementadas con backtesting completo
- [ ] Meta-agente con Sharpe OOS > 0.8 vs estrategia individual mejor
- [ ] Strategy rotation desactiva estrategias perdedoras automáticamente
- [ ] A/B framework activo para candidatos de modelo
- [ ] Portfolio optimizer con risk parity verificado matemáticamente

---

## FASE 5 — ADVANCED RISK INTELLIGENCE
**Duración:** Semanas 13-15 · **Prioridad:** ALTA · **~100h estimadas**

### Objetivo
Implementar Risk Engine 2.0 con CVaR, volatility targeting, correlación entre posiciones, y tail risk protection. El sistema actual tiene gestión de riesgo básica (5.5/10 técnico, 5.5/10 cuantitativo).

### Módulos a implementar

**M5.1 — Risk Engine 2.0 — Arquitectura**

```
┌─────────────────────┐
│   Meta Risk Engine   │ (orquesta y agrega señales de riesgo)
└─────────┬───────────┘
┌──────────┐   ┌──────────┐   ┌──────────┐
│ Position │   │Portfolio │   │Systemic  │
│  Risk    │   │  Risk    │   │  Risk    │
│          │   │          │   │          │
│ ATR-SL   │   │ Correl.  │   │ VIX mon. │
│ Vol tgt  │   │ CVaR 95% │   │ Liquidity│
│ Dynamic  │   │ Concent. │   │ Cross-mkt│
│  R:R     │   │ Sector   │   │ BlkSwn   │
└──────────┘   └──────────┘   └──────────┘
```

**M5.2 — Adaptive Position Risk (SL/TP dinámico)**

```python
class AdaptivePositionRisk:
    ATR_MULTIPLIERS = {
        MarketRegime.BULL_TRENDING_STRONG: 1.5,
        MarketRegime.BEAR_TRENDING_STRONG: 2.0,
        MarketRegime.RANGE_BOUND_NARROW:   1.0,
        MarketRegime.RANGE_BOUND_WIDE:     2.0,
        MarketRegime.VOLATILE_CRASH:       3.0,
        MarketRegime.TRANSITION:           2.5,
    }
    
    def calculate_dynamic_sl(self, atr, regime, profile) -> float:
        mult = self.ATR_MULTIPLIERS[regime] * profile.risk_multiplier
        return atr * mult
    
    def calculate_dynamic_tp(self, atr, regime, model_confidence) -> float:
        """TP proporcional al R:R mínimo del perfil y confianza del modelo."""
        min_rr = 1.5 if model_confidence < 0.7 else 2.0
        return self.calculate_dynamic_sl(...) * min_rr
```

**M5.3 — Volatility Targeting**

```python
class VolatilityTargetingEngine:
    target_annual_vol: float = 0.10  # 10% anualizada

    def scale_factor(self, realized_vol_20d: float) -> float:
        if realized_vol_20d <= 0:
            return 1.0
        ratio = self.target_annual_vol / realized_vol_20d
        return np.clip(ratio, 0.20, 2.0)  # entre 20% y 200% del tamaño base
```

**M5.4 — Portfolio Risk (CVaR + correlaciones)**

```python
class PortfolioRiskEngine:
    def calculate_cvar(self, returns: pd.Series, alpha: float = 0.05) -> float:
        """CVaR al 95%: pérdida esperada en el 5% peor de los casos."""
        var = returns.quantile(alpha)
        return returns[returns <= var].mean()
    
    def correlation_adjusted_size(self, new_symbol, existing_positions) -> float:
        """Reduce tamaño si correlación rolling > 0.7 con posiciones existentes."""
        max_corr = max(
            self._rolling_correlation(new_symbol, pos.symbol, window=20)
            for pos in existing_positions
        ) if existing_positions else 0.0
        return max(0.3, 1.0 - max_corr * 0.7)  # reduce hasta 30% por correlación
    
    def max_portfolio_exposure(self, vol_regime, regime) -> float:
        """Exposure inversamente proporcional al riesgo sistémico."""
        vol_factor = {"low": 1.0, "medium": 0.8, "high": 0.5, "extreme": 0.2}
        regime_factor = {
            MarketRegime.BULL_TRENDING_STRONG: 1.0,
            MarketRegime.RANGE_BOUND_NARROW:   0.7,
            MarketRegime.BEAR_TRENDING_STRONG: 0.5,
            MarketRegime.CRISIS:               0.1,
        }
        return 0.80 * vol_factor[vol_regime] * regime_factor.get(regime, 0.5)
```

**M5.5 — Adaptación automática al mercado**

| Condición | Respuesta automática |
|-----------|---------------------|
| Volatilidad > P90 | Reducir position size 50%, SL multiplier 3x ATR, desactivar mean reversion |
| Volatilidad < P10 | Activar range trading, reducir TP targets, buscar breakout setups |
| ADX > 30 | Activar momentum, desactivar mean reversion, trailing stops |
| Hurst < 0.40 | Activar mean reversion, z-score strategies, VWAP reversion |
| Drawdown > 5% en 4h | Kill switch parcial, cerrar posiciones riesgosas |
| Baja liquidez (Asian session) | Reducir tamaño 70%, spreads más amplios en cost model |
| Correlación cross-asset alta | Reducir exposición total, diversificar timeframes |

**M5.6 — User Profile Engine**

```python
@dataclass
class TradingProfile:
    risk_per_trade: float     # 0.005 (conservative) a 0.02 (aggressive)
    max_drawdown: float       # 0.05 a 0.25
    min_rr_ratio: float       # 1.0 a 2.5
    min_confidence: float     # 0.45 a 0.75
    max_signals_per_day: int  # 1 a 30
    
PROFILES = {
    "scalper":    TradingProfile(0.005, 0.05, 1.0, 0.60, 30),
    "day_trader": TradingProfile(0.010, 0.08, 1.5, 0.55, 8),
    "swing":      TradingProfile(0.015, 0.12, 2.0, 0.60, 3),
    "position":   TradingProfile(0.020, 0.20, 2.5, 0.70, 1),
    "conservative": TradingProfile(0.005, 0.05, 2.5, 0.75, 3),
}
```

### Criterios de aceptación (Fase 5)
- [ ] CVaR 95% calculado y monitoreado por posición y portfolio
- [ ] Volatility targeting verificado: exposure escala inversamente a vol realizada
- [ ] Correlación entre posiciones verificada: si corr > 0.7 se reduce tamaño
- [ ] SL/TP dinámico por régimen activo y verificado en backtesting
- [ ] User Profile Engine con 5 perfiles configurables
- [ ] Adaptación automática al mercado activa (7 condiciones del cuadro)

---

## FASE 6 — AI ADAPTIVE ECOSYSTEM
**Duración:** Semanas 16-19 · **Prioridad:** MEDIA · **~150h estimadas**

### Prerrequisito
Fases 1-5 completadas. I1 demuestra Sharpe neto OOS > 1.0.

### Objetivo
Sistema que se adapta continuamente al mercado sin intervención humana. Incluye online learning, detección de concept drift, y los primeros componentes de RL.

### Módulos a implementar

**M6.1 — Online Learning (River)**

```python
class OnlineLearningAgent:
    """
    Modelo incremental que se actualiza con cada nueva barra.
    No requiere reentrenamiento completo.
    
    Framework: River (ex scikit-multiflow)
    Modelos: AMFClassifier (adaptive random forest) + HoeffdingTreeClassifier
    Benchmark vs: LightGBM batch (reentrenado cada 100 barras)
    
    Criterio de adopción: River mantiene ≥ 80% del Sharpe de LightGBM
    con latencia de actualización < 50ms por barra.
    """
```

**M6.2 — Concept Drift Detection**

```python
class DriftDetector:
    """
    Monitorea:
    1. Feature drift: KL-divergence entre distribución actual vs training set
       Alerta si KL > umbral (configurable, típicamente 0.1)
    2. Performance decay: Sharpe rolling cae > 30% vs baseline
    3. Regime change: HMM detecta transición a estado no visto en training
    4. Prediction distribution: predicciones todas iguales → error silencioso
    
    Respuesta automática:
    - Leve: aumentar peso de online learning vs batch
    - Moderado: trigger de reentrenamiento urgente
    - Grave: desactivar modelos afectados, activar fallback rule-based
    """
```

**M6.3 — Reinforcement Learning Agent (base)**

```python
class RLTradingAgent:
    """
    Algoritmo: PPO (Proximal Policy Optimization) con curiosity-driven exploration
    
    State: [features mercado, estado portfolio, performance reciente]
    Action: {hold, buy_small, buy_large, sell_small, sell_large, close_all}
    Reward: Sharpe ratio diferencial (evita inactividad)
    
    Entrenamiento: simulación con datos históricos + perturbaciones sintéticas
    Deployment: shadow mode primero (100+ episodios de evaluación)
    
    NO deploy a live sin: Sharpe OOS > 1.2 + Max DD < 15% en 10 episodios
    """
```

**M6.4 — Stress Testing Engine**

```python
class StressTestEngine:
    """
    Escenarios históricos:
    - COVID crash (Marzo 2020): BTC -50% en 2 días
    - Crypto winter (Nov 2022-Ene 2023): BTC -75% en 60 días
    - Flash crash genérico: -20% en 1 hora
    - EURUSD SNB (Enero 2015): 15% en 1 minuto
    
    Escenarios sintéticos (Monte Carlo con fat tails):
    - t-distribution con df=3 (fat tails extremos)
    - Volatility clustering (GARCH simulado)
    - Correlation breakdown (crisis → todos los activos caen juntos)
    
    Criterio de aceptación: sistema sobrevive todos los escenarios con
    drawdown < 25% y kill switch activo antes de -30%.
    """
```

**M6.5 — Alpha Decay Monitor**

```python
class AlphaDecayMonitor:
    """
    Tracking automático de degradación de alpha por estrategia:
    - Sharpe rolling (ventana: últimos 50 trades)
    - Alerta si Sharpe rolling < 0.5 (umbral configurable)
    - Alerta si win_rate cae > 10% vs baseline
    - Desactivación automática si Sharpe rolling < 0 por 20 trades consecutivos
    - Reactivación: solo si régimen de mercado cambia Y backtest reciente > umbral
    """
```

### Criterios de aceptación (Fase 6)
- [ ] Online learning (River) con Sharpe ≥ 80% del batch LightGBM
- [ ] Drift detector activo: alertas verificadas en datos históricos conocidos
- [ ] RL agent en shadow mode con > 500 episodios evaluados
- [ ] Stress testing: sistema sobrevive 5 escenarios históricos con DD < 25%
- [ ] Alpha decay monitor activo con alertas en Telegram

---

## FASE 7 — PRODUCTION GRADE PLATFORM
**Duración:** Semanas 20-24 · **Prioridad:** MEDIA-ALTA · **~156h estimadas**

### Prerrequisito
Fases 1-6 completadas. Paper trading operativo con Sharpe OOS > 1.0 durante mínimo 60 días consecutivos. Revisión legal/regulatoria completada.

### Objetivo
Sistema apto para capital real limitado bajo supervisión continua. Integración real con exchanges, infraestructura enterprise, y operación continua 24/7.

### Módulos a implementar

**M7.1 — Integración real Binance (crypto live)**
- Conexión real verificada con capital < 1% del total como prueba
- Order routing inteligente (market vs limit según liquidez)
- TWAP/VWAP execution para órdenes grandes
- Monitoring de fill quality y slippage real vs estimado

**M7.2 — Integración real OANDA (forex/CFD)**
- Conexión verificada con capital mínimo
- Gestión de rollover/swap costs en posiciones overnight
- Margin management para CFDs

**M7.3 — Infraestructura enterprise**
- Celery + Redis Queue para pipeline async con retry
- HashiCorp Vault para gestión de secrets
- Disaster recovery y backup automatizado de DB (TimescaleDB continuous aggregate)
- Multi-exchange execution routing con fallback

**M7.4 — Observabilidad enterprise**
- Grafana dashboards productivos (P&L, signals, latencia, risk metrics)
- Alertas PagerDuty-style para eventos críticos (kill switch, drawdown > 5%)
- Distributed tracing (OpenTelemetry)
- SLA monitoring: latencia pipeline < 500ms en P95

**M7.5 — Compliance y auditoría**
- Audit log completo (inmutable): toda decisión de trading trazable
- Reportes automáticos de P&L por estrategia, activo y período
- Export para contabilidad/impuestos

### Criterios de aceptación (Fase 7)
- [ ] Paper trading con Sharpe OOS > 1.0 durante 60+ días verificado
- [ ] Integración Binance real funcional con capital de prueba
- [ ] Latencia pipeline P95 < 500ms verificada bajo carga
- [ ] Disaster recovery probado: sistema recuperado en < 15 minutos
- [ ] Kill switch probado en live: corta todas las posiciones en < 30 segundos

---

## QUALITY GATES OBLIGATORIOS (todas las fases)

| Gate | Criterio | Alcance |
|------|----------|---------|
| QG-1 | Cobertura de tests ≥ 80% en módulos core (risk, execution, signals) | Cada fase |
| QG-2 | Zero errores mypy en módulos domain y application | Cada fase |
| QG-3 | Ningún módulo domain importa infraestructura | Permanente |
| QG-4 | Kill switch verificado funcional ANTES de cada fase | Cada fase |
| QG-5 | Backtests automáticos pasan en CI antes de merge a main | Permanente |
| QG-6 | Todo cambio en parámetros de riesgo genera audit log | Permanente |
| QG-7 | Ningún modelo a producción sin Sharpe OOS > 1.0 | Fase 3+ |
| QG-8 | Ningún deploy sin smoke test del pipeline completo en paper mode | Fase 1+ |
| QG-9 | Sharpe neto OOS > 0.8 ANTES de iniciar Fase 4 | Gate Fase 4 |
| QG-10 | 60 días de paper trading con Sharpe > 1.0 ANTES de live | Gate Fase 7 |

---

## INVESTIGACIONES PRIORITARIAS (paralelas al desarrollo)

| ID | Pregunta | Método | Criterio éxito | Timeline |
|----|----------|--------|---------------|----------|
| **I1** ⚠️ | ¿Existe edge estadístico real después de costos? | Walk-forward + 1000 bootstraps + benchmark random | Sharpe neto > 0.8, p-value < 0.05 | Semanas 5-6 |
| **I2** | ¿Cuáles features aportan información predictiva real? | Permutation importance + SHAP por régimen + mutual info | Eliminar features con importance ≤ ruido | Semana 5 |
| **I3** | ¿LightGBM con 300 árboles está sobreajustado? | Curvas de complejidad (n_estimators vs Sharpe OOS) | Encontrar punto óptimo bias-variance | Semana 6 |
| **I4** | ¿En qué regímenes el sistema destruye valor? | Backtest segmentado por régimen | Identificar regímenes donde desactivar | Semana 7 |
| **I5** | ¿Qué activos son trending vs mean-reverting? | Hurst exponent rolling (100, 250, 500 barras) | Mapear activo → estrategia óptima | Semana 8 |
| **I6** | ¿El stacking del AssetSpecificAgent aporta valor? | Stacking vs promedio ponderado vs mejor individual | Adoptar si Sharpe stacking ≥ +15% | Semana 9 |
| **I7** | ¿Features multi-timeframe mejoran la predicción? | Benchmark 1h vs 1h+4h vs 1h+4h+1D | Adoptar si mejora ≥ +10% Sharpe OOS | Semanas 9-10 |
| **I8** | ¿Online learning (River) es viable vs batch? | Benchmark accuracy y Sharpe: River vs LightGBM | River ≥ 80% del Sharpe batch | Semanas 11-12 |

> **⚠️ I1 es BLOQUEANTE:** si Sharpe neto OOS ≤ 0, no invertir en Fases 3-7 hasta resolver el problema de edge. Priorizar feature engineering y validación estadística sobre nuevas estrategias.

---

## TIMELINE MAESTRO

```
Semana 1:    [QWT-1→10] + [Fase 0] — Foundation & Quick Wins técnicos
Semana 2:    [QWQ-1→5]  + [Fase 1 — inicio] — Quick Wins cuantitativos + DB + Auth
Semana 3:    [QWQ-6→10] + [Fase 1 — fin]   — Pipeline autónomo operativo
Semana 4:    [Fase 2 — inicio] — Feature Engineering V2 + Feature Store
Semana 5:    [Fase 2] + [I1, I2] — Validación estadística + investigaciones
Semana 6:    [Fase 2 — fin] + [I3] — Backtesting V2 + costos reales
             ⛔ GATE: si I1 falla → replantear approach antes de continuar
Semana 7:    [Fase 3 — inicio] + [I4] — HMM + Modelos mejorados
Semana 8:    [Fase 3] + [I5] — Consensus dinámico + Hurst
Semana 9:    [Fase 3 — fin] + [I6, I7] — Observabilidad + investigaciones
Semana 10:   [Fase 4 — inicio] — Strategy Framework + TSMOM
             ⛔ GATE: Sharpe OOS > 0.8 verificado
Semana 11:   [Fase 4] + [I8] — Cross-Sectional Momentum + Stat Arb
Semana 12:   [Fase 4 — fin] — Meta-agente + Portfolio Optimizer
Semana 13:   [Fase 5 — inicio] — Risk Engine 2.0 + CVaR
Semana 14:   [Fase 5] — Volatility Targeting + Correlaciones
Semana 15:   [Fase 5 — fin] — User Profiles + Adaptación automática
Semana 16:   [Fase 6 — inicio] — Online Learning + Drift Detection
Semana 17:   [Fase 6] — RL Agent (shadow mode)
Semana 18:   [Fase 6] — Stress Testing
Semana 19:   [Fase 6 — fin] — Alpha Decay Monitor
Semanas 20-24: [Fase 7] — Live trading con capital limitado
              ⛔ GATE: 60 días paper trading Sharpe > 1.0
```

---

## DEUDA TÉCNICA PRIORIZADA (resumen ejecutivo)

### Crítica — Resolver en Semanas 1-3

| # | Deuda | Esfuerzo | Fase |
|---|-------|----------|------|
| 1 | DB nunca inicializada → todo el sistema es volátil | 12h | F1 |
| 2 | Pipeline scheduler completamente desactivado | 16h | F1 |
| 3 | Incompatibilidad Signal ↔ RiskManager.validate_signal | 4h | QW |
| 4 | JWT secret sin validación productiva (`and False`) | 1h | QW |
| 5 | 4 workers uvicorn con estado en memoria → race conditions | 8h | F1 |

### Alta — Resolver en Semanas 4-9

| # | Deuda | Esfuerzo | Fase |
|---|-------|----------|------|
| 6 | Sin tests de api/routes/ (cobertura ~5%) | 16h | F2 |
| 7 | Sin tests de agentes IA (core/agents/) | 12h | F3 |
| 8 | Rate limiting declarado pero inexistente | 4h | QW |
| 9 | dashboard.py God File de 931 líneas | 8h | F2 |
| 10 | Token JWT sin blacklist (logout inefectivo) | 6h | F1 |
| 11 | Walk-forward sin reentrenamiento real | 16h | F2 |
| 12 | Features genéricas sin edge diferenciado | 40h | F2 |
| 13 | Target ruidoso (sign de ret_1) | 8h | F2 |
| 14 | Detección régimen via if/else (sin HMM real) | 16h | F3 |
| 15 | Pesos estáticos del consensus engine | 8h | F3 |

---

## REGLAS DE SESIÓN DE TRABAJO (para cada sesión con IA)

Antes de iniciar cualquier sesión de desarrollo:

```
1. ¿En qué FASE estoy trabajando? (0-7)
2. ¿Cuál es la spec aprobada del módulo a implementar?
3. ¿Están los Quality Gates de la fase anterior verificados?
4. ¿Está el kill switch activo y funcional?
5. ¿Estoy en EXECUTION_MODE=paper? (nunca cambiar sin autorización)

Orden obligatorio: SPEC → TESTS → IMPLEMENTACIÓN → AUDITORÍA
No avanzar al siguiente paso sin completar el anterior.
```

---

## SEMÁFORO DE ESTADO ACTUAL

| Componente | Estado | Blocker |
|-----------|:---:|---------|
| Autenticación JWT | 🟡 | `and False` en validación → QWT-1 |
| Base de datos | 🔴 | `init_pool` comentado → F1 |
| Pipeline autónomo | 🔴 | APScheduler comentado → F1 |
| Ejecución de órdenes | 🔴 | Bug Signal/dict mismatch → QWT-2/10 |
| Docker Compose | 🔴 | YAML inválido → QWT-3 |
| Feature Engineering | 🟡 | Solo 17 features genéricas → QWQ-1+F2 |
| Validación estadística | 🔴 | Sin purged k-fold, sin walk-forward real → F2 |
| Modelos ML | 🟡 | Funcionales, sin validación temporal → F3 |
| Detección de régimen | 🟡 | If/else en lugar de HMM real → F3 |
| Consensus Engine | 🟡 | Pesos estáticos → QWQ-4+F3 |
| Risk Manager | 🟡 | Funcional pero sin CVaR ni correlaciones → F5 |
| Backtesting | 🟡 | Sin costos reales, sin reentrenamiento → F2 |
| Observabilidad | 🟡 | structlog+Prometheus OK, sin Grafana dashboards → F3 |
| Testing/Cobertura | 🟡 | api/routes sin tests → F2 |

🔴 No funciona · 🟡 Parcial · 🟢 Operativo

---

## TABLA DE CONTENIDOS (PLAN ESPECIALIZADO)

- [Ecosistema del proyecto](#ecosistema-del-proyecto--configuración-real) — Exchanges, activos, estrategias reales
- [Quick Wins](#quick-wins--ejecutar-en--1-semana-antes-de-cualquier-fase) — 21h técnica + 15d cuantitativa
  - QW-TECH: Seguridad crítica (QWT-1 al 10)
  - QW-QUANT: Features e indicadores (QWQ-1 al 10)
  - Cronograma: Semana 1
- [Fase 0](#fase-0--foundation--governance) — Semana 1 (gobernanza + CI/CD)
- [Fase 1](#fase-1--secure-core-foundation-especializada) — Semanas 2-3 (DB + Auth + Pipeline autónomo)
  - M1.1: Database + Persistence (TimescaleDB + Alembic)
  - M1.2: Auth JWT con validación real
  - M1.3: Pipeline autónomo con APScheduler
  - M1.4: Paper Executor multisimbol multi-exchange
  - M1.5: Redis para estado distribuido
- [Fase 2 a 7](#fase-2--data--quant-infrastructure-hasta-fase-7--production-grade) — Semanas 4-24 (ML, Risk, Strategies)
- [Quality Gates](#quality-gates-obligatorios-todas-las-fases) — Criterios de aceptación
- [Investigaciones prioritarias](#investigaciones-prioritarias-paralelas-al-desarrollo) — I1-I8
- [Deuda técnica priorizada](#deuda-técnica-priorizada-resumen-ejecutivo) — 136h estimadas
- [Semáforo de estado](#semáforo-de-estado-actual) — Componentes por nivel de avance

---

## MÉTRICAS CLAVE POR SEMANA

```
SEMANA 1 (Quick Wins + Fase 0):
├── QW-TECH: 21h
├── QW-QUANT: 4 días (retornos, target ternario, embargo, ADX, Hurst)
└── Fase 0: CI/CD + estructura Clean Architecture
    Hito: "Sistema puede iniciar sin errores"

SEMANA 2-3 (Fase 1):
├── Lunes-Martes: DB + migraciones (12h)
├── Martes-Miércoles: Auth JWT (8h)
├── Miércoles-Viernes: APScheduler + pipeline (16h)
└── Todo: Paper executor + Redis (16h)
    Hito: "Primera orden ejecutada en paper mode"

SEMANA 4-6 (Fase 2):
├── Features V2 (35+ indicadores sin look-ahead)
├── Feature Store versionado
├── Validación estadística rigurosa
├── Backtesting V2 con costos reales
└── I1 completada: ¿existe edge real?
    Hito: "Sharpe neto OOS > 0.8 o pivotear"

SEMANA 7-9 (Fase 3):
├── HMM con 8 estados
├── Consensus dinámico
├── Model validation gate
└── Observabilidad completa
    Hito: "Modelos con validación temporal correcta"

SEMANA 10-12 (Fase 4):
├── Multi-estrategia (TSMOM, Cross-sectional, Stat Arb)
├── Meta-agente selector
├── Strategy rotation engine
└── Portfolio optimizer
    Hito: "Sharpe OOS > 0.8 con múltiples estrategias"

SEMANA 13-15 (Fase 5):
├── Risk Engine 2.0 (CVaR, vol targeting, correlaciones)
├── Adaptación automática al mercado
└── User profile engine
    Hito: "Risk management enterprise-grade"

SEMANA 16-19 (Fase 6):
├── Online learning (River)
├── Drift detection
├── RL agent (shadow mode)
├── Stress testing
    Hito: "Sistema adapta automáticamente a mercado"

SEMANA 20-24 (Fase 7):
├── Live con capital limitado (<1% total)
├── Integración Binance real
├── Integración OANDA real
└── Disaster recovery + compliance
    Hito: "Operando con capital real, Sharpe > 1.0"
```

---

## EXCHANGES ESPECÍFICOS — DETALLES DE INTEGRACIÓN

### Binance (Crypto — spot + futures)

**Estado actual:** ✅ Implementado (`core/ingestion/binance_client.py`)

**Símbolos:**
- BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT

**Parámetros Fase 1:**
```python
# Comisión
BINANCE_MAKER_FEE = 0.0002  # 0.02% (puede ser menor con BNB)
BINANCE_TAKER_FEE = 0.0004  # 0.04%

# Paper executor
BINANCE_SLIPPAGE_PCT = 0.001  # 0.1% (volatile, 24/7)
BINANCE_LATENCY_MS = (50, 150)

# Límites por orden
MIN_ORDER_AMOUNT_USD = 10  # $10 mínimo
MAX_ORDER_PCT = 0.10       # máximo 10% del capital por orden

# Testnet durante Fase 1-3, live en Fase 4+
BINANCE_TESTNET = True  # cambiar a False solo en Fase 4 con autorización
```

**Pasos para integración live (Fase 4):**
1. Crear cuenta en Binance (https://www.binance.com)
2. Generar API key en Settings → API Management
   - Habilitar: Spot Trading, Margin Trading (si es necesario)
   - Desbloquear: restricción por IP (solo desde servidor de trading)
3. Agregar a `.env`:
   ```
   BINANCE_API_KEY=xxx
   BINANCE_SECRET_KEY=yyy
   BINANCE_TESTNET=false
   ```
4. Test: correr `pytest tests/integration/test_exchange_clients.py::TestBinanceClient::test_get_klines`

---

### OANDA (Forex + Indices + Commodities)

**Estado actual:** ✅ Implementado (`core/ingestion/oanda_client.py`)

**Símbolos:**
- Forex: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
- Indices: SPX500, NAS100, US30, DE40, UK100, JP225
- Commodities: XAUUSD, XAGUSD, USOIL, UKOIL, NATGAS, WHEAT

**Parámetros Fase 1:**
```python
# Spread aproximado (incluido en comisión = 0)
OANDA_SPREAD_USD = {
    "EURUSD": 2,      # 0.0002 * 100,000 = $20 por lote
    "GBPUSD": 3,      # 0.0003
    "XAUUSD": 0.30,   # 0.30 USD por onza troy
    "SPX500": 1.0,    # 1 USD por lote
}

# Paper executor
OANDA_SLIPPAGE_PCT = 0.0001  # 1 pip
OANDA_LATENCY_MS = (100, 300)

# Límites
MIN_ORDER_UNITS = 1        # 1 unidad (EURUSD = 100,000 unidades)
MAX_ORDER_PCT = 0.15       # máximo 15% del capital

# Account type
OANDA_ENVIRONMENT = "practice"  # cambiar a "live" en Fase 4+
```

**Pasos para integración live (Fase 4):**
1. Crear cuenta en OANDA (https://www.oanda.com/us-en/trading)
2. Generar token de API en Account Settings
3. Agregar a `.env`:
   ```
   OANDA_API_KEY=xxx
   OANDA_ACCOUNT_ID=yyy
   OANDA_ENVIRONMENT=live
   ```
4. Test: correr `pytest tests/integration/test_exchange_clients.py::TestOandaClient::test_get_candles`

---

### MetaTrader 5 / IC Markets (Forex + Commodities + Indices)

**Estado actual:** ✅ Implementado (`core/ingestion/providers/mt5_client.py`)

**Símbolos:**
- Todos los OANDA + más pares forex menores y exóticos

**Parámetros Fase 1:**
```python
# MT5 connection
MT5_SERVER = "ICMarketsSC-Demo04"  # cambiar a "ICMarketsSC-Real01" en Fase 4+
MT5_LOGIN = 123456                  # tu login demo
MT5_PASSWORD = "password"

# Paper executor
MT5_SLIPPAGE_PIPS = 1.0             # 1 pip slippage
MT5_LATENCY_MS = (80, 250)

# Swap costs (overnight carry)
# Actualizados dinámicamente via MT5Client.get_symbol_info()
```

**Pasos para integración live (Fase 4):**
1. Abrir cuenta en IC Markets (https://www.icmarkets.com)
2. Descargar MetaTrader 5 y conectar
3. Obtener server, login, password
4. Agregar a `.env`:
   ```
   MT5_SERVER=ICMarketsSC-Real01
   MT5_LOGIN=xxxxx
   MT5_PASSWORD=yyyy
   ```

---

## ESTRATEGIAS BUILTIN — DETALLES POR FASE

### Estrategia 1: EMA Crossover + RSI (`ema_rsi_v1`)

**Fase:** 1 (ya implementada, mejorar en Fase 2)

**Simbolos donde funciona mejor:**
- Forex majors: EURUSD, GBPUSD
- Índices: SPX500, NAS100
- Crypto trending: BTC, ETH (en regímenes bull)

**Mejoras en Fase 2-3:**
- Agregar ADX como filtro de fuerza de tendencia
- Dynamic RSI levels basados en volatilidad histórica
- Incorporar Hurst exponent para confirmar tendencia

---

### Estrategia 2: Mean Reversion (`mean_rev_v1`)

**Fase:** 1 (ya implementada, mejorar en Fase 2)

**Símbolos donde funciona mejor:**
- Forex pairs: EURUSD, GBPUSD, AUDUSD
- Índices: SPX500, NAS100
- Commodities: XAUUSD

**Mejoras en Fase 2-3:**
- Z-score dinámico calibrado por volatilidad
- Incorporar Hurst Exponent (< 0.45 = mean-reverting)
- VWAP reversion con reset diario

---

### Estrategia 3: TSMOM (`tsmom_v1`)

**Fase:** 1-2 (ya implementada, pero validar edge en Fase 2)

**Símbolos donde funciona mejor:**
- Todos los activos en regímenes trending
- Crypto: BTC, ETH (multidía)
- Forex: en breakouts

**Mejoras en Fase 4:**
- Combine con meta-agente selector
- Multi-timeframe: 1h + 4h + 1D signals

---

### Estrategia 4: Volatility Breakout Adaptive (`vol_breakout_v1`)

**Fase:** 2-3 (mejorar detección de consolidación)

**Símbolos donde funciona mejor:**
- Crypto: todos (24/7 trading)
- Commodities: XAUUSD, USOIL (volatility clustering)
- Índices: en pre-apertura USA

**Mejoras en Fase 3:**
- Detección automática de consolidación (ATR bajo)
- Adaptive bands basados en volatility regime

---

*Plan maestro especializado generado el 2026-05-16*  
*Próxima revisión: tras completar Quick Wins (Semana 1)*  
*Responsable de ejecución: [TU NOMBRE]*
