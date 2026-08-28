# TRADER AI — SPEC BACKLOG

**Origen:** `docs/AUDITORIA_INTEGRAL_2026-08-28.md` (commit `aeea1c5`).
**Uso:** cada entrada es implementable por un agente de IA sin reinterpretar decisiones arquitectónicas. El orden es el de ejecución (F1 → F6). No iniciar una spec sin cumplir su *Definition of Ready*; no cerrarla sin su *Definition of Done*.

**Definition of Ready (todas):** spec leída, dependencias disponibles, interfaces existentes localizadas, criterio de aceptación entendido, rama creada desde `main`.
**Definition of Done (todas):** código + tests nuevos verdes + `pytest tests/unit tests/quant` sin nuevos fallos + doc actualizada + sin `except Exception` nuevos que degraden seguridad + criterio de aceptación demostrado en el PR.

---

## FASE 1 — ESTABILIZACIÓN CRÍTICA

### SPEC-A01 — Alta de usuarios segura  *(cierra F-01, F-08)*
- **PURPOSE / BUSINESS VALUE:** eliminar la escalada de privilegios: hoy `POST /auth/register` (`api/routes/auth.py:44-67`) no exige auth y acepta `role` del cuerpo; `Role(body.role)` admite `"admin"`.
- **SCOPE:** `api/routes/auth.py`, `core/db/user_repository.py` (`create_user`), `core/config/settings.py`.
- **NON-SCOPE:** MFA, verificación de email, invitaciones (backlog futuro).
- **ACTORS:** usuario anónimo (registro público), admin (alta de roles elevados), sistema (seed inicial).
- **INPUTS:** público `{email: EmailStr, password: str}`; admin `{email, password, role}`.
- **OUTPUTS:** `TokenResponse` (registro público / admin) o `201` sin token para alta admin (a decidir; preferible sin token).
- **PRECONDITIONS:** `REGISTRATION_ENABLED` (nuevo, default `false`) para el endpoint público.
- **POSTCONDITIONS:** usuario creado con rol permitido; entrada de auditoría `user_created` con `actor`.
- **BUSINESS RULES:**
  1. Endpoint público: si `REGISTRATION_ENABLED=false` → `404`. Si `true` → crea **solo** `viewer`; ignora / rechaza cualquier `role` en el cuerpo.
  2. Alta de `trader`/`analyst`/`admin`: endpoint separado `POST /auth/users` con `Depends(require_admin)`.
  3. Password: longitud ≥ 12; rechazar si está en una lista de 1.000 comunes embebida.
  4. `JWT_SECRET_KEY`: validador **siempre activo** — `len(v) >= 32` y `v != "change-me-in-production"`, salvo `ALLOW_INSECURE_JWT=true` (solo tests).
- **INTERFACES:** reusar `create_user(email, password, role)`, `get_user_by_email`, `jwt.create_access_token`.
- **ERROR CONDITIONS:** `404` registro deshabilitado; `403` rol elevado sin admin; `409` email existente; `422` password débil / rol inválido.
- **SECURITY REQUIREMENTS:** rate limit `3/minute` público, `10/minute` admin; audit con actor; nunca devolver si el email existe en un flujo distinto al `409`.
- **OBSERVABILITY:** log `user_registered{role}` / `user_created_by_admin{actor,role}`.
- **TEST REQUIREMENTS:**
  - `test_public_register_cannot_set_role`: POST público con `role=admin` → usuario resultante es `viewer` (o `422`).
  - `test_admin_endpoint_requires_admin`: `POST /auth/users` sin token admin → `403`.
  - `test_register_disabled_by_default`: sin `REGISTRATION_ENABLED` → `404`.
  - `test_weak_password_rejected` → `422`.
  - `test_settings_rejects_short_or_default_jwt_secret` → `ValidationError`.
- **ACCEPTANCE CRITERIA:** no existe ningún camino a un usuario `admin` sin un `admin` previo (o el seed documentado); `pytest -k "register or jwt_secret"` verde.

---

