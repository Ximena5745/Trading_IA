# PROGRESS — Plan de Elevación de Madurez (2026-08-28)

> Una fila por entregable de todas las fases del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`.
> Fuente de verdad del avance. Se actualiza en cada PR.
>
> **Estados:** `Pendiente` · `En curso` · `Bloqueada` · `Hecho` · `Hecho (pend. auditoría)` · `GATE`
> **Baseline:** `docs/audits/BASELINE_2026-08-28.md` · **Commit base:** `aeea1c5`

## Resumen por fase

| Fase | Entregables | Hechos | Estado | Auditoría de cierre |
|---|---|---|---|---|
| F0 — Gobernanza mínima | 2 | 2 | **GO** | `docs/audits/AUDIT_F0_2026-08-28.md` |
| F1 — Habilitación mínima del core | 9 | 7 | En curso (1.1–1.7 hechos, sigue 1.8) | — |
| F2 — Validación del core + GATE | 7 | 0 | Pendiente | ⛔ GATE |
| F3 — Coherencia arquitectónica | 5 | 0 | Pendiente | — |
| F4 — Estrategias y multi-activo | 3 | 0 | Pendiente | — |
| F5 — IA/ML | 4 | 0 | Pendiente | — |
| F6 — Risk & Execution | 4 | 0 | Pendiente | — |
| F7 — Testing avanzado | 6 | 0 | Pendiente | — |
| F8 — Seguridad/DevSecOps/Observabilidad | 6 | 0 | Pendiente | — |
| F9 — Paper Trading extendido | 4 | 0 | Pendiente | GATE pre-capital |
| F10 — Production Readiness | 6 | 0 | Pendiente | Production Gate |

---

## BLOQUE A — hasta el GATE

### F0 — Gobernanza mínima

| ID | Entregable | Estado | Evidencia | PR |
|---|---|---|---|---|
| 0.1 | ADR-003 (core = agentes + consenso; estrategias = params I1), ADR-004 (universo canónico + nomenclatura), ADR-005 (kill switch fail-safe; blacklist fail-open) | Hecho | `docs/adr/ADR-003-*.md`, `docs/adr/ADR-004-*.md`, `docs/adr/ADR-005-*.md`, `docs/adr/README.md` | `043d218` (+ correcciones F0-A01/02/03 sin commitear) |
| 0.2 | `docs/audits/AUDIT_TEMPLATE.md` + `docs/audits/BASELINE_2026-08-28.md` (21 áreas, congelado) + `docs/PROGRESS.md` (una fila por entregable) | Hecho | `docs/audits/AUDIT_TEMPLATE.md`, `docs/audits/BASELINE_2026-08-28.md`, `docs/PROGRESS.md` | `043d218` |

**Auditoría de cierre F0:** ✅ **GO** — `docs/audits/AUDIT_F0_2026-08-28.md`. 3 discrepancias menores doc↔código (P3) encontradas y corregidas en el pase; sin P0/P1/P2; sin regresiones. Documentación 3.5 → 3.8; global 4.6 sin cambio.

### F1 — Habilitación mínima del core

| ID | Entregable | Spec | Cierra | Estado | Evidencia | PR |
|---|---|---|---|---|---|---|
| 1.1 | Split worker/API: quitar APScheduler + `_refresh_task` del `lifespan`; `run_pipeline.py` único dueño con lock Redis `SET NX EX`; servicio `worker` en compose | SPEC-A02 | F-04, D-04 | Hecho (pend. auditoría F1) | `core/infrastructure/scheduler_lock.py`, `scripts/run_pipeline.py:run_scheduler`, `api/main.py:lifespan`, `docker/docker-compose.yml:worker`, `tests/unit/test_scheduler_split.py` (7 ✅) | |
| 1.2 | Empaquetado + persistencia: `COPY alembic/` + `alembic.ini`; fail-fast si `EXECUTION_MODE=live` sin DB; `/health` expone `db_initialized`; HEALTHCHECK sin `requests` | SPEC-A03 | F-05, D-05, D-22 | Hecho (pend. auditoría F1) | `docker/Dockerfile` (COPY alembic + HEALTHCHECK urllib + data no horneada), `api/main.py:lifespan` (raise en live), `api/main.py:/health` (`db_initialized`), `docker/docker-compose.yml` (`../data:/app/data` en app+worker), `tests/unit/test_startup_db_policy.py` (3 ✅) | |
| 1.3 | Un universo de activos: `TRADED_UNIVERSE` único en `core/config/constants.py` + dict de mapeo a broker; los 3 consumidores lo importan; símbolos sin datos → skip con log | SPEC-B03 | G-10, D-11 | Hecho (pend. auditoría F1) | `core/config/constants.py` (`TRADED_UNIVERSE`, `BROKER_SYMBOL_MAP`, `has_market_data`, `SPX500`→`US500`), `core/config/settings.py` (`SUPPORTED_SYMBOLS = list(TRADED_UNIVERSE)`), `core/ml/i1_gate_validator/config.py` (`PIPELINE_SYMBOLS` derivado), `scripts/run_pipeline.py` (`SCHEDULE` derivado + Gate 0 `cycle_skipped_no_data`), `tests/unit/test_universe_single_source.py` (13 ✅) | |
| 1.4 | Una fuente de estrategias + conectar params I1 al pipeline: `StrategyRegistry` catálogo único; gate I1 escribe `data/models/i1_params/<symbol>.json`; pipeline carga params por activo; sin archivo aprobado ⇒ no emite señales; `grep default_v1` → 1 punto | SPEC-B06, SPEC-D01 | F-03, G-3 | Hecho (pend. auditoría F1) | `core/strategies/approved_params.py` (nuevo: contrato `<SYMBOL>.json`, `load_approved_strategy`, `write_approved_params`), `core/strategies/strategy_registry.py` (pliega `I1_STRATEGY_REGISTRY`: `strategy_ids()`/`get_i1_spec()`/`has()`), `scripts/run_pipeline.py` (Gate 0b `no_approved_strategy` + confirmación `signal_vetoed_by_strategy` + `strategy_id` real), `core/ml/i1_gate_validator/gate_validator.py` (`_write_approved` para activos `passed`), `core/signals/signal_engine.py` (`default_v1` = punto único), `data/models/i1_params/` (6 legacy → `legacy/`, nuevo `XAUUSD.json`), `tests/unit/test_approved_strategy_wiring.py` (7 ✅) | |
| 1.5 | Correctitud de decisiones: fix tests HMM; exposición agregada de cartera en `RiskManager.validate_signal`; `run_pipeline` pasa `recent_trades` reales a `update_kill_switch` | SPEC-A08, SPEC-A05 (f1) | D-12, F-09, D-09 | Hecho (pend. auditoría F1) | `core/adaptation/hmm_regime_detector.py` (drop NaN, `MIN_TRAIN_SAMPLES`, states adaptativos, `diag`+`min_covar`), `core/risk/risk_manager.py` (`aggregate_open_exposure` + chequeo directo de pérdida diaria en `validate_signal`), `core/portfolio/portfolio_manager*.py` (`get_recent_trades` + registro de cierres), `scripts/run_pipeline.py` (`recent_trades` reales al kill switch), `tests/unit/test_risk_decision_correctness.py` (6 ✅) + `test_hmm_regime_detector.py` (12 ✅, antes 2 ❌) | |
| 1.6 | Trazabilidad mínima + productor: `correlation_id` en `_pipeline_cycle` propagado y persistido; `GET /trace/{id}`; pipeline persiste señal vía repo + registra decisión en `AuditLog` | SPEC-B04, F-06 | F-06, G-6 | Hecho (pend. auditoría F1; falta columna `correlation_id` en tablas DB — migración alembic diferida a F3.2) | `core/observability/decision_tracer.py` (`TraceStore` Redis+memoria, `get/set_trace_store`), `core/models.py` (`correlation_id` en `FeatureSet`/`AgentOutput`/`ConsensusOutput`/`Signal`), `scripts/run_pipeline.py` (genera `correlation_id`, `bind_contextvars`, `tracer.record` de las 8 etapas, `AuditLog` por decisión, `repo.save_signal` con id), `api/routes/trace.py` (`GET /trace/{id}` + `require_trader`), `api/main.py` (router), `tests/unit/test_pipeline_trace.py` (3 ✅: `_pipeline_cycle` mockeado → traza completa; endpoint 200/404) | |
| 1.7 | Suelo de seguridad: `REGISTRATION_ENABLED` (default false); registro público solo `viewer`; `POST /auth/users` con `require_admin`; validador de `JWT_SECRET_KEY` siempre activo | SPEC-A01 (subset) | **F-01 (P0)**, F-08 | Hecho (pend. auditoría F1) | `core/config/settings.py` (`REGISTRATION_ENABLED`, `ALLOW_INSECURE_JWT`, validador JWT siempre activo: ≥32 y ≠ default), `api/routes/auth.py` (`/register` → 404 si off / solo `viewer` / sin campo `role`; nuevo `POST /auth/users` con `require_admin`; password `min_length=12`), `tests/conftest.py` (`ALLOW_INSECURE_JWT=true`), `.env.example`, `tests/unit/test_security_floor.py` (6 ✅) | |
| 1.8 | Base de tests herméticos: fixture `docker_services` (testcontainers); fixture `live_server` para `test_dashboard_e2e.py`; marca `@pytest.mark.integration`; fix `bandita`→`bandit`; CI unit+integration en un job | SPEC-B01, SPEC-A07 (subset) | G-8, D-10, F-07 | Pendiente | | |
| 1.9 | Entorno reproducible: `docker compose up` levanta `api`+`worker`+`db`+`redis`; migraciones aplicadas; runbook `docs/RUN_CORE_VALIDATION.md` | — | — | Pendiente | | |

**Auditoría de cierre F1:** 5 hitos + tests `test_scheduler_single_owner`, `test_startup_live_without_db_exits`, `test_risk_portfolio_exposure_aggregation`, `test_pipeline_only_trades_approved_symbols`, `test_universe_is_single_source`, `test_pipeline_cycle_produces_full_trace`, `test_public_register_cannot_set_role`.

### F2 — Validación del core · ⛔ GATE

| ID | Entregable | Track | Estado | Evidencia | PR |
|---|---|---|---|---|---|
| 2.1 | Corrida end-to-end en paper contra Binance testnet + datos reales; checklist por etapa | A (¿funciona?) | Pendiente | | |
| 2.2 | Prueba de reproducibilidad: 2 corridas sobre el mismo dataset → resultado idéntico | A | Pendiente | | |
| 2.3 | Ventana de paper ~2 semanas; cada operación/rechazo explicado vía `GET /trace/{id}`; `docs/CORE_PAPER_WINDOW_<fecha>.md` | A | Pendiente | | |
| 2.4 | Ampliación/saneamiento de datos + auditoría de leakage de `feature_engineering.py` / `target_engine.py` | B (¿edge?) | Pendiente | | |
| 2.5 | `scripts/run_quant_report.py` → `data/reports/quant_report.{json,md}` (Sharpe/Sortino/Calmar/expectancy/PF/DD/...) | B | Pendiente | | |
| 2.6 | Robustez del edge: Monte Carlo block-bootstrap 1000 paths; barrido de costos ×1..×3; descomposición por régimen; walk-forward anclado | B | Pendiente | | |
| 2.7 | `docs/CORE_VALIDATION_DECISION_<fecha>.md`: veredicto de las 3 condiciones; activos que operan o mini-plan de pivote | Decisión | Pendiente | | |

**⛔ GATE F2:** (a) FUNCIONA + (b) EDGE (≥1 activo Sharpe neto holdout ≥ 0.8, CI MC > 0, sobrevive costos ×2, no mono-régimen) + (c) SIN PÉRDIDA NO EXPLICADA (~2 sem paper). **GO** solo si las tres → F3. **NO-GO** → el plan se detiene.

---

## BLOQUE B — robustecer (solo si GATE F2 = GO)

### F3 — Coherencia arquitectónica

| ID | Entregable | Spec | Cierra | Estado | Evidencia | PR |
|---|---|---|---|---|---|---|
| 3.1 | Un árbol de capas (ADR-002): `core/` oficial; migrar `Protocol` de `application/ports/*` a `core/ports/`; eliminar `domain/application/infrastructure/interfaces` | SPEC-B02 | G-9, D-07 | Pendiente | | |
| 3.2 | Una abstracción de repositorio: consolidar `core/db/repository.py` y `core/db/repositories/*`; `run_pipeline` migra | SPEC-B05 | D-14 | Pendiente | | |
| 3.3 | Reescritura de `docs/architecture/` con la arquitectura real; consolidación de docs de estado en `docs/STATUS.md`; `PLAN_MAESTRO.md` → `docs/ROADMAP.md` + `CHANGELOG.md` | SPEC-H01 | D-18 | Pendiente | | |
| 3.4 | ADR-001, ADR-006, ADR-007 restantes; `docs/api-reference` regenerada desde `/openapi.json` | SPEC-H01 | D-18 | Pendiente | | |
| 3.5 | Refactor de god files con spec previa: `mtf_sl_tp_manager` (cálculo puro vs política), `asset_specific_models` | — | D-16 | Pendiente | | |

### F4 — Estrategias y multi-activo

| ID | Entregable | Spec | Estado | Evidencia | PR |
|---|---|---|---|---|---|
| 4.1 | Strategy scoring continuo + degradación automática: cablear `strategy_rotation.py` y `auto_adaptation.py` | SPEC-D03 | Pendiente | | |
| 4.2 | MT5 demo end-to-end (`MT5Client` + `MT5Executor` contra demo IC Markets) **o** ADR-008 que saca forex/índices/oro del alcance | SPEC-D02 | Pendiente | | |
| 4.3 | Backtest OOS por estrategia como job real de CI (walk-forward, no el smoke `ci_backtest_gate.py`) | SPEC-D01/F7 | Pendiente | | |

### F5 — IA/ML e inteligencia adaptativa

| ID | Entregable | Spec | Estado | Evidencia | PR |
|---|---|---|---|---|---|
| 5.1 | `ModelRegistry` con métricas por versión; `/models` deja de devolver `metrics_tracked:false` | SPEC-E01 | Pendiente | | |
| 5.2 | Cablear `DriftDetector.set_baseline()` + `record()` y `AlphaDecayMonitor.record_trade()` desde el cierre de posición en `_pipeline_cycle` | SPEC-E02 | Pendiente | | |
| 5.3 | Auditoría formal de leakage / look-ahead / survivorship + `docs/ML_BIAS_AUDIT_<fecha>.md` | SPEC-E03 | Pendiente | | |
| 5.4 | `model_validation_gate.py` obligatorio antes de promover cualquier `.pkl` a producción | SPEC-E01 | Pendiente | | |

### F6 — Risk & Execution intelligence

| ID | Entregable | Spec | Cierra | Estado | Evidencia | PR |
|---|---|---|---|---|---|---|
| 6.1 | Matriz de correlación rolling + límite por cluster en `RiskManager.validate_signal` (vía `portfolio_risk_engine.py`) | SPEC-F6-01 | F-09 (resto) | Pendiente | | |
| 6.2 | `volatility_targeting.py` cableado al `PositionSizer` | SPEC-F6-02 | — | Pendiente | | |
| 6.3 | 1 venue live en testnet end-to-end con reconciliación; segregar `MarketDataSource` vs `TradingVenue` (LSP) | SPEC-F6-03 | D-13 | Pendiente | | |
| 6.4 | Circuit breakers de ejecución: stale price, límite órdenes/min, parada ante desconexión, kill switch ejercido en live-testnet | SPEC-F6-03 | — | Pendiente | | |

### F7 — Testing y validación avanzada

| ID | Entregable | Estado | Evidencia | PR |
|---|---|---|---|---|
| 7.1 | `tests/e2e/test_pipeline_cycle.py`: ciclo completo con brokers/repos efímeros, verde en CI | Pendiente | | |
| 7.2 | Walk-forward / gate I1 como job real de CI (falla si un activo aprobado deja de pasar) | Pendiente | | |
| 7.3 | Property-based tests de riesgo (Hypothesis): invariantes de `RiskManager` y `PositionSizer` | Pendiente | | |
| 7.4 | Cobertura `core/` ≥ 75% con gate en CI; tests de `api/routes/` sin cobertura | Pendiente | | |
| 7.5 | Tests de concurrencia (scheduler multi-worker, kill switch concurrente, idempotencia bajo replay) | Pendiente | | |
| 7.6 | Chaos básico: Redis/Postgres/broker caídos → degradación fail-safe verificada | Pendiente | | |

### F8 — Seguridad, DevSecOps y Observabilidad

| ID | Entregable | Spec | Cierra | Estado | Evidencia | PR |
|---|---|---|---|---|---|---|
| 8.1 | `python-jose` → `PyJWT`; revisión completa de JWT (algoritmos, expiración, `jti`, blacklist access + refresh; rate limit `/refresh`; validar token en `KillSwitchRedis.reset`) | SPEC-G01 | S-03, S-05, S-06 | Pendiente | | |
| 8.2 | Correlation ID en todas las capas (API ↔ core ↔ worker): middleware que lo genera/propaga y lo mete en structlog | SPEC-G02 (parte) | Observabilidad | Pendiente | | |
| 8.3 | Grafana con paneles reales (P&L, señales/hora, rechazos de riesgo, latencia, kill switch, drift) + alertas Telegram | SPEC-G02 | Observabilidad | Pendiente | | |
| 8.4 | Gestión de secretos: quitar defaults inseguros de compose; documentar rotación; evaluar Vault / `docker secrets` | — | S-08, S-09, D-21 | Pendiente | | |
| 8.5 | Hardening de despliegue: no publicar 5432/6379 en prod; `nginx.conf` con TLS + headers; Trivy + SBOM en CI | — | S-08 | Pendiente | | |
| 8.6 | Auditar y estrechar los ~148 `except Exception` (loguear con contexto, nunca degradar seguridad en silencio) | — | D-17, S-07 | Pendiente | | |

### F9 — Paper Trading extendido

| ID | Entregable | Estado | Evidencia | PR |
|---|---|---|---|---|
| 9.1 | Worker 24/7 contra Binance testnet + MT5 demo; runbook de arranque/parada/recuperación | Pendiente | | |
| 9.2 | Monitoreo diario: checklist de salud, revisión de trazas anómalas, métricas vs lo predicho en F2 | Pendiente | | |
| 9.3 | Ejercicio real del kill switch y de los circuit breakers en vivo | Pendiente | | |
| 9.4 | `docs/PAPER_TRADING_REPORT_<fecha>.md`: P&L, señales, rechazos, slippage realizado vs esperado, incidentes, drift, comparación con F2 | Pendiente | | |

**GATE F9 (previo a capital real):** uptime ≥28 días; métricas coherentes con F2; sin incidentes de seguridad ni pérdida no explicada; kill switch demostrado en vivo.

### F10 — Production Readiness (capital limitado supervisado)

| ID | Entregable | Estado | Evidencia | PR |
|---|---|---|---|---|
| 10.1 | HA del worker: activo/pasivo con el lock Redis como failover; prueba de failover documentada | Pendiente | | |
| 10.2 | Runbooks operativos: arranque, parada de emergencia, recuperación, rotación de secretos, despliegue, on-call | Pendiente | | |
| 10.3 | Disaster Recovery probado: backup automatizado de Postgres/TimescaleDB, restore verificado, RTO/RPO | Pendiente | | |
| 10.4 | Revisión legal/regulatoria previa a live: `docs/COMPLIANCE_REVIEW_<fecha>.md` | Pendiente (externo, bloqueante) | | |
| 10.5 | Despliegue con capital limitado: hard cap en `settings`; `TRADING_ENABLED` con doble confirmación; `EXECUTION_MODE=live` solo tras checklist firmado | Pendiente | | |
| 10.6 | Post-deploy review a 14 y 30 días: `docs/POST_DEPLOY_REVIEW_<fecha>.md` (realizado vs paper vs backtest) | Pendiente | | |

**Production Gate F10:** score global ≥ 7.5/10, 0 P0/P1, DR y failover probados, compliance cerrado, post-deploy a 30 días sin sorpresas.
