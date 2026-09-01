# Plan de Elevación de Madurez — TRADER AI

> **Fecha:** 2026-08-28 · **Base:** `docs/AUDITORIA_INTEGRAL_2026-08-28.md` (commit `aeea1c5`) y `docs/SPEC_BACKLOG_2026-08-28.md`
> **Estado:** aprobado · **en ejecución** · **Ejecución:** 1 persona + asistencia IA
> **Avance (2026-08-31):** F0 ✅ GO · F1 ✅ GO CON CONDICIONES · F2 ⛔ **NO-GO CONCLUYENTE** (condición (b) — sin edge robusto) → `docs/CORE_VALIDATION_DECISION_2026-08-30.md`. **Bloque B (F3–F10) en pausa.** **Pivote Rama 1 ejecutado** → `docs/CORE_VALIDATION_RAMA1_2026-08-30.md`: (1) CostModel de XAUUSD corregido (bug ~100×; Momentum holdout 1.32→1.02); (2) BTC/ETH con 9 años de datos / holdout 1.8 años → todas las familias 1h negativas; (3+4) XAUUSD extendido a **28.4 años vía MT5 IC Markets**, holdout 2.2 años → **extender el holdout NO rescató el edge; cada métrica se degrada monótonamente** (MC full-sample cruza cero, anchored WF ≤ 0). El edge era la ventana 2021-2026. **⛔ NO-GO de (b) CONCLUYENTE.**
> **Rama 2 (2026-08-31)** — `docs/CORE_VALIDATION_RAMA2_2026-08-31.md`. Barrido de **84 combos** (7 símbolos × 6 familias × {1d,4h}) sobre 14-28 años de datos MT5 IC Markets → **83 FRAGILE, 1 EDGE_ROBUST** (`US500/vol_breakout_v1/1d`), y ese único candidato es **falso positivo** (verificado sobre S&P 500 real 1970→2026, 57 años: holdout Sharpe −0.18, P(Sh>0) full-sample 0.117). **Acumulado Ramas 1+2: ~95 combos activo×estrategia×TF sobre 9-57 años → 0 con edge robusto.** Ramas 1 y 2 del pivote agotadas sin GO. **Decisión pendiente del usuario: Rama 3 (replanteo de universo) vs Rama 4 (replanteo de producto).** Detalle y recomendación: `docs/PROGRESS.md`.

## Context

**Por qué este plan.** La auditoría integral del 2026-08-28 (`docs/AUDITORIA_INTEGRAL_2026-08-28.md`, commit `aeea1c5`) situó la madurez global en **4.6/10** y dejó cuatro bloqueos de fondo: (1) `POST /auth/register` permite auto-asignarse rol `admin`; (2) el gate I1 corregido reprueba 7/8 activos — sin evidencia de edge salvo XAUUSD; (3) tres registros de "estrategia" desconectados y el pipeline real decide con `strategy_id="default_v1"` fijo, dos árboles de capas, tres universos de activos, cadena de decisión sin productor de trazas; (4) `Dockerfile` corre 4 workers con el scheduler embebido (pipeline y órdenes cuádruples) y la imagen no incluye `alembic/` (arranca sin DB en silencio).

**Principio rector (decisión del usuario).** El foco es **la funcionalidad y el core del sistema**. Si el core no funciona correctamente y no tiene edge, robustecer el resto (seguridad completa, arquitectura, MLOps, observabilidad, HA) no aporta valor. Por tanto el plan se ordena así:

1. **Habilitación mínima** — solo lo imprescindible para correr el pipeline end-to-end y confiar en sus números (incluye un suelo de seguridad barato y una base de tests herméticos, por decisión del usuario).
2. **Validación del core** — ⛔ **GATE**: ¿el pipeline ejecuta ciclos completos, correctos y reproducibles? ¿tiene edge robusto en ≥1 activo? ¿toda operación y rechazo se explica por la traza en una ventana de ~2 semanas de paper?
3. **Robustecer** (fases 3–10) — **solo si el GATE da GO**. Coherencia arquitectónica, estrategias/multi-activo, IA/ML, risk/execution intelligence, testing avanzado, seguridad/DevSecOps/observabilidad completa, paper trading extendido y production readiness con capital limitado.

**Parámetros confirmados.**
- **Ejecución:** 1 persona + asistencia IA. Estimaciones en **días-persona (d)** secuenciales, sin fechas de calendario.
- **Alcance final:** hasta producción con capital limitado supervisado (condicionado al GATE).
- **GATE de validación del core:** triple condición (funciona **Y** edge **Y** sin pérdida no explicada). NO-GO ⇒ el plan se detiene en la fase 2 y entra un ciclo de arreglo/pivote antes de re-planificar 3–10.

**Esfuerzo hasta el GATE:** ~85 días-persona activos + ~2 semanas de observación (≈ 4 meses en solitario). **Esfuerzo total** (si GATE=GO): ~330 días-persona + compliance externo + 4 semanas de observación en la fase 9.

---

## Estado de ejecución — 2026-08-30

> Instantánea del avance. Fuente de verdad por entregable: `docs/PROGRESS.md`.
> Todo el trabajo F1/F2 vive en una rama sobre `043d218` (F0), **sin commitear** al
> redactar esto. Los "pases de auditoría fresca" que exige el método siguen pendientes.

| Fase | Entregables hechos | Veredicto de cierre | Doc |
|---|---|---|---|
| **F0** — Gobernanza mínima | 2 / 2 | ✅ **GO** | `docs/audits/AUDIT_F0_2026-08-28.md` |
| **F1** — Habilitación mínima del core | 9 / 9 | ✅ **GO CON CONDICIONES** | `docs/audits/AUDIT_F1_2026-08-30.md` |
| **F2** — Validación del core (⛔ GATE) | 5 / 7 (2.2, 2.4, 2.5, 2.6, 2.7) · 2.1 y 2.3 requieren stack + ventana de 2 sem | ⛔ **NO-GO preliminar** | `docs/CORE_VALIDATION_DECISION_2026-08-30.md` |
| F3–F10 (Bloque B) | — | **En pausa** (depende de GATE F2 = GO) | — |

