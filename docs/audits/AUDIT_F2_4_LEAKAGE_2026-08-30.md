# AUDIT F2.4 — Leakage & data hygiene

> Entregable 2.4 del `docs/PLAN_ELEVACION_MADUREZ_2026-08-28.md`.
> Alcance: **solo verificación**, sin ML nuevo, sin refactor.

- **Fecha:** 2026-08-30
- **Auditor:** pase de revisión de código + auditoría de datos ejecutada
- **Archivos bajo lupa:** `core/features/feature_engineering.py`,
  `core/features/indicators.py` (donde `calculate_all` hace el trabajo real),
  `core/ml/target_engine.py`
- **Datos:** `data/raw/parquet/1h/*.parquet` (6 archivos) vía
  `scripts/audit_data_quality.py`

---

## Veredicto

| | |
|---|---|
| **Features (`indicators.py` / `feature_engineering.py`)** | ✅ **Sin look-ahead.** Todo `rolling`/`ewm`/`shift` es causal. 2 notas de robustez (VWAP path-dependent; sesiones hard-coded UTC — OK porque los datos son UTC). |
| **Labels (`target_engine.py`)** | ⚠️ **6 puntos de look-ahead**, todos de la misma clase: **umbral/edge calibrado sobre toda la serie (incluida la zona del target desplazado)**. **Ninguno está cableado** en `core/` ni `scripts/` salvo `build_ternary_training_labels`, que se usa **solo con slices de train** → no explotado hoy. Trampa para F5. |
| **Alineación feature/label** (`i1_ml_signal.fit_model_in_memory`) | ✅ Correcta: label en `i` = signo de `(close[i+6]-close[i])/close[i]`; feature en `i`; las 6 filas finales se descartan (`enriched.iloc[:n]`). |
| **Impacto en el GATE F2 / edge de 2.6** | **Nulo.** XAUUSD opera con `Momentum` (regla). Las 7 estrategias I1 basadas en reglas no tocan `target_engine`. Solo `ml_lgb_v1` lo usa y no está aprobado en ningún símbolo. |

---

## Parte 1 — `core/features/indicators.py` (+ `feature_engineering.py`)

`FeatureEngine.calculate*` delega en `calculate_all`, que aplica en orden: RSI, EMA,
MACD, ATR, Bollinger, volumen, tendencia, régimen de volatilidad, retornos, ADX,
retornos ajustados por vol, features temporales, features avanzadas.

### Revisión causal (bar `i` solo usa datos ≤ `i`)

| Grupo | Mecanismo | Causal? |
|---|---|:--:|
| RSI 14/7, EMA 9/21/50/200, MACD | `ta.*` / `ewm(adjust=False)` | ✅ |
| ATR 14 (`calculate_atr_series`) | Wilder / `ewm` sobre `high-low`, `close.shift(1)` | ✅ |
| Bollinger (`bb_*`) | `rolling(20).mean/std` | ✅ |
| `ret_1..24` | `close.pct_change(n)` | ✅ |
| ADX 14 (`_calc_adx`) | `diff`, `ewm(span=14)` | ✅ |
| `vol_adj_ret` | `ret_1 / (atr_14/close)` | ✅ |
| Régimen de volatilidad (`_calc_volatility_regime`) | `atr_pct.rolling(100, min_periods=20).quantile(...)` — **rolling**, no global | ✅ (el comentario "evita look-ahead" es correcto) |
| Temporales (`hour_sin/cos`, sesiones, `is_weekend`) | solo `timestamp` | ✅ |
| OBV | `cumsum(sign(diff)*volume)` | ✅ |
| Hurst (`_calculate_hurst`) | `series.iloc[i-window:i]` — **excluye** `i` | ✅ |
| `rolling_sharpe_20/50/100`, `rolling_kurtosis/skewness` | `pct.rolling(w).mean/std/apply` | ✅ |
| `autocorr_lag1..5`, `returns_autocorr` | `rolling(w).apply(autocorr)` | ✅ |
| `z_score_vs_ma20` | `(close - rolling(20).mean) / rolling(20).std` | ✅ |
| `volume_price_corr` | `close.iloc[i-20:i].corr(volume.iloc[i-20:i])` — **excluye** `i` | ✅ |
| `volume_imbalance` | `up/down_volume.rolling(20).mean` | ✅ |