### SPEC-A02 — Separación API / Worker de pipeline  *(cierra F-04)*
- **PURPOSE:** hoy `api/main.py` arranca el APScheduler (`:284-315`) y `_refresh_task` (`:255`) dentro del `lifespan`; `docker/Dockerfile:41` corre `--workers 4` → 4 ejecuciones de cada job.
- **SCOPE:** `api/main.py` (quitar scheduler + refresh), `scripts/run_pipeline.py` (único dueño), `docker/docker-compose.yml` (nuevo servicio `worker`), `docker/Dockerfile` (soportar dos comandos).
- **NON-SCOPE:** reescribir el pipeline; HA activo/activo.
- **BUSINESS RULES:**
  1. La API no ejecuta jobs programados. `_refresh_fundamental` se mueve al worker.
  2. Exactamente 1 scheduler. Al arrancar, `run_scheduler` toma un lock Redis `SET trader:scheduler:owner <id> NX EX 90`, renovado cada 30 s; si no lo obtiene, espera (modo pasivo) y reintenta.
  3. `docker-compose`: servicio `worker` con `command: python scripts/run_pipeline.py`, mismo `env_file`, `depends_on: [db, redis]`.
- **INTERFACES:** `run_pipeline.run_scheduler(settings)` ya existe; añadir el lock.
- **OBSERVABILITY:** métrica `pipeline_cycles_total{symbol}`; logs `scheduler_owner_acquired` / `scheduler_owner_standby`.
- **TEST REQUIREMENTS:**
  - `test_api_lifespan_starts_no_scheduler`: tras `lifespan`, no hay `AsyncIOScheduler` en `app.state` ni jobs.
  - `test_scheduler_single_owner`: dos llamadas concurrentes a la adquisición de lock → solo una activa.
- **ACCEPTANCE CRITERIA:** con la API a `--workers 4`, un contador de invocaciones de `_pipeline_cycle` marca 1 por símbolo por ventana.

---

### SPEC-A03 — Empaquetado con migraciones + fail-fast  *(cierra F-05)*
- **PURPOSE:** `docker/Dockerfile` no copia `alembic/` ni `alembic.ini` → `run_migrations()` (`core/db/migrate.py:16`, `Config("alembic.ini")`) lanza excepción → `api/main.py:177-178` la traga → contenedor arranca sin DB en silencio. Tampoco copia `data/`.
- **SCOPE:** `docker/Dockerfile`, `api/main.py` (política de fallo), `docker/Dockerfile` HEALTHCHECK.
- **BUSINESS RULES:**
  1. `COPY alembic/ ./alembic/` y `COPY alembic.ini .` en la imagen.
  2. Si `EXECUTION_MODE=live` y `init_pool` o `run_migrations` fallan → `raise` (proceso no arranca, exit ≠ 0).
  3. Si `EXECUTION_MODE=paper` → degradar con `logger.warning` visible; `GET /health` expone `db_initialized: false`.
  4. HEALTHCHECK: usar `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` (no `requests`, que no está en `requirements.txt`).
  5. Decidir sobre `data/`: montar como volumen en compose (no hornear en la imagen).
- **TEST REQUIREMENTS:**
  - `test_startup_live_without_db_exits`: `EXECUTION_MODE=live` + `DATABASE_URL` inválida → `SystemExit`/excepción en el `lifespan`.
  - `test_health_reports_db_state`.
- **ACCEPTANCE CRITERIA:** `docker build -f docker/Dockerfile .` + `docker run` aplica migraciones a `head`; en `live` sin DB, el contenedor no queda "up".

---

### SPEC-A05 (fase 1) — Exposición agregada de cartera en `validate_signal`  *(cierra F-09 parcial)*
- **PURPOSE:** `RiskManager.validate_signal` (`core/risk/risk_manager.py:58-100`) compara el riesgo de **la señal entrante** con `MAX_PORTFOLIO_RISK_PCT`; no suma posiciones abiertas; `update_kill_switch` recibe `recent_trades=[]` en el pipeline.
- **SCOPE:** `core/risk/risk_manager.py`, `core/risk/portfolio_risk_engine.py`, `scripts/run_pipeline.py:264` (pasar trades reales).
- **BUSINESS RULES:**
  1. `exposición_actual = Σ(|entry−SL|·qty)/total_capital` sobre `portfolio["open_positions"]`.
  2. Rechazar si `exposición_actual + riesgo_señal_nueva > MAX_PORTFOLIO_RISK_PCT`.
  3. Rechazar si `daily_pnl_pct <= -DAILY_LOSS_LIMIT_PCT` (chequeo directo, no solo vía kill switch).
  4. `run_pipeline` pasa `recent_trades` reales a `update_kill_switch` (de `portfolio` o `repo`).