**Condiciones abiertas de F1** (no bloquean, con fecha de cierre comprometida):
1. Pase de auditoría fresco (sesión nueva sin contexto, acotada a F1).
2. `pytest -m integration` verde en runner con Docker (CI cableado, falta el primer push).

**GATE F2 — por qué NO-GO preliminar.** La condición **(b) EDGE** no se cumple con el
criterio literal del plan: de 8 símbolos, solo XAUUSD tiene Sharpe neto holdout ≥ 0.8
(+1.32), y al pasarlo por la batería de robustez (2.6) resulta **FRÁGIL** — el CI de
Monte Carlo del holdout es **[−1.43, +3.76]** (cruza cero) y el edge depende del
régimen ADX. Confirma **F-02 (P0, sin edge)** a nivel de universo (7/8 con Sharpe
holdout negativo). (a) queda parcial (determinismo de la cadena de decisión ✅ vía
2.2; corrida real testnet ⏳ 2.1/2.3) y (c) sin evaluar — ninguna de las dos puede
revertir el NO-GO.

**Qué sigue.** Mini-plan de pivote de 4–8 semanas (detalle en
`CORE_VALIDATION_DECISION_2026-08-30.md`): **Rama 0** (cerrar formalmente (a)/(c) +
pase de auditoría cuantitativa independiente) + **Rama 1** (extender histórico 1h a
≥ 4–5 años, revisar el `CostModel` de XAUUSD, re-correr 2.5/2.6 sobre el holdout
largo y sobre las estrategias alternativas de XAUUSD). Si Rama 1 no da GO: 4h/1d y
familias nuevas → replanteo de universo → replanteo de producto. **No se inicia
ningún entregable de F3–F10 hasta que el GATE F2 dé GO.**

> **Rama 1 — subset ejecutado (2026-08-30)** — `docs/CORE_VALIDATION_RAMA1_2026-08-30.md`.
> (1) **CostModel de XAUUSD**: bug de unidades ~100× corregido (`spread_pips` 0.25→30);
> XAUUSD/Momentum cae de holdout Sharpe 1.32 a **1.02** y baja del gate 0.8 a costos
> ×1.75; el MC full-sample pasa a cruzar cero. `i1_gate_report.json` quedó optimista.
> (2) **BTC/ETH**: los parquet de 9 años ya existían sin cablear; con holdout de
> 1.8 años **todas** las familias 1h dan Sharpe neto holdout **negativo** → la
> hipótesis "es longitud de datos" se **refuta** para cripto.
> (3) **Alternativas de XAUUSD** bajo 2.6: ninguna pasa (b); **`MA_10_30`** es el
> mejor candidato (holdout 2.31, sobrevive costos ×3, MC full CI inf +0.25) pero
> falla mono-régimen ADX y por −0.04 en el MC holdout.
> **Pendiente por infra:** histórico 1h de XAUUSD ≥ 4–5 años (proveedor externo;
> yfinance no da intradía > ~730 días) para re-probar `MA_10_30`; Rama 0 completa.
> **NO-GO de (b) reforzado.**

---

## Convenciones

### Formato de cada fase
- **Objetivo** — qué cambia en el sistema y en el score de madurez.
- **Entregables** — artefacto concreto + días-persona. `SPEC-*` → `docs/SPEC_BACKLOG_2026-08-28.md`; `F-*/D-*/G-*` → la auditoría.
- **Hitos** — puntos verificables intermedios ("ya se puede X").
- **Auditoría de cierre (gate)** — condición para pasar a la fase siguiente.

### Auditoría de cierre — procedimiento estándar (todas las fases)
Produce `docs/audits/AUDIT_F<n>_<AAAA-MM-DD>.md` y un veredicto:

| Veredicto | Significado |
|---|---|
| **GO** | Todos los criterios objetivos cumplidos. Se inicia la fase siguiente. |
| **GO CON CONDICIONES** | ≤2 hallazgos menores con fecha de cierre comprometida. La siguiente arranca en paralelo al cierre. |
| **NO-GO** | Criterio bloqueante incumplido. No se avanza. |

Método (3 partes, siempre):
1. **Checklist objetivo** — comandos/tests reproducibles con salida esperada (cada fase define el suyo).
2. **Pase de auditoría fresco** — sesión nueva de Claude Code aplicando `TRADER_AI_PROMPT_MAESTRO.md` acotado al alcance de la fase, sin contexto de la implementación, verificando contra el código.
3. **No-regresión** — re-verificar que ningún hallazgo `GO` previo (2026-05, 07, 08 y fases anteriores) se reabrió. Matriz "hallazgo previo → estado actual → evidencia".

Salida: matriz de hallazgos (`ID | área | hallazgo | evidencia | severidad | veredicto`) + score de madurez por área + veredicto global.

### Grafo de dependencias
```
F0 ──▶ F1 ──▶ F2 ──[⛔ GATE: funciona Y edge Y sin pérdida no explicada]──┐
                                                                          │
   NO-GO ──▶ ciclo de arreglo/pivote (4–8 sem) ──▶ re-planificar F3–F10   │
                                                                          │ GO
   ┌──────────────────────────────────────────────────────────────────────┘
   ▼
   F3 ──▶ F4 ──▶ F5 ──┐
              │        ├──▶ F7 ──▶ F8 ──▶ F9 ──[GATE paper]──▶ F10 ──[Production Gate]
              └──▶ F6 ─┘
   (F5 y F6 solapan parcialmente tras F4)
```

---

# BLOQUE A — HASTA EL GATE (siempre se ejecuta)

## FASE 0 — Gobernanza mínima

> **Estado (2026-08-30): ✅ GO.** 0.1 y 0.2 hechos. `docs/audits/AUDIT_F0_2026-08-28.md`
> (3 discrepancias doc↔código P3 corregidas en el pase; sin regresiones).

