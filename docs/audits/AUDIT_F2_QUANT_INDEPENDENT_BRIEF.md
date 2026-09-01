# BRIEF — Auditoría cuantitativa independiente del GATE F2 (condición b)

> **Para ejecutar en una sesión nueva de Claude Code / Cursor / Codex, SIN contexto
> de la implementación del pivote**, cargando `TRADER_AI_PROMPT_MAESTRO.md`
> (SECCIÓN 1 + SECCIÓN 2) y acotada a este alcance. Corresponde a la **Parte 2 del
> procedimiento de auditoría de cierre** (`PLAN_ELEVACION_MADUREZ_2026-08-28.md`
> §"Auditoría de cierre — procedimiento estándar") para la FASE 2.
>
> **Fecha de emisión:** 2026-08-31 · **Emitido tras:** Ramas 1 y 2 del pivote
> (`docs/CORE_VALIDATION_RAMA1_2026-08-30.md`, `docs/CORE_VALIDATION_RAMA2_2026-08-31.md`).

---

## 1. Pregunta de la auditoría

**¿La conclusión "el universo actual no tiene edge robusto a 1h/4h/1d" está
justificada, o es un artefacto de la metodología de la batería 2.6?**

Dos sub-preguntas, ambas obligatorias:

- **(A) ¿La batería de robustez (`scripts/run_edge_robustness.py`) es correcta y
  NO está sesgada a rechazar edges reales?** (falsos negativos)
- **(B) ¿Algún paso de la cadena señal→P&L→métrica introduce look-ahead o un bug
  que *infla* un edge aparente, o *lo suprime*?** (ambas direcciones)

El veredicto del pivote es NO-GO. Una auditoría honesta debe intentar **tumbarlo**
(encontrar un edge que la batería descartó indebidamente) y, si no lo consigue,
**confirmarlo**.

---

## 2. Alcance — archivos a auditar (y NADA más)

| Archivo | Qué verificar |
|---|---|
| `scripts/run_edge_robustness.py` | Los 4 sub-tests de 2.6: MC block-bootstrap, barrido de costos, descomposición por régimen, walk-forward anclado. Criterios de PASS. |
| `core/ml/i1_gate_validator/costs.py` | `half_side_cost_pct`, `net_returns`, `gross_returns`, `signal_turnover`. |
| `core/backtesting/costs.py` | `CostModel` (rama MT5 y cripto). |
| `core/backtesting/metrics.py` | `sharpe_ratio`, `sortino_ratio`, `max_drawdown`, `calmar_ratio`. |
| `core/ml/i1_gate_validator/signal_filters.py` | `prepare_signals`, `apply_regime_filter`, `apply_min_holding`, `apply_cooldown`. |
| `core/ml/i1_strategies.py` | `signal_*` de las 6 familias; `_ensure_indicators`; `iter_param_combinations`. |
| `core/features/indicators.py` | Solo el **set estándar** (`_calc_rsi`..`_calc_temporal_features`); causalidad (sin look-ahead). |
| `core/models.py` | `INSTRUMENT_CONFIGS` (spread_pips, pip_value, lot_size) para el universo. |
| `core/ml/i1_gate_validator/config.py` | `GATE_SHARPE_NET`, `HOLDOUT_FRACTION`, `PERIODS_PER_YEAR_1H`, `I1_ASSET_OVERRIDES` (cooldown/min_hold/min_adx). |

**Fuera de alcance:** API, DB, seguridad, arquitectura, todo lo no cuantitativo.

---

## 3. Reproducción

Datos ya en el repo (`data/raw/parquet/{1h,4h,1d}/`), de MT5 IC Markets + Yahoo:
XAUUSD 28 a, XAGUSD 24 a, FX/índices 14 a, S&P (`spx_long_1d.parquet`) 57 a,
BTC/ETH 9 a.