- **NON-SCOPE (queda para SPEC-F6-01):** matriz de correlación, límite por cluster.
- **TEST REQUIREMENTS:**
  - `test_risk_portfolio_exposure_aggregation`: 3 posiciones a 4% cada una + señal 4% → rechazada (>10%).
  - `test_daily_loss_limit_blocks_in_validate_signal`.
  - `test_pipeline_passes_recent_trades_to_kill_switch`.
- **ACCEPTANCE CRITERIA:** ninguna combinación de posiciones abiertas + nueva señal supera `MAX_PORTFOLIO_RISK_PCT`.

---

### SPEC-A07 — CI reparado + dependency scanning  *(cierra F-07)*
- **SCOPE:** `.github/workflows/ci.yml`.
- **BUSINESS RULES:**
  1. `lint`: `pip install ruff black bandit` (corregir `bandita`).
  2. Nuevo job `deps-scan`: `pip install pip-audit && pip-audit -r requirements.txt` (no `continue-on-error`; fallar en `HIGH`/`CRITICAL`).
  3. `i1-gate`: corregir la condición de datos (`ls data/raw/parquet/1h/*_1h.parquet`); mantener `continue-on-error` pero publicar el `i1_gate_report.md` como artifact.
  4. `integration-tests`: añadir `services: postgres` + `redis` al job, o marcarlo `if: false` con TODO explícito hasta SPEC-B01.
  5. Nuevo gate: `--cov=core --cov-fail-under=70` en `unit-tests` (subir gradualmente).
- **ACCEPTANCE CRITERIA:** un push a una rama `feature/*` deja el workflow **verde** (o rojo solo por hallazgos reales), con `lint`, `type-check`, `unit-tests`, `deps-scan` ejecutándose.

---

### SPEC-A08 — Fix tests HMM + `datetime.utcnow`  *(cierra D-12, D-19)*
- **SCOPE:** `core/adaptation/hmm_regime_detector.py`, `core/adaptation/pure_hmm.py`, y ~10 módulos con `datetime.utcnow()`.
- **BUSINESS RULES:**
  1. `HMMRegimeDetector.fit` con NaN en el input → imputar / dropear y loguear, no romper (`test_fit_handles_nan`).
  2. `predict` con < `min_samples` → devolver régimen `UNKNOWN`/`SIDEWAYS` con `confidence=0`, no excepción (`test_predict_with_insufficient_data`).
  3. Reemplazar `datetime.utcnow()` → `datetime.now(timezone.utc)` en core/auth, core/risk, core/execution, tests.
- **ACCEPTANCE CRITERIA:** `pytest tests/unit tests/quant` → **0 failed**; `pytest -W error::DeprecationWarning tests/unit/test_kill_switch.py` sin ese warning.

---

## FASE 2 — COHERENCIA ARQUITECTÓNICA

### SPEC-B01 — Tests de integración herméticos  *(cierra G-8)*
- **SCOPE:** `tests/integration/*`, `tests/test_dashboard_e2e.py`, `tests/conftest.py`.
- **BUSINESS RULES:**
  1. Fixture `docker_services` (testcontainers o `pytest-docker`) que levanta Postgres + Redis efímeros; `DATABASE_URL`/`REDIS_URL` apuntan ahí.
  2. Fixture `live_server` que arranca `uvicorn api.main:app` en un puerto libre para `test_dashboard_e2e.py` (hoy asume `127.0.0.1:8000` y no lo arranca → 20 fallos fijos).
  3. Marca `@pytest.mark.integration`; la señal "verde" por defecto (`pytest -m "not integration"`) no los incluye, pero CI sí los corre en su job.
- **ACCEPTANCE CRITERIA:** `pytest tests/integration tests/test_dashboard_e2e.py` en un runner con Docker → 0 failed / 0 errors.

### SPEC-B02 — Un árbol de capas  *(cierra G-9, D-07)*
- **SCOPE:** `domain/`, `application/`, `infrastructure/`, `interfaces/` vs `core/`.
- **DECISIÓN A TOMAR (ADR-002):** (a) `core/` es el paquete oficial → borrar `domain/application/infrastructure/interfaces` y mover lo poco que aporten (`application/ports/*` Protocols) a `core/ports/`; **o** (b) migrar `core/` a la estructura hexagonal (coste alto, no recomendado ahora).
- **BUSINESS RULES:** tras la decisión, `grep -r "from domain\." api core` y `from application\.` devuelven 0 (o el inverso).
- **ACCEPTANCE CRITERIA:** un solo lugar donde vive el dominio; ADR-002 escrita; suite verde.

