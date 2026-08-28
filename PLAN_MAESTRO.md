# TRADER AI — Plan Maestro Consolidado

> **Versión:** 1.1.0 (post-auditoría técnica) · **Fecha:** 2026-07-25
> **Sustituye a:** `PLAN_TRABAJO.md` (abril), `docs/PLAN_MAESTRO_EJECUCION_2026-05-16.md`, `docs/RESUMEN_EJECUTIVO_PLAN_2026-05-16.md`, `docs/INDICE_MAESTRO_2026-05-16.md`, `docs/CHECKLIST_SEMANA1_2026-05-16.md` — archivados en `docs/archive/` (ver [Anexo](#anexo--documentos-archivados))
> **Actualizado con evidencia de ejecución real** de [`docs/AUDITORIA_TECNICA_TRADING_CORE_2026-07-25.md`](docs/AUDITORIA_TECNICA_TRADING_CORE_2026-07-25.md) — la v1.0.0 de este plan solo tenía código leído (⚪ no verificado en casi todo); esta versión ya corrió tests, mypy, y el propio Gate I1, y leyó el código de riesgo/seguridad línea por línea.
> **EXECUTION_MODE:** paper (nunca cambiar a live sin autorización explícita)
> **🔴 Veredicto de la auditoría: NO avanzar a Fase 4.** El Gate I1 "APROBADO (8/8)" era metodológicamente inválido (ignoraba su propio holdout, negativo en 6/8 activos). **Actualización 2026-07-26:** se corrigió el criterio del gate para exigir también `sharpe_net_holdout >= 0.8` y se re-ejecutó contra los 8 activos reales — resultado real: **1/8 PASA (solo XAUUSD)**, gate **BLOCKED**. El kill switch fail-open ante caída de Redis también se corrigió (fail-closed ahora). Ver [Estado Actual Verificado](#estado-actual-verificado-2026-07-25-actualizado-post-auditoría) y `data/reports/i1_gate_report.md`.

---

## Nota de consolidación — léase primero

Este proyecto acumuló **tres planes sucesivos que se contradecían entre sí**:

1. `PLAN_TRABAJO.md` (5 abril 2026) declaraba FASE 2 y FASE 3 "completadas, production-ready".
2. `docs/PLAN_MAESTRO_EJECUCION_2026-05-16.md` (16 mayo 2026), basado en dos auditorías, decía que el sistema estaba **roto** (score técnico 5.3/10, JWT falsificable, DB nunca se inicializa, pipeline comentado) — sin mencionar que abril ya daba por completadas otras fases.
3. Ninguno de los dos se actualizó después del commit `1c9b127` (20 mayo 2026, "proyecto"), que implementó una cantidad sustancial de los módulos que el plan de mayo pedía (auth, compliance, RL agent, drift detector, arquitectura hexagonal, HMM, marketplace, risk engine 2.0...) sin que ningún documento lo reflejara.

Este documento reemplaza a los tres. Se construyó así:

- **Estructura y rigor metodológico** (fases 0-7, quality gates, investigaciones I1-I8, gates estadísticos): heredados del plan de mayo, que es el más disciplinado.
- **Arquitectura de modelos por clase de activo y sistema MTF SL/TP**: heredados del plan de abril, que sí describe correctamente ese diseño (y el código correspondiente existe).
- **Estado real de cada fase**: verificado el 2026-07-25 contra el filesystem del repo (no contra lo que cualquiera de los planes anteriores *afirmaba*). Ver la sección [Estado Actual Verificado](#estado-actual-verificado-2026-07-25).

**Importante:** "existe el archivo" no significa "está validado". Varias piezas están implementadas a nivel de código pero no hay evidencia (tests corriendo, resultados de I1, docs actualizados) de que estén verificadas end-to-end. Cada tabla de estado abajo distingue entre **presente en código** y **verificado funcionalmente**.

**Actualización 2026-07-25 (misma fecha, misma sesión):** se ejecutó una auditoría técnica con verificación real (no solo lectura de código) — se corrió la suite de tests, `mypy --strict`, y el propio Gate I1 contra datos reales, y se trazó el código de seguridad (kill switch, auth, API) línea por línea. Resultado completo en [`docs/AUDITORIA_TECNICA_TRADING_CORE_2026-07-25.md`](docs/AUDITORIA_TECNICA_TRADING_CORE_2026-07-25.md). Los hallazgos de esa auditoría reemplazan las celdas "⚪ no verificado" de la tabla de abajo allí donde ya hay evidencia, y son la fuente de los dos hallazgos críticos que bloquean avanzar de fase.

---

## ¿Qué es el sistema?

Plataforma de trading algorítmico multiactivo (forex, índices, commodities, cripto) que genera señales de compra/venta con un sistema multi-agente de IA, valida cada señal contra reglas de riesgo estrictas, y ejecuta órdenes en modo papel o (eventualmente, tras validación) en real. Opera en **modo papel por defecto**.

---

## Ecosistema del proyecto — configuración real

### Exchanges configurados

| Exchange | Tipo | Estado | Símbolos | Adaptador |
|----------|------|--------|----------|-----------|
| Binance | Crypto spot + futuros | Implementado | BTC, ETH, SOL, BNB (USDT) | `core/ingestion/binance_client.py` |
| Bybit | Crypto futuros/perps | Implementado | BTC, ETH, SOL, BNB perpetuos | `core/ingestion/bybit_client.py` |
| OANDA | Forex + índices + commodities | Implementado | 40+ pares | `core/ingestion/oanda_client.py` |
| MetaTrader 5 (IC Markets) | Forex + commodities + índices | Implementado | Majors/minors, oro, oil, índices | `core/ingestion/providers/mt5_client.py` |
| Interactive Brokers | Multiactivo | Parcial | Acciones, opciones, futuros, forex | `core/ingestion/providers/ib_client.py` |

### Activos por clase (28 configurados, 6 timeframes)

```
CRYPTO (Binance + Bybit):      BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT
FOREX (OANDA + MT5):           EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
INDICES (OANDA + MT5):         SPX500, NAS100, US30, DE40, UK100, JP225
COMMODITIES (OANDA + MT5):     XAUUSD, XAGUSD, USOIL, UKOIL, NATGAS, WHEAT
```

Nota: los datos históricos ya descargados en `data/raw/` cubren un subconjunto distinto (BTCUSDT, ETHUSDT, EURUSD, GBPUSD, USDJPY, XAUUSD, US30, US500) — hay que decidir si se amplía a los 28 activos del plan o se recorta el plan al universo real de datos disponibles (ver [Gaps](#gaps-confirmados-hoy)).

### Estrategias builtin

| Estrategia | ID | Régimen óptimo | Archivo |
|---|---|---|---|
| EMA Crossover + RSI | `ema_rsi_v1` | Trending | `core/strategies/builtin/ema_rsi.py` |
| Mean Reversion | `mean_rev_v1` | Rango/lateral | `core/strategies/builtin/mean_reversion.py` |
| TSMOM (momentum) | `tsmom_v1` | Trending persistente | `core/strategies/builtin/tsmom.py` |
| Volatility Breakout Adaptive | `vol_breakout_v1` | Post-consolidación | `core/strategies/builtin/volatility_breakout.py` |

---

## Principios no negociables

| # | Principio | Aplicación |
|---|-----------|-----------|
| P1 | Spec-Driven Development | Ningún código sin spec aprobada previa |
| P2 | Quant-First | Edge estadístico > features de UI |
| P3 | SOLID + Clean Architecture | SRP, OCP, LSP, ISP, DIP en cada módulo |
| P4 | Fail-Safe by Default | Kill switch con precedencia absoluta |
| P5 | Robustez sobre velocidad | Validar datos antes de modelos, siempre |
| P6 | Evidencia estadística | Sharpe OOS > 1.0 · Max DD < 20% antes de producción |
| P7 | Trazabilidad total | Desde dato de entrada hasta orden ejecutada |

---

## Estado Actual Verificado (2026-07-25, actualizado post-auditoría)

Esta tabla reemplaza al "semáforo" del plan de mayo y a los checklists contradictorios de abril — está basada en inspección directa del repo, no en lo que un documento anterior declaraba. Las filas marcadas **[EJECUTADO]** ya no son ⚪ — se corrieron de verdad en la auditoría del 2026-07-25 (ver anexo de comandos en el documento de auditoría).

| Componente | Código presente | Verificado funcionalmente | Nota |
|---|:---:|:---:|---|
| JWT sin `and False` | 🟢 | 🟢 **[EJECUTADO]** | Código leído completo (`settings.py`, `jwt_handler.py`): sin bypass, algoritmo whitelisted |
| DB `init_pool()` | 🟢 | 🟢 **[EJECUTADO]** confirmado en código, ⚠️ | Llamado en `api/main.py:172`, pero su fallo se tolera silenciosamente (arranca sin DB) |
| Pipeline `APScheduler` | 🟢 | 🟢 **[EJECUTADO]** confirmado en código | `add_job` activo en `scripts/run_pipeline.py:433-461` |
| Pipeline end-to-end (ciclo completo) | 🟢 (código) | ❌ **no ejecutado** | Bloqueado: sin `.env` real, requiere Postgres+Redis+Binance alcanzables — ninguno disponible en este entorno |
| Kill switch (memoria + Redis) | 🟢 | 🟢 **[CORREGIDO 2026-07-26]** fail-closed | `kill_switch_redis.py`: si Redis no responde, `is_active()`/`state` ahora reportan **activo** (bloquea trading) en vez de `False`. `activate()`/`reset()` propagan el error en vez de fallar en silencio. 6 tests nuevos en `tests/unit/test_kill_switch.py` simulan Redis caído. Ya no es el hallazgo crítico #1 — resuelto. |
| Auth (JWT handler, API keys, permissions) | 🟢 | 🟢 **[EJECUTADO]** RBAC correcto | `require_trader`/`require_admin` verificados en rutas sensibles; blacklist funcional en `jwt_handler.py` (se salta si Redis cae, severidad baja) |
| Repositorios DB (signals, orders, audit) | 🟢 | ⚪ no verificado | `core/db/repositories/` existe |
| Feature Engineering V2 (35+ features, ADX, Hurst) | 🟢 | ⚪ no verificado | `core/features/hurst_engine.py`, `feature_store.py` existen. ATR duplicado vs. `mtf_sl_tp_manager.py` (ver hallazgo de calidad) |
| Validación estadística (Purged K-Fold, walk-forward) | 🟢 | 🟢 confirmado no-stub | `class PurgedKFold`, `class WalkForwardValidator` en `core/ml/validation.py` — clases reales, usadas por Gate I1 |
| Backtesting con costos reales | 🟢 | 🟢 usado por I1 | `core/backtesting/costs.py` es un cost model real por clase de activo, consumido por `i1_gate_validator.py`. `scripts/ci_backtest_gate.py` es un smoke test de CI distinto, sobre datos sintéticos — no es el gate I1 |
| Modelos ML por activo (LightGBM/CatBoost/HMM/stacking) | 🟢 | ⚪ no verificado fuera de I1 | `core/models/asset_specific_models.py`, `core/agents/asset_specific_agent.py` |
| Modelos entrenados (.pkl) | 🟢 | 🟢 confirmados en `data/models/i1_ml/` | LightGBM real para BTCUSDT/ETHUSDT/US30/US500, usados por Gate I1 |
| Sistema MTF SL/TP + Fibonacci | 🟢 | ⚪ no verificado funcionalmente | `core/risk/mtf_sl_tp_manager/` — 🟢 **refactorizado 2026-07-27**: paquete de 5 submódulos (config/fibonacci/atr/manager/quality_filter), ya no es god file |
| HMM regime detector | 🟢 | ⚪ no verificado | `core/adaptation/hmm_regime_detector.py`, `pure_hmm.py` |
| Consensus engine dinámico | 🟢 | ⚪ no verificado, sin spec | `core/consensus/voting_engine.py`, `asset_specific_consensus.py` — cero menciones en `docs/` |
| Model Validation Gate | 🟢 | ⚪ no verificado | `core/ml/model_validation_gate.py` |
| Investigación I1 (edge estadístico) | 🟢 código real y completo | 🔴 **[RE-EJECUTADO 2026-07-26, x2] BLOCKED (1/8)** | Gate corregido para exigir `sharpe_net_holdout >= 0.8`. Primera corrida reveló un segundo bug: `ml_lgb_v1` no era walk-forward real (reusaba un modelo estático entrenado una sola vez sobre todo el 80% WF, así que sus ventanas de test eran in-sample) — afectaba BTCUSDT/ETHUSDT/US500. Se corrigió para reentrenar por ventana (`core/ml/i1_ml_signal.py`: `fit_model_in_memory`/`predict_signals_from_bundle`) y se re-corrió. Resultado final: **solo XAUUSD pasa** (Sharpe holdout 1.323); los 7 restantes fallan, casi todos con Sharpe holdout negativo pese a WF fuertemente positivo (BTCUSDT -2.17, ETHUSDT -2.10, EURUSD -0.98, GBPUSD -0.95, USDJPY -1.49, US500 -3.96, US30 +0.64 pero <0.8 umbral). Con el bug de leakage ya descartado como explicación, este patrón consistente (WF+/holdout−) en 7/8 activos y 6 estrategias distintas apunta a un cambio real de régimen entre el período WF y el holdout (I4/I5), no a un artefacto de código. Ver `data/reports/i1_gate_report.md`. |
| Drift detection / alpha decay / A-B testing | 🟢 | ⚪ no verificado | `core/ml/drift_detector.py`, `alpha_decay_monitor.py`, `ab_testing.py` |
| RL trading agent | 🟢 (código) | ❌ no debería usarse aún | `core/ml/rl_trading_agent.py` — prerequisito I1 sigue sin cumplirse de forma confiable tras el hallazgo de holdout negativo |
| Risk 2.0 (CVaR, correlaciones, vol targeting, perfiles) | 🟢 | ⚪ no verificado | `core/risk/portfolio_risk_engine.py`, `volatility_targeting.py`, `user_profile_engine.py`, `adaptive_position_risk.py` |
| Compliance / audit system | 🟢 | ⚪ no verificado | `core/compliance/audit_system.py` |
| Marketplace de estrategias | 🟢 | ⚪ no verificado | `core/marketplace/` |
| Arquitectura hexagonal (ports/adapters) | 🟢 | 🟢 **[EJECUTADO]** `mypy --strict` corrido | `domain/`+`application/` — **6 errores en 4 archivos** (no cero, pero localizados: tipos genéricos sin parametrizar y 2 params sin anotar). `domain/` confirmado sin imports de infraestructura. Lógica de negocio sí se filtra a `api/routes/execution.py:126-127` (cálculo de R:R en el route handler) |
| Frontend (7 páginas Streamlit + dashboard HTML/JS nativo) | 🟢 | ⚪ no verificado en navegador | **Decisión 2026-08-22:** el dashboard HTML/JS nativo (`static/dashboard.html`) es la aplicación web oficial; Streamlit (`app/`) se retira tras alcanzar paridad. Investigación reveló 3 implementaciones + 1 huérfano (`api/routes/dashboard.py`, 930L con 380L de código muerto confirmado) en vez de las 2 documentadas. **Dirección visual aprobada 2026-08-23** (paleta índigo/cian/púrpura, sidebar izquierdo, Geist+Inter+JetBrains Mono; prototipo clickeable en Claude Design) — ver Fase 1c del plan. Plan de migración completo en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) — diseñado, no ejecutado en código real todavía. Brecha de paridad crítica: la SPA nativa no tiene equivalente de 3 páginas Streamlit (`strategies`, `backtesting`, `simulator`) — bloquea retirar Streamlit hasta portarlas. |
| Componentes de frontend reutilizables (`app/components/`) | ❌ **descartado del alcance 2026-07-27** | — | Declarado como entregable en el plan de abril pero nunca se creó; confirmado (grep) que nada lo referencia — sin necesidad funcional identificada |
| `data/processed/` (features cacheados) | 🟢 **existe** | ⚪ no verificado el contenido | 34 archivos `*_1d_features.parquet` ya en disco; agregado a `.gitignore` (mismo patrón que `data/raw/`) el 2026-07-27 |
| Suite de tests | 🟢 (30 archivos, no 34) | 🟢 **[CORREGIDO 2026-07-26] 356 passed / 2 failed** | Partiendo de 329 passed/35 failed/1 error: se corrigieron 3 bugs reales de producción (`technical_agent.py` sin importar `pd`/`Path`; `validate_with_purged_kfold` dependía de `self._model` no inicializado; `has_permission` lanzaba `ValueError` sin capturar ante rol inválido), 2 tests con typos/diseño desactualizado (`test_portfolio.py`, `test_pipeline_paper.py` reusaba una instancia de `SignalEngine` con cooldown stateful), y el `ImportError` de colección de `test_api_execution.py` (ver fila WebSocket). Quedan 2 fallos documentados sin forzar: HMM de 8 estados con covarianza "full" sobreparametrizado para muestras pequeñas (`test_hmm_regime_detector.py`) — requiere decisión de arquitectura (¿covarianza "diag"?), no un fix de test. `test_api_execution.py` colecta (16 tests) pero no puede *ejecutarse* en este entorno: el lifespan real intenta conectar a Postgres sin timeout corto configurado en `asyncpg.create_pool` y cuelga indefinidamente sin DB disponible — mismo gap ambiental que el punto "pipeline end-to-end" de abajo. |
| WebSocket streaming al dashboard | 🟢 | 🟢 **[CORREGIDO 2026-07-26]** autenticado | `api/routes/websocket.py` exige un JWT válido (`?token=`) antes de `accept()`; conexión sin token o con token inválido se cierra con código 1008. 7 tests nuevos en `tests/unit/test_websocket_auth.py`. De paso se arregló un `ImportError` real que rompía el arranque de toda la API (`get_market_data_cache` había sido eliminado de `market.py` sin actualizar este import). Nota: no se encontró ningún cliente frontend que use este endpoint hoy. |
| IDOR en endpoints de órdenes | — | 🟢 **[CORREGIDO 2026-07-26]** | `Order` nunca tuvo tracking de dueño (ni en el modelo, ni en la tabla `orders`, ni en el `OrderTracker` en memoria) — cualquier usuario autenticado con rol trader podía ver/cancelar cualquier orden. Se agregó `user_id` a `Order`, migración `007_add_user_id_to_orders.py`, y helpers `_owns_order`/`_is_admin` en `execution.py`: `get_order`/`cancel_order` devuelven 404 (no 403, para no confirmar existencia) si la orden no es del usuario; `get_orders` filtra por dueño. Admin ve/cancela cualquier orden. 13 tests nuevos en `tests/unit/test_execution_idor.py`. |
| Interfaz de exchange (LSP) | 🟢 | 🟢 **[CORREGIDO 2026-07-27]** unificada en `ExchangeAdapter` | Los 5 clientes (Binance, Bybit, OANDA, IB, MT5) + Alpha Vantage migraron/convergieron a `ExchangeAdapter`; se borró `ExchangeClient` (`base_client.py`) y el `ExchangeAdapterRegistry` muerto. La investigación encontró el problema más profundo de lo documentado: `OandaClient` y `AlphaVantageClient` no se podían instanciar (`TypeError`, faltaban métodos abstractos), y `MT5Client` tampoco debería haber podido instanciarse (`is_connected()` nunca implementado) — los tres se corrigieron. `exchange_registry.py` ya no usa `hasattr()` en ningún lado (antes en 5 sitios) y su fábrica `_instantiate_client` para `mt5` pasaba kwargs que no existían en el constructor real (`account`/sin `password`) — corregido. `unified_pipeline.py` tenía el mismo patrón de duck-typing duplicado, también corregido. De paso se arreglaron 5 call sites ya rotos hoy por el desajuste de interfaz (`run_pipeline.py` x2, `validate_all_assets.py`, `run_backtest.py`, `seed_data.py` x2). 15 tests nuevos en `tests/unit/test_exchange_adapter_compliance.py`. |

🟢 presente en código / verificado OK · 🟡 parcial · 🔴 ausente o falla verificada · ⚪ no verificado en esta auditoría · ❓ desconocido

**Lectura honesta de esta tabla:** el código avanzó muchísimo más de lo que cualquiera de los tres planes documentaba, y ahora además hay evidencia de ejecución real (no solo lectura) en los puntos más críticos. **Actualización 2026-07-26:** los dos hallazgos críticos de la auditoría (kill switch fail-open, Gate I1 auto-aprobado) ya se corrigieron. El resultado sigue sin ser tranquilizador en el fondo: con el gate corregido, **el sistema no demuestra edge estadístico real** — solo 1 de 8 activos (XAUUSD) pasa. El riesgo pasó de "el gate miente" a "el gate dice la verdad y la verdad es que no hay edge todavía en 7/8 activos". Fase 4 sigue bloqueada, ahora con una razón válida. Detalle completo, hallazgos de seguridad y de calidad SOLID/arquitectura en [`docs/AUDITORIA_TECNICA_TRADING_CORE_2026-07-25.md`](docs/AUDITORIA_TECNICA_TRADING_CORE_2026-07-25.md).

---

## Diagnóstico heredado (de las auditorías de mayo — aún relevante como checklist)

### Los 4 blockers que motivaron el plan de mayo (verificados en la auditoría del 2026-07-25)

```
BLOCKER-1: init_pool nunca llamado           → RESUELTO y VERIFICADO (api/main.py:172, llamado en startup)
BLOCKER-2: APScheduler comentado             → RESUELTO y VERIFICADO (run_pipeline.py:433-461, add_job activo)
BLOCKER-3: POST /execution Signal/dict + explanation=None → no verificado directamente; sí se encontró un problema nuevo y más grave en el mismo archivo: IDOR en get_order/cancel_order (execution.py:211-250)
BLOCKER-4: JWT secret sin validación (and False) → RESUELTO y VERIFICADO (sin bypass, código leído completo)
```

### Deuda técnica — actualizada con evidencia de la auditoría del 2026-07-25

| # | Deuda | Estado | Esfuerzo estimado |
|---|-------|--------|--------------------|
| 1 | Token JWT sin módulo dedicado de blacklist (`core/auth/token_blacklist.py` no existe como archivo) | 🟢 **corregido 2026-07-27** — extraída a `core/auth/token_blacklist.py` (`TokenBlacklist`), `JWTHandler` delega en ella. Se mantiene fail-open ante caída de Redis (deliberado, documentado en la clase: fail-closed aquí tumbaría toda la autenticación por un blip de Redis, no solo el trading como con el kill switch). 6 tests nuevos en `tests/unit/test_token_blacklist.py` | — |
| 2 | Cobertura de tests en `api/routes/` | 🟢 **corregido 2026-07-26** — 356 passed/2 failed (desde 329/35/1); `test_api_execution.py` ya colecta. Quedan 2 fallos de HMM documentados (decisión de arquitectura, no bug de test) y la ejecución de `test_api_execution.py` bloqueada por falta de Postgres real en este entorno | — |
| 3 | `dashboard.py` God File (931 líneas en plan de mayo) | 🟢 **re-verificado y explicado 2026-08-22**: es `api/routes/dashboard.py` (930L), no `app/dashboard.py` (solo 316L, shell de Streamlit). 380 de esas 930 líneas son código muerto confirmado (segundo bloque HTML tras un `return` inalcanzable), y el archivo entero es huérfano (sin consumidores en el HTML vivo — `static/crypto-dashboard.html` ya cubre lo mismo, embebido vía iframe en la SPA). Ver plan de limpieza (Fase 0 y 4) en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md). Los 3 god files de la auditoría de julio (`mtf_sl_tp_manager.py`, `i1_gate_validator.py`, `asset_specific_models.py`) 🟢 **refactorizados 2026-07-27** — ver fila de arriba | Ver plan de migración — Fase 0 es de bajo esfuerzo (borrar código muerto) |
| 11 | **[nuevo, encontrado 2026-07-27]** `core/models.py` y `core/models/` coexisten; `AssetClass` está definida dos veces como clases distintas, coincidiendo solo por valor de string | 🟡 no rompe nada hoy (confirmado empíricamente), pero es frágil — ver detalle en "Próximos pasos" punto 7e | No estimado — requiere decidir el enfoque de consolidación antes de dimensionar |
| 4 | Rate limiting declarado pero sin confirmar aplicado en endpoints críticos | 🟢 **cerrado** — verificado: `slowapi` aplicado con `@limiter.limit()` en `execution.py` y `risk.py` | — |
| 5 | Resultado de I1 no documentado — bloquea decisión de avanzar a estrategias avanzadas (Fase 4+) | 🔴 **peor de lo esperado** — sí está documentado ("APPROVED 8/8") pero el criterio de aprobación es metodológicamente inválido (ignora holdout negativo en 6/8 activos) | 4-8h para corregir el gate + re-correr |
| 6 | **[nuevo]** Kill switch falla abierto si Redis no responde | 🟢 **corregido 2026-07-26** — fail-closed, tests de simulación de caída de Redis agregados | — |
| 7 | **[nuevo]** WebSocket sin autenticación (`api/routes/websocket.py:23-31`) | 🟢 **corregido 2026-07-26** — requiere JWT válido, 7 tests agregados | — |
| 8 | **[nuevo]** Interfaz de exchange con violación de LSP (`ExchangeClient` vs `ExchangeAdapter`) | 🟢 **corregido 2026-07-27** — unificado en `ExchangeAdapter`, ver tabla de estado y paso 7 de "Próximos pasos" | — |
| 9 | **[nuevo]** IDOR en `api/routes/execution.py:211-250` (get_order/cancel_order sin check de ownership) | 🟢 **corregido 2026-07-26** — user_id en Order + migración + 13 tests | — |
| 10 | **[nuevo]** ATR duplicado entre `core/features/indicators.py` y `core/risk/mtf_sl_tp_manager.py` | 🟢 **corregido 2026-07-27** — `core/features/indicators.py` expone `calculate_atr_series()` (Wilder vía pandas_ta, fallback EWM); `mtf_sl_tp_manager.py._calculate_atr` delega en ella en vez de reimplementar True Range con SMA. Nota: esto cambia ligeramente los valores de ATR usados en SL/TP (antes SMA, ahora EWM/Wilder) — es el efecto esperado de unificar, no un bug. 4 tests nuevos en `tests/unit/test_atr_deduplication.py` | — |

---

## Arquitectura de modelos por clase de activo

*(heredado del plan de abril — el diseño coincide con el código real en `core/models/asset_specific_models.py`)*

| Clase | Modelos (peso en stacking) | Features especializadas |
|---|---|---|
| **CRYPTO** (BTC, ETH) | LightGBM 35% + LSTM 30% + Temporal Fusion Transformer 25% + CatBoost 10% | Microstructure (order book imbalance, spread), ATR/RSI/Bollinger cripto-específicas, agregación 5m→15m→1h |
| **FOREX** (EUR/USD, GBP/USD, USD/JPY) | LightGBM 40% + HMM (regime switching) 25% + Logistic Regression 20% + SVM 15% | Session times (London/NY), correlación cross-pair (USD strength), régimen trending vs range |
| **INDICES** (US500, US30) | LightGBM 35% + XGBoost 30% + Random Forest 20% + reserva RL 15% | Sector rotation, momentum rate-of-change, Fibonacci pivots, MACD ponderado por volumen |
| **COMMODITIES** (Gold, Oil) | CatBoost 40% + HMM 30% + SVR 20% + Random Forest 10% | USD index, real rates, VIX, régimen macro, estacionalidad mensual |

Meta-modelo: `StackingClassifier` por clase de activo. Target: ternario (BUY +1 / HOLD 0 / SELL -1) con zona muerta calibrada por percentil de ATR — evita el ruido de `sign(retorno)` puro.

### Sistema MTF SL/TP dinámico (`core/risk/mtf_sl_tp_manager.py`)

- **ATR multi-timeframe** ponderado por clase de activo entre 15m/1h/4h/1d (pesos distintos para CRYPTO/FOREX/INDICES/COMMODITIES).
- **Niveles Fibonacci** (7 niveles, 0%–100%) ponderados junto al ATR según activo (ej. FOREX 60% Fib/40% ATR; CRYPTO 40% Fib/60% ATR).
- **5 regímenes de volatilidad** (LOW a EXTREME) con multiplicadores de SL/TP distintos.
- **`SignalQualityFilter`** con 4 validaciones: alineación temporal multi-TF, zona Fibonacci válida, extremos de volatilidad, ratio R:R mínimo (>1.5:1).

Este sistema es, junto con el consensus engine dinámico, la pieza de mayor valor diferencial del proyecto — y ya está implementado. Falta confirmar que está entrenado/calibrado con datos reales y que supera el gate I1.

---

## Fases del roadmap

Numeración y contenido heredados del plan de mayo (el más riguroso). Estado actualizado según la tabla de verificación de arriba.

### FASE 0 — Foundation & Governance
**Objetivo:** Estructura de repo, tooling, CI/CD, specs.
**Estado:** 🟢 mayormente presente — `pre-commit`, CI en `.github/workflows/`, `application/ports/` (arquitectura hexagonal) implementados. Verificar: `mypy --strict` pasa en `domain/`/`application/`, pre-commit hooks activos.

### FASE 1 — Secure Core Foundation
**Objetivo:** DB persistente, auth JWT real, pipeline autónomo, paper executor multi-exchange, Redis para estado distribuido.
**Estado:** 🟢 código presente para los 5 sub-módulos (DB, auth, scheduler, paper executor, Redis kill switch). **Criterio de aceptación pendiente de confirmar:** ejecución real de un ciclo de pipeline sin errores, señales persistidas en TimescaleDB.

### FASE 2 — Data & Quant Infrastructure
**Objetivo:** Features V2 sin look-ahead, Feature Store versionado, validación estadística rigurosa (Purged K-Fold + walk-forward), backtesting con costos reales, target ternario calibrado.
**Estado:** 🟢 clases presentes (`PurgedKFold`, `WalkForwardValidator`, `FeatureStore`, `hurst_engine.py`). **Gate crítico I1 pendiente de documentar resultado.**

### FASE 3 — Quantitative Intelligence
**Objetivo:** Modelos ML con validación temporal rigurosa, Model Validation Gate, HMM real (6-8 estados), consensus engine con pesos dinámicos.
**Estado:** 🟢 código presente (`model_validation_gate.py`, `hmm_regime_detector.py`, `voting_engine.py`). Investigaciones I2-I4 (feature importance, complejidad óptima, rendimiento por régimen) sin evidencia de resultados documentados.

### FASE 4 — Strategy Intelligence System
**Prerrequisito:** Fase 3 completada **y** I1 con Sharpe neto OOS > 0.8. **No avanzar si el edge no está demostrado.**
**Objetivo:** Portafolio de estrategias (TSMOM, cross-sectional momentum, stat arb, pairs trading), meta-agente selector, strategy rotation engine, portfolio optimizer, A/B testing de modelos.
**Estado:** 🔴 **BLOQUEADA — no iniciar.** Auditoría del 2026-07-25 corrió Gate I1 en vivo y confirmó que el "APPROVED (8/8)" documentado ignora el Sharpe holdout, negativo en 6/8 activos — no hay evidencia válida de que se cumpla QG-9. Las 4 estrategias builtin base existen; meta-agente/rotation/portfolio optimizer siguen sin implementar (`core/optimization/` solo tiene `__init__.py` vacío, confirmado hoy).

### FASE 5 — Advanced Risk Intelligence
**Objetivo:** Risk Engine 2.0 (CVaR, correlaciones, volatility targeting, perfiles de usuario, adaptación automática a condiciones de mercado).
**Estado:** 🟢 código presente casi en su totalidad: `portfolio_risk_engine.py`, `volatility_targeting.py`, `user_profile_engine.py`, `adaptive_position_risk.py`, `auto_adaptation.py`.

### FASE 6 — AI Adaptive Ecosystem
**Prerrequisito:** Fases 3-5 validadas con datos reales.
**Objetivo:** Online learning, drift detection, RL agent (shadow mode primero), stress testing, alpha decay monitor.
**Estado:** 🟢 código presente (`drift_detector.py`, `rl_trading_agent.py`, `stress_testing.py`, `alpha_decay_monitor.py`, `online_learning_agent.py`). ⚠️ El RL agent no debería activarse en modo real hasta que I1 y los gates de fases anteriores estén verificados — es fácil adelantarse aquí porque el código "ya existe".

### FASE 7 — Production Grade Platform
**Prerrequisito:** 60 días de paper trading con Sharpe > 1.0 verificado.
**Objetivo:** Staging, testnet, activación live gradual con capital mínimo, monitoreo en producción, playbook de emergencia.
**Estado:** 🔴 no hay evidencia de que se haya iniciado — es la fase final y depende de todos los gates anteriores.

---

## Quality Gates obligatorios (todas las fases)

| Gate | Criterio |
|---|---|
| QG-1 | Cobertura de tests ≥ 80% en módulos core (risk, execution, signals) |
| QG-2 | Zero errores mypy en `domain/` y `application/` |
| QG-3 | Ningún módulo `domain` importa infraestructura |
| QG-4 | Kill switch verificado funcional antes de cada fase |
| QG-5 | Backtests automáticos pasan en CI antes de merge a main |
| QG-6 | Todo cambio en parámetros de riesgo genera audit log |
| QG-7 | Ningún modelo a producción sin Sharpe OOS > 1.0 |
| QG-8 | Ningún deploy sin smoke test del pipeline completo en paper mode |
| QG-9 | Sharpe neto OOS > 0.8 antes de iniciar Fase 4 |
| QG-10 | 60 días de paper trading con Sharpe > 1.0 antes de live |

## Investigaciones críticas (I1–I8)

| ID | Pregunta | Criterio de éxito | Estado |
|---|---|---|---|
| **I1** ⚠️ bloqueante | ¿Existe edge estadístico real después de costos? | Sharpe neto OOS > 0.8, p-value < 0.05, **y** Sharpe holdout > 0.8 | 🔴 **corregido (2x) y re-evaluado (2026-07-26): BLOCKED, 1/8.** Solo XAUUSD (Momentum, Sharpe holdout 1.323) pasa los tres criterios. Se descartaron dos explicaciones de código (criterio del gate ignorando holdout; leakage en `ml_lgb_v1`) — el resultado final es consistente y apunta a un cambio de régimen real entre WF y holdout, no a un bug. **No hay edge demostrado fuera de XAUUSD; Fase 4 sigue bloqueada.** Próximo paso honesto: I4 (¿en qué régimen el sistema destruye valor?) e I5 (Hurst), no más ajustes de parámetros. |
| I2 | ¿Qué features aportan información predictiva real? | Eliminar features con importance ≤ ruido | ❓ no documentado |
| I3 | ¿LightGBM está sobreajustado? | Curva de complejidad óptima | ❓ no documentado |
| I4 | ¿En qué regímenes el sistema destruye valor? | Identificar regímenes a desactivar | ❓ no documentado |
| I5 | ¿Qué activos son trending vs mean-reverting? | Mapear activo → estrategia óptima (Hurst) | ❓ no documentado |
| I6 | ¿El stacking del AssetSpecificAgent aporta valor? | Adoptar si Sharpe ≥ +15% vs promedio ponderado | ❓ no documentado |
| I7 | ¿Features multi-timeframe mejoran la predicción? | Adoptar si mejora ≥ +10% Sharpe OOS | ❓ no documentado |
| I8 | ¿Online learning (River) es viable vs batch? | River ≥ 80% del Sharpe batch | ❓ no documentado |

> **I1 sigue siendo el gate más importante del proyecto.** Todo el código de Fases 4-7 (estrategias avanzadas, RL, live trading) ya existe en el repo, lo cual crea la tentación de avanzar sin haber confirmado que el sistema tiene edge real. No hacerlo — es exactamente el escenario que el plan de mayo advertía evitar.

---

## Gaps confirmados hoy

Actualizado tras la auditoría con ejecución real del 2026-07-25. Los que ya se resolvieron se marcan explícitamente; se agregan los hallazgos nuevos de seguridad/calidad que la auditoría encontró y que no estaban en la lista original.

1. ~~`pytest` no está instalado~~ → 🟢 **cerrado**: se instaló en `.venv` y se corrió la suite completa. Resultado real: **329 passed, 35 failed, 1 error, 1 archivo sin colectar** (`tests/integration/test_api_execution.py`, `PydanticUndefinedAnnotation: RegisterRequest`). El claim de "160 tests pasando" queda sin poder confirmarse tal cual, y la suite **no pasa limpia**.
2. **Resultado de I1: documentado, pero inválido.** El código sí corrió (`data/reports/i1_gate_report.json`, 2026-05-17) y se reprodujo en vivo hoy (XAUUSD, Sharpe 2.609/p=0.001, coincide exacto). El problema no es falta de datos — es que el criterio de aprobación ignora el Sharpe holdout, negativo en 6/8 activos. **Este es ahora el hallazgo bloqueante #1**, más grave que "falta ejecutar".
3. ~~`data/processed/`~~ → 🟢 **cerrado 2026-07-27**: el directorio ya existe en el filesystem con 34 archivos de features reales (`*_1d_features.parquet`), generados en algún punto fuera de esta auditoría — solo nunca se había trackeado su gitignore. Se agregó `data/processed/*.parquet` a `.gitignore` (mismo patrón que `data/raw/*.parquet`, son datos regenerables desde raw+código, no deben versionarse).
4. **`app/components/`** confirmado que sigue sin existir, y se verificó (grep) que nada en `app/dashboard.py` ni `app/pages/*.py` lo importa o espera — se descarta del alcance: no hay necesidad funcional identificada hoy, no queda como deuda abierta indefinida.
5. ~~`core/auth/token_blacklist.py` no existe como archivo separado~~ → 🟢 **cerrado 2026-07-27**: extraído a módulo propio (`TokenBlacklist`), `JWTHandler` delega en él.
6. **`core/optimization/`** sigue prácticamente vacío (solo `__init__.py`), confirmado hoy — bloquea meta-agente/portfolio optimizer de Fase 4.
7. Documentación desincronizada (`ESTADO_PROYECTO.md`, `TRADER_AI_PROMPT_MAESTRO.md`) — sin cambios, sigue pendiente.
8. Universo de activos: 8 símbolos reales en `data/raw/` vs. 28 declarados — confirmado sin cambios hoy.
9. **[nuevo]** Kill switch falla abierto ante caída de Redis (`kill_switch_redis.py:39-58`) — **hallazgo crítico #2**, no estaba en la lista de gaps original porque requería trazar el código de fallo, no solo confirmar que el archivo existe.
10. **[nuevo]** WebSocket de streaming sin autenticación (`api/routes/websocket.py:23-31`).
11. **[nuevo]** IDOR en `get_order`/`cancel_order` (`api/routes/execution.py:211-250`).
12. **[nuevo]** Violación de LSP entre `ExchangeClient` y `ExchangeAdapter` (dos interfaces de exchange incompatibles, compensadas con duck-typing).
13. **[nuevo]** 6 errores de `mypy --strict` en `domain/`+`application/` (localizados, no sistémicos — confirmado hoy que esas carpetas sí existen y son ejecutables contra mypy).
14. **[nuevo]** ATR duplicado entre `core/features/indicators.py` y `core/risk/mtf_sl_tp_manager.py`.

---

## Próximos pasos inmediatos (en orden, actualizado post-auditoría)

1. ~~Corregir el criterio de Gate I1 para que dependa del Sharpe holdout~~ → 🟢 **hecho 2026-07-26**: gate re-evaluado contra los 8 activos reales, resultado **BLOCKED (1/8)**, solo XAUUSD pasa. Sigue sin haber edge demostrado para avanzar a Fase 4.
2. ~~Arreglar el fail-open del kill switch~~ → 🟢 **hecho 2026-07-26**: `kill_switch_redis.py` ahora falla cerrado (bloquea trading) si Redis no responde; 6 tests nuevos simulando la caída lo verifican.
3. ~~Autenticar el WebSocket de streaming~~ → 🟢 **hecho 2026-07-26**: requiere JWT válido vía `?token=`, cierra con código 1008 si falta o es inválido. De paso se corrigió un `ImportError` que rompía el arranque de la API entera.
4. ~~Arreglar la suite de tests~~ → 🟢 **hecho 2026-07-26**: 356 passed/2 failed (desde 329/35/1 error). El `ImportError` que rompía el arranque completo de la API (`get_market_data_cache`, ver paso 3) y el `PydanticUndefinedAnnotation` que bloqueaba la colección de `test_api_execution.py` (causado por `from __future__ import annotations` + decorador `@limiter.limit` de slowapi perdiendo el `__globals__` correcto al resolver forward refs — mismo patrón en `auth.py` y `execution.py`, corregido quitando el future-import en ambos) están resueltos. Quedan 2 fallos de HMM documentados como decisión de arquitectura pendiente (no bug), y `test_api_execution.py` no puede *ejecutarse* aquí por falta de Postgres real (cuelga en el lifespan, gap ambiental ya conocido).
5. ~~Cerrar el IDOR de `execution.py`~~ → 🟢 **hecho 2026-07-26**: `Order`/tabla `orders`/`OrderTracker` no rastreaban dueño en absoluto (no era solo falta de un check, faltaba el dato). Se agregó `user_id` de punta a punta (modelo, migración, executor, rutas). `get_order`/`cancel_order` devuelven 404 si la orden no pertenece al usuario (admin bypassa); `get_orders` filtra. 13 tests nuevos.
6. **Confirmar que el pipeline corre un ciclo completo end-to-end** en paper mode con Postgres+Redis reales disponibles (no se pudo en este entorno de auditoría) y registrar evidencia (logs, filas en DB).
7. ~~Unificar la interfaz de exchange~~ → 🟢 **hecho 2026-07-27**: los 6 clientes convergen a `ExchangeAdapter`; `ExchangeClient` eliminado; `hasattr()` duck-typing eliminado de `exchange_registry.py` y `unified_pipeline.py`; 3 bugs de instanciación (Oanda, AlphaVantage, MT5) y 5 call sites rotos corregidos de paso.
7b. ~~Deduplicar ATR~~ → 🟢 **hecho 2026-07-27**: `core/features/indicators.py` expone `calculate_atr_series()`; `mtf_sl_tp_manager` delega en ella en vez de reimplementar True Range con una fórmula distinta (SMA vs. EWM/Wilder).
7c. ~~Refactorizar `mtf_sl_tp_manager.py` (810L, god file)~~ → 🟢 **hecho 2026-07-27**: convertido de archivo único a paquete `core/risk/mtf_sl_tp_manager/` con 5 submódulos por responsabilidad (`config.py` multiplicadores por activo, `fibonacci.py` niveles de swing, `atr.py` ATR multi-timeframe, `manager.py` orquestación, `quality_filter.py` gates de calidad de señal). El import path público `core.risk.mtf_sl_tp_manager` no cambió — `__init__.py` re-exporta todo, cero call sites tocados fuera del propio paquete.
7d. ~~Refactorizar `i1_gate_validator.py` (730L, god file)~~ → 🟢 **hecho 2026-07-27**: convertido de archivo único a paquete `core/ml/i1_gate_validator/` con 9 submódulos (`config.py` constantes/overrides, `params_io.py` persistencia JSON, `windows.py` tamaño de ventanas WF, `costs.py` P&L neto/bruto, `signal_filters.py` post-procesado de señales, `statistics.py` bootstrap p-value, `optimization.py` purged-CV/Optuna, `walk_forward.py` evaluación OOS, `report.py` dataclasses, `gate_validator.py` orquestación). Import path público `core.ml.i1_gate_validator` sin cambios; los 14 tests de `tests/quant/test_i1_gate.py` (incluido el end-to-end marcado `slow`) pasan sin modificarlos.
7e. ~~Refactorizar `asset_specific_models.py` (745L, god file — último de los 3 confirmados)~~ → 🟢 **hecho 2026-07-27**: convertido a paquete `core/models/asset_specific_models/` con 6 submódulos (`enums.py`, `features.py`, `specs.py`, `configs.py` con los 4 ensembles concretos + registry, `predictions.py` pydantic, `training_config.py` pydantic). Import path público sin cambios; `core/models/__init__.py`, `core/agents/asset_specific_agent.py` y `scripts/train_asset_specific_models.py` siguen funcionando sin tocarlos. **Los 3 god files identificados en la auditoría original están refactorizados.**

**[Hallazgo nuevo, no en la auditoría original, encontrado durante este refactor]** `core/models.py` (archivo) y `core/models/` (paquete) coexisten en el mismo directorio `core/`. Python resuelve `import core.models` al **paquete**, no al archivo — `core/models/__init__.py` ya lo sabía y compensa cargando `core/models.py` dinámicamente vía `importlib.util.spec_from_file_location` y re-exportando sus símbolos a mano. Efecto colateral: `core/models.py` define su **propia** clase `AssetClass` (usada internamente por `detect_asset_class()`), completamente distinta como objeto de la `AssetClass` que `core/models/asset_specific_models.py` expone y que `core/models/__init__.py` re-exporta como la pública. Hoy **no rompe nada** porque ambas son `str, Enum` con los mismos valores (`"crypto"`, `"forex"`, etc.), así que `==` y `hash()` coinciden por igualdad de string — confirmado empíricamente (`detect_asset_class("BTCUSDT") == AssetClass.CRYPTO` → `True`, aunque son clases distintas). Es deuda frágil: si algún día una definición añade un miembro que la otra no tiene, o se comparan con `is`/`isinstance` estricto, se rompe en silencio. No se corrigió en este pase — arreglarlo implica renombrar/consolidar `core/models.py`, que toca prácticamente todo el repo (todo lo que hace `from core.models import ...`), un cambio de mayor riesgo que los refactors anteriores. Pendiente de decisión explícita.
8. ~~Extraer `token_blacklist.py` a módulo propio~~ → 🟢 **hecho 2026-07-27**. ~~Decidir sobre `app/components/` y `data/processed/`~~ → 🟢 **hecho 2026-07-27**: `data/processed/` ya existía en disco (solo faltaba en `.gitignore`); `app/components/` se descarta del alcance (sin referencias en el código).
9. **Actualizar `ESTADO_PROYECTO.md`** para que apunte a este documento en vez de a `PLAN_TRABAJO.md`, o fusionarlo aquí en una siguiente revisión.
10. **Establecer el hábito de actualizar este único documento** al final de cada sesión de trabajo relevante, incluyendo tras cada auditoría — evitar que se repita el patrón de 3 planes desincronizados.
11. **Ejecutar el plan de migración del dashboard** ([`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md), diseñado 2026-08-22): ~~Fase 0 (limpieza segura, código muerto)~~ → 🟢 **hecho 2026-08-24**: `api/routes/dashboard.py` quedó en 549 líneas (eliminadas las 380 líneas inalcanzables tras un `return`, bloque HTML duplicado); `DEPLOYMENT.md:72` corregido (`streamlit run app/main.py` → `app/dashboard.py`); `static/crypto-dashboard.html` no se tocó (sigue vivo). Suite verde: 409 passed/2 skipped (los 22 fallos de `test_dashboard_e2e.py` y el error de `test_api_execution.py` son preexistentes, requieren servidor/Postgres real levantado, no relacionados con este cambio). → ~~Fase 1 (portar `strategies`/`backtesting`/`simulator` a la SPA nativa)~~ → 🟢 **hecho 2026-08-24**: 3 tabs nuevos en `static/dashboard.html` (Strategies/Backtesting/Simulator), verificados de punta a punta contra el backend real con un JWT generado a mano. De paso se encontraron y corrigieron 2 bugs de backend que bloqueaban por completo estas 3 páginas: (a) `core/auth/token_blacklist.py` cacheaba un cliente Redis roto tras el primer fallo de conexión, causando 500 en toda llamada autenticada *subsecuente* a la primera (bug de alcance amplio, afectaba cualquier endpoint protegido, no solo estos 3); (b) `api/routes/simulation.py` instanciaba `FeatureStore()` sin el `redis_url` requerido y llamaba a un método `async` sin `await`, por lo que el 100% de los jobs de simulación fallaban con un `TypeError` de firma antes de siquiera intentar conectar a Redis. Suite verde (409 passed, mismos 2/1 preexistentes). Detalle completo en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1.
   **Auth gap cerrado el mismo día**, priorizado por el usuario justo después de terminar el porting: `static/dashboard.html` nunca había tenido UI de login (tampoco Streamlit). Se agregó botón "Iniciar sesión"/modal en el nav → `POST /auth/login` real, tokens en `localStorage`, botón "Cerrar sesión" → `POST /auth/logout`. Verificado que `/auth/login` responde 401 limpio con credenciales inválidas incluso sin Postgres en este entorno (falla abierto, no 500); el flujo de éxito completo no se pudo probar de punta a punta por falta de una DB poblada aquí, pero el contrato de `TokenResponse` coincide exactamente con lo que el cliente espera. Pendiente de seguimiento (no bloqueante): refresh automático del access token al expirar (60 min).
   **Fase 1b prioridad alta cerrada el mismo día** (código fantasma de indicadores): los 11/15 indicadores del modal que no dibujaban nada (ATR/SMA/ROC/Stochastic/CCI/ADX/VWAP/Ichimoku/OBV/MFI/Williams %R) ahora se calculan client-side desde el OHLCV cargado y se dibujan (overlays sobre el candlestick para SMA/VWAP/Ichimoku, panel dinámico de osciladores para el resto). Bug adicional corregido de paso: los parámetros del modal (period, k/d, etc.) nunca se guardaban, así que cambiarlos no tenía efecto ni en los indicadores que ya funcionaban. Se borraron los 3 archivos JS confirmados muertos (`indicators-engine.js`, `lightweight-charts-manager.js`, `integration-examples.js`) y se actualizaron sus referencias en `static/README.md`. Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.
   **Fase 2 hecha (parcial) 2026-08-25** (adoptar WebSocket): corregido de paso un error de alcance en el plan original — solo existe `/ws/prices/{symbol}`, no hay WS de `signals` en el backend, así que esa parte no aplica (no es una regresión, nunca existió). Market View ahora abre WS por símbolo con el token de la Fase 1, actualiza el último candle en vivo, reconecta con backoff exponencial, y el `.live-dot` del topbar (antes decorativo) refleja el estado real de la conexión. Verificado el contrato del servidor de punta a punta con un cliente WebSocket de Python puro (conecta, autentica, transmite candles reales). **Limitación honesta**: no se pudo clic-verificar en un navegador real — Chromium headless vía Playwright en este entorno nunca resuelve conexiones `ws://` (confirmado que es el entorno, no el código, con una prueba mínima sin relación al dashboard). Recomendado verificar manualmente en un navegador real antes de dar la fase por 100% cerrada. Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 2.
   **Fase 4 cerrada 2026-08-25** (resolver `api/routes/dashboard.py` huérfano): comparado línea por línea contra `static/crypto-dashboard.html`, contenido funcionalmente idéntico, cero consumidores confirmados (ningún HTML/JS/test referenciaba `/dashboard/crypto`). Eliminado el archivo y su registro en `api/main.py`; `GET /dashboard` (la SPA real, definida directo en `main.py`) intacto. Bug relacionado corregido de paso: `static/crypto-dashboard.html` nunca enviaba el Bearer token a `/backtest/crypto/validation` (mostraba 403 siempre) — ahora lee `localStorage.trader_ia_token` (mismo origen que el login de la Fase 1) y muestra un mensaje claro si no hay sesión. Suite verde.
   **Fase 1c cerrada el mismo día** (dirección visual real, no solo prototipo): `static/css/styles.css` migrado a la paleta índigo/cian/púrpura + tipografía Geist/Inter aprobada; `static/dashboard.html` reestructurado de tabs horizontales a sidebar izquierdo fijo; Market View ahora tiene Agent Consensus Ring, Risk Shield Validation, Execution Pipeline Trace y Deployed Agents con Confidence DNA (datos reales, no mock — histórico de confianza acumulado en memoria durante la sesión). Verificado con Playwright (Chromium headless) contra el servidor real, no solo lectura de código — encontró y permitió corregir 3 bugs reales: la barra de herramientas de dibujo del chart quedaba flotando sobre el sidebar (posicionamiento `left:0` calibrado al layout viejo); un canvas de dibujo sin ancestro `position:relative` se anclaba al viewport y **bloqueaba los clics en todo el sidebar** (probablemente un bug preexistente nunca detectado porque nadie había hecho click-testing automatizado); la pestaña Crypto colapsaba a 300px de ancho por un caso límite de flexbox con el tamaño intrínseco por defecto de un `<iframe>`. Suite verde (409 passed) tras el cambio. Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1c.
   **Fase 3 cerrada 2026-08-25** (retirar Streamlit): confirmada paridad completa antes de tocar nada — las 7 páginas de Streamlit (`market_view`/`signals`/`risk_monitor`/`portfolio`/`strategies`/`backtesting`/`simulator`) tienen equivalente funcional en las 8 tabs de la SPA nativa. `app/` (dashboard.py, pages/, requirements.txt, .streamlit/, README.md) movido con `git mv` a `docs/archive/app_streamlit_legacy/` — decisión explícita del usuario de archivar en vez de borrar, mismo patrón que los planes archivados. `app/` queda vacío y se elimina. `streamlit` quitado de `requirements.txt` raíz — y de paso `plotly` también: el plan original asumía que se quedaba "porque la SPA lo sigue usando vía CDN", pero se verificó (`grep -rn "import plotly"`) que el paquete **Python** `plotly` solo lo importaban las páginas Streamlit ya archivadas; el `Plotly.js` que usa la SPA es una librería JS completamente distinta cargada desde CDN en `dashboard.html`, sin relación con el paquete pip. Sin este chequeo se habría dejado una dependencia Python muerta. Documentos con instrucciones activas de `streamlit run` corregidos para apuntar a la SPA nativa: `DEPLOYMENT.md`, `GUIA_OPERACION.md`, `INSTRUCCIONES_EJECUCION.md`, `SETUP_MANUAL.md`, `docs/technical-integration/docker-deployment.md`, `Skills/SKILL.md`, `scripts/run_training_pipeline.py`. `grep -rn "streamlit" --include="*.py" .` (fuera de `.venv` y del archivo) da limpio. Suite verde. Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 3.
   **Fase 1b prioridad media — Order entry UI cerrada 2026-08-26** (primer ítem operativo pedido pero ausente en ambos frontends, D.19 de la auditoría de brechas): botón "+ Nueva Orden" en el topbar abre un modal (`static/dashboard.html`) que prellena símbolo/precio de entrada desde el último candle cargado, permite elegir BUY/SELL, SL/TP con preview de R:R en vivo, y envía la orden real a `POST /execution` (no un mock) — pasa por el `RiskManager.validate_signal()` real y el `PaperExecutor` real (slippage/comisión simulados), mostrando la razón de rechazo o el fill real de vuelta al usuario. Bug encontrado y corregido: `--z-modal` (1000) empataba en z-index con `.drawing-canvas` (`drawing.css`, también 1000), y por orden de aparición en el DOM el canvas ganaba el empate e interceptaba los clics dentro del modal — mismo patrón de bug que el del sidebar en la Fase 1c, esta vez sobre el modal nuevo. Corregido subiendo `--z-modal`/`--z-tooltip` a 2000/2100 en `static/css/styles.css`. Verificado de punta a punta con Playwright contra un servidor real (JWT de prueba, sin Postgres): abre el modal, prellena correctamente, calcula R:R en vivo, alterna BUY/SELL, y al enviar recibe y muestra el rechazo real por kill switch (`"Kill switch active: redis_unavailable"` — comportamiento fail-closed esperado en este entorno sin Redis, no un bug). Suite verde: 409 passed/2 fallos HMM preexistentes/1 error Postgres preexistente, sin regresiones. Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.
   **Fase 1b prioridad media — Exportar CSV/JSON cerrada 2026-08-26**: botón "⬇ Exportar" en el topbar (`static/dashboard.html`), junto a "+ Nueva Orden", abre un menú que exporta `window.currentChartData` (el array OHLCV+features ya cargado, sin llamada nueva al backend) como CSV (58 columnas, escape correcto de comas/comillas/saltos de línea) o JSON (`JSON.stringify` con indentación), vía `Blob`+`URL.createObjectURL`, nombre de archivo `{symbolo}_{timeframe}_{fecha}.{ext}`. Complementa el "exportar PNG" ya existente de Plotly, que solo cubre el gráfico visual. Verificado de punta a punta con Playwright contra un servidor real: ambas descargas interceptadas, CSV parseado (519 líneas = 518 velas + cabecera), JSON parseado (518 registros), contenido coincide con los datos realmente cargados. Un 500 preexistente en `/market/EURUSD/features` (`ValueError: Out of range float values are not JSON compliant: nan`, bug de serialización del backend sin relación con este cambio) no afecta la exportación porque lee datos ya en el cliente. Suite verde (409 passed, mismos 2/1 preexistentes). Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.
   **Fase 1b prioridad media — Botón "ver razón de rechazo" en Signals cerrado 2026-08-26**: filas `rejected`/`cancelled`/`skipped` en la tabla de Signals (`static/dashboard.html`) muestran un botón ⓘ que abre un modal con el motivo del rechazo (`sig.reason`). **Hallazgo importante encontrado al implementarlo**: el store en memoria de `api/routes/signals.py` (`store_signal()`) nunca es llamado por ningún pipeline real (confirmado por grep) — `/signals` siempre devuelve vacío en este entorno, así que Signals en la SPA siempre ha corrido sobre `MOCK_SIGNALS`, que no tenía ninguna señal bloqueada (el contador "Bloqueadas" siempre marcaba 0). Se agregaron 2 señales mock con `reason` en el mismo formato de texto que ya usa `RiskManager.validate_signal()` (el motor real de razones, visible también en los rechazos de Order Entry) para que el drill-down sea demostrable; la UI queda lista para datos reales en cuanto exista un pipeline que llame `store_signal()`. Verificado con Playwright: "Bloqueadas"=2, botones ⓘ solo en filas bloqueadas, modal abre/cierra correctamente con la razón esperada. Suite verde (409 passed, mismos 2/1 preexistentes). Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.
   **Fase 1b prioridad media — VaR / Expected Shortfall cerrado 2026-08-26**: nueva sección en el tab Risk (`static/dashboard.html`) con 3 tarjetas (VaR 95% 1d, VaR 99% 1d, Expected Shortfall 95%) en % y $ sobre el capital actual. Cálculo client-side por simulación histórica (no paramétrico) sobre los retornos diarios de `GET /portfolio/history/public`, sin backend nuevo. Verificado con Playwright: relación VaR99% &gt; ES95% &gt; VaR95% correcta sobre datos reales/mock. Suite verde (409 passed, mismos 2/1 preexistentes). Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.
   **Fase 1b prioridad media — Panel SL/TP dinámico editable cerrado 2026-08-26**: a diferencia de los ítems anteriores de esta fase, este requirió **backend nuevo** — no existía forma de leer/escribir la configuración de `core/risk/mtf_sl_tp_manager`. Se agregó `GET/PUT/DELETE /risk/sltp-config` (`api/routes/risk.py`) respaldado por un registro de overrides en memoria en `core/risk/mtf_sl_tp_manager/config.py`, consultado por `get_sltp_config()` **antes** de la tabla de defaults — el override es real: lo usa `MTFSLTPManager.calculate_sl_tp()` sin ningún cambio adicional. El panel nuevo en el tab Risk (`static/dashboard.html`) tiene sliders para los 5 parámetros (multiplicadores ATR SL/TP, peso ATR↔Fibonacci, min R:R, max SL%), preview de R:R en vivo, Guardar/Restablecer. Detalle de diseño expuesto en la UI: el override aplica por (clase de activo, timeframe), no por símbolo individual — así estaba indexada la tabla original. Se agregó `tests/integration/test_api_sltp_config.py` (15 tests, todos verdes: defaults, mapeo símbolo→clase, auth, validación de rangos, integración directa con `get_sltp_config()`). **Bug real encontrado y corregido**: `loadSltpConfig()` borraba el mensaje de éxito/error de forma síncrona, y el propio flujo de Guardar lo llamaba justo después de mostrar su mensaje de éxito — se borraba antes de que el usuario lo viera; corregido moviendo el borrado a los listeners de cambio de contexto (símbolo/timeframe). Verificado con Playwright contra servidor real: guardar/restablecer funcionan de punta a punta. Suite verde: 424 passed (409 + 15 nuevos), mismos 2 fallos HMM preexistentes, 2 errores de teardown (el preexistente + uno nuevo de idéntica naturaleza — `TestClient` con scope de módulo cerrando el lifespan async sin Redis disponible, no una falla de aserción). Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.
   **Fase 1b prioridad alta — Página "Models" cerrada 2026-08-26**: nuevo tab "Models" (`static/dashboard.html`) con catálogo de los 5 agentes reales (`technical_v1`/`regime_v1`/`microstructure_v1`/`fundamental`/`asset_specific_v1`), tabla comparativa + gráfico de barras (Plotly) con el peso real de cada uno en los 3 esquemas de consenso (`AGENT_WEIGHTS_CRYPTO`/`AGENT_WEIGHTS_MT5` de `core/consensus/voting_engine.py`, `ASSET_SPECIFIC_WEIGHTS` de `core/consensus/asset_specific_consensus.py`), y un Model Card modal por agente. Backend nuevo: `GET /models` y `GET /models/{model_id}` (`api/routes/models.py`, público, registrado en `api/main.py`). **Decisión de honestidad investigada antes de escribir código**: se confirmó por grep que no existe ningún registro persistido de accuracy/F1/precision por modelo en todo el repo — el endpoint devuelve esos campos como `null` con `metrics_tracked: false` explícito, y la UI muestra "no disponible" en vez de inventar cifras. El panel de sliders ATR/Fibonacci ya estaba cubierto por el ítem 10 (SL/TP dinámico, tab Risk) — no se duplicó. Verificado con Playwright contra servidor real: tab renderiza 5 modelos, gráfico agrupado, modal abre/cierra por fila. Suite verde: 424 passed, mismos 2 fallos HMM y 2 errores de teardown preexistentes, sin regresiones (sin tests de integración nuevos — endpoint de solo lectura sobre datos estáticos). Detalle en [`docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md`](docs/PLAN_MIGRACION_DASHBOARD_2026-08-22.md) Fase 1b.

---

## Anexo — documentos archivados

Los siguientes documentos quedaron obsoletos por este consolidado y se movieron a `docs/archive/` para referencia histórica (no editar, no usar como fuente de verdad):

| Archivo original | Nueva ubicación | Motivo |
|---|---|---|
| `PLAN_TRABAJO.md` | `docs/archive/PLAN_TRABAJO_2026-04-05.md` | Numeración de fases duplicada/contradictoria, declaraba "completado" código nunca ejecutado |
| `docs/PLAN_MAESTRO_EJECUCION_2026-05-16.md` | `docs/archive/PLAN_MAESTRO_EJECUCION_2026-05-16.md` | Base estructural de este documento, pero su "estado actual" quedó obsoleto tras el commit de mayo |
| `docs/RESUMEN_EJECUTIVO_PLAN_2026-05-16.md` | `docs/archive/RESUMEN_EJECUTIVO_PLAN_2026-05-16.md` | Resumen del anterior, mismo motivo |
| `docs/INDICE_MAESTRO_2026-05-16.md` | `docs/archive/INDICE_MAESTRO_2026-05-16.md` | Índice de navegación de los documentos de mayo |
| `docs/CHECKLIST_SEMANA1_2026-05-16.md` | `docs/archive/CHECKLIST_SEMANA1_2026-05-16.md` | Checklist de una semana ya transcurrida (mayo) |
| `app/` (dashboard.py, pages/, requirements.txt, .streamlit/, README.md) | `docs/archive/app_streamlit_legacy/` | Streamlit retirado 2026-08-25 (Fase 3 de la migración del dashboard) tras confirmar paridad completa con la SPA nativa |

Documentos que **no** se archivaron (siguen vigentes como referencia):

- `docs/AUDITORIA_TECNICA_2026-05-16.md` y `docs/AUDITORIA_CUANTITATIVA_CORE_2026-05-16.md` — evidencia/hallazgos, no planes; siguen siendo útiles como contexto histórico de por qué se tomaron ciertas decisiones.
- `TRADER_AI_PROMPT_MAESTRO.md` — principios/spec maestro, no un plan de ejecución.
- `ESTADO_PROYECTO.md` — desactualizado (4 abril) pero no es estrictamente un plan; recomendado fusionarlo aquí en una próxima revisión en vez de mantenerlo por separado.
