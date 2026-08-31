# TRADER AI — SYSTEM AUDIT

**Audit Date:** 2026-08-28
**Repository Version/Commit:** `aeea1c5` (`main`) — "Unify exchanges, add token blacklist & MTF SL/TP"
**Auditoría:** Integral (arquitectura, quant, IA/ML, seguridad, riesgo/ejecución, testing, observabilidad, documentación)
**Estado del sistema:** **Development / pre-Paper-Trading.** No apto para capital real.
**Metodología:** verificación directa contra filesystem, código y ejecución de tests reales en este entorno. Los hallazgos de las auditorías `2026-05-16` y `2026-07-25` se usan como baseline pero se re-verificaron uno a uno.

> **Actualización 2026-08-30:** ver **[ADDENDUM — Avances F0–F2](#addendum--avances-f0f2-del-plan-de-elevación-2026-08-30)**. F-01 y F-03…F-08 cerrados en la rama de trabajo de F1; **F-02 confirmado y escalado a GATE F2 = NO-GO preliminar** (`docs/CORE_VALIDATION_DECISION_2026-08-30.md`).

> **Regla aplicada:** nada se marca como `IMPLEMENTED` por aparecer en documentación, tener una clase o un endpoint. Solo si se pudo trazar en el flujo real. Donde no se pudo ejecutar end-to-end (falta Postgres/Redis/broker en el entorno), se marca `UNKNOWN` explícitamente.

---

# EXECUTIVE SUMMARY

**Una frase:** TRADER AI es un sistema con una base de código grande y bien organizada, en el que las correcciones críticas de estabilidad y seguridad de mayo–julio **sí se aplicaron** (DB activa, scheduler activo, kill switch fail-safe, WebSocket autenticado, IDOR cerrado, gate I1 con criterio corregido), pero que sigue **sin evidencia de edge estadístico** (el gate I1 corregido reprueba 7 de 8 activos), con **una vía de escalada de privilegios nueva e inmediata** (`POST /auth/register` deja elegir rol `admin` sin autenticación), y con un **abismo entre lo que el pipeline de decisión real ejecuta y lo que el resto del sistema —estrategias, marketplace, dashboard, gate I1— describe y valida.**

**Madurez global: 4.6 / 10.** Sube desde el 5.3 de mayo en estabilidad e infraestructura, pero baja en honestidad quant (ahora que el gate mide bien, el resultado es negativo) y en seguridad (regresión por el endpoint de registro).

### Lo que mejoró de forma verificable desde 2026-07-25

| Hallazgo previo | Estado hoy | Evidencia |
|---|---|---|
| Kill switch falla **abierto** ante caída de Redis | ✅ **Resuelto** | `core/risk/kill_switch_redis.py:85-96` — `is_active()` devuelve `True` (bloquea) si Redis no responde; `KillSwitchRedisUnavailableError` propaga en `activate/reset`. Tests: `tests/unit/test_kill_switch.py` (209 asserts, verde). |
| Gate I1 aprueba ignorando el holdout | ✅ **Resuelto (criterio)** — ⚠️ **el resultado ahora es negativo** | `core/ml/i1_gate_validator/gate_validator.py:150-154` — `passed = sharpe_net_wf>=0.8 AND p<0.05 AND sharpe_net_holdout>=0.8`. Reporte regenerado `data/reports/i1_gate_report.json` (2026-07-26): **1/8 pasa (solo XAUUSD)**, `gate_approved: false`. |
| WebSocket de streaming sin autenticación | ✅ **Resuelto** | `api/routes/websocket.py:46-50` — rechaza con close `1008` antes de `accept()` si el JWT falta o es inválido. Tests: `tests/unit/test_websocket_auth.py` (9, verde). |
| IDOR en endpoints de órdenes | ✅ **Resuelto** | `api/routes/execution.py:218-228` `_owns_order()` + `:238-239, :255, :260, :274`. Órdenes con `user_id=None` tratadas como de nadie. Tests: `tests/unit/test_execution_idor.py` (verde). |
| DB nunca inicializada / scheduler comentado | ✅ **Resuelto** | `api/main.py:173-176` (`init_pool` + `run_migrations`), `:284-315` (APScheduler activo con `_pipeline_cycle`). |
| `POST /execution` roto por type mismatch | ✅ **Resuelto** | `core/risk/risk_manager.py:52-58` acepta `Signal | dict`; `execution.py:115-132` construye `Signal` con `explanation=[]`. |
| `and False` en validación de JWT secret | ⚠️ **Parcial** | `core/config/settings.py:103-108` — ahora `os.getenv("ENVIRONMENT")=="production"`; pero compose no setea `ENVIRONMENT`, y no hay chequeo de longitud/entropía. |
| `docker-compose.yml` YAML inválido | ✅ **Resuelto** | `docker/docker-compose.yml` — YAML válido, `nginx.conf` y `prometheus.yml` existen. |
| Suite de tests: 329 passed / 35 failed | ✅ **Muy mejorado** | Suite completa (21 min): **424 passed, 22 failed, 2 skipped, 2 errors**. `pytest tests/unit tests/quant`: **333 passed, 2 failed** (62 s). Los 22 fallos = **20 de `test_dashboard_e2e.py`** (requiere servidor vivo en `127.0.0.1:8000`, `ConnectionError`) + **2 de `test_hmm_regime_detector.py`**. Los 2 errores = teardown de `TestClient` sin Redis en `test_api_execution.py` / `test_api_sltp_config.py`. Es decir: **0 fallos de lógica** una vez descontada la falta de infraestructura. |
| Dashboard: 3 implementaciones + god file | ✅ **Resuelto** | SPA única `static/dashboard.html`; Streamlit archivado en `docs/archive/app_streamlit_legacy/`; `api/routes/dashboard.py` eliminado. Ver `docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`. |

### Lo que sigue abierto o empeoró

- **[P0 — NUEVO] Escalada de privilegios por registro abierto.** `POST /auth/register` (`api/routes/auth.py:44-67`) no requiere autenticación y acepta `role` del cuerpo: `Role(body.role)` valida contra el enum, que **incluye `admin`**. Cualquiera con acceso de red a la API se registra como admin. Rate limit `3/minute` es irrelevante.
- **[P0 — quant] Sin edge.** Gate I1 corregido: 7/8 activos con Sharpe holdout negativo (BTC −2.17, ETH −2.10, EURUSD −0.98, GBPUSD −0.95, USDJPY −1.49, US500 −3.96, US30 +0.64<0.8). Solo XAUUSD pasa. No hay base para avanzar a estrategias/ML sofisticados.
- **[P1 — arquitectura] Tres sistemas de "estrategia" desconectados.** (a) `core/strategies/builtin/*` (`AbcStrategy`: EmaRsi, MeanReversion, TSMOM, VolBreakout, CrossSectionalMomentum) → expuestas por API/marketplace/simulador; (b) `core/ml/i1_strategies.py` (`I1_STRATEGY_REGISTRY`: 7 estrategias) → solo el gate I1; (c) el pipeline de decisión real (`scripts/run_pipeline.py`) → **no usa ninguna de las dos**: usa agentes + `ConsensusEngine` + `SignalEngine` con `strategy_id="default_v1"` hardcodeado. Lo que se valida no es lo que se ejecuta; lo que se ejecuta no se valida.
- **[P1 — infra] `Dockerfile` corre `uvicorn --workers 4`** (`docker/Dockerfile:41`) con `_refresh_fundamental` y el **APScheduler dentro del `lifespan`** → 4 procesos ejecutando el mismo pipeline programado y el mismo refresh → señales/órdenes cuádruples. Redis cubre kill switch / order tracker / portfolio, pero no el scheduler ni `RiskManager`/`PaperExecutor`/caché de mercado en memoria.
- **[P1 — infra] `Dockerfile` no copia `alembic/` ni `alembic.ini`** → `run_migrations()` lanza excepción dentro del contenedor → `api/main.py:177-178` la traga → el contenedor arranca **sin DB, en silencio**. Tampoco copia `data/` (parquet) → dashboard sin datos en contenedor.
- **[P1 — quant/producto] "Productores" ausentes.** El store en memoria de `api/routes/signals.py` (`store_signal`/`update_signal_status`) nunca se llama; `ComplianceAuditSystem` nunca se instancia; `AlphaDecayMonitor` y el baseline de `DriftDetector` nunca se alimentan. El único productor real es `run_pipeline.py`, cuya ejecución end-to-end **no se pudo verificar** (requiere Binance + MT5 + Postgres + Redis).
- **[P2] Tres universos de activos inconsistentes.** `settings.SUPPORTED_SYMBOLS` (10: …SPX500, NAS100, USOIL) vs `run_pipeline.SCHEDULE` (12: …US500, US30, UK100, AUDUSD, USDCHF, USDCAD) vs `i1_gate_validator` (8) vs `data/raw/` (6 no-crypto). Nomenclatura de índices divergente (`SPX500` vs `US500`).
- **[P2] CI roto en el job de lint.** `.github/workflows/ci.yml:26` — `pip install ruff black bandita` (typo: `bandita`). El job `lint` falla siempre; los `needs: lint` posteriores no corren.
- **[P2] `test_dashboard_e2e.py` contamina la señal de test.** Sus 20 casos asumen un servidor FastAPI ya levantado en `127.0.0.1:8000` y no lo arrancan → **siempre** cuentan como 20 fallos en CI y en cualquier entorno sin arranque manual. Los `tests/integration/*` sí corren (2 errores de teardown por falta de Redis, no de aserción).

---

# ADDENDUM — Avances F0–F2 del Plan de Elevación (2026-08-30)

> Esta auditoría es una **instantánea en `aeea1c5`**. Lo de abajo NO la reescribe:
> registra el estado de sus hallazgos tras ejecutar F0–F2 del
> `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`. El trabajo vive en una rama sobre
> `043d218`, **sin commitear**, y **pendiente del pase de auditoría fresca** que el
> plan exige. Detalle por entregable: `docs/PROGRESS.md`.

## Estado de los hallazgos críticos

| ID | Hallazgo (resumen) | Sev. original | Estado 2026-08-30 | Evidencia del cambio |
|---|---|---|---|---|
| **F-01** | `POST /auth/register` permite auto-asignarse `admin` | P0 | ✅ **CERRADO** | `REGISTRATION_ENABLED` (default false); `/register` sin campo `role`, solo crea `viewer`; nuevo `POST /auth/users` con `require_admin`; validador `JWT_SECRET_KEY` siempre activo (≥32, ≠ default). `tests/unit/test_security_floor.py` (6 ✅). Plan F1.7. |
| **F-02** | Sin edge: gate I1 reprueba 7/8 activos | P0 | ⛔ **CONFIRMADO y ESCALADO a GATE NO-GO** | 2.5: `data/reports/quant_report.*` — solo XAUUSD con WF+holdout consistentes. 2.6: `data/reports/edge_robustness.*` — XAUUSD/Momentum **FRÁGIL** (CI Monte Carlo holdout **[−1.43, +3.76]**, mono-régimen ADX). Veredicto: `docs/CORE_VALIDATION_DECISION_2026-08-30.md` → **NO-GO preliminar**. |
| **F-03** | El pipeline real decide con `strategy_id="default_v1"` fijo; 3 registros de estrategia desconectados | P1 | ✅ **CERRADO** | `core/strategies/approved_params.py` (contrato `data/models/i1_params/<SYMBOL>.json`); el gate I1 escribe el archivo por activo `passed`; `run_pipeline` carga params por activo (Gate 0b `no_approved_strategy` fail-safe) + confirmación de estrategia; `StrategyRegistry` pliega `I1_STRATEGY_REGISTRY`; `grep -rn "default_v1" scripts core` → 1. Plan F1.4. |
| **F-04** | 4 workers uvicorn con scheduler embebido → pipeline/órdenes ×4 | P1 | ✅ **CERRADO** | APScheduler y `_refresh_task` fuera del `lifespan`; `scripts/run_pipeline.py` único dueño con lock Redis (`SET NX EX` + renovación Lua); servicio `worker` en compose. `tests/unit/test_scheduler_split.py` (7 ✅). Plan F1.1. |
| **F-05** | Contenedor arranca sin DB en silencio (falta `alembic/` en la imagen) | P1 | ✅ **CERRADO** | `Dockerfile` `COPY alembic/` + `alembic.ini`; `alembic/env.py` async (asyncpg, sin psycopg2) leyendo `DATABASE_URL` de env; servicio one-shot `migrate` que bloquea `app`/`worker`; arranque **falla** si `EXECUTION_MODE=live` y la DB no inicializa; `/health.db_initialized`. Plan F1.2/F1.9. |
| **F-06** | Cadena de trazas sin productor (`store_signal`/`AuditLog`/alpha-decay nunca invocados) | P1 | ✅ **CERRADO (núcleo)** | `correlation_id` generado en `_pipeline_cycle` y propagado a features/agentes/consenso/señal; `TraceStore` (Redis + fallback memoria) registra 8 etapas; `AuditLog` por decisión; señal persistida vía repo; `GET /trace/{id}`. `tests/unit/test_pipeline_trace.py` (3 ✅). **Diferido:** columna DB `correlation_id` (migración → Plan F3.2). Plan F1.6. |
| **F-07** | Job `lint` de CI roto (typo `bandita`); dependientes no corren | P1 | ✅ **CERRADO** | `bandita`→`bandit`; job de integración con `services: postgres+redis` y `-m integration`; `unit-tests` con `-m "not slow and not integration"`. Verde local; **falta el primer push a CI** (condición abierta de F1). Plan F1.8. |
| **F-08** | Enforcement de `JWT_SECRET_KEY` solo en `production`, sin chequeo de longitud | P1 | ✅ **CERRADO** | Validador siempre activo: `len ≥ 32` y `≠ "change-me-in-production"`, salvo `ALLOW_INSECURE_JWT=true` explícito (solo tests). Plan F1.7. |
| **F-09** | `RiskManager.validate_signal` no agrega riesgo de posiciones abiertas ni correlación | P1 | ✅ **PARCIAL** | `aggregate_open_exposure(portfolio, capital)` (Σ posiciones abiertas + señal nueva vs `MAX_PORTFOLIO_RISK_PCT`) + chequeo directo de pérdida diaria en `validate_signal`. `tests/unit/test_risk_decision_correctness.py` (6 ✅). Plan F1.5. **Falta:** límite por correlación/cluster → Plan F6.1. |

## Deuda técnica y hallazgos P2 tocados

- **Universo de activos (P2, G-10/D-11):** `TRADED_UNIVERSE` único en `core/config/constants.py` (8 símbolos, `US###`), importado por `settings.SUPPORTED_SYMBOLS`, `run_pipeline.SCHEDULE` y `i1_gate_validator.PIPELINE_SYMBOLS`. `SPX500`→`US500`. `tests/unit/test_universe_single_source.py` (13 ✅). Plan F1.3.
- **HMM roto (D-12):** `hmm_regime_detector` — drop de filas no finitas, `MIN_TRAIN_SAMPLES`, nº de estados adaptativo, `covariance_type="diag"` + `min_covar`. 12 tests verdes (antes 2 ❌). Plan F1.5.
- **`test_dashboard_e2e.py` mal diseñado (P2):** ahora `@pytest.mark.integration` + fixture `live_server` (uvicorn en puerto libre, arranque ligero). Deselección por defecto vía `pytest.ini`. Plan F1.8.
- **Datos (nuevo, Plan F2.4):** `scripts/audit_data_quality.py` → **0 violaciones duras** en los 6 parquet 1h (UTC, monótonos, sin dups, OHLC íntegro). `core/features/indicators.py`: **sin look-ahead**. `core/ml/target_engine.py`: 6 puntos de look-ahead (umbral/cortes sobre serie completa) **no cableados** — trampa para F5. `docs/audits/AUDIT_F2_4_LEAKAGE_2026-08-30.md`. **BTC/ETH: sin parquet 1h.**

## Efecto neto sobre el score

Las correcciones F1 elevan varias áreas (Seguridad, Estrategias, Risk, Observabilidad,
Testing, Performance, DevSecOps, Multi-Asset) — estimación en `docs/audits/AUDIT_F1_2026-08-30.md`:
**global ~4.6 → ~5.4**. Pero **Quant sigue en 2.5**: el gate F2 confirma que **no hay
edge robusto demostrable** en el universo actual. Mientras eso no cambie, el techo de
madurez global del sistema está limitado por (b) — ninguna mejora de arquitectura,
seguridad u observabilidad lo levanta.

## Recomendación actualizada

La **FINAL RECOMMENDATION** de esta auditoría sigue vigente en lo esencial: el bloqueo
de fondo es **F-02**. Con F1 hecho, el sistema ya es *auditable y determinista* — se
puede medir el edge sin ambigüedad — y la medición dio negativa. El siguiente paso es
el **mini-plan de pivote** de `docs/CORE_VALIDATION_DECISION_2026-08-30.md` (datos más
largos, revisión de costos de XAUUSD, estrategias alternativas; luego otros
timeframes/familias; luego replanteo de universo o de producto), **no** avanzar a
F3–F10.

---

# SYSTEM MATURITY SCORE

| Área | Score /10 | Sustento (evidencia) |
|---|---|---|
| Arquitectura | 5.5 | Hexagonal declarada (`domain/`, `application/ports/`) y limpia en el núcleo, pero **conviven dos árboles**: `domain/application/infrastructure/interfaces/` (26 archivos, poco usados) y `core/` (166 archivos, donde vive todo lo real). Lógica de negocio filtrada a la API (`execution.py:125-126` calcula R:R en el handler). Singletons vía globals de módulo + `app.state`. |
| Código | 5.5 | Type hints consistentes, ruff/black/mypy configurados. 148 `except Exception`/`except:` en `core/`+`api/` (varios tragan errores). 3 `god files` conocidos siguen (ver Deuda). Solo 3 TODO/FIXME. |
| SOLID | 4.5 | SRP: god files. OCP: `exchange_registry._instantiate_client` sigue siendo if/elif por exchange (`core/ingestion/exchange_registry.py:74-113`). LSP: mejoró — hay un `ExchangeAdapter` ABC canónico, pero `binance_client`/`oanda_client`/`alpha_vantage_client` aún lanzan `NotImplementedError` en `place_order`/`cancel_order`. DIP: `domain/` limpio; API acoplada a singletons. |
| DDD | 4.0 | Entidades ricas (`Signal`, `Order`, `Portfolio` con validadores). Sin bounded contexts explícitos, sin domain events, sin aggregates formales. `core/` es un paquete técnico, no un modelo de dominio. |
| Core Trading | 5.0 | El flujo existe y está codificado end-to-end en `scripts/run_pipeline.py` (gates de calendario, evento macro, features, agentes, consenso, riesgo, sizing, ejecución, persistencia, alerta). **No verificado en ejecución real.** Consenso y SignalEngine son implementaciones reales, no stubs. |
| Quant | 2.5 | Gate I1 metodológicamente correcto (walk-forward + purged 5-fold + holdout 20% + bootstrap p-value + CostModel por clase de activo) y ahora **honesto**: 1/8 activos. Sin expectancy/profit-factor/Calmar documentados por estrategia. `sharpe_ratio` casero en `core/backtesting/metrics.py`. |
| Estrategias | 3.0 | 5 builtin (`AbcStrategy`) + 7 en `I1_STRATEGY_REGISTRY`, **ninguna en el path de decisión real**. Sin validación out-of-sample por estrategia salvo lo que hace el gate I1 sobre su propio registro. |
| IA/ML | 3.5 | LightGBM real para BTC/ETH/US30/US500 en `data/models/i1_ml/`. `TechnicalAgent` cae a reglas si no hay `.pkl` (y los `.pkl` que el pipeline busca —`data/models/technical_crypto_v1.pkl`— probablemente no existen). Sin registro de métricas por modelo (confirmado: `metrics_tracked:false` en `/models`). `drift_detector`/`alpha_decay_monitor`/`online_learning_agent`/`rl_trading_agent` presentes pero **no cableados**. |
| Adaptabilidad | 3.5 | Pesos de consenso dinámicos por EWMA de accuracy (`voting_engine.py:78-94`) — pero `record_trade_result` no se llama desde ningún flujo. Pesos por `asset_class` sí aplican. `strategy_rotation.py`, `auto_adaptation.py`, `regime_watcher.py` presentes; integración no verificada. |
| Multi-Asset | 4.0 | `detect_asset_class`, `InstrumentConfig` (pip/lot por símbolo), pesos de consenso crypto vs MT5, `MarketCalendar`. Pero universo inconsistente en 3 sitios y solo 6 símbolos no-crypto con datos. MT5 = 0 configurado → forex/índices/oro se **saltan** en el pipeline. |
| Risk | 5.5 | Kill switch fail-safe (bien), R:R mínimo, drawdown, límite de riesgo. **Debilidad:** `validate_signal` mide el riesgo de *la señal entrante* contra `MAX_PORTFOLIO_RISK_PCT`, no suma el riesgo de posiciones abiertas; sin chequeo de correlación; sin límite de pérdida diaria en `validate_signal` (solo en trigger del kill switch). |
| Execution | 4.5 | `PaperExecutor` con slippage e idempotencia por `idempotency_key`. `OrderTracker` en Redis. Ejecutores live (Binance/Bybit/OANDA/IB/MT5) presentes; `NotImplementedError` en `live_executor.py:123,128` y `mt5_executor.py:132,137`. Sin reconciliación verificada, sin manejo probado de rechazo/desconexión. |
| Market Data | 4.5 | Parquet 1h/4h/1d para 6+2 símbolos. `BinanceClient` real. `ExchangeAdapter` ABC unifica interfaz. Sin normalización de timestamps/timezone verificada; `/market/EURUSD/features` documentado con `500` por `NaN` no JSON-compliant (`PLAN_MIGRACION_DASHBOARD` §1b.7). |
| Testing | 5.5 | 448 tests. Suite completa: 424✅/22❌/2 err (21 min). Fallos reales de lógica: **solo 2** (HMM); los otros 20 son `test_dashboard_e2e.py` sin servidor. Buen uso de Hypothesis. `api/routes/` con cobertura baja. `test_dashboard_e2e.py` mal diseñado (no arranca el server). Gate I1 ≠ `ci_backtest_gate` (smoke sobre OHLCV sintético). |
| Seguridad | 3.0 | **Regresión P0**: registro abierto con rol `admin`. JWT secret con enforcement débil. Blacklist fail-open (documentado y razonado). Rate limiting real vía slowapi en auth/execution/kill-switch. RBAC aplicado. CORS con allowlist. Sin secretos hardcodeados (grep limpio). `python-jose==3.3.0` (CVEs históricos). |
| Usuarios/Accesos | 3.5 | Roles `admin/trader/analyst/viewer` en `core/auth/permissions.py`. Login/refresh/logout/register/me. **`register` rompe el modelo de roles.** `refresh` sin rate limit; logout no revoca el refresh token. |
| Observabilidad | 4.5 | `structlog` estructurado en todo el core, Prometheus en :8001, `decision_tracer.py`, `AuditLog` JSONL. **Pero** el audit trail no tiene productor, no hay dashboards de Grafana provisionados con paneles reales, sin tracing distribuido, sin correlation IDs entre capas. |
| Performance | 4.5 | `_load_parquet_data` ya en `asyncio.to_thread`. `_refresh_task` con cancelación. Riesgos: 4 workers duplican trabajo; carga de parquet en cada arranque; `calculate_all` CPU-bound; sin backpressure real en el scheduler más allá de `max_instances=1`. |
| DevSecOps | 4.0 | CI con lint/mypy/unit/integration/safety/i1/backtest/docker-build — **pero el job lint falla por el typo `bandita`**, `i1-gate` es `continue-on-error`, no hay quality gate de cobertura, no hay dependency scanning (pip-audit/safety real), no hay CD. Pre-commit configurado. |
| Documentación | 3.5 | Enorme (`PLAN_MAESTRO.md` 60 KB, `PROYECTO_COMPLETO.md`, `ESTADO_PROYECTO.md`, `TRADER_AI_PROMPT_MAESTRO.md` 96 KB…). `docs/architecture/*` describe Streamlit como frontend (obsoleto). ~9 docs raíz con instrucciones parcialmente corregidas. Specs solo para 5 módulos (`specs/SPEC-001..005`). Sin ADRs. Solapamiento y contradicción entre documentos de estado. |
| Escalabilidad | 3.5 | Monolito. Estado parcialmente en Redis. Scheduler in-process no apto para multi-worker/multi-instancia. Sin cola de tareas. Sin sharding de símbolos. |

**Score global ponderado: 4.6 / 10.**

---

# CRITICAL FINDINGS (P0 / P1)

| ID | Área | Hallazgo | Evidencia | Sev. | Recomendación |
|---|---|---|---|---|---|
| F-01 | Seguridad | `POST /auth/register` sin auth permite `role="admin"` → escalada de privilegios total | `api/routes/auth.py:44-67`; `core/auth/permissions.py` (enum `Role` incluye `ADMIN`) | **P0** | Quitar `role` del `RegisterRequest` (forzar `viewer`/`trader`); o exigir `require_admin` para crear cuentas; o feature-flag `REGISTRATION_ENABLED=false` por defecto. Añadir test que registre `admin` y espere 403. |
| F-02 | Quant | Sin edge estadístico: gate I1 corregido reprueba 7/8 activos (Sharpe holdout negativo) | `data/reports/i1_gate_report.json` (2026-07-26): `symbols_passed:1`, `gate_approved:false` | **P0** | Congelar cualquier trabajo de "estrategias avanzadas" / ML / RL. Reenfocar en encontrar un edge robusto en 1–2 activos (XAUUSD es el candidato) con más datos y estrategias más simples antes de escalar. |
| F-03 | Arquitectura | El pipeline de decisión real no usa las estrategias registradas ni las validadas por I1 | `scripts/run_pipeline.py:222` (`strategy_id="default_v1"` fijo); `StrategyRegistry` solo alimenta API/simulador; `I1_STRATEGY_REGISTRY` solo alimenta el gate | **P1** | Decidir UNA fuente de verdad de estrategias. Conectar el resultado del gate I1 (params por activo en `data/models/i1_params/`) al `SignalEngine`/pipeline, o documentar explícitamente que el pipeline de agentes es el sistema y el resto es exploratorio. |
| F-04 | Infra | `Dockerfile` corre 4 workers uvicorn con scheduler + refresh dentro del `lifespan` | `docker/Dockerfile:41`; `api/main.py:255` (`_refresh_task`), `:296-307` (scheduler) | **P1** | Mover scheduler y refresh a un proceso worker dedicado (`scripts/run_pipeline.py` ya existe como tal) y dejar la API con N workers sin jobs; o `--workers 1` + `guard` por lock Redis en el arranque del scheduler. |
| F-05 | Infra | Contenedor arranca sin DB en silencio: falta `alembic/` + `alembic.ini` en la imagen | `docker/Dockerfile:24-29` (no copia alembic); `core/db/migrate.py:16` (`Config("alembic.ini")`); `api/main.py:177-178` traga la excepción | **P1** | `COPY alembic/ ./alembic/` y `COPY alembic.ini .` en el Dockerfile. Hacer que el arranque **falle** si `EXECUTION_MODE=live` y la DB no inicializa. |
| F-06 | Quant/Producto | Cadena de observabilidad de decisiones sin productor: `store_signal`, `AuditLog`, `AlphaDecayMonitor`, baseline de drift nunca se invocan | grep: `store_signal`/`update_signal_status` 0 llamadas; `ComplianceAuditSystem` 0 instancias; `PLAN_MIGRACION_DASHBOARD` §1b.15-16 lo confirma | **P1** | Cablear `run_pipeline._pipeline_cycle` para: persistir señal vía `SignalRepository`, registrar decisión en `AuditLog`, alimentar `record_trade()` del alpha-decay tras cierre de posición. Sin esto, "reconstruir Market State → Decision → Order → Fill" es imposible. |
| F-07 | Testing/DevSecOps | Job `lint` de CI roto (typo `bandita`); jobs dependientes no corren | `.github/workflows/ci.yml:26` | **P1** | `pip install ruff black bandit`. Añadir `pip-audit`/`safety` como job propio. Hacer `i1-gate` informativo pero visible (no `continue-on-error` silencioso). |
| F-08 | Seguridad | Enforcement de `JWT_SECRET_KEY` solo si `ENVIRONMENT=production`; compose no lo setea; sin chequeo de longitud | `core/config/settings.py:103-108`; `docker/docker-compose.yml` (sin `ENVIRONMENT`) | **P1** | Validar siempre: `len(v) >= 32` y `v != "change-me-in-production"`, salvo un `ALLOW_INSECURE_JWT=true` explícito para tests. |
| F-09 | Riesgo | `RiskManager.validate_signal` no agrega el riesgo de posiciones abiertas ni correlación | `core/risk/risk_manager.py:58-100` — compara exposición de la señal entrante contra `MAX_PORTFOLIO_RISK_PCT`; no suma posiciones existentes | **P1** | Calcular exposición de cartera = Σ(|entry−SL|·qty)/capital sobre posiciones abiertas + la nueva. Añadir límite por correlación y límite de pérdida diaria en `validate_signal` (no solo en el trigger del kill switch). |

---

# ARCHITECTURE AUDIT

## Arquitectura real (reconstruida del código)

```
                         ┌───────────────────────────────────────────┐
   Cliente ── HTTP/WS ──▶ │ FastAPI (api/main.py, lifespan monolito)   │
                         │  routers: auth, market, signals, execution,│
                         │  portfolio, risk, strategies, marketplace,  │
                         │  simulation, backtesting, models, monitoring│
                         │  drawings, indicators, websocket            │
                         └───────┬───────────────────────────┬─────────┘
                                 │ singletons vía globals    │ app.state
                                 ▼                           ▼
   ┌──────────────── core/ (paquete técnico, 166 .py) ─────────────────┐
   │ ingestion(Binance/Bybit/OANDA/IB/MT5/AlphaVantage + adapter/reg)  │
   │ features(feature_engineering, indicators, store, validator, hurst)│
   │ adaptation(HMM regime, pure_hmm, regime_watcher, retraining)      │
   │ agents(technical, regime, microstructure, fundamental, asset_spec)│
   │ consensus(voting_engine ▶ ConsensusOutput, conflict_logger)       │
   │ signals(signal_engine ▶ Signal, xai_module)                       │
   │ risk(risk_manager, position_sizer, kill_switch[_redis], mtf_sl_tp,│
   │      portfolio_risk_engine, user_profile_engine, vol_targeting)   │
   │ execution(paper_executor, order_tracker[_redis], live_* executors)│
   │ portfolio(manager[_redis], optimizer, rebalancer, factory)        │
   │ ml(i1_gate_validator/*, i1_strategies, drift, alpha_decay,        │
   │    online_learning, rl_trading, model_validation_gate, edge_res.) │
   │ strategies(base + builtin/*, registry, rotation, marketplace)     │
   │ db(session[asyncpg pool], repositories, migrate[alembic])         │
   │ observability(structlog, decision_tracer) · monitoring(prometheus,│
   │   alert_engine, perf_tracker) · compliance(audit_system)          │
   └──────────────────────────────────────────────────────────────────┘
        │                                   ▲
        ▼ (proceso separado, NO la API)     │
   scripts/run_pipeline.py ── APScheduler ──┘   (también embebido en lifespan)
      SCHEDULE[12 símbolos] ▶ _pipeline_cycle:
        calendar gate ▶ macro-event gate ▶ OHLCV(Binance|MT5) ▶ features
        ▶ agents(tech/regime/micro) ▶ ConsensusEngine ▶ SignalEngine
        ▶ RiskManager.validate ▶ PositionSizer ▶ PaperExecutor|MT5Executor
        ▶ PortfolioManager ▶ kill_switch.check ▶ repo/feature_store ▶ Alert

   Infra: Postgres/TimescaleDB (7 migraciones alembic) · Redis (kill switch,
          order tracker, portfolio, feature store) · Prometheus/Grafana ·
          Nginx · static/dashboard.html (SPA única)
```

## Documentada vs Real

| Componente | Esperado (docs) | Real | Diferencia | Riesgo |
|---|---|---|---|---|
| Frontend | Streamlit (`app/`) — `docs/architecture/*` | SPA vanilla `static/dashboard.html` | Streamlit **archivado**; docs de arquitectura no actualizados | Medio (confunde onboarding) |
| Capas | Clean/Hexagonal `domain/application/infrastructure` | Todo lo real en `core/`; `domain/*` casi sin uso | Dos árboles paralelos | Alto (deuda estructural, ambigüedad de dónde va el código nuevo) |
| Pipeline | Autónomo, multi-activo, adaptativo | Codificado; MT5 desconectado; ejecución real no verificada; 4× por workers | `divergent` | Alto |
| Estrategias | Registrables, rotación dinámica, marketplace | 3 registros desconectados; decisión real con 1 strategy_id fijo | `divergent` | Alto |
| Gate I1 | "APPROVED 8/8" (docs de mayo) | `gate_approved:false`, 1/8 | Documentación de estado obsoleta | Crítico si se usa para decidir |
| Persistencia | TimescaleDB activa | Activa en `lifespan`; se degrada a "sin DB" ante fallo | `partially aligned` | Medio |
| Observabilidad de decisiones | Trazable Market→Decision→Order→Fill | Infra presente, **sin productor** | `divergent` | Alto |

**Veredicto arquitectónico:** el diseño conceptual es razonable para un monolito modular; la ejecución tiene **fragmentación** (dos árboles de capas, tres registros de estrategias, tres universos de activos, dos lugares que arrancan el scheduler) que multiplica el costo de cada cambio y hace que "lo que el sistema hace" no sea deducible de "lo que el sistema documenta".

---

# SOLID AUDIT

| Violación | Ubicación | Sev. | Impacto | Solución |
|---|---|---|---|---|
| SRP — god file | `core/risk/mtf_sl_tp_manager/manager.py` + módulo (ATR, Fibonacci, quality_filter, config, orquestación) | Media | Auditabilidad de la lógica de SL/TP | Ya está parcialmente partido en submódulos; terminar de separar cálculo puro vs política. |
| SRP — god file | `core/models/asset_specific_models/*` (enums + 6 modelos + factories + specs + training_config) | Media | — | Aceptable si cada archivo tiene una responsabilidad; revisar `specs.py`. |
| OCP | `core/ingestion/exchange_registry.py:74-113` (`_instantiate_client` if/elif por exchange) | Media | Añadir un exchange = editar este método | Constructor uniforme `from_config(ExchangeConfig)` en cada adapter + registro por decorador. |
| LSP | `core/ingestion/binance_client.py:105-108`, `oanda_client.py:153-159`, `alpha_vantage_client.py:249-268` — `place_order`/`cancel_order` → `NotImplementedError` | Media | Un caller genérico sobre `ExchangeAdapter` puede romper en runtime | Segregar interfaces: `MarketDataSource` vs `TradingVenue`. AlphaVantage solo implementa la primera. |
| LSP | `RiskManager(kill_switch: KillSwitch)` recibe `KillSwitchRedis` (jerarquías distintas, duck-typed) | Baja | — | Definir `KillSwitchProtocol` (typing.Protocol) y tiparlo así. |
| DIP | `api/routes/execution.py:125-126` calcula `risk_reward_ratio` en el handler | Baja | Lógica de dominio en la capa de presentación | Mover a `Signal` (factory) o a un `SignalAssembler`. |
| ISP | `application/ports/*.py` — **cumple** (interfaces cohesivas) | — | — | Mantener; considerar migrar `core/` a consumir estos puertos. |

---

# DDD AUDIT

- **Entities / Value Objects:** `Signal`, `Order`, `Portfolio`, `MarketData`, `FeatureSet`, `ConsensusOutput`, `AgentOutput` — modelados como Pydantic con validadores. Ricos pero anémicos en comportamiento (la lógica vive en servicios `core/*`).
- **Aggregates:** no hay raíces de agregado explícitas. `Portfolio` + posiciones sería la candidata natural.
- **Domain services:** `SignalEngine`, `ConsensusEngine`, `RiskManager`, `PositionSizer` cumplen ese rol de facto.
- **Repositories:** `core/db/repositories/*` (signal, order, audit) + `core/db/repository.py` (`TradingRepository`) — **dos abstracciones de repo distintas** (la API usa las primeras, el pipeline usa `TradingRepository`). Consolidar.
- **Domain events:** ausentes. No hay `SignalGenerated` / `OrderFilled` / `KillSwitchTriggered` como eventos; todo es llamada directa + logging.
- **Bounded contexts:** implícitos (ingestion / decisión / ejecución / riesgo / cumplimiento) pero sin fronteras de código ni de lenguaje.

**Veredicto:** DDD "táctico" parcial (entidades + servicios + repos), sin DDD "estratégico" (contexts, eventos, agregados). Para el tamaño actual es defendible; documentarlo como decisión.

---

# QUANT CORE AUDIT

**Lo que es real y correcto:**
- `core/ml/i1_gate_validator/` — metodología sólida: split holdout 20% **antes** de optimizar, walk-forward sobre el 80%, purged 5-fold (embargo 5 barras), `bootstrap_pvalue_wf` (1000 resamples), `CostModel` por clase de activo, cooldown y filtro de régimen (ADX≥20) configurables por activo. El criterio de paso ahora incluye el holdout (`gate_validator.py:150-154`).
- El resultado regenerado es **creíble y negativo**:

| Símbolo | Sharpe net WF | p-value | Sharpe net **holdout** | passed |
|---|---|---|---|---|
| BTCUSDT | 1.70 | 0.047 | **−2.17** | ❌ |
| ETHUSDT | 1.87 | 0.049 | **−2.10** | ❌ |
| EURUSD | 2.45 | 0.015 | **−0.98** | ❌ |
| GBPUSD | 2.22 | 0.027 | **−0.95** | ❌ |
| USDJPY | 2.97 | 0.003 | **−1.49** | ❌ |
| US500 | 2.44 | 0.100 | **−3.96** | ❌ |
| US30 | 3.32 | 0.031 | **+0.64** (<0.8) | ❌ |
| XAUUSD | 2.61 | 0.001 | **+1.32** | ✅ |

- Interpretación: Sharpe WF alto + holdout negativo en 7/8 = **sobreajuste al proceso de walk-forward**. El único activo con señal consistente es XAUUSD, y con n=1 no es una base para un sistema multi-activo.

**Lo que falta:**
- Métricas por estrategia y por activo más allá del Sharpe: expectancy, profit factor, win rate, Sortino, Calmar, max drawdown, exposure, tail ratio — no hay un reporte consolidado.
- Análisis de alpha decay real (el monitor existe, no se alimenta).
- Sensibilidad a costos: el `CostModel` existe pero no hay un barrido "¿a partir de qué spread/comisión desaparece el edge de XAUUSD?".
- Regime-dependency del edge (¿XAUUSD funciona en todos los regímenes o solo en tendencia?).

**Recomendación quant (Regla 3 y 4 del prompt):** no tratar XAUUSD como "estrategia ganadora" con un solo holdout positivo. Antes de FASE 3/4: ampliar histórico, correr Monte Carlo sobre el equity, stress test de costos, y walk-forward anclado con re-optimización periódica. **No** introducir ML/RL sobre un baseline no confirmado.

---

# STRATEGY AUDIT

| Estrategia | Registro | Activos/TF | Usada por | Validación | Estado |
|---|---|---|---|---|---|
| EMA Crossover + RSI (`ema_rsi.py`) | builtin `AbcStrategy` | genérico / 1h | API `/strategies`, simulador | ninguna propia | `CODE_ONLY` |
| Bollinger Mean Reversion (`mean_reversion.py`) | builtin | genérico | API, simulador | ninguna | `CODE_ONLY` |
| Time-Series Momentum (`tsmom.py`) | builtin | genérico | API, simulador | ninguna | `CODE_ONLY` |
| Volatility Breakout (`volatility_breakout.py`) | builtin | genérico | API, simulador | ninguna | `CODE_ONLY` |
| Cross-Sectional Momentum (`cross_sectional_momentum.py`) | builtin | multi-símbolo | API, simulador | ninguna | `CODE_ONLY` |
| `tsmom_v1`, `vol_breakout_v1`, `mean_rev_v1`, `ema_rsi_v1`, `ml_lgb_v1`, `BB_ZScore`, `Momentum` | `I1_STRATEGY_REGISTRY` | 8 símbolos I1 / 1h | **solo gate I1** | walk-forward + holdout (reprueba 7/8) | `PARTIALLY_IMPLEMENTED` |
| `default_v1` | ninguno (string literal) | pipeline / 1h | **el pipeline real** | ninguna — es el output del consenso de agentes | `IMPLEMENTED` (pero no es una "estrategia", es el consenso) |

**Hallazgo central:** hay 12+ artefactos llamados "estrategia" y el sistema que decide operaciones no consume ninguno como tal. `strategy_rotation.py`, `meta_agent.py`, `ab_testing.py` (x2, en `core/ml/` y `core/strategies/`), `strategy_marketplace.py` amplifican la superficie sin cerrar el bucle.

---

# AI/ML AUDIT

| Componente | Estado | Evidencia |
|---|---|---|
| `TechnicalAgent` | `IMPLEMENTED` con fallback a reglas | `run_pipeline.py:88-89` apunta a `data/models/technical_crypto_v1.pkl` / `technical_forex_v1.pkl` — **no confirmados en disco**; sí hay `data/models/i1_ml/*.pkl` para BTC/ETH/US30/US500. |
| `RegimeAgent` / HMM (`hmm_regime_detector.py`, `pure_hmm.py`) | `PARTIALLY_IMPLEMENTED` | 2 tests fallando (`test_fit_handles_nan`, `test_predict_with_insufficient_data`). El pipeline usa `_make_regime_gate` (heurística sobre score), no el HMM. |
| `MicrostructureAgent` | `IMPLEMENTED` (crypto only) | Peso 0 para MT5 (sin L2). |
| `FundamentalAgent` | `IMPLEMENTED` | `refresh()` cada 30 min; `is_blocked_by_event` gatea el pipeline. |
| `asset_specific_agent` / `asset_specific_models` | `PARTIALLY_IMPLEMENTED` | Presente y expuesto en `/models`; integración en el pipeline no verificada. |
| `drift_detector` | `CODE_ONLY` | Sin baseline persistido; `/monitoring/drift` calcula JS-divergence ad-hoc sobre el caché. |
| `alpha_decay_monitor` | `CODE_ONLY` | `wired:false` explícito en `/monitoring/alpha-decay`. |
| `online_learning_agent`, `rl_trading_agent` | `CODE_ONLY` — **correcto que no estén activos** (prerequisito I1 no cumplido) | — |
| `model_validation_gate`, `ab_testing`, `stress_testing`, `edge_research` | `CODE_ONLY` / exploratorio | `edge_research.py` es implementación paralela previa al gate I1 modularizado. |
| Registro de métricas por modelo | **Inexistente** | Confirmado por el equipo en `PLAN_MIGRACION_DASHBOARD` §1b.8: `accuracy/f1/precision = null`, `metrics_tracked:false`. |

**Riesgos de sesgo:** el gate I1 mitiga look-ahead (holdout previo a optimización, señal con lag de 1 barra, purga+embargo). No hay evidencia de control de **survivorship bias** (universo fijo elegido a mano) ni de **feature leakage** en `feature_engineering.py` (no auditado línea a línea aquí — pendiente).

---

# MARKET DATA AUDIT

- **Proveedores:** `BinanceClient` (real, usado), `MT5Client` (usado si `MT5_LOGIN≠0`; hoy 0 → forex/índices/oro **no operan**), `OANDA/Bybit/IB/AlphaVantage` (`CODE_ONLY`).
- **Abstracción:** `ExchangeAdapter` ABC (`get_klines`, `get_order_book`, `get_balance`, `place_order`, `cancel_order`, `get_order_status`) + `ExchangeRegistry`. Mejora real vs. julio (había dos jerarquías). Falta: que todos los clientes hereden de verdad de `ExchangeAdapter` y que `run_pipeline` los obtenga vía el registry en vez de importar `BinanceClient` directamente.
- **Datos:** parquet 1h/4h/1d para eurusd, gbpusd, usdjpy, us30, us500, xauusd (+ crypto). `data/processed/` sigue sin existir.
- **Calidad:** `data_validator.py`, `feature_validator.py` presentes. Bug conocido de serialización `NaN`→JSON en `/market/{symbol}/features`. Sin verificación de timezone/gaps/outliers en esta auditoría.
- **Cambio de proveedor sin tocar el core:** **parcial** — posible vía registry para la API, no para el pipeline.

---

# RISK AUDIT

Cadena real (`run_pipeline._pipeline_cycle`): `SignalEngine.generate` → `RiskManager.validate_signal` → `RiskManager.calculate_position_size` (`PositionSizer`, InstrumentConfig-aware) → executor → `PortfolioManager.open_position` → `kill_switch.check_and_trigger`.

**Correcto:**
- El kill switch puede vetar cualquier señal con confianza alta (`validate_signal` chequea `is_active()` primero).
- Kill switch fail-safe ante Redis caído.
- R:R mínimo (`HARD_LIMITS["min_risk_reward_ratio"]`) chequeado en `SignalEngine` **y** `RiskManager`.
- `PositionSizer` multi-activo con pip/lot por `InstrumentConfig`.
- SL/TP adaptativo por percentiles de ATR (`signal_engine.py:41-73`) + `mtf_sl_tp_manager` (ATR + Fibonacci).

**Débil / faltante:**
- **Exposición de cartera:** `validate_signal` calcula el riesgo de la señal entrante, no Σ de posiciones abiertas (F-09). Un sistema puede abrir N posiciones cada una <10% y quedar 40% expuesto.
- Sin límite por **correlación** entre posiciones (EURUSD+GBPUSD+XAUUSD son correlacionados).
- El **límite de pérdida diaria** solo dispara el kill switch reactivamente; `validate_signal` no lo consulta.
- `update_kill_switch` en el pipeline se llama con `recent_trades=[]` (`run_pipeline.py:264`) → el trigger de "pérdidas consecutivas" **nunca se evalúa con datos reales** en ese flujo.
- `portfolio_risk_engine.py`, `adaptive_position_risk.py`, `volatility_targeting.py` existen pero su integración en el flujo real no está confirmada.

---

# EXECUTION AUDIT

| Aspecto | Estado |
|---|---|
| Idempotencia | ✅ `PaperExecutor` cachea por `idempotency_key`; `execution.py:164-167` no re-asigna owner en replay. |
| Order lifecycle / estado | ✅ `OrderTracker`(+Redis) con `register`/`get`/`update_status`/`get_open_orders`. |
| Slippage paper | ✅ `PAPER_SLIPPAGE_PCT` aplicado. |
| Ejecutores live | ⚠️ Binance/Bybit/OANDA/IB/MT5 presentes; `live_executor.py` y `mt5_executor.py` con `NotImplementedError` en métodos clave; ninguno verificado contra broker. |
| Reintentos / rechazo / desconexión | ❓ No verificado; múltiples `except Exception` sin política clara. |
| Reconciliación | ❓ No hay flujo de reconciliación de posiciones broker↔local verificado. |
| Ejecución duplicada por multi-worker | ❌ Riesgo real (F-04): 4 workers = 4 llamadas a `_pipeline_cycle` por símbolo/hora. |
| `stale signal` / `stale price` | ⚠️ Cooldown de 3 barras en `SignalEngine`; sin chequeo de antigüedad del último candle antes de ejecutar. |

---

# SECURITY AUDIT

| # | Hallazgo | Ubicación | Sev. | Acción |
|---|---|---|---|---|
| S-01 | Registro abierto con selección de rol `admin` | `api/routes/auth.py:44-67` | **Crítica** | Ver F-01. |
| S-02 | Enforcement de JWT secret condicionado a `ENVIRONMENT=production` (no seteado en compose) + sin chequeo de longitud | `core/config/settings.py:103-108` | Alta | Ver F-08. |
| S-03 | `logout` no revoca el **refresh token** (solo el access); refresh sin rate limit | `api/routes/auth.py:90-111` | Media | Blacklistear también el `jti` del refresh; `@limiter.limit` en `/refresh`. |
| S-04 | Blacklist de JWT **fail-open** si Redis cae | `core/auth/token_blacklist.py:23-27, 44-53` | Baja (documentada y razonada; ventana ≤ TTL) | Aceptable como decisión; monitorear disponibilidad de Redis y alertar. |
| S-05 | `python-jose==3.3.0` (CVEs históricos: algoritmo/confusión) | `requirements.txt` | Media | Migrar a `PyJWT`, o fijar y añadir `pip-audit` en CI. |
| S-06 | `KillSwitchRedis.reset(admin_token)` no valida el token (mitigado por `require_admin` en la ruta) | `core/risk/kill_switch_redis.py:181` | Baja | Validar el token dentro de la función (defensa en profundidad). |
| S-07 | 148 `except Exception`/`except:` en core+api; varios tragan errores (`api/main.py:177`, pipeline microstructure `run_pipeline.py:206`) | varios | Media | Auditar y estrechar; loguear siempre con contexto; nunca degradar seguridad en silencio. |
| S-08 | Puertos 5432/6379 publicados en compose | `docker/docker-compose.yml` | Baja (dev) | No publicar en prod; red interna only. |
| S-09 | `GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}` (default `admin`) | `docker/docker-compose.yml` | Baja | Quitar el default; requerir la variable. |

**Verificado correcto:** sin secretos hardcodeados (grep de patrones limpio); `.env` gitignored y no trackeado; RBAC (`require_trader`/`require_admin`) aplicado en execution/risk; rate limiting real vía slowapi; CORS con allowlist (no `*`); algoritmo JWT whitelisted; sin `and False`.

**SECRET DETECTED: NO** (en el árbol trackeado).

---

# USERS & ACCESS AUDIT

| Rol | Definido | Puede (según `permissions.py` + dependencias) |
|---|---|---|
| `admin` | ✅ | Todo: `require_admin` (reset kill switch, etc.) + todo lo de trader. |
| `trader` | ✅ | `POST /execution`, `DELETE /orders/{id}`, `PUT/DELETE /risk/sltp-config`, activar kill switch. |
| `analyst` | ✅ (enum) | Lectura; sin verificación de que existan rutas que lo distingan de `viewer`. |
| `viewer` | ✅ | Lectura de endpoints autenticados. |
| service/system | ❌ | No hay identidad de servicio para el pipeline; opera sin usuario (órdenes con `user_id=None`). |

**Problemas:** (1) `register` deja crear cualquier rol → el modelo entero es papel mojado hasta corregir F-01. (2) No hay flujo de alta administrada (invitación/aprobación). (3) `analyst` vs `viewer` sin diferenciación efectiva verificada. (4) Sin política de contraseñas visible (longitud/complejidad) en `create_user`. (5) Sin MFA/segunda confirmación para acciones de alto impacto (activar trading live, reset kill switch).

---

# TESTING AUDIT

- **Colectados:** 448. **Suite completa:** 424 passed / 22 failed / 2 skipped / 2 errors (1257 s ≈ 21 min). **Unit+quant aislados:** 333 passed / 2 failed / 2 skipped (62 s).
- **Fallos (22):** 20 en `tests/test_dashboard_e2e.py` — todos por `ConnectionError` a `127.0.0.1:8000` (el test asume un servidor FastAPI ya corriendo; no lo levanta). 2 en `tests/unit/test_hmm_regime_detector.py` (`test_fit_handles_nan`, `test_predict_with_insufficient_data`) — fallos de lógica reales.
- **Errores (2):** teardown del fixture `TestClient` (cierre async del lifespan sin Redis) en `test_api_execution.py` y `test_api_sltp_config.py`.
- **Lectura honesta:** descontada la infraestructura ausente, **la suite no tiene fallos de lógica salvo los 2 de HMM**. Pero `test_dashboard_e2e.py` está diseñado de forma que **siempre** cuenta como 20 fallos en cualquier entorno sin servidor manual — contamina la señal.
- **Integration/E2E:** `tests/integration/*` (6 archivos) + `tests/test_dashboard_e2e.py` — **no herméticos**: requieren Postgres+Redis+servidor vivo; en este entorno cuelgan (reintentos con timeout). No verificables aquí y frágiles en CI.
- **Cobertura por zona (estimada, sin ejecutar `--cov` completo):** `core/risk` alta, `core/ml/i1_*` con `tests/quant/test_i1_gate.py`, `core/auth` alta, `core/execution` media (IDOR, MT5, cost model), `core/consensus` media (`test_voting_engine_mt5`), `api/routes/` baja salvo auth/execution/websocket/sltp-config, `core/agents` baja, `core/portfolio` baja, `core/adaptation` baja, `scripts/run_pipeline.py` **sin test end-to-end**.
- **Falsos verdes / gaps:**
  - `ci_backtest_gate.py` es smoke sobre OHLCV sintético, no valida correctitud del pipeline ni edge.
  - No hay contract test entre lo que `run_pipeline` produce y lo que las repos/DB esperan.
  - No hay test de multi-worker / concurrencia del scheduler.
  - No hay test que registre `admin` vía `/auth/register` (habría cazado F-01).
- **Recomendación:** hacer `tests/integration` hermético con `testcontainers` (Postgres+Redis efímeros) o marcar `@pytest.mark.integration` y excluir de la señal verde por defecto; añadir un `tests/e2e/test_pipeline_cycle.py` con brokers y repos mockeados que ejerza `_pipeline_cycle` completo.

---

# OBSERVABILITY AUDIT

- **Logs:** `structlog` estructurado, consistente, con eventos nombrados (`kill_switch_triggered_redis`, `consensus_result`, `cycle_complete`…). Bueno.
- **Métricas:** Prometheus en :8001 (`prometheus_metrics.py`). Falta catálogo documentado de métricas y alertas por umbral.
- **Tracing:** `decision_tracer.py` existe; sin OpenTelemetry, sin correlation ID propagado entre API↔core↔pipeline.
- **Audit trail:** `core/compliance/audit_system.py` (`AuditLog` JSONL en `logs/audit/`) + `AuditRepository` (DB). `execution.py:186-193` sí llama `_audit_repo.log_action` en la ruta de ejecución de la API. Pero el **pipeline** (`run_pipeline`) no escribe auditoría, y `ComplianceAuditSystem` no se instancia.
- **Reconstrucción "Market State → Model Decision → Signal → Risk Decision → Order → Fill → Position":** **no posible hoy** de forma íntegra — falta el productor unificado (F-06) y falta un identificador que ligue las etapas.
- **Grafana:** provisioning presente (`docker/grafana/provisioning/`); paneles reales no auditados / probablemente vacíos.

---

# PERFORMANCE AUDIT

| Punto | Estado |
|---|---|
| Carga de parquet en arranque | ✅ en `asyncio.to_thread`; ⚠️ se repite en cada worker. |
| Tarea async huérfana | ✅ `_refresh_task` con `cancel()` + `wait_for` en shutdown. |
| CPU-bound en event loop | ⚠️ `calculate_all` / features en el ciclo del pipeline; aceptable si el pipeline es su propio proceso. |
| Scheduler multi-worker | ❌ 4× ejecución (F-04). |
| Backpressure | Parcial: `max_instances=1`, `coalesce=True`, `misfire_grace_time=120` por job. Sin cola. |
| Redis connection reuse | OK (clientes cacheados; blacklist resetea en fallo). |
| Model inference | LightGBM ligero; sin benchmark. |
| DB | asyncpg pool; 7 migraciones; `005_create_hypertable` (TimescaleDB). Sin análisis de índices/retención. |

---

# DEVSECOPS AUDIT

- **CI (`ci.yml`):** lint → type-check → unit → integration → safety / i1 / backtest → docker-build.
  - ❌ `lint`: `pip install ruff black bandita` (typo) → job falla → cadena `needs: lint` bloqueada.
  - ⚠️ `integration-tests` correrá sin Postgres/Redis → fallará o colgará (no hay `services:` en el job).
  - ⚠️ `i1-gate`: `continue-on-error: true` + condicionado a que haya parquet en `data/raw/*_1h.parquet` (los datos están en `data/raw/parquet/1h/`) → **nunca corre**.
  - ✅ `safety-checks`: verifica `EXECUTION_MODE=paper` / `TRADING_ENABLED=false` en `.env.example` y grep de secretos.
  - Sin: `pip-audit`/`safety`, quality gate de cobertura, SBOM, escaneo de imagen Docker, CD.
- **Pre-commit:** ruff + black + mypy + bandit configurados (`.pre-commit-config.yaml`).
- **Branching:** trabajo directo en `main` (los últimos 5 commits en `main`).

---

# DOCUMENTATION AUDIT

| Documento | Estado | Problema | Acción |
|---|---|---|---|
| `docs/architecture/*.md` | Obsoleto | Describe Streamlit como frontend; no menciona la SPA ni el pipeline actual | Reescribir con la arquitectura de este documento. |
| `PLAN_MAESTRO.md` (60 KB) | Vivo pero enorme | Mezcla plan, estado y bitácora; difícil usar como fuente de verdad | Partir en: ROADMAP (qué falta) + CHANGELOG (qué se hizo). |
| `ESTADO_PROYECTO.md`, `PROYECTO_COMPLETO.md`, `RESUMEN_FINAL_EJECUCION.md` | Solapados / parcialmente obsoletos | Afirmaciones de "gate I1 aprobado", "160 tests" no vigentes | Consolidar en uno; borrar el resto. |
| `docs/AUDITORIA_*_2026-05-16.md`, `_2026-07-25.md` | Vigentes como baseline | — | Enlazar desde este documento (hecho). |
| `DOCUMENTACION_MODELOS.md`, `Propuestas_mejora_modelos.md` | Aspiracional | Describe modelos/mejoras no implementadas | Marcar `[PROPUESTA]` en el título. |
| `API_REFERENCE.md`, `docs/api-reference/endpoints.md` | Parcialmente desalineado | Rutas viejas; falta `/models`, `/monitoring/*`, `/auth/register` | Regenerar desde OpenAPI (`/openapi.json`). |
| `TRADER_AI_PROMPT_MAESTRO.md` (96 KB) | Meta-doc | No es documentación del sistema | Mover a `docs/process/`. |
| `specs/SPEC-001..005` | Vigentes, útiles | Solo cubren 5 módulos | Extender el patrón al backlog de este documento. |
| `MULTIACTIVOS_CHECKLIST.md` | Parcial | Checklist sin estado real | Actualizar contra `settings.SUPPORTED_SYMBOLS` real. |

---

# TECHNICAL DEBT

| # | Deuda | Criticidad | Esfuerzo |
|---|---|---|---|
| D-01 | `POST /auth/register` con rol arbitrario | CRITICAL | 2 h |
| D-02 | Sin edge quant confirmado (reenfoque de roadmap) | CRITICAL | — (estratégico) |
| D-03 | 3 registros de estrategias desconectados del pipeline real | HIGH | 24–40 h |
| D-04 | Scheduler + refresh dentro de la API con 4 workers | HIGH | 8 h |
| D-05 | Dockerfile no incluye `alembic/`; arranque sin DB silencioso | HIGH | 3 h |
| D-06 | Cadena de decisión sin productor (signals/audit/drift/alpha-decay) | HIGH | 16–24 h |
| D-07 | Dos árboles de capas (`core/` vs `domain/application/...`) | HIGH | 40 h+ (o decisión de borrar uno) |
| D-08 | CI `lint` roto + sin dependency scanning + `i1-gate` nunca corre | HIGH | 6 h |
| D-09 | `RiskManager` sin agregación de exposición de cartera ni correlación | HIGH | 12 h |
| D-10 | Integration/E2E no herméticos | MEDIUM | 16 h |
| D-11 | 3 universos de activos inconsistentes | MEDIUM | 4 h |
| D-12 | 2 tests HMM fallando | MEDIUM | 4 h |
| D-13 | `NotImplementedError` en ejecutores live + LSP en clientes de exchange | MEDIUM | 16 h |
| D-14 | `TradingRepository` vs `repositories/*` (dos abstracciones de repo) | MEDIUM | 8 h |
| D-15 | `python-jose` → `PyJWT`; enforcement de JWT secret | MEDIUM | 6 h |
| D-16 | God files (`mtf_sl_tp_manager`, `asset_specific_models`) | MEDIUM | 16 h |
| D-17 | 148 `except Exception` sin política | MEDIUM | 12 h |
| D-18 | Docs de arquitectura obsoletas + consolidación de docs de estado | MEDIUM | 12 h |
| D-19 | `datetime.utcnow()` deprecado en ~10 módulos | LOW | 3 h |
| D-20 | `data/processed/`, `core/optimization/` vacíos desde abril | LOW | — |
| D-21 | `version: "3.9"` obsoleto en compose; Grafana pass default `admin` | LOW | 1 h |
| D-22 | Healthcheck del Dockerfile usa `requests` (no está en `requirements.txt`) | LOW | 1 h |

---

# PREVIOUS AUDIT COMPARISON

| Hallazgo anterior (2026-05 / 2026-07) | Estado anterior | Estado actual | Evidencia |
|---|---|---|---|
| Kill switch fail-open | Crítico abierto | ✅ Resuelto | `kill_switch_redis.py:85-96` + tests |
| Gate I1 ignora holdout | Crítico abierto | ✅ Criterio resuelto / resultado negativo | `gate_validator.py:150-154`; `i1_gate_report.json` 1/8 |
| WebSocket sin auth | Alto abierto | ✅ Resuelto | `websocket.py:46-50` + tests |
| LSP exchanges (2 jerarquías) | Alto abierto | 🟡 Parcial | `ExchangeAdapter` ABC único, pero `NotImplementedError` persiste y `_instantiate_client` if/elif |
| Pipeline no corre end-to-end | Alto abierto | 🟡 Sin cambio verificable | Requiere infra ausente |
| 35 tests fallando + `test_api_execution` no colecta | Medio abierto | ✅ Muy mejorado | 2 fallos unit/quant; `RegisterRequest` ya definido |
| IDOR en órdenes | Medio abierto | ✅ Resuelto | `execution.py:218-228` + tests |
| God files sin spec | Medio abierto | 🟡 Parcial | `mtf_sl_tp_manager` modularizado; `i1_gate_validator` modularizado; `asset_specific_models` partido |
| ATR duplicado | Medio abierto | ❓ No re-verificado en detalle | `test_atr_deduplication.py` existe (verde) — probablemente abordado |
| `token_blacklist` sin módulo | Bajo abierto | ✅ Resuelto | `core/auth/token_blacklist.py` dedicado |
| `and False` JWT secret | Crítico abierto | 🟡 Parcial | Ahora `ENVIRONMENT==production` (débil) |
| docker-compose YAML inválido | P0 abierto | ✅ Resuelto | YAML válido |
| DB nunca inicializada / scheduler comentado | P0/P1 abierto | ✅ Resuelto | `api/main.py:173-176, 284-315` |
| Dashboard god file + 3 implementaciones | P1/P3 abierto | ✅ Resuelto | SPA única; `dashboard.py` eliminado |
| `POST /auth/register` no existe | Gap | ⚠️ Existe pero **inseguro** | F-01 |

**Evolución neta:** fuerte progreso en estabilidad/infra/seguridad-base y en honestidad de la validación quant; regresión puntual grave en control de acceso; el problema de fondo (¿hay edge? ¿qué sistema decide?) sigue sin resolver.

---

# GAP ANALYSIS

| # | Current state | Target state | Gap | Riesgo | Esfuerzo | Prioridad |
|---|---|---|---|---|---|---|
| G-1 | Registro abierto rol-arbitrario | Alta de usuarios controlada, rol mínimo por defecto | Auth de registro | Crítico | S | MUST |
| G-2 | 1/8 activos con edge; sin métricas consolidadas | ≥1 activo con edge robusto (MC + stress costos + regime) documentado | Investigación quant enfocada | Crítico | L | MUST |
| G-3 | 3 registros de estrategia; pipeline con `default_v1` | 1 fuente de verdad; params I1 conectados al SignalEngine | Integración estrategia↔decisión | Alto | L | MUST |
| G-4 | Scheduler en API x4 workers | Worker de pipeline dedicado, 1 instancia, con lock | Separación de procesos | Alto | M | MUST |
| G-5 | Contenedor sin DB silencioso | Migraciones en la imagen; fallo ruidoso en `live` | Empaquetado + fail-fast | Alto | S | MUST |
| G-6 | Decisiones no trazables end-to-end | Trace Market→Fill con correlation ID persistido | Productor unificado + trace id | Alto | M | MUST |
| G-7 | Riesgo por señal, no por cartera | Exposición agregada + correlación + pérdida diaria en `validate_signal` | Motor de riesgo de cartera | Alto | M | MUST |
| G-8 | `test_dashboard_e2e.py` sin server + integration con teardown frágil | testcontainers (Postgres+Redis efímeros); fixture que arranca el server; `tests/e2e/test_pipeline_cycle.py` verde en CI | Infra de test | Medio | M | SHOULD |
| G-9 | 2 árboles de capas | 1 estructura; el otro borrado o adoptado | Decisión + refactor | Medio | L | SHOULD |
| G-10 | Multi-activo: MT5 off, universo triple | MT5 demo conectado o forex/índices explícitamente fuera de alcance; 1 universo | Config + datos | Medio | M | SHOULD |
| G-11 | Sin métricas por modelo, drift/alpha-decay no cableados | Registro de métricas + monitores alimentados tras cada trade | MLOps mínimo | Medio | M | SHOULD |
| G-12 | Docs de arquitectura obsoletas | Docs alineadas + ADRs para las 6 decisiones clave | Documentación | Bajo | M | SHOULD |
| G-13 | CI lint roto, sin dep-scan | CI verde + `pip-audit` + gate de cobertura | DevSecOps | Medio | S | SHOULD |
| G-14 | Ejecutores live incompletos | 1 venue live (paper/testnet) end-to-end con reconciliación | Ejecución | Alto | L | COULD (post paper) |

---

# TARGET ARCHITECTURE (resumen)

1. **Dos procesos, un repo:** `api` (FastAPI, N workers, solo request/response, sin jobs) y `worker` (`scripts/run_pipeline.py`, 1 instancia, dueño del scheduler; lock en Redis para HA activo/pasivo).
2. **Una estructura de capas:** elegir `core/` como paquete de aplicación+dominio+infra con submódulos claros, **borrar** `domain/application/infrastructure/interfaces/` o migrar todo a ellos — no ambas. Documentar en ADR.
3. **Una fuente de verdad de estrategias:** `StrategyRegistry` como catálogo; cada estrategia declara `params` optimizables; el gate I1 escribe `data/models/i1_params/<symbol>.json`; el `SignalEngine`/pipeline **carga esos params** para el activo. El marketplace consume el mismo registry.
4. **Trace de decisión:** `correlation_id` generado al inicio de `_pipeline_cycle`, propagado a features/consenso/señal/orden, persistido en cada tabla y en `AuditLog`. Un endpoint `/trace/{correlation_id}` reconstruye la cadena.
5. **Riesgo de cartera** como servicio (`PortfolioRiskEngine`) consultado por `RiskManager.validate_signal`: exposición agregada, correlación (matriz rolling), pérdida diaria, límite por clase de activo.
6. **MLOps mínimo:** `ModelRegistry` con métricas por versión; `record_trade()` de alpha-decay y `update()` de drift alimentados desde el cierre de posición.
7. **Un universo de activos** en `core/config/constants.py`, consumido por settings, pipeline y gate.

---

# NEW FUNCTIONALITIES (priorizadas — solo tras cerrar P0/P1)

**Quant / IA (SHOULD, post-edge):** strategy scoring continuo con degradación automática; regime-aware sizing real (hoy la heurística no cambia sizing); ensemble/meta-model **solo** si ≥2 modelos con edge individual medido.

**Risk (SHOULD):** tail-risk engine (CVaR ya calculado en UI — llevarlo a backend y al gate de riesgo); exposición dinámica por volatilidad objetivo (`volatility_targeting.py` ya existe — cablearlo).

**Execution (COULD, post paper):** smart execution (TWAP/partial), execution quality analytics (slippage realizado vs esperado), multi-venue routing.

**Producto (COULD):** perfiles de trader (`user_profile_engine.py` existe — conectar a límites de riesgo y timeframe por usuario); paper trading multi-cuenta.

---

# PRIORITIZATION

**MUST HAVE (bloquea todo lo demás):** F-01, F-02(quant reenfoque), F-03, F-04, F-05, F-06, F-08, F-09.
**SHOULD HAVE (antes de paper trading serio):** G-8..G-13, D-12, D-13, D-15.
**COULD HAVE:** god files, `datetime.utcnow`, ejecutores live, nuevas features quant.
**FUTURE:** multi-tenancy, RL, online learning, multi-venue.

---

# MASTER ROADMAP

| Fase | Objetivo | Contenido | Gate de salida |
|---|---|---|---|
| **F0 — Governance** | Fuente de verdad | Consolidar docs; ADRs de las 7 decisiones de Target Architecture; congelar `PROMPT_MAESTRO` como proceso | ADR-001..007 aprobadas; `docs/architecture` reescrita |
| **F1 — Estabilización crítica** | Cerrar P0/P1 de seguridad e infra | F-01, F-04, F-05, F-08, F-07(mínimo), CI lint fix, 2 tests HMM | CI verde real; `docker compose up` con DB; no hay ruta a `admin` sin admin; test de escalada falla-cierra |
| **F2 — Coherencia arquitectónica** | Un sistema, no tres | F-03 (una fuente de estrategias), G-9 (un árbol de capas), G-10 (un universo), F-06 (productor + trace id), `TradingRepository`↔repos | `/trace/{id}` reconstruye una decisión; `grep default_v1` acotado a un punto documentado |
| **F3 — Core cuantitativo** | ¿Hay edge? | Ampliar datos; barrido de costos; Monte Carlo sobre equity; regime-dependency; reporte consolidado de métricas por activo/estrategia | Documento firmado: lista de activos con edge robusto (o "ninguno, pivotar") |
| **F4 — Estrategias & multi-activo** | Solo si F3 da ≥1 activo | Conectar params I1 al pipeline; MT5 demo o descartar forex/índices formalmente; strategy scoring | Backtest OOS por estrategia conectada ≥ umbral acordado |
| **F5 — IA/ML** | Solo si baseline confirmado | `ModelRegistry` + métricas; drift/alpha-decay cableados; validación de leakage en `feature_engineering.py` | Métricas por modelo visibles y no nulas; drift con baseline |
| **F6 — Risk & Execution intelligence** | Endurecer | `PortfolioRiskEngine` en el gate; volatility targeting; 1 venue paper/testnet end-to-end con reconciliación | Test de cartera con N posiciones correlacionadas rechaza correctamente |
| **F7 — Testing avanzado** | Confianza | testcontainers; `tests/e2e/test_pipeline_cycle.py`; walk-forward en CI (job real); property tests de riesgo | Cobertura `core/` ≥ 75%; e2e verde en CI |
| **F8 — Security/DevSecOps/Observabilidad** | Operable | `PyJWT`; `pip-audit`; correlation ID en todas las capas; Grafana con paneles reales; alertas por umbral | Dashboard de P&L/señales/riesgo/latencia vivo; escaneo de deps en CI |
| **F9 — Paper Trading** | Validación en vivo sin capital | Worker corriendo 24/7 contra testnet/demo; auditoría completa; kill switch ejercido | ≥ 4 semanas de operación paper con métricas dentro de lo esperado |
| **F10 — Production Readiness** | Capital limitado supervisado | HA del worker; runbooks; DR probado; revisión legal | Checklist de Acceptance Gates 100% |

---

# SPEC BACKLOG (extracto — formato SPEC-DRIVEN)

Backlog completo en `docs/SPEC_BACKLOG_2026-08-28.md`. Ejemplos de las specs MUST:

### SPEC-A01 — Alta de usuarios segura
- **PURPOSE:** eliminar la escalada de privilegios de `POST /auth/register`.
- **SCOPE:** `api/routes/auth.py`, `core/db/user_repository.py`, `core/auth/permissions.py`.
- **BUSINESS RULES:** (1) registro público, si está habilitado (`REGISTRATION_ENABLED`, default `false`), solo crea rol `viewer`. (2) Crear `trader`/`analyst`/`admin` requiere `require_admin`. (3) Password ≥ 12 chars, no en top-1000.
- **INPUTS:** `{email, password}` (sin `role` para el endpoint público).
- **ERROR CONDITIONS:** 403 si `role` != viewer sin admin; 409 email existente; 422 password débil; 404 si `REGISTRATION_ENABLED=false`.
- **SECURITY:** rate limit 3/min; audit `user_created` con actor.
- **TEST REQUIREMENTS:** test que POSTea `role=admin` sin token → 403/422; test admin crea trader → 201; test password débil → 422.
- **ACCEPTANCE:** `pytest -k register` verde; no existe camino a `admin` sin un `admin` previo (seed inicial documentado).

### SPEC-A02 — Separación API / Worker de pipeline
- **PURPOSE:** eliminar la ejecución x4 del scheduler y del refresh fundamental.
- **SCOPE:** `api/main.py` (quitar scheduler + `_refresh_task`), `scripts/run_pipeline.py` (único dueño), `docker/docker-compose.yml` (servicio `worker`), `docker/Dockerfile` (o `command` override).
- **BUSINESS RULES:** exactamente 1 instancia del scheduler; si se corren varias, un lock Redis (`SET NX EX`) elige la activa.
- **OBSERVABILITY:** métrica `pipeline_cycles_total{symbol}`; log `scheduler_owner_acquired`.
- **ACCEPTANCE:** con `--workers 4` en la API, `_pipeline_cycle` se ejecuta 1×/símbolo/hora (test con contador).

### SPEC-A03 — Empaquetado con migraciones + fail-fast
- **SCOPE:** `docker/Dockerfile` (`COPY alembic/`, `COPY alembic.ini`), `api/main.py` lifespan.
- **BUSINESS RULES:** si `EXECUTION_MODE=live` y `init_pool`/`run_migrations` fallan → el proceso **no arranca** (exit ≠ 0). En `paper` puede degradarse pero loguea `WARNING` visible y `app.state.db_initialized=false` expuesto en `/health`.
- **ACCEPTANCE:** `docker build` + `docker run` aplica migraciones; test de arranque en `live` sin DB → exit 1.

### SPEC-A04 — Trace de decisión end-to-end
- **SCOPE:** `scripts/run_pipeline.py`, repos, `AuditLog`, nuevo `GET /trace/{correlation_id}`.
- **OUTPUTS:** JSON con features usadas, salidas de cada agente, `ConsensusOutput`, `Signal`, veredicto de riesgo, orden, fill, snapshot de portfolio.
- **ACCEPTANCE:** ejecutar `_pipeline_cycle` (mocks de broker/DB) y recuperar la cadena completa por `correlation_id`.

### SPEC-A05 — Riesgo de cartera en el gate
- **SCOPE:** `core/risk/portfolio_risk_engine.py`, `core/risk/risk_manager.py:validate_signal`.
- **BUSINESS RULES:** rechazar si `Σ(|entry−SL|·qty)/capital + riesgo_nueva > MAX_PORTFOLIO_RISK_PCT`; si correlación media de la nueva posición con las abiertas > 0.7 y ya hay 2 en ese cluster; si pérdida diaria acumulada ≥ `DAILY_LOSS_LIMIT_PCT`.
- **TEST:** 3 posiciones EURUSD/GBPUSD/XAUUSD → 4ª correlacionada rechazada; suma de exposiciones respeta el límite.

### SPEC-A06 — Una fuente de verdad de estrategias
- **SCOPE:** `core/strategies/strategy_registry.py`, `core/ml/i1_strategies.py`, `core/signals/signal_engine.py`, `scripts/run_pipeline.py`.
- **BUSINESS RULES:** el pipeline carga, por activo, la estrategia + params ganadores del gate I1 (`data/models/i1_params/<symbol>.json`); si no hay params aprobados para un activo, ese activo **no genera señales** (fail-safe quant).
- **ACCEPTANCE:** con solo XAUUSD aprobado, el pipeline solo emite señales de XAUUSD; el resto loguea `no_approved_strategy`.

---

# IMPLEMENTATION PLAN (F1 — detalle)

| ID | Fase | Actividad | Módulo | Prioridad | Complejidad | Riesgo | Entregable | Tests | Criterio de aceptación |
|---|---|---|---|---|---|---|---|---|---|
| I-101 | F1 | Cerrar registro (SPEC-A01) | `api/routes/auth.py`, `user_repository.py` | P0 | Baja | Bajo | PR + flag `REGISTRATION_ENABLED` | `test_auth.py::test_register_cannot_escalate` | POST `role=admin` sin token → 403/422 |
| I-102 | F1 | Fix CI lint + añadir `pip-audit` | `.github/workflows/ci.yml` | P1 | Baja | Bajo | CI verde | run del workflow | `lint` pasa; `pip-audit` job presente |
| I-103 | F1 | Dockerfile: `alembic/` + fail-fast en live (SPEC-A03) | `docker/Dockerfile`, `api/main.py` | P1 | Baja | Medio | imagen que migra | `test_startup_live_without_db_exits` | `docker run` aplica migraciones |
| I-104 | F1 | Separar worker/API (SPEC-A02) | `api/main.py`, `run_pipeline.py`, compose | P1 | Media | Medio | servicio `worker` + lock Redis | `test_scheduler_single_owner` | 1×/símbolo/hora con 4 workers |
| I-105 | F1 | Enforcement JWT secret (SPEC-A01 anexo) | `core/config/settings.py` | P1 | Baja | Bajo | validador robusto | `test_settings_rejects_short_secret` | secret <32 o default → ValueError salvo flag test |
| I-106 | F1 | Exposición de cartera mínima en `validate_signal` (SPEC-A05 fase 1) | `core/risk/risk_manager.py` | P1 | Media | Medio | suma de exposiciones | `test_risk_portfolio_exposure_aggregation` | N posiciones respetan `MAX_PORTFOLIO_RISK_PCT` |
| I-107 | F1 | Arreglar 2 tests HMM | `core/adaptation/hmm_regime_detector.py` | P2 | Baja | Bajo | tests verdes | los 2 tests | `pytest tests/unit tests/quant` 0 fallos |
| I-108 | F1 | `datetime.utcnow()` → `datetime.now(UTC)` | ~10 módulos | P3 | Baja | Bajo | sin DeprecationWarning | suite | 0 warnings de ese tipo |

---

# ACCEPTANCE GATES

| Gate | Pregunta | Estado hoy |
|---|---|---|
| **Architecture Gate** | ¿Una estructura de capas, un scheduler, un universo? | ❌ |
| **SOLID Gate** | ¿OCP/LSP sin `NotImplementedError` en interfaces compartidas? | ❌ |
| **Spec Gate** | ¿Cada cambio en core lleva spec? | ❌ (solo 5 specs) |
| **Quant Gate** | ¿Evidencia de edge neto de costos OOS? | ❌ (1/8, n insuficiente) |
| **Risk Gate** | ¿El gate de riesgo considera la cartera completa? | ❌ |
| **Security Gate** | ¿Sin escalada de privilegios, secretos enforced? | ❌ (F-01, F-08) |
| **Test Gate** | ¿Suite hermética verde en CI incluyendo e2e? | 🟡 (unit/quant sí; integration/e2e no) |
| **Production Gate** | ¿Listo para capital real? | ❌ |

> **Estado 2026-08-30 (rama F1, sin commitear):** Architecture Gate → 🟡 (un scheduler
> con lock, un universo, una fuente de estrategias; el árbol de capas dual sigue → F3.1).
> Risk Gate → 🟡 (exposición de cartera agregada; falta correlación → F6.1).
> Security Gate → ✅ (F-01 y F-08 cerrados). Test Gate → 🟡 (fixtures herméticos +
> `live_server` listos; falta la corrida verde de `-m integration` en CI).
> **Quant Gate → ❌ confirmado** (GATE F2 = NO-GO preliminar). Production Gate → ❌.

---

# FINAL RECOMMENDATION

1. **Hoy mismo:** cerrar F-01 (registro/rol) y F-08 (JWT secret). Son minutos de código y son la diferencia entre "pre-alpha interno" y "cualquiera es admin".
2. **Esta iteración (F1):** separar worker/API, arreglar el empaquetado Docker, arreglar CI, y llevar el gate de riesgo a nivel de cartera. Sin esto, el sistema no puede correr de forma fiable ni siquiera en paper.
3. **Antes de escribir una línea más de "estrategias avanzadas", ML o RL (F3):** responder con datos si existe edge. El gate I1 corregido dice que hoy **no**, salvo XAUUSD. Aceptar ese resultado y pivotar el esfuerzo a confirmar/expandir ese único caso, o a buscar edge en otro sitio, es la decisión quant correcta (Reglas 3 y 4).
4. **Deuda de coherencia (F2):** el mayor riesgo no-financiero del proyecto es que "lo que el sistema hace" ya no se puede deducir de "lo que el sistema dice". Un árbol de capas, un registro de estrategias, un universo de activos, un productor de trazas — antes de añadir features.
5. **Nunca** `Development → Production`. La ruta es `→ Backtest → OOS → Stress → Paper (≥4 semanas) → Capital limitado supervisado → Production`, con los Acceptance Gates de arriba en verde.

> **No conectar capital real.** El sistema no tiene edge confirmado, tiene una escalada de privilegios abierta, y su pipeline de decisión se ejecuta de forma no determinista bajo la configuración de despliegue actual.
>
> **Actualización 2026-08-30 (rama F1, sin commitear):** la escalada de privilegios está
> cerrada (F-01) y el pipeline ya es determinista y con dueño único (F-04, verificado
> por `scripts/check_reproducibility.py`). El bloqueo restante es el central: **sin edge
> confirmado** — el GATE F2 dio **NO-GO preliminar** (`docs/CORE_VALIDATION_DECISION_2026-08-30.md`).
> Sigue vigente: **no conectar capital real**; el plan está en ciclo de pivote.

---

*Anexo — comandos ejecutados en esta auditoría:*
```
git log/rev-parse; find core|tests|specs; 
pytest --collect-only -q                    # 448 tests
pytest tests/unit tests/quant -q            # 333 passed, 2 failed, 2 skipped (62s)
python -c "json.load('data/reports/i1_gate_report.json')"   # 1/8 passed, gate_approved:false
Read: api/main.py, core/risk/kill_switch_redis.py, core/ml/i1_gate_validator/{gate_validator,config}.py,
      api/routes/{websocket,execution,auth}.py, core/auth/token_blacklist.py, core/bootstrap.py,
      core/db/migrate.py, scripts/run_pipeline.py, core/consensus/voting_engine.py,
      core/signals/signal_engine.py, core/risk/risk_manager.py, core/ingestion/exchange_{adapter,registry}.py,
      core/config/settings.py, docker/{Dockerfile,docker-compose.yml}, .github/workflows/ci.yml,
      pyproject.toml, requirements.txt, .env.example, docs/AUDITORIA_*_2026-{05,07}.md,
      docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md
grep: NotImplementedError, except Exception, TODO/FIXME, store_signal, agent_id, streamlit
```