**Objetivo.** Fijar solo las decisiones y el instrumental imprescindibles para que la validación del core sea auditable. Se difiere la reescritura de documentación y la consolidación de docs a la Fase 3 (post-GATE).

**Entregables.**
| # | Entregable | Días |
|---|---|---|
| 0.1 | ADR-003 (el pipeline de decisión es *agentes + consenso*; las estrategias son parametrizaciones validadas por el gate I1, cargadas por activo desde `data/models/i1_params/<symbol>.json`), ADR-004 (universo de activos canónico y nomenclatura de índices), ADR-005 (kill switch fail-safe obligatorio; blacklist JWT fail-open aceptado). | 2 |
| 0.2 | `docs/audits/` con plantilla `AUDIT_TEMPLATE.md` + `docs/audits/BASELINE_2026-08-28.md` (score por 21 áreas, congelado). `docs/PROGRESS.md` con una fila por entregable de todas las fases (ID, fase, estado, evidencia, PR). | 2 |

**Hitos.**
- H0.1 — Existe una decisión escrita e inequívoca de "qué es el core y cómo se valida" (ADR-003).

**Auditoría de cierre F0.** Checklist: las 3 ADRs existen con secciones "Decisión" y "Consecuencias" y no se contradicen con el código actual; `BASELINE` tiene el score por área. Veredicto GO si: la base de medición y la decisión sobre el core están fijadas.

---

## FASE 1 — Habilitación mínima del core

> **Estado (2026-08-30): ✅ GO CON CONDICIONES.** Los 9 entregables (1.1–1.9) hechos
> con tests verdes (`pytest tests/unit tests/quant` → **410 passed / 2 skipped / 0
> failed**). `docs/audits/AUDIT_F1_2026-08-30.md`. **F-01 (P0) cerrado.** Diferido a
> F3.2: columna DB `correlation_id` (migración alembic). Condiciones abiertas:
> (1) pase de auditoría fresco; (2) `pytest -m integration` verde en CI con Docker.

**Objetivo.** Que el pipeline se pueda ejecutar end-to-end de forma determinista y que sus resultados sean confiables y trazables. Incluye el suelo de seguridad barato y la base de tests herméticos. **No** incluye robustez de arquitectura, MLOps, observabilidad completa ni HA.

**Entregables.**
| # | Entregable | Spec | Cierra | Días |
|---|---|---|---|---|
| 1.1 | **Split worker/API.** Quitar APScheduler y `_refresh_task` del `lifespan` de `api/main.py`; `scripts/run_pipeline.py` como único dueño del scheduler con lock Redis (`SET NX EX`); servicio `worker` en `docker-compose.yml`. Sin esto el pipeline corre 4× y sus números no son fiables. | SPEC-A02 | F-04, D-04 | 4 |
| 1.2 | **Empaquetado + persistencia.** `COPY alembic/` + `alembic.ini` en `docker/Dockerfile`; arranque falla (exit≠0) si `EXECUTION_MODE=live` y la DB no inicializa; `/health` expone `db_initialized`; HEALTHCHECK sin `requests`. | SPEC-A03 | F-05, D-05, D-22 | 3 |
| 1.3 | **Un universo de activos.** `TRADED_UNIVERSE` único en `core/config/constants.py` con nomenclatura de índices única + dict de mapeo a símbolos de broker; `settings.SUPPORTED_SYMBOLS`, `run_pipeline.SCHEDULE`, `i1_gate_validator.PIPELINE_SYMBOLS` lo importan; símbolos sin datos → `data_available:false` y el pipeline los salta con log. | SPEC-B03 | G-10, D-11 | 4 |
| 1.4 | **Una fuente de estrategias + conectar params I1 al pipeline.** `StrategyRegistry` catálogo único; `I1_STRATEGY_REGISTRY` se pliega dentro; el gate I1 escribe `data/models/i1_params/<symbol>.json` con `{strategy_id, params, sharpe_net_holdout, approved_at}`; el `SignalEngine`/pipeline **cargan esos params por activo**; **sin archivo aprobado ⇒ ese símbolo no emite señales** (fail-safe quant); `grep -rn "default_v1" scripts core` → un único punto documentado. **Es el núcleo de "poder validar el core": lo que se valida y lo que decide deben ser lo mismo.** | SPEC-B06, SPEC-D01 | F-03, G-3 | 14 |
| 1.5 | **Correctitud de las decisiones.** Fix tests HMM (`test_fit_handles_nan`, `test_predict_with_insufficient_data`) — la detección de régimen está rota; exposición agregada de cartera en `RiskManager.validate_signal` (Σ posiciones abiertas + señal nueva vs `MAX_PORTFOLIO_RISK_PCT`, chequeo directo de pérdida diaria); `run_pipeline` pasa `recent_trades` reales a `update_kill_switch`. | SPEC-A08, SPEC-A05 (fase 1) | D-12, F-09, D-09 | 7 |
| 1.6 | **Trazabilidad mínima + productor.** `correlation_id` generado en `_pipeline_cycle` y propagado a features/agentes/consenso/señal/orden/snapshot, persistido en cada tabla y en `AuditLog`; `GET /trace/{correlation_id}` reconstruye Market State → Fill; el pipeline **persiste la señal** vía repo y **registra la decisión** en `AuditLog`; logs del ciclo con `correlation_id` en el contexto structlog. | SPEC-B04, F-06 (parcial) | F-06, G-6 | 8 |
| 1.7 | **Suelo de seguridad.** `REGISTRATION_ENABLED` (default false); registro público solo crea `viewer`; `POST /auth/users` con `require_admin` para roles elevados; validador de `JWT_SECRET_KEY` siempre activo (≥32 chars, ≠ default). | SPEC-A01 (subset) | F-01, F-08 | 4 |
| 1.8 | **Base de tests herméticos.** Fixture `docker_services` (Postgres+Redis efímeros vía testcontainers); fixture `live_server` que arranca uvicorn en puerto libre para `test_dashboard_e2e.py`; marca `@pytest.mark.integration`; fix typo `bandita`→`bandit` en CI; CI corre unit + integration herméticos en un job. | SPEC-B01, SPEC-A07 (subset) | G-8, D-10, F-07 | 8 |
| 1.9 | **Entorno reproducible.** `docker compose up` levanta `api` (sin jobs) + `worker` (1 dueño) + `db` + `redis`; migraciones aplicadas; runbook `docs/RUN_CORE_VALIDATION.md` para arrancar el stack y correr un ciclo del pipeline contra Binance testnet + datos reales. | — | — | 2 |

