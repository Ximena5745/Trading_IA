# CORE VALIDATION — RAMA 1 (pivote) — 2026-08-30

> Continuación del mini‑plan de pivote de `docs/CORE_VALIDATION_DECISION_2026-08-30.md`.
> **Rama 1** = ¿el NO‑GO de la condición (b) del GATE F2 es **longitud de datos** o
> **ausencia de señal**? Tres palancas ejecutables sin stack/keys:
> (1) revisión del `CostModel`, (2) BTC/ETH con holdout largo (9 años 1h),
> (3) estrategias alternativas de XAUUSD bajo la batería 2.6.

- **Fecha:** 2026-08-30
- **Base:** commit `cee5b63` + rama de trabajo F1/F2
- **Insumos regenerados:** `data/reports/quant_report.{json,md}`,
  `data/reports/edge_robustness.{json,md}` (XAUUSD/Momentum),
  `data/reports/edge_robustness_XAUUSD_{tsmom_v1,MA_10_30}.{json,md}`,
  `data/reports/data_quality_report.{json,md}`.
- **Cambios de código de esta rama:**
  - `core/models.py` — `XAUUSD.spread_pips` 0.25 → 30 (bug de unidades: ~100× de subestimación).
  - `core/ml/i1_gate_validator/costs.py` — nota sobre pares JPY‑quote (bug ~100× no corregido, no gate‑relevante).
  - `scripts/run_edge_robustness.py` — `--strategy` / `--params` / `--out-name` para estresar candidatas no aprobadas.
  - `data/raw/parquet/1h/{btcusdt,ethusdt}_1h.parquet` — 78 472 barras (2017‑08‑17 → 2026‑08‑05),
    normalizados desde `data/raw/*_1h.parquet` (ya existían, nunca cableados al pipeline quant).
    Enriquecidos con el set de indicadores estándar (sin `calculate_advanced_features`,
    que tiene loops O(n) por fila y hacía inviable el reporte sobre 78k barras).
  - `data/raw/XAUUSD_1h_mt5.parquet` + `data/raw/parquet/1h/xauusd_long_1h.parquet` —
    **28 399 barras H1** del terminal MT5 Bullfy‑Trade, 2021‑11 → 2026‑08 (~4.8 años).
  - `data/raw/XAUUSD_1h_icm.parquet` + `data/raw/parquet/1h/xauusd_icm_1h.parquet` —
    **67 694 barras H1** del terminal **MT5 IC Markets** (demo `ICMarketsSC-Demo`,
    Raw Trading Ltd), **1998‑04‑22 → 2026‑08‑31 = ~28.4 años**. Holdout 20 % =
    13 538 barras ≈ **2.2 años** (desde 2024‑05‑16). `pip install MetaTrader5` (5.0.6147).
    Spread ECN del broker = **5–10 points ($0.05–0.10)** → el `CostModel` a 30 points
    ($0.30) es **conservador ~3–6×**.
  - `scripts/run_edge_robustness.py` — `--data-file` para re‑probar un símbolo sobre
    un parquet de histórico extendido conservando su cost model / asset config.

---

## Palanca 1 — Revisión del `CostModel` de XAUUSD

### Hallazgo

`core.ml.i1_gate_validator.costs.half_side_cost_pct` para instrumentos MT5 calcula
`spread_pips * pip_value / (lot_size * ref_price)`. Esto colapsa a
`spread_en_precio / precio` **solo** cuando `pip_value == pip_size * lot_size`.

| Símbolo | half‑side ANTES | half‑side AHORA | Realista | Estado |
|---|--:|--:|--:|---|
| **XAUUSD** | **0.009 bps** | **1.13 bps** (ref 2650) | ~1–2 bps | ✅ corregido (`spread_pips` 0.25 → 30) |
| EURUSD | 0.56 bps | 0.56 bps | ~0.5–1 bps | ✅ ya correcto |
| US500 | 0.80 bps | 0.80 bps | ~0.6–1 bps | ✅ ya correcto |
| US30 | 0.50 bps | 0.50 bps | ~0.5–1 bps | ✅ ya correcto |
| USDJPY | 0.004 bps | 0.004 bps | ~0.5–1 bps | ⚠️ bug ~100× (JPY‑quote); documentado, no corregido (Sharpe −1.5, no gate‑relevante) |

