# Auditoría Técnica del Trading Core — Trader AI

> **Fecha:** 2026-07-25 · **Alcance:** Data → Features → Modelos → Consensus → Riesgo → Ejecución
> **EXECUTION_MODE:** paper durante toda la auditoría (no modificado)
> **Metodología:** verificación directa contra filesystem/código/ejecución real, no contra lo que documentos previos afirman.

---

## 1. Resumen ejecutivo

**Estado real en una frase:** el trading core tiene una arquitectura y una cantidad de código notablemente más completa de lo esperado, incluido un Gate I1 que **corre de verdad y produce un resultado reproducible** — pero ese resultado ("APROBADO 8/8") es producto de un criterio de aprobación que **ignora su propia métrica holdout**, la cual es negativa en 6 de 8 activos. El sistema no tiene, hoy, evidencia creíble de edge estadístico neto de costos.

**Resultado de I1:** el código de I1 (`core/ml/i1_gate_validator.py`) es real, ejecutable y fue efectivamente corrido el 2026-05-17, generando `data/reports/i1_gate_report.json` con **Sharpe neto walk-forward 2.21–10.08 y p<0.05 en los 8 símbolos** → veredicto guardado "GATE FASE 5: APPROVED (8/8)". Reproducimos XAUUSD en vivo hoy y obtuvimos el mismo número exacto (Sharpe 2.609, p=0.0010), confirmando que el artefacto no es fabricado ni está obsoleto respecto al código actual. **Pero** el propio reporte también registra `sharpe_net_holdout` (tramo de validación nunca tocado durante la optimización walk-forward) y es **negativo en 6/8 activos** (BTCUSDT -0.65, ETHUSDT -2.90, EURUSD -0.33, GBPUSD -0.95, USDJPY -1.49, US500 -1.81; solo US30 +0.64 y XAUUSD +1.32 son positivos). El criterio de paso/fallo en el código (línea 553) solo evalúa `sharpe_net_wf`, nunca `sharpe_net_holdout` — es decir, **el gate se aprobó a sí mismo con una métrica que es consistente con sobreajuste al proceso de walk-forward, no con edge real**.

**Los 3 riesgos más críticos:**

1. **[CRÍTICO — seguridad]** El kill switch (`core/risk/kill_switch_redis.py:39-58`) **falla abierto**: si Redis no responde, `is_active()` devuelve `False` por defecto y el sistema sigue operando como si no hubiera ningún corte de riesgo activo. Es la falla de diseño más peligrosa encontrada — exactamente el escenario que P4 (Fail-Safe by Default) prohíbe.
2. **[CRÍTICO — quant]** El Gate I1 aprueba fases basándose en una métrica (Sharpe walk-forward) que ignora su propio holdout negativo en el 75% de los activos. Avanzar a Fase 4 con esta "aprobación" tal como está formulada sería avanzar sin evidencia real de edge.
3. **[ALTO — calidad/mantenibilidad]** Violación de LSP entre los 5 clientes de exchange: existen **dos jerarquías de interfaz incompatibles** (`ExchangeClient` con `get_historical_klines`/dict balance vs. `ExchangeAdapter` con `get_klines`/float balance), y el código de enrutamiento (`exchange_registry.py:224`) ya tiene que recurrir a `hasattr()` duck-typing para compensarlo — es deuda estructural que hace frágil cualquier cambio en la capa de ingesta.

---

## 2. Resultado del Gate I1 — evidencia cruda

| Símbolo | Sharpe neto WF (usado para pass/fail) | p-value | Sharpe neto holdout (calculado, **no usado para pass/fail**) | Veredicto guardado |
|---|---|---|---|---|
| BTCUSDT | alto (rango 2.21–10.08 agregado) | <0.05 | **-0.646** | PASS |
| ETHUSDT | idem | <0.05 | **-2.901** | PASS |
| EURUSD | idem | <0.05 | **-0.328** | PASS |
| GBPUSD | idem | <0.05 | **-0.951** | PASS |
| USDJPY | idem | <0.05 | **-1.487** | PASS |
| US500 | idem | <0.05 | **-1.810** | PASS |
| US30 | idem | <0.05 | +0.640 | PASS |
| XAUUSD | 2.609 (reproducido en vivo) | 0.0010 (reproducido en vivo) | +1.323 | PASS |