**Hitos.**
- H1.1 — `docker compose up` levanta el stack; con `--workers 4` el pipeline ejecuta 1×/símbolo/ventana (contador lo prueba).
- H1.2 — Con solo `XAUUSD.json` aprobado presente, el pipeline emite señales únicamente de XAUUSD; el resto loguea `no_approved_strategy`. `grep -rn "default_v1" scripts core` → 1 punto.
- H1.3 — `GET /trace/{id}` reconstruye un ciclo completo (mocks de broker/DB).
- H1.4 — `pytest tests/unit tests/quant` → 0 failed; `pytest -m integration` en runner con Docker → 0 failed / 0 errors.
- H1.5 — No hay camino a un usuario `admin` sin un `admin` previo (test que lo demuestra).

**Auditoría de cierre F1.**
- Checklist: los 5 hitos + `test_scheduler_single_owner`, `test_startup_live_without_db_exits`, `test_risk_portfolio_exposure_aggregation`, `test_pipeline_only_trades_approved_symbols`, `test_universe_is_single_source`, `test_pipeline_cycle_produces_full_trace`, `test_public_register_cannot_set_role` verdes.
- Pase fresco: mini-auditoría acotada a `scripts/run_pipeline.py`, `core/signals/`, `core/consensus/`, `core/strategies/`, `core/risk/risk_manager.py`, `docker/` — ¿el pipeline es determinista? ¿decide con lo que se valida?
- No-regresión: los 8 hallazgos "Resuelto" de la auditoría 2026-08 siguen resueltos.
- Veredicto GO si: el pipeline se ejecuta de forma determinista, decide con los params validados por I1, es trazable, y no hay escalada de privilegios trivial.

---

## FASE 2 — Validación del core  ·  ⛔ GATE (funciona Y edge Y sin pérdida no explicada)

> **Estado (2026-08-30): ⛔ NO-GO preliminar.** Hechos: **2.2** (reproducibilidad —
> `scripts/check_reproducibility.py`, digests SHA-256 idénticos en 2 pasadas, 0 RNG de
> decisión sin semilla), **2.4** (auditoría de leakage — features sin look-ahead; 6
> puntos en `target_engine.py` no cableados; `scripts/audit_data_quality.py` → 0
> violaciones duras en 6 parquet), **2.5** (`scripts/run_quant_report.py` — H2.1 ✅,
> XAUUSD Momentum holdout Sharpe 1.3232 = gate), **2.6** (`scripts/run_edge_robustness.py`
> — XAUUSD/Momentum = **FRÁGIL**: CI Monte Carlo holdout [−1.43, +3.76], mono-régimen
> ADX), **2.7** (`docs/CORE_VALIDATION_DECISION_2026-08-30.md`). Pendientes por infra:
> **2.1** y **2.3** (stack Docker + testnet + ventana de ~2 semanas). Reportes en
> `data/reports/{reproducibility_report,data_quality_report,quant_report,edge_robustness}.{json,md}`.
> **Veredicto (b) EDGE: no cumplido.** F3–F10 no arrancan.

**Objetivo.** Responder con datos si el core (a) funciona correctamente de punta a punta, (b) tiene edge estadístico robusto neto de costos en ≥1 activo, y (c) opera ~2 semanas en paper sin ninguna decisión sin explicar. Score: Quant 2.5 → (5.0 si GO / se congela); Core Trading 5.0 → 6.5; Backtesting → 6.0.

**Entregables — Track A (¿funciona?).**
| # | Entregable | Días |
|---|---|---|
| 2.1 | Corrida end-to-end del pipeline en paper contra Binance testnet + datos reales; checklist de verificación por etapa (features sin NaN/Inf; consenso coherente con las salidas de agentes; señal con SL/TP/RR válidos y dentro de límites; riesgo evalúa y puede vetar; ejecución paper con `fill_price` y slippage; persistencia de señal/orden/portfolio; alerta emitida). | 5 |
| 2.2 | Prueba de reproducibilidad: 2 corridas del pipeline sobre el mismo conjunto de datos → resultados idénticos (señales, órdenes, snapshots). Documentar cualquier fuente de no-determinismo y eliminarla. | 3 |
| 2.3 | Ventana de paper de ~2 semanas: worker 24/7 contra testnet; monitoreo diario; **cada operación y cada rechazo de riesgo se explica vía `GET /trace/{id}`**; registro `docs/CORE_PAPER_WINDOW_<fecha>.md` con toda decisión anómala y su causa raíz. | 6 (repartidos en 2 sem) |

**Entregables — Track B (¿tiene edge?).**
| # | Entregable | Spec | Días |
|---|---|---|---|
| 2.4 | Ampliación y saneamiento de datos: extender el histórico 1h del universo (timestamps UTC, gaps/outliers marcados); auditoría de leakage de `core/features/feature_engineering.py` y `core/ml/target_engine.py` (shift/rolling/target — solo verificación, sin ML nuevo). | SPEC-E03 (parcial) | 6 |
| 2.5 | Reporte quant consolidado `scripts/run_quant_report.py` → `data/reports/quant_report.{json,md}`: por (activo, estrategia), en WF y holdout: Sharpe/Sortino/Calmar, expectancy, profit factor, win rate, max DD, exposure, turnover, cost drag, tail ratio. | SPEC-C01 | 5 |
| 2.6 | Robustez del edge (por activo que pase el gate I1): Monte Carlo block-bootstrap 1000 paths → CI del Sharpe; barrido de costos ×1..×3 → punto de anulación; descomposición por régimen (ADX alto/bajo, vol alto/bajo); walk-forward anclado con re-optimización trimestral. | SPEC-C02 | 10 |