```bash
export PYTHONPATH=$PWD

# un run de la batería (activo × estrategia × timeframe):
python scripts/run_edge_robustness.py --timeframe 1d --symbols US500 \
  --strategy vol_breakout_v1 --paths 1000 --out data/reports/audit --out-name X

# override de datos (histórico extendido, conserva cost model del símbolo):
python scripts/run_edge_robustness.py --timeframe 1d --symbols US500 \
  --strategy vol_breakout_v1 --data-file data/raw/parquet/1d/spx_long_1d.parquet \
  --paths 1000 --out data/reports/audit --out-name X_spx57

# barrido completo (84 combos, ~1 h): bucle sobre
#   TF ∈ {1d,4h} · SYM ∈ {XAUUSD XAGUSD EURUSD GBPUSD USDJPY US500 US30}
#   STRAT ∈ {MA_10_30 tsmom_v1 Momentum vol_breakout_v1 mean_rev_v1 BB_ZScore}
```

Los ~95 JSON del pivote están en `data/reports/rama2/` y
`data/reports/edge_robustness*_{long,icm}.json`. `_sweep_summary.txt` los resume.

Reportes existentes a contrastar: `data/reports/rama2/*.json`,
`data/reports/edge_robustness*_{long,icm}.{json,md}`.

---

## 4. Hipótesis de sesgo a FALSAR (el pivote ya las revisó — verificar de forma independiente)

### M-1 — hallazgo de método CONFIRMADO Y CORREGIDO por el pivote (verificar)

**`net_returns` sobre-cobraba ~2× a los instrumentos MT5 (FX / índices / metales).**
`core/ml/i1_gate_validator/costs.py`: `net_returns` multiplica `unit_cost` por
`signals.diff().abs()`, que suma **2 por round-trip** → el diseño asume que
`half_side_cost_pct` devuelve el coste **de un lado (medio spread)**. La rama
**cripto** sí lo hacía (`commission_pct + slippage_pct`, por fill). La rama **MT5**
devolvía `spread_pips·pip_value/notional` = el **spread completo** → cobraba
**2 spreads por round-trip** en lugar de 1. Dirección del sesgo: penaliza de más
→ **sesga a FRAGILE**.
- **Fix aplicado:** la rama MT5 ahora devuelve `(spread_dollars/notional) / 2`
  (medio spread por lado). Costes round-trip resultantes: XAUUSD 1.13 bps, EURUSD
  0.56, US500 0.80, US30 0.50 (cripto intacto, 30 bps). Comisión de bróker
  (~$3.5/lot RT en IC Raw) sigue sin modelar; la cubre el barrido ×1..×3.
- **Re-verificación con M-1 corregido** (1000 paths):
  | Caso | Holdout | MC holdout | MC full-sample | Anchored WF | Veredicto |
  |---|--:|---|---|--:|:--:|
  | XAUUSD/Momentum 1h (28a) | +1.00 | [−0.26,+2.41] | [−0.47,+0.72] P=0.65 | −0.08 | FRAGILE (falla 3) |
  | **XAUUSD/MA_10_30 1h (28a)** | +1.42 | [+0.19,+2.82] ✅ | **[−0.40,+0.73] P=0.73** | +0.07 (folds<½) | **FRAGILE (`not_single_regime` + WF)** |
  | US500/tsmom_v1 1d (S&P 57a) | +0.44 | [−0.09,+0.95] | [−0.22,+0.27] P=0.56 | −0.05 | FRAGILE (falla 3) |
  | US500/vol_breakout 1d (S&P 57a) | −0.16 | [−0.67,+0.33] | [−0.39,+0.11] P=0.14 | +0.18 | FRAGILE (falla 3) |
- **Conclusión del pivote:** M-1 corregido mejora las métricas marginales
  (MC-holdout de MA_10_30 pasa), **pero NO revierte el NO-GO**: el MC **full-sample**
  sigue cruzando cero sobre 14-57 a (P(Sharpe>0) ≈ 0.56-0.73) y `not_single_regime`
  + anchored WF largo siguen fallando. Ningún (activo, estrategia, TF) alcanza
  EDGE_ROBUST — ni con M-1 corregido, ni con coste **cero** (comprobado a ×0.1).
- **Para el auditor:** verificar el fix de M-1, dictaminar su severidad como
  hallazgo previo (¿afectó decisiones anteriores?), y confirmar que la
  re-verificación de arriba es correcta y suficiente.

### Hipótesis restantes