- Código: `core/ml/i1_gate_validator.py` (731 líneas) — walk-forward + purged 5-fold CV + holdout 20%, bootstrap p-value (1000 resamples), `CostModel` real por clase de activo. Condición de paso, línea 553: `passed = sharpe_net_wf >= GATE_SHARPE_NET and p_val < GATE_P_VALUE` — **el holdout no entra en la condición**.
- Artefactos existentes: `data/reports/i1_gate_report.json`, `i1_gate_matrix.csv`, `i1_gate_report.md`, `I1_PHASE5_GATE.md`, generados 2026-05-17T06:34:03Z.
- Reproducción en vivo hoy: `python scripts/run_i1_edge_research.py --symbols XAUUSD` → Sharpe 2.609 / p=0.0010, **coincide exactamente** con el artefacto guardado. Los 4 archivos de reporte fueron restaurados con `git checkout --` inmediatamente después de la prueba (verificado limpio con `git status --short`).
- `core/ml/edge_research.py` es una implementación paralela/anterior (`EdgeResearcher`), **no** la que está conectada al pipeline real — el entrypoint real es `scripts/run_i1_edge_research.py` → `i1_gate_validator.py`.
- `scripts/ci_backtest_gate.py` **no es el gate I1** — es un smoke test de CI sobre datos OHLCV sintéticos, no relacionado con validación de edge estadístico.