**Entregable — Decisión.**
| # | Entregable | Días |
|---|---|---|
| 2.7 | `docs/CORE_VALIDATION_DECISION_<fecha>.md`: veredicto de las tres condiciones con evidencia; si GO, lista de activos que operan y por qué; si NO-GO, opciones de pivote (nuevos activos, timeframes, familias de estrategia, o replanteo del producto) y mini-plan de investigación (4–8 semanas). | 3 |

**Hitos.**
- H2.1 — `quant_report.md` cubre el universo canónico; los números de XAUUSD coinciden con `data/reports/i1_gate_report.json`.
- H2.2 — Dos corridas idénticas del pipeline producen exactamente el mismo output.
- H2.3 — En la ventana de paper, el 100 % de operaciones y rechazos tiene explicación en la traza.

**Auditoría de cierre F2 — ⛔ GATE.**
- Checklist: `python scripts/run_quant_report.py` regenera los mismos números; el gate I1 corre en CI y publica artifact; `docs/CORE_PAPER_WINDOW` no tiene decisiones sin causa raíz; la prueba de reproducibilidad pasa.
- Pase fresco: auditoría cuantitativa independiente (Regla 3 y 4 del prompt maestro) — ¿los análisis de robustez soportan la conclusión de edge? ¿el edge sobrevive a costos realistas y a todos los regímenes? — **y** auditoría funcional del pipeline — ¿alguna etapa produce basura silenciosa?
- **Veredicto (las TRES condiciones):**
  - **(a) FUNCIONA** — 2 corridas idénticas → mismo output; toda etapa produce output válido; `GET /trace` reconstruye cualquier ciclo.
  - **(b) EDGE** — ≥1 activo con Sharpe neto holdout ≥ 0.8, CI de Monte Carlo con límite inferior > 0, edge que sobrevive a costos ×2, no dependiente de un único régimen.
  - **(c) SIN PÉRDIDA NO EXPLICADA** — en ~2 semanas de paper, 0 operaciones/rechazos sin explicación en la traza; 0 comportamiento anómalo sin causa raíz.
  - **GO** solo si se cumplen las tres → se continúa a F3.
  - **NO-GO** en cualquiera → **el plan se detiene aquí.** Se ejecuta `docs/CORE_VALIDATION_DECISION` y su mini-plan de investigación/arreglo. F3–F10 se re-planifican después. No se invierte en robustecer un core no validado.

> **Veredicto real (2026-08-30): ⛔ NO-GO preliminar** — condición (b) incumplida
> (`docs/CORE_VALIDATION_DECISION_2026-08-30.md`). El checklist y el pase fresco
> quedan pendientes de la corrida paper (2.1/2.3) y de la auditoría cuantitativa
> independiente, pero **ninguno puede convertir (b) en GO**. **El plan está en el
> ciclo de arreglo/pivote de 4–8 semanas.**

> **F3–F10 asumen GATE F2 = GO.** Hoy ese supuesto **no se cumple** → todo el Bloque
> B está en pausa.

---

# BLOQUE B — ROBUSTECER (solo si GATE F2 = GO)

> **⏸ EN PAUSA (2026-08-30).** El GATE F2 dio **NO-GO preliminar** (sin edge robusto).
> Ninguna fase de este bloque arranca hasta que un ciclo de pivote produzca un edge
> que pase la condición (b) y se re-abra F2 con veredicto GO. Al re-planificar,
> revisar alcance y estimaciones a la luz de lo aprendido en el pivote.

## FASE 3 — Coherencia arquitectónica

**Objetivo.** Que "lo que el sistema hace" sea deducible de "lo que documenta". Score: Arquitectura 5.5 → 7.0; SOLID 4.5 → 6.0; DDD 4.0 → 5.5; Documentación 3.5 → 6.0.

**Entregables.**
| # | Entregable | Spec | Cierra | Días |
|---|---|---|---|---|
| 3.1 | Un árbol de capas (ADR-002): `core/` es el paquete oficial. Migrar los `Protocol` útiles de `application/ports/*` a `core/ports/`; **eliminar** `domain/`, `application/`, `infrastructure/`, `interfaces/`. `grep -r "from domain\.\|from application\." api core` → 0. | SPEC-B02 | G-9, D-07 | 12 |
| 3.2 | Una abstracción de repositorio: consolidar `core/db/repository.py` (`TradingRepository`) y `core/db/repositories/*` en una sola (granular); `run_pipeline` migra a ella; la otra se elimina o queda como fachada delgada. | SPEC-B05 | D-14 | 5 |
| 3.3 | Reescritura de `docs/architecture/` con la arquitectura real (diagrama de la auditoría §ARCHITECTURE AUDIT); Streamlit fuera de los diagramas. Consolidación de docs de estado en `docs/STATUS.md`; `PLAN_MAESTRO.md` → `docs/ROADMAP.md` + `CHANGELOG.md`; el resto a `docs/archive/`. | SPEC-H01 | D-18 | 8 |
| 3.4 | ADR-001, ADR-006, ADR-007 restantes; `docs/api-reference` regenerada desde `/openapi.json`. | SPEC-H01 | D-18 | 3 |
| 3.5 | Refactor de god files con spec previa: `mtf_sl_tp_manager` (cálculo puro vs política), `asset_specific_models`. | — | D-16 | 6 |

**Hitos.** H3.1 — `grep -r "from domain\.\|from application\." api core` → 0. H3.2 — Un solo tipo de repo por entidad. H3.3 — `docs/architecture/` refleja el código; `docs/STATUS.md` es la única fuente de estado.

**Auditoría de cierre F3.** Checklist: hitos + suite verde. Pase fresco: auditoría Clean Architecture + SOLID + doc↔código. No-regresión: F1/F2 intactas. Veredicto GO si: una fuente de verdad por dimensión; documentación de arquitectura alineada con el código.

---

## FASE 4 — Estrategias y multi-activo

