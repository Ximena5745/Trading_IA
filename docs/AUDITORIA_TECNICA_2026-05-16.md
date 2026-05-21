# AUDITORÍA TÉCNICA INTEGRAL — TRADER AI v2.0.0

**Fecha:** 16 de mayo de 2026
**Auditor:** Lead Architect + Security Auditor + QA Lead + Technical Product Owner
**Versión analizada:** v2.0.0
**Alcance:** Repositorio completo (~271 archivos, 136 `.py`, 32 `.md`)

---

## Tabla de contenidos

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Score general del proyecto](#2-score-general-del-proyecto)
3. [Análisis arquitectónico](#3-análisis-arquitectónico)
4. [Matriz de cumplimiento vs spec](#4-matriz-de-cumplimiento-vs-spec)
5. [Funcionalidades implementadas](#5-funcionalidades-implementadas)
6. [Hallazgos críticos](#6-hallazgos-críticos)
7. [Auditoría de seguridad](#7-auditoría-de-seguridad)
8. [Auditoría de testing](#8-auditoría-de-testing)
9. [Auditoría de performance](#9-auditoría-de-performance)
10. [Documentación obsoleta](#10-documentación-obsoleta)
11. [Propuestas de evolución](#11-propuestas-de-evolución)
12. [Roadmap actualizado](#12-roadmap-actualizado)
13. [Quick wins](#13-quick-wins)
14. [Deuda técnica prioritaria](#14-deuda-técnica-prioritaria)
15. [Conclusión técnica](#15-conclusión-técnica)

---

## 1. RESUMEN EJECUTIVO

**Estado general:** El proyecto tiene una arquitectura bien concebida y documentada, con una capa de dominio sólida y una API FastAPI funcional. Sin embargo, existen **brechas críticas entre la especificación y la implementación real** que impiden que el sistema opere de forma completa y segura en producción.

**Nivel de madurez:** **MVP parcial** — Fases 1–4 mayoritariamente implementadas a nivel estructural, con varios módulos core que son stubs o tienen bugs bloqueantes. Fase 5 (marketplace, simulación) implementada parcialmente a nivel API pero sin persistencia real.

**Riesgos críticos:**
- El endpoint `POST /execution` falla en runtime por incompatibilidad de tipos entre `Signal` (Pydantic) y `RiskManager.validate_signal(dict)`.
- La validación del JWT secret está **desactivada programáticamente** con `and False`.
- El `docker-compose.yml` tiene **YAML inválido** (claves duplicadas al nivel raíz) que puede impedir el despliegue.
- El pipeline scheduler está **completamente comentado** — el sistema nunca ejecuta ciclos automáticos de trading.
- La base de datos **nunca se inicializa** en el lifespan del servidor (`init_pool` está en código comentado).

**Estado arquitectónico:** Bueno a nivel de diseño, con violaciones puntuales en la capa API (inyección de singletons via globals, lógica de negocio en routes).

**Estado de seguridad:** Crítico — JWT secret sin enforce, rate limiting declarado pero no aplicado, múltiples endpoints sensibles sin autenticación.

**Estado funcional:** ~45% operativo end-to-end. Market data funciona (con datos parquet). Execution tiene bug bloqueante. DB desconectada. Pipeline desactivado.

---

## 2. SCORE GENERAL DEL PROYECTO

| Área | Score /10 | Observaciones |
|------|-----------|---------------|
| **Arquitectura** | 6.5 | Diseño sólido, Clean Architecture parcial; inyección de deps con globals, scheduler desactivado |
| **Seguridad** | 3.5 | JWT secret sin enforce, rate limiting no aplicado, endpoints públicos sin auth, YAML compose roto |
| **Testing** | 5.5 | Buenos unit tests con Hypothesis; cobertura solo en `core/`, sin cobertura de `api/`, E2E requiere servidor levantado |
| **Observabilidad** | 5.0 | structlog configurado, Prometheus iniciado, pero sin dashboards de Grafana configurados, sin alertas por threshold |
| **Performance** | 5.0 | Sin benchmark real; carga parquet en startup (bloquea); async incorrecto en `_refresh_fundamental` (sin cancelación) |
| **Calidad código** | 6.0 | Tipado correcto, ruff configurado; bugs semánticos graves en execution y portfolio; bare `except:` en varias rutas |
| **IA/ML** | 5.5 | Modelos entrenados (LightGBM/XGBoost/CatBoost); pipeline ML scripts presentes; SHAP parcial; sin walk-forward activo |
| **DevOps** | 5.0 | CI pipeline bien estructurado; docker-compose roto; sin CD; sin quality gate de cobertura mínima |
| **Escalabilidad** | 4.0 | Monolito sin separación de servicios; singletons en memoria; sin Redis para estado compartido; sin cola de tareas |
| **Mantenibilidad** | 6.0 | Documentación extensa; estructura modular; pero divergencias doc↔código aumentan deuda de mantenimiento |

> **Score global: 5.3/10 — Sistema en desarrollo activo, no apto para producción financiera real.**

---

## 3. ANÁLISIS ARQUITECTÓNICO

### Fortalezas

- **Separación de capas bien declarada**: `core/` (dominio) → `api/` (presentación). El dominio no importa FastAPI.
- **Modelos Pydantic ricos**: `core/models.py` define `Signal`, `Order`, `Portfolio`, `MarketData` con validadores `@model_validator`.
- **Kill switch implementado**: `KillSwitch` con lógica de triggers por drawdown, pérdidas consecutivas y pérdida diaria.
- **Observabilidad estructurada**: `structlog` configurado desde el arranque, logs con contexto enriquecido.
- **CI bien pensado**: lint → unit → integration → safety gate → backtest gate → docker build.
- **Configuración por env vars**: `pydantic-settings` con `.env`, sin valores hardcodeados en lógica de negocio.
- **Multi-asset**: `InstrumentConfig` con 9 símbolos, pip values, lot sizes por tipo de activo.
- **PositionSizer separado**: delegación correcta del sizing al `PositionSizer`.

### Debilidades

- **DB nunca inicializada en runtime**: `init_pool(settings.DATABASE_URL)` está en código comentado. Ningún router accede a la BD — todo es in-memory o parquet estático.
- **Singletons via globals en routes**: `_order_tracker`, `_risk_manager`, `_portfolio_manager` son variables de módulo globales mutadas desde `lifespan`. Válido para monolito, pero frágil ante recarga parcial.
- **Pipeline scheduler comentado**: `APScheduler` desactivado en `main.py` — el sistema no tiene ciclos automáticos. Es un servidor de consultas, no un sistema de trading autónomo.
- **`drawings` e `indicators` en memoria**: sin persistencia, sin auth, se pierden al reiniciar.
- **Lógica de negocio en `api/routes/dashboard.py`**: ~931 líneas con HTML/CSS/JS incrustado y lógica de mapeo de regímenes. Violación de Single Responsibility.
- **`_load_parquet_data` síncrono en lifespan async**: bloquea el event loop durante el startup si hay muchos archivos parquet.

### Riesgos

| Riesgo | Severidad | Impacto |
|--------|-----------|---------|
| `init_pool` no llamado → no hay persistencia | Crítico | Toda la data se pierde al reiniciar |
| Scheduler desactivado → no hay trading autónomo | Crítico | Sistema no opera como especificado |
| Signal type mismatch en execution | Crítico | RuntimeError en prod al ejecutar órdenes |
| `asyncio.create_task` sin handle en lifespan | Alto | Tarea huérfana de `_refresh_fundamental` no se cancela en shutdown |
| Monolito con estado en memoria + 4 workers uvicorn | Alto | Race conditions garantizadas; estado inconsistente entre workers |

### Violaciones SOLID

| Principio | Archivo | Descripción |
|-----------|---------|-------------|
| **SRP** | `api/routes/dashboard.py` | 931 líneas mezclando HTML, CSS, JS y lógica de dominio |
| **OCP** | `core/risk/risk_manager.py` | `validate_signal` hardcodea todas las reglas; añadir una nueva requiere modificar la clase |
| **LSP** | `api/routes/execution.py` | Pasa `Signal` (Pydantic) donde `RiskManager` espera `dict` |
| **DIP** | `api/routes/*.py` | Imports directos de singletons globales en lugar de inyección formal |

### Anti-patterns detectados

1. **God File**: `dashboard.py` con 931 líneas mezclando responsabilidades.
2. **Shotgun Surgery**: bug de `user.get("sub")` disperso en 4+ archivos.
3. **Feature Envy**: `execution.py` construye `Signal` con `explanation=None` violando el contrato del modelo.
4. **Dead Code**: bloque de HTML que nunca se ejecuta en `get_crypto_dashboard_public` (código después de `return`).
5. **Magic `and False`**: supresión silenciosa de validación de seguridad crítica en `settings.py`.
6. **Bare `except:`**: en `portfolio.py` captura excepciones sin loguear ni diferenciar tipo de error.

---

## 4. MATRIZ DE CUMPLIMIENTO VS SPEC

| Módulo | Estado | % avance | Observaciones | Riesgo |
|--------|--------|----------|---------------|--------|
| **Data Ingestion** | Parcial | 60% | Parquet/CSV OK; WebSocket stream existe pero no conectado al pipeline; Binance adapter presente | Alto |
| **Feature Engine** | Implementado | 80% | `calculate_all` funciona; `FeatureSet` completo; falta validación de calidad de datos | Medio |
| **Regime Detection (HMM)** | Parcial | 50% | Modelo HMM existe; mapeo en `main.py` es simplista (4 reglas if/else sin HMM real en producción) | Alto |
| **Agentes IA (Technical)** | Implementado | 75% | `asset_specific_agent.py` con LGB/XGB/CB; SHAP TODO pendiente | Medio |
| **Fundamental Agent** | Parcial | 40% | Existe; `refresh()` cada 30min; lógica de análisis no verificada en profundidad | Medio |
| **Consensus Engine** | Parcial | 55% | `voting_engine` presente; `ConsensusOutput` modelado; integración con pipeline desactivada | Alto |
| **Signal Engine** | Parcial | 60% | `Signal` bien modelado; generación de señales no automatizada (scheduler off) | Alto |
| **Risk Manager** | Implementado | 85% | Kill switch, position sizer, validaciones de límites; bug con tipos en execution | Crítico |
| **Execution Engine** | Roto | 30% | API endpoint existe pero falla en runtime; sin conexión a broker real verificada | Crítico |
| **Portfolio Manager** | Parcial | 60% | PortfolioManager inicializado; sin persistencia DB; endpoints public con mock data | Alto |
| **Order Tracker** | Implementado | 70% | `OrderTracker` en memoria; funcional para paper trading; sin persistencia | Medio |
| **Backtesting** | Implementado | 70% | Scripts de backtest crypto presentes; resultados JSON guardados; CI gate existe | Medio |
| **Simulación** | Parcial | 50% | `HistoricalSimulator` inicializado; API endpoints presentes; lógica interna no verificada | Medio |
| **Marketplace** | Stub | 25% | Modelos y endpoints API presentes; sin persistencia real; sin validación de estrategias | Bajo |
| **Monitoring/Alertas** | Parcial | 50% | `AlertEngine` + Telegram bot configurados; Prometheus corriendo; sin alertas por threshold | Medio |
| **Observabilidad** | Parcial | 60% | structlog OK; Prometheus OK; Grafana sin dashboards configurados; sin tracing distribuido | Medio |
| **Auth (JWT)** | Implementado | 75% | Login/refresh/logout; RBAC básico (admin/trader/viewer); validación JWT desactivada | Crítico |
| **Frontend Dashboard** | Implementado | 70% | dashboard.html funcional con Plotly; LightweightCharts manager; dibujos/indicadores | Bajo |
| **WebSocket streaming** | Inexistente | 5% | Archivo existe; no montado en FastAPI; no conectado a clientes | Alto |
| **Multi-exchange** | Stub | 20% | Settings con Bybit/OANDA; adaptadores presentes; integración real no verificada | Medio |
| **Pipeline automático** | Inexistente | 5% | Código comentado en `main.py`; `run_pipeline.py` existe solo como script manual | Crítico |
| **Adaptación/Online learning** | Inexistente | 10% | Directorio `core/adaptation/` presente; contenido no integrado al pipeline | Medio |
| **DB/TimescaleDB** | Inexistente | 10% | Pool declarado; `init_pool` nunca llamado en lifespan; sin migraciones activas | Crítico |

---

## 5. FUNCIONALIDADES IMPLEMENTADAS

### Completas

- Autenticación JWT (login, refresh, logout, `GET /me`)
- Kill switch con triggers automáticos y endpoint de activación manual
- Position sizer multi-asset (forex, crypto, índices, commodidades)
- Feature engine (indicadores técnicos: RSI, MACD, BB, ATR, EMA, VWAP, OBV)
- Carga de datos históricos desde parquet al startup
- Endpoints de market data (`/market/symbols`, `/{symbol}/data`, `/features`, `/regime`)
- Endpoints de señales (`GET /signals`, `/latest/{symbol}`)
- Rate limiter inicializado (aunque no aplicado a endpoints individuales)
- CI pipeline completo (lint → unit → integration → safety → backtest → docker)
- Modelos Pydantic ricos con validaciones de dominio
- structlog con contexto estructurado
- Prometheus metrics server en puerto 8001
- Dashboard HTML estático con Plotly y LightweightCharts
- Scripts de backtesting con resultados JSON persistidos

### Parciales

- Risk manager (funcional como objeto, roto cuando invocado desde execution API)
- Portfolio manager (inicializado sin persistencia; endpoints con mock/stale data)
- Agentes IA técnicos (modelos entrenados; integración en pipeline no activa)
- Fundamental agent (existe y refresca; lógica de análisis no verificada)
- Consensus/voting engine (modelos definidos; sin integración automática)
- Monitoring/alertas (estructura presente; sin umbrales configurados)
- Simulación histórica (API endpoints presentes; lógica interna no verificada)
- Marketplace (modelos y endpoints; sin persistencia ni validación)
- Multi-exchange connectors (settings y adaptadores; integración no verificada)

### Inexistentes (especificados pero no operativos)

- Pipeline automático de trading (scheduler completamente comentado)
- Base de datos TimescaleDB activa (pool nunca inicializado en runtime)
- WebSocket streaming a clientes frontend
- Persistence layer para drawings e indicators
- Walk-forward validation automatizada
- Grafana dashboards configurados
- Alertas operacionales con thresholds
- Rate limiting efectivo por endpoint
- CD/deployment automatizado
- `POST /auth/register` (documentado pero no implementado)

### Obsoletas / Código muerto

- Bloque HTML duplicado en `get_crypto_dashboard_public` (código inalcanzable después de `return`)
- Validador `validate_jwt_secret` con `and False` (nunca se ejecuta)
- Código comentado de scheduler en `lifespan` (10+ líneas)
- Segunda definición de `grafana:` y `prometheus:` en `docker-compose.yml` fuera de `services:`

---

## 6. HALLAZGOS CRÍTICOS

### P0 — Bloqueantes de producción inmediata

#### P0-001: `POST /execution` falla en runtime

**Archivo:** `api/routes/execution.py:71-83`

```python
# Bug 1: explanation=None no es válido en core/models.py
signal = Signal(
    ...
    explanation=None,   # campo es list[SignalExplanationFactor], no Optional
)

# Bug 2: validate_signal espera dict, no Signal Pydantic
approved, reason = rm.validate_signal(signal, portfolio=None)
# → AttributeError: 'NoneType' has no attribute 'get'  (portfolio=None)
# → AttributeError: 'Signal' has no attribute 'get'   (signal es Pydantic)
```

**Impacto:** El endpoint de ejecución de órdenes **nunca puede completarse exitosamente**.

---

#### P0-002: JWT Secret sin validación en producción

**Archivo:** `core/config/settings.py:106`

```python
@field_validator("JWT_SECRET_KEY")
@classmethod
def validate_jwt_secret(cls, v: str) -> str:
    if v == "change-me-in-production" and False:  # ← nunca se evalúa
        raise ValueError("JWT_SECRET_KEY must be set in production")
    return v
```

**Impacto:** Si se despliega sin configurar `JWT_SECRET_KEY`, el sistema usa `"change-me-in-production"` como secreto. Cualquier persona puede forjar tokens JWT válidos.

---

#### P0-003: `docker-compose.yml` YAML inválido

**Archivo:** `docker/docker-compose.yml:131-153`

Los bloques `grafana:`, `prometheus:` y `volumes:` se repiten **al nivel raíz del documento**, fuera de la clave `services:`. Esto genera claves duplicadas en el YAML y puede impedir que `docker compose up` interprete el archivo correctamente.

---

#### P0-004: Base de datos nunca inicializada

**Archivo:** `api/main.py:255-278`

```python
# ── Start pipeline scheduler ─────────────────────────────────────────────
_scheduler = None
try:
    # Scheduler disabled for now - prevents blocking on DB initialization
    # from apscheduler.schedulers.asyncio import AsyncIOScheduler
    # ...
    # await init_pool(settings.DATABASE_URL)   ← COMENTADO
    logger.info("pipeline_scheduler_skipped_for_dev")
```

`init_pool` nunca se llama en el lifespan. El servidor arranca sin conexión a TimescaleDB. **Ningún router persiste datos.**

---

### P1 — Críticos funcionales

#### P1-001: Pipeline automático desactivado

Todo el bloque de `APScheduler` en `lifespan` está comentado. El sistema es un servidor de consultas, no una plataforma de trading autónoma.

#### P1-002: `user.get("sub")` incorrecto en 4+ archivos

`get_current_user` retorna `{"user_id": ..., "role": ...}` sin clave `"sub"`. Afecta `execution.py`, `marketplace.py`, `simulation.py`, `portfolio.py`. Resultado: logs con `user=None`; `author` en marketplace incorrecto; auditoría comprometida.

#### P1-003: `BINANCE_API_SECRET` vs `BINANCE_SECRET_KEY`

- CI `ci.yml:56`: `BINANCE_API_SECRET: ""`
- Settings `settings.py:19`: campo `BINANCE_SECRET_KEY`
- `scripts/seed_data.py`: usa `settings.BINANCE_API_SECRET` → `AttributeError` en runtime

#### P1-004: Tarea async `_refresh_fundamental` sin cancelación

```python
# main.py — sin guardar el handle
asyncio.create_task(_refresh_fundamental())
# Al apagar: "Task was destroyed but it is pending!" warning en producción
```

---

### P2 — Importantes técnicos

| ID | Descripción | Archivo |
|----|-------------|---------|
| P2-001 | Rate limiting configurado pero no aplicado a ningún endpoint | `api/main.py:59` |
| P2-002 | `drawings` e `indicators` sin persistencia ni auth | `api/routes/drawings.py`, `indicators.py` |
| P2-003 | `_load_parquet_data()` síncrono en contexto async → bloquea event loop | `api/main.py:215` |
| P2-004 | Bare `except:` en portfolio routes — enmascara errores de producción | `api/routes/portfolio.py` |

---

### P3 — Mejoras de calidad

| ID | Descripción |
|----|-------------|
| P3-001 | `dashboard.py` God File de 931 líneas con HTML/CSS/JS incrustado |
| P3-002 | `pyproject.toml` inexistente — sin herramienta de gestión moderna de dependencias |
| P3-003 | `docs/api-reference/endpoints.md` describe rutas que no existen en el código real |

---

## 7. AUDITORÍA DE SEGURIDAD

### Vulnerabilidades críticas

| ID | Descripción | Severidad | Archivo |
|----|-------------|-----------|---------|
| SEC-001 | JWT secret sin validación en producción (`and False`) | **Crítica** | `core/config/settings.py:106` |
| SEC-002 | Grafana password por defecto `admin` en compose | **Alta** | `docker-compose.yml:95` |
| SEC-003 | DB password por defecto `trader` en compose | **Alta** | `docker-compose.yml:38` |
| SEC-004 | Redis password por defecto `redis` en compose | **Alta** | `docker-compose.yml:56` |
| SEC-005 | Rate limiting declarado pero no implementado en ningún endpoint | **Alta** | `api/main.py:59` |
| SEC-006 | Endpoints de drawings/indicators sin autenticación | **Media** | `api/routes/drawings.py`, `indicators.py` |
| SEC-007 | `GET /dashboard/crypto/public` expone datos de mercado sin restricción | **Media** | `api/routes/dashboard.py` |

### Riesgos operacionales

- **Kill switch manual sin doble confirmación**: `POST /risk/kill-switch/activate` requiere solo rol `trader`. En un sistema financiero, operaciones de alto impacto deberían requerir confirmación adicional (TOTP, doble aprobación).
- **`portfolio=None` en validate_signal**: en paper mode podría pasar silenciosamente si el kill switch está activo (retorna antes del `.get()`), dando falsa sensación de seguridad en la cadena de validación.
- **Sin verificación de idempotencia en OrderTracker**: el campo `idempotency_key` existe en el modelo pero no hay verificación de duplicados — órdenes duplicadas posibles.

### Riesgos financieros

- **`TRADING_ENABLED: false` en compose**: correcto por defecto, pero sin mecanismo de doble confirmación para activación en producción.
- **Validación R:R nunca se ejecuta en execution**: si el endpoint tiene el bug de tipos, la validación de riesgo queda sin efecto — se puede aceptar una señal con R:R insuficiente.
- **Execution sin broker real conectado**: el endpoint acepta señales (en papel), pero sin conexión real verificada a ningún exchange.

### Riesgos de autenticación

- **Refresh token sin blacklist**: no hay revocación. Un token robado es válido 7 días.
- **`POST /auth/logout`**: probablemente no invalida el token (implementación JWT pura sin blacklist Redis).
- **Sin `POST /auth/register`**: documentado pero no implementado. Alta de usuarios solo via script `seed_admin.py`.
- **CORS restrictivo a localhost**: correcto para desarrollo, requiere configuración explícita para producción.

### Riesgos de infraestructura

- **Puerto 6379 (Redis) expuesto** en docker-compose: accesible desde el host sin firewall adicional.
- **Puerto 5432 (PostgreSQL) expuesto**: misma consideración — solo para desarrollo local.
- **`nginx.conf` referenciado pero no verificado**: si no existe el archivo, el container de nginx falla al arrancar silenciosamente.
- **`python-jose`**: tiene CVEs históricos conocidos — evaluar migración a `PyJWT`.

---

## 8. AUDITORÍA DE TESTING

### Cobertura real

| Área | Unit Tests | Integration | E2E | Cobertura estimada |
|------|-----------|-------------|-----|--------------------|
| `core/risk/` | ✅ Hypothesis | Parcial | ❌ | ~80% |
| `core/features/` | ✅ | ❌ | ❌ | ~60% |
| `core/execution/` | ✅ (MT5) | Parcial | ❌ | ~50% |
| `core/signals/` | ✅ | ❌ | ❌ | ~55% |
| `api/routes/` | ❌ | ❌ | Parcial* | ~5% |
| `core/agents/` | ❌ | ❌ | ❌ | ~0% |
| `core/consensus/` | ❌ | ❌ | ❌ | ~0% |
| `core/portfolio/` | ❌ | ❌ | ❌ | ~0% |
| `core/marketplace/` | ❌ | ❌ | ❌ | ~0% |
| `core/simulation/` | ❌ | ❌ | ❌ | ~0% |

> *E2E en `test_dashboard_e2e.py` requiere servidor levantado en `http://127.0.0.1:8000` — no puede correr en CI sin infraestructura adicional.

### Gaps críticos

1. **`api/routes/execution.py` sin tests**: el bug P0-001 habría sido detectado con un test básico del endpoint.
2. **`core/agents/` sin tests**: los modelos ML más críticos del sistema no tienen validación automatizada.
3. **`core/portfolio/portfolio_manager.py` sin tests**: tracking de P&L y capital sin validación.
4. **Integration tests sin cobertura**: `--cov` no aplicado en el job de integration del CI.
5. **Backtest gate** (`ci_backtest_gate.py`): no verifica correctitud del pipeline, solo que el script no lance excepción.
6. **Sin contract tests**: entre `Signal` esperado por `RiskManager` y `Signal` construido en `execution.py`.
7. **Sin tests de concurrencia**: comportamiento del kill switch bajo carga concurrente no validado.

### Riesgos no cubiertos

- Ejecución de órdenes con datos de mercado adversos (precios extremos, NaN, gaps).
- Drift de features entre entrenamiento y producción.
- Recovery tras fallo de conexión a broker.
- Rollover/expiración de tokens JWT.
- Idempotencia de órdenes duplicadas.
- Comportamiento del portfolio manager bajo pérdida total de capital.

---

## 9. AUDITORÍA DE PERFORMANCE

### Bottlenecks identificados

| Problema | Ubicación | Impacto |
|---------|-----------|---------|
| `_load_parquet_data()` síncrono en startup async | `api/main.py:215` | Bloquea event loop; startup lento con muchos parquets |
| `pd.read_parquet()` sin streaming | `_load_parquet_data` | Carga todo en RAM; no escala con datasets grandes |
| `calculate_all(df)` en cada archivo parquet | `api/main.py:114` | CPU-bound en startup; puede bloquear minutos |
| `_refresh_fundamental` cada 30min sin backpressure | `api/main.py:220-225` | Si `refresh()` tarda más de 30min, se acumulan tareas |

### Problemas async

- **`asyncio.create_task` sin `await` ni handle**: la tarea de refresh fundamental no puede cancelarse limpiamente en shutdown.
- **Pandas en event loop**: procesamiento de dataframes es CPU-bound y bloquea el loop — debería usarse `asyncio.to_thread()` o `ProcessPoolExecutor`.
- **Prometheus en thread separado** (`start_metrics_server`): correcto, pero sin manejo de fallos al reiniciar el proceso.

### Riesgos de escalabilidad

- **Estado en memoria con 4 workers uvicorn**: `OrderTracker`, `PortfolioManager`, `KillSwitch` son objetos en memoria. Con múltiples workers, cada worker tiene su propio estado → **inconsistencia garantizada** en paper trading.
- **Sin cola de tareas** (Celery/Redis Queue): señales de trading procesadas síncronamente sin gestión de backlog ni retry.
- **Sin connection pool a Redis**: sin estado distribuido entre workers ni caché compartida.
- **Market data cache en memoria**: sin expiración ni LRU — crecimiento ilimitado con muchos símbolos y timeframes.

---

## 10. DOCUMENTACIÓN OBSOLETA

| Elemento | Estado | Impacto | Acción recomendada |
|---------|--------|---------|-------------------|
| `docs/api-reference/endpoints.md` — `POST /auth/register` | Inexistente en código | Alto | Eliminar o marcar como `[PENDIENTE]` |
| `docs/api-reference/endpoints.md` — `GET /risk/kill-switch/trigger` | Ruta incorrecta (es `/activate`) | Alto | Actualizar a `/kill-switch/activate` |
| `docs/api-reference/endpoints.md` — `/execution/order` | Ruta incorrecta (es `POST /execution`) | Alto | Actualizar ruta en documentación |
| `docs/architecture/security.md` — Rate limiting por endpoint | No implementado en código | Alto | Implementar o marcar como pendiente |
| `docs/README.md` — "76 tests" | Número no verificado con árbol actual | Medio | Actualizar con `pytest --collect-only` |
| `validate_jwt_secret` con `and False` | Comentario dice "skip in dev" pero afecta producción | Crítico | Implementar correctamente |
| CI job `BINANCE_API_SECRET` | Nombre incorrecto vs `Settings.BINANCE_SECRET_KEY` | Alto | Unificar nombre de variable |
| Código muerto en `get_crypto_dashboard_public` | Bloque HTML después de `return` — inalcanzable | Bajo | Eliminar |
| Scheduler comentado en `main.py` | 15+ líneas de código comentado | Medio | Extraer a rama feature o reactivar |
| `nginx.conf` referenciado en compose | Existencia del archivo no verificada | Alto | Confirmar/crear el archivo |
| `docs/technical-integration/pipeline-scheduler.md` | Documenta scheduler que está desactivado | Alto | Actualizar con estado real |

---

## 11. PROPUESTAS DE EVOLUCIÓN

| Propuesta | Valor | Complejidad | Prioridad | Riesgo | Impacto |
|-----------|-------|-------------|-----------|--------|---------|
| Activar DB + Alembic migrations | Crítico | Baja | P0 | Bajo | Habilita toda la capa de persistencia |
| Fix bug P0-001 execution | Crítico | Baja | P0 | Bajo | Desbloquea ejecución de órdenes |
| Activar JWT secret validation | Crítico | Baja | P0 | Bajo | Cierra vulnerabilidad crítica de auth |
| Fix docker-compose.yml | Crítico | Baja | P0 | Bajo | Habilita despliegue Docker completo |
| Reactivar scheduler con APScheduler | Alto | Media | P1 | Medio | Convierte el sistema en autónomo |
| Redis para estado distribuido | Alto | Media | P1 | Medio | Habilita múltiples workers sin race conditions |
| Rate limiting real por endpoint | Alto | Baja | P1 | Bajo | Protección DDoS y abuso de API |
| Token blacklist con Redis | Alto | Baja | P1 | Bajo | Logout real y revocación de tokens |
| Tests de API routes completos | Alto | Media | P1 | Bajo | Detecta regressions como P0-001 |
| WebSocket para streaming de precios | Alto | Alta | P2 | Medio | Dashboard en tiempo real |
| Grafana dashboards predefinidos | Medio | Media | P2 | Bajo | Observabilidad operacional real |
| Walk-forward validation automática | Alto | Alta | P2 | Medio | Validación rigurosa de modelos ML |
| SHAP explicability completa en todos los agentes | Medio | Media | P2 | Bajo | Explainability de señales operativa |
| Feature Store (Redis/Parquet versionado) | Alto | Alta | P2 | Medio | Previene data leakage, habilita versionado |
| HMM regime detection real (reemplazar if/else) | Alto | Media | P2 | Medio | Detección de régimen correcta |
| Celery + Redis Queue para pipeline async | Medio | Alta | P3 | Medio | Pipeline asíncrono escalable con retry |
| HashiCorp Vault para gestión de secrets | Alto | Alta | P3 | Bajo | Gestión enterprise de credenciales |
| Online learning / detección de concept drift | Medio | Muy alta | P3 | Alto | Adaptación continua del modelo |
| Multi-tenancy | Medio | Muy alta | P4 | Alto | Múltiples usuarios con estrategias propias |
| Chaos engineering | Medio | Alta | P4 | Medio | Resiliencia verificada en producción |

---

## 12. ROADMAP ACTUALIZADO

### Fase 0: Estabilización Crítica (Semana 1–2)

**Objetivo: Sistema funcional y seguro en paper mode**

| Tarea | Prioridad | Estimación | Riesgo |
|-------|-----------|------------|--------|
| Fix `Signal` en `execution.py` — `explanation=[]`, tipos correctos | P0 | 2h | Bajo |
| Fix `JWT_SECRET_KEY` validación — eliminar `and False` | P0 | 1h | Bajo |
| Fix `docker-compose.yml` — eliminar bloques duplicados (líneas 131-153) | P0 | 1h | Bajo |
| Activar `init_pool` en lifespan | P0 | 4h | Medio |
| Crear migraciones Alembic iniciales (signals, orders, portfolio) | P0 | 8h | Medio |
| Fix `user.get("sub")` → `user.get("user_id")` en 4 archivos | P1 | 2h | Bajo |
| Fix `BINANCE_API_SECRET` → `BINANCE_SECRET_KEY` en CI | P1 | 1h | Bajo |
| Mover `_load_parquet_data` a `asyncio.to_thread` | P1 | 2h | Bajo |
| Guardar handle de `_refresh_fundamental` para cancelación en shutdown | P1 | 1h | Bajo |
| Aplicar `@limiter.limit()` en endpoints críticos (auth, execution) | P1 | 4h | Bajo |
| Añadir `Depends(get_current_user)` a drawings e indicators | P1 | 3h | Bajo |
| Crear `nginx.conf` o eliminar referencia en compose | P1 | 2h | Bajo |

**Total estimado:** ~31h
**Impacto:** Sistema pasa de "roto" a "operativo en paper mode".

---

### Fase 1: Pipeline Autónomo (Semana 3–4)

**Objetivo: Trading automático en paper mode funcionando de extremo a extremo**

| Tarea | Prioridad | Estimación | Riesgo |
|-------|-----------|------------|--------|
| Reactivar APScheduler en lifespan | P1 | 8h | Medio |
| Conectar pipeline end-to-end (ingestion → features → agents → consensus → signal → execution) | P1 | 16h | Alto |
| Persistencia de signals y orders en TimescaleDB | P1 | 8h | Medio |
| Persistencia de portfolio y positions | P1 | 8h | Medio |
| Redis para estado compartido (kill switch, portfolio, cache de features) | P1 | 12h | Medio |
| Fix uvicorn workers → 1 worker o migrar estado a Redis | P1 | 4h | Bajo |

**Total estimado:** ~56h
**Dependencias:** Fase 0 completada.
**Impacto:** Sistema ejecuta ciclos de trading autónomamente en paper mode.

---

### Fase 2: Observabilidad y Seguridad (Semana 5–6)

**Objetivo: Sistema observable y seguro para operación continua**

| Tarea | Prioridad | Estimación | Riesgo |
|-------|-----------|------------|--------|
| Grafana dashboards (P&L, signals, risk, latencia de pipeline) | P2 | 16h | Bajo |
| Alertas operacionales con thresholds configurables (Telegram) | P2 | 8h | Bajo |
| Token blacklist con Redis (logout real) | P2 | 6h | Bajo |
| Tests de `api/routes/` con `TestClient` de FastAPI | P2 | 16h | Bajo |
| Tests de `core/agents/` y `core/portfolio/` | P2 | 12h | Bajo |
| Quality gate de cobertura mínima en CI (≥70%) | P2 | 4h | Bajo |
| WebSocket streaming de precios al frontend | P2 | 20h | Medio |
| `nginx.conf` real con TLS + headers de seguridad | P2 | 8h | Bajo |

**Total estimado:** ~90h
**Dependencias:** Fase 1 completada.

---

### Fase 3: ML Avanzado y Validación Estadística (Semana 7–10)

**Objetivo: Modelos ML productivos con validación rigurosa**

| Tarea | Prioridad | Estimación | Riesgo |
|-------|-----------|------------|--------|
| Walk-forward validation automatizada en CI | P2 | 24h | Medio |
| SHAP completo en todos los agentes IA | P2 | 12h | Bajo |
| Feature Store versionado (Redis + Parquet) | P2 | 24h | Medio |
| Detección de concept drift y feature drift | P3 | 20h | Alto |
| HMM regime detection real en lugar de if/else | P2 | 16h | Medio |
| Backtesting multi-asset unificado con métricas estándar | P2 | 20h | Medio |

**Total estimado:** ~116h
**Dependencias:** Fase 2 completada.

---

### Fase 4: Escalabilidad y Productización (Semana 11–16)

**Objetivo: Sistema apto para capital real limitado bajo supervisión**

| Tarea | Prioridad | Estimación | Riesgo |
|-------|-----------|------------|--------|
| Integración real Binance (crypto live con capital limitado) | P2 | 24h | Alto |
| Integración OANDA real (forex/CFD live) | P3 | 24h | Alto |
| Celery + Redis Queue para pipeline async con retry | P3 | 32h | Medio |
| HashiCorp Vault para gestión de secrets | P3 | 20h | Bajo |
| Multi-exchange execution routing | P3 | 40h | Alto |
| Disaster recovery y backup automatizado de DB | P3 | 16h | Bajo |

**Total estimado:** ~156h
**Dependencias:** Fases 1–3 completadas. Revisión legal/regulatoria previa a live.

---

## 13. QUICK WINS

Lista de mejoras de **alto impacto con bajo esfuerzo** (menos de 4 horas cada una):

1. **Fix `explanation=None` en `Signal`** — `execution.py:81`: cambiar a `explanation=[]` y ajustar tipo del campo a `Optional[list]`. Desbloquea `POST /execution` completamente.

2. **Fix `and False` en JWT validator** — `settings.py:106`: eliminar `and False`. Cierra la vulnerabilidad P0 de autenticación en 5 minutos.

3. **Fix `user.get("sub")`** — buscar y reemplazar `user.get("sub")` por `user.get("user_id")` en los 4 archivos afectados. Corrige auditoría y logging.

4. **Fix `docker-compose.yml`** — eliminar líneas 131–153 (bloques `grafana:`, `prometheus:`, `volumes:` duplicados fuera de `services:`).

5. **Unificar `BINANCE_API_SECRET`** — en `ci.yml:56` corregir a `BINANCE_SECRET_KEY` para alinear con `Settings`.

6. **Aplicar `@limiter.limit("100/minute")`** en los endpoints de `/auth/login`, `/execution`, `/risk/kill-switch/activate` como mínimo.

7. **Cancelación correcta de tarea async** — guardar `_fundamental_task = asyncio.create_task(...)` y llamar `_fundamental_task.cancel()` en el bloque post-yield del lifespan.

8. **`_load_parquet_data` en thread** — cambiar a `await asyncio.to_thread(_load_parquet_data)` en el lifespan. Libera el event loop durante el startup.

9. **Auth en drawings/indicators** — añadir `Depends(get_current_user)` a todos los endpoints de `drawings.py` e `indicators.py`.

10. **Refactorizar `validate_signal`** para aceptar `Signal | dict` o hacer conversión explícita en `execution.py` antes de llamar al risk manager.

---

## 14. DEUDA TÉCNICA PRIORITARIA

| # | Deuda | Criticidad | Área | Esfuerzo estimado |
|---|-------|-----------|------|-------------------|
| 1 | DB nunca inicializada → todo el sistema es volátil | Crítica | Infraestructura | 12h |
| 2 | Pipeline scheduler completamente desactivado | Crítica | Core | 16h |
| 3 | Incompatibilidad de tipos `Signal` ↔ `RiskManager.validate_signal` | Crítica | Dominio | 4h |
| 4 | JWT secret sin validación productiva (`and False`) | Crítica | Seguridad | 1h |
| 5 | 4 workers uvicorn con estado en memoria → race conditions | Crítica | Infraestructura | 8h |
| 6 | Sin tests de `api/routes/` (cobertura ~5%) | Alta | Testing | 16h |
| 7 | Sin tests de agentes IA (`core/agents/`) | Alta | Testing | 12h |
| 8 | Rate limiting declarado pero inexistente en endpoints | Alta | Seguridad | 4h |
| 9 | `dashboard.py` God File de 931 líneas | Alta | Arquitectura | 8h |
| 10 | Token JWT sin blacklist (logout inefectivo) | Alta | Seguridad | 6h |
| 11 | `user.get("sub")` incorrecto en 4 archivos | Media | Correctness | 1h |
| 12 | Detección de régimen via if/else en lugar de HMM real | Media | ML | 16h |
| 13 | SHAP pendiente en `asset_specific_agent` | Media | ML/Explainability | 12h |
| 14 | Persistencia de drawings/indicators en memoria | Media | Funcional | 8h |
| 15 | `_load_parquet_data` síncrono en contexto async | Media | Performance | 2h |
| 16 | Ausencia de `pyproject.toml` / gestión moderna de deps | Baja | DevEx | 2h |
| 17 | Documentación de API desalineada con código real | Baja | Documentación | 4h |
| 18 | Bare `except:` en portfolio routes | Baja | Calidad | 2h |
| 19 | Código muerto en dashboard (bloque HTML inalcanzable) | Baja | Limpieza | 1h |
| 20 | CORS hardcodeado a localhost sin configuración de producción | Baja | Seguridad | 1h |

**Deuda total estimada: ~136h de trabajo focalizado**

---

## 15. CONCLUSIÓN TÉCNICA

**TRADER AI v2.0.0** presenta una arquitectura bien concebida con un dominio rico y bien modelado, una estrategia de CI sólida y una base de código organizativamente coherente. El trabajo invertido en modelos de datos, kill switch, position sizing multi-asset y el pipeline de feature engineering es genuinamente valioso y de calidad técnica notable.

Sin embargo, **el sistema no puede operar como plataforma de trading algorítmico real** en su estado actual por cuatro razones fundamentales:

1. **La base de datos nunca se inicializa** en runtime — el sistema es completamente volátil; toda la data de órdenes, señales y portfolio se pierde al reiniciar.
2. **El pipeline automático de trading está desactivado** — el servidor es un sistema de consultas estático, no una plataforma de trading autónoma.
3. **El endpoint de ejecución de órdenes tiene un bug bloqueante** — `POST /execution` no puede completarse exitosamente por incompatibilidad de tipos.
4. **La validación del secreto JWT está programáticamente desactivada** — cualquier actor con conocimiento del secreto por defecto puede forjar tokens válidos.

La brecha entre especificación e implementación es **aproximadamente del 55%**: hay módulos excelentemente diseñados pero desconectados entre sí. El riesgo más silencioso es la arquitectura multi-worker con estado en memoria — si se desplegara con los 4 workers de uvicorn que indica el Dockerfile, cada worker tendría su propio `KillSwitch`, `OrderTracker` y `PortfolioManager` independientes, generando inconsistencias de estado que en un sistema financiero pueden resultar en pérdidas reales o decisiones de riesgo basadas en datos incorrectos.

**Recomendación estratégica:** antes de conectar capital real, completar la **Fase 0** (estabilización crítica, ~31h) y la **Fase 1** (pipeline autónomo, ~56h) con rigor de ingeniería. El sistema tiene una base arquitectónica sólida que justifica la inversión. Con 2–3 semanas de trabajo focalizado en los hallazgos P0/P1 identificados, TRADER AI puede convertirse en una plataforma de paper trading completamente funcional y segura, lista para iniciar el camino hacia operativa real con capital limitado bajo supervisión continua.

> **No conectar capital real hasta que Fase 0 y Fase 1 estén completas y auditadas.**

---

*Documento generado automáticamente por auditoría técnica integral el 16/05/2026.*
*Próxima revisión recomendada: tras completar Fase 0 (estimado: 30/05/2026).*