`spread_pips=0.25` para el oro estaba en **dólares** cuando el campo se expresa en
unidades de `point` (1 point = $0.01 para el oro). Un spread real de ~$0.25–0.30
son **25–30 points**, no 0.25. Efecto: el barrido de costos ×1..×3 de 2.6 era
**vacío** (cost drag ≈ 0 en Sharpe).

### Impacto en (b) — XAUUSD / Momentum lookback 16 (estrategia aprobada)

Re‑corrida de `run_edge_robustness.py --symbols XAUUSD` con el modelo corregido:

| Métrica | Antes (drag ≈ 0) | Ahora (costos reales) | Criterio (b) |
|---|--:|--:|:--:|
| Holdout Sharpe neto | 1.3232 | **1.0203** | ✅ ≥ 0.8 (por poco) |
| Cost drag (Sharpe) | 0.0025 | **0.3054** | — |
| Sharpe neto @ costos ×1.75 | ~1.32 | **0.7921** | ❌ < gate 0.8 |
| Sharpe neto @ costos ×2 | ~1.32 | **0.7162** | ⚠️ > 0 (pasa literal) pero < gate |
| MC holdout CI95 | [−1.43, 3.76] | **[−1.75, 3.47]** | ❌ cruza 0 |
| MC full‑sample CI95 | [+0.45, +2.85] | **[−0.08, +2.35]** | ❌ ahora **también** cruza 0 |
| Régimen (ADX+ buckets) | 1/2 | **1/2** | ❌ mono‑régimen |
| Anchored WF OOS Sharpe | +1.59 | **+1.12** (4/4 folds +) | ✅ |

**Lectura:** el único activo con edge nominal se debilita de forma **material** con
un modelo de costos honesto. El Sharpe holdout cae por debajo del gate a un
múltiplo de costos de solo **1.75×**, y la defensa "es longitud de datos, no
ausencia de señal" se erosiona: el CI de Monte Carlo **full‑sample** (13 707
barras) ahora también cruza cero. **Refuerza el NO‑GO de (b).**

> ⚠️ **`data/reports/i1_gate_report.json` quedó obsoleto/optimista.** Fue generado
> con el `CostModel` roto (Sharpe holdout XAUUSD 1.3232). El cross‑check de 2.5
> ahora marca `✗` para XAUUSD/Momentum (holdout 1.02 vs 1.32, Δ 0.30 > tol 0.20).
> Re‑correr el gate I1 completo es trabajo del pivote, no de esta rama.

---

## Palanca 2 — BTC/ETH con holdout largo

`data/raw/parquet/1h/{btcusdt,ethusdt}_1h.parquet`: **78 472 barras** cada uno,
2017‑08‑17 → 2026‑08‑05, 0 duplicados, gaps sanos
(`audit_data_quality.py` → `ok` en los 8 símbolos). Holdout 20 % ≈ **15 694 barras
≈ 1.8 años** — vs 2 741 barras / 0.45 años de XAUUSD.

### Resultado (2.5 — `quant_report.md`, estrategias del override I1 para cripto)

| Symbol | Mejor estrategia | WF Sharpe | **HO Sharpe neto** | HO MaxDD | CostDrag |
|---|---|--:|--:|--:|--:|
| BTCUSDT | vol_breakout_v1 | −0.13 | **−0.39** | 0.79 | 0.74 |
| BTCUSDT | tsmom_v1 / Momentum | −1.45 | −2.40 | 0.92 | 2.39 |
| ETHUSDT | vol_breakout_v1 | −0.29 | **−1.04** | 0.82 | 0.42 |
| ETHUSDT | tsmom_v1 / Momentum | −1.52 | −1.49 | 0.93 | 1.64 |

**Todas negativas.** El holdout largo **no** revela un edge cripto oculto: con
9 años de datos y un holdout de 1.8 años, ninguna de las 3 familias técnicas 1h
tiene Sharpe neto holdout positivo. Ni siquiera se justifica correr 2.6 (no hay
candidata que pase el umbral de entrada).

**Conclusión Palanca 2:** para BTC/ETH la hipótesis "es longitud de datos" **falla
limpiamente** — es ausencia de señal. Consistente con F‑02 a nivel de universo.

---

## Palanca 3 — Estrategias alternativas de XAUUSD bajo 2.6

`run_edge_robustness.py --symbols XAUUSD --strategy <id>`, con el `CostModel`
corregido, sobre las candidatas que en 2.5 superaban al `Momentum` aprobado.

