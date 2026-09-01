# CORE VALIDATION — RAMA 2 (pivote) — 2026-08-31

> Continuación de `docs/CORE_VALIDATION_RAMA1_2026-08-30.md`.
> **Rama 2** del mini‑plan de pivote (`docs/CORE_VALIDATION_DECISION_2026-08-30.md`):
> barrer **4h y 1d** sobre el universo actual con la misma metodología (batería 2.6),
> aprovechando que el terminal MT5 IC Markets sirve 14–28 años de historia.

- **Fecha:** 2026-08-31
- **Base:** commit `cee5b63` + rama de trabajo F1/F2/pivote
- **Cambios de código:**
  - `scripts/fetch_mt5_history.py` — nuevo: tira H1/H4/D1 del universo desde MT5
    (IC Markets) → `data/raw/parquet/{tf}/<sym>_<tf>.parquet` enriquecido.
  - `scripts/run_edge_robustness.py` — nuevo `--timeframe {1h,4h,1d}` (rebinding de
    `periods_per_year` / `quarter_bars` / bloque MC por timeframe).
- **Datos** (MT5 IC Markets, resample local 1h→4h→1d):
  XAUUSD 28.4 a · XAGUSD 24 a · EURUSD/GBPUSD/USDJPY 14.5 a · US500/US30 14.1 a.
- **Reportes:** `data/reports/rama2/` (`_sweep_summary.txt` + un JSON/MD por run).

---

## Barrido — 84 combinaciones

7 símbolos × 6 familias (`MA_10_30`, `tsmom_v1`, `Momentum`, `vol_breakout_v1`,
`mean_rev_v1`, `BB_ZScore`) × {1d, 4h}. Batería 2.6 completa (MC block‑bootstrap,
barrido de costos ×1..×3, descomposición por régimen, walk‑forward anclado).

### Resultado

| | |
|---|---|
| FRAGILE | **83 / 84** |
| EDGE_ROBUST | **1 / 84** — `US500 / vol_breakout_v1 / 1d` |
| Patrón de fallo dominante | `monte_carlo_ci_lower_gt_0` (MC holdout cruza cero) + `not_single_regime`. El MC **full‑sample** cruza cero en **todos** los runs. |

1 de 84 ≈ 1.2 % — **por debajo** de los ~4 falsos positivos que cabría esperar por
azar (84 tests, ~5 % por test en el criterio MC‑holdout).

---

## El único candidato — `US500 / vol_breakout_v1 / 1d` — es un falso positivo

### Lo que "pasaba" (1000 paths, datos IC Markets 2012→2026)

- Holdout Sharpe neto 1.5364 · holdout 726 barras (nov‑2023 → ago‑2026) · turnover 51
- MC holdout CI95 = [+0.38, +2.65], P(Sharpe>0) = 0.994 → PASS
- Barrido de costos: plano (drag 0.024) → PASS
- Régimen: 2/2 ADX, 2/2 vol → PASS (pero `pnl_share` ADX‑alto = **0.935**)
- Anchored WF: 55 folds, 38 positivos, OOS +0.33 → PASS

### Por qué no es real

| Señal | Detalle |
|---|---|
| MC **full‑sample** CI95 = **[−0.07, +0.86]** | Sobre 14 años el Sharpe no se distingue de cero. |
| Holdout = ventana alcista pura | nov‑2023 → ago‑2026 es todo bull del S&P. |
| WF montaña rusa | OOS de −4.74 / −4.06 / −3.93 en 2019‑2022; positivo solo en los folds recientes. El +0.33 lo cargan 2022‑2026. |
| 94 % del P&L en ADX‑alto | El check `not_single_regime` no lo caza porque el bucket ADX‑bajo es +0.22 (no negativo). De facto dependiente de régimen. |
| Turnover 51 / 726 | ~1 operación cada 14 días, mayormente largo → casi "S&P largo con filtro de tendencia" durante un bull. Por eso el sweep de costos es plano. |
| Datos cortos | El CFD US500 de IC Markets empieza en **2012**. No hay muestra pre‑2012. |

### Prueba definitiva — S&P 500 real, 57 años

`^GSPC` diario vía Yahoo (14 287 barras, **1970 → 2026**; holdout 20 % = 2 857
barras ≈ **11 años**, 2015‑2026). Batería 2.6, 1000 paths
(`data/reports/rama2/spx57_*.{json,md}`):