| # | Hipótesis de falso-negativo | Chequeo ya hecho (verificar) | Estado según el pivote |
|---|---|---|---|
| H1 | El **tamaño de bloque del MC** (`block`: 24@1h, 12@4h, **5@1d**) es demasiado corto → CI del Sharpe demasiado ancho → rechaza edges reales. | Re-corrida S&P 57 a / `tsmom_v1` con block 5/10/20/30: la CI holdout se mantiene rozando cero; la CI **full-sample** no se mueve ([−0.25,+0.23]); WF OOS invariante (−0.04). | **No explica el NO-GO.** |
| H2 | El criterio "**CI MC holdout con límite inferior > 0**" es estadísticamente demasiado exigente para holdouts de 2–3 años. | El plan lo fija explícitamente; además el **MC full-sample** (usa toda la muestra, 14–57 a) también cruza cero en ~todos los runs. | **No explica el NO-GO.** El auditor debe pronunciarse sobre si el bar del plan es razonable. |
| H3 | `apply_regime_filter` con `min_adx` alto (20–24) mata señales buenas antes de evaluarlas. | Pendiente — **auditar**: correr con `regime_filter=False` sobre 3–4 (activo, estrategia) y ver si aparece edge. | No evaluado a fondo. |
| H4 | `apply_min_holding` / `apply_cooldown` (bucles Python) tienen un bug que degrada la serie de señales. | Pendiente — **auditar**: property-test contra una implementación de referencia. | No evaluado. |
| H5 | El **holdout = último 20%** cae en un régimen desfavorable para las familias probadas. | Al contrario: para S&P y oro el holdout reciente es el régimen *favorable* (bull) y aun así fallan full-sample. | Sesga a **aceptar**, no a rechazar. |
| H6 | `_ensure_indicators` sirve indicadores mal calculados (los parquet enriquecidos saltan `calculate_advanced_features`). | Las 6 familias solo leen `close/high/low/ema_9/ema_21/rsi_14/bb_*/adx_14/atr_14` — todos del set estándar. | Verificado; **auditar** de todos modos. |
| H7 | `net_returns` penaliza el coste de forma incorrecta. | **Ver M-1 arriba — CONFIRMADO.** Sobre-cargo ~2× a instrumentos MT5. No revierte el NO-GO. | Confirmado; el auditor fija severidad. |

## 5. Hipótesis de FALSO-POSITIVO a falsar (para el candidato US500/vol_breakout/1d)

| # | Hipótesis | Chequeo del pivote |
|---|---|---|
| P1 | El "EDGE_ROBUST" del barrido es real y se descartó por prejuicio. | Refutado: sobre S&P real 57 a → holdout Sharpe **−0.18**, P(Sh>0) full-sample **0.117**. |
| P2 | `not_single_regime` deja pasar concentración de P&L > 85 % si el bucket menor no es negativo. | Confirmado como **hueco del check** (sesga a aceptar). El auditor debe decidir si endurecerlo. |

---

## 6. Entregable de la auditoría

`docs/audits/AUDIT_F2_QUANT_<AAAA-MM-DD>.md` con el formato de `AUDIT_TEMPLATE.md`:

1. **Matriz de hallazgos** `ID | área | hallazgo | evidencia | severidad | veredicto`.
2. Para cada hipótesis H1–H7 / P1–P2: **confirmada / refutada / no concluyente** + evidencia reproducible.
3. **Veredicto sobre la metodología:** ¿la batería 2.6 es apta para decidir (b)? ¿algún criterio hay que recalibrar (con justificación estadística escrita)?
4. **Veredicto sobre la conclusión:** ¿se sostiene el NO-GO de (b), o hay ≥ 1 (activo, estrategia, TF) con edge que la batería descartó indebidamente?
5. Score de área **Quant** (baseline `docs/audits/BASELINE_2026-08-28.md`: 2.5) → nuevo valor.

**Si el veredicto confirma el NO-GO:** el pivote pasa a Rama 3 (universo) o Rama 4
(producto) — decisión de negocio del usuario.
**Si encuentra un edge indebidamente descartado:** se re-abre F2 solo para ese
activo con el criterio corregido y documentado.