| Estrategia | HO Sharpe neto | drag | MC holdout CI95 | MC full CI95 | Sharpe @×2 | Régimen | Anchored WF OOS | Veredicto |
|---|--:|--:|---|---|--:|:--:|--:|:--:|
| Momentum (aprobada) | 1.02 | 0.31 | [−1.75, 3.47] | [−0.08, 2.35] | 0.72 | mono 1/2 | +1.12 (4/4) | **FRAGILE** |
| tsmom_v1 | 1.32 | 0.35 | [−1.39, 3.75] | [−0.33, 2.21] | 0.98 | mono 1/2 | +0.20 (3/4) | **FRAGILE** |
| **MA_10_30** | **2.31** | **0.18** | **[−0.04, 4.88]** | **[+0.25, 2.68]** | **2.12** | mono 1/2 | +1.39 (3/4) | **FRAGILE** |

- **MA_10_30 es la candidata más fuerte con diferencia:** holdout Sharpe 2.31,
  turnover bajo (254), sobrevive costos ×3 con holgura (drag 0.18), MC
  **full‑sample con límite inferior +0.25**, y el MC **holdout falla por un pelo**
  (límite inferior **−0.039**, P(Sharpe>0) = 0.972). Con un holdout algo más largo
  cruzaría a positivo.
- **Falla `not_single_regime`:** el edge se concentra en ADX alto (1/2 buckets
  ADX positivos). Es inherente a un cruce de medias trend‑following, pero el
  criterio literal del plan lo reprueba. **No se relaja aquí** (regla explícita de
  la decisión); queda como punto para la auditoría cuantitativa independiente.
- tsmom_v1: holdout OK pero Anchored WF casi nulo (+0.20, un fold −2.94) → peor
  que Momentum en robustez temporal.

**Conclusión Palanca 3 (holdout corto, 2.4 años):** ninguna candidata pasa (b).
`MA_10_30` parecía el mejor candidato (holdout 2.31, MC holdout fallando por
−0.04). **La Palanca 4 lo pone a prueba con el holdout largo.**

---

## Palanca 4 — XAUUSD con holdout largo (MT5)

`run_edge_robustness.py --symbols XAUUSD --strategy <id> --data-file …` con el
`CostModel` de oro corregido, sobre tres muestras de longitud creciente.

### Progresión al alargar la muestra — `MA_10_30`

| Muestra | Fuente | HO bars (≈años) | **HO Sharpe** | **MC holdout CI95** | **MC full‑sample CI95** | P(Sh>0) full | Anchored WF | Veredicto |
|---|---|--:|--:|---|---|--:|--:|:--:|
| 2.4 años | yfinance `GC=F` | 2 741 (0.45) | **2.31** | [−0.04, 4.88] | **[+0.25, +2.68]** | 0.994 | +1.39 (3/4) PASS | FRAGILE (2/4) |
| 4.8 años | MT5 Bullfy | 5 679 (1.0) | **1.44** | [−0.42, 3.43] | **[−0.32, +1.36]** | 0.887 | +0.63 (8/11) PASS | FRAGILE (2/4) |
| **28.4 años** | **MT5 IC Markets** | 13 538 (2.2) | **1.18** | [−0.07, 2.59] | **[−0.60, +0.54]** | **0.451** | **−0.18 (10/29) FAIL** | **FRAGILE (fail 3/4)** |

### `Momentum` (lookback 16) sobre las 67 694 barras de IC Markets

| Métrica | Valor | Criterio (b) |
|---|--:|:--:|
| Holdout Sharpe neto | **0.6254** | ❌ **< gate 0.8 en crudo** |
| Cost drag (Sharpe) | 0.759 | — |
| Sharpe neto @ costos ×2 | **−0.1249** | ❌ se anula a ×2 |
| MC holdout CI95 | [−0.62, 2.05] | ❌ cruza 0 |
| MC full‑sample CI95 | [−0.80, +0.41], P(Sh>0) = **0.258** | ❌ |
| Régimen | mono (1/2 ADX, 1/2 vol) | ❌ |
| Anchored WF (29 folds) | **−0.72**, 7/29 positivos | ❌ |
| **Verdict** | **FRAGILE — falla los 4 criterios** | |

### Resultado decisivo

**Cada métrica se degrada de forma monótona al alargar la muestra.** El "edge" de
XAUUSD era **enteramente un artefacto de la ventana alcista 2021‑2026**:

1. El **MC full‑sample CI** pasa de `[+0.25, +2.68]` (2.4 a) → `[−0.32, +1.36]`
   (4.8 a) → **`[−0.60, +0.54]` con P(Sharpe>0) = 0.45** (28 a). Sobre 28 años el
   Sharpe de `MA_10_30` es **indistinguible de cero, simétricamente**.
2. El **walk‑forward anclado a 29 folds** (1998→2026) da OOS neto **−0.18**
   (`MA_10_30`) y **−0.72** (`Momentum`): OOS negativo sostenido en toda la década
   de 2010, solo positivo en los últimos folds (2024‑2026).
3. `Momentum` **no llega ni al gate 0.8 en crudo** (0.63) y se vuelve negativo a
   costos ×2.
4. Ambas siguen siendo **mono‑régimen**.

**Conclusión Palanca 4:** la hipótesis "el NO‑GO de (b) es longitud de datos"
**queda refutada de forma concluyente para XAUUSD** con la muestra más larga
obtenible (28 años). El oro a 1h con estrategias técnicas **no tiene edge**.

---

## Veredicto de Rama 1

| Palanca | Hipótesis | Resultado |
|---|---|---|
| 1 — CostModel | El barrido de costos de 2.6 no era informativo | ✅ Confirmado y corregido (bug ~100×). XAUUSD/Momentum **empeora** (holdout 1.32 → 1.02; < gate a ×1.75). El gate I1 quedó optimista. Spread live del broker $0.14 → el modelo a $0.30 es conservador. |
| 2 — BTC/ETH holdout largo | El NO‑GO cripto es longitud de datos | ❌ **Refutada.** 9 años de datos, holdout 1.8 años, todas las familias con Sharpe neto holdout **negativo**. Ausencia de señal. |
| 3 — Alternativas XAUUSD (holdout corto) | Otra estrategia de XAUUSD pasa (b) | ❌ Ninguna pasa. `MA_10_30` parecía cerca (MC holdout −0.04). |
| 4 — XAUUSD holdout largo (MT5) | El NO‑GO de XAUUSD es longitud de datos | ❌ **Refutada de forma concluyente.** Progresión 2.4 a → 4.8 a → **28.4 a** (IC Markets, 67 694 barras): cada métrica se degrada monótonamente. A 28 años, `MA_10_30` MC full‑sample **[−0.60, +0.54]** (P = 0.45), anchored WF 29 folds **−0.18 (FAIL)**; `Momentum` **falla los 4 criterios** (holdout 0.63 < gate, negativo a costos ×2, WF −0.72). El edge era la ventana alcista 2021‑2026. |

**⛔ El NO‑GO de la condición (b) es CONCLUYENTE, no preliminar, en lo que respecta
al edge:** las dos vías que podían salvarlo (más datos de cripto — 9 años; más
datos de oro — 28 años) están **agotadas y ambas lo refutan**. No existe ningún
(activo, estrategia) del universo actual con edge robusto a 1h.

### Qué sigue

1. **Rama 0** (cierre formal de (a)/(c): stack + testnet + ventana corta + pase de
   auditoría cuantitativa independiente) — sin cambios; documenta pero **no puede
   revertir (b)**.
2. **Auditoría cuantitativa independiente** — que valide (no relaje): (i) la
   refutación de la hipótesis de longitud de datos, (ii) el `CostModel` de XAUUSD
   a 30 points, (iii) si `not_single_regime` aplica a un trend‑follower puro
   (aunque ya no cambia el veredicto: el MC full‑sample también falla).
3. **Pasar a Rama 2** del plan de pivote: **4h / 1d** sobre el mismo universo
   (menos ruido, menos coste relativo) + **familias nuevas** (carry/roll,
   estacionalidad, cross‑asset momentum, pairs). **El terminal MT5 IC Markets ya
   está operativo y sirve ~28 años de historia** (XAUUSD desde 1998; el resto del
   universo FX/índices/metales con profundidad similar) — se puede tirar H1/H4/D1
   largo de todo el universo directamente, sin proveedor externo. Wiring sugerido:
   un `scripts/fetch_mt5_history.py` que recorra `TRADED_UNIVERSE` →
   `data/raw/parquet/{tf}/<sym>_<tf>.parquet`.
4. Si Rama 2 no produce un edge que pase (b) → replanteo de universo → replanteo
   de producto (Rama 3 / 4).

**No se inicia ningún entregable de F3–F10.**