### SPEC-B03 — Un universo de activos  *(cierra G-10, D-11)*
- **SCOPE:** `core/config/constants.py` (fuente única `TRADED_UNIVERSE`), `core/config/settings.py:SUPPORTED_SYMBOLS`, `scripts/run_pipeline.py:SCHEDULE`, `core/ml/i1_gate_validator/config.py:PIPELINE_SYMBOLS`.
- **BUSINESS RULES:**
  1. Una lista canónica con nomenclatura única de índices (elegir `US500`/`US30`/`UK100` **o** `SPX500`/`NAS100`; documentar el mapeo a símbolos de broker en un solo dict).
  2. `settings`, pipeline y gate la importan; los `SCHEDULE` offsets se derivan de ella.
  3. Símbolos sin datos en `data/raw/` → marcados `data_available: false`, el pipeline los salta con log explícito.
- **ACCEPTANCE CRITERIA:** `test_universe_is_single_source`: los 3 consumidores producen el mismo set.

### SPEC-B04 — Trace de decisión end-to-end  *(cierra F-06, G-6)*
- **SCOPE:** `scripts/run_pipeline.py`, `core/db/repositories/*` + `core/db/repository.py` (consolidar en uno — ver SPEC-B05), `core/compliance/audit_system.py`, nuevo `GET /trace/{correlation_id}` en un router.
- **BUSINESS RULES:**
  1. `_pipeline_cycle` genera `correlation_id = uuid4()` al inicio y lo propaga a `FeatureSet`, `AgentOutput`, `ConsensusOutput`, `Signal`, `order`, snapshot de portfolio.
  2. Cada repo persiste `correlation_id`; `AuditLog.log` recibe `correlation_id`.
  3. `GET /trace/{id}` (auth `require_trader`) devuelve la cadena: features → salidas de agentes → consenso → señal → veredicto de riesgo → orden → fill → portfolio.
- **OBSERVABILITY:** todos los `logger.*` del ciclo llevan `correlation_id` en el contexto structlog.
- **TEST REQUIREMENTS:** `test_pipeline_cycle_produces_full_trace` (brokers y repos mockeados) — recuperar la cadena completa por id.
- **ACCEPTANCE CRITERIA:** dada una ejecución de `_pipeline_cycle`, `/trace/{id}` reconstruye Market State → Fill.

### SPEC-B05 — Una abstracción de repositorio  *(cierra D-14)*
- **SCOPE:** `core/db/repository.py` (`TradingRepository`, usado por el pipeline) vs `core/db/repositories/{signal,order,audit}_repository.py` (usados por la API).
- **BUSINESS RULES:** elegir una (preferible `repositories/*` por granularidad); `run_pipeline` migra a ellas; `TradingRepository` se elimina o queda como fachada delgada sobre ellas.
- **ACCEPTANCE CRITERIA:** un solo tipo por entidad; tests de repos existentes verdes.

### SPEC-B06 — Una fuente de verdad de estrategias  *(cierra F-03, G-3)*
- **SCOPE:** `core/strategies/strategy_registry.py`, `core/ml/i1_strategies.py`, `core/signals/signal_engine.py`, `scripts/run_pipeline.py`, `data/models/i1_params/`.
- **DECISIÓN (ADR-003):** el pipeline de decisión real es "agentes + consenso"; las "estrategias" son parametrizaciones de señal validadas por el gate I1. Se unifican así:
  1. `StrategyRegistry` es el catálogo único; cada estrategia expone `optimizable_params` y un `evaluate(df) -> signal_series`.
  2. `I1_STRATEGY_REGISTRY` se pliega dentro de `StrategyRegistry` (misma clave, mismo objeto) o se documenta como "vista del gate" sobre el registry.
  3. El gate I1 escribe, por activo aprobado, `data/models/i1_params/<symbol>.json` con `{strategy_id, params, sharpe_net_holdout, approved_at}`.
  4. `SignalEngine.generate` / el pipeline cargan esos params para el activo; **si no hay archivo aprobado para un símbolo, ese símbolo no emite señales** (fail-safe quant) y loguea `no_approved_strategy`.
- **TEST REQUIREMENTS:**
  - `test_pipeline_only_trades_approved_symbols`: con solo `XAUUSD.json` presente → el pipeline emite señales solo de XAUUSD.
  - `test_strategy_registry_is_single_source`: `I1_STRATEGY_REGISTRY` keys ⊆ `StrategyRegistry` keys.