**Objetivo.** Rotación y degradación reales; decidir formalmente el alcance multi-activo. Score: Estrategias 5.0 → 6.5; Multi-Asset 4.0 → 6.0; Adaptabilidad 3.5 → 5.5.

**Entregables.**
| # | Entregable | Spec | Días |
|---|---|---|---|
| 4.1 | Strategy scoring continuo + degradación automática: cablear `core/strategies/strategy_rotation.py` y `core/risk/auto_adaptation.py` — una estrategia cuyo Sharpe rolling cae bajo umbral se desactiva sola y alerta. | SPEC-D03 | 10 |
| 4.2 | MT5 demo conectado end-to-end (`MT5Client` + `MT5Executor` contra cuenta demo IC Markets) **o** ADR-008 que saca forex/índices/oro del alcance según qué activos pasaron el GATE F2. | SPEC-D02 | 10 |
| 4.3 | Backtest OOS por estrategia conectada como job real de CI (walk-forward, no el smoke `ci_backtest_gate.py`). | SPEC-D01/F7 | 5 |

**Hitos.** H4.1 — El pipeline opera exactamente los activos aprobados en F2, con sus params. H4.2 — Caída simulada de performance → estrategia desactivada sola + alerta.

**Auditoría de cierre F4.** Checklist: `test_pipeline_only_trades_approved_symbols` con params reales; test de degradación automática; job de backtest OOS en CI. Pase fresco: auditoría de estrategias. Veredicto GO si: cero divergencia entre lo validado y lo que opera; degradación automática demostrada.

---

## FASE 5 — IA/ML e inteligencia adaptativa

**Objetivo.** MLOps mínimo: métricas por modelo, drift y alpha-decay vivos, sin sesgos. Score: IA/ML 3.5 → 6.0; Adaptabilidad 5.5 → 6.5.

**Entregables.**
| # | Entregable | Spec | Días |
|---|---|---|---|
| 5.1 | `ModelRegistry` con métricas por versión (accuracy/F1/precision/AUC reales); `/models` deja de devolver `metrics_tracked:false`. | SPEC-E01 | 10 |
| 5.2 | Cablear `DriftDetector.set_baseline()` + `record()` y `AlphaDecayMonitor.record_trade()` desde el cierre de posición en `_pipeline_cycle`. | SPEC-E02 | 8 |
| 5.3 | Auditoría formal de leakage / look-ahead / survivorship + `docs/ML_BIAS_AUDIT_<fecha>.md`. | SPEC-E03 | 6 |
| 5.4 | `model_validation_gate.py` obligatorio antes de promover cualquier `.pkl` a producción (retrain → validación → registro → promoción). | SPEC-E01 | 6 |

**Hitos.** H5.1 — `/models` con métricas reales. H5.2 — Tras N trades en paper, drift compara contra baseline persistido y alpha-decay muestra Sharpe rolling real. H5.3 — `ML_BIAS_AUDIT` sin hallazgos abiertos.

**Auditoría de cierre F5.** Checklist: métricas no nulas; baseline persistido; `record_trade` invocado en el flujo real (test); reporte de sesgos cerrado. Pase fresco: auditoría IA/ML. Veredicto GO si: sin sesgo conocido sin mitigar; monitores vivos con datos reales.

---

## FASE 6 — Risk & Execution intelligence

**Objetivo.** Gate de riesgo a nivel de cartera; ejecución en venue real (testnet) con reconciliación. Score: Risk 5.5 → 7.5; Execution 5.5 → 7.0.

**Entregables.**
| # | Entregable | Spec | Cierra | Días |
|---|---|---|---|---|
| 6.1 | Matriz de correlación rolling + límite por cluster en `RiskManager.validate_signal` (vía `portfolio_risk_engine.py`). | SPEC-F6-01 | F-09 (resto) | 8 |
| 6.2 | `volatility_targeting.py` cableado al `PositionSizer` (objetivo de volatilidad de cartera). | SPEC-F6-02 | — | 6 |
| 6.3 | 1 venue live en testnet end-to-end con reconciliación: `place_order`/`cancel_order`/`get_order_status` reales (quitar `NotImplementedError` para ese venue); loop de reconciliación broker↔local; segregar `MarketDataSource` vs `TradingVenue` (LSP). | SPEC-F6-03 | D-13 | 15 |
| 6.4 | Circuit breakers de ejecución: chequeo de antigüedad del último candle (stale price); límite órdenes/minuto; parada ante desconexión del broker; kill switch ejercido en el flujo live-testnet. | SPEC-F6-03 | — | 6 |

**Hitos.** H6.1 — 3 posiciones correlacionadas → la 4ª se rechaza; suma de exposiciones respeta el límite. H6.2 — Orden en testnet reconciliada en el estado local; desconexión del broker detiene nuevas órdenes.

**Auditoría de cierre F6.** Checklist: tests de correlación/cluster, reconciliación, stale-price. Pase fresco: auditoría de riesgo y ejecución. Veredicto GO si: el gate de riesgo razona a nivel de cartera; hay un venue con ciclo de ejecución completo y reconciliado en testnet.

---

## FASE 7 — Testing y validación avanzada

**Objetivo.** Confianza para operar sin supervisión constante. Score: Testing 6.5 → 8.0; DevSecOps 6.0 → 7.0.

**Entregables.**
| # | Entregable | Días |
|---|---|---|
| 7.1 | `tests/e2e/test_pipeline_cycle.py`: ciclo completo con brokers/repos efímeros (testcontainers), verde en CI. | 6 |
| 7.2 | Walk-forward / gate I1 como job real de CI (falla si un activo aprobado deja de pasar). | 4 |
| 7.3 | Property-based tests de riesgo (Hypothesis): invariantes de `RiskManager` y `PositionSizer`. | 6 |
| 7.4 | Cobertura `core/` ≥ 75% con gate en CI; tests de `api/routes/` sin cobertura (`portfolio`, `strategies`, `marketplace`, `simulation`, `backtesting`, `models`, `monitoring`). | 8 |
| 7.5 | Tests de concurrencia (scheduler multi-worker, kill switch concurrente, idempotencia bajo replay). | 5 |
| 7.6 | Chaos básico: Redis/Postgres/broker caídos → degradación fail-safe verificada (no se abre trading). | 5 |