**No se encontró un solo cómputo que use `shift(-k)` (k>0), `.quantile()`/`.median()`
global, `.expanding()` mal usado, ni normalización con estadísticos de todo el
dataset.** Las features son aptas para walk-forward siempre que se recalculen con
warm-up histórico real (ya lo hace `_is_enriched` para no recomputar sobre slices
truncados).

### Notas de robustez (no leakage)

| ID | Nota | Severidad | Recomendación |
|---|---|---|---|
| R-1 | **VWAP path-dependent.** `_calc_volume_indicators`: `vwap = (tp*vol).cumsum()/vol.cumsum()` con reset diario por `ffill`. Es causal, pero el valor histórico **depende de dónde arranca el DataFrame**: cortar la serie en otro punto cambia el VWAP de todas las barras anteriores al primer reset diario contenido. | Baja | Documentar; o forzar el primer reset al inicio de cada frame. Afecta reproducibilidad de backtests que hacen slicing, no al live. |
| R-2 | **Sesiones hard-coded en UTC** (`is_london_session` 8–16, `is_new_york_session` 13–21). Correcto **porque** los parquet son `datetime64[ms, UTC]` (verificado en Parte 3). Si alguna vez entra data en otra tz, las banderas quedan corridas. | Baja | `assert` de tz UTC al entrar a `_calc_temporal_features`. |
| R-3 | `_validate_nan` solo mira `tail(100)` de 5 columnas críticas. Un bloque de NaN en el medio de la serie no lo detecta. | Baja | Suficiente para el uso actual (features "as-of last bar"); ampliar si se entrena sobre toda la serie. |

---

## Parte 2 — `core/ml/target_engine.py`

### Uso real (grep `core/` + `scripts/`)

- `build_ternary_training_labels` → `core/ml/i1_ml_signal.py:66` (entrena `ml_lgb_v1`),
  `scripts/retrain.py:119`. **Ambos pasan slices de train**, no la serie completa.
- `compute_target`, `_dynamic_target`, `_multi_step_target`, `_asymmetric_target`,
  `_risk_adjusted_target`, `_volatility_regime_target`, `calculate_volatility_regime`,
  `calculate_asymmetric_threshold`, `calculate_dynamic_threshold`:
  **sin referencias en `core/` ni `scripts/`** (código latente / usado en notebooks/tests).

### Hallazgos de look-ahead

| ID | Ubicación | Problema | Severidad efectiva hoy | Fix sugerido |
|---|---|---|---|---|
| **L-1** | `build_ternary_training_labels` (l.94) | `q30 = np.nanpercentile(pct_moves, 30)` sobre **todo el array de entrada**. La zona muerta de cada label usa un percentil informado por barras futuras del mismo frame. Solo afecta el **ancho de la zona muerta**, no la dirección. | **BAJA** — los 2 callers pasan train-only, así que no hay fuga al holdout. | Percentil expandido (`pct_moves[:i]`) o pasar `q30` calculado por fold. |
| **L-2** | `compute_target` rama `ternary` (l.128-133) y `_multi_step_target` (l.211) | `calculate_dynamic_threshold(returns, window)` hace `returns.tail(window).std()` → **un escalar global tomado del final de la serie** aplicado a todas las filas. | BAJA (dead code) | Umbral por fila con ventana móvil que termine en `i`. |
| **L-3** | `_asymmetric_target` (l.228) | `calculate_asymmetric_threshold` usa `returns[returns>0].mean()` sobre **toda** la serie. | BAJA (dead code) | Ídem L-2, expandiendo. |
| **L-4** | `_risk_adjusted_target` (l.247-250) | `sharpe_like` contiene `future_return`; `median = sharpe_like.median()` sobre **todo** (incluye futuro) y se usa como umbral del label. | MEDIA si se cablea | Umbral fijo o mediana de train. |
| **L-5** | `calculate_volatility_regime` (l.68-70) → `_volatility_regime_target` | `rolling_std = returns.rolling(w).std()` (bien), pero luego `low_thresh = rolling_std.quantile(q)` es **cuantil global** de toda la serie. | MEDIA si se cablea | `rolling_std.expanding().quantile()` o cuantil de train. |
| **L-6** | `compute_target` rama `percentile` (l.143-148) | `pd.qcut(future_return.dropna(), q=5)` calcula los cortes sobre **toda** la distribución del target futuro. | MEDIA si se cablea | Cortes por fold. |
| **L-7** | `compute_target` (l.168) | Devuelve el df con el mismo índice y **no recorta** las últimas `horizon` filas (target NaN). Un caller descuidado entrena con NaN. `i1_ml_signal` sí recorta (`enriched.iloc[:n]`). | BAJA | `return df.iloc[:-horizon]` o documentar el contrato. |