- **ACCEPTANCE CRITERIA:** `grep -rn "default_v1" scripts core` → un único punto, documentado; el marketplace, el simulador y el pipeline consultan el mismo registry.

---

## FASE 3 — CORE CUANTITATIVO

### SPEC-C01 — Reporte quant consolidado por activo/estrategia
- **SCOPE:** nuevo `scripts/run_quant_report.py`, `core/backtesting/metrics.py`.
- **OUTPUTS:** `data/reports/quant_report.{json,md}` con, por (activo, estrategia): Sharpe/Sortino/Calmar, expectancy, profit factor, win rate, max DD, exposure, turnover, cost drag, tail ratio; en WF y en holdout.
- **ACCEPTANCE CRITERIA:** el reporte cubre el universo canónico; los números de XAUUSD coinciden con `i1_gate_report.json`.

### SPEC-C02 — Robustez del edge de XAUUSD (o pivote)
- **SCOPE:** `core/ml/i1_gate_validator/*`, `core/ml/stress_testing.py`.
- **BUSINESS RULES:** para cada activo que pase el gate: (1) Monte Carlo sobre el equity (block bootstrap, 1.000 paths) → CI del Sharpe; (2) barrido de costos (spread/comisión ×1…×3) → punto donde el edge se anula; (3) descomposición por régimen (ADX alto/bajo, vol alto/bajo); (4) walk-forward anclado con re-optimización trimestral.
- **ACCEPTANCE CRITERIA:** documento firmado con la lista de activos con edge robusto y sus condiciones; si es ∅, decisión explícita de pivote registrada en ADR.

---

## FASES 4–6 — RESUMEN DE SPECS (detallar al llegar)

| Spec | Fase | Objetivo | Cierra |
|---|---|---|---|
| SPEC-D01 | F4 | Conectar params I1 aprobados al `SignalEngine` en producción | F-03 (impl.) |
| SPEC-D02 | F4 | MT5 demo conectado end-to-end **o** ADR que saca forex/índices del alcance | G-10 |
| SPEC-D03 | F4 | Strategy scoring continuo + degradación automática (`strategy_rotation.py`) | Adaptabilidad |
| SPEC-E01 | F5 | `ModelRegistry` con métricas por versión (accuracy/F1/precision no nulos) | IA/ML score |
| SPEC-E02 | F5 | Cablear `DriftDetector.set_baseline` + `record()` y `AlphaDecayMonitor.record_trade()` tras cierre de posición | F-06, G-11 |
| SPEC-E03 | F5 | Auditoría de leakage en `core/features/feature_engineering.py` (shift/rolling/target) | Sesgos ML |
| SPEC-F6-01 | F6 | Matriz de correlación rolling + límite por cluster en el gate de riesgo | F-09 (resto) |
| SPEC-F6-02 | F6 | `volatility_targeting.py` cableado al sizing | Risk score |
| SPEC-F6-03 | F6 | 1 venue live (testnet/paper) con reconciliación de posiciones broker↔local | D-13 |
| SPEC-G01 | F8 | `python-jose` → `PyJWT`; blacklist del refresh token en logout; rate limit en `/refresh` | S-03, S-05 |
| SPEC-G02 | F8 | Correlation ID propagado API↔core; Grafana con paneles P&L/señales/riesgo/latencia; alertas por umbral | Observabilidad |
| SPEC-H01 | F2/F8 | Reescribir `docs/architecture/*` + ADR-001..007 | D-18 |

---

## ADRs a redactar en FASE 0

| ADR | Decisión |
|---|---|
| ADR-001 | Monolito modular con 2 procesos (API + worker), no microservicios |
| ADR-002 | `core/` como paquete único de dominio+aplicación; se elimina `domain/application/infrastructure/interfaces` |
| ADR-003 | El pipeline de decisión es "agentes + consenso"; las estrategias son parametrizaciones validadas por el gate I1 |
| ADR-004 | Universo de activos canónico y nomenclatura de índices |
| ADR-005 | Blacklist de JWT fail-open (aceptado); kill switch fail-safe (obligatorio) |
| ADR-006 | Trace de decisión por `correlation_id` persistido en todas las tablas |
| ADR-007 | Ruta a producción: Backtest → OOS → Stress → Paper ≥4 semanas → Capital limitado supervisado |