**Hitos.** H7.1 — CI ejecuta unit + integration + e2e + walk-forward + cobertura, todo verde. H7.2 — Chaos demuestra que ninguna caída de infra abre trading.

**Auditoría de cierre F7.** Checklist: cobertura ≥ 75%; e2e, walk-forward y chaos verdes en CI. Pase fresco: auditoría de testing (¿cobertura real o teatro? ¿falsos verdes?). Veredicto GO si: ningún módulo crítico (risk, execution, consensus, signal, pipeline) sin test significativo.

---

## FASE 8 — Seguridad, DevSecOps y Observabilidad

**Objetivo.** Postura de seguridad y observabilidad de operación continua. Score: Seguridad 6.5 → 8.0; Observabilidad 6.5 → 8.0; DevSecOps 7.0 → 8.0.

**Entregables.**
| # | Entregable | Spec | Cierra | Días |
|---|---|---|---|---|
| 8.1 | `python-jose` → `PyJWT`; revisión completa de JWT (algoritmos, expiración, `jti`, blacklist de access y refresh; rate limit en `/refresh`; validar token en `KillSwitchRedis.reset`). | SPEC-G01 | S-03, S-05, S-06 | 6 |
| 8.2 | Correlation ID en todas las capas (API ↔ core ↔ worker): middleware que lo genera/propaga por request y lo mete en el contexto structlog. | SPEC-G02 (parte) | Observabilidad | 5 |
| 8.3 | Grafana con paneles reales: P&L, señales/hora, rechazos de riesgo, latencia del ciclo, estado del kill switch, drift/alpha-decay. Alertas por umbral (Telegram): kill switch activo, pérdida diaria cerca del límite, drift grave, worker sin latido, error rate de ejecución. | SPEC-G02 | Observabilidad | 8 |
| 8.4 | Gestión de secretos: quitar defaults inseguros de `docker-compose.yml`; documentar rotación; evaluar Vault / `docker secrets` para producción. | — | S-08, S-09, D-21 | 4 |
| 8.5 | Hardening de despliegue: no publicar 5432/6379 en prod; `nginx.conf` con TLS + headers de seguridad; escaneo de imagen (Trivy) + SBOM en CI. | — | S-08 | 6 |
| 8.6 | Auditar y estrechar los ~148 `except Exception` (política: loguear con contexto, nunca degradar seguridad en silencio); prioridad en `api/main.py`, `run_pipeline.py`, ejecutores. | — | D-17, S-07 | 8 |

**Hitos.** H8.1 — Un `correlation_id` de un request HTTP se sigue en los logs hasta la decisión del pipeline. H8.2 — Grafana muestra P&L y salud en vivo; alerta de prueba llega a Telegram. H8.3 — `pip-audit` + Trivy sin HIGH/CRITICAL.

**Auditoría de cierre F8.** Checklist: `grep -rn "python-jose" .` → 0; Trivy y `pip-audit` limpios; paneles con datos reales; alerta de prueba entregada. Pase fresco: auditoría de seguridad completa (OWASP-style) + observabilidad (¿un incidente simulado es reconstruible end-to-end?). No-regresión: F1 (suelo de seguridad) y F7 intactas. Veredicto GO si: 0 hallazgos de seguridad HIGH/CRITICAL; incidente simulado reconstruible.

---

## FASE 9 — Paper Trading extendido

**Objetivo.** Validar el sistema completo operando 24/7 contra testnet/demo ≥ 4 semanas.

**Entregables.**
| # | Entregable | Días activos |
|---|---|---|
| 9.1 | Worker 24/7 contra Binance testnet + MT5 demo (según F4); runbook de arranque/parada/recuperación. | 4 |
| 9.2 | Monitoreo diario: checklist de salud, revisión de trazas anómalas, verificación de métricas vs lo predicho en F2. | 8 (en 4 sem) |
| 9.3 | Ejercicio real del kill switch y de los circuit breakers en vivo (provocar los triggers). | 2 |
| 9.4 | `docs/PAPER_TRADING_REPORT_<fecha>.md`: P&L, nº señales, rechazos de riesgo y por qué, slippage realizado vs esperado, incidentes, drift observado, comparación con F2. | 3 |

**Hitos.** H9.1 — ≥28 días de uptime sin intervención no planificada. H9.2 — Kill switch disparado en vivo (provocado) y bloqueó trading. H9.3 — Métricas realizadas coherentes con F2.

**Auditoría de cierre F9 — GATE previo a capital real.** Checklist: uptime ≥28 días; reporte completo; incidentes con causa raíz y fix. Pase fresco: auditoría de operación. **Veredicto GO** si: métricas coherentes con F2, sin incidentes de seguridad ni pérdida no explicada, kill switch demostrado en vivo. **NO-GO** → volver a la fase responsable (F2 si el edge no se materializó; F6 ejecución; F8 observabilidad/seguridad).

---

## FASE 10 — Production Readiness (capital limitado supervisado)

**Objetivo.** Operar con capital real acotado, bajo supervisión, con infraestructura de producción. Score: Escalabilidad 3.5 → 6.5; resto ≥ 7.

**Entregables.**
| # | Entregable | Días |
|---|---|---|
| 10.1 | HA del worker: activo/pasivo con el lock Redis como failover; prueba de failover documentada. | 8 |
| 10.2 | Runbooks operativos: arranque, parada de emergencia, recuperación (DB/Redis/broker), rotación de secretos, despliegue, on-call. | 6 |
| 10.3 | Disaster Recovery probado: backup automatizado de Postgres/TimescaleDB, restore verificado en entorno limpio, RTO/RPO documentados. | 6 |
| 10.4 | Revisión legal/regulatoria previa a live (según jurisdicción): licencias, KYC del broker, reporting fiscal, límites. `docs/COMPLIANCE_REVIEW_<fecha>.md`. | externo (bloqueante) |
| 10.5 | Despliegue con capital limitado: hard cap de capital en `settings` independiente del sizing; `TRADING_ENABLED` con doble confirmación; `EXECUTION_MODE=live` solo tras checklist firmado. | 5 |
| 10.6 | Post-deploy review a 14 y 30 días: `docs/POST_DEPLOY_REVIEW_<fecha>.md` comparando realizado vs paper vs backtest; decisión de escalar o no el capital. | 4 |