| Estrategia | Holdout Sharpe | MC holdout CI95 | MC full‑sample CI95 | P(Sh>0) full | Anchored WF (224 folds) | Veredicto |
|---|--:|---|---|--:|--:|:--:|
| **vol_breakout_v1** | **−0.18** | [−0.68, +0.31] | [−0.40, +0.09] | **0.117** | +0.16 (127/224) | **FRAGILE** |
| MA_10_30 | 0.22 | [−0.31, +0.74] | [−0.31, +0.17] | 0.312 | +0.08 (111/224) FAIL | **FRAGILE** |
| tsmom_v1 | 0.41 | [−0.13, +0.91] | [−0.26, +0.23] | 0.439 | −0.04 (118/224) FAIL | **FRAGILE** |

Sobre la serie real de 57 años, `vol_breakout_v1` en el S&P es **negativo** en el
holdout de 11 años; P(Sharpe>0) full‑sample = **11.7 %**. El "EDGE_ROBUST" del
barrido era enteramente un artefacto de **datos cortos (post‑2012) + holdout que
cae íntegro en el bull 2023‑2026**.

---

## Veredicto de Rama 2

**⛔ Sin edge robusto en ninguna parte del universo actual, en ningún timeframe.**

> **Addendum (2026-08-31) — corrección M-1.** El barrido usó `net_returns`
> sobre-cobrando ~2× a los instrumentos MT5 (§M-1 del brief de auditoría).
> Corregido y re-verificado sobre el subconjunto más fuerte: sigue sin GO
> (XAUUSD/MA_10_30 28a: MC full-sample [−0.40,+0.73], `not_single_regime` FAIL;
> US500/tsmom S&P 57a: MC full-sample [−0.22,+0.27], WF −0.05). El sesgo de M-1
> era *hacia* FRAGILE, así que corregirlo solo puede reducir falsos negativos —
> y no aparece ninguno. Datos `data/raw/parquet/1h/` regenerados desde MT5 IC
> Markets (14-28 a) — sustituyen los stubs yfinance de 2.4 a.

Recuento acumulado del pivote (Ramas 1 + 2):

| Dimensión | Cobertura | Resultado |
|---|---|---|
| Timeframes | 1h, 4h, 1d | — |
| Familias de estrategia | 6 (trend, momentum, breakout, mean‑rev, BB) | — |
| Activos | 8 (BTC, ETH, EUR, GBP, JPY, US500, US30, XAU) + XAG | — |
| Historia | cripto 9 a · FX/índices 14 a · oro 28 a · S&P (proxy) 57 a | — |
| **Combos (activo × estrategia × TF) evaluados con la batería (b) completa** | **~95** | **0 con edge robusto** |

El patrón es **universal y consistente**: cualquier Sharpe holdout positivo se
explica por la ventana reciente; el MC full‑sample siempre cruza cero; el
walk‑forward largo siempre es ≈ 0 o negativo. **El universo de 8 instrumentos
macro muy líquidos no tiene un edge direccional demostrable para estrategias
técnicas a 1h/4h/1d.**

### Qué sigue

**Decisión del usuario (2026-08-31): auditoría cuantitativa independiente primero.**
Brief: **`docs/audits/AUDIT_F2_QUANT_INDEPENDENT_BRIEF.md`**. Incluye un hallazgo de
método ya confirmado (**M-1**: `net_returns` sobre-cobra ~2× a instrumentos MT5) que
**no revierte el NO-GO** pero el auditor debe verificar y ponderar. Si la auditoría
confirma el NO-GO, se decide entre:

Las Ramas 1 y 2 del plan de pivote están **agotadas sin GO**. Quedan:

- **Rama 3 — replanteo del universo.** El universo actual es estructuralmente
  pobre en ineficiencia. Candidatos: cripto de mediana cap, futuros de materias
  primas con estructura de plazos (carry/roll), cestas de acciones con factores
  conocidos (value/quality/low‑vol). Requiere fuentes de datos nuevas y, en
  cripto de mediana cap, un adaptador de exchange.
- **Rama 4 — replanteo del producto.** Si se acepta que no hay alfa direccional
  con los datos/estrategias disponibles: (a) pivotar a un producto de
  **ejecución / analytics / risk** (el pipeline, la traza y el risk manager
  tienen valor sin alfa), (b) pausar y traer un quant externo, (c) archivar.

**No se inicia ningún entregable de F3–F10.** Recomendación en la nota de cierre
del `PROGRESS.md`.
