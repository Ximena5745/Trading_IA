# ADR-003 — El core de decisión es "agentes + consenso"; las estrategias son parametrizaciones validadas por el gate I1

- **Estado:** Aceptado (2026-08-28)
- **Fase:** F0 · entregable 0.1 del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`
- **Contexto base:** `docs/AUDITORIA_INTEGRAL_2026-08-28.md` (F-03, G-3), `docs/SPEC_BACKLOG_2026-08-28.md` (SPEC-B06, SPEC-D01)
- **Supersede:** ninguna. **Relacionada:** ADR-004 (universo), ADR-006 (trace), ADR-007 (ruta a producción)

## Contexto

Hoy conviven tres artefactos llamados "estrategia" y ninguno alimenta la decisión real:

1. `core/strategies/builtin/*` (`AbcStrategy`: EmaRsi, MeanReversion, TSMOM, VolBreakout, CrossSectionalMomentum) — solo los consumen la API `/strategies`, el marketplace y el simulador.
2. `core/ml/i1_strategies.py` (`I1_STRATEGY_REGISTRY`, 8 claves: `MA_10_30`, `BB_ZScore`, `Momentum`, `ema_rsi_v1`, `mean_rev_v1`, `tsmom_v1`, `vol_breakout_v1`, `ml_lgb_v1` — la auditoría integral citó 7; el registro real incluye además `MA_10_30`) — solo los consume el gate I1.
3. El pipeline real (`scripts/run_pipeline.py`) — no usa ninguno de los dos: genera la señal con agentes + `ConsensusEngine` + `SignalEngine` y llama a `SignalEngine.generate(..., strategy_id="default_v1")` con el identificador **hardcodeado** (`scripts/run_pipeline.py:223`, `core/signals/signal_engine.py:87`).

Consecuencia: lo que el gate I1 valida no es lo que el pipeline ejecuta, y lo que el pipeline ejecuta no lo valida nadie. No se puede afirmar que el core "tiene edge" porque el objeto medido y el objeto operado son distintos.

## Decisión

1. **El productor de decisiones del sistema es el pipeline de agentes + consenso** (`agents/*` → `ConsensusEngine` → `SignalEngine` → `RiskManager` → executor). No se introduce un motor de "selección de estrategia" paralelo. `meta_agent.py`, `ab_testing.py`, `strategy_marketplace.py` quedan como superficie exploratoria fuera del path de decisión hasta que una fase posterior los cablee explícitamente.

2. **Una "estrategia" es una parametrización de señal para un activo, y solo es válida si el gate I1 la aprobó.** El catálogo único es `StrategyRegistry` (`core/strategies/strategy_registry.py`); `I1_STRATEGY_REGISTRY` se pliega dentro como una vista del gate sobre el mismo registry (mismas claves, mismos objetos). Cada estrategia expone `optimizable_params` y `evaluate(df) -> signal_series`.

3. **El gate I1 es el único que aprueba.** Por cada activo aprobado escribe `data/models/i1_params/<symbol>.json` con el contrato:

   ```json
   { "strategy_id": "<clave en StrategyRegistry>",
     "params": { "...": "..." },
     "sharpe_net_holdout": 1.32,
     "approved_at": "2026-08-28T00:00:00Z" }
   ```

   > **Estado actual (a migrar en F1.4):** los archivos existentes son `data/models/i1_params/<symbol>_<strategy>.json` y solo llevan `{symbol, strategy, params}`. F1.4 los reescribe al contrato de arriba (nombre `<symbol>.json`, campos `strategy_id` / `sharpe_net_holdout` / `approved_at`). Este ADR fija el contrato objetivo; no describe el formato heredado.

4. **El pipeline carga los params por activo desde ese archivo.** `SignalEngine.generate` / `run_pipeline._pipeline_cycle` leen `data/models/i1_params/<symbol>.json` y usan `strategy_id` + `params` de ahí.

5. **Fail-safe cuantitativo:** si para un símbolo no existe archivo aprobado, **ese símbolo no emite señales** y el ciclo loguea `no_approved_strategy` (`correlation_id` incluido). No hay fallback a `"default_v1"` ni a parámetros por defecto.

6. **`strategy_id="default_v1"` deja de ser un literal disperso.** Tras F1.4, `grep -rn "default_v1" scripts core` devuelve **un único punto documentado** (el default del parámetro en `SignalEngine`, marcado como "solo para tests / nunca en el path del pipeline").

## Consecuencias

**Positivas**
- Lo que se valida = lo que se opera. El GATE de la Fase 2 pasa a ser una afirmación verificable.
- Añadir un activo al trading requiere, por construcción, pasar el gate I1 primero.
- La ausencia de edge se vuelve fail-safe: sin `i1_params/<symbol>.json` no hay operativa en ese símbolo.
- Un solo catálogo de estrategias para API, simulador, marketplace, gate y pipeline.

**Negativas / coste**
- F1.4 (14 d) es el entregable más caro del Bloque A: unificar registros, reescribir el productor de `i1_params`, cablear la carga por activo y migrar los JSON heredados.
- Con el reporte I1 actual (`data/reports/i1_gate_report.json`: 1/8 aprobado, `gate_approved:false`), el pipeline operará **solo XAUUSD** hasta que otros activos pasen el gate. Es el comportamiento deseado, pero reduce la cobertura a corto plazo.
- El marketplace y el A/B testing pierden su rol de "seleccionar estrategia en vivo" hasta una fase futura.

**Neutras**
- Los builtin `AbcStrategy` siguen disponibles para exploración y para el simulador; su promoción a trading pasa por el gate.

## Alternativas consideradas

- **A. Documentar que "el pipeline de agentes es el sistema y el resto es exploratorio", sin conectar el gate I1.** Rechazada: deja el core sin ninguna validación cuantitativa; el GATE de la Fase 2 quedaría sin sustento.
- **B. Hacer del `StrategyRegistry` el productor de decisiones (rotación de estrategias en vivo) y relegar los agentes.** Rechazada: el pipeline de agentes es el único camino codificado end-to-end y verificado como no-stub; reescribirlo es fuera de alcance del Bloque A.
- **C. Mantener dos formatos de `i1_params` (heredado + nuevo) con lectura tolerante.** Rechazada: perpetúa la ambigüedad; el coste de migrar 6 archivos pequeños es trivial.