**Hitos.** H10.1 — Failover del worker probado (sin doble ejecución ni hueco). H10.2 — Restore de DR verificado en entorno limpio. H10.3 — Compliance cerrado. H10.4 — Primera operación con capital real bajo el hard cap, supervisada.

**Auditoría de cierre F10 — Production Gate.** Checklist: failover y DR restore probados; compliance cerrado; hard cap verificado por test; checklist de go-live firmado; los 8 Acceptance Gates de la auditoría 2026-08 en verde. Pase fresco: auditoría integral completa (mismo alcance que `AUDITORIA_INTEGRAL_2026-08-28.md`) → score global ≥ 7.5/10, 0 hallazgos P0/P1. No-regresión: matriz completa contra todas las auditorías previas + F0–F9. **Veredicto GO** (autoriza operación continuada con capital limitado) si: score ≥ 7.5, 0 P0/P1, DR y failover probados, compliance cerrado, post-deploy a 30 días sin sorpresas.

---

## Resumen de esfuerzo

| Fase | Días-persona activos | Condicionada a |
|---|---|---|
| **BLOQUE A — hasta el GATE** | | |
| F0 — Gobernanza mínima | 4 | — |
| F1 — Habilitación mínima del core | 54 | F0 |
| F2 — Validación del core + GATE | 38 + 2 sem obs. | F1 |
| **Subtotal hasta GATE** | **~96 d + 2 sem** | — |
| **BLOQUE B — robustecer (solo si GATE=GO)** | | |
| F3 — Coherencia arquitectónica | 34 | GATE GO |
| F4 — Estrategias y multi-activo | 25 | F3 |
| F5 — IA/ML | 30 | F4 |
| F6 — Risk & Execution | 35 | F4 (solapa F5) |
| F7 — Testing avanzado | 34 | F5, F6 |
| F8 — Seguridad/DevSecOps/Observabilidad | 37 | F7 |
| F9 — Paper Trading extendido | 17 + 4 sem obs. | F8 |
| F10 — Production Readiness | 33 + compliance | GATE F9 GO |
| **Total (si GATE=GO)** | **~340 d + compliance + 6 sem obs.** | — |

En solitario a tiempo completo: **~4 meses hasta el GATE**; **~16–18 meses** hasta producción con capital limitado si el GATE da GO. Si el GATE da **NO-GO**, el plan se detiene tras ~96 días-persona y entra un ciclo de investigación/pivote de 4–8 semanas antes de re-planificar el Bloque B.

---

## Archivos y utilidades a reutilizar (no reimplementar)

- **Riesgo:** `core/risk/portfolio_risk_engine.py`, `core/risk/volatility_targeting.py`, `core/risk/auto_adaptation.py`, `core/risk/kill_switch_redis.py` (ya fail-safe) — **cablear**, no crear.
- **Adaptación:** `core/strategies/strategy_rotation.py`, `core/adaptation/regime_watcher.py`, `core/ml/alpha_decay_monitor.py`, `core/ml/drift_detector.py`.
- **Quant:** `core/ml/i1_gate_validator/*` (metodología correcta), `core/ml/stress_testing.py`, `core/backtesting/{costs,metrics}.py`.
- **Ejecución:** `core/execution/order_tracker_redis.py`, `core/execution/paper_executor.py` (idempotencia resuelta), `core/execution/live_*_executor.py` (esqueletos).
- **Observabilidad:** `core/observability/decision_tracer.py`, `core/compliance/audit_system.py` (`AuditLog`), `core/monitoring/prometheus_metrics.py`, `docker/grafana/provisioning/`.
- **Infra:** `core/bootstrap.py` + `*_factory.py` (Redis con fallback), `core/db/migrate.py` (Alembic).
- **Specs base:** `specs/SPEC-001..005` — extender ese patrón por entregable.

---

## Verificación end-to-end del plan

**Hasta el GATE (F0–F2):**
1. `docker compose up` levanta `api` (sin jobs) + `worker` (1 dueño) + `db` + `redis`; migraciones aplicadas; `/health` → `db_initialized: true`.
2. `grep -rn "default_v1" scripts core` → 1 punto; el pipeline solo opera activos con `data/models/i1_params/<symbol>.json` aprobado.
3. `pytest tests/unit tests/quant` → 0 failed; `pytest -m integration` (runner con Docker) → 0 failed/errors.
4. `GET /trace/{correlation_id}` reconstruye una decisión real end-to-end.
5. 2 corridas idénticas del pipeline → mismo output.
6. `data/reports/quant_report.md` + `docs/CORE_VALIDATION_DECISION` documentan si el core funciona y qué activos tienen edge.
7. `docs/CORE_PAPER_WINDOW` muestra ~2 semanas de paper sin decisiones sin explicar.
8. Auditoría de cierre F2 = **GO** (las tres condiciones).

**Tras el Bloque B (solo si GATE=GO):**
9. CI: unit + integration + e2e + walk-forward + chaos verdes; cobertura `core/` ≥ 75%.
10. `pip-audit` + Trivy sin HIGH/CRITICAL; `grep "python-jose"` → 0.
11. Grafana con P&L y salud en vivo; alerta de prueba entregada.
12. `docs/PAPER_TRADING_REPORT` ≥ 4 semanas coherente con backtest.
13. Failover del worker y restore de DR probados y documentados; compliance cerrado.
14. Auditoría integral final: score global ≥ 7.5/10, 0 P0/P1, matriz de no-regresión completa contra las 3 auditorías previas + F0–F9.