### Lo que está BIEN hecho

- `_dynamic_target` (l.172-196): umbral **por fila** con `returns_series.iloc[:i]` (expanding, sin futuro). Es la implementación de referencia — el resto debería copiar este patrón.
- La forma del target (`close.shift(-horizon)`) es correcta: mirar hacia adelante **es** la definición del label.
- `i1_ml_signal.fit_model_in_memory`: `n = len(labels)`, `X = enriched.iloc[:n]` → alineación feature/label exacta y descarte de la cola.

---

## Parte 3 — Higiene de datos (`scripts/audit_data_quality.py`)

`python scripts/audit_data_quality.py` → **0 violaciones duras** en los 6 archivos.

| Symbol | Rows | Span (d) | UTC | Mono | Dups | OHLC bad | Gaps intradía | Gaps fin de semana | Ret > límite | z>10 |
|---|--:|--:|:--:|:--:|--:|--:|--:|--:|--:|--:|
| EURUSD | 17222 | 1019 | ✓ | ✓ | 0 | 0 | 9 | 145 | 0 | 3 |
| GBPUSD | 17224 | 1019 | ✓ | ✓ | 0 | 0 | 8 | 145 | 0 | 2 |
| USDJPY | 17125 | 1019 | ✓ | ✓ | 0 | 0 | 7 | 145 | 0 | 6 |
| XAUUSD | 13708 | 876 | ✓ | ✓ | 0 | 0 | 27 | 124 | 0 | 3 |
| US30 | 5068 | 1063 | ✓ | ✓ | 0 | 0 | 580 | 149 | 0 | 0 |
| US500 | 5068 | 1063 | ✓ | ✓ | 0 | 0 | 580 | 149 | 0 | 1 |

**Lectura.**
- **Duro:** timestamps `datetime64[ms, UTC]`, monótonos, sin duplicados; OHLC íntegro
  (high≥low, high≥max(o,c), low≤min(o,c), precios>0, sin NaN). ✅
- **Blando:** los "gaps de fin de semana" (~145) son el cierre viernes→lunes de FX;
  los 580 "gaps intradía" de US30/US500 son instrumentos **solo sesión** (~6.5 h/día),
  cada cierre nocturno cuenta como hueco — esperado, no es corrupción.
- Los `z>10` (2–6 por símbolo FX) son barras de noticias (CPI/NFP/BoJ); ninguna supera
  el límite de plausibilidad de `|log-return|` por clase → no se recortan.
- **BTCUSDT / ETHUSDT: sin parquet 1h.** Es la brecha de datos ya conocida
  (F1 audit, `test_all_symbols_have_1d_data`).

---

## Pendiente de 2.4 (no ejecutable en esta sesión)

**Ampliación del histórico** (extender la ventana 1h, incorporar BTC/ETH) requiere
credenciales de proveedor y descargas — queda para una corrida con red/keys. La
maquinaria de verificación (`scripts/audit_data_quality.py`) ya está y se vuelve a
correr sobre los datos nuevos.

---

## Acciones recomendadas

| Prioridad | Acción | Fase |
|---|---|---|
| P2 | Antes de aprobar **cualquier** estrategia ML: arreglar L-1..L-6 (umbrales/cortes calculados **por fold**, nunca sobre la serie completa). Copiar el patrón de `_dynamic_target`. | F5 |
| P3 | `compute_target`: recortar las últimas `horizon` filas o documentar el contrato (L-7). | F5 |
| P3 | `assert` de tz UTC en `_calc_temporal_features`; documentar la path-dependence del VWAP (R-1, R-2). | F3 |
| P3 | Descargar histórico 1h de BTC/ETH y extender el resto; re-correr `audit_data_quality.py`. | F2.4 (con red) |
