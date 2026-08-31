# CORE VALIDATION DECISION — 2026-08-30

> Entregable 2.7 del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`.
> Veredicto de las **tres condiciones del ⛔ GATE F2**. Si NO-GO: el plan se
> detiene aquí y se ejecuta el mini-plan de pivote de abajo.

- **Fecha:** 2026-08-30
- **Base:** commit `cee5b63` + rama de trabajo F1/F2 (sin commitear al redactar)
- **Insumos:** `data/reports/i1_gate_report.json`, `data/reports/quant_report.{json,md}`
  (2.5), `data/reports/edge_robustness.{json,md}` (2.6),
  `data/reports/reproducibility_report.{json,md}` (2.2),
  `data/reports/data_quality_report.{json,md}` + `docs/audits/AUDIT_F2_4_LEAKAGE_2026-08-30.md` (2.4)

---

## Veredicto global

| | |
|---|---|
| **NO-GO (preliminar)** | ❌ La condición **(b) EDGE** no se cumple con el criterio literal del plan. Las condiciones (a) y (c) no están completas pero **no pueden revertir** el NO-GO por sí solas. |

**Preliminar** porque el plan exige además (i) la ventana de paper de ~2 semanas
(2.3) y (ii) un pase de auditoría cuantitativa independiente (Regla 3 y 4 del
prompt maestro). Ninguno de los dos puede convertir (b) en GO: 2.3 solo evalúa (c),
y la auditoría independiente valida — no relaja — los criterios. **El resultado
esperado del cierre formal de F2 es NO-GO.**

Por tanto: **se activa el mini-plan de pivote.** F3–F10 quedan re-planificadas
para después.

---

## Condición (a) — FUNCIONA

> Criterio: 2 corridas idénticas → mismo output; toda etapa produce output válido;
> `GET /trace` reconstruye cualquier ciclo.

| Sub-criterio | Estado | Evidencia |
|---|---|---|
| 2 corridas → mismo output (cadena de decisión cuantitativa) | ✅ | 2.2: `check_reproducibility.py` — 2 pasadas independientes, **digests SHA-256 idénticos** en los 8 símbolos (combined SHA `fae4239a…`). 0 usos de RNG de decisión sin semilla; `uuid4`/`datetime.now` solo en metadata. |
| 2 corridas → mismo output (**pipeline full-stack**: órdenes + snapshots vía Redis/DB/testnet) | ⏳ Pendiente | Requiere el stack corriendo — entregable 2.1/2.3. No ejecutable en esta sesión. |
| Toda etapa produce output válido | ⏳ Parcial | Verificado bajo mocks en F1 (`test_pipeline_cycle_produces_full_trace`, 8 etapas). Falta la corrida real contra testnet (2.1). |
| `GET /trace/{id}` reconstruye un ciclo | ✅ (mocks) | F1.6: `api/routes/trace.py` + `test_pipeline_trace.py`. Falta ejercerlo sobre ciclos reales (2.3). |

**Estado (a): parcialmente satisfecha.** El core de decisión es determinista y
trazable; falta la evidencia de la corrida real (2.1/2.3), que es trabajo de
calendario + infra, no de diseño.

---

## Condición (b) — EDGE  ❌

> Criterio: ≥1 activo con **Sharpe neto holdout ≥ 0.8**, **CI de Monte Carlo con
> límite inferior > 0**, edge que **sobrevive a costos ×2**, **no dependiente de un
> único régimen**.

### Panorama del universo (I1 gate — `i1_gate_report.json`)

| Symbol | Pasa gate | Mejor estrategia | Sharpe neto holdout |
|---|:--:|---|--:|
| **XAUUSD** | ✅ | Momentum | **+1.3232** |
| US30 | ❌ | mean_rev_v1 | +0.6396 |
| GBPUSD | ❌ | ema_rsi_v1 | −0.9514 |
| EURUSD | ❌ | BB_ZScore | −0.9767 |
| USDJPY | ❌ | vol_breakout_v1 | −1.4867 |
| ETHUSDT | ❌ | vol_breakout_v1 | −2.1019 |
| BTCUSDT | ❌ | vol_breakout_v1 | −2.1701 |
| US500 | ❌ | tsmom_v1 | −3.9607 |

**1 de 8 símbolos** tiene Sharpe neto holdout positivo. Esto confirma **F-02
(P0 — "el core no tiene edge demostrado")**: no es un problema de un activo, es el
universo entero salvo el oro.

### XAUUSD / Momentum (lookback 16) bajo la batería de robustez (2.6)

| Test | Resultado | Criterio (b) |
|---|---|:--:|
| Sharpe neto holdout (recalculado) | +1.3232 (= gate; cross-check exacto) | ✅ ≥ 0.8 |
| **Monte Carlo** block-bootstrap 1000 paths (holdout, 2741 barras) | **CI95 = [−1.4333, +3.7598]**, P(Sharpe>0) = 0.816 | ❌ **límite inferior < 0** |
| Monte Carlo full-sample (contexto, 13 707 barras) | CI95 = [+0.4535, +2.8507], P(Sharpe>0) = 0.993 | (no gating) |
| Barrido de costos ×1..×3 | Sharpe neto 1.3232 → 1.3181; sin anulación hasta ×3 | ⚠️ "pasa" pero **cost drag holdout = 0.0025** → el `CostModel` casi no penaliza XAUUSD; evidencia débil, no informativa |
| Descomposición por régimen | ADX+ buckets = **1/2** (edge concentrado en ADX alto); vol+ buckets = 2/2 | ❌ **mono-régimen** |
| Walk-forward anclado, re-opt trimestral | 4/4 folds positivos; OOS Sharpe neto = **+1.5935** | ✅ |

**Veredicto 2.6: FRAGILE.** El único activo con edge nominal **falla 2 de los 4
sub-criterios** de la condición (b):

1. **El CI de Monte Carlo del holdout cruza cero.** Con 2741 barras de holdout el
   Sharpe no es estadísticamente distinguible de cero al 95 %. En full-sample el
   CI sí es positivo (límite inferior +0.45), lo que sugiere que el problema es
   **longitud de datos**, no ausencia de señal — pero el criterio del plan es
   explícito sobre el holdout.
2. **El edge depende del régimen ADX** (solo rinde con tendencia fuerte). El plan
   pide que **no** dependa de un único régimen.
3. La "supervivencia a costos ×2" es un pase vacío: el modelo de costos apenas
   cobra spread sobre el oro (drag ≈ 0), así que multiplicar por 2 no prueba nada.
   Hay que revisar el `CostModel` para XAUUSD antes de darlo por robusto.

### Nota sobre alternativas en XAUUSD

`quant_report.md` (2.5) mostró que otras estrategias sobre XAUUSD tenían Sharpe
holdout aún mayor (tsmom_v1 ≈ 1.67, vol_breakout_v1 ≈ 1.68, MA_10_30 ≈ 2.49) con
WF también positivo. **No fueron sometidas a 2.6** (que corre solo la estrategia
aprobada). Es plausible que alguna sobreviva la batería completa — pero el
walk-forward anclado eligió `lookback 16` de forma consistente y el CI de Monte
Carlo seguiría limitado por el holdout corto. Es una vía a explorar en el pivote,
no una razón para cambiar el veredicto hoy.

**Estado (b): NO CUMPLIDA.**

---

## Condición (c) — SIN PÉRDIDA NO EXPLICADA

> Criterio: en ~2 semanas de paper, 0 operaciones/rechazos sin explicación en la
> traza; 0 comportamiento anómalo sin causa raíz.

**Estado (c): NO EVALUADA.** Requiere el worker 24/7 contra testnet durante ~2
semanas (2.3) + `docs/CORE_PAPER_WINDOW_<fecha>.md`. No ejecutable en esta sesión.
Aunque saliera limpia, no cambia el NO-GO de (b).

---

## Resumen de las tres condiciones

| Condición | Estado | ¿Puede revertir el NO-GO? |
|---|---|:--:|
| (a) FUNCIONA | Parcial (determinismo ✅, corrida real ⏳) | — |
| **(b) EDGE** | **❌ NO CUMPLIDA** (MC CI holdout cruza cero; mono-régimen) | Es la que bloquea |
| (c) SIN PÉRDIDA NO EXPLICADA | No evaluada (2.3 pendiente) | No — solo evalúa (c) |

**GO** exige las tres. **→ NO-GO.**

---

## Mini-plan de investigación / pivote (4–8 semanas)

Ordenado de más barato/probable a más caro. Cada rama tiene un criterio de
corte explícito.

### Rama 0 — Cerrar el papeleo del GATE (1 semana, en paralelo)

- Correr 2.1 + 2.3 (paper testnet, ventana corta de 3–5 días basta para (a)/(c)
  a efectos de esta decisión) y el pase de auditoría independiente.
- Objetivo: dejar (a) y (c) formalmente cerradas para que el NO-GO quede
  atribuido **solo** a (b) sin ambigüedad.

### Rama 1 — ¿Es longitud de datos, no ausencia de señal? (2 semanas) — **prioridad**

- **Extender el histórico 1h de XAUUSD** hacia atrás (objetivo ≥ 4–5 años) y
  descargar BTC/ETH (brecha conocida). Re-correr `scripts/audit_data_quality.py`.
- Re-correr 2.5 + 2.6 sobre XAUUSD con el holdout más largo y sobre las
  estrategias alternativas (tsmom_v1, vol_breakout_v1, MA_10_30).
- Revisar el `CostModel` de XAUUSD (spread/slippage realistas para oro spot).
- **Corte GO:** algún (activo, estrategia) con Sharpe neto holdout ≥ 0.8, **CI95
  de Monte Carlo con límite inferior > 0 sobre un holdout de ≥ 2 años**,
  superviviente a costos ×2 **con un modelo de costos que sí penalice**, y
  positivo en ≥ 2 regímenes ADX. → Si se cumple, **reabrir F2 solo para ese
  activo** y continuar el plan.

### Rama 2 — Otros timeframes / familias de estrategia (3–4 semanas)

- Barrer 4h y 1d (menos ruido, menos costo relativo) sobre el mismo universo con
  la misma metodología (I1 gate + 2.5 + 2.6).
- Familias no cubiertas hoy: carry/roll (FX, futuros), estacionalidad, cross-asset
  momentum, pairs/statistical arbitrage (EURUSD/GBPUSD, US30/US500).
- **Corte GO:** ≥ 1 (activo, TF, estrategia) que pase la batería completa de (b).

### Rama 3 — Replanteo del universo (2–3 semanas)

- El universo actual (`TRADED_UNIVERSE`, 8 símbolos macro muy eficientes) puede
  ser estructuralmente pobre en edge para estrategias técnicas 1h. Evaluar:
  cripto de mediana cap (más ineficiencia), futuros de materias primas con
  estructura de plazos, o un puñado de acciones con factores conocidos.
- **Corte GO:** idem Rama 2 sobre el universo nuevo.

### Rama 4 — Replanteo del producto (si Ramas 1–3 fallan)

- Si tras 6–8 semanas ninguna rama produce un edge que pase (b): el sistema no
  tiene una ventaja direccional demostrable con los datos/estrategias
  disponibles. Opciones: (a) pivotar a un producto de **ejecución/analytics**
  (el pipeline, la traza y el risk manager tienen valor aunque no haya alfa),
  (b) pausar y re-evaluar con un quant externo, (c) archivar.

### Qué NO hacer

- No avanzar a F3–F10 ("robustecer") sobre un core sin edge validado — es la
  regla explícita del plan.
- No "arreglar" el CI de Monte Carlo relajando el criterio. Si se cambia el
  umbral, que sea con justificación estadística escrita y en el pase de auditoría
  independiente, no aquí.
- No aprobar `ml_lgb_v1` para ningún símbolo hasta cerrar L-1..L-6 del
  `AUDIT_F2_4_LEAKAGE_2026-08-30.md`.

---

## Decisión

**NO-GO preliminar.** Ejecutar Rama 0 (cierre formal) + Rama 1 (datos largos +
estrategias alternativas de XAUUSD + revisión de costos) como primer movimiento.
Reconsiderar el veredicto cuando Rama 1 termine, con `edge_robustness.json`
regenerado sobre el holdout extendido.

---

## Actualización — Rama 1 ejecutada (subset sin infra) — 2026-08-30

Ver **`docs/CORE_VALIDATION_RAMA1_2026-08-30.md`**. Resumen:

- **CostModel de XAUUSD corregido** (bug ~100×). XAUUSD/Momentum **empeora**:
  holdout Sharpe 1.32 → **1.02**, < gate 0.8 a costos ×1.75, y el MC full-sample
  ahora **también** cruza cero. `i1_gate_report.json` quedó optimista.
- **BTC/ETH con holdout de 1.8 años (9 años de datos 1h)**: todas las familias
  técnicas con **Sharpe neto holdout negativo** (BTC best −0.39, ETH best −1.04).
  La hipótesis "es longitud de datos" queda **refutada** para cripto.
- **Estrategias alternativas de XAUUSD bajo 2.6** (holdout corto): ninguna pasa (b);
  `MA_10_30` parecía cerca (MC holdout −0.04).
- **XAUUSD extendido a 28.4 años vía terminal MT5 IC Markets** (67 694 barras H1,
  1998→2026; holdout 2.2 años): **cada métrica se degrada monótonamente al alargar
  la muestra** (2.4a → 4.8a → 28.4a). A 28 años `MA_10_30` MC full-sample
  **[−0.60, +0.54]** (P(Sharpe>0) = 0.45), anchored WF 29 folds **−0.18 → FAIL**;
  `Momentum` **falla los 4 criterios** (holdout 0.63 < gate, negativo a costos ×2,
  WF −0.72). El "edge" era enteramente la ventana alcista 2021-2026.

**⛔ El NO-GO de (b) es CONCLUYENTE en cuanto al edge:** las dos vías que podían
salvarlo (más datos de cripto — 9 años; más datos de oro — 28 años) están
**agotadas y ambas lo refutan**. Siguiente paso del plan de pivote: **Rama 2**
(4h/1d + familias nuevas; el terminal MT5 IC Markets ya sirve ~28 años de todo el
universo). Rama 0 y el pase independiente siguen pendientes pero no revierten (b).