**Conclusión de esta sección:** I1 es ejecutable, reproducible, y el "PASS" está técnicamente calculado — pero el criterio de aprobación tiene un defecto metodológico que invalida su uso como evidencia de edge real hasta que se corrija (ver Hallazgo Crítico #2 abajo).

---

## 3. Tabla de estado verificado por módulo

| Módulo | Presente | Probado/Ejecutado | Resultado |
|---|:---:|:---:|---|
| Ingesta (`core/ingestion/*`) | 🟢 | ⚪ no verificado end-to-end | Dos jerarquías de interfaz incompatibles (ver §4 LSP) |
| Feature engineering (`core/features/*`) | 🟢 | ⚪ no verificado | ATR duplicado vs. `mtf_sl_tp_manager.py` (ver §4 duplicación) |
| Validación estadística (`core/ml/validation.py`) | 🟢 real | ⚪ no ejecutado en esta auditoría de forma aislada | `PurgedKFold`/`WalkForwardValidator` no son stubs |
| Gate I1 (`edge_research.py`, `i1_gate_validator.py`) | 🟢 real y completo | 🟢 **ejecutado hoy, reproducido exacto** | PASS con defecto metodológico (holdout ignorado) — ver §2 |
| Modelos por activo (`asset_specific_models.py`, `.pkl`) | 🟢 (LightGBM real para BTCUSDT/ETHUSDT/US30/US500 en `data/models/i1_ml/`) | ⚪ no verificado fuera del contexto de I1 | — |
| HMM (`hmm_regime_detector.py`, `pure_hmm.py`) | 🟢 | ⚪ no verificado | — |
| Consensus engine | 🟢 | ⚪ no verificado, sin spec documentada | — |
| Model Validation Gate | 🟢 | ⚪ no verificado | — |
| Riesgo (`mtf_sl_tp_manager.py`, `portfolio_risk_engine.py`, etc.) | 🟢 | ⚪ no verificado funcionalmente | God file en `mtf_sl_tp_manager.py` (810 líneas, 5+ responsabilidades) |
| Kill switch (`kill_switch_redis.py`) | 🟢 | 🟢 **código leído y trazado** | **Falla abierto ante caída de Redis** — crítico, ver §6 |
| Backtesting (`costs.py`, `ci_backtest_gate.py`) | 🟢 | ⚪ `ci_backtest_gate.py` no ejecutado en esta auditoría | Cost model real, usado por I1 |
| Ejecución (paper, `core/execution/*`) | 🟢 (live_bybit/oanda/binance_executor.py) | ⚪ no verificado end-to-end; manejo de excepciones no verificado línea por línea | — |
| Drift/adaptación online | 🟢 | ⚪ no verificado | — |
| RL agent | 🟢 (código) | ❌ correctamente no activado — prerrequisito I1 no cumplido de forma confiable | No debe activarse |
| Tests (suite completa) | 🟢 (30 archivos, no 34) | 🟢 **ejecutado hoy** | **329 passed, 35 failed, 1 error, 1 archivo no colecta** (ver §3.1) |
| mypy --strict en `domain/`+`application/` | 🟢 (carpetas existen) | 🟢 **ejecutado hoy** | **6 errores en 4 archivos** (no cero, pero acotado) |
| DB `init_pool()` | 🟢 | 🟢 confirmado en código | Llamado en `api/main.py:172`, pero falla **tolerada silenciosamente** (arranca sin DB) |
| Pipeline scheduler | 🟢 | 🟢 confirmado en código | `add_job` activo, no comentado |
| Pipeline end-to-end | 🟢 (código) | ❌ **no ejecutado** | Bloqueado por: sin `.env` real, requiere Postgres+Redis+Binance alcanzables, ninguno disponible en este entorno |
| `data/processed/` | 🔴 no existe | — | Gap confirmado, sigue abierto |
| `app/components/` | 🔴 no existe | — | Gap confirmado, sigue abierto |
| `core/optimization/` | 🟡 solo `__init__.py` vacío | — | Meta-agente/portfolio optimizer de Fase 4 no implementados |
| `core/auth/token_blacklist.py` | 🔴 no existe como archivo | — | Lógica de blacklist vive dentro de `jwt_handler.py`, sí existe funcionalmente (ver §6) |
| Universo de activos | — | 🟢 confirmado | 8 símbolos reales en `data/raw/` vs. 28 declarados — gap ya conocido, sigue abierto |

### 3.1 Detalle de la corrida de tests (2026-07-25)

Comando: `.venv/Scripts/python.exe -m pytest -q --ignore=tests/integration/test_api_execution.py`
Resultado: **329 passed, 35 failed, 1 skipped, 1 error** en 107s.
- `tests/integration/test_api_execution.py` no colecta: `pydantic.errors.PydanticUndefinedAnnotation: name 'RegisterRequest' is not defined`.
- Fallos concentrados en `test_dashboard_e2e.py` (probablemente requiere servidor vivo), `test_technical_agent_improved.py` (falla completo), y fallos parciales en `test_auth.py`, `test_hmm_regime_detector.py`, `test_kill_switch.py`.
- El claim histórico de "160 tests pasando" **no se puede confirmar ni refutar directamente** (la suite real tiene ~365 tests recolectables), pero en su estado actual **no pasa limpia**.

---

## 4. Auditoría de calidad técnica (Spec-Driven / SOLID / Clean Architecture)

| Principio | Veredicto | Evidencia puntual |
|---|---|---|
| P1 Spec-Driven | **No cumple** | Solo existe `docs/SPEC_TEMPLATE.md` (plantilla vacía). `docs/business-logic/risk-management.md` documenta módulos que ya no son los que están en producción (`risk_manager.py`/`position_sizer.py` en vez de `mtf_sl_tp_manager.py`/`portfolio_risk_engine.py`). Cero menciones de consensus engine en `docs/`. Sin ADRs (grep vacío). |
| SRP | **No cumple** | God files: `mtf_sl_tp_manager.py` (810 líneas: ATR + Fibonacci + heurísticas SL/TP + config + orquestación), `i1_gate_validator.py` (730 líneas: ventaneo WF + costos + filtros + estadística + Optuna + I/O), `asset_specific_models.py` (745 líneas: 4 enums + 6+ modelos + factories). |
| OCP | **No cumple** | `core/ingestion/exchange_registry.py:74-113` (`_instantiate_client`) es un if/elif por nombre de exchange — agregar un exchange exige editar este método. Coexiste con `exchange_adapter.py` que sí soporta registro abierto — dos mecanismos inconsistentes. |
| LSP | **No cumple** | Dos jerarquías incompatibles de cliente de exchange: `ExchangeClient` (`get_historical_klines`, balance como `dict`) vs. `ExchangeAdapter` (`get_klines`, balance como `float`). `BinanceClient.place_order/cancel_order` lanzan `NotImplementedError`. El registry recurre a `hasattr()` duck-typing (`exchange_registry.py:224`) para compensar la incompatibilidad. |
| ISP | **Cumple** | `application/ports/*.py` son interfaces cohesivas y acotadas (`IExchangePort` 9 métodos, `IModelPort` 7, etc.), sin métodos stub. |
| DIP / Hexagonal | **Cumple parcialmente** | `domain/` está limpio (sin imports de infraestructura). Pero lógica de negocio se filtra a la API: `api/routes/execution.py:126-127` calcula `risk_reward_ratio` directamente en el route handler en vez de delegarlo a la capa de dominio. |
| Type hints | **Cumple** | Archivos muestreados (`voting_engine.py`, `risk_manager.py`, `edge_research.py`, `asset_specific_agent.py`) tienen anotaciones completas. |
| Duplicación | **No cumple** | ATR implementado dos veces de forma independiente: `core/features/indicators.py:149-157` (vía `pandas_ta`) vs. `core/risk/mtf_sl_tp_manager.py:476-490` (reimplementación manual de True Range) — riesgo de inconsistencia numérica entre señal y sizing. |

---

## 5. Auditoría de seguridad

| # | Hallazgo | Ubicación | Severidad | Explotabilidad |
|---|---|---|---|---|
| 1 | Kill switch falla **abierto** si Redis no responde — `is_active()` devuelve `False` por defecto ante excepción | `core/risk/kill_switch_redis.py:39-58` | **Crítica** | Interna (requiere caída/partición de Redis, pero es un evento operacional realista, no un ataque) |
| 2 | WebSocket de streaming sin autenticación — `websocket.accept()` sin verificar token | `api/routes/websocket.py:23-31` | **Alta** | Externa |
| 3 | IDOR en endpoints de órdenes — `get_orders`/`get_order`/`cancel_order` no verifican pertenencia al usuario, solo requieren estar autenticado | `api/routes/execution.py:211-250` | **Media** | Externa (requiere solo un token válido de bajo privilegio; mitigado parcialmente por IDs `uuid4`) |
| 4 | `KillSwitchRedis.reset(admin_token)` no valida el token recibido — el parámetro se ignora salvo para logging | `core/risk/kill_switch_redis.py:140-148` | **Media** | Interna (hoy mitigado porque la ruta que lo llama ya exige `require_admin`, pero la función en sí no tiene defensa propia) |
| 5 | Blacklist de JWT se salta silenciosamente si Redis no está disponible durante `decode()` | `core/auth/jwt_handler.py:73-77` | **Baja** | Interna (ventana acotada por TTL de 60 min) |
| 6 | Dependencias sensibles sin verificación de CVE (no hay acceso a internet en este entorno) | `requirements.txt`: `python-jose==3.3.0`, `fastapi==0.110.0`, `slowapi==0.1.9`, etc. | **No determinada** | — pendiente de revisión manual/CVE scanner |
| 7 | Manejo de excepciones en `core/execution/live_*_executor.py` tiene varios `except Exception:` — no se verificó línea por línea si alguno oculta fallos silenciosamente | `core/execution/live_bybit_executor.py`, `live_oanda_executor.py`, `live_binance_executor.py` | No verificado | — |

**Verificado correcto, sin hallazgo:** JWT sin bypass (`and False` no presente, algoritmo whitelisted); rate limiting real y aplicado vía `slowapi` en rutas de ejecución/kill-switch; RBAC (`require_trader`/`require_admin`) correctamente aplicado; CORS con allowlist explícita (no `*`); sin credenciales hardcodeadas; `.env` correctamente gitignored y no trackeado.

---

## 6. Hallazgos críticos consolidados (orden de severidad)

1. **[Crítica]** Kill switch falla abierto ante caída de Redis (`kill_switch_redis.py:39-58`) — el control de riesgo más importante del sistema queda deshabilitado exactamente cuando la infraestructura falla.
2. **[Crítica]** El criterio de aprobación de Gate I1 (`i1_gate_validator.py:553`) ignora el Sharpe holdout, que es negativo en 6/8 activos — el "APPROVED (8/8)" documentado no es evidencia confiable de edge real.
3. **[Alta]** WebSocket de streaming sin autenticación (`api/routes/websocket.py:23-31`).
4. **[Alta]** Violación de LSP entre dos jerarquías de cliente de exchange incompatibles, compensada con duck-typing (`exchange_registry.py:224`) — deuda estructural en la capa de ingesta.
5. **[Alta]** Pipeline no se puede correr end-to-end en este entorno (falta `.env`, Postgres, Redis, conectividad real) — el criterio "smoke test del pipeline completo" (QG-8) no está verificado.
6. **[Media]** 35 tests fallando + 1 archivo de test que no colecta (`test_api_execution.py`) — la suite no pasa limpia hoy.
7. **[Media]** IDOR en endpoints de órdenes (`execution.py:211-250`).
8. **[Media]** God files sin spec (`mtf_sl_tp_manager.py`, `i1_gate_validator.py`, `asset_specific_models.py`) — mantenibilidad y auditabilidad futuras en riesgo.
9. **[Media]** ATR duplicado entre `indicators.py` y `mtf_sl_tp_manager.py` — riesgo de divergencia numérica entre señal y gestión de riesgo.
10. **[Baja]** `token_blacklist` funcional pero sin módulo dedicado; se salta silenciosamente si Redis cae.
11. **[Baja]** 6 errores de `mypy --strict` en `domain/`/`application/` (localizados, no sistémicos).

---

## 7. Deuda técnica confirmada

| Deuda | Estado | Esfuerzo estimado |
|---|---|---|
| Gate I1: incorporar `sharpe_net_holdout` al criterio de pass/fail y re-evaluar los 8 activos | Abierta, bloqueante | 4-8h + tiempo de cómputo |
| Kill switch: fail-safe real ante caída de Redis (bloquear trading, no permitirlo) | Abierta, crítica | 4h |
| Unificar interfaz de exchange (`ExchangeClient` vs `ExchangeAdapter`) | Abierta | 16-24h (toca 5 clientes + registry) |
| Autenticar WebSocket de streaming | Abierta | 2-4h |
| Corregir 35 tests fallando + `test_api_execution.py` (fix `RegisterRequest` forward-ref) | Abierta | 8-16h |
| IDOR en endpoints de órdenes: verificar ownership antes de get/cancel | Abierta | 4h |
| `data/processed/`, `app/components/`, `core/optimization/` | Abiertas desde abril, nunca generadas | variable, depende de si se retoman |
| `mypy --strict`: 6 errores localizados | Abierta, menor | 2h |
| Documentar specs/ADRs de consensus engine, MTF SL/TP, risk engine | Abierta | 16h+ |
| Deduplicar ATR (`indicators.py` vs `mtf_sl_tp_manager.py`) | Abierta | 4h |
| Refactorizar god files (`mtf_sl_tp_manager.py`, `i1_gate_validator.py`, `asset_specific_models.py`) | Abierta | 24h+ |

---

## 8. Plan de acción priorizado

1. **Corregir el criterio de Gate I1 para incluir el holdout** y re-correr los 8 activos. *Hecho cuando:* `data/reports/i1_gate_report.json` refleje un `passed` que dependa de `sharpe_net_holdout >= umbral`, y el resultado se documente explícitamente (aprobado o no) por activo.
2. **Arreglar el fail-open del kill switch.** *Hecho cuando:* una prueba que simule Redis caído (mock/desconexión) resulte en `is_active() == True` (bloqueo) en vez de `False`.
3. **Autenticar el WebSocket.** *Hecho cuando:* una conexión sin token válido reciba un cierre/rechazo explícito (test automatizado que lo confirme).
4. **Arreglar la suite de tests** (35 fallos + 1 error de colección). *Hecho cuando:* `pytest -q` completo (sin `--ignore`) reporte 0 fallidos/errores, o cada fallo remanente esté documentado con causa raíz.
5. **Cerrar IDOR en `execution.py`.** *Hecho cuando:* `get_order`/`cancel_order` devuelvan 403/404 si el `order_id` no pertenece al usuario autenticado, verificado con un test.
6. **Ejecutar un ciclo end-to-end del pipeline en un entorno con Postgres+Redis reales (no live exchange).** *Hecho cuando:* exista al menos una fila de señal persistida en la DB con log completo del ciclo.
7. **Unificar la interfaz de exchange** (elegir `ExchangeClient` o `ExchangeAdapter`, migrar los 5 clientes). *Hecho cuando:* `exchange_registry.py` ya no necesite `hasattr()` duck-typing.
8. Cerrar gaps baratos: `core/auth/token_blacklist.py` como módulo dedicado (o documentar que vive en `jwt_handler.py` y cerrar el gap de documentación), decidir sobre `data/processed/`, `app/components/`, `core/optimization/`.
9. Escribir specs/ADRs mínimas para consensus engine, MTF SL/TP manager y risk engine.
10. Deduplicar ATR y refactorizar los god files identificados.

---

## 9. Anexo de comandos ejecutados

```
# Gate I1
python scripts/run_i1_edge_research.py --symbols XAUUSD
git status --short   # (post-restauración de reportes)
git checkout -- data/reports/i1_gate_report.json data/reports/i1_gate_matrix.csv data/reports/i1_gate_report.md data/reports/I1_PHASE5_GATE.md

# Tests
.venv/Scripts/python.exe -m pip install pytest pytest-asyncio hypothesis mypy==1.9.0 "pydantic[email]"
.venv/Scripts/python.exe -m pytest -q --ignore=tests/integration/test_api_execution.py

# mypy
.venv/Scripts/python.exe -m mypy --strict domain/ application/

# Grep de seguridad (patrones de secretos)
grep -rE '(api_key|secret|password|token)\s*=\s*["\']' --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv .
git ls-files | grep -i '\.env'

# Inspección manual (Read) de:
core/ml/i1_gate_validator.py, core/ml/edge_research.py, core/ml/validation.py
core/risk/kill_switch_redis.py, core/risk/mtf_sl_tp_manager.py
core/ingestion/exchange_registry.py, exchange_adapter.py, base_client.py, binance_client.py
api/routes/execution.py, api/routes/websocket.py, api/routes/risk.py, api/dependencies.py
core/auth/jwt_handler.py, core/config/settings.py, core/auth/permissions.py
api/main.py (líneas ~172, ~341)
scripts/run_pipeline.py (líneas ~433-461)
core/features/indicators.py, core/models/asset_specific_models.py
```

---

## 10. Pregunta de cierre obligatoria

**¿Es seguro y justificado avanzar a Fase 4 (QG-9: Sharpe neto OOS > 0.8) con la evidencia recolectada hoy?**

**No.**

El artefacto de I1 documenta formalmente "APPROVED (8/8)" y ese número es real y reproducible — pero está calculado con un criterio que **no evalúa la métrica que importa** (el Sharpe en el tramo holdout, genuinamente no visto durante la optimización), y esa métrica es **negativa en 6 de los 8 activos**. Un Sharpe walk-forward alto combinado con un holdout negativo es la firma clásica de sobreajuste al proceso de optimización, no de edge real. Avanzar a Fase 4 sobre esta base sería exactamente el escenario que el propio proyecto identificó como riesgo principal: dejarse llevar por código que "ya existe" sin haber confirmado que el sistema tiene edge real. La acción previa obligatoria es la del punto 1 del plan de acción: corregir el criterio de gate para que dependa del holdout, y volver a evaluar los 8 activos con ese criterio corregido antes de tomar cualquier decisión sobre Fase 4.
