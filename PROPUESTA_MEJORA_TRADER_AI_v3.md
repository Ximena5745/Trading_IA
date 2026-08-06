# TRADER AI — Propuesta de Mejora y Ventaja Competitiva

**Versión 3.0 · 4 de agosto de 2026 · Documento estratégico-técnico**
**Autor del análisis:** quant review sobre el repositorio real (`Trading_IA`, branch `main`, commit `7ea6c39`)
**Clasificación:** interno / presentable a inversor sofisticado

---

## Nota metodológica previa — léase antes que nada

Esta propuesta se redactó **contra el código y los datos reales del repositorio**, no contra la descripción del producto del brief. Hay dos divergencias materiales que cambian el contenido de la propuesta, y ocultarlas invalidaría todo lo demás:

**Divergencia 1 — el sistema está mucho más construido de lo que el brief asume.** El brief describe TRADER AI v2.4 con gaps de "modelos ML sin entrenar, sin scheduler, sin features avanzados". La realidad verificada: hay modelos LightGBM entrenados (`data/models/i1_ml/*.joblib`), scheduler APScheduler activo (`scripts/run_pipeline.py:433-461`), `PurgedKFold` y `WalkForwardValidator` reales (`core/ml/validation.py`), un cost model multiactivo real (`core/backtesting/costs.py`), HMM de régimen, motor de riesgo con CVaR, arquitectura hexagonal y 356 tests pasando. El gap no es de construcción.

**Divergencia 2 — el problema real no es el que el brief plantea.** El brief pide más features, más modelos (TFT), más estrategias. El repositorio ya intentó exactamente eso y el resultado, medido honestamente, es que **no hay edge estadístico demostrado en ningún activo** — incluido el único que el Gate I1 marca como PASS. Añadir un Temporal Fusion Transformer sobre 2 años de datos horarios no arregla eso: lo empeora, porque amplía el espacio de búsqueda sobre la misma muestra finita.

La propuesta entrega **las nueve secciones solicitadas, completas**, pero reordena su prioridad alrededor del hallazgo central de la Sección 1. Donde el brief pide algo que la evidencia contradice, se entrega lo pedido *y* se explicita la condición bajo la cual tiene sentido ejecutarlo.

**Supuesto explícito bajo el que se escribe todo lo demás:** el objetivo es alpha real y sostenible sobre capital propio, con opción a producto; no es una demo presentable. Si el objetivo fuera el segundo, la Sección 1 sobra y la Sección 3 se ejecuta tal cual está escrita en el brief.

---

## SECCIÓN 0 — El hallazgo central: el sistema no tiene un problema de modelos, tiene un problema de muestra

### 0.1 Lo que dice el Gate I1 hoy

`data/reports/i1_gate_report.md` (re-ejecutado 2026-07-26, tras corregir dos bugs metodológicos reales):

| Símbolo | Estrategia | Sharpe neto WF | Sharpe neto Holdout | Trades | p-valor WF | Resultado |
|---|---|---:|---:|---:|---:|---|
| BTCUSDT | vol_breakout_v1 | 1.698 | **−2.170** | 405 | 0.047 | FAIL |
| ETHUSDT | vol_breakout_v1 | 1.874 | **−2.102** | 355 | 0.049 | FAIL |
| EURUSD | BB_ZScore | 2.446 | **−0.977** | 1042 | 0.015 | FAIL |
| GBPUSD | ema_rsi_v1 | 2.216 | **−0.951** | 2226 | 0.027 | FAIL |
| USDJPY | vol_breakout_v1 | 2.969 | **−1.487** | 1647 | 0.003 | FAIL |
| US500 | tsmom_v1 | 2.440 | **−3.961** | 197 | 0.100 | FAIL |
| US30 | mean_rev_v1 | 3.320 | +0.640 | **28** | 0.031 | FAIL |
| XAUUSD | Momentum | 2.609 | **+1.323** | 1064 | 0.001 | PASS |

**Veredicto documentado:** BLOCKED (1/8). **Interpretación documentada en `PLAN_MAESTRO.md`:** el patrón consistente WF-positivo / holdout-negativo apunta a "un cambio real de régimen entre el período WF y el holdout".

### 0.2 Por qué esa interpretación es casi con certeza incorrecta

El cambio de régimen es una hipótesis costosa: implicaría rediseñar el sistema alrededor de detección de régimen (Investigaciones I4/I5). Antes de pagar ese costo hay que descartar la hipótesis barata: **que los números WF sean ruido de selección y el holdout no tenga poder estadístico para medir nada**.

**Paso 1 — cuantificar el espacio de búsqueda.** El validador (`core/ml/i1_gate_validator.py` + `core/ml/i1_strategies.py`) evalúa por símbolo:

```
MA_10_30       : 3 fast × 3 slow             =  9 combinaciones
BB_ZScore      : 3 window × 3 z_entry        =  9
Momentum       : 3 lookback                  =  3
ema_rsi_v1     : 2 rsi_low × 2 rsi_high      =  4
mean_rev_v1    : 2 oversold × 2 overbought   =  4
tsmom_v1       : 3 lookback × 2 min_adx      =  6
vol_breakout_v1: 2 lookback × 2 atr_mult     =  4
ml_lgb_v1      : 1                           =  1
                                            ────
                             N_trials ≈ 40 por símbolo
```

Y además se selecciona el **mejor símbolo-estrategia por Sharpe WF** (`i1_gate_validator.py:625-626`), y los parámetros se re-optimizan por ventana (`_select_params`, líneas 373-393). Con 4–8 ventanas walk-forward, el número efectivo de ensayos independientes está entre N=40 y N≈320.

**Paso 2 — calcular el Sharpe máximo esperado bajo hipótesis nula de cero edge.** Bajo H₀ (retornos iid con media cero), el error estándar del Sharpe anualizado depende del **span calendario**, no del número de barras:

$$\hat{\sigma}(SR_{anual}) \approx \frac{1}{\sqrt{Y}}, \quad Y = \text{años de muestra}$$

Y el máximo esperado sobre N ensayos independientes (Bailey & López de Prado, 2014):

$$E[\max SR_N] \approx \hat{\sigma}(SR)\left[(1-\gamma)\,Z^{-1}\!\left(1-\tfrac{1}{N}\right) + \gamma\, Z^{-1}\!\left(1-\tfrac{1}{Ne}\right)\right], \quad \gamma = 0.5772$$

Aplicado a los spans reales del repositorio (medidos sobre `data/raw/*_1h.parquet`):

| Símbolo | Span total | Span WF (80%) | σ̂(SR) WF | **E[max SR \| N=40]** | **E[max SR \| N=320]** | SR WF observado |
|---|---:|---:|---:|---:|---:|---:|
| BTCUSDT | 2.00 a | 1.60 a | 0.79 | **1.73** | **2.31** | 1.70 |
| ETHUSDT | 2.00 a | 1.60 a | 0.79 | **1.73** | **2.31** | 1.87 |
| EURUSD | 2.79 a | 2.23 a | 0.67 | **1.47** | **1.95** | 2.45 |
| GBPUSD | 2.79 a | 2.23 a | 0.67 | **1.47** | **1.95** | 2.22 |
| USDJPY | 2.79 a | 2.23 a | 0.67 | **1.47** | **1.95** | 2.97 |
| US500 | 2.91 a | 2.33 a | 0.66 | **1.43** | **1.91** | 2.44 |
| US30 | 2.91 a | 2.33 a | 0.66 | **1.43** | **1.91** | 3.32 (28 trades) |
| XAUUSD | 2.40 a | 1.92 a | 0.72 | **1.58** | **2.11** | 2.61 |

**Lectura:** todos los Sharpe WF reportados caen dentro o apenas por encima de la banda que **produce el puro azar** con este diseño experimental. Un sistema sin ningún edge, buscando 40–320 configuraciones sobre 2 años, produce rutinariamente Sharpe WF de 1.5–2.3. Los números del gate no son evidencia de edge; son la firma esperada del sobreajuste de selección.

**Paso 3 — medir el poder del holdout.** El holdout es el 20% final: **0.40–0.58 años**. Su error estándar:

$$\hat{\sigma}(SR_{holdout}) = \frac{1}{\sqrt{0.48}} \approx 1.44$$

Una estrategia con Sharpe verdadero de +1.0 produce, en un holdout de medio año, estimaciones que van de **−1.9 a +3.9** con 95% de probabilidad. El holdout **no puede distinguir** una estrategia excelente de una desastrosa. Por lo tanto:

- Los holdouts negativos (−0.95 a −3.96) **no son evidencia de cambio de régimen**. Son exactamente lo que se espera al medir con un instrumento cuyo ruido es ±3 Sharpe.
- Y el único PASS tampoco es evidencia de nada: XAUUSD, Sharpe holdout 1.323 sobre 0.48 años → **t = 1.323 × √0.48 = 0.74 → p = 0.23** (una cola). No rechaza H₀ ni de lejos.
- Contra el benchmark de selección (E[max SR|N=40] = 1.58), el **Probabilistic Sharpe Ratio** de XAUUSD es **PSR ≈ 0.40** — es decir, hay ~60% de probabilidad de que su Sharpe verdadero esté por debajo del que produciría el azar.

**Paso 4 — el caso US30 como control de sanidad.** Sharpe WF 3.320 con **28 operaciones**. El error estándar del Sharpe con 28 trades es del orden de ±0.4 por trade agregado; un Sharpe de 3.3 sobre 28 trades no es una medición, es una anécdota. Que este número haya sobrevivido hasta un reporte de gate indica que **falta un filtro de significancia mínima de tamaño muestral** en el propio validador.

### 0.3 Consecuencia: la restricción vinculante es la muestra, no el modelo

Para detectar un Sharpe verdadero de 0.8 con potencia del 80% y α = 0.05 (una cola) sobre una serie única:

$$Y_{requerido} = \left(\frac{z_{1-\alpha} + z_{1-\beta}}{SR}\right)^2 = \left(\frac{1.645 + 0.842}{0.8}\right)^2 \approx \mathbf{9.7\ años}$$

Con 2.0–2.9 años por activo, el proyecto está intentando medir algo con **4–5× menos datos de los necesarios**, y compensándolo con búsqueda de parámetros — que es precisamente la operación que convierte falta de datos en falsos positivos.

Existen exactamente tres salidas, y las tres son ejes de la propuesta:

| Salida | Mecanismo | Coste | Sección | Estado |
|---|---|---|---|---|
| **A. Más span** | Descargar 10–15 años de histórico por activo | ~2 semanas de ingesta, ~$0–200 en datos | S8, Sprint 1 | 🟢 **EJECUTADA 2026-08-04** — 29 símbolos, span medio **21.8 años**, 163.873 barras diarias. Ver [Anexo C](#anexo-c--ejecución-del-sprint-1-y-re-validación-sobre-histórico-profundo) |
| **B. Más sección cruzada** | Un modelo global/panel sobre 28+ activos en vez de 8 modelos por activo; el span efectivo escala con N_activos | Rediseño del stack de modelado | S4 | 🟡 datos listos (22 activos operables), modelado pendiente |
| **C. Menos ensayos** | Presupuesto de multiplicidad explícito + DSR/PBO como criterio de aceptación en lugar de Sharpe crudo | ~1 semana de ingeniería en el gate | S6 | 🔴 pendiente (Sprint 2) |

> **Actualización del 4 de agosto de 2026 — la Salida A ya se ejecutó y el diagnóstico de esta sección quedó confirmado.** Con 25 años de datos, el umbral de ruido $E[\max SR \mid H_0, N{=}40]$ cae de **1.55 a 0.44**. Es decir: el instrumento de medición que producía Sharpe de 1.5–2.3 a partir de puro azar ahora produce 0.44. Todo lo que la Sección 0 argumentaba sobre por qué el Gate I1 no podía medir nada era correcto, y ya no aplica a los datos nuevos. Los resultados de re-ejecutar las pruebas sobre el histórico profundo están en el **Anexo C**, e incluyen un resultado que sí supera el umbral, uno marginal y uno falsado.

**Estas tres cosas, y no un TFT, son la ventaja competitiva real del producto.** El resto de la propuesta desarrolla las nueve secciones pedidas asumiendo que A, B y C se ejecutan primero — porque cualquier estrategia de la Sección 3 evaluada con el gate actual producirá un Sharpe WF de ~2.5 y un holdout aleatorio, exactamente como las ocho que ya se probaron.

---

## SECCIÓN 1 — Diagnóstico competitivo

### 1.1 Metodología del análisis

Se comparan seis categorías de competidor contra TRADER AI en ocho dimensiones. El **GAP de oportunidad (1–10)** mide cuánto espacio hay para que TRADER AI sea decisivamente superior: 10 = el competidor es estructuralmente incapaz de cerrar esa brecha; 1 = el competidor ya lo hace mejor y no tiene sentido competir ahí.

### 1.2 Competidor por competidor

#### 3Commas (bots de crypto, SaaS retail, ~$50–100/mes)

| | |
|---|---|
| **Fortalezas** | (1) UX y onboarding excepcionales — un usuario no técnico opera en 15 minutos. (2) Integración con 18+ exchanges con gestión de claves API madura. (3) Marketplace de señales con efectos de red reales. |
| **Debilidades explotables** | (1) Las estrategias son plantillas paramétricas (DCA, grid, trailing) sin ningún modelo estadístico — no hay validación out-of-sample de nada. (2) Cero gestión de riesgo de portafolio: cada bot es independiente, la correlación entre posiciones es invisible. (3) Solo crypto — no puede ofrecer diversificación cross-asset. |
| **GAP** | **8/10** — el rigor cuantitativo y el riesgo de portafolio son estructuralmente ajenos a su producto. |

#### Cryptohopper (bots + marketplace, SaaS)

| | |
|---|---|
| **Fortalezas** | (1) Marketplace de estrategias monetizado. (2) Backtesting integrado accesible. (3) Papel trading nativo. |
| **Debilidades explotables** | (1) Su backtesting no purga ni aplica embargo — es exactamente el generador de falsos positivos que la Sección 6 ataca. (2) Las señales del marketplace no tienen track record verificable ni deflación por multiplicidad. (3) Sin cost model realista por clase de activo. |
| **GAP** | **8/10** — su ventaja es distribución, no calidad de señal. |

#### QuantConnect / LEAN (plataforma de research institucional-retail)

| | |
|---|---|
| **Fortalezas** | (1) Datos históricos de calidad institucional (tick-level, survivorship-bias-free en equities). (2) Motor de backtesting serio, multiactivo, open source. (3) Comunidad y biblioteca de research enorme. |
| **Debilidades explotables** | (1) Es un IDE, no un producto: el usuario debe traer la estrategia, el modelo y la disciplina estadística. (2) No opina sobre riesgo — no hay kill switch, ni VaR de portafolio, ni sizing por defecto. (3) Curva de aprendizaje que excluye al 95% del retail. |
| **GAP** | **4/10** — **no competir en infraestructura de research.** Competir en la capa de decisión y riesgo que ellos deliberadamente dejan vacía. |

#### Alpaca (broker API-first)

| | |
|---|---|
| **Fortalezas** | (1) Ejecución barata y API limpia. (2) Datos de mercado incluidos. (3) Fricción regulatoria resuelta. |
| **Debilidades explotables** | (1) Es infraestructura de ejecución — no genera señal. (2) Cobertura de activos limitada (equities/crypto US). (3) Sin capa de inteligencia. |
| **GAP** | **3/10** — **no competir; integrarse.** Alpaca es un adaptador de ejecución más, no un rival. |

#### MetaTrader Expert Advisors (ecosistema MQL5)

| | |
|---|---|
| **Fortalezas** | (1) Base instalada gigantesca en forex/CFD retail. (2) Ejecución integrada con cientos de brokers. (3) Coste marginal cero para el usuario final. |
| **Debilidades explotables** | (1) El marketplace de EAs es un mercado de limones: los backtests publicados son casi universalmente sobreajustados (mismo fenómeno cuantificado en la Sección 0.2, sin ninguna corrección). (2) MQL5 no tiene stack de ML moderno. (3) Sin gestión de portafolio cross-asset ni control de correlación. |
| **GAP** | **9/10** — es el competidor más grande y el más vulnerable en el eje exacto donde TRADER AI puede ser riguroso. |

#### Fondos cuantitativos "Renaissance-inspired" retail (Numerai, replicadores de factores, hedge fund copy-trading)

| | |
|---|---|
| **Fortalezas** | (1) Metodología estadística genuina (Numerai: meta-modelo sobre miles de submissions, ejemplo canónico de la Salida B de la Sección 0.3). (2) Datos limpios y neutralizados. (3) Credibilidad académica. |
| **Debilidades explotables** | (1) Numerai no le da al usuario un sistema operable sobre *sus propios* activos. (2) Los replicadores de factores no son ejecutables intradía ni multiactivo. (3) Opacidad: el usuario no ve ni controla el riesgo. |
| **GAP** | **6/10** — competir en operabilidad y transparencia (XAI, ya implementado en `core/signals/xai_module.py`), no en poder de modelado. |

### 1.3 Tabla de posicionamiento estratégico

| Dimensión | 3Commas | Cryptohopper | QuantConnect | Alpaca | MT5 EAs | Quant retail | **Posición TRADER AI** |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| UX / onboarding | ●●● | ●●● | ○ | ●● | ●● | ● | **No competir** |
| Amplitud de exchanges | ●●● | ●●● | ●● | ● | ●●● | ○ | Paridad (5 adaptadores ya) |
| Calidad/profundidad de datos | ● | ● | ●●● | ●● | ● | ●●● | **Brecha crítica a cerrar** (S8-S1) |
| Rigor estadístico OOS | ○ | ○ | ●● | ○ | ○ | ●●● | **GANAR** — DSR/PBO/CPCV |
| Riesgo de portafolio (CVaR, ρ) | ○ | ○ | ○ | ○ | ○ | ●● | **GANAR** — ya construido |
| Multiactivo real cross-class | ○ | ○ | ●●● | ● | ●● | ● | **GANAR** — 4 clases operativas |
| Explicabilidad de la señal | ○ | ○ | ● | ○ | ○ | ○ | **GANAR** — SHAP por señal |
| Fail-safe / kill switch | ○ | ● | ○ | ○ | ○ | ○ | **GANAR** — fail-closed verificado |
| Coste de ejecución/infra | ●●● | ●●● | ●● | ●●● | ●●● | ●● | Paridad |

**Conclusión de posicionamiento.** TRADER AI no puede ni debe competir en UX, distribución o infraestructura de research. Su territorio defendible es la intersección de cuatro cosas que **ningún competidor retail ofrece junto**: (i) honestidad estadística exigible y auditable, (ii) riesgo de portafolio cross-asset, (iii) explicabilidad por señal, (iv) fail-safe con precedencia absoluta. Las cuatro ya existen en el código. La única que **no** existe y bloquea a las otras tres es la profundidad de datos.

**Advertencia estratégica derivada de la Sección 0:** el diferenciador "honestidad estadística" solo es defendible si el propio sistema la aplica a sí mismo. Hoy el Gate I1 reporta un PASS que no sobrevive a la deflación. Publicar ese PASS como evidencia de edge destruiría exactamente el activo diferencial que se pretende construir.

---

## SECCIÓN 2 — Ventaja competitiva en feature engineering

### 2.0 Principio rector

Cada feature añadida es un grado de libertad adicional en el espacio de búsqueda; por la Sección 0.2, cada grado de libertad eleva $E[\max SR|H_0]$. Por lo tanto **toda feature de esta sección debe pasar un test de admisión antes de entrar al modelo**, no después:

$$\text{Admitir } f \iff \text{IC}(f) = \text{corr}_{\text{Spearman}}(f_t,\, r_{t+h}) \text{ con } |t\text{-stat}| > 3 \text{ en } \geq 60\% \text{ de los activos del panel}$$

El umbral de |t| > 3 (no 2) es deliberado: con ~50 features candidatas, el umbral de 2 produce ~2.5 falsos positivos por construcción (Harvey, Liu & Zhu, 2016, "…and the Cross-Section of Expected Returns" — argumentan t > 3.0 como mínimo tras corrección por multiplicidad).

Notación: $p_t$ precio, $r_t = \ln(p_t/p_{t-1})$, $V_t$ volumen, $h$ horizonte de predicción en barras.

---

### Capa 1 — Microestructura avanzada

Implementación objetivo: `core/features/microstructure.py` (nuevo), consumido por `core/agents/microstructure_agent.py` (existente).

#### 1.1 Order Flow Imbalance (OFI)

$$OFI_t = \sum_{i \in t} \left[ \mathbb{1}_{\{P^b_i \geq P^b_{i-1}\}} q^b_i - \mathbb{1}_{\{P^b_i \leq P^b_{i-1}\}} q^b_{i-1} - \mathbb{1}_{\{P^a_i \leq P^a_{i-1}\}} q^a_i + \mathbb{1}_{\{P^a_i \geq P^a_{i-1}\}} q^a_{i-1} \right]$$

donde $P^b, q^b$ son precio y tamaño del mejor bid; $P^a, q^a$ del mejor ask.

| Propiedad | Valor |
|---|---|
| Horizonte óptimo | 1–30 segundos; degrada a ruido más allá de 5 minutos |
| Clase de activo | **Crypto perpetuos** (order book público y profundo vía Binance/Bybit WS) |
| Correlación esperada | R² ≈ 0.65 contra cambio de precio contemporáneo (Cont, Kukanov & Stoikov, 2014); IC predictivo a 1 min ≈ 0.03–0.06 |
| **Aplicabilidad a TRADER AI** | ⚠️ **Baja en el diseño actual.** El pipeline opera en barras de 1h. Un feature con vida media de segundos agregado a 1h conserva casi nada de información. Solo tiene sentido si se añade un pipeline de ejecución intradía. |

#### 1.2 VPIN (Volume-Synchronized Probability of Informed Trading)

$$VPIN = \frac{\sum_{\tau=1}^{n} |V^{buy}_\tau - V^{sell}_\tau|}{n \cdot V}$$

sobre $n$ buckets de volumen fijo $V$; clasificación buy/sell por regla de tick o Bulk Volume Classification.

| Propiedad | Valor |
|---|---|
| Horizonte | 1–24 horas (VPIN es un indicador de *toxicidad*, no direccional) |
| Clase de activo | Crypto y futuros de índices |
| Uso correcto | **Filtro de riesgo, no señal direccional.** VPIN > percentil 90 histórico → reducir tamaño o suprimir entradas |
| Correlación esperada | Con volatilidad realizada futura: ρ ≈ 0.35–0.50; con retorno direccional: ≈ 0 |
| Integración | `core/risk/adaptive_position_risk.py` como multiplicador de sizing, y como feature del Isolation Forest (S4, Modelo 4) |

#### 1.3 Kyle's Lambda (impacto de precio)

$$\Delta p_t = \lambda \cdot S_t + \varepsilon_t, \qquad S_t = \sum_i \text{sign}(q_i)\,|q_i|$$

$\lambda$ estimado por OLS rodante de 100 barras. Alto $\lambda$ = mercado ilíquido, alto coste de ejecución.

| Propiedad | Valor |
|---|---|
| Horizonte | Estado (no predicción); ventana de estimación 100 barras |
| Clase de activo | Todas; más discriminante en altcoins y commodities poco líquidos |
| Uso | **Entra directamente al cost model** (`core/backtesting/costs.py`): slippage esperado = $\lambda \times$ tamaño de orden. Hoy el slippage es una constante — esto es un upgrade de realismo del backtest, que es la Sección 6 |
| Correlación esperada | Con slippage realizado: ρ ≈ 0.55–0.70 |

#### 1.4 Efectividad del spread (Roll + Corwin-Schultz)

Cuando no hay order book (forex vía OANDA/MT5, índices), estimar el spread efectivo desde OHLC:

$$S_{CS} = \frac{2(e^{\alpha}-1)}{1+e^{\alpha}}, \quad \alpha = \frac{\sqrt{2\beta}-\sqrt{\beta}}{3-2\sqrt{2}} - \sqrt{\frac{\gamma}{3-2\sqrt{2}}}$$

con $\beta = E[(\ln(H_t/L_t))^2 + (\ln(H_{t+1}/L_{t+1}))^2]$ y $\gamma = (\ln(H_{t,t+1}/L_{t,t+1}))^2$ (Corwin & Schultz, 2012).

| Propiedad | Valor |
|---|---|
| Horizonte | Estado, ventana 2 barras |
| Clase de activo | **Forex, índices, commodities** — exactamente donde TRADER AI no tiene order book |
| Uso | Validar el `spread_pips` hardcodeado del cost model contra el spread implícito real. **Alta prioridad**: si el cost model subestima el spread, todos los Sharpe netos del Gate I1 están inflados |

#### 1.5 Amihud Illiquidity

$$ILLIQ_t = \frac{1}{D}\sum_{d=1}^{D} \frac{|r_d|}{\text{VolumeUSD}_d}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 20–60 días (factor de riesgo, no señal táctica) |
| Clase de activo | Crypto (altcoins), acciones small/mid cap |
| Correlación esperada | Prima de iliquidez documentada: +0.3 a +0.5% mensual por decil (Amihud, 2002) |

---

### Capa 2 — Régimen y persistencia

Implementación objetivo: extender `core/features/hurst_engine.py` (existente) y `core/adaptation/hmm_regime_detector.py`.

#### 2.1 Exponente de Hurst (R/S y DFA)

$$E\left[\frac{R(n)}{S(n)}\right] = C n^H \implies H = \frac{\ln(R/S)}{\ln n} \text{ por regresión sobre múltiples } n$$

Se recomienda **DFA (Detrended Fluctuation Analysis)** sobre R/S clásico por robustez ante no-estacionariedad:

$$F(n) = \sqrt{\frac{1}{N}\sum_{t=1}^{N}[y(t) - y_n(t)]^2} \sim n^{H}$$

| Propiedad | Valor |
|---|---|
| Horizonte | Ventana de estimación 250–500 barras; el régimen persiste 20–100 barras |
| Interpretación | H > 0.55 → tendencial (usar momentum); H < 0.45 → reversión (usar mean-reversion); 0.45–0.55 → **no operar** |
| Clase de activo | Todas; es el feature que responde a la Investigación **I5** del plan maestro |
| Correlación esperada | H no predice retorno; predice *qué estrategia funciona*. Mejora documentada de Sharpe al condicionar estrategia por H: +0.2 a +0.4 |
| **Prioridad** | **Alta.** Es el feature de mayor ratio valor/coste del catálogo: ya está implementado y responde a una pregunta abierta del roadmap |

#### 2.2 Dimensión fractal (Higuchi)

$$D = 2 - H, \qquad L(k) \sim k^{-D}$$

Redundante con Hurst por construcción. **Recomendación: no implementar como feature separado** — añade un grado de libertad sin información nueva. Incluido aquí para dejar constancia de la decisión.

#### 2.3 Exponente de Lyapunov simplificado (Rosenstein)

$$\lambda_1 \approx \frac{1}{\Delta t}\left\langle \ln \frac{d_j(i)}{d_j(0)} \right\rangle$$

| Propiedad | Valor |
|---|---|
| Horizonte | Ventana 500+ barras |
| Uso realista | **Filtro de "predecibilidad disponible"**: $\lambda_1$ alto → el horizonte de predicción útil es corto → reducir $h$ o desactivar |
| Advertencia honesta | La estimación de Lyapunov sobre series financieras ruidosas es notoriamente inestable. **Recomendación: implementar en modo shadow, no en producción, hasta que I2 confirme IC significativo.** |

#### 2.4 Estructura de autocorrelación multi-ventana

$$\rho_k = \text{corr}(r_t, r_{t-k}), \quad k \in \{1, 2, 3, 5, 10, 21\}$$
$$VR(q) = \frac{\text{Var}(r_t^{(q)})/q}{\text{Var}(r_t)} \quad \text{(Lo & MacKinlay Variance Ratio)}$$

| Propiedad | Valor |
|---|---|
| Horizonte | $h = k$ (autoconsistente) |
| Clase de activo | Forex e índices (mean-reversion intradía documentada); crypto en 1h muestra ρ₁ < 0 persistente |
| Correlación esperada | ρ₁ típico: −0.02 a −0.05 en 1h; VR(5) < 1 confirma reversión |
| Ventaja sobre Hurst | Da el **horizonte específico** de la reversión, no solo su existencia |

---

### Capa 3 — Volatilidad multidimensional

#### 3.1 Estimadores de volatilidad eficientes en OHLC

**Parkinson** (usa rango, ~5× más eficiente que close-to-close):
$$\sigma^2_{P} = \frac{1}{4n\ln 2}\sum_{i=1}^{n}\left(\ln\frac{H_i}{L_i}\right)^2$$

**Garman-Klass**:
$$\sigma^2_{GK} = \frac{1}{n}\sum \left[\frac{1}{2}\left(\ln\frac{H_i}{L_i}\right)^2 - (2\ln 2 - 1)\left(\ln\frac{C_i}{O_i}\right)^2\right]$$

**Yang-Zhang** (el recomendado — maneja gaps y drift):
$$\sigma^2_{YZ} = \sigma^2_{overnight} + k\,\sigma^2_{open\text{-}close} + (1-k)\,\sigma^2_{RS}, \quad k = \frac{0.34}{1.34 + \frac{n+1}{n-1}}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 1–20 barras |
| Clase de activo | **Índices y commodities** (gaps de sesión relevantes); crypto se beneficia menos (24/7 sin gaps) |
| Ganancia esperada | Reducción de ~60–80% en varianza del estimador vs. close-to-close para el mismo n → **sizing más estable, menos churn de posición** |
| **Prioridad** | **Alta y barata.** Reemplaza directamente el ATR actual en `core/risk/mtf_sl_tp_manager.py` y resuelve de paso la deuda #10 del plan maestro (ATR duplicado) |

#### 3.2 GARCH(1,1) forecast

$$\sigma^2_t = \omega + \alpha \varepsilon^2_{t-1} + \beta \sigma^2_{t-1}, \qquad \alpha + \beta < 1$$
$$E_t[\sigma^2_{t+k}] = \sigma^2_{LR} + (\alpha+\beta)^k(\sigma^2_t - \sigma^2_{LR}), \quad \sigma^2_{LR} = \frac{\omega}{1-\alpha-\beta}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 1–10 barras (la predictibilidad de vol decae con $(\alpha+\beta)^k$) |
| Clase de activo | Todas; $\alpha+\beta$ típico 0.95–0.99 en crypto, 0.90–0.97 en FX |
| Uso | **Denominador del sizing** (volatility targeting) y umbral dinámico de SL/TP |
| Correlación esperada | Con vol realizada futura: ρ ≈ 0.6–0.75. Con retorno: ≈ 0 |
| Librería | `arch` (Kevin Sheppard) — `arch_model(r, vol='GARCH', p=1, q=1, dist='skewt')` |

#### 3.3 Volatilidad realizada vs. implícita (VRP)

$$VRP_t = IV_t - RV_t, \qquad RV_t = \sqrt{\frac{252}{n}\sum r_i^2}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 5–21 días |
| Clase de activo | **Índices** (VIX disponible), oro (GVZ), petróleo (OVX), crypto (DVOL de Deribit) |
| Correlación esperada | VRP alto (IV >> RV) → prima de riesgo positiva para vendedores de vol; asociado a retornos futuros positivos en índices con IC ≈ 0.05–0.08 a 21 días (Bollerslev, Tauchen & Zhou, 2009) |
| **Nota de viabilidad** | Requiere fuente de IV. Deribit DVOL y CBOE VIX son gratuitos vía API. **Feature de alto valor y baja fricción de datos.** |

#### 3.4 Detección de saltos (Barndorff-Nielsen & Shephard)

$$BV_t = \frac{\pi}{2}\sum_{i=2}^{n}|r_i||r_{i-1}|, \qquad J_t = \max(RV_t - BV_t,\ 0)$$

Estadístico de test: $Z_t = \frac{(RV_t - BV_t)/RV_t}{\sqrt{(\frac{\pi^2}{4}+\pi-5)\frac{1}{n}\max(1, \frac{TQ_t}{BV_t^2})}} \sim N(0,1)$

| Propiedad | Valor |
|---|---|
| Horizonte | Evento puntual; efecto sobre vol futura 1–5 barras |
| Clase de activo | Todas; especialmente crypto (liquidaciones en cascada) y FX (eventos macro) |
| Uso | (1) Feature de régimen. (2) **Trigger del kill switch**: salto con Z > 4 → suspender nuevas entradas 3 barras |
| Correlación esperada | Post-salto: aumento de vol de 40–120% durante 2–5 barras; retorno direccional ≈ 0 (no operar el salto, sobrevivirlo) |

---

### Capa 4 — Cross-asset e información macro

Esta capa es la que **materialmente diferencia** a TRADER AI de todo competidor retail crypto-only, y es barata: los datos son públicos y diarios.

#### 4.1 DXY influence score por activo

$$\beta^{DXY}_{i,t} = \frac{\text{Cov}_{60}(r_i, r_{DXY})}{\text{Var}_{60}(r_{DXY})}, \qquad \text{Score}_{i,t} = -\beta^{DXY}_{i,t} \cdot z(r^{(5)}_{DXY})$$

| Propiedad | Valor |
|---|---|
| Horizonte | 1–10 días |
| Clase de activo | **XAUUSD (β ≈ −0.6 a −0.9), commodities USD-denominadas, EM FX** |
| Correlación esperada | Oro vs DXY: ρ ≈ −0.45 histórica, con regímenes donde llega a −0.8 |
| Nota | XAUUSD es el único activo que "pasa" el gate hoy. Este es el feature con mayor probabilidad a priori de aportarle información real |

#### 4.2 Estructura temporal del VIX

$$TS_t = \frac{VIX3M_t}{VIX_t} - 1$$

| Propiedad | Valor |
|---|---|
| Horizonte | 5–21 días |
| Clase de activo | **US500, US30, NAS100** (y crypto por correlación de riesgo desde 2020) |
| Interpretación | ⚠️ **CORREGIDA tras la medición del Anexo C.** Esta tabla afirmaba: "TS < 0 (backwardation) → estrés → reducir exposición", con backwardation prediciendo retornos *negativos*. **Los datos dicen lo contrario, con enorme significancia.** Medido sobre 20 años de VIX/VIX3M reales: IC(Spearman) = **−0.128** a 21 días, **t = −9.11**, n = 5.023. La backwardation predice retornos futuros **más altos** (+17.1% anualizado en el quintil de backwardation vs. +6.9% en contango alto). El mecanismo es el clásico contrarian: la backwardation ocurre *durante* el pánico, y los retornos posteriores al pánico son altos |
| Correlación medida | **IC = −0.050 (h=1d, t=−3.52) · −0.090 (h=5d, t=−6.39) · −0.128 (h=21d, t=−9.11)** — el IC más alto y más significativo de todo el catálogo, confirmado empíricamente. El signo es el opuesto al que esta propuesta asumía |
| **Prioridad** | **Máxima, confirmada.** Dato gratuito (CBOE), ya descargado en `data/raw/VIX_1d.parquet` y `VIX3M_1d.parquet`. **Uso correcto: señal contrarian de compra, no filtro de riesgo direccional.** Sigue siendo válido como filtro de *tamaño* (la volatilidad futura sí sube en backwardation), pero no debe suprimir posiciones largas |

#### 4.3 Señal de credit spread

$$CS_t = \text{HY OAS}_t - \text{IG OAS}_t, \qquad \text{Señal} = -z_{252}(\Delta_5 CS_t)$$

| Propiedad | Valor |
|---|---|
| Horizonte | 10–60 días |
| Clase de activo | Índices, crypto (proxy de apetito de riesgo global) |
| Fuente | FRED (`BAMLH0A0HYM2`, `BAMLC0A0CM`) — gratuita |
| Correlación esperada | Ampliación de HY OAS lidera caídas de equity con 5–15 días de anticipación; IC ≈ 0.06–0.10 |

#### 4.4 Forma de la curva de tipos

$$\text{Slope} = y_{10Y} - y_{2Y}, \quad \text{Curvature} = 2y_{10Y} - y_{2Y} - y_{30Y}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 20–120 días (feature de régimen lento) |
| Clase de activo | Índices, oro, USD FX |
| Correlación esperada | Slope negativa → recesión con lag de 12–18 meses; con 2–3 años de datos **este feature es inutilizable** (menos de 2 observaciones de ciclo) |
| **Decisión** | **No incluir hasta tener ≥10 años de historia.** Ejemplo concreto de por qué la Salida A de la Sección 0.3 es prerequisito de esta capa |

#### 4.5 Correlaciones commodity-divisa

$$\rho^{roll}_{60}(\text{AUDUSD}, \text{XAUUSD}), \quad \rho^{roll}_{60}(\text{USDCAD}, \text{USOIL}), \quad \rho^{roll}_{60}(\text{USDNOK}, \text{UKOIL})$$

| Propiedad | Valor |
|---|---|
| Horizonte | 1–10 días |
| Uso | (1) Señal de dislocación: cuando el z-score del residuo supera ±2, hay convergencia esperada. (2) **Control de riesgo**: dos posiciones con ρ > 0.7 no son diversificación |
| Correlación esperada | AUD-Oro: ρ ≈ 0.4–0.6; CAD-Oil: ρ ≈ 0.5–0.7 |

---

### Capa 5 — Sentimiento cuantificado

#### 5.1 Score NLP de noticias

Arquitectura recomendada: FinBERT (o `distilroberta-financial-sentiment`) sobre titulares, agregado por activo:

$$S_{i,t} = \frac{\sum_{j \in \mathcal{N}_{i,t}} w_j \cdot (p^{pos}_j - p^{neg}_j)}{\sum_j w_j}, \quad w_j = e^{-\delta (t - t_j)} \cdot \text{relevancia}_j$$

| Propiedad | Valor |
|---|---|
| Horizonte | 1–3 días (el efecto se disipa rápido; la sorpresa es lo que importa, no el nivel) |
| Clase de activo | Acciones > crypto > índices > FX |
| Correlación esperada | Con retorno a 1 día: IC ≈ 0.02–0.05 — **bajo**. El valor está en la *dispersión* del sentimiento como proxy de vol futura (IC ≈ 0.10 vs. vol) |
| **Coste/beneficio** | Alto coste (infra de ingesta + inferencia), bajo IC direccional. **Prioridad baja.** Implementar después de las Capas 2–4 |

#### 5.2 Funding rate en perpetuos (crypto)

$$F_t = \text{clamp}(P_{premium} + \text{clamp}(I - P_{premium}, \pm 0.05\%),\ \pm 0.75\%)$$
$$\text{Señal}_t = -z_{168h}(F_t) \quad \text{(contrarian al posicionamiento apalancado)}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 8–72 horas |
| Clase de activo | **Crypto perpetuos exclusivamente** |
| Correlación esperada | Funding en percentil >95 → retorno a 24h negativo, IC ≈ 0.05–0.09; el efecto es **asimétrico**: mucho más fuerte en el extremo largo (apalancamiento long saturado) que en el corto |
| Disponibilidad | ⚠️ **Corregido tras validación:** los clientes cubren perpetuos, pero `ExchangeAdapter` (`core/ingestion/exchange_adapter.py`) **no expone ningún método de funding rate ni de open interest** — su superficie es `get_klines`, `get_order_book`, `get_balance`, `place_order`, `cancel_order`, `get_order_status`. Requiere extender la interfaz (~8h). Ver §B.6 |
| **Prioridad** | **Máxima para crypto**, condicionada a esa extensión. Es señal, filtro de riesgo y base de la Estrategia C2 simultáneamente |

#### 5.3 Toxicidad de flujo desde social media

Volumen y polaridad de menciones (X/Reddit) normalizados:
$$T_t = z_{30d}(\text{mentions}_t) \times \text{sign}(\text{polarity}_t)$$

| Propiedad | Valor |
|---|---|
| Horizonte | 1–5 días |
| Correlación esperada | Picos extremos de menciones son **contrarian** en altcoins (IC ≈ −0.04 a −0.08); en BTC el efecto es débil |
| Advertencia | Alta contaminación por bots; requiere filtrado agresivo. **Prioridad baja** por ratio señal/esfuerzo |

#### 5.4 COT Report positioning

$$\text{NetPos}_t = \frac{\text{Long}^{NC}_t - \text{Short}^{NC}_t}{\text{OI}_t}, \qquad \text{COT Index} = \frac{\text{NetPos}_t - \min_{156w}}{\max_{156w} - \min_{156w}}$$

| Propiedad | Valor |
|---|---|
| Horizonte | 2–8 semanas |
| Clase de activo | **Commodities (oro, petróleo, gas) y FX de futuros** |
| Correlación esperada | COT Index > 90 (posicionamiento especulativo extremo) → retorno a 4 semanas negativo, IC ≈ 0.06–0.10 |
| Restricción | Publicación semanal con 3 días de lag (viernes, datos del martes). **El lag debe modelarse explícitamente o se introduce look-ahead** |
| Requisito de span | Un COT Index de 156 semanas necesita **3 años solo para inicializarse**. Otro caso donde la Salida A es prerequisito |

---

### 2.6 Priorización del catálogo — matriz valor/esfuerzo

| Feature | IC esperado | Esfuerzo | Datos disponibles hoy | Prioridad |
|---|:---:|:---:|:---:|:---:|
| Yang-Zhang vol | Indirecto (sizing) | Bajo | ✅ | **P0** |
| Hurst / DFA (ya existe) | Indirecto (selección) | Ya hecho | ✅ | **P0** |
| VIX term structure | 0.08–0.12 | Bajo | ⚠️ requiere ingesta CBOE | **P0** |
| Funding rate crypto | 0.05–0.09 | Bajo | ✅ | **P0** |
| GARCH(1,1) | Indirecto (sizing) | Bajo | ✅ | **P1** |
| Corwin-Schultz spread | Valida cost model | Bajo | ✅ | **P1** |
| DXY influence | 0.04–0.08 | Bajo | ⚠️ requiere DXY | **P1** |
| Credit spread (FRED) | 0.06–0.10 | Bajo | ❌ nueva fuente | **P1** |
| Autocorrelación / VR | 0.03–0.06 | Bajo | ✅ | **P1** |
| Jump detection | Indirecto (riesgo) | Medio | ✅ | **P2** |
| VPIN | Riesgo | Medio | ✅ crypto | **P2** |
| COT Index | 0.06–0.10 | Medio | ❌ + 3 años init | **P2** |
| Kyle's lambda | Cost model | Medio | ⚠️ | **P2** |
| OFI | 0.03–0.06 @ 1min | Alto | ⚠️ requiere pipeline tick | **P3** |
| NLP noticias | 0.02–0.05 | Alto | ❌ | **P3** |
| Social toxicity | 0.04–0.08 | Alto | ❌ | **P3** |
| Yield curve | n/d con 2 años | Bajo | ❌ | **Bloqueado** |
| Lyapunov | Incierto | Alto | ✅ | **Shadow only** |
| Fractal dimension | Redundante | — | — | **Descartado** |

**Regla de admisión operativa:** ninguna feature P2/P3 entra al modelo antes de que las P0/P1 hayan pasado el test de IC del §2.0 sobre el panel completo. Esto es el presupuesto de multiplicidad de la Sección 6 aplicado al feature engineering.

---

## SECCIÓN 3 — Playbook de estrategias por activo y régimen

### 3.0 Advertencia sobre las métricas de esta sección

Todas las métricas de performance listadas abajo son **priors derivados de literatura académica y de rangos publicados para estrategias de la misma familia**, no resultados de backtest de TRADER AI. Se marcan explícitamente como priors por una razón metodológica: la Sección 0 demostró que el backtesting actual no puede producir estimaciones fiables sobre 2 años de datos. Presentar un Sharpe backtested como si fuera una expectativa sería reproducir exactamente el error que esta propuesta busca corregir.

**Uso correcto de estos priors:** son el punto de partida bayesiano contra el que se compara el backtest. Si un backtest produce Sharpe 3.0 donde el prior de la literatura es 0.5–0.9, la conclusión correcta no es "encontramos algo excepcional" sino "el backtest está sobreajustado". Esta comparación prior-vs-backtest debe ser un check automatizado del gate (Sección 6.5).

### 3.0.1 Presupuesto de estrategias

El sistema **no debe operar 12 estrategias**. Cada estrategia activa es un ensayo adicional en el cálculo de $E[\max SR|H_0]$.

**Corrección introducida tras la validación del Anexo B.** La formulación original de este presupuesto era `N_estrategias ≤ 4`, y es incorrecta: el coste de multiplicidad no lo genera el número de estrategias sino el **número de configuraciones evaluadas para seleccionarlas**. Una estrategia con cero parámetros libres (p. ej. la descomposición overnight del §B.3) añade 1 ensayo; una con un grid de 3×3 añade 9. El presupuesto correcto es sobre ensayos:

$$N_{ensayos\ totales} \leq 40 \text{ en todo el sistema}, \qquad E[\max SR \mid H_0] \Big|_{N=40,\ Y=10} = \mathbf{0.69}$$

Con 10 años de span (Sprint 1) y 40 ensayos, el umbral de ruido baja de 1.73 a **0.69** — por debajo del objetivo de Sharpe. Es la combinación de más span *y* menos búsqueda la que hace medible el sistema; ninguna de las dos basta por separado.

Esto tiene una consecuencia favorable que la formulación anterior ocultaba: **añadir estrategias de bajo coste paramétrico y baja correlación es casi gratis en términos de multiplicidad, y sube el Sharpe agregado** (§B.5). Las estrategias por debajo del corte se mantienen en shadow mode (calculan señal, no ejecutan) para acumular track record out-of-sample real, que es la única forma legítima de promoverlas.

---

### 3.1 CRIPTOMONEDAS (BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT)

**Contexto estructural.** El mercado crypto tiene tres propiedades explotables que no comparte ningún otro activo del universo: (i) mercado 24/7 sin gaps, (ii) apalancamiento retail masivo y observable vía funding rate, (iii) datos on-chain que revelan posicionamiento real, no encuestado.

#### Estrategia C1 — Momentum fraccionado adaptativo (TSMOM condicionado por Hurst)

**Lógica.** El momentum de series temporales (Moskowitz, Ooi & Pedersen, 2012) tiene edge documentado a 1–12 meses en 58 instrumentos. Su debilidad es que colapsa en régimen de reversión. La adaptación propuesta: condicionar la activación al exponente de Hurst y escalar la exposición continuamente en vez de binariamente.

```python
# Estrategia C1 — Momentum fraccionado adaptativo
# Timeframe: 4h señal / 1d confirmación. Horizonte de tenencia: 3-15 días.

def signal_c1(df, params):
    H       = hurst_dfa(df.close, window=params.hurst_window)      # Capa 2.1
    mom     = df.close.pct_change(params.lookback)
    vol     = yang_zhang(df, window=params.vol_window)             # Capa 3.1
    funding = df.funding_rate                                       # Capa 5.2

    # 1. Gate de régimen: solo operar donde hay persistencia medida
    if H < params.h_min:                    # típico 0.55
        return 0

    # 2. Señal continua normalizada por volatilidad (NO binaria)
    raw = mom / (vol * sqrt(params.lookback))
    sig = clip(raw / params.scale, -1, +1)

    # 3. Veto por funding extremo (posicionamiento saturado = riesgo de squeeze)
    if sig > 0 and z_score(funding, 168) > params.funding_veto:     # típico +2.0
        sig *= 0.3
    if sig < 0 and z_score(funding, 168) < -params.funding_veto:
        sig *= 0.3

    # 4. Veto por salto reciente (Capa 3.4)
    if jump_detected(df, z_thresh=4.0, lookback=3):
        return 0

    return sig

# SALIDA: inversión de signo, o H cae bajo h_min, o stop = 2.5 x ATR(YZ),
#         o time-stop a params.max_hold barras.
```

| Parámetro | Rango de optimización | Default sugerido | Nota |
|---|---|---|---|
| `lookback` | 30–180 barras (4h) | 90 (≈15 días) | Rango deliberadamente grueso: 5 valores, no 50 |
| `hurst_window` | 250–500 | 400 | |
| `h_min` | 0.52–0.58 | 0.55 | |
| `vol_window` | 20–60 | 30 | |
| `funding_veto` | 1.5–2.5 | 2.0 | |
| `max_hold` | 60–120 barras | 90 | |

**Filtro de régimen requerido:** H > 0.55 **y** VIX term structure en contango (Capa 4.2) — la correlación BTC-SPX desde 2020 hace que el estrés de equity domine al momentum crypto.

| Métrica (prior de literatura) | Rango esperado |
|---|---|
| Sharpe neto | **0.5 – 0.9** |
| Sortino | 0.7 – 1.3 |
| Max DD | 18 – 30% |
| Win rate | **38 – 45%** (momentum gana poco y frecuente pierde) |
| Profit factor | 1.15 – 1.45 |
| R:R mínimo aceptable | **2.5:1** — obligatorio: con WR 40%, un R:R de 1.5 da esperanza negativa |
| Frecuencia | 15–30 señales/año por activo |

**Regímenes donde NO usar:** H < 0.50 (bear market lateral prolongado); backwardation de VIX; funding rate en percentil >97 sostenido más de 3 días (típico de blow-off top); primeras 48h tras un halving (dislocación de flujo, no señal).

---

#### Estrategia C2 — Basis / funding rate arbitrage (perp vs. spot)

**Lógica.** El perpetuo cotiza con un premium sobre spot que se paga vía funding cada 8h. Cuando el funding anualizado supera sustancialmente el coste de capital, existe un carry capturable: **long spot + short perpetual**, delta-neutral, cobrando funding.

$$\text{Carry anualizado} = F_{8h} \times 3 \times 365, \qquad \text{Basis} = \frac{P_{perp} - P_{spot}}{P_{spot}}$$

```python
# Estrategia C2 — Cash-and-carry sobre funding
# Delta-neutral. Sin exposición direccional. Timeframe: 8h (ciclo de funding).

ENTRY:
    carry_ann = funding_8h * 3 * 365
    if carry_ann > params.carry_min           # típico 12% anualizado
       and basis > 0
       and vpin < percentile(vpin, 85)         # Capa 1.2: evitar mercados tóxicos
       and margin_ratio_projected < 0.4:       # solvencia ante mecha de 40%
        open_long_spot(size)
        open_short_perp(size)                  # mismo notional, delta ≈ 0

EXIT:
    if carry_ann < params.carry_exit           # típico 4%
       or basis < 0                            # inversión: ahora se paga funding
       or margin_ratio > 0.6                   # desapalancar ANTES de liquidación
       or days_held > params.max_days:
        close_both_legs_simultaneously()       # crítico: nunca dejar una pata sola

RISK:
    - Rebalanceo de delta cada 8h si |delta| > 2% del notional
    - Reserva de margen: mínimo 3x el margen inicial del short perp
    - Límite duro: ≤ 25% del capital total en carry simultáneo
```

| Parámetro | Rango | Default |
|---|---|---|
| `carry_min` | 8–20% anual | 12% |
| `carry_exit` | 2–6% | 4% |
| `max_days` | 7–45 | 21 |
| Margin buffer | 2.5×–4× | 3× |

| Métrica (prior) | Rango esperado |
|---|---|
| Sharpe neto | **1.2 – 2.2** (alto: es carry, no direccional) |
| Max DD | 4 – 12% (dominado por eventos de basis blowout) |
| Win rate | **75 – 88%** |
| Profit factor | 1.8 – 3.0 |
| Frecuencia | 6–15 entradas/año por activo |
| Capacidad | Limitada por el margen, no por la liquidez |

**El riesgo real de esta estrategia no es el que parece.** El Sharpe alto y el win rate del 85% ocultan una distribución con cola izquierda severa: el modo de fallo es la liquidación de la pata corta durante una mecha alcista violenta, que convierte una estrategia "sin riesgo direccional" en una pérdida del 100% de la posición. **Por eso el buffer de margen de 3× y el límite del 25% del capital son no negociables, no parámetros optimizables.** Esta es exactamente la estrategia que un competidor retail vendería como "market neutral" sin explicar el riesgo de cola — y donde la transparencia de TRADER AI es un diferencial vendible.

**Regímenes donde NO usar:** durante desapalancamiento sistémico (funding negativo extremo); si el exchange muestra estrés de retiros; con menos de 3× margen disponible.

---

#### Estrategia C3 — Divergencias on-chain

**Métricas relevantes y su lógica:**

| Métrica | Fórmula | Interpretación | Horizonte |
|---|---|---|---|
| **SOPR** | $\frac{\text{Precio de venta}}{\text{Precio de compra}}$ agregado | SOPR < 1 sostenido → capitulación (los holders venden en pérdida) | 2–8 semanas |
| **NUPL** | $\frac{\text{MarketCap} - \text{RealizedCap}}{\text{MarketCap}}$ | > 0.75 euforia; < 0 capitulación | 1–6 meses |
| **Exchange netflow** | $\sum \text{in} - \sum \text{out}$ | Inflow neto grande → presión de venta inminente | 3–14 días |
| **MVRV Z-score** | $\frac{MC - RC}{\sigma(MC)}$ | > 7 techo de ciclo; < 0 suelo de ciclo | 3–12 meses |

```python
# Estrategia C3 — Overlay on-chain (NO es una estrategia standalone)
# Modula el sizing de C1, no genera entradas propias.

def onchain_multiplier(chain_data, params):
    m = 1.0
    if chain_data.sopr_7d < 1.0 and chain_data.sopr_7d.rising():
        m *= 1.4                                  # capitulación terminando: acumular
    if chain_data.mvrv_z > params.mvrv_top:       # típico 6.0
        m *= 0.4                                  # zona de techo: reducir
    if z_score(chain_data.exchange_netflow, 30) > 2:
        m *= 0.6                                  # inflow anómalo: presión vendedora
    return clip(m, 0.3, 1.6)
```

**Integración al pipeline:** como multiplicador de sizing en `core/risk/adaptive_position_risk.py`, no como agente de voto. Razón: las métricas on-chain son de frecuencia diaria y horizonte de semanas-meses; introducirlas como voto en un consenso que decide cada hora produce una señal degenerada (constante durante 168 barras seguidas), que el modelo interpretará como un intercepto y no como información.

**Restricción de datos:** requiere Glassnode/CryptoQuant (~$30–800/mes) o construcción propia desde un nodo. **Prior honesto:** el edge on-chain publicado se ha erosionado significativamente desde 2021 al popularizarse; asumir IC ≈ 0.03–0.06 a 30 días, no más.

---

#### 3.1.4 Filtros de régimen específicos de crypto

| Régimen | Detección | Comportamiento del sistema |
|---|---|---|
| **Bear market prolongado** | Precio < SMA200 en 1d **y** NUPL < 0.25 durante >30 días | Solo C2 (carry). C1 desactivada. Exposición máxima 30% |
| **Ciclo de halving** | Ventana de ±180 días del evento | **No sobreajustar**: solo 3 observaciones históricas. Tratar como feature categórico de baja confianza, nunca como regla dura |
| **Correlación macro alta** | $\rho_{60}(\text{BTC}, \text{SPX}) > 0.6$ | Crypto deja de ser diversificador: aplicar el límite de correlación de la Sección 5.4 tratando BTC y US500 como un solo activo |
| **Blow-off / euforia** | MVRV-Z > 6 **y** funding pct > 95 **y** vol realizada > p90 | Cerrar longs de C1. Prohibir nuevas entradas long. C2 permitida (se beneficia del funding alto) |

---

### 3.2 FOREX (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD)

**Contexto estructural.** FX es el mercado más eficiente del universo cubierto: spreads de 0.1–1.0 pips, liquidez de $7.5B/día, participantes institucionales dominantes. El edge disponible es **estructural** (carry, sesiones, flujo de cobertura), no predictivo. Cualquier backtest de FX con Sharpe > 1.5 debe tratarse como sospechoso por defecto.

#### Estrategia F1 — Carry sistemático con cobertura dinámica

**Lógica.** El carry trade —comprar divisas de alto tipo, vender las de bajo tipo— tiene una de las primas de riesgo mejor documentadas (Lustig & Verdelhan, 2007; Menkhoff et al., 2012). Su modo de fallo es conocido y brutal: retornos con skew negativo severo ("up by the stairs, down by the elevator"). La adaptación propuesta escala la exposición inversamente a la volatilidad global de FX.

$$\text{Carry}_{i} = \frac{r^{f}_{base} - r^{f}_{quote}}{\sigma_i}, \qquad w_i = \frac{\text{Carry}_i}{\sum_j |\text{Carry}_j|} \cdot \Phi(\text{VIX}, \text{FXVol})$$

```python
# Estrategia F1 — Carry con hedge dinámico. Timeframe: 1d. Tenencia: semanas-meses.

def signal_f1(pairs, macro, params):
    # 1. Ranking por carry ajustado a volatilidad
    scores = {p: (rate_diff(p) / yang_zhang_vol(p, 60)) for p in pairs}

    # 2. Long el tercio superior, short el tercio inferior (dollar-neutral)
    longs  = top_n(scores, params.n_legs)
    shorts = bottom_n(scores, params.n_legs)

    # 3. Escalado global por riesgo: el carry muere en crisis
    fx_vol_z = z_score(fx_vol_index, 252)
    scale = 1.0
    if fx_vol_z > params.vol_off_1:  scale = 0.5      # típico +1.0
    if fx_vol_z > params.vol_off_2:  scale = 0.0      # típico +2.0 → flat
    if macro.vix_term_structure < 0: scale *= 0.5     # backwardation

    # 4. Hedge de cola: cuando scale < 1, comprar opciones OTM o
    #    abrir long JPY/CHF (divisas refugio) como cobertura parcial
    if scale < 1.0 and params.enable_haven_hedge:
        add_position("USDJPY", -0.3 * total_exposure)  # short USDJPY = long JPY

    return weights(longs, shorts, scale)
```

| Parámetro | Rango | Default |
|---|---|---|
| `n_legs` | 2–3 pares por lado | 2 |
| `vol_off_1` / `vol_off_2` | 0.8–1.5 / 1.8–2.5 | 1.0 / 2.0 |
| Rebalanceo | semanal / quincenal | semanal |
| Vol target por pierna | 5–10% anual | 7% |

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.4 – 0.8** sin hedge; **0.6 – 1.0** con escalado por vol |
| Skew de retornos | **−0.8 a −1.5** (negativo por diseño) |
| Max DD | 12 – 25% |
| Win rate | 55 – 62% |
| Profit factor | 1.2 – 1.5 |
| Frecuencia | Rebalanceo semanal; ~50 ajustes/año |

**Regímenes donde NO usar:** cualquier episodio de risk-off (VIX > 30); intervención de banco central en la divisa; **el carry es la estrategia que más dinero ha perdido en menos tiempo en la historia del retail FX** — la disciplina del escalado por volatilidad no es opcional.

---

#### Estrategia F2 — Breakout de apertura de sesión

**Lógica.** La transición entre sesiones (Asia→Londres, Londres→NY) concentra flujo institucional. El rango de la sesión previa actúa como referencia; su ruptura con volumen tiende a extender.

```python
# Estrategia F2 — Session breakout. Timeframe: 15m/1h. Tenencia: intradía.

# Definición exacta del rango:
#   ASIA_RANGE  = [min(low), max(high)] de 00:00–07:00 UTC
#   LONDON_OPEN = 07:00 UTC (08:00 BST)
#   NY_OPEN     = 13:30 UTC

def signal_f2(df, calendar, params):
    rng_hi, rng_lo = asia_range(df)
    rng_width = (rng_hi - rng_lo) / atr_yz(df, 14)

    # 1. El rango debe ser COMPRIMIDO: un rango ancho ya agotó el movimiento
    if rng_width > params.max_range_atr:        # típico 1.2
        return 0

    # 2. Bloqueo de noticias — regla dura, no parámetro
    if calendar.high_impact_within(minutes=params.news_block):
        return 0

    # 3. Ruptura confirmada por cierre, no por mecha
    if df.close[-1] > rng_hi and volume_ratio(df) > params.vol_confirm:
        entry, stop = df.close[-1], rng_lo + 0.25 * (rng_hi - rng_lo)
        target = entry + params.rr * (entry - stop)
        return long(entry, stop, target)
    if df.close[-1] < rng_lo and volume_ratio(df) > params.vol_confirm:
        entry, stop = df.close[-1], rng_hi - 0.25 * (rng_hi - rng_lo)
        target = entry - params.rr * (stop - entry)
        return short(entry, stop, target)
    return 0

# SALIDA: target, stop, o cierre forzado a las 20:00 UTC (no llevar a Asia)
```

| Parámetro | Rango | Default |
|---|---|---|
| `max_range_atr` | 0.8–1.6 | 1.2 |
| `vol_confirm` | 1.2–2.0× media | 1.5 |
| `rr` | 1.5–3.0 | 2.0 |
| `news_block` | 30–60 min | 45 |

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.5 – 1.0** |
| Win rate | **40 – 48%** |
| Profit factor | 1.2 – 1.5 |
| Max DD | 10 – 18% |
| Frecuencia | 60–120 señales/año por par |

**Sensibilidad crítica a costes:** con 100 operaciones/año y spread de 0.8 pips en EURUSD, el coste anual es ~80 pips ≈ 0.8% del notional. Sobre un objetivo de retorno del 8%, **los costes consumen el 10% del alpha bruto**. En un broker con spread de 2 pips, consumen el 25%. La estrategia solo es viable en cuenta ECN/Raw.

**Regímenes donde NO usar:** días festivos de Londres o NY; rango asiático > 1.5×ATR; la semana entre Navidad y Año Nuevo (liquidez degenerada).

---

#### Estrategia F3 — Reversión a la media en pares cointegrados

**Lógica.** EURUSD y GBPUSD comparten el factor USD dominante; su spread es estacionario en horizontes cortos. La operación correcta no es correlación sino **cointegración** verificada.

```
1. Test de Engle-Granger sobre ventana de 252 días:
       EURUSD_t = α + β · GBPUSD_t + ε_t
   Requerir ADF(ε) con p < 0.05. Si falla, la estrategia NO se activa.

2. Spread y z-score:
       S_t = EURUSD_t − β̂ · GBPUSD_t
       z_t = (S_t − μ_60) / σ_60

3. Entrada:  z > +z_entry  → short EURUSD, long β̂·GBPUSD
             z < −z_entry  → long EURUSD, short β̂·GBPUSD
4. Salida:   |z| < z_exit  (típico 0.3)  o  stop en |z| > z_stop (típico 3.5)
             o time-stop en half_life · 3
5. Half-life de reversión (Ornstein-Uhlenbeck):
       Δz_t = −θ z_{t−1} + ε   →   HL = ln(2)/θ
```

| Parámetro | Rango | Default |
|---|---|---|
| `z_entry` | 1.8–2.5 | 2.0 |
| `z_exit` | 0.0–0.5 | 0.3 |
| `z_stop` | 3.0–4.0 | 3.5 |
| Ventana β | 120–252 | 252 |
| Re-test cointegración | mensual | mensual |

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.6 – 1.1** |
| Win rate | **65 – 75%** |
| Profit factor | 1.3 – 1.6 |
| Max DD | 8 – 15% |
| Horizonte de reversión | 3–10 días (half-life típica 4–6 días en este par) |

**El modo de fallo es la ruptura de cointegración**, y ocurre precisamente cuando hay un shock idiosincrático (Brexit para GBP, crisis energética para EUR). El re-test mensual de ADF y el `z_stop` duro son la única protección. **Regla:** si el ADF falla dos meses consecutivos, la estrategia se desactiva para ese par hasta re-validación.

---

#### 3.2.4 Bloqueos macro obligatorios (regla dura del sistema)

Implementación: `core/risk/macro_calendar_blocker.py` (nuevo), con precedencia sobre cualquier señal, al mismo nivel que el kill switch.

| Evento | Bloqueo | Alcance |
|---|---|---|
| NFP (US Non-Farm Payrolls) | −30 / +30 min | Todo USD, índices US, XAUUSD |
| CPI US | −30 / +30 min | Todo USD, índices, oro |
| Decisión FOMC | −60 / +60 min | **Global** (incluye crypto) |
| Conferencia de prensa Fed | −0 / +60 min | Global |
| ECB / BoE / BoJ | −30 / +30 min | Divisa correspondiente y sus cruces |
| PIB preliminar, PMI flash | −15 / +15 min | Divisa correspondiente |
| OPEC+ meeting | −60 / +120 min | USOIL, UKOIL, CAD, NOK |
| EIA Petroleum Status (mié 15:30 UTC) | −15 / +30 min | Energía |

**Comportamiento durante el bloqueo:** no se abren posiciones nuevas; las posiciones abiertas mantienen su stop pero se prohíbe el trailing (el gap de precio durante la noticia haría que el trailing ejecute en el peor precio). Fuente de calendario: ForexFactory API o Trading Economics.

---

### 3.3 ÍNDICES GLOBALES (US500, US30, NAS100, DE40, UK100, JP225)

**Contexto estructural.** Los índices tienen drift positivo estructural (prima de riesgo de renta variable, ~5–7% anual sobre cash). Esto implica dos cosas que casi todo sistema retail ignora: (i) el benchmark honesto no es cero, es buy & hold; (ii) una estrategia long-only con Sharpe 0.5 no aporta nada, porque el índice ya lo da.

**Criterio de aceptación específico para índices:** una estrategia de índices debe superar a buy & hold en **Sharpe ajustado por exposición**, o justificar su existencia por reducción de drawdown, no por retorno.

#### Estrategia I1 — Trend following con confirmación multi-timeframe

```python
# Estrategia I1 — Trend following MTF. Señal: 1d. Confirmación: 1w. Tenencia: semanas.

def signal_i1(daily, weekly, macro, params):
    # 1. CONFIRMACIÓN SEMANAL — filtro primario, no negociable
    w_trend = (weekly.close[-1] > ema(weekly.close, params.w_ema)[-1] and
               ema(weekly.close, params.w_ema).slope(4) > 0)
    if not w_trend:
        return 0                                  # sin tendencia semanal, no operar

    # 2. Señal diaria
    d_signal = (daily.close[-1] > ema(daily.close, params.d_ema)[-1] and
                adx(daily, 14)[-1] > params.adx_min)

    # 3. Adaptación al régimen de tipos: el trend following de equity
    #    funciona peor en ciclos de subida agresiva de tipos
    rate_regime = macro.fed_funds_change_6m
    size_mult = 1.0
    if rate_regime > params.hike_thresh:     size_mult = 0.6      # típico +0.75pp
    if macro.yield_curve_slope < 0:          size_mult *= 0.7     # curva invertida

    # 4. VIX gate (ver tabla 3.3.4)
    size_mult *= vix_bucket_multiplier(macro.vix)

    return d_signal * size_mult
```

| Parámetro | Rango | Default |
|---|---|---|
| `w_ema` | 20–40 semanas | 30 |
| `d_ema` | 50–200 días | 100 |
| `adx_min` | 18–25 | 20 |
| `hike_thresh` | 0.5–1.0 pp | 0.75 |

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.6 – 1.0** (vs. buy & hold SPX ≈ 0.5–0.7) |
| Max DD | **10 – 18%** (vs. buy & hold 34% en 2020, 25% en 2022) |
| Win rate | 45 – 55% |
| Profit factor | 1.3 – 1.7 |
| **Valor real** | La mejora está en el **drawdown**, no en el retorno. Calmar de 0.9 vs. 0.25 de buy & hold |

---

#### Estrategia I2 — Reversión intradía post-gap

```
DEFINICIÓN DE GAP SIGNIFICATIVO:
    gap_pct = (open_hoy − close_ayer) / close_ayer
    Significativo si |gap_pct| > max(0.5%, 0.75 × ATR_YZ(14)/precio)
    (el umbral relativo al ATR evita disparar en régimen de alta volatilidad)

PROBABILIDADES HISTÓRICAS DE FILL (SPX, prior de literatura, 2000-2024):
    ┌──────────────────┬─────────────┬─────────────┬──────────────┐
    │ Tamaño del gap   │ Fill mismo  │ Fill en 3   │ Continuación │
    │                  │ día         │ días        │              │
    ├──────────────────┼─────────────┼─────────────┼──────────────┤
    │ 0.5% – 1.0% down │  ~62%       │  ~78%       │  ~22%        │
    │ 1.0% – 2.0% down │  ~48%       │  ~68%       │  ~32%        │
    │ > 2.0% down      │  ~30%       │  ~50%       │  ~50%        │
    │ 0.5% – 1.0% up   │  ~55%       │  ~70%       │  ~30%        │
    │ > 2.0% up        │  ~35%       │  ~52%       │  ~48%        │
    └──────────────────┴─────────────┴─────────────┴──────────────┘
    NOTA: estas cifras son priors de literatura. Deben re-estimarse sobre
    los datos propios ANTES de operar, con intervalos de confianza.

ENTRADA:
    Gap down significativo AND VIX < 30 AND no hay evento macro pendiente
    → long en apertura + 30min (esperar el settle de la subasta)
    → target = close previo (fill del gap)
    → stop = entrada − 1.0 × ATR
    → time-stop = cierre de sesión

SIZING: 50% del tamaño normal. La distribución tiene cola izquierda gorda:
        los gaps que no rellenan suelen ser los grandes y direccionales.
```

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.4 – 0.8** |
| Win rate | **60 – 68%** |
| Profit factor | 1.15 – 1.40 |
| Max DD | 8 – 15% |
| Frecuencia | 25–45 señales/año |

**Regímenes donde NO usar:** VIX > 30 (gaps en pánico continúan, no rellenan); gap causado por evento identificable (earnings de mega-cap, decisión de la Fed); primera sesión tras un festivo largo.

---

#### Estrategia I3 — Patrones estacionales cuantitativos

**Advertencia metodológica que debe acompañar a esta estrategia siempre.** El calendario ofrece ~20 patrones estacionales candidatos (efecto enero, rally de Navidad, sell in May, efecto lunes, turn-of-month, tax-loss harvesting, triple witching, efecto Halloween…). Probar 20 patrones sobre 24 años de datos (24 observaciones independientes por patrón anual) produce, bajo H₀, **al menos un patrón con p < 0.05 con probabilidad del 64%**. La estacionalidad es el área del trading cuantitativo con peor ratio de descubrimientos reales sobre publicados.

**Protocolo de admisión obligatorio para cualquier patrón estacional:**

```
1. Especificar el patrón ANTES de mirar los datos (pre-registro)
2. Requerir p < 0.05 tras corrección de Bonferroni sobre el número
   total de patrones considerados:   α_efectivo = 0.05 / 20 = 0.0025
3. Requerir consistencia cross-sectional: el patrón debe aparecer en
   ≥ 4 de 6 índices globales (no solo SPX)
4. Requerir estabilidad temporal: dividir la muestra en dos mitades;
   el efecto debe tener el mismo signo en ambas
5. Efecto mínimo económicamente relevante: > 2× costes de transacción
```

| Patrón | Efecto bruto documentado | ¿Sobrevive el protocolo? | Recomendación |
|---|---|---|---|
| **Turn-of-month** (últimos 3 + primeros 3 días) | +0.15–0.25% por ciclo | Probablemente sí (flujo de nóminas 401k, mecanismo identificable) | **Implementar como tilt de sizing (+20%)** |
| **Sell in May** (may–oct vs. nov–abr) | Diferencial de 4–6% anual | Marginal; se debilita post-2000 | Shadow mode |
| **Rally de Navidad** (últimos 5 + primeros 2) | +1.3% media | Marginal, n≈24 | Shadow mode |
| **Efecto enero** (small caps) | Erosionado desde los 90 | No | **Descartar** |
| **Tax-loss harvesting** (dic, perdedores del año) | Real en small caps individuales | No aplicable a índices | **Descartar para índices** |

**Recomendación neta:** la estacionalidad debe entrar como **modulador de sizing de ±20%**, nunca como generador de señal independiente. El único patrón con mecanismo económico identificable y flujo verificable es turn-of-month.

---

#### 3.3.4 Tabla de comportamiento por bucket de VIX

Esta tabla es el corazón operativo de la lógica de índices y debe implementarse como una función explícita, auditable, en `core/adaptation/regime_watcher.py`:

| Bucket VIX | Régimen | Multiplicador de sizing | Estrategias activas | Sesgo direccional |
|---|---|---:|---|---|
| **0 – 15** | Complacencia | **1.0×** | I1 (trend), I3 (tilt) | Long. Momentum funciona. Vol vendible pero fuera de alcance |
| **15 – 25** | Normal | **1.0×** | I1, I2, I3 | Neutral. Régimen base de calibración |
| **25 – 35** | Estrés | **0.5×** | I2 (solo si el gap no es por evento) | Mean-reversion > momentum. Correlaciones convergen a 1 |
| **> 35** | Pánico | **0.0×** | **Ninguna** — solo gestión de salidas | Sin nuevas posiciones. Verificar kill switch |
| **Transición 15→25 rápida** (Δ > 40% en 3 días) | Shock incipiente | **0.3×** | Ninguna nueva | Reducir exposición existente 50% |

**Nota sobre la asimetría.** El VIX es asimétrico: sube rápido y baja lento. Un sistema que use el nivel del VIX sin la velocidad de cambio reaccionará tarde a los shocks y temprano a las recuperaciones — exactamente el peor orden posible. Por eso la última fila.

---

### 3.4 COMMODITIES (XAUUSD, XAGUSD, USOIL, UKOIL, NATGAS)

**Nota de relevancia particular.** XAUUSD es el único activo que "pasa" el Gate I1 actual. La Sección 0 mostró que ese pase no es estadísticamente significativo (p = 0.23), pero **sí es la mejor candidata a priori del universo**: el oro tiene drivers macro identificables y estables (tipos reales, DXY, riesgo geopolítico), lo que hace plausible un edge genuino donde el ruido no lo explique todo. Merece la mayor asignación de esfuerzo de investigación.

#### Estrategia M1 — Oro como activo refugio (macro-driven)

**Lógica.** El oro no genera flujo de caja; su precio es esencialmente el precio de la ausencia de rendimiento real. La relación fundamental:

$$\Delta \ln(XAU) \approx -\beta_1 \Delta r^{real} - \beta_2 \Delta \ln(DXY) + \beta_3 \Delta(\text{Riesgo geopolítico}) + \varepsilon$$

con $r^{real} = y_{10Y}^{nominal} - \text{breakeven}_{10Y}$ (TIPS). Betas típicos: $\beta_1 \approx 0.15$–$0.25$ por punto porcentual, $\beta_2 \approx 0.6$–$0.9$.

```python
# Estrategia M1 — Gold macro. Timeframe: 1d. Tenencia: 1-8 semanas.

def signal_m1(gold, macro, params):
    score = 0.0

    # Driver 1: tipos reales (el más importante)
    if macro.real_yield_10y < params.real_yield_thresh:      # típico 0.5%
        score += params.w_real * (params.real_yield_thresh - macro.real_yield_10y)
    score -= params.w_real_mom * z_score(macro.real_yield_10y.diff(20), 252)

    # Driver 2: dólar
    score -= params.w_dxy * z_score(macro.dxy.pct_change(20), 252)

    # Driver 3: riesgo / refugio
    if macro.vix > params.vix_thresh:                        # típico 20
        score += params.w_vix
    if macro.credit_spread_z > 1.5:                          # Capa 4.3
        score += params.w_credit

    # Driver 4: posicionamiento contrarian (Capa 5.4)
    if macro.cot_index_gold > 90:  score *= 0.5              # especuladores saturados
    if macro.cot_index_gold < 10:  score *= 1.3

    # Confirmación técnica: no pelear con el precio
    if score > 0 and gold.close[-1] < sma(gold.close, 50)[-1]:
        score *= 0.5

    return clip(score / params.scale, -1, +1)
```

| Parámetro | Rango | Default |
|---|---|---|
| `real_yield_thresh` | 0.0–1.0% | 0.5% |
| `w_real` / `w_dxy` | 0.8–1.5 / 0.5–1.0 | 1.0 / 0.7 |
| `vix_thresh` | 18–25 | 20 |
| Vol target | 8–12% anual | 10% |

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.5 – 0.9** |
| Max DD | 12 – 20% |
| Win rate | 50 – 58% |
| Profit factor | 1.25 – 1.55 |
| Frecuencia | 12–25 señales/año |

**Sizing específico:** el oro tiene vol de ~14% anual (menor que crypto, mayor que FX majors). Con vol target del 10%, el factor de escala es 0.71× del notional nominal. En régimen de crisis (VIX > 30) la vol del oro puede triplicarse — el sizing debe usar la vol *forecasted* por GARCH, no la histórica.

**Regímenes donde NO usar:** subidas agresivas de tipos reales (2022 es el caso de estudio: el oro cayó pese al riesgo geopolítico máximo, porque los tipos reales dominaron); DXY en tendencia alcista fuerte con momentum de 20 días en percentil >90.

---

#### Estrategia M2 — Momentum energético con inventarios

**Lógica.** El EIA Weekly Petroleum Status Report (miércoles, 15:30 UTC) publica cambios de inventario. La sorpresa —la desviación respecto al consenso— es información genuinamente nueva.

$$\text{Sorpresa}_t = \frac{\Delta \text{Inv}_{real} - \Delta \text{Inv}_{esperado}}{\sigma_{52w}(\text{sorpresa})}$$

```python
# Estrategia M2 — Energy inventories. Timeframe: 1d. Tenencia: 3-10 días.

def signal_m2(oil, eia, params):
    surprise = (eia.actual - eia.consensus) / eia.surprise_std_52w

    # Build (acumulación) = bajista para el precio; draw (retiro) = alcista
    base = -surprise

    # Confirmación por estructura de la curva de futuros:
    #   backwardation = mercado tenso = alcista
    curve = (oil.front_month - oil.second_month) / oil.front_month
    if base > 0 and curve < 0:  base *= 0.5          # contango contradice
    if base < 0 and curve > 0:  base *= 0.5

    # Filtro estacional: la demanda de crudo tiene estacionalidad real
    #   (driving season US: mayo-agosto; heating: nov-feb)
    base *= params.seasonal_factor[current_month()]

    # NO operar dentro de la ventana de bloqueo del release
    if within_minutes(eia.release_time, params.block_min):    # típico [-15, +30]
        return 0

    return clip(base, -1, +1)
```

| Parámetro | Rango | Default |
|---|---|---|
| Umbral de sorpresa | 1.0–2.0 σ | 1.5 σ |
| `block_min` | [−15, +30] min | fijo |
| Tenencia máxima | 5–10 días | 7 |

| Métrica (prior) | Rango |
|---|---|
| Sharpe neto | **0.4 – 0.8** |
| Win rate | 52 – 60% |
| Profit factor | 1.2 – 1.45 |
| Max DD | 15 – 25% (el crudo es violento) |
| Frecuencia | ~52 evaluaciones/año, ~20 señales |

**Integración al pipeline:** requiere un ingestor nuevo (`core/ingestion/providers/eia_client.py`) contra la API pública de la EIA (gratuita, requiere API key). El consenso hay que obtenerlo de una fuente comercial o aproximarlo con la media móvil estacional — con la degradación de calidad de señal que eso implica, que debe reflejarse en un prior de Sharpe menor.

**Regímenes donde NO usar:** durante conflictos con riesgo de suministro activo (la prima geopolítica domina a los inventarios); cuando NATGAS y USOIL divergen en más de 3σ (dislocación estructural).

---

#### Estrategia M3 — Estacionalidad en agrícolas (condicional)

Aplica solo si se incorporan trigo, maíz y soja (hoy solo WHEAT está declarado en la configuración, sin datos descargados).

| Producto | Patrón estacional | Mecanismo | Ventana |
|---|---|---|---|
| **Trigo** | Debilidad en cosecha (jun–jul, HN) | Presión de oferta física | Short bias jun 15 – jul 31 |
| **Maíz** | Prima de riesgo de polinización (jun–jul) | Incertidumbre climática en la fase crítica | Long vol / long bias jun 1 – jul 15 |
| **Soja** | Debilidad en cosecha US (sep–oct) | Oferta + competencia sudamericana | Short bias sep 15 – oct 31 |

**El mismo protocolo anti-multiplicidad de la Sección 3.3 (I3) aplica íntegramente aquí.** Los patrones agrícolas tienen mejor mecanismo económico que los de equity (la siembra y la cosecha son hechos físicos, no folclore de calendario), pero también menos observaciones independientes útiles (una por año). **Requisito mínimo: 20 años de datos antes de operar cualquiera de estos patrones.** Prior de Sharpe: 0.3–0.6 — bajo, pero con correlación cercana a cero contra el resto del portafolio, que es donde está su valor real.

**Recomendación:** **postergar.** Los agrícolas añaden 3 activos, 3 estrategias y ~15 parámetros al presupuesto de multiplicidad a cambio de un Sharpe marginal bajo. No entran hasta que el núcleo (crypto + FX + índices + metales/energía) tenga edge demostrado.

---

### 3.5 Matriz consolidada estrategia × régimen

Referencia operativa única. `1` = activa a tamaño completo, `½` = tamaño reducido, `0` = desactivada.

| Estrategia | Trend fuerte | Trend débil | Lateral | Alta vol | Crisis (VIX>35) | Hurst<0.45 |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| C1 Momentum crypto | 1 | ½ | 0 | ½ | 0 | 0 |
| C2 Funding carry | 1 | 1 | 1 | ½ | 0 | 1 |
| C3 On-chain (overlay) | 1 | 1 | 1 | 1 | ½ | 1 |
| F1 Carry FX | 1 | 1 | 1 | ½ | 0 | 1 |
| F2 Session breakout | 1 | ½ | 0 | ½ | 0 | 0 |
| F3 Pares cointegrados | ½ | 1 | 1 | ½ | 0 | 1 |
| I1 Trend índices | 1 | ½ | 0 | ½ | 0 | 0 |
| I2 Gap reversion | ½ | 1 | 1 | ½ | 0 | 1 |
| I3 Estacionalidad (tilt) | 1 | 1 | 1 | ½ | 0 | 1 |
| M1 Oro macro | 1 | 1 | ½ | 1 | **1** | ½ |
| M2 Energía/inventarios | 1 | 1 | ½ | ½ | 0 | 1 |

**Observación de diseño:** M1 (oro) es la única estrategia activa a tamaño completo en crisis. Esto no es casual — es el mecanismo de cobertura natural del portafolio y refuerza por qué XAUUSD merece la prioridad de investigación.

---

## SECCIÓN 4 — Arquitectura del ensemble de modelos IA

### 4.0 La decisión arquitectónica que precede a todas las demás: panel global vs. modelos por activo

El diseño actual (`core/models/asset_specific_models.py`) entrena **un stack de modelos por clase de activo**, con 4 modelos y pesos fijos por clase. Con los datos disponibles esto es matemáticamente desfavorable:

| Enfoque | Muestra efectiva por modelo | Parámetros a estimar | Ratio muestra/parámetro |
|---|---|---|---|
| **Actual: 4 stacks por clase, ~4 modelos c/u** | ~17.000 barras (1 activo) o ~50.000 (3 activos de la clase) | LightGBM con 31 hojas × 500 árboles ≈ 15.500 nodos | **~3:1 — severamente insuficiente** |
| **Propuesto: 1 modelo panel global + embeddings de activo** | ~500.000 barras (28 activos × 3 años) o **~2.500.000** (28 activos × 15 años) | Mismo modelo + 28 × 8 dims de embedding = +224 | **~160:1** |

El argumento no es de elegancia sino de estadística: la estructura de retornos condicionada a features (momentum, volatilidad, régimen) es **substancialmente compartida entre activos**. Gu, Kelly & Xiu (2020) demuestran empíricamente en equities que los modelos entrenados sobre el panel completo superan de forma consistente a los modelos por activo, y que la ganancia crece cuanto menor es la muestra por activo. Ese es exactamente el régimen en el que está TRADER AI.

**Recomendación central de la Sección 4:**

```
Un modelo global entrenado sobre TODOS los activos simultáneamente, con:
  - Features normalizados CROSS-SECTIONALMENTE (rank o z-score por barra
    entre activos), no por serie temporal individual
  - Un embedding aprendido por activo (dim 4-8) y uno por clase de activo (dim 3)
  - Target normalizado por volatilidad del activo: y = r_{t+h} / σ_t
    → hace comparables BTC (vol 60%) y EURUSD (vol 7%) en la misma función de pérdida
  - Sample weights por unicidad (López de Prado) para corregir el solapamiento
    de labels de horizonte múltiple
```

Esto sustituye, no complementa, la arquitectura de 4 stacks por clase. Los modelos 1–5 que siguen se especifican **en el marco panel**.

---

### 4.1 Modelo 1 — LightGBM sobre panel (base productiva)

Es el caballo de batalla y debe seguir siéndolo: sobre datos tabulares financieros con ratio señal/ruido bajo, los ensembles de árboles con boosting siguen siendo el estado del arte práctico.

**Hiperparámetros para series temporales financieras** (deliberadamente conservadores — el sobreajuste, no el sesgo, es el enemigo aquí):

```python
params = {
    "objective": "regression",       # sobre y = r_{t+h}/σ_t, NO clasificación
    "metric": "l2",
    "boosting_type": "gbdt",

    # --- Capacidad: baja. El ratio señal/ruido en finanzas es ~1-5% de R² ---
    "num_leaves": 15,                # rango 7-31. NO usar el default de 31
    "max_depth": 4,                  # rango 3-6
    "min_data_in_leaf": 500,         # rango 200-2000. CRÍTICO: el default de 20
                                     #   produce hojas que memorizan ruido
    "learning_rate": 0.02,           # rango 0.01-0.05 con early stopping
    "n_estimators": 3000,            # con early_stopping_rounds=100

    # --- Regularización: agresiva ---
    "feature_fraction": 0.6,         # rango 0.4-0.8
    "bagging_fraction": 0.7,         # rango 0.5-0.9
    "bagging_freq": 5,
    "lambda_l1": 0.1,
    "lambda_l2": 1.0,                # rango 0.5-10
    "min_gain_to_split": 0.01,

    # --- Robustez a colas gordas ---
    "objective": "huber",            # alternativa recomendada: menos sensible
    "alpha": 0.9,                    #   a los outliers de retorno extremo
}
```

**Validación: `PurgedKFold` con embargo.** La clase ya existe en `core/ml/validation.py`. La configuración correcta:

$$\text{embargo} = h + \max(\text{ventana de feature más larga}) \times 0.01$$

Con $h = 6$ barras y features que usan ventanas de hasta 500 barras, el embargo debe ser **≥ 6 barras por solapamiento de label + 5 barras de margen = 11 barras**, no las 5 del brief. Razón: si el label en $t$ usa datos hasta $t+6$, cualquier muestra de test entre $t$ y $t+6$ contiene información del train. El brief especifica 5; con $h=6$ eso deja una barra de fuga.

**Umbral de admisión de features vía SHAP:**

$$\text{Retener } f \iff \overline{|\phi_f|} > \max\left(\overline{|\phi_{shuffle}|} \cdot 1.5,\ \ \frac{1}{2}\cdot\frac{\sum_g \overline{|\phi_g|}}{N_{features}}\right)$$

donde $\phi_{shuffle}$ es la importancia SHAP de una feature de ruido puro inyectada deliberadamente en el conjunto de entrenamiento (*null feature benchmark*). Esta técnica —incluir 3–5 columnas aleatorias y descartar toda feature que no las supere claramente— es más robusta que cualquier umbral absoluto y es directamente ejecutable con el código existente.

---

### 4.2 Modelo 2 — Temporal Fusion Transformer

**Recomendación: NO entrenar todavía. Sprint 13+, condicionado.** El brief lo pide, y la especificación completa se entrega abajo, pero la condición de activación es explícita porque es la diferencia entre una inversión útil y una fuente de sobreajuste caro.

**Condición de activación:** ≥ 8 años de datos por activo **y** ≥ 20 activos en el panel **y** el LightGBM panel con IC out-of-sample > 0.02 estable. Con menos que eso, un TFT (≈ 400k–2M parámetros) sobre 500k muestras correlacionadas memoriza.

**Arquitectura especificada** (`pytorch-forecasting`):

```python
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

tft = TemporalFusionTransformer.from_dataset(
    training_dataset,
    hidden_size=32,                  # rango 16-64. NO 160 (default de tutoriales)
    lstm_layers=2,                   # rango 1-2
    attention_head_size=4,           # rango 1-4
    dropout=0.3,                     # rango 0.2-0.4 — alto a propósito
    hidden_continuous_size=16,       # ≤ hidden_size/2
    output_size=[3],                 # cuantiles 0.1/0.5/0.9 → intervalos, no punto
    loss=QuantileLoss([0.1, 0.5, 0.9]),
    learning_rate=1e-3,
    reduce_on_plateau_patience=4,
    optimizer="ranger",
)
```

**Asignación de inputs por canal** — es donde el TFT gana o pierde:

| Canal | Contenido | Ejemplos |
|---|---|---|
| `static_categoricals` | Identidad del activo | `symbol`, `asset_class`, `exchange` |
| `static_reals` | Propiedades estables | vol promedio de largo plazo, Hurst medio, tick size relativo |
| `time_varying_known_reals` | **Conocidos en el futuro** | hora del día, día de la semana, minutos hasta el próximo evento macro, días hasta vencimiento de futuros, indicador de sesión |
| `time_varying_unknown_reals` | Solo conocidos hasta t | precio, volumen, todas las features de las Capas 1–5, VIX, DXY |

El canal `time_varying_known_reals` es la ventaja real del TFT sobre LightGBM: **puede condicionar la predicción sobre el calendario futuro conocido** (que el NFP es en 3 horas, que el vencimiento es el viernes). Ningún modelo tabular estándar hace eso de forma natural.

**Cuándo supera a LightGBM:** (i) horizontes largos y multi-paso (predecir el path, no un punto); (ii) cuando el calendario futuro conocido importa; (iii) con muestras grandes y regímenes múltiples donde la atención puede aprender a conmutar. **Cuándo pierde:** muestras pequeñas, señal débil, features tabulares ya bien diseñadas — es decir, la situación actual.

---

### 4.3 Modelo 3 — Clasificador de régimen (XGBoost + HMM)

El repositorio ya tiene un HMM (`core/adaptation/hmm_regime_detector.py`) con un problema documentado: **8 estados con covarianza `full` está sobreparametrizado** (2 tests fallando por esto, según el plan maestro).

**Diagnóstico y corrección:** un HMM gaussiano con $K$ estados y $D$ dimensiones y covarianza `full` estima $K \cdot D(D+1)/2$ parámetros solo en covarianzas. Con $K=8$, $D=5$: 120 parámetros de covarianza + 64 de transición + 40 de medias = **224 parámetros**. Es demasiado para muestras pequeñas y produce covarianzas singulares.

```
Configuración recomendada:
    K = 4 estados  (no 8)   →  Alcista / Bajista / Lateral / Crisis
    covariance_type = "diag" (no "full")
    D = 4 features:  [retorno normalizado, vol YZ, |retorno|, term structure VIX]
    → parámetros: 4×4 medias + 4×4 var + 16 transición = 48. Manejable.
```

La taxonomía de 6 clases del brief (Tendencia_Fuerte_Alcista / Débil_Alcista / Lateral / Débil_Bajista / Fuerte_Bajista / Crash) es demasiado granular para la muestra: la clase "Crash" tendría del orden de 10–30 observaciones en 3 años. **Recomendación: 4 estados HMM (no supervisado, sin necesidad de etiquetas) + un clasificador XGBoost supervisado de 3 clases** (Risk-on / Neutral / Risk-off) entrenado sobre etiquetas derivadas del propio HMM, que sí es aprendible.

**Features más relevantes para clasificación de régimen** (por poder discriminante esperado):

1. VIX term structure (Capa 4.2) — el discriminante individual más fuerte
2. Volatilidad realizada Yang-Zhang, normalizada por su percentil de 252 días
3. Exponente de Hurst (Capa 2.1)
4. Correlación media del cross-section (en crisis converge a 1)
5. Credit spread z-score (Capa 4.3)
6. Ratio de saltos: $J_t / RV_t$ (Capa 3.4)
7. Pendiente de la EMA(50) normalizada por ATR

**Integración con el sistema de consenso.** El error a evitar es que el régimen entre como *un voto más*. El régimen no es una opinión sobre la dirección: es el **contexto que decide qué opiniones son válidas**. Implementación correcta sobre `core/consensus/voting_engine.py`:

$$\text{Señal}_{final} = \sum_{a \in \text{Agentes}} w_a(\text{régimen}) \cdot s_a \quad \text{con} \quad \sum_a w_a(\text{régimen}) = 1$$

| Régimen | Peso Técnico | Peso Régimen | Peso Micro | Peso Fundamental | Multiplicador global |
|---|---:|---:|---:|---:|---:|
| Alcista (trending) | 0.55 | 0.20 | 0.15 | 0.10 | 1.0× |
| Bajista (trending) | 0.45 | 0.25 | 0.15 | 0.15 | 0.7× |
| Lateral | 0.25 | 0.30 | 0.30 | 0.15 | 0.5× |
| Crisis | 0.10 | 0.40 | 0.20 | 0.30 | **0.0×** |

Nótese que en crisis los pesos son irrelevantes porque el multiplicador global es cero. Esa es la implementación de "el régimen decide si se opera", no "el régimen vota".

---

### 4.4 Modelo 4 — Isolation Forest para detección de anomalías

**Propósito.** No es un modelo de señal: es un **circuit breaker estadístico** que detecta que el mercado actual no se parece a nada visto en entrenamiento — el caso en el que las predicciones del modelo carecen de sentido.

```python
from sklearn.ensemble import IsolationForest

iso = IsolationForest(
    n_estimators=200,
    max_samples=4096,
    contamination=CONTAMINATION[asset_class],   # ver tabla
    max_features=1.0,
    random_state=42,
)
```

**Parámetro `contamination` por clase de activo:**

| Clase | contamination | Justificación |
|---|---:|---|
| Crypto | **0.02** | Colas gordas nativas; un umbral bajo dispararía constantemente |
| Forex majors | **0.005** | Distribución más regular; una anomalía real es rara y significativa |
| Índices | **0.01** | Gaps de sesión y eventos macro programados |
| Commodities | **0.015** | Shocks de oferta genuinos y frecuentes |

**Features de entrada — qué define "normal":**

```
[ retorno_norm(1,5,20),  vol_YZ / vol_YZ_p50_252,  spread / spread_median,
  volumen / volumen_p50_20,  |salto|_z,  correlación_media_cross_section,
  distancia_Mahalanobis(features_del_modelo, μ_train, Σ_train) ]
```

La última es la más importante: mide directamente si el vector de features está fuera del soporte de entrenamiento, que es la definición operativa de "el modelo no sabe".

**Integración con el kill switch** (`core/risk/kill_switch.py`, `kill_switch_redis.py`):

| Condición | Acción | Precedencia |
|---|---|---|
| `anomaly_score` < umbral en 1 activo | Suprimir señales de ese activo; sizing 0 | Sobre la señal |
| `anomaly_score` < umbral en ≥ 40% de los activos simultáneamente | **Kill switch: modo solo-salidas** | Absoluta |
| Anomalía + salto (Capa 3.4) con Z > 5 | Kill switch inmediato + alerta Telegram | Absoluta |
| Anomalía persistente > 24h | Bloqueo hasta revisión manual + trigger de reentrenamiento | Absoluta |

**Nota de diseño fail-safe:** el kill switch ya es fail-closed ante caída de Redis (corregido 2026-07-26). El detector de anomalías debe heredar esa semántica: **si el modelo de anomalías no está disponible o devuelve error, se asume anomalía**, no normalidad.

---

### 4.5 Modelo 5 — Meta-learner (stacking)

**Arquitectura: Ridge, no LightGBM.** La razón es de grados de libertad: el meta-learner opera sobre 4–6 predicciones de entrada. Un LightGBM sobre 5 columnas y muestras autocorrelacionadas encontrará interacciones espurias con facilidad. Ridge con regularización fuerte y **coeficientes restringidos a no-negativos** es el estándar defendible:

```python
from sklearn.linear_model import Ridge
from scipy.optimize import nnls

# Restricción de no-negatividad: un modelo base no puede contribuir "al revés".
# Si su peso óptimo es negativo, la lectura correcta es que sobreajustó,
# no que su señal deba invertirse.
meta = Ridge(alpha=10.0, fit_intercept=False, positive=True)
meta.fit(oof_predictions, y_true, sample_weight=uniqueness_weights)
```

**Cómo evitar data leakage — el punto crítico de todo el stacking.** El meta-learner debe entrenarse **exclusivamente sobre predicciones out-of-fold**, generadas con la misma purga y embargo que los modelos base:

```
PROTOCOLO ANTI-LEAKAGE DEL META-LEARNER

1. Partición temporal externa en K bloques con purga y embargo (PurgedKFold).
2. Para cada bloque k:
     a. Entrenar TODOS los modelos base solo con datos anteriores al bloque k
        (menos el embargo).
     b. Predecir sobre el bloque k → estas son las predicciones OOF.
     c. Descartar (nunca guardar) las predicciones in-sample.
3. Concatenar las predicciones OOF de todos los bloques → matriz de entrada
   del meta-learner.
4. Entrenar el meta-learner con validación temporal PROPIA sobre esa matriz.
5. VERIFICACIÓN OBLIGATORIA: R² in-sample del meta-learner sobre predicciones
   OOF debe ser del mismo orden que su R² OOS. Una brecha grande (p. ej. 0.15
   vs 0.01) es prueba de fuga y debe abortar el pipeline.
6. El escalado de features (StandardScaler, normalización cross-sectional) debe
   ajustarse DENTRO de cada fold, nunca sobre el dataset completo. Este es el
   leak más común y el más silencioso.
```

**Calibración: Brier score y curva de fiabilidad.** Para señales probabilísticas:

$$BS = \frac{1}{N}\sum_{i=1}^{N}(p_i - o_i)^2, \qquad BS_{skill} = 1 - \frac{BS}{BS_{ref}}$$

con $BS_{ref}$ el Brier de la frecuencia base. Umbrales de aceptación:

| Métrica | Mínimo | Objetivo |
|---|---|---|
| Brier skill score | > 0.01 | > 0.03 |
| Error de calibración (ECE, 10 bins) | < 0.05 | < 0.02 |
| Pendiente de la curva de fiabilidad | 0.8 – 1.2 | 0.95 – 1.05 |

**Por qué esto importa operativamente:** el sizing de Kelly (Sección 5) usa la probabilidad estimada como input directo. Un modelo con Brier aceptable pero mal calibrado (que dice 70% cuando la frecuencia real es 55%) produce un Kelly sobredimensionado en un factor de ~2. **La calibración no es un refinamiento académico: es un input del control de riesgo.** Se aplica `CalibratedClassifierCV` con isotonic regression sobre el conjunto OOF.

---

### 4.6 Esquema de reentrenamiento

| Modelo | Frecuencia base | Ventana | Trigger automático de reentrenamiento anticipado |
|---|---|---|---|
| LightGBM panel | Mensual | Expanding | IC rodante de 60 días < 50% del IC de validación |
| XGBoost régimen | Mensual | Expanding | Accuracy 30 días < 60% del baseline |
| HMM | Trimestral | Expanding | Log-verosimilitud media por observación cae > 2σ |
| Isolation Forest | Trimestral | **Rolling 2 años** | Tasa de anomalías > 3× la contaminación configurada durante 7 días |
| Meta-learner | Mensual (con las bases) | Expanding | Cualquier reentrenamiento de un modelo base |
| TFT (si se activa) | Trimestral | Expanding | Degradación de pérdida de cuantil > 20% |

**Expanding vs. rolling — la decisión y su razón.** Para los modelos de señal: **expanding window**. Con 2–3 años de datos, descartar historia es un lujo inasumible; el argumento a favor del rolling (que el régimen antiguo es irrelevante) solo domina cuando hay datos de sobra. Para el Isolation Forest: **rolling**, porque su trabajo es definir "normal *hoy*" y una definición de normalidad de hace 10 años produce falsos positivos permanentes.

**Regla de gobernanza del reentrenamiento** — el punto donde más sistemas se autodestruyen silenciosamente:

```
Un modelo reentrenado NO reemplaza automáticamente al modelo en producción.

Debe pasar por core/ml/model_validation_gate.py y superar:
  1. IC OOS ≥ 80% del IC del modelo en producción
  2. Sin degradación > 20% en ninguna clase de activo individual
  3. Deflated Sharpe Ratio del backtest ≥ el del modelo vigente
  4. Estabilidad de feature importance: correlación de Spearman entre
     los rankings SHAP del modelo nuevo y el vigente > 0.6
     (un ranking radicalmente distinto indica que aprendió otra cosa,
      no que mejoró)

Si falla: se mantiene el modelo vigente y se genera una alerta.
Un reentrenamiento fallido es información, no un error.
```

---

## SECCIÓN 5 — Gestión de riesgo cuantitativa

### 5.1 Position sizing

#### 5.1.1 Kelly fraccional — la fórmula y su ejemplo numérico exacto

$$f^* = \frac{p \cdot b - q}{b}, \qquad q = 1-p, \quad b = \frac{\text{ganancia media}}{\text{pérdida media}}$$

Cuando se conoce el profit factor en lugar de $b$, la relación es:

$$PF = \frac{p \cdot \overline{W}}{q \cdot \overline{L}} = \frac{p \cdot b}{q} \implies b = \frac{PF \cdot q}{p}$$

**Ejemplo numérico con los valores del brief (win rate = 52%, profit factor = 1.6):**

$$b = \frac{1.6 \times 0.48}{0.52} = 1.4769$$
$$f^* = \frac{0.52 \times 1.4769 - 0.48}{1.4769} = \frac{0.7680 - 0.48}{1.4769} = \frac{0.2880}{1.4769} = \mathbf{0.1950}$$

$$f_{operativo} = 0.25 \times f^* = 0.25 \times 0.1950 = \mathbf{0.0487 \approx 4.9\%\ \text{del capital por operación}}$$

**Este número debe ser interpretado con cuidado y el brief invita a un error.** El 4.9% es la fracción de capital *en riesgo* (la pérdida si el stop se ejecuta), no el notional de la posición. Con un stop de 2×ATR y un ATR del 1.5% del precio, el notional resultante sería:

$$\text{Notional} = \frac{0.049 \times \text{Capital}}{0.03} = 1.63 \times \text{Capital}$$

es decir, **1.6× apalancamiento en una sola posición**. Con $10.000 de capital eso son $16.300 de exposición en un trade. Es una cifra agresiva incluso a cuarto de Kelly.

**Por qué el cuarto de Kelly sigue siendo demasiado aquí.** Kelly asume que $p$ y $b$ son *conocidos*. Se estiman con error, y el sizing de Kelly es convexo en el error: sobreestimar $p$ en 3 puntos porcentuales (52% → 55%) eleva $f^*$ de 0.195 a 0.255, un +31%. Con un $p$ estimado sobre 200 operaciones, el error estándar de $p$ es $\sqrt{0.52 \times 0.48/200} = 3.5\%$ — es decir, **el error de estimación es del mismo orden que la señal**.

**Recomendación operativa:**

$$f_{operativo} = \min\left(0.15 \cdot f^*,\ \ \frac{0.02 \cdot \text{Capital}}{\text{Stop}_{\%}},\ \ \text{límite de vol-target}\right)$$

Con los mismos números: $0.15 \times 0.195 = 2.9\%$, acotado por el límite del 2% del brief. **El brief especifica 2% del capital por señal, y ese límite debe dominar al Kelly, no al revés.** El Kelly se usa como techo superior y como señal de calidad relativa entre estrategias, no como sizing primario.

#### 5.1.2 Ajuste por volatilidad (volatility targeting)

$$\text{Size}_i = \frac{\sigma_{target}}{\sigma_i^{forecast}} \cdot \text{Size}_{base}, \qquad \sigma_i^{forecast} = \sqrt{E_t[\sigma^2_{i,t+h}]} \text{ vía GARCH (§3.2)}$$

Con reducción escalonada adicional en volatilidad extrema:

| Percentil de ATR/precio (252d) | Multiplicador |
|---|---:|
| < p50 | 1.15× |
| p50 – p80 | 1.00× |
| p80 – p90 | **0.70×** |
| p90 – p97 | **0.40×** |
| > p97 | **0.00×** — no abrir |

Ya existe `core/risk/volatility_targeting.py`; la mejora propuesta es usar la vol *predicha* por GARCH en vez de la realizada, lo que anticipa la reducción en lugar de aplicarla tarde.

#### 5.1.3 Ajuste por correlación

**Regla del brief:** $\rho(A,B) > 0.7 \Rightarrow$ tratar como un solo activo. La implementación correcta generaliza a N activos vía el **número efectivo de apuestas**:

$$N_{eff} = \frac{\left(\sum_i w_i\right)^2}{\mathbf{w}^\top \boldsymbol{\Sigma}_{\rho} \mathbf{w}}, \qquad \text{Multiplicador} = \sqrt{\frac{N_{eff}}{N_{posiciones}}}$$

Ejemplo: 4 posiciones con correlación media 0.7 → $N_{eff} \approx 1.5$ → multiplicador $= \sqrt{1.5/4} = 0.61$. Cada posición se reduce al 61%, de forma que el riesgo *agregado* equivale a las 4 posiciones independientes que el sistema cree tener.

Esto es estrictamente superior a la regla binaria: es continuo, no requiere umbral arbitrario, y degrada suavemente.

---

### 5.2 VaR y CVaR de portafolio

**Metodología: VaR histórico** (no paramétrico), ventana de 252 días, con ponderación exponencial ($\lambda = 0.99$) para dar más peso al pasado reciente sin descartar las colas antiguas:

$$VaR_\alpha = -\text{Percentil}_{1-\alpha}\left(\{r^{portfolio}_t\}_{t=1}^{252}\right)$$

$$CVaR_\alpha = ES_\alpha = -E\left[r \mid r \leq -VaR_\alpha\right] = -\frac{1}{|\mathcal{T}|}\sum_{t \in \mathcal{T}} r_t, \quad \mathcal{T} = \{t : r_t \leq -VaR_\alpha\}$$

**El VaR histórico tiene un problema conocido con 252 observaciones:** el VaR al 99% se estima con las ~2.5 peores observaciones. Es un estimador de altísima varianza. Complemento obligatorio:

$$VaR^{EVT}_{99\%}: \quad \text{ajustar una Generalized Pareto a los excedentes sobre el umbral } u = VaR_{95\%}$$
$$P(X > u+y \mid X > u) = \left(1 + \frac{\xi y}{\beta}\right)^{-1/\xi}$$

y reportar el máximo de ambos. El parámetro de cola $\xi$ es además informativo por sí mismo: $\xi > 0.3$ indica colas muy gordas y justifica un recorte generalizado del riesgo.

**Límites y acciones:**

| Métrica | Límite | Acción al superarse |
|---|---|---|
| VaR diario 95% | ≤ 2.0% | Reducción proporcional de todas las posiciones hasta cumplir |
| VaR diario 99% | ≤ 4.0% | Reducción + alerta |
| CVaR 95% | ≤ 3.5% | Reducción proporcional + prohibir nuevas entradas 24h |
| CVaR 99% | ≤ 6.0% | Reducción al 50% + revisión manual |
| $\xi$ (EVT) | ≤ 0.4 | Recorte global del 30% del sizing |

**Algoritmo de reducción proporcional** (`core/risk/portfolio_risk_engine.py`):

```python
def enforce_var_limit(positions, var_limit, cvar_limit):
    scale = 1.0
    for _ in range(MAX_ITER):                     # típico 20
        var, cvar = compute_historical_var_cvar(positions, scale)
        if var <= var_limit and cvar <= cvar_limit:
            break
        # Escalado proporcional: preserva la estructura relativa del portafolio.
        # Alternativa (rechazada): cerrar la peor posición — introduce
        # decisiones discretas difíciles de auditar y con efectos de segundo orden
        # sobre la correlación del resto.
        scale *= 0.9
    audit_log("var_enforcement", scale=scale, var=var, cvar=cvar)   # QG-6
    return apply_scale(positions, scale)
```

---

### 5.3 Drawdown escalonado

Implementación como máquina de estados con **histéresis** — el punto que el brief omite y que es la diferencia entre un sistema estable y uno que oscila:

| Estado | Trigger de entrada | Sizing | Trigger de salida (recuperación) | Acción adicional |
|---|---|---:|---|---|
| **NORMAL** | DD < 5% | 100% | — | — |
| **CAUTION** | DD ≥ 5% | **75%** | DD < 3% | Log |
| **DEFENSIVE** | DD ≥ 8% | **50%** | DD < 5% | **Alerta Telegram** |
| **MINIMAL** | DD ≥ 12% | **25%** | DD < 8% | Alerta + revisión de modelos |
| **HALTED** | DD ≥ 15% | **0%** | **Manual únicamente** | **Kill switch: solo salidas** |

**Por qué la histéresis es obligatoria:** sin ella, un sistema oscilando alrededor del 5% de drawdown alterna entre 100% y 75% de sizing en días consecutivos, generando costes de transacción sin cambio de riesgo real. Los umbrales de salida son ~60% del de entrada.

**Definición precisa del drawdown a usar:** sobre el **equity mark-to-market incluyendo posiciones abiertas**, no sobre el equity realizado. Un sistema que mide DD solo sobre trades cerrados no ve su propio riesgo hasta que es tarde — es el modo de fallo clásico de los sistemas que "nunca cierran perdedores".

$$DD_t = \frac{\max_{s \leq t} E_s - E_t}{\max_{s \leq t} E_s}, \qquad E_t = \text{Cash}_t + \sum_i q_{i,t} \cdot p_{i,t}$$

**La transición a HALTED requiere intervención humana para revertirse.** Es deliberado: el 15% de drawdown es información sobre el modelo, no mala suerte, y reactivar automáticamente equivale a ignorar la única señal fuerte que el mercado ha dado sobre la validez del sistema.

---

### 5.4 Correlación dinámica y cobertura

**Matriz de correlación rodante con shrinkage.** La correlación muestral de 30 días sobre 28 activos es un estimador singular (28 activos requieren ≥ 28 observaciones solo para ser invertible, y muchas más para ser estable). Se aplica **Ledoit-Wolf shrinkage**:

$$\hat{\boldsymbol{\Sigma}}_{LW} = (1-\delta)\,\mathbf{S} + \delta\,\mathbf{F}, \qquad \mathbf{F} = \bar{\rho}\,\boldsymbol{\sigma}\boldsymbol{\sigma}^\top + \text{diag}(\boldsymbol{\sigma}^2 - \bar{\rho}\sigma_i^2)$$

con $\delta$ óptimo estimado analíticamente (`sklearn.covariance.LedoitWolf`). Ventana recomendada: **60 días**, no 30 — con 28 activos, 30 observaciones es insuficiente incluso con shrinkage.

**Reglas de exposición por correlación media del portafolio $\bar{\rho}$:**

| $\bar{\rho}$ | Posiciones simultáneas máximas | Multiplicador de sizing |
|---:|---:|---:|
| < 0.3 | 8 | 1.0× |
| 0.3 – 0.5 | 6 | 0.9× |
| 0.5 – 0.6 | 4 | 0.75× |
| 0.6 – 0.75 | 3 | 0.6× |
| > 0.75 | **2** | **0.4×** |

**Cobertura automática — con una advertencia importante.** El brief propone: cuando $\rho(\text{BTC}, \text{SPX}) > 0.8$, abrir XAUUSD como cobertura. La lógica es razonable (crypto deja de diversificar, el oro es el refugio residual) pero **el oro no es un hedge fiable**: su correlación con equities es inestable y en 2022 fue positiva durante la caída, porque el driver dominante eran los tipos reales, no el riesgo.

Implementación propuesta, más honesta:

```python
def hedge_decision(corr_matrix, macro, portfolio):
    # 1. Detectar pérdida de diversificación
    if corr_matrix["BTCUSDT"]["US500"] < 0.8:
        return None

    # 2. Verificar que el hedge candidato SIGUE siendo un hedge
    #    (condición que el brief omite y que es donde falla en la práctica)
    gold_equity_corr_60 = corr_matrix["XAUUSD"]["US500"]
    if gold_equity_corr_60 > -0.1:
        # El oro no está actuando como refugio en este régimen.
        # Reducir exposición es más fiable que cubrir con un hedge roto.
        return ReduceExposure(factor=0.6)

    # 3. Cobertura dimensionada por beta, no por notional
    beta = portfolio_beta_to_equity(portfolio)
    hedge_size = -beta * portfolio.notional * gold_equity_corr_60 / gold_vol_ratio
    return OpenHedge("XAUUSD", size=min(hedge_size, 0.25 * portfolio.notional))
```

**Principio general:** reducir exposición es un hedge que siempre funciona; comprar un activo correlacionado negativamente es un hedge que funciona hasta que deja de hacerlo, normalmente en el momento exacto en que hace falta.

---

## SECCIÓN 6 — Backtesting robusto y anti-overfitting

Esta sección es la implementación de ingeniería del diagnóstico de la Sección 0. Es, en la evaluación de este análisis, **el trabajo de mayor valor marginal de toda la propuesta**: sin él, cada mejora de las Secciones 2–5 se evalúa con un instrumento que produce Sharpe de 2.5 a partir de ruido.

### 6.1 Presupuesto de multiplicidad — el mecanismo que falta hoy

Antes de cualquier técnica, la infraestructura debe **contar los ensayos**. Hoy nada lo hace, y por eso el gate no puede deflactar nada.

```python
# core/ml/trial_registry.py  (NUEVO — prerequisito de todo lo demás)

@dataclass(frozen=True)
class Trial:
    trial_id: str          # hash del (estrategia, params, features, target, símbolo)
    timestamp: datetime
    strategy_id: str
    params: dict
    feature_set_hash: str
    symbol: str
    sharpe_is: float
    sharpe_oos: float
    n_obs: int
    span_years: float

class TrialRegistry:
    """Registro append-only, persistido en Postgres. Nunca se borra.

    Toda evaluación de estrategia — incluidas las exploratorias y las
    descartadas — DEBE registrarse. El número de ensayos es el input del
    Deflated Sharpe Ratio; un registro incompleto produce un DSR optimista,
    que es exactamente el fallo que este módulo existe para prevenir.
    """
    def register(self, trial: Trial) -> None: ...
    def n_trials(self, scope: str) -> int: ...
    def variance_of_sharpes(self, scope: str) -> float: ...
```

**Regla de gobernanza:** un backtest que no pase por el registro no puede citarse en ningún documento, reporte ni decisión. Esto convierte la disciplina estadística en un invariante del sistema y no en una intención.

### 6.2 Deflated Sharpe Ratio — el criterio de aceptación primario

$$DSR = \Phi\left(\frac{(\widehat{SR} - SR_0)\sqrt{T-1}}{\sqrt{1 - \hat{\gamma}_3 \widehat{SR} + \frac{\hat{\gamma}_4 - 1}{4}\widehat{SR}^2}}\right)$$

donde $\hat{\gamma}_3, \hat{\gamma}_4$ son el skew y la curtosis de los retornos (la corrección por momentos superiores importa mucho: una estrategia con skew negativo, como el carry, tiene un Sharpe menos fiable del que aparenta), y $SR_0$ es el **benchmark de selección**:

$$SR_0 = \sqrt{V[\{\widehat{SR}_n\}]}\left[(1-\gamma)\Phi^{-1}\!\left(1-\tfrac{1}{N}\right) + \gamma\,\Phi^{-1}\!\left(1-\tfrac{1}{Ne}\right)\right]$$

**Criterio de aceptación: DSR > 0.95.** Es decir, ≥95% de probabilidad de que el Sharpe verdadero supere el que produciría la búsqueda por azar.

**Aplicado retroactivamente al Gate I1 actual** (N=40, spans reales del repositorio):

| Símbolo | SR holdout | Span holdout | $SR_0$ (N=40) | t-stat vs 0 | **DSR aprox.** | Veredicto correcto |
|---|---:|---:|---:|---:|---:|---|
| XAUUSD | 1.323 | 0.48 a | 1.58 | 0.74 | **≈ 0.40** | **NO PASA** |
| US30 | 0.640 | 0.58 a | 1.43 | 0.49 | ≈ 0.31 | NO PASA (28 trades) |
| Resto | < 0 | ~0.5 a | 1.4–1.7 | < 0 | < 0.10 | NO PASA |

**El Gate I1 corregido debe reportar 0/8, no 1/8.** Esto es una mala noticia y también el resultado más valioso del análisis: sitúa al proyecto en la casilla correcta del tablero, que es "aún no hemos medido nada concluyente", en lugar de "tenemos un activo que funciona".

### 6.3 CPCV y probabilidad de sobreajuste del backtest (PBO)

**Combinatorial Purged Cross-Validation** (López de Prado, 2018, cap. 12): se parte la muestra en $N$ grupos y se evalúan todas las combinaciones de $k$ grupos como test, generando $\binom{N}{k}$ caminos backtest en lugar de uno.

```
Configuración recomendada:
    N = 8 grupos, k = 2  →  C(8,2) = 28 caminos de backtest
    Purga: eliminar observaciones del train cuyo label solape con el test
    Embargo: h + 5 barras después de cada bloque de test
```

$$PBO = P\left[\text{rank}_{OOS}(\text{estrategia ganadora IS}) < \text{mediana}\right]$$

Operativamente: para cada uno de los 28 caminos, se elige la mejor configuración según el in-sample y se mide su rango relativo out-of-sample. Si la ganadora in-sample cae por debajo de la mediana out-of-sample más de la mitad de las veces, la selección no tiene poder — que es la definición de sobreajuste.

| PBO | Interpretación | Acción |
|---:|---|---|
| < 0.15 | Selección robusta | Aprobar |
| 0.15 – 0.30 | Aceptable con reservas | Aprobar con sizing reducido |
| 0.30 – 0.50 | Selección débil | Rediseñar el espacio de parámetros |
| **> 0.50** | La selección es peor que aleatoria | **Descartar sin excepción** |

**Predicción de este análisis:** aplicado al setup actual (40 configuraciones, 2 años), se espera un PBO de **0.4–0.6**. Si el resultado es mucho menor, la implementación del CPCV debe auditarse antes de creerse el número.

### 6.4 Monte Carlo de caminos — las tres variantes necesarias

El brief pide reordenar aleatoriamente las operaciones históricas. Esa variante es la más débil de las tres y, por sí sola, engañosa:

| Variante | Qué hace | Qué mide | Qué NO detecta |
|---|---|---|---|
| **1. Permutación de trades** (la del brief) | Reordena los retornos de las operaciones | Dispersión del drawdown dado el conjunto de trades | Nada sobre si los trades eran replicables. **Destruye la autocorrelación** — infraestima el DD real |
| **2. Block bootstrap estacionario** | Remuestrea bloques de longitud aleatoria (media 20 barras) | Igual que 1 pero **preservando la autocorrelación y el clustering de volatilidad** | Sesgo de selección de estrategia |
| **3. Permutación de la señal** | Aleatoriza los timestamps de la señal manteniendo el precio | **Si el timing aporta información** — la pregunta que realmente importa | — |

**Recomendación: implementar las tres, con la 3 como criterio primario.**

```python
# Variante 3 — la más informativa y la que nadie implementa
def signal_permutation_test(prices, signal, n_perm=1000):
    """H0: el timing de la señal no aporta información.
    Se preserva la distribución marginal de la señal (misma exposición
    media, mismo turnover) y se destruye únicamente su alineación temporal
    con el precio. Si el Sharpe real no está en la cola de la distribución
    nula, la estrategia no aporta timing — solo exposición.
    """
    real = sharpe(strategy_returns(prices, signal))
    null = []
    for _ in range(n_perm):
        shuffled = circular_shift(signal, random_offset())   # preserva estructura
        null.append(sharpe(strategy_returns(prices, shuffled)))
    p_value = mean([s >= real for s in null])
    return real, percentile(null, [5, 50, 95]), p_value
```

**Criterios de aceptación:**

| Test | Umbral |
|---|---|
| Percentil 25 del Sharpe (block bootstrap) | **> 0.8** |
| Percentil 5 del Sharpe (block bootstrap) | > 0.0 |
| Percentil 95 del Max DD | < 20% |
| p-valor de permutación de señal | **< 0.01** |
| Ratio Sharpe_real / Sharpe_p95_nulo | > 1.2 |

### 6.5 Walk-forward optimization

```
Ventana de entrenamiento: 12 meses   (expanding recomendado sobre rolling)
Ventana de test:           3 meses   (sin solapamiento)
Embargo:                   h + 5 barras = 11 barras con h=6
Re-optimización:           por ventana, con el espacio de parámetros REDUCIDO
                           (≤ 8 combinaciones por estrategia, no 40)
```

**Métricas de estabilidad — el output que importa más que el Sharpe:**

$$\text{Estabilidad de parámetros} = 1 - \frac{1}{P}\sum_{j=1}^{P} \frac{\sigma(\theta_j^{ventanas})}{\bar{\theta_j}}$$

$$\text{Eficiencia WF} = \frac{SR_{OOS\ agregado}}{SR_{IS\ medio}}$$

| Métrica | Mínimo | Interpretación de fallo |
|---|---|---|
| Estabilidad de parámetros | > 0.6 | Parámetros óptimos que saltan cada ventana = la superficie de optimización es ruido |
| Eficiencia WF | **> 0.5** | < 0.3 significa que el 70% del rendimiento IS es sobreajuste |
| Consistencia de signo | ≥ 70% de ventanas positivas | Un Sharpe agregado positivo con 40% de ventanas positivas es una o dos ventanas afortunadas |

**Check automatizado prior-vs-backtest** (referido en §3.0):

```python
def sanity_check_vs_prior(backtest_sharpe, strategy_family):
    prior_hi = LITERATURE_PRIORS[strategy_family].upper   # p.ej. momentum: 0.9
    if backtest_sharpe > 2.0 * prior_hi:
        raise SuspiciousBacktestError(
            f"Sharpe {backtest_sharpe:.2f} excede 2x el máximo de la literatura "
            f"({prior_hi:.2f}) para {strategy_family}. Causas probables, en orden "
            f"de frecuencia: (1) look-ahead en features, (2) costes ausentes o "
            f"subestimados, (3) sesgo de supervivencia, (4) sobreajuste de "
            f"selección. Auditar antes de continuar."
        )
```

### 6.6 Out-of-sample final bloqueado

```
PROTOCOLO DE HOLDOUT SAGRADO

1. Reservar los últimos 6 meses de datos. Almacenados en un directorio con
   permisos distintos: data/holdout_locked/ (no leído por ningún pipeline
   de research, verificado por un test de CI).
2. UNA SOLA evaluación permitida, y únicamente cuando todos los demás gates
   hayan pasado.
3. El resultado se registra en el TrialRegistry con la marca `final_holdout`.
4. Si falla: la estrategia se rediseña SIN volver a usar esos datos. Cada
   evaluación adicional sobre el mismo holdout lo convierte en un conjunto de
   validación más, y su valor probatorio decae como 1/√k.
5. Cuando el holdout se agota (2-3 usos como máximo en la vida del proyecto),
   se sustituye por datos nuevos acumulados en producción — el único holdout
   verdaderamente incorruptible.
```

**Nota crítica de la Sección 0 aplicada aquí:** un holdout de 6 meses tiene $\hat\sigma(SR) = 1/\sqrt{0.5} = 1.41$. **No puede validar nada por sí solo.** Su función correcta es *falsar*: un holdout muy negativo es evidencia contra la estrategia; un holdout positivo no es evidencia a favor. Con la profundidad de datos actual, el holdout debe usarse como filtro de descarte, y la validación positiva debe apoyarse en CPCV + DSR + paper trading real.

### 6.7 Métricas de calidad mínimas — tabla revisada

Se conserva la tabla del brief y se añaden las filas que la Sección 0 demuestra imprescindibles (en **negrita**):

| Métrica | Mínimo | Objetivo | Crítico (descartar) |
|---|---|---|---|
| Sharpe ratio (neto, OOS) | ≥ 1.0 | ≥ 1.5 | < 0.7 |
| Sortino ratio | ≥ 1.2 | ≥ 2.0 | < 0.8 |
| Calmar ratio | ≥ 0.8 | ≥ 1.2 | < 0.5 |
| Win rate | ≥ 48% | ≥ 55% | < 42% |
| Profit factor | ≥ 1.3 | ≥ 1.6 | < 1.1 |
| Max Drawdown | ≤ 15% | ≤ 10% | > 20% |
| PBO | < 0.30 | < 0.15 | > 0.50 |
| Número de operaciones | ≥ 200 | ≥ 500 | < 100 |
| **Deflated Sharpe Ratio** | **> 0.90** | **> 0.95** | **< 0.75** |
| **Span de datos (años)** | **≥ 5** | **≥ 10** | **< 3** |
| **Eficiencia walk-forward** | **> 0.50** | **> 0.70** | **< 0.30** |
| **p-valor de permutación de señal** | **< 0.05** | **< 0.01** | **> 0.10** |
| **Nº de ensayos registrados** | **Declarado** | **≤ 20 por estrategia** | **Desconocido** |
| **Sharpe vs. prior de literatura** | **≤ 2× prior alto** | **dentro del rango** | **> 3× prior alto** |

**Sobre el "Sharpe ≥ 1.0" del brief y del gate QG-7.** Con la profundidad de datos actual, exigir Sharpe ≥ 1.0 sin exigir DSR es contraproducente: *fuerza* al proceso a buscar hasta encontrar un 1.0, y buscar es exactamente lo que infla el Sharpe medido. **El umbral de Sharpe sin umbral de DSR no es un filtro de calidad, es un incentivo al sobreajuste.** Las dos filas nuevas de DSR y nº de ensayos son las que convierten QG-7 en un gate real.

---

## SECCIÓN 7 — Proyecciones financieras y escenarios

### 7.1 Supuestos explícitos

Todo lo que sigue es condicional a estos supuestos. Cambiarlos cambia los resultados de forma no trivial, y se listan para que puedan ser auditados y discutidos uno por uno.

| Supuesto | Valor | Justificación / sensibilidad |
|---|---|---|
| Capital inicial | $10.000 USD | Del brief |
| Horizonte | 18 meses desde el inicio del paper trading | Del brief |
| **Volatilidad objetivo anualizada** | **10%** | **Supuesto añadido, imprescindible.** El brief da Sharpe pero no volatilidad, y el retorno = Sharpe × vol. Sin fijar vol, las proyecciones son indeterminadas. Un 10% es consistente con 2% de capital en riesgo por señal y 3–8 posiciones simultáneas parcialmente correlacionadas |
| Vol mensual implicada | 2.89% | $10\%/\sqrt{12}$ |
| Frecuencia de señales | 2–5 op./semana por clase de activo | Del brief; ~400–1.000 operaciones/año en total |
| Costes de transacción | 0.10% crypto, 0.02% forex, 0.05% índices | Del brief |
| Slippage | 0.05% normal, 0.15% alta volatilidad | Del brief |
| **Coste anual total estimado** | **1.8 – 3.5% del capital** | 500 op./año × ~0.05% medio de ida y vuelta sobre notional apalancado ~1× |
| Sizing | 2% del capital en riesgo por señal | Del brief (domina al Kelly, ver §5.1.1) |
| Distribución de retornos | Normal para la simulación base | **Simplificación optimista.** Los retornos reales tienen skew negativo y curtosis > 3, lo que empeora las colas. Se cuantifica en §7.5 |
| Reinversión | Compounding mensual | |

**Los Sharpe de los tres escenarios (0.8 / 1.2 / 1.8) son supuestos del brief, no proyecciones derivadas de evidencia.** A día de hoy la evidencia del proyecto no permite estimar el Sharpe verdadero: como se demostró en la Sección 0, el intervalo de confianza al 95% del Sharpe medido es de aproximadamente ±1.4, lo que hace que los tres escenarios sean **estadísticamente indistinguibles con los datos disponibles**. Esto es la afirmación más importante de esta sección y debe acompañar a cualquier presentación de las tablas siguientes.

### 7.2 Metodología de la simulación

Monte Carlo de 20.000 caminos por escenario, retornos mensuales $r_m \sim N(SR \cdot \sigma/12,\ \sigma/\sqrt{12})$, con drawdown medido sobre el equity mark-to-market y el pico móvil. Semilla fija (7) para reproducibilidad.

### 7.3 Proyección de capital — los tres escenarios

Capital mediano proyectado (USD), partiendo de $10.000:

| Mes | Conservador (SR 0.8) | Base (SR 1.2) | Optimista (SR 1.8) |
|---:|---:|---:|---:|
| 1 | 10.063 | 10.096 | 10.147 |
| 2 | 10.126 | 10.193 | 10.296 |
| 3 | 10.189 | 10.291 | 10.447 |
| 4 | 10.253 | 10.390 | 10.601 |
| 5 | 10.317 | 10.490 | 10.756 |
| 6 | 10.382 | 10.591 | 10.914 |
| 7 | 10.447 | 10.693 | 11.075 |
| 8 | 10.513 | 10.796 | 11.237 |
| 9 | 10.579 | 10.900 | 11.402 |
| 10 | 10.645 | 11.005 | 11.570 |
| 11 | 10.712 | 11.111 | 11.740 |
| 12 | 10.779 | 11.218 | 11.912 |
| 13 | 10.847 | 11.326 | 12.087 |
| 14 | 10.915 | 11.435 | 12.264 |
| 15 | 10.983 | 11.545 | 12.444 |
| 16 | 11.052 | 11.656 | 12.627 |
| 17 | 11.121 | 11.768 | 12.812 |
| 18 | **11.190** | **11.881** | **13.002** |

### 7.4 Dispersión, drawdown y meses en pérdida

| Métrica (18 meses) | Conservador | Base | Optimista |
|---|---:|---:|---:|
| Capital mediano final | $11.211 | $11.886 | $12.952 |
| **Percentil 10** | **$9.576** | **$10.186** | **$11.098** |
| Percentil 90 | $13.075 | $13.870 | $15.130 |
| Retorno anualizado mediano | **7.9%** | **12.2%** | **18.8%** |
| **Max DD mediano (p50)** | 7.1% | 6.0% | 4.7% |
| **Max DD p90** | **13.4%** | **11.1%** | **8.9%** |
| Max DD p95 | 15.8% | 13.1% | 10.5% |
| **Meses con pérdida (media de 18)** | **7.4** | **6.5** | **5.4** |
| **P(capital final < inicial)** | **18.0%** | **7.7%** | **1.6%** |
| P(activación del kill switch de DD 15%) | ~7% | ~3% | ~0.6% |

**Tres lecturas que estas cifras imponen y que ninguna presentación comercial suele hacer:**

1. **Incluso en el escenario optimista, más de 5 de cada 18 meses son negativos.** Un sistema con Sharpe 1.8 —excelente, top decil de la industria— pierde dinero el 30% de los meses. Cualquier expectativa de "meses consistentemente positivos" es incompatible con la aritmética.

2. **El escenario conservador tiene un 18% de probabilidad de terminar los 18 meses por debajo del capital inicial.** No por un fallo del sistema: es el resultado esperado de un Sharpe de 0.8 sobre un horizonte corto.

3. **El drawdown p90 del escenario conservador (13.4%) está a un paso del kill switch de 15%.** Con Sharpe 0.8, hay una probabilidad no despreciable (~7%) de que el sistema se auto-detenga sin haber hecho nada mal. Esto tiene una implicación de diseño: **el umbral de kill switch y el Sharpe esperado no son parámetros independientes.** Con Sharpe esperado de 0.8, o se sube el umbral a 18%, o se baja la volatilidad objetivo al 8%.

### 7.5 Corrección por colas gordas — el ajuste que las proyecciones normales omiten

La simulación anterior usa retornos normales. Los reales no lo son. Re-simulando con $t$-Student de 4 grados de libertad reescalada a la misma volatilidad y skew de −0.5:

| Métrica | Normal (base) | **t(4) con skew −0.5** | Deterioro |
|---|---:|---:|---|
| Max DD p90 | 11.1% | **~15–17%** | **+40%** |
| Max DD p95 | 13.1% | ~19–22% | +55% |
| P(kill switch 15%) | 3% | **~11%** | ×3.7 |
| Capital mediano | $11.886 | ~$11.800 | ≈ igual |

**La mediana apenas cambia; las colas empeoran sustancialmente.** Esta es la firma característica del riesgo real en trading: no aparece en la proyección central, aparece en la probabilidad de eventos que detienen el sistema. Cualquier proyección presentada a un inversor debe incluir esta fila.

### 7.6 Punto de equilibrio y comparación con benchmark

**Escenario base — breakeven.** El sistema no tiene coste fijo de capital (la infraestructura es propia), por lo que el breakeven contable es inmediato. El breakeven **estadísticamente significativo** —el momento en que se puede afirmar con 95% de confianza que el retorno no es azar— requiere:

$$T_{significancia} = \left(\frac{1.645}{SR}\right)^2 = \left(\frac{1.645}{1.2}\right)^2 = 1.88\ \text{años} \approx \mathbf{23\ meses}$$

**Es decir: con Sharpe 1.2, el horizonte de 18 meses del brief no es suficiente para demostrar que el sistema funciona.** Con Sharpe 0.8 harían falta 4.2 años. Este cálculo debe gobernar el cronograma de escalado de capital de la §7.7 — y es la razón de que el escalado propuesto sea más lento que el del brief.

**Comparación contra benchmarks** (referencias de largo plazo, no proyecciones):

| Benchmark | Retorno anual | Sharpe | Max DD histórico | Comentario |
|---|---:|---:|---:|---|
| SPY buy & hold | ~10% | ~0.5 | 34% (2020), 25% (2022) | El benchmark honesto para un sistema long-biased |
| BTC buy & hold | Muy variable | ~0.7–1.0 | **77%** (2018), 76% (2022) | Sharpe comparable, drawdown incompatible con capital gestionado |
| 60/40 clásico | ~7% | ~0.6 | 21% | |
| **TRADER AI base (SR 1.2)** | **12.2%** | **1.2** | **11% (p90)** | **La ventaja está en el Calmar (1.1 vs 0.29 de SPY), no en el retorno** |

**Argumento de valor correcto:** el sistema no promete batir a SPY en retorno — promete un retorno similar con un tercio del drawdown y correlación baja contra ambos benchmarks. Esa es la propuesta de valor defendible; "supera a bitcoin" no lo es.

### 7.7 Cronograma de escalado de capital

Se conserva la estructura del brief y se endurecen los criterios, por el argumento de §7.6 (18 meses no bastan para significancia con SR 1.2):

| Periodo | Capital comprometido | Criterio de promoción | Criterio de reversión |
|---|---|---|---|
| **Mes 1–3** | $0 (paper) | Pipeline estable 90 días sin incidentes; ≥150 operaciones registradas | — |
| **Mes 4–6** | **5%** del objetivo | Sharpe paper ≥ 0.8 **y** DSR > 0.90 **y** tracking error paper-vs-backtest < 30% | Cualquier fallo → volver a paper |
| **Mes 7–9** | **10%** | Sharpe live ≥ 0.6 en 3 meses **y** slippage real ≤ 1.5× el modelado | DD > 8% → congelar nivel |
| **Mes 10–12** | **25%** | Sharpe live ≥ 0.8 acumulado **y** cero activaciones de kill switch | DD > 10% → bajar un nivel |
| **Mes 13–18** | **50%** | Sharpe live ≥ 0.8 con ≥ 400 operaciones acumuladas | DD > 12% → bajar un nivel |
| **Mes 19–30** | **100%** | Sharpe live ≥ 0.8 sostenido ≥ 24 meses (umbral de significancia de §7.6) | — |

**Diferencia deliberada respecto al brief:** el brief llega al 100% del capital en el mes 18. Esta propuesta lo posterga al mes 19–30, porque el mes 18 cae *antes* del punto en que el resultado es estadísticamente distinguible del azar. Comprometer el 100% del capital sobre evidencia no concluyente es precisamente el error que toda la Sección 6 existe para evitar; sería incoherente aceptarlo en el cronograma financiero.

**Adicionalmente — la regla del "tracking error paper-vs-live".** El indicador más predictivo de fallo en el paso a real no es el Sharpe: es la divergencia entre el fill simulado y el real. Se propone medirlo desde el primer día:

$$TE = \frac{1}{N}\sum_i \left| \frac{p^{real}_i - p^{simulado}_i}{p^{simulado}_i} \right|$$

Si $TE > 1.5 \times$ el slippage modelado durante 2 semanas, se detiene el escalado independientemente del P&L. Un sistema rentable con un modelo de costes equivocado es un sistema que dejará de ser rentable al escalar.

### 7.8 Proyección a 5 años (escenario optimista, con reservas)

Con Sharpe 1.8 sostenido, vol 10%, sin aportes:

| Año | Capital mediano | Capital p10 | Capital p90 |
|---:|---:|---:|---:|
| 1 | $11.912 | $10.467 | $13.470 |
| 2 | $14.190 | $11.700 | $17.200 |
| 3 | $16.900 | $13.000 | $22.000 |
| 4 | $20.100 | $14.500 | $28.000 |
| 5 | **$24.000** | **$16.100** | **$35.700** |

**Advertencia obligatoria sobre esta tabla.** Proyectar un Sharpe de 1.8 a 5 años ignora el fenómeno mejor documentado del trading cuantitativo: **el decaimiento del alpha**. Las estrategias sistemáticas pierden entre el 30% y el 50% de su Sharpe out-of-sample tras su descubrimiento (McLean & Pontiff, 2016, sobre 97 anomalías publicadas). Una proyección honesta aplicaría $SR_t = 1.8 \times 0.85^t$, lo que da un capital a 5 años de aproximadamente **$18.500–19.500** en vez de $24.000. El proyecto ya tiene el módulo para detectar esto (`core/ml/alpha_decay_monitor.py`); la proyección debe ser coherente con su existencia.

**Tiempo para duplicar capital** (escenario optimista, con decaimiento del 15% anual de Sharpe): ~4.5 años. Sin decaimiento: 3.9 años. Con Sharpe base 1.2 y decaimiento: ~7 años. **El apalancamiento del negocio no está en el retorno compuesto sobre $10.000, sino en la escalabilidad del capital gestionado** — lo que traslada la discusión a la Sección 9.

---

## SECCIÓN 8 — Hoja de ruta técnica priorizada (16 semanas)

### 8.0 Desviación respecto al orden solicitado, y por qué

El brief especifica este orden: features → ensemble → estrategias → riesgo → backtesting robusto → paper → optimización → live. Esta propuesta lo reordena poniendo **datos y validación primero**:

| Sprint | Orden del brief | **Orden propuesto** | Razón del cambio |
|---|---|---|---|
| 1–2 | Feature engineering | **Profundidad de datos + registro de ensayos** | Sin span, ninguna feature puede validarse (Sección 0) |
| 3–4 | Ensemble (TFT, IF, meta) | **Backtesting robusto (CPCV, DSR, PBO)** | Sin medición fiable, entrenar más modelos amplifica el error |
| 5–6 | Estrategias + PBO | **Feature engineering P0/P1 con test de admisión** | Ahora sí es medible |
| 7–8 | Risk management | **Modelo panel global + validación** | El cambio arquitectónico de mayor impacto |
| 9–10 | Backtesting + MC | **Estrategias por régimen (≤4 activas)** | Con presupuesto de multiplicidad explícito |
| 11–12 | Paper multiactivo | **Risk management avanzado** | Sin cambios de fondo |
| 13–14 | Optimización + reentrenamiento | **Paper trading multiactivo** | Sin cambios de fondo |
| 15–16 | Live + auditoría | **Reentrenamiento automático + auditoría** | Live se pospone: §7.6 |

**Ningún entregable del brief se elimina.** El TFT (Sprint 3–4 del brief) se traslada a la condición de activación de §4.2, que probablemente no se cumpla dentro de las 16 semanas — se declara explícitamente en lugar de programarse y fallar en silencio.

---

### Sprint 1 (semanas 1–2) — Profundidad de datos y registro de ensayos

**Objetivo medible:** pasar de 2.0–2.9 años a **≥ 10 años** de historia por activo en ≥ 12 activos, y tener todo backtest contabilizado.

| Entregable | Archivo |
|---|---|
| Ingesta histórica extendida (Binance klines desde 2017, Dukascopy/HistData para FX desde 2010, Stooq/Yahoo para índices desde 2000) | `scripts/backfill_history.py` |
| Validador de calidad de datos (gaps, duplicados, splits, saltos imposibles, horarios de sesión) | `core/ingestion/data_quality.py` |
| `data/processed/` con features cacheadas y versionadas (gap #3 del plan maestro, abierto desde abril) | `core/features/feature_store.py` (extender) |
| **Trial registry** append-only en Postgres | `core/ml/trial_registry.py` + migración `008_trial_registry.py` |

**Criterio de éxito (binario):** `pytest tests/quant/test_data_coverage.py` verifica que ≥ 12 símbolos tienen ≥ 10 años de barras 1h **o** 1d sin gaps > 5 días, y que `TrialRegistry.n_trials()` devuelve un conteo no nulo tras correr el gate.

**Dependencias:** ninguna. Es el sprint raíz.

**Riesgo principal:** los datos 1h de FX/índices con 10+ años de profundidad no son gratuitos en todas las fuentes. **Mitigación:** degradar a 1d para el histórico profundo (2000–2020) y mantener 1h solo para 2020+. Un panel con 20 años de barras diarias es estadísticamente muy superior a 2 años de barras horarias para todo lo que no sea ejecución intradía — 5.000 observaciones diarias con 20 años de span dan $\hat\sigma(SR) = 0.22$ frente al 0.79 actual.

---

### Sprint 2 (semanas 3–4) — Backtesting robusto y gate honesto

**Objetivo medible:** que el Gate I1 produzca DSR y PBO, y que reporte el veredicto correcto sobre los datos actuales.

| Entregable | Archivo |
|---|---|
| CPCV con purga y embargo, 28 caminos | `core/ml/cpcv.py` |
| PBO sobre los caminos CPCV | `core/ml/pbo.py` |
| Deflated Sharpe Ratio + PSR consumiendo `TrialRegistry` | `core/ml/deflated_sharpe.py` |
| Tres variantes de Monte Carlo (permutación de trades, block bootstrap, permutación de señal) | `core/backtesting/monte_carlo.py` |
| Refactor del gate: `i1_gate_validator.py` (730 líneas, god file) → `gate_criteria.py` + `gate_runner.py` + `gate_report.py` | `core/ml/gates/` |
| Check automatizado prior-vs-backtest | `core/ml/sanity_checks.py` |
| Validación del cost model contra spread implícito Corwin-Schultz | `core/backtesting/costs.py` (extender) |

**Criterio de éxito (binario):** el gate re-ejecutado sobre los 8 activos actuales reporta DSR y PBO por activo, **y** el veredicto para XAUUSD pasa de PASS a NO-PASS (validación de que la deflación funciona). Adicionalmente: se rechaza automáticamente todo resultado con < 100 operaciones (caso US30).

**Dependencias:** Sprint 1 (trial registry).

**Riesgo principal:** el equipo interpreta el resultado "0/8" como un retroceso y presiona por relajar el criterio. **Mitigación:** documentar el resultado como el hallazgo esperado y planificado de este sprint, no como un fallo. El éxito del sprint es que el gate diga la verdad, no que apruebe.

---

### Sprint 3 (semanas 5–6) — Feature engineering P0/P1 con admisión estadística

**Objetivo medible:** ≥ 12 features nuevas implementadas, de las cuales las que sobrevivan al test de admisión del §2.0 (esperado: 5–9) entran al modelo.

| Entregable | Archivo |
|---|---|
| Yang-Zhang, Parkinson, Garman-Klass; **deduplicación del ATR** (deuda #10) | `core/features/volatility.py` |
| GARCH(1,1) con forecast | `core/features/garch.py` |
| VIX term structure, DXY, credit spread (FRED), correlaciones commodity-divisa | `core/features/cross_asset.py` |
| Funding rate como feature (crypto) | `core/features/crypto_microstructure.py` |
| Autocorrelación multi-ventana + variance ratio | `core/features/persistence.py` |
| Detección de saltos (BNS) | `core/features/jumps.py` |
| Pipeline de admisión: IC, t-stat, null-feature benchmark, SHAP | `core/ml/feature_admission.py` |
| Ingesta FRED + CBOE | `core/ingestion/providers/macro_client.py` |

**Criterio de éxito:** `feature_admission.py` produce un reporte con IC y t-stat por feature sobre el panel completo; ≥ 4 features superan |t| > 3 en ≥ 60% de los activos; las features rechazadas quedan registradas y **no** se incorporan.

**Dependencias:** Sprints 1–2.

**Riesgo:** ninguna feature nueva supera el umbral. **Mitigación:** es un resultado válido y valioso — significa que el edge no está en la ingeniería de features, y redirige el esfuerzo hacia el Sprint 4 (arquitectura panel) y hacia las estrategias estructurales (C2 carry, F1 carry), que no dependen de poder predictivo.

---

### Sprint 4 (semanas 7–8) — Modelo panel global

**Objetivo medible:** un único LightGBM panel con IC out-of-sample positivo y estable, comparado head-to-head contra los modelos por activo actuales.

| Entregable | Archivo |
|---|---|
| Dataset panel con normalización cross-sectional y embeddings de activo/clase | `core/ml/panel_dataset.py` |
| Target normalizado por volatilidad + sample weights por unicidad | `core/ml/target_engine.py` (extender) |
| Entrenamiento panel con `PurgedKFold`, embargo = h+5 | `core/ml/panel_trainer.py` |
| Isolation Forest por clase de activo integrado al kill switch | `core/ml/anomaly_detector.py` |
| HMM corregido: 4 estados, covarianza `diag` (cierra los 2 tests fallando) | `core/adaptation/hmm_regime_detector.py` |
| Meta-learner Ridge no-negativo con protocolo anti-leakage y calibración | `core/ml/meta_learner.py` |
| Comparativa panel vs. per-asset | `data/reports/panel_vs_asset_comparison.md` |

**Criterio de éxito:** IC OOS del modelo panel > 0.015 **y** ≥ IC del mejor modelo por activo, en ≥ 60% de los activos; los 2 tests de HMM pasan; el meta-learner supera el check de fuga (brecha R² IS/OOS < 3×).

**Dependencias:** Sprints 1–3.

**Riesgo:** el modelo panel no supera al per-asset. **Mitigación:** la comparativa es el entregable, no la victoria del panel. Si pierde, se documenta y se conserva el enfoque per-asset con las features nuevas — la decisión queda tomada con evidencia en vez de por preferencia.

---

### Sprint 5 (semanas 9–10) — Estrategias por régimen (máximo 4 activas)

**Objetivo medible:** 4 estrategias implementadas, backtested con CPCV+DSR+PBO, con presupuesto de ensayos declarado a priori.

| Entregable | Archivo |
|---|---|
| C2 Funding carry (delta-neutral, con gestión de margen) | `core/strategies/builtin/funding_carry.py` |
| F3 Pares cointegrados (con test ADF automático) | `core/strategies/builtin/cointegration_pairs.py` |
| I1 Trend MTF con confirmación semanal y gate de VIX | `core/strategies/builtin/trend_mtf.py` |
| M1 Oro macro (tipos reales + DXY + COT) | `core/strategies/builtin/gold_macro.py` |
| Matriz estrategia × régimen (§3.5) como configuración auditable | `core/strategies/regime_matrix.yaml` |
| Bloqueador de calendario macro con precedencia de kill switch | `core/risk/macro_calendar_blocker.py` |

**Criterio de éxito:** ≥ 2 de las 4 estrategias alcanzan DSR > 0.90 y PBO < 0.30 sobre ≥ 10 años de datos. Presupuesto de ensayos: **≤ 8 combinaciones de parámetros por estrategia**, declarado antes de correr y verificado por el `TrialRegistry`.

**Dependencias:** Sprints 1–2 (obligatorias), 3–4 (deseables).

**Riesgo:** ninguna alcanza DSR > 0.90. **Mitigación:** las estrategias de carry (C2, F1) son las de mayor probabilidad a priori porque su retorno es estructural (una prima de riesgo cobrada) y no predictivo. Si el sprint falla completo, el diagnóstico correcto es que el proyecto debe reposicionarse como plataforma de **gestión de riesgo y ejecución** sobre estrategias de carry conocidas, no como generador de alpha predictivo — un producto más pequeño, pero honesto y viable.

---

### Sprint 6 (semanas 11–12) — Risk management avanzado

**Objetivo medible:** el motor de riesgo aplica Kelly acotado, VaR/CVaR con EVT, drawdown escalonado con histéresis y correlación con shrinkage, todo auditado.

| Entregable | Archivo |
|---|---|
| Kelly fraccional acotado por el límite del 2% y por vol-target | `core/risk/position_sizer.py` (extender) |
| VaR/CVaR histórico + EVT (GPD sobre excedentes) | `core/risk/portfolio_risk_engine.py` (extender) |
| Máquina de estados de drawdown con histéresis | `core/risk/drawdown_state_machine.py` |
| Correlación Ledoit-Wolf + número efectivo de apuestas | `core/risk/correlation_engine.py` |
| Lógica de hedge con verificación de que el hedge sigue siéndolo | `core/risk/hedging.py` |
| Refactor de `mtf_sl_tp_manager.py` (810 líneas → 3 módulos) | `core/risk/mtf/` |

**Criterio de éxito:** cobertura de tests ≥ 90% en `core/risk/` (QG-1 exige 80%); simulación de estrés que verifica las 5 transiciones de estado de drawdown y su histéresis; todo cambio de parámetro de riesgo genera audit log (QG-6).

**Dependencias:** Sprint 5.

**Riesgo:** interacción no prevista entre kill switch, máquina de estados de DD y detector de anomalías (tres sistemas que pueden bloquear). **Mitigación:** definir una jerarquía de precedencia explícita y un test de integración que verifique que **ningún camino de código puede reactivar el trading sin pasar por todos los checks**.

---

### Sprint 7 (semanas 13–14) — Paper trading multiactivo con tracking

**Objetivo medible:** 14 días continuos de operación en papel sin intervención, con métricas comparadas contra backtest y benchmark.

| Entregable | Archivo |
|---|---|
| Ciclo end-to-end verificado con Postgres+Redis reales (paso 6 pendiente del plan maestro) | evidencia en `data/reports/e2e_run.md` |
| Tracking error paper-vs-backtest (§7.7) | `core/monitoring/tracking_error.py` |
| Benchmark tracking (SPY, BTC, 60/40) en el dashboard | `app/pages/` |
| Alertas Telegram por estado de DD y kill switch | `core/notifications/` (extender) |
| Reporte diario automatizado | `scripts/daily_report.py` |

**Criterio de éxito (binario):** 14 días × 24h sin caídas no gestionadas; ≥ 30 señales generadas y ejecutadas en papel; tracking error < 30%; todas las señales con explicación SHAP persistida y recuperable.

**Dependencias:** Sprints 1–6.

**Riesgo:** el gap ambiental documentado (sin Postgres real, el lifespan de la API cuelga). **Mitigación:** este sprint tiene como prerequisito duro levantar el entorno completo con Docker Compose; añadir timeout explícito a `asyncpg.create_pool` (bug ya identificado en la auditoría) para que el fallo sea inmediato y diagnosticable en lugar de un cuelgue.

---

### Sprint 8 (semanas 15–16) — Reentrenamiento automático y auditoría

**Objetivo medible:** el sistema se reentrena solo, no se auto-promociona, y pasa una auditoría de seguridad.

| Entregable | Archivo |
|---|---|
| Scheduler de reentrenamiento con los triggers de §4.6 | `core/adaptation/retraining.py` (extender) |
| Gate de promoción de modelo (4 criterios de §4.6) | `core/ml/model_validation_gate.py` (extender) |
| Monitor de alpha decay operativo con alertas | `core/ml/alpha_decay_monitor.py` (activar) |
| Auditoría de seguridad: `token_blacklist.py` extraído, rate limiting verificado, secretos rotados, permisos de `data/holdout_locked/` | varios |
| Playbook de emergencia (fallo de exchange, posición huérfana, kill switch, desconexión) | `docs/RUNBOOK_EMERGENCIA.md` |
| Actualización del `PLAN_MAESTRO.md` con el estado real | `PLAN_MAESTRO.md` |

**Criterio de éxito:** un reentrenamiento completo se ejecuta automáticamente y es **rechazado** por el gate de promoción en un test de simulación (verifica que el gate no es decorativo); `mypy --strict` con 0 errores en `domain/` y `application/` (QG-2, hoy 6 errores); playbook probado con un simulacro.

**Dependencias:** todos los anteriores.

**Riesgo:** presión para activar live trading al final de las 16 semanas. **Mitigación:** el criterio de §7.6 es explícito y numérico — con Sharpe 1.2 hacen falta 23 meses de evidencia. La semana 16 es el inicio del paper trading serio, no el final del proceso. `EXECUTION_MODE=paper` permanece bloqueado.

---

### 8.9 Resumen del roadmap y factibilidad

| Sprint | Semanas | Foco | Entregables | Esfuerzo estimado (1–2 personas) |
|---|---|---|---|---|
| 1 | 1–2 | Datos + registro de ensayos | 4 | 60–80 h |
| 2 | 3–4 | Backtesting honesto | 7 | 70–90 h |
| 3 | 5–6 | Features P0/P1 | 8 | 70–90 h |
| 4 | 7–8 | Modelo panel | 7 | 80–100 h |
| 5 | 9–10 | Estrategias | 6 | 70–90 h |
| 6 | 11–12 | Riesgo | 6 | 60–80 h |
| 7 | 13–14 | Paper trading | 5 | 50–70 h |
| 8 | 15–16 | Automatización + auditoría | 6 | 50–70 h |
| | | **Total** | **49** | **510–670 h** |

Con 1 persona a tiempo completo (~35 h/semana efectivas × 16 = 560 h) el plan es **ajustado pero factible**; con 2 personas hay holgura para absorber los riesgos identificados. El plan es ejecutable en gran medida porque **no requiere construir infraestructura nueva**: el 70% del esfuerzo es sobre módulos que ya existen.

**Los tres sprints que no son negociables** si hubiera que recortar: 1 (datos), 2 (validación) y 7 (paper end-to-end). Sin ellos, los otros cinco producen código que no puede evaluarse.

---

## SECCIÓN 9 — Resumen ejecutivo y diferenciadores

### 9.1 Los cinco diferenciadores reales

**1. Honestidad estadística exigible por construcción.**
Ningún competidor retail deflacta el Sharpe por el número de ensayos. 3Commas, Cryptohopper y el marketplace de MT5 publican backtests sin corrección de multiplicidad, sin purga y sin embargo — el equivalente a publicar un ensayo clínico sin grupo de control. TRADER AI puede ser el único producto retail donde **el número de configuraciones probadas es un dato registrado y auditable**, y donde el criterio de aprobación es el Deflated Sharpe Ratio, no el Sharpe. Es un diferenciador difícil de copiar porque exige aceptar públicamente que la mayoría de las estrategias no funcionan — algo estructuralmente incompatible con el modelo de negocio de un marketplace de señales.

**2. Riesgo de portafolio cross-asset, no riesgo por posición.**
Todos los competidores gestionan el riesgo trade a trade. Ninguno calcula VaR/CVaR de portafolio, número efectivo de apuestas, ni ajusta el sizing por la correlación dinámica entre posiciones. Un usuario de 3Commas con 6 bots de altcoins cree tener 6 posiciones diversificadas; tiene una posición apalancada 6× en beta de BTC. El código de TRADER AI ya distingue ambas cosas.

**3. Multiactivo real con cobertura cruzada de clases.**
Cinco adaptadores de exchange unificados bajo una interfaz común (trabajo completado el 2026-07-27), cuatro clases de activo operativas. Esto permite algo estructuralmente imposible para un producto crypto-only: **reducir exposición crypto cuando la correlación con equity supera un umbral, y rotar hacia oro cuando el oro sigue comportándose como refugio**. Es la diferencia entre diversificación nominal y diversificación real.

**4. Explicabilidad por señal (SHAP) unida a fail-safe verificado.**
Cada señal lleva su descomposición de contribuciones. Combinado con un kill switch verificado como fail-closed (si Redis cae, el trading se bloquea, no continúa), da algo que ningún competidor ofrece: **el usuario puede auditar por qué se abrió una posición y confiar en que el sistema se detiene cuando su propia infraestructura falla**. La mayoría de los sistemas retail fallan abiertos — siguen operando cuando pierden el estado.

**5. Un cronograma de escalado de capital gobernado por significancia estadística, no por calendario.**
El sistema no compromete el 100% del capital hasta que la evidencia acumulada permite rechazar la hipótesis nula (§7.6, ~23 meses con Sharpe 1.2). Ningún producto retail condiciona el despliegue de capital a un umbral de potencia estadística. Es el diferenciador menos vistoso y el que más dinero protege.

### 9.2 El argumento cuantitativo: ¿por qué es plausible generar alpha sostenido?

El argumento **no** es que un modelo de ML descubra patrones invisibles. Los mercados líquidos son razonablemente eficientes y esa afirmación es, en general, falsa a escala retail. El argumento es que existen **primas de riesgo estructurales, documentadas y persistentes** que un sistema disciplinado puede cosechar, y que la ventaja está en la *ejecución disciplinada de la cosecha*, no en la predicción:

| Fuente de retorno | Mecanismo económico | Evidencia académica | Estrategia en esta propuesta |
|---|---|---|---|
| **Momentum de series temporales** | Difusión lenta de información, comportamiento de rebaño | Jegadeesh & Titman (1993); Moskowitz, Ooi & Pedersen (2012), 58 instrumentos, 25 años | C1, I1 |
| **Carry** | Compensación por riesgo de crash y de liquidez | Lustig & Verdelhan (2007); Koijen et al. (2018), "Carry", 6 clases de activo | F1, C2 |
| **Basis / funding en perpetuos** | Compensación por proveer apalancamiento a especuladores | Estructura de mercado observable, no anomalía | C2 |
| **Prima de iliquidez** | Compensación por coste de ejecución | Amihud (2002) | Sizing y selección de activos |
| **Reversión a corto plazo** | Presión de liquidez temporal, market making | Lo & MacKinlay (1990) | F3, I2 |
| **Prima de riesgo de volatilidad** | Aversión al riesgo asimétrica | Bollerslev, Tauchen & Zhou (2009) | Capa 3.3, gates de VIX |
| **Factores de riesgo cross-sectional** | Compensación por exposición factorial | Fama & French (1993, 2015) | Modelo panel (§4.0) |

**El diferencial de TRADER AI no está en descubrir estas primas —son públicas— sino en tres cosas:** (i) cosechar varias simultáneamente con correlación baja entre ellas, lo que multiplica el Sharpe agregado por aproximadamente $\sqrt{N_{eff}}$; (ii) no destruirlas con costes de transacción, mediante un cost model realista y validado; (iii) no abandonarlas en el peor momento, mediante reglas de drawdown mecánicas.

**La aritmética de la diversificación de fuentes.** Cuatro estrategias con Sharpe individual de 0.6 y correlación media de 0.2 entre ellas producen:

$$SR_{portfolio} = \frac{\sum w_i SR_i}{\sqrt{\mathbf{w}^\top \boldsymbol{\Sigma}_\rho \mathbf{w}}} = \frac{0.6}{\sqrt{\frac{1 + 3(0.2)}{4}}} = \frac{0.6}{0.632} = \mathbf{0.95}$$

Éste, y no un modelo mejor, es el camino realista al Sharpe > 1: **cuatro fuentes mediocres y poco correlacionadas superan a una fuente buena.** Es también un objetivo mucho más robusto, porque no depende de que ninguna estrategia individual sea excepcional.

### 9.3 El riesgo principal del negocio y cómo la arquitectura lo mitiga

**El riesgo principal no es perder dinero en el mercado. Es creer que se tiene edge cuando no se tiene, y escalar capital sobre esa creencia.**

Es el modo de fallo que ha destruido más capital retail que cualquier crash, y el proyecto ya estuvo a un paso de materializarlo: un Gate I1 que reportaba "APPROVED 8/8" ignorando un holdout negativo en 6 de 8 activos habría autorizado el avance a estrategias avanzadas y, eventualmente, a capital real. Ese error se detectó y se corrigió. El análisis de la Sección 0 muestra que **la corrección se quedó a medio camino**: el gate corregido sigue reportando un PASS (XAUUSD) que no sobrevive a la deflación por multiplicidad.

Mitigaciones arquitectónicas, en orden de fuerza:

| Mitigación | Estado | Efecto |
|---|---|---|
| Trial registry append-only | Por construir (Sprint 1) | Hace imposible reportar un Sharpe sin declarar cuántos ensayos costó |
| DSR como criterio de aprobación | Por construir (Sprint 2) | Convierte la multiplicidad en un coste explícito |
| Holdout bloqueado con permisos separados y test de CI | Por construir (Sprint 2) | Elimina la contaminación accidental |
| Escalado de capital por significancia | Definido (§7.7) | Limita el daño de un falso positivo a una fracción del capital |
| Drawdown escalonado + kill switch fail-closed | **Ya implementado y verificado** | Acota la pérdida máxima estructuralmente |
| Alpha decay monitor | Implementado, por activar (Sprint 8) | Detecta la degradación antes de que el drawdown la revele |

**Riesgos secundarios:** dependencia de un exchange único (mitigado: 5 adaptadores unificados); riesgo operativo de infraestructura (mitigado: fail-closed por defecto); riesgo regulatorio (bajo con capital propio, material si se convierte en SaaS con gestión de fondos de terceros — ver §9.4).

### 9.4 Visión a 3 años

| Horizonte | Estado objetivo | Condición de paso | Riesgo dominante |
|---|---|---|---|
| **Año 1** | Plataforma personal con edge demostrado en 2–4 fuentes de retorno; capital al 25–50% | DSR > 0.95 en ≥ 2 estrategias; 12 meses de paper/live con tracking error estable | Que no haya edge. Probabilidad no despreciable — y detectarlo barato es el objetivo del año |
| **Año 2** | Capital al 100%; track record auditado de 24 meses; alpha decay bajo control | Sharpe live ≥ 0.8 sostenido 24 meses | Decaimiento del alpha más rápido que la capacidad de reemplazo |
| **Año 3 — vía A: SaaS** | Producto de señales + gestión de riesgo, no de ejecución discrecional | Track record público y verificable; el diferenciador de honestidad estadística como argumento comercial central | Riesgo regulatorio (asesoramiento financiero); riesgo reputacional si el sistema falla públicamente |
| **Año 3 — vía B: fondo cuantitativo** | Vehículo con capital de terceros | Track record auditado externamente ≥ 24 meses; infraestructura de compliance (parcialmente ya construida) | Regulatorio (licencia de gestión); capacidad de la estrategia; la exigencia de capital mínimo |

**Recomendación estratégica.** La vía A (SaaS) tiene una asimetría favorable: el diferenciador de honestidad estadística es **más vendible como producto de información que como fondo**, porque no exige que las estrategias sean excepcionales — exige que la evaluación sea creíble. Un producto que le dice a un usuario "esta estrategia tiene un DSR de 0.4, no la operes" tiene valor incluso cuando la respuesta es negativa, y no existe hoy en el mercado retail. La vía B exige un track record que la aritmética de §7.6 sitúa a 24+ meses vista, y capital y compliance que multiplican el coste fijo.

### 9.5 Conclusión de una página

TRADER AI tiene, hoy, más infraestructura construida y verificada que la mayoría de los productos con los que compite: cinco adaptadores de exchange unificados, motor de riesgo con CVaR, kill switch fail-closed verificado, arquitectura hexagonal, XAI por señal, 356 tests pasando, validación temporal con purga real. Lo que no tiene es **evidencia de que genere alpha**, y el análisis de la Sección 0 muestra que con 2–3 años de datos y 40 configuraciones probadas por activo, **es imposible tenerla**: el instrumento de medición produce Sharpe de 1.5–2.3 a partir de puro ruido, y su holdout tiene un error estándar de ±1.4 Sharpe.

Esto no es una mala noticia si se actúa en consecuencia. Es la diferencia entre un proyecto que va a descubrir su problema dentro de 18 meses y $10.000 de capital, y uno que lo descubre en 4 semanas y lo corrige. Las dos intervenciones que lo resuelven —**profundidad de datos** y **medición deflactada por multiplicidad**— son las dos primeras semanas de trabajo del roadmap, no requieren tecnología nueva, y hacen que todo el trabajo posterior sea evaluable.

La ventaja competitiva del producto no es su stack de IA; ninguna arquitectura de modelos es defendible durante mucho tiempo. Es que sea **el único sistema retail que puede demostrar, con un procedimiento auditable, que lo que reporta es real**. En un mercado donde el competidor mediano publica un Sharpe de 3 sobre un backtest sobreajustado, poder decir "nuestro Sharpe es 0.9 y aquí está el DSR, el PBO, el número de ensayos y el holdout que no tocamos" es una posición estratégica que nadie más puede ocupar sin rehacer su producto desde los cimientos.

---

## Referencias

- Amihud, Y. (2002). Illiquidity and stock returns: cross-section and time-series effects. *Journal of Financial Markets*, 5(1), 31–56.
- Bailey, D. H., & López de Prado, M. (2014). The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting, and Non-Normality. *Journal of Portfolio Management*, 40(5), 94–107.
- Bailey, D. H., Borwein, J., López de Prado, M., & Zhu, Q. J. (2017). The Probability of Backtest Overfitting. *Journal of Computational Finance*, 20(4), 39–69.
- Barndorff-Nielsen, O. E., & Shephard, N. (2006). Econometrics of testing for jumps in financial economics using bipower variation. *Journal of Financial Econometrics*, 4(1), 1–30.
- Bollerslev, T., Tauchen, G., & Zhou, H. (2009). Expected stock returns and variance risk premia. *Review of Financial Studies*, 22(11), 4463–4492.
- Cont, R., Kukanov, A., & Stoikov, S. (2014). The price impact of order book events. *Journal of Financial Econometrics*, 12(1), 47–88.
- Corwin, S. A., & Schultz, P. (2012). A simple way to estimate bid-ask spreads from daily high and low prices. *Journal of Finance*, 67(2), 719–760.
- Easley, D., López de Prado, M., & O'Hara, M. (2012). Flow toxicity and liquidity in a high-frequency world. *Review of Financial Studies*, 25(5), 1457–1493.
- Fama, E. F., & French, K. R. (1993). Common risk factors in the returns on stocks and bonds. *Journal of Financial Economics*, 33(1), 3–56.
- Fama, E. F., & French, K. R. (2015). A five-factor asset pricing model. *Journal of Financial Economics*, 116(1), 1–22.
- Gu, S., Kelly, B., & Xiu, D. (2020). Empirical asset pricing via machine learning. *Review of Financial Studies*, 33(5), 2223–2273.
- Harvey, C. R., Liu, Y., & Zhu, H. (2016). …and the cross-section of expected returns. *Review of Financial Studies*, 29(1), 5–68.
- Jegadeesh, N., & Titman, S. (1993). Returns to buying winners and selling losers. *Journal of Finance*, 48(1), 65–91.
- Koijen, R., Moskowitz, T., Pedersen, L. H., & Vrugt, E. (2018). Carry. *Journal of Financial Economics*, 127(2), 197–225.
- Kyle, A. S. (1985). Continuous auctions and insider trading. *Econometrica*, 53(6), 1315–1335.
- Ledoit, O., & Wolf, M. (2004). A well-conditioned estimator for large-dimensional covariance matrices. *Journal of Multivariate Analysis*, 88(2), 365–411.
- Lim, B., Arık, S. Ö., Loeff, N., & Pfister, T. (2021). Temporal Fusion Transformers for interpretable multi-horizon time series forecasting. *International Journal of Forecasting*, 37(4), 1748–1764.
- Lo, A. W., & MacKinlay, A. C. (1990). When are contrarian profits due to stock market overreaction? *Review of Financial Studies*, 3(2), 175–205.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. (Caps. 4, 7, 11, 12 — unicidad, purged CV, backtesting, CPCV)
- Lustig, H., & Verdelhan, A. (2007). The cross section of foreign currency risk premia and US consumption growth risk. *American Economic Review*, 97(1), 89–117.
- McLean, R. D., & Pontiff, J. (2016). Does academic research destroy stock return predictability? *Journal of Finance*, 71(1), 5–32.
- Menkhoff, L., Sarno, L., Schmeling, M., & Schrimpf, A. (2012). Carry trades and global foreign exchange volatility. *Journal of Finance*, 67(2), 681–718.
- Moskowitz, T., Ooi, Y. H., & Pedersen, L. H. (2012). Time series momentum. *Journal of Financial Economics*, 104(2), 228–250.
- Yang, D., & Zhang, Q. (2000). Drift-independent volatility estimation based on high, low, open, and close prices. *Journal of Business*, 73(3), 477–492.

---

## Anexo A — Correspondencia con el repositorio actual

| Sección | Módulos existentes que se extienden | Módulos nuevos |
|---|---|---|
| S2 Features | `core/features/{indicators,hurst_engine,feature_store}.py` | `volatility.py`, `garch.py`, `cross_asset.py`, `persistence.py`, `jumps.py`, `crypto_microstructure.py` |
| S3 Estrategias | `core/strategies/builtin/*` (4 existentes) | `funding_carry.py`, `cointegration_pairs.py`, `trend_mtf.py`, `gold_macro.py`, `regime_matrix.yaml` |
| S4 Modelos | `core/models/asset_specific_models.py`, `core/adaptation/hmm_regime_detector.py`, `core/ml/{validation,target_engine,model_validation_gate}.py`, `core/consensus/voting_engine.py` | `panel_dataset.py`, `panel_trainer.py`, `meta_learner.py`, `anomaly_detector.py` |
| S5 Riesgo | `core/risk/*` (11 módulos existentes) | `drawdown_state_machine.py`, `correlation_engine.py`, `hedging.py`, `macro_calendar_blocker.py`, `core/risk/mtf/` |
| S6 Backtesting | `core/backtesting/{costs,engine,metrics}.py`, `core/ml/i1_gate_validator.py` | `trial_registry.py`, `cpcv.py`, `pbo.py`, `deflated_sharpe.py`, `monte_carlo.py`, `sanity_checks.py`, `core/ml/gates/` |
| S8 Datos | `core/ingestion/*` (6 adaptadores) | `backfill_history.py`, `data_quality.py`, `macro_client.py`, `eia_client.py` |

**Deudas técnicas del `PLAN_MAESTRO.md` que esta propuesta cierra:** #3 (god files: `mtf_sl_tp_manager`, `i1_gate_validator`), #5 (resultado de I1 metodológicamente válido), #10 (ATR duplicado), gap #3 (`data/processed/`), gap #6 (`core/optimization/` vacío), gap #13 (errores de mypy), y las investigaciones I2 (features con información real), I4 (regímenes destructores de valor) e I5 (Hurst por activo).

---

## Anexo B — Validación de estrategias adicionales aplicables

*Añadido el 4 de agosto de 2026, tras revisar el catálogo de estrategias contra las capacidades reales del repositorio y someter a las candidatas a un test empírico sobre `data/raw/`.*

### B.0 Criterios de admisión aplicados

Toda candidata se evaluó contra cinco filtros. Se descarta al primero que falle:

| Filtro | Pregunta | Por qué |
|---|---|---|
| **F1 — Mecanismo** | ¿El retorno es *estructural* (prima de riesgo cobrada) o *predictivo* (patrón que hay que encontrar)? | Las estructurales no requieren búsqueda de parámetros → no inflan $E[\max SR\mid H_0]$ |
| **F2 — Datos hoy** | ¿Se puede calcular con lo que hay en `data/raw/` y lo que exponen los adaptadores? | Una estrategia que necesita datos inexistentes no es una propuesta, es un deseo |
| **F3 — Coste paramétrico** | ¿Cuántos ensayos añade al presupuesto de §3.0.1? | Es la moneda real del sistema |
| **F4 — Correlación** | ¿Está descorrelacionada de las 4 ya propuestas y del beta de mercado? | Es de donde sale el Sharpe agregado (§B.5) |
| **F5 — Span requerido** | ¿Cuántos años necesita para ser medible? | Con 2–3 años, cualquier cosa que exija 20 está bloqueada |

### B.1 Hallazgo previo: una estrategia ya implementada que nunca se ha evaluado

`core/strategies/builtin/cross_sectional_momentum.py` (`cross_sectional_v1`) existe, está registrada en `strategy_registry.py:30`, y es referenciada por `meta_agent.py:161`, `hurst_engine.py:100` y `auto_adaptation.py:91`. **No aparece en `I1_STRATEGY_REGISTRY` (`core/ml/i1_strategies.py`), por lo que el Gate I1 nunca la ha evaluado.**

Además tiene dos limitaciones que la hacen inoperante hoy:

- Su universo está fijado a `CRYPTO_UNIVERSE = ("BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT")`, de los cuales **solo BTCUSDT y ETHUSDT tienen datos descargados**. Un ranking cross-seccional de 2 elementos es un signo, no un ranking.
- La interfaz `AbcStrategy.should_enter(features)` es *por símbolo*, y la estrategia lo sortea con un caché externo (`update_universe_momentum`). Cualquier estrategia cross-seccional o multi-pata choca con esta interfaz (ver §B.6).

**Acción:** no es una estrategia nueva que añadir — es una existente que hay que conectar al gate y ampliar de universo. Coste ≈ 6h, valor alto.

### B.2 Resultados empíricos sobre los datos del repositorio

> ⚠️ **SUPERSEDIDO por el Anexo C (2026-08-04).** Los resultados de esta subsección se midieron sobre el panel de 8 activos y 498 días que había en el repositorio. Tras descargar 25 años de histórico y repetir las mismas pruebas, **dos de las tres conclusiones cambian**: N3 (momentum cross-seccional) queda falsada y N1 (overnight) queda confirmada con mucha más fuerza. Se conserva esta subsección sin editar porque el contraste entre ambas mediciones es, en sí mismo, la mejor ilustración del argumento de la Sección 0: con 2 años de datos, una estrategia sin edge medía SR 0.78 y una con edge medía 1.35; con 25 años, la primera mide −0.26 y la segunda 0.62. **La muestra corta no daba estimaciones malas: daba estimaciones sin relación con la realidad.**

Tests ejecutados sobre `data/raw/` con barras diarias, señales desplazadas un período (sin look-ahead), **Sharpe bruto sin costes**. El panel alineado de 8 activos cubre 498 días (2024-04-08 → 2026-04-02) — limitado por el activo con menos historia.

**Test 1 — Descomposición overnight vs. intradía (índices, sesión cash 13:00–20:00 UTC):**

| Activo | Componente | n | Retorno anualizado | Vol | **Sharpe** | **t-stat** |
|---|---|---:|---:|---:|---:|---:|
| US500 | **Overnight** (cierre→apertura) | 729 | **+12.64%** | 9.4% | **1.35** | **2.30** |
| US500 | Intradía (apertura→cierre) | 730 | +4.92% | 12.6% | 0.39 | 0.66 |
| US30 | Overnight | 729 | +3.21% | 8.2% | 0.39 | 0.67 |
| US30 | Intradía | 730 | +9.18% | 11.5% | 0.80 | 1.36 |

**Test 2 — Momentum cross-seccional (long top 25% / short bottom 25%, escalado por volatilidad):**

| Lookback | n | Sharpe bruto | t-stat | Turnover diario |
|---:|---:|---:|---:|---:|
| 5 d | 498 | −0.21 | −0.29 | 0.80 |
| 12 d | 498 | +0.21 | 0.29 | 0.54 |
| 21 d | 498 | +0.65 | 0.91 | 0.45 |
| **63 d** | 498 | **+0.78** | 1.09 | 0.27 |
| 126 d | 498 | +0.15 | 0.21 | 0.22 |

**Test 3 — TSMOM agrupado (pooled, un solo parámetro para los 8 activos) vs. per-activo:**

| Configuración | Sharpe | t-stat |
|---|---:|---:|
| **Pooled, lookback 63 d** | **0.99** | 1.39 |
| Pooled, lookback 21 d | 0.87 | 1.22 |
| Per-activo, 63 d | BTC 0.17 · ETH 0.47 · EUR 0.04 · GBP −0.55 · JPY −0.13 · **XAU 1.28** · US30 0.70 · US500 0.65 | — |
| Per-activo, 21 d | BTC −0.25 · **ETH 1.20** · EUR 0.89 · GBP 0.41 · JPY 0.06 · XAU 0.30 · US30 −0.23 · US500 0.47 | — |

**Test 4 — Correlaciones:**

| Par | ρ |
|---|---:|
| Cross-seccional 21d ↔ TSMOM pooled 63d | 0.52 |
| Cross-seccional 21d ↔ US500 buy & hold | **−0.07** |
| TSMOM pooled 63d ↔ US500 buy & hold | **−0.10** |

### B.2.1 Lectura honesta de estos números

**Ninguno de estos resultados es significativo salvo el overnight de US500** (t = 2.30, y con 2 activos probados el umbral corregido sería t > 2.24 — pasa por poco). Los Sharpe de 0.78–0.99 tienen t-stats de 1.09–1.39: no rechazan H₀. Esto era esperable y **es coherente con el diagnóstico de la Sección 0**: 498 días de panel dan $\hat\sigma(SR) = 1/\sqrt{1.36} = 0.86$, así que cualquier Sharpe por debajo de ~1.4 es indistinguible de cero.

Lo que sí aportan estos tests es información **relativa**, que no depende de la significancia absoluta:

1. **El TSMOM pooled (SR 0.99) supera a 6 de los 8 modelos per-activo, usando un solo parámetro en lugar de ocho selecciones.** Es la demostración empírica, sobre los propios datos del repositorio, del argumento panel del §4.0. Y explica el patrón del Gate I1: per-activo, el "mejor" (XAUUSD 1.28) es en gran medida el ganador de una lotería de 8 boletos; pooled no hay lotería.
2. **El momentum cross-seccional tiene la forma esperada por la literatura**: nulo a 5–12 días, máximo a 21–63 días, decayendo a 126. Un patrón espurio no tendría por qué respetar la estructura de horizontes documentada. Es evidencia débil pero direccionalmente correcta.
3. **Ambas familias están descorrelacionadas del beta de equity (ρ ≈ −0.1).** Es el hallazgo con más valor práctico del anexo: son fuentes de retorno *aditivas*, no una reformulación del buy & hold.

### B.3 Estrategias validadas para incorporar

#### ✅ N1 — Descomposición overnight / intradía en índices (**P0, la más barata del catálogo**)

**Mecanismo (F1: estructural).** Prácticamente toda la prima de riesgo de renta variable se acumula fuera de la sesión de negociación. El mecanismo documentado es la compensación por asumir riesgo de gap sin poder ajustar la posición, más el efecto de la subasta de apertura (Lou, Polk & Skouras, 2019, "A tug of war: Overnight versus intraday expected returns").

```python
# N1 — Overnight equity premium. Cero parámetros libres.
ENTRADA:  comprar al cierre de la sesión cash (20:00 UTC)
SALIDA:   vender en la apertura siguiente (13:30 UTC + 5 min de settle)
FILTRO:   no operar si VIX > 30 (los gaps de pánico invierten el signo)
          no operar la víspera de FOMC/CPI (§3.2.4)
SIZING:   vol targeting sobre la vol overnight, no la total (son 9.4% vs 15%)
```

| Filtro | Evaluación |
|---|---|
| F1 Mecanismo | ✅ Estructural, con literatura y explicación económica |
| F2 Datos hoy | ✅ US30/US500 con barras 1h de sesión cash — **ya descargados** |
| F3 Coste paramétrico | ✅ **1 ensayo** (cero parámetros libres; los filtros son reglas duras) |
| F4 Correlación | ⚠️ Correlacionada con el beta largo de equity — es una descomposición de él, no una fuente nueva |
| F5 Span | ✅ Medible con 3 años; ya da t = 2.30 en US500 |

**Advertencia obligatoria: el resultado no replica en US30 (t = 0.67).** Dos índices, uno pasa y otro no. Con 2 ensayos eso está al borde de lo que produce el azar. **Antes de operarla hay que replicarla en ≥ 4 índices** (NAS100, DE40, UK100, JP225 — sin datos hoy) y sobre ≥ 10 años. Es la primera candidata a validar en el Sprint 1, precisamente porque es barata de comprobar.

**Coste real que puede matarla:** operar el gap exige cruzar el spread dos veces al día, ~500 veces al año. Con 0.05% de coste ida y vuelta, son ~2.5 puntos porcentuales anuales de un retorno bruto de 12.6%. **Debe backtestearse con el cost model antes de cualquier entusiasmo.**

---

#### ✅ N2 — TSMOM agrupado (pooled) multiactivo (**P0, el de mayor impacto estructural**)

**Mecanismo (F1: estructural).** Es la estrategia canónica de los CTA/managed futures: signo del retorno pasado, escalado por volatilidad inversa, sobre un universo amplio. Moskowitz, Ooi & Pedersen (2012) la documentan sobre 58 instrumentos y 25 años.

La diferencia con el `tsmom_v1` que ya existe en el repositorio es fundamental y no es de fórmula, es de **estimación**: hoy se optimiza `lookback` y `min_adx` por activo (6 combinaciones × 8 activos = 48 ensayos); pooled se fija **un solo lookback para todo el panel** (1–3 ensayos).

```python
# N2 — Pooled TSMOM. 1 parámetro para todo el sistema.
señal_i,t = sign( ret_i(t-63, t) )
peso_i,t  = señal_i,t / σ_i,t          # inverso de volatilidad
pesos     = pesos / Σ|pesos|            # normalización a exposición unitaria
# Overlay de protección contra crashes de momentum (Barroso & Santa-Clara, 2015):
escala_t  = σ_objetivo / σ_realizada(retornos_estrategia, 126d)
```

| Filtro | Evaluación |
|---|---|
| F1 Mecanismo | ✅ Estructural, la prima mejor documentada del universo multiactivo |
| F2 Datos hoy | ✅ 8 activos ya descargados; escala a 28 con el Sprint 1 |
| F3 Coste paramétrico | ✅ **1–3 ensayos** frente a los 48 del enfoque per-activo |
| F4 Correlación | ✅ ρ = −0.10 contra US500; ρ = 0.52 contra cross-seccional |
| F5 Span | ✅ Se beneficia directamente del panel: más activos → mayor Sharpe → menos span necesario |

**Overlay recomendado — protección contra crashes de momentum.** El momentum tiene un modo de fallo característico: pierde catastróficamente en los rebotes tras un pánico. Barroso & Santa-Clara (2015) demuestran que escalar la exposición por la volatilidad *realizada de la propia estrategia* (no del activo) casi duplica el Sharpe del momentum y elimina el skew negativo. Es una línea de código y aplica también a C1 e I1.

---

#### ✅ N3 — Momentum cross-seccional multiactivo (**P0, es la extensión de código ya escrito**)

**Mecanismo (F1: estructural).** Long a los activos con mayor momentum relativo, short a los de menor, dentro del universo. Asness, Moskowitz & Pedersen (2013, "Value and Momentum Everywhere") lo documentan en 8 mercados y 4 clases de activo simultáneamente.

**Por qué merece prioridad pese a no ser significativo en el test:** es la única familia de estrategias cuya potencia estadística **crece con el número de activos y no solo con el span**. Con 8 activos el test da t = 1.09; con 28 activos, el mismo edge subyacente produce un Sharpe agregado mayor (§B.5) y por tanto es detectable con menos años. Es la respuesta directa al problema de la Sección 0.

| Filtro | Evaluación |
|---|---|
| F1 Mecanismo | ✅ Estructural |
| F2 Datos hoy | ⚠️ Funciona con 8, necesita ≥ 15 para ser útil. **`cross_sectional_v1` ya está codificada** (§B.1) |
| F3 Coste paramétrico | ✅ **2 ensayos** (lookback + cuantil, ambos fijables por literatura: 63d, 25%) |
| F4 Correlación | ✅ ρ = −0.07 contra US500; ρ = 0.52 contra N2 (comparten factor momentum) |
| F5 Span | ✅✅ **Es la única que mejora con activos en vez de con años** |

**Restricción de implementación:** el universo de `cross_sectional_v1` debe pasar de las 4 cryptos hardcodeadas al panel completo, y la estrategia debe poder ver todos los símbolos a la vez (§B.6).

---

#### ✅ N4 — Paridad de riesgo entre clases de activo (**P1, capa de portafolio**)

**Mecanismo (F1: estructural).** No es una estrategia de señal: es una regla de asignación que iguala la contribución al riesgo de cada clase en lugar de igualar el capital. Su prima documentada (Asness, Frazzini & Pedersen, 2012) proviene del apalancamiento restringido de los inversores, que sobreponderan activos de alta volatilidad.

$$w_i \propto \frac{1}{\sigma_i}, \qquad \text{o, con correlaciones: } w_i \propto \frac{1}{(\boldsymbol{\Sigma}\mathbf{w})_i}$$

| Filtro | Evaluación |
|---|---|
| F1 Mecanismo | ✅ Estructural |
| F2 Datos hoy | ✅ Solo requiere volatilidades y correlaciones; `core/portfolio/portfolio_optimizer.py` ya existe |
| F3 Coste paramétrico | ✅ **0 ensayos** (no hay nada que optimizar) |
| F4 Correlación | ✅ Es ortogonal: modifica *cómo* se combinan las demás, no añade una señal |
| F5 Span | ✅ Estimar volatilidades necesita meses, no años |

**Es la incorporación con mejor ratio valor/riesgo de todo el anexo**, porque no puede sobreajustarse: no tiene parámetros que ajustar. Su efecto es subir el Sharpe agregado sin tocar ninguna señal.

---

#### ⚠️ N5 — Factor de fortaleza del dólar en FX (**P2, condicionada**)

Construir un índice sintético del dólar desde los 6 pares configurados y operar las desviaciones de cada par respecto al factor común:

$$\text{USD}_t = \frac{1}{6}\sum_i \text{sign}_i \cdot z(r_{i,t}), \qquad \varepsilon_{i,t} = r_{i,t} - \beta_i \cdot \text{USD}_t$$

| Filtro | Evaluación |
|---|---|
| F1 Mecanismo | ⚠️ **Predictivo**, no estructural — asume que $\varepsilon$ revierte |
| F2 Datos hoy | ⚠️ 3 de los 6 pares descargados (EURUSD, GBPUSD, USDJPY) |
| F3 Coste paramétrico | ⚠️ 4–6 ensayos (ventana β, umbral z, horizonte) |
| F4 Correlación | ✅ Probablemente baja |
| F5 Span | ⚠️ Requiere ≥ 5 años |

**Veredicto: shadow mode.** El mecanismo es plausible (es una generalización de F3, cointegración, a 6 dimensiones) pero es predictiva y con solo la mitad de los datos. No entra en producción hasta el Sprint 5 como muy pronto.

### B.4 Candidatas evaluadas y descartadas — con la razón

| Candidata | Filtro que falla | Detalle |
|---|---|---|
| **Ratio oro/plata (mean reversion)** | F2 | **XAGUSD no tiene datos** en `data/raw/`. Mecanismo bueno, cero parámetros. Reactivar tras el Sprint 1 |
| **Stat arb entre índices** (US30-US500, DE40-UK100) | F2 | Solo 2 índices con datos; DE40/UK100/NAS100/JP225 ausentes |
| **Cross-section cripto ampliada** | F2 | SOLUSDT y BNBUSDT están configurados pero **sin descargar** |
| **Roll yield / carry en futuros** (CL, GC, NG) | F2 | Requiere datos de curva de futuros; el adaptador IB está "Parcial" y no expone term structure |
| **Prima de riesgo de volatilidad** (venta de vol) | F2 | **No hay adaptador de opciones.** Ningún broker configurado permite operar opciones desde el sistema |
| **Betting Against Beta** (Frazzini & Pedersen) | F2 + F5 | Necesita un universo amplio de activos individuales; con 8 no hay dispersión de beta suficiente |
| **Estacionalidad agrícola** | F5 | Requiere ≥ 20 años (ya argumentado en §3.4, M3) |
| **Order Flow Imbalance intradía** | F2 | Exige pipeline de tick; el sistema opera en barras de 1h |
| **Efecto lunes / efectos de calendario menores** | F1 | Sin mecanismo económico; es exactamente el tipo de patrón que la §3.3 (I3) enseña a rechazar |
| **Copy trading / seguimiento de ballenas on-chain** | F1 | Sin mecanismo replicable; el edge publicado se erosiona por construcción |

**Nota sobre el patrón:** de 15 candidatas evaluadas, **7 fallan por falta de datos (F2), no por falta de mérito**. Es la confirmación más clara de que el Sprint 1 (profundidad y amplitud de datos) desbloquea más valor que cualquier otro trabajo: no solo hace medibles las estrategias existentes, sino que habilita 7 familias adicionales.

### B.5 La aritmética que justifica añadirlas

Multiplicador de Sharpe al combinar $N$ fuentes con correlación media $\rho$, y span necesario para demostrarlo:

$$SR_{agregado} = SR_{individual} \cdot \sqrt{\frac{N}{1 + (N-1)\rho}}, \qquad Y_{necesario} = \left(\frac{2.49}{SR_{agregado}}\right)^2$$

| N fuentes | ρ = 0.2 | ρ = 0.4 | SR agregado (individual 0.4, ρ=0.2) | **Años para demostrarlo** |
|---:|---:|---:|---:|---:|
| 1 | 1.00× | 1.00× | 0.40 | 39 años |
| 4 | 1.58× | 1.35× | 0.63 | 15.6 años |
| 8 | 1.83× | 1.45× | 0.73 | 11.6 años |
| 16 | 2.00× | 1.51× | 0.80 | 9.7 años |
| 28 | 2.09× | 1.54× | 0.84 | 8.8 años |

Y en sentido inverso — cuánto span exige cada nivel de Sharpe agregado:

| Sharpe agregado | Años necesarios (potencia 80%, α=0.05) |
|---:|---:|
| 0.6 | 17.2 |
| 0.8 | 9.7 |
| 1.0 | 6.2 |
| **1.2** | **4.3** |
| **1.5** | **2.7** |
| 1.8 | 1.9 |

**Ésta es la conclusión operativa del anexo, y modifica la estrategia del proyecto.** Existen dos palancas para hacer el sistema medible, y son multiplicativas:

- **Palanca A (Sprint 1): más span.** Pasar de 2.5 a 10 años reduce $\hat\sigma(SR)$ de 0.79 a 0.32.
- **Palanca B (este anexo): más fuentes descorrelacionadas.** Combinar 6–8 fuentes de Sharpe individual mediocre (0.4–0.6) con ρ ≈ 0.2 produce un Sharpe agregado de 0.73–1.1.

Con las dos: un sistema de Sharpe agregado ~1.2 sobre 10 años de datos es **demostrable con margen** (necesita 4.3 años, hay 10). Con ninguna de las dos —el estado actual: una fuente por activo, 2.5 años— haría falta el orden de 40 años. **Ésa es exactamente la distancia entre el proyecto de hoy y un proyecto que puede probar lo que afirma.**

### B.6 Bloqueadores técnicos detectados durante la validación

| # | Bloqueador | Evidencia | Impacto | Esfuerzo |
|---|---|---|---|---|
| B-1 | **`ExchangeAdapter` no expone funding rate ni open interest** | `core/ingestion/exchange_adapter.py:65-130` — solo klines, order book, balance, órdenes | **Bloquea C2 (funding carry), la estrategia de mayor Sharpe prior de la propuesta**, y la feature 5.2 | 8h (extender interfaz + los 2 clientes de crypto) |
| B-2 | **`AbcStrategy` es por símbolo** | `should_enter(features: FeatureSet)` recibe un único activo | Bloquea N3, N4 y cualquier estrategia multi-pata; `cross_sectional_v1` ya lo sortea con un caché externo (síntoma, no solución) | 12h (añadir `PortfolioStrategy` con `should_rebalance(panel)`) |
| B-3 | **`cross_sectional_v1` no está en `I1_STRATEGY_REGISTRY`** | `core/ml/i1_strategies.py` lista 8 estrategias, ninguna cross-seccional | Estrategia implementada que nunca se ha evaluado | 6h |
| B-4 | **6 de los 28 símbolos declarados no tienen datos** | XAGUSD, NAS100, DE40, UK100, SOLUSDT, BNBUSDT ausentes de `data/raw/` | Bloquea 7 familias de estrategias (§B.4) | Sprint 1 |

**B-1 y B-2 son prerequisitos, no mejoras.** Ambos deben entrar en el Sprint 1 junto con la ingesta de datos; sin ellos, tres de las cuatro estrategias validadas en este anexo no son implementables aunque los datos existan.

### B.7 Impacto en el roadmap de la Sección 8

| Sprint | Cambio |
|---|---|
| **Sprint 1** | **+ B-1** (funding rate en `ExchangeAdapter`) y **+ B-2** (`PortfolioStrategy` para estrategias de panel). +16–20h. Son prerequisitos de los Sprints 4 y 5 |
| **Sprint 2** | **+ N1 y N2 como primeros casos de prueba del gate deflactado.** Tienen 1–3 ensayos, así que su DSR es alto por construcción si el edge existe. Son el mejor test de que el gate nuevo funciona: si N2 pooled (SR 0.99, 1 ensayo) no supera a `tsmom_v1` per-activo (SR "3.32", 48 ensayos) en DSR, el gate está mal implementado |
| **Sprint 4** | **+ N4 (paridad de riesgo)** en la capa de portafolio — cero parámetros, sin riesgo de sobreajuste |
| **Sprint 5** | Cartera revisada de **6 estrategias** (no 4): C2 funding carry, F3 cointegración, M1 oro macro, **N1 overnight**, **N2 pooled TSMOM**, **N3 cross-seccional** — con un presupuesto conjunto de **≤ 40 ensayos**, no ≤ 4 estrategias. I1 trend MTF se absorbe en N2 (son la misma familia; mantener ambas sería duplicar la apuesta de momentum) |
| **Sprint 5** | N5 (factor USD) y las 7 familias bloqueadas por datos entran en **shadow mode** para acumular track record OOS real |

**Resumen del anexo:** de 15 candidatas evaluadas, **4 se incorporan** (N1, N2, N3, N4), 1 va a shadow mode (N5), 10 se descartan o quedan bloqueadas — 7 de ellas exclusivamente por falta de datos. Ninguna de las 4 incorporadas es un modelo nuevo ni una técnica exótica: tres son primas de riesgo documentadas desde hace más de una década y la cuarta es una regla de asignación sin parámetros. **El valor no está en su sofisticación, sino en que cuestan 4 ensayos entre las cuatro y están descorrelacionadas entre sí y del mercado** — que es, según §B.5, la única vía aritmética por la que este sistema puede llegar a demostrar lo que afirma dentro del horizonte de datos disponible.

---

## Anexo C — Ejecución del Sprint 1 y re-validación sobre histórico profundo

*4 de agosto de 2026. Descarga del universo completo con `scripts/download_data.py` y re-ejecución de todas las pruebas del Anexo B sobre 25 años de datos.*

### C.1 Datos adquiridos

| Clase | Símbolos | Span | Fuente |
|---|---|---|---|
| Crypto | BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT | 6.0–9.0 a | Binance REST (1d + 1h) |
| Forex | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD | 20.2–25.0 a | Yahoo |
| Índices | US500, US30, NAS100, DE40, UK100, JP225 | 25.0 a | Yahoo |
| ETF replicables | SPY, QQQ, DIA | 25.0 a | Yahoo |
| Commodities | XAUUSD, XAGUSD, USOIL, UKOIL, NATGAS, WHEAT | 19.0–25.0 a | Yahoo |
| Macro | VIX, VIX3M, DXY, US10Y | 20.0–25.0 a | Yahoo |

**Total: 29 símbolos · span medio 21.8 años · 163.873 barras diarias · 285.897 barras horarias de crypto.** Frente al punto de partida (8 símbolos, 2.0–2.9 años), es un aumento de **~9× en span** y **~3.6× en amplitud**.

Calidad: 0 duplicados en 29 series; gaps > 5 días solo en JP225 (28, festivos japoneses) y DE40 (8); 61 barras FX (0.3%) con OHLC internamente inconsistente.

### C.2 El umbral de ruido, recalculado

$E[\max SR \mid H_0]$ — el Sharpe que produce la búsqueda de parámetros **sin ningún edge**:

| Escenario | Span | N=8 | **N=40** | N=320 |
|---|---:|---:|---:|---:|
| **ANTES** (8 activos, 1h, 2.0–2.9 a) | 2.0 a | 1.03 | **1.55** | 2.06 |
| AHORA — crypto | 9.0 a | 0.49 | **0.73** | 0.97 |
| AHORA — forex | 22.7 a | 0.31 | **0.46** | 0.61 |
| AHORA — índices y commodities | 25.0 a | 0.29 | **0.44** | 0.58 |

**El listón baja de 1.55 a 0.44.** Un Sharpe de 0.6 pasa de ser indistinguible del ruido a ser potencialmente significativo. Este único número es el retorno de la inversión del Sprint 1.

*Declaración de multiplicidad de este anexo:* se evaluaron ~40 configuraciones en total (4 lookbacks × 2 familias de momentum, 9 instrumentos para overnight, 3 horizontes de VIX, 2 reglas de asignación, 1 señal de oro). Todos los veredictos de abajo se contrastan contra el umbral de N=40, no contra cero.

### C.3 Resultados

Metodología: barras diarias, señales desplazadas 1 día (sin look-ahead), panel sobre calendario de días hábiles, costes explicitados donde aplican.

#### N1 — Descomposición overnight / intradía: **CONFIRMADA**

| Instrumento | n | Ret. overnight | **SR overnight** | **t** | SR intradía | SR buy&hold |
|---|---:|---:|---:|---:|---:|---:|
| **JP225** | 6.119 | +12.24% | **1.02** | **5.03** | −0.18 | 0.41 |
| **QQQ** | 6.284 | +10.57% | **0.81** | **4.03** | 0.22 | 0.63 |
| **DE40** | 6.345 | +7.67% | **0.72** | **3.64** | 0.04 | 0.38 |
| **NAS100** | 6.284 | +8.75% | **0.66** | **3.32** | 0.28 | 0.60 |
| **SPY** | 6.284 | +6.95% | **0.62** | **3.09** | 0.27 | 0.58 |
| **DIA** | 6.284 | +6.21% | **0.58** | **2.91** | 0.29 | 0.57 |
| **US500** | 6.284 | +3.25% | **0.57** | **2.82** | 0.34 | 0.49 |
| US30 | 6.284 | +1.46% | 0.29 | 1.42 | 0.40 | 0.46 |
| UK100 | 6.313 | +0.01% | 0.07 | 0.34 | 0.24 | 0.24 |

**7 de 9 instrumentos superan el umbral de 0.44, todos con t > 2.8.** Replica en tres mercados independientes (EE. UU., Alemania, Japón). El SR overnight supera al de buy & hold en 8 de 9 casos, capturando la mayor parte del retorno con menos exposición temporal.

Con costes (1 pb ida y vuelta, ETF líquidos): **QQQ 0.61 (t=3.07)**, SPY 0.39 (t=1.97), DIA 0.35 (t=1.73). Solo QQQ sobrevive con holgura — **el resultado es real pero el margen sobre costes es estrecho**, y depende críticamente de ejecutar en subasta de apertura/cierre y no cruzando spread.

#### N2 — TSMOM agrupado: **MARGINAL, salvo con el overlay**

| Lookback | SR bruto | t | SR neto | MaxDD | Mediana per-activo | % activos positivos |
|---:|---:|---:|---:|---:|---:|---:|
| 21 d | 0.13 | 0.65 | −0.24 | 27.6% | 0.04 | 55% |
| 63 d | 0.08 | 0.38 | −0.14 | 21.8% | 0.04 | 55% |
| **126 d** | **0.34** | 1.70 | 0.19 | 18.8% | 0.15 | **73%** |
| 252 d | 0.31 | 1.49 | 0.19 | 26.7% | 0.11 | 68% |

Con el **overlay Barroso–Santa-Clara** (escalar por la volatilidad de la propia estrategia):

| Lookback | SR sin overlay | **SR con overlay** | **t** | Skew |
|---:|---:|---:|---:|---|
| 63 d | 0.08 | **0.24** | 1.19 | −0.16 → +0.07 |
| 126 d | 0.34 | **0.48** | **2.37** | −0.18 → +0.16 |
| **252 d** | 0.31 | **0.57** | **2.76** | −0.43 → −0.30 |

El overlay sube el Sharpe **y** corrige el skew — exactamente lo que la literatura predice, replicado aquí. Con él, 126d y 252d superan el umbral de 0.44. **Veredicto: prometedora pero no concluyente.** El pooled (0.34) supera a la mediana per-activo (0.15) y el 73% de los activos son positivos individualmente, lo que respalda el argumento panel del §4.0; pero los costes se comen la mitad del edge bruto.

#### N3 — Momentum cross-seccional: **FALSADA**

| Lookback | SR bruto | t | Turnover | SR neto |
|---:|---:|---:|---:|---:|
| 21 d | −0.15 | −0.75 | 0.382 | −0.84 |
| 63 d | −0.26 | −1.31 | 0.250 | −0.72 |
| 126 d | −0.01 | −0.03 | 0.193 | −0.35 |
| 252 d | 0.13 | 0.62 | 0.143 | −0.13 |

**Ningún lookback es positivo neto de costes; ninguno alcanza |t| > 1.4 en bruto.** Sobre el panel de 8 activos y 2 años, el mismo test daba SR 0.78 a 63 días. Sobre 22 activos y 25 años da **−0.26**. La conclusión anterior era ruido, y este es el resultado más útil del anexo: **una falsación limpia que ahorra un sprint de trabajo.**

#### N4 — Reglas de asignación sin parámetros: **EL MEJOR RESULTADO DEL ESTUDIO**

| Regla | SR | **t** | Vol anual | MaxDD | Parámetros |
|---|---:|---:|---:|---:|---:|
| **Equiponderado (22 activos)** | **0.89** | **4.42** | 13.4% | 34.6% | **0** |
| **Paridad de riesgo (1/vol)** | **0.76** | **3.80** | 7.0% | **25.6%** | **0** |
| US500 buy & hold (referencia) | 0.49 | 2.43 | 19.1% | 56.8% | — |

Diversificar entre 22 activos sin optimizar nada bate al S&P 500 en Sharpe (0.89 vs 0.49) y en drawdown (34.6% vs 56.8%). La paridad de riesgo da el mejor perfil de drawdown (25.6%) con un tercio de la volatilidad del índice.

**Caveat honesto:** la cartera long-only incluye posiciones largas en pares FX (largo USDJPY = corto yen), que es una apuesta direccional al dólar y no una decisión neutra. El resultado es real pero está parcialmente influido por el ciclo del dólar y por el mercado alcista de metales del periodo.

#### Combinación de fuentes

| Cartera | SR | t | Span |
|---|---:|---:|---:|
| Solo overnight SPY | 0.68 | 3.38 | 24.9 a |
| Solo TSMOM 126d | 0.34 | 1.70 | 24.4 a |
| **TSMOM + overnight (equirriesgo)** | **0.81** | **4.00** | 24.4 a |
| TSMOM + overnight + cross-seccional | 0.41 | 2.01 | 24.4 a |

La combinación de las dos fuentes que funcionan (0.68 y 0.34) da **0.81** — más que cualquiera por separado. Es la aritmética de §B.5 verificada empíricamente. Añadir la fuente falsada (N3) **destruye** el resultado, bajándolo a 0.41: es la demostración de por qué el presupuesto de ensayos y el criterio de descarte importan tanto como la búsqueda de estrategias.

#### Otros resultados

| Test | Resultado |
|---|---|
| **VIX term structure** | IC = −0.128 a 21d, **t = −9.11**, n = 5.023. **Signo opuesto al que asumía §Capa 4.2**, ya corregido en el documento. El IC más significativo de todo el catálogo |
| **Oro vs. DXY** | corr = **−0.401** sobre 6.261 días — la relación de la §3.4/M1 se confirma. Pero la señal ingenua ("DXY baja → largo oro", media móvil 20d) da **SR 0.06, t = 0.31**: la correlación existe y no es explotable así. M1 necesita la especificación completa (tipos reales + COT), no solo el DXY |

### C.4 Veredicto consolidado

| Fuente | SR | t | Umbral N=40 | Veredicto |
|---|---:|---:|---:|---|
| **N4 Equiponderado / paridad de riesgo** | 0.89 / 0.76 | 4.42 / 3.80 | 0.44 | ✅ **SUPERA con holgura** |
| **N1 Overnight (bruto)** | 0.57–1.02 | 2.8–5.0 | 0.44 | ✅ **SUPERA en 7/9** |
| **N1 Overnight (neto de costes)** | 0.35–0.61 | 1.7–3.1 | 0.44 | 🟡 **solo QQQ con holgura** |
| **N2 TSMOM pooled + overlay** | 0.48–0.57 | 2.4–2.8 | 0.44 | 🟡 **marginal** |
| N2 TSMOM pooled (bruto) | 0.34 | 1.70 | 0.44 | ❌ no supera |
| **N3 Cross-seccional** | −0.26 | −1.31 | 0.44 | ❌ **falsada** |

### C.5 Hallazgos de calidad de datos (todos nuevos)

| # | Hallazgo | Gravedad | Implicación |
|---|---|---|---|
| C-1 | **`US500_1d.parquet` y `US30_1d.parquet` contenían precios de SPY y DIA (ETF), no de los índices** — escala 483–694 y 366–500 frente a 4.983–7.737 y 37.646–54.086 | 🔴 **Alta** | Datos mal etiquetados en el repositorio desde antes de este trabajo. Los retornos son similares pero no idénticos (el ETF excluye dividendos y tiene tracking error). Ficheros reconstruidos limpios |
| C-2 | Los `open` de los índices cash de Yahoo tienen ticks corruptos: **US30 con un retorno overnight de +9.935%** | 🔴 Alta | Cualquier estrategia que use aperturas de índice cash (N1, I2 gap reversion) queda envenenada. **Los ETF son la fuente correcta**: sus open/close son precios transaccionados |
| C-3 | USOIL con precio ≤ 0 el 2020-04-20 | 🟢 **No es un error** | Es el WTI negativo real. Un validador que lo "corrija" destruiría un dato verdadero |
| C-4 | NATGAS y USOIL con saltos > 20% en fin de mes | 🟡 Media | Gaps de *roll* de los futuros continuos (`NG=F`, `CL=F`), no movimientos de mercado. Deben ajustarse por roll antes de backtestear |
| C-5 | 61 barras FX (0.3%) con OHLC internamente inconsistente | 🟢 Baja | Calidad conocida de Yahoo en FX |

**C-1 y C-2 juntos explican por qué la primera pasada de tests dio volatilidad del 183% para el S&P y drawdowns del 643%.** Ninguno de los dos habría sido detectado por una revisión de código: solo aparecen al mirar los datos.

### C.6 Bugs corregidos en `scripts/download_data.py`

El script existía y su arquitectura era correcta (paginación, detección de gaps, merge incremental). Tenía cinco defectos que lo hacían inservible para este trabajo:

| # | Bug | Efecto | Corrección |
|---|---|---|---|
| 1 | `yfinance` declarado en `requirements-data.txt` pero **no instalado** en el `.venv` | Los 6 símbolos no-crypto fallaban con `ImportError` sin capturar | Instalado (v1.5.2) |
| 2 | **El modo incremental solo extiende hacia adelante.** Sobre un fichero que ya llega a hoy devolvía "actualizado" y no descargaba nada | Imposible profundizar histórico existente — el bloqueo principal | Flag `--backfill` |
| 3 | `if not raw: break` abortaba en la **primera ventana vacía** | **SOLUSDT descargaba 0 filas** (listó en 2020; el primer lote de 1.000 días acababa en 2019). Afecta a todo símbolo listado después del primer lote | Avanza la ventana; corta tras 200 lotes vacíos |
| 4 | Merge de `timestamp` **tz-naive con tz-aware** (los ficheros del repo son heterogéneos: `US500` era tz-aware, `BTCUSDT` tz-naive) | `ValueError` al fusionar | Normalización a UTC antes del concat |
| 5 | Todos los símbolos pasaban primero por Binance | 400 espurio y traza de error en 6 de cada 8 descargas | Enrutado por `BINANCE_NATIVE_SYMBOLS` |

Además se amplió el universo de 8 a **29 símbolos** (los 28 de `PLAN_MAESTRO.md` + macro + ETF).

**Bug en la metodología de prueba, no en el repositorio:** la primera pasada de tests de panel construía el índice como unión de fechas de crypto (24/7) y TradFi (5 días). Cada fin de semana inyectaba un `NaN` en las series TradFi, y `rolling(60).std()` con `min_periods` por defecto propagaba ese `NaN` a la ventana entera — la volatilidad de todos los activos TradFi quedaba nula a partir de 2017 y la cartera pasaba a ser **crypto-only sin ningún aviso**. Se documenta porque es el tipo de fallo silencioso que el `data_quality.py` del Sprint 1 debe detectar: no lanza excepción, no deja rastro en logs, y produce resultados plausibles.

### C.7 Qué cambia en el plan

| Cambio | Detalle |
|---|---|
| **Sprint 1: parcialmente completado** | Ingesta ejecutada (29 símbolos, 21.8 años de media). Pendiente: `data_quality.py` — los hallazgos C-1 a C-5 son su especificación de requisitos, escrita a partir de fallos reales |
| **N3 sale de la cartera** | Falsada. Libera 2 ensayos del presupuesto y ~1 sprint de trabajo |
| **N4 sube a P0 y a la cartera base** | Mejor resultado del estudio, cero parámetros, imposible de sobreajustar |
| **N1 pasa a depender de la ejecución** | El edge bruto es sólido (t hasta 5.03) pero neto sobrevive con holgura solo en QQQ. El trabajo siguiente **no es más investigación de señal, es investigación de ejecución**: subastas de apertura/cierre en vez de cruzar spread |
| **N2 requiere el overlay para ser viable** | Sin él no supera el umbral; con él sí. El overlay pasa de "mejora opcional" a componente obligatorio |
| **Capa 4.2 (VIX) corregida de signo** | Ya aplicado en la Sección 2 |
| **Gate I1 debe re-ejecutarse** | Sobre 25 años en vez de 2. Es la pieza que falta para cerrar la Sección 0: con el umbral en 0.44 en vez de 1.55, el veredicto puede cambiar en cualquier dirección — y esta vez significará algo |

**La conclusión de fondo del anexo.** Antes de este trabajo, el proyecto tenía ocho estrategias con Sharpe reportado de 1.7–3.3 y ninguna con evidencia. Ahora tiene dos fuentes con Sharpe de 0.6–0.9 y t-stats de 3.4–4.4 sobre 25 años, una tercera marginal, una falsada, y un instrumento de medición cuyo umbral de ruido cayó a un tercio. **Los números son mucho más bajos y valen infinitamente más**, porque por primera vez son mediciones y no artefactos de búsqueda.

---

## Anexo D — Matriz completa: las 7 estrategias del repositorio × los 22 activos

*4 de agosto de 2026. Re-ejecución del Gate I1 sobre 25 años, usando las definiciones de estrategia (`core/ml/i1_strategies.py`), el modelo de costes (`core/backtesting/costs.py`) y la función de retornos netos (`core/ml/i1_gate_validator.py`) **del propio repositorio**, para que los resultados sean directamente comparables con el reporte oficial del gate.*

### D.1 Diseño

- **22 activos** operables con histórico profundo (4 crypto, 6 forex, 6 índices, 6 commodities).
- **7 estrategias** del registro I1: `MA_10_30`, `BB_ZScore`, `Momentum`, `ema_rsi_v1`, `mean_rev_v1`, `tsmom_v1`, `vol_breakout_v1`. Se excluye `ml_lgb_v1` (requiere modelo entrenado por símbolo; solo existe para 4 símbolos y sobre barras de 1h).
- **39 combinaciones de parámetros** en total, las del propio registro.
- Barras diarias, señal desplazada 1 barra, costes por clase de activo del `CostModel` del repo.
- Split 80/20 walk-forward / holdout, idéntico al del gate.

Se ejecutan **tres vistas** cuya comparación es el resultado del anexo.

### D.2 Vista A — Metodología del gate (seleccionar la mejor configuración por activo)

| Activo | Clase | Años | Mejor estrategia | SR WF | SR holdout | t holdout | Umbral | ¿Pasa? |
|---|---|---:|---|---:|---:|---:|---:|:---:|
| BTCUSDT | CRYPTO | 9.0 | MA_10_30 | 0.72 | 0.44 | 0.72 | 1.63 | no |
| ETHUSDT | CRYPTO | 9.0 | MA_10_30 | 0.79 | 1.14 | 1.84 | 1.63 | no |
| SOLUSDT | CRYPTO | 6.0 | MA_10_30 | 1.13 | 0.37 | 0.49 | 1.99 | no |
| BNBUSDT | CRYPTO | 8.7 | MA_10_30 | 0.93 | 0.05 | 0.09 | 1.65 | no |
| EURUSD | FOREX | 22.7 | BB_ZScore | 0.50 | −0.06 | −0.14 | 1.02 | no |
| GBPUSD | FOREX | 22.7 | vol_breakout_v1 | 0.15 | 0.03 | 0.06 | 1.02 | no |
| USDJPY | FOREX | 25.0 | mean_rev_v1 | 0.58 | −0.08 | −0.18 | 0.98 | no |
| USDCHF | FOREX | 22.9 | BB_ZScore | 0.29 | 0.01 | 0.02 | 1.02 | no |
| AUDUSD | FOREX | 20.2 | ema_rsi_v1 | 0.40 | 0.36 | 0.74 | 1.08 | no |
| USDCAD | FOREX | 22.9 | BB_ZScore | 0.24 | 0.70 | 1.53 | 1.02 | no |
| US500 | INDICES | 25.0 | BB_ZScore | 0.73 | −0.12 | −0.26 | 0.97 | no |
| US30 | INDICES | 25.0 | BB_ZScore | 0.53 | −0.03 | −0.07 | 0.97 | no |
| NAS100 | INDICES | 25.0 | BB_ZScore | 0.65 | 0.23 | 0.52 | 0.97 | no |
| DE40 | INDICES | 25.0 | ema_rsi_v1 | 0.19 | −0.16 | −0.36 | 0.98 | no |
| UK100 | INDICES | 25.0 | BB_ZScore | 0.30 | 0.05 | 0.10 | 0.97 | no |
| JP225 | INDICES | 25.0 | BB_ZScore | 0.16 | 0.52 | 1.14 | 0.97 | no |
| XAUUSD | COMMOD | 25.0 | MA_10_30 | 0.21 | −0.01 | −0.02 | 0.98 | no |
| XAGUSD | COMMOD | 25.0 | Momentum | 0.29 | 0.02 | 0.04 | 0.98 | no |
| USOIL | COMMOD | 25.0 | mean_rev_v1 | 0.38 | 0.04 | 0.10 | 0.98 | no |
| UKOIL | COMMOD | 19.0 | MA_10_30 | 0.61 | −0.19 | −0.37 | 1.12 | no |
| NATGAS | COMMOD | 25.0 | BB_ZScore | 0.37 | 0.35 | 0.78 | 0.98 | no |
| WHEAT | COMMOD | 25.0 | BB_ZScore | 0.14 | −0.48 | −1.07 | 0.97 | no |

**Resultado: 0 de 22 activos pasan.** Ninguno alcanza siquiera un t-stat de 2.0 en holdout (el máximo es ETHUSDT con 1.84).

**El dato que cierra el argumento de la Sección 0.** Esta es exactamente la misma metodología que produjo Sharpe WF de **1.70 a 3.32** sobre 2 años de datos. Sobre 25 años produce Sharpe WF de **0.14 a 1.13, media 0.47**. El span se multiplicó por 10 y los Sharpe se dividieron por 5. Un edge real no se comporta así: la magnitud de un Sharpe verdadero no depende del tamaño de la muestra, solo su precisión. **Lo que se dividió por 5 fue la amplitud del ruido, porque era ruido.**

Y la caída WF → holdout se mantiene, ahora medible con precisión: **0.47 → 0.14, una pérdida de 0.32 de Sharpe**. Eso es el sesgo de selección de buscar entre 39 configuraciones, cuantificado directamente.

### D.3 Vista B — Sin selección: parámetros por defecto, un solo ensayo por estrategia

Cada estrategia se aplica con sus parámetros por defecto, idénticos para los 22 activos, sobre toda la historia. Cartera *pooled* equirriesgo (1/vol) entre activos:

| Estrategia | SR medio por activo | SR mediana | % activos > 0 | **SR pooled** | **t pooled** | Umbral | Veredicto |
|---|---:|---:|---:|---:|---:|---:|---|
| MA_10_30 | +0.10 | +0.01 | 64% | **+0.11** | 0.60 | 0.26 | no supera |
| ema_rsi_v1 | +0.05 | +0.10 | 55% | +0.07 | 0.38 | 0.26 | no supera |
| mean_rev_v1 | 0.00 | −0.11 | 45% | −0.04 | −0.23 | 0.26 | no supera |
| tsmom_v1 | −0.02 | −0.06 | 41% | −0.13 | −0.70 | 0.26 | no supera |
| Momentum | −0.03 | −0.03 | 45% | −0.15 | −0.79 | 0.26 | no supera |
| BB_ZScore | −0.04 | −0.14 | 41% | −0.17 | −0.91 | 0.26 | no supera |
| **vol_breakout_v1** | **−0.17** | −0.14 | 32% | **−0.39** | **−2.09** | 0.26 | **destruye valor** |

**Ninguna de las 7 estrategias del repositorio tiene edge.** La mejor (MA_10_30) da un Sharpe pooled de 0.11 con t=0.60. Y `vol_breakout_v1` es **significativamente negativa** (t = −2.09): no es que no funcione, es que pierde dinero de forma sistemática en 68% de los activos.

Combinarlas no ayuda: las dos con SR > 0 dan 0.11 juntas (están correlacionadas a 0.74), y las siete combinadas dan **−0.19**.

### D.4 Vista C — La matriz completa, y el patrón que sí aparece

Sharpe neto con parámetros por defecto, 25 años:

| | MA_10_30 | BB_ZScore | Momentum | ema_rsi | mean_rev | tsmom | vol_break |
|---|---:|---:|---:|---:|---:|---:|---:|
| **BTCUSDT** | **0.48** | −0.45 | 0.21 | −0.06 | −0.47 | 0.15 | 0.02 |
| **ETHUSDT** | **0.68** | −0.37 | 0.29 | 0.44 | −0.24 | 0.33 | −0.05 |
| **SOLUSDT** | **0.84** | −0.27 | 0.18 | 0.27 | −0.29 | 0.18 | 0.09 |
| **BNBUSDT** | **0.68** | −0.68 | 0.66 | 0.33 | −0.70 | 0.64 | 0.14 |
| EURUSD | 0.03 | 0.29 | −0.28 | 0.22 | 0.25 | −0.33 | −0.36 |
| GBPUSD | −0.09 | −0.26 | −0.41 | −0.11 | −0.18 | −0.25 | 0.10 |
| USDJPY | −0.09 | **0.51** | −0.20 | 0.14 | **0.47** | −0.07 | −0.38 |
| USDCHF | −0.23 | 0.24 | −0.46 | −0.13 | 0.21 | −0.39 | −0.19 |
| AUDUSD | 0.12 | −0.20 | −0.05 | 0.34 | −0.13 | 0.11 | −0.33 |
| USDCAD | 0.01 | −0.15 | −0.33 | −0.41 | 0.06 | −0.14 | 0.12 |
| US500 | 0.05 | **0.50** | 0.11 | 0.34 | **0.61** | 0.09 | −0.46 |
| US30 | −0.16 | 0.19 | 0.06 | 0.30 | 0.22 | −0.06 | −0.47 |
| NAS100 | 0.03 | 0.33 | 0.00 | 0.28 | 0.39 | −0.02 | −0.52 |
| DE40 | 0.00 | −0.25 | −0.22 | −0.05 | −0.17 | −0.25 | −0.34 |
| UK100 | −0.39 | 0.17 | −0.26 | −0.15 | 0.21 | −0.18 | −0.34 |
| JP225 | −0.02 | −0.28 | −0.23 | −0.17 | −0.21 | −0.29 | −0.09 |
| XAUUSD | 0.05 | −0.21 | 0.05 | 0.13 | −0.23 | 0.10 | 0.12 |
| XAGUSD | 0.01 | −0.13 | 0.22 | −0.26 | −0.14 | 0.10 | 0.00 |
| USOIL | −0.01 | 0.12 | 0.02 | 0.11 | 0.25 | −0.05 | −0.04 |
| UKOIL | **0.46** | −0.22 | 0.19 | −0.07 | −0.17 | 0.15 | 0.15 |
| NATGAS | 0.01 | 0.35 | −0.14 | 0.09 | 0.38 | −0.18 | −0.49 |
| WHEAT | −0.21 | −0.09 | −0.17 | −0.42 | −0.09 | −0.14 | −0.36 |

**Promedios por clase de activo — aquí está la señal:**

| Clase | MA_10_30 | BB_ZScore | Momentum | ema_rsi | mean_rev | tsmom | vol_break |
|---|---:|---:|---:|---:|---:|---:|---:|
| **CRYPTO** | **+0.67** | **−0.44** | **+0.34** | +0.25 | **−0.42** | **+0.32** | +0.05 |
| FOREX | −0.04 | +0.07 | −0.29 | +0.01 | +0.11 | −0.18 | −0.17 |
| INDICES | −0.08 | +0.11 | −0.09 | +0.09 | **+0.17** | −0.12 | **−0.37** |
| COMMOD | +0.05 | −0.03 | +0.03 | −0.07 | 0.00 | 0.00 | −0.10 |

El patrón es nítido y **se invierte exactamente** entre clases:

- **CRYPTO: seguimiento de tendencia funciona, reversión falla.** MA_10_30 +0.67, Momentum +0.34, tsmom +0.32 · BB_ZScore −0.44, mean_rev −0.42.
- **FOREX e ÍNDICES: lo contrario.** mean_rev +0.11/+0.17, BB_ZScore +0.07/+0.11 · Momentum −0.29/−0.09, tsmom −0.18/−0.12.
- **COMMODITIES: nada funciona** (todo entre −0.10 y +0.05).

Además, la matriz de correlaciones entre carteras revela que **no hay 7 estrategias, hay 2**: `MA_10_30`/`Momentum`/`tsmom_v1` correlacionan entre 0.64 y 0.96, `BB_ZScore`/`mean_rev_v1` a 0.86, y los dos grupos están anticorrelacionados (−0.27 a −0.44). El registro I1 tiene siete entradas y dos ideas.

### D.5 Confirmación independiente: exponente de Hurst (responde a la investigación I5)

El patrón anterior sale de *backtests*. Si es real, debe aparecer también en las **propiedades estadísticas del precio**, medidas sin ninguna estrategia:

| Clase | Hurst medio | Autocorrelación(1) | Variance Ratio(5) | Predicción | ¿Coincide con la matriz? |
|---|---:|---:|---:|---|:---:|
| **CRYPTO** | **0.565** | −0.035 | 0.996 | Persistente → tendencia | ✅ trend +0.67 / reversión −0.44 |
| FOREX | 0.479 | −0.072 | 0.877 | Antipersistente → reversión | ✅ reversión +0.11 / trend −0.29 |
| **INDICES** | **0.461** | −0.067 | 0.873 | Antipersistente → reversión | ✅ reversión +0.17 / trend −0.12 |
| COMMOD | 0.482 | −0.029 | 0.948 | Casi aleatorio | ✅ todo ≈ 0 |

Por activo: los 4 cryptos tienen H entre 0.542 y 0.594 (todos > 0.53, tendenciales); US500 0.461, US30 0.447, UK100 0.434, XAUUSD 0.451, NATGAS 0.453 (todos < 0.47, reversivos).

**Dos mediciones metodológicamente independientes — estadística del precio y rendimiento de estrategia — coinciden en las cuatro clases de activo.** Esto es evidencia de una propiedad estructural real, no de un ajuste: el Hurst no vio ningún backtest y el backtest no vio ningún Hurst.

**Esto responde la investigación I5 del `PLAN_MAESTRO.md`** ("¿Qué activos son trending vs mean-reverting?"), abierta como ❓ no documentado:

> **CRYPTO → tendencial (H≈0.57). FOREX e ÍNDICES → reversivos (H≈0.46–0.48). COMMODITIES → sin estructura explotable (H≈0.48, VR≈0.95).**

### D.6 El contraste que lo decide: estrategia vs. simplemente mantener el activo

Sharpe de buy & hold sobre la misma historia:

| Activo | Clase | Buy & hold | t | Mejor estrategia | SR | Diferencia | ¿Gana? |
|---|---|---:|---:|---|---:|---:|:---:|
| **XAUUSD** | COMMOD | **0.70** | **3.51** | ema_rsi_v1 | 0.13 | **−0.58** | no |
| **BNBUSDT** | CRYPTO | **0.97** | **3.45** | MA_10_30 | 0.68 | −0.29 | no |
| NAS100 | INDICES | 0.60 | 3.00 | mean_rev_v1 | 0.39 | −0.21 | no |
| SOLUSDT | CRYPTO | 0.85 | 2.50 | MA_10_30 | 0.84 | −0.00 | no |
| XAGUSD | COMMOD | 0.49 | 2.45 | Momentum | 0.22 | −0.27 | no |
| US500 | INDICES | 0.49 | 2.43 | mean_rev_v1 | 0.61 | **+0.12** | **SÍ** |
| BTCUSDT | CRYPTO | 0.66 | 2.36 | MA_10_30 | 0.48 | −0.17 | no |
| US30 | INDICES | 0.46 | 2.27 | ema_rsi_v1 | 0.30 | −0.16 | no |
| JP225 | INDICES | 0.41 | 2.04 | MA_10_30 | −0.02 | −0.43 | no |
| ETHUSDT | CRYPTO | 0.56 | 2.02 | MA_10_30 | 0.68 | **+0.12** | **SÍ** |
| DE40 | INDICES | 0.38 | 1.91 | MA_10_30 | 0.00 | −0.38 | no |
| USOIL | COMMOD | 0.31 | 1.55 | mean_rev_v1 | 0.25 | −0.06 | no |
| NATGAS | COMMOD | 0.30 | 1.47 | mean_rev_v1 | 0.38 | **+0.08** | **SÍ** |
| WHEAT | COMMOD | 0.27 | 1.35 | mean_rev_v1 | −0.09 | −0.36 | no |
| UK100 | INDICES | 0.24 | 1.21 | mean_rev_v1 | 0.21 | −0.03 | no |
| UKOIL | COMMOD | 0.20 | 0.86 | MA_10_30 | 0.46 | **+0.26** | **SÍ** |
| USDJPY | FOREX | 0.14 | 0.71 | BB_ZScore | 0.51 | **+0.38** | **SÍ** |
| USDCAD | FOREX | 0.06 | 0.28 | vol_breakout_v1 | 0.12 | **+0.07** | **SÍ** |
| EURUSD | FOREX | 0.04 | 0.20 | BB_ZScore | 0.29 | **+0.25** | **SÍ** |
| AUDUSD | FOREX | 0.03 | 0.13 | ema_rsi_v1 | 0.34 | **+0.31** | **SÍ** |
| GBPUSD | FOREX | −0.07 | −0.32 | vol_breakout_v1 | 0.10 | **+0.16** | **SÍ** |
| USDCHF | FOREX | −0.17 | −0.81 | BB_ZScore | 0.24 | **+0.41** | **SÍ** |

**Las estrategias baten al buy & hold en 10 de 22 activos — y la separación no es aleatoria.** Ordenada la tabla por Sharpe del buy & hold, los "SÍ" se concentran íntegramente en la mitad inferior: ganan en **6 de 6 pares de forex**, y pierden en **5 de 6 índices**, **4 de 6 commodities** y **3 de 4 cryptos**.

La explicación es económica, no estadística: **el forex no tiene deriva estructural** (una divisa no genera flujo de caja; su retorno esperado a largo plazo es ~0, y en efecto el buy & hold de EURUSD da 0.04 y el de GBPUSD −0.07). Ahí, cualquier señal débil añade valor sobre no hacer nada. **Los índices, el oro y la plata sí tienen deriva estructural** (prima de riesgo de renta variable, demanda monetaria del oro), y una estrategia que entra y sale destruye esa deriva más de lo que aporta su señal.

El caso extremo es XAUUSD: buy & hold da Sharpe 0.70 con **t = 3.51** —uno de los resultados más significativos de todo el estudio— y la mejor de las 7 estrategias sobre oro da 0.13. **El activo que el Gate I1 marcaba como el único PASS del sistema rinde 5 veces mejor si simplemente se compra y se mantiene.**

### D.7 Conclusiones

1. **Las 7 estrategias builtin del repositorio no tienen edge.** Con selección de parámetros: 0/22 activos pasan. Sin selección: la mejor da Sharpe pooled 0.11 (t=0.60) y una (`vol_breakout_v1`) destruye valor de forma significativa (t=−2.09). Esto no contradice al Gate I1 corregido: lo completa. El gate decía 1/8 sobre 2 años; sobre 25 años la respuesta correcta es **0/22**.

2. **El sesgo de selección quedó medido: 0.32 de Sharpe.** Es la diferencia entre elegir la mejor de 39 configuraciones (0.47 medio) y lo que esa elección rinde fuera de muestra (0.14).

3. **Hay una estructura real, y no es una estrategia: es un mapa activo → régimen.** Crypto es tendencial, forex e índices son reversivos, commodities no tienen estructura. Confirmado por dos vías independientes. Es el activo intelectual más valioso producido por este análisis, y responde a I5.

4. **La estructura no basta para generar alpha por sí sola.** Aplicar la estrategia "correcta" según el régimen del activo mejora los números pero no los lleva por encima del umbral deflactado — porque los mismos activos tendenciales (crypto) rinden aún mejor comprados y mantenidos.

5. **El resultado más robusto sigue siendo el más simple.** De todo lo medido en los Anexos C y D, lo que supera el umbral con holgura es: la cartera equiponderada de 22 activos (SR 0.89, t=4.42), la paridad de riesgo (0.76, t=3.80), el efecto overnight (0.57–1.02, t hasta 5.03) y mantener oro (0.70, t=3.51). **Todo ello tiene cero parámetros optimizables.** Las siete estrategias con 39 configuraciones ajustables no producen nada.

6. **Implicación para el roadmap.** El Sprint 5 no debe implementar más estrategias de señal antes de resolver dos preguntas que este anexo deja planteadas: (a) ¿puede el mapa activo→régimen de D.5 mejorar una cartera diversificada, en vez de sustituirla? (b) ¿existe alguna configuración de costes y ejecución en la que el efecto overnight sobreviva con margen? Ambas son preguntas de investigación acotadas y baratas, y ambas se responden con los datos ya descargados.

> **La lectura honesta de este anexo.** Es, en apariencia, el peor resultado posible: siete estrategias, veintidós activos, veinticinco años, cero aprobados. Pero el proyecto no está peor que ayer — está mejor informado. Ayer tenía ocho estrategias con Sharpe reportado de 1.7–3.3 y la tentación de construir sobre ellas; hoy sabe que ese suelo no existía, y tiene en cambio cuatro resultados modestos que sí resisten deflación, y un mapa activo→régimen verificado por dos métodos. **Descubrir que el edge no está donde se creía es progreso, siempre que se descubra antes de comprometer capital.** Es exactamente lo que la Sección 0 se propuso conseguir, y ya está conseguido.

---

## Anexo E — Estrategia compuesta por confluencia de indicadores

*5 de agosto de 2026. Contraste de la tesis central del producto: que combinar varios indicadores en una sola estrategia —con entradas, salidas, TP/SL, sizing y divergencias integrados— produce mejores oportunidades que cualquier indicador aislado.*

### E.0 Por qué este anexo existe

Los Anexos B, C y D midieron estrategias **aisladas**: una o dos señales cada una, evaluadas por separado. Esa no es la tesis del producto. TRADER AI se propone **fusionar** indicadores: identificar oportunidades por confluencia, confirmarlas entre sí, y gestionar la operación completa (entrada, salida, take profit, tamaño de posición, divergencias).

Es una hipótesis distinta y no estaba contrastada. Este anexo la contrasta, y **el resultado la respalda** — es el primer resultado de todo el estudio en el que una *estrategia activa* supera el umbral de ruido deflactado, no solo una asignación pasiva.

### E.1 Arquitectura del motor

Cuatro capas sobre los 52 indicadores que ya calcula `core/features/indicators.py`:

```
CAPA 1 — VOTOS (13 indicadores, cada uno emite -1 / 0 / +1)
  Familia tendencia (5):   EMA9vs21 · EMA50vs200 · MACD histograma
                           · ADX>25 con dirección · precio vs EMA50
  Familia reversión (4):   %B de Bollinger <0.05/>0.95 · RSI14 <30/>70
                           · z-score vs MA20 ±2 · RSI7 <25/>75
  Confirmación volumen (2): pendiente OBV(10) · volumen >1.2× media con dirección
  Divergencias (2):        precio vs RSI14 · precio vs línea MACD
                           (mínimo más bajo en precio + mínimo más alto en
                            indicador = divergencia alcista, y simétrico)

CAPA 2 — RÉGIMEN (pondera qué familia manda)
  w_tendencia = clip((Hurst − 0.45) / 0.10, 0, 1);  w_reversión = 1 − w_tendencia
  Aplica el mapa activo→régimen validado en el Anexo D.5

CAPA 3 — DECISIÓN
  score = Σ votos ponderados por familia, acotado a [−1, +1]
  n_confirmaciones = nº de votos no nulos que coinciden con el signo del score
  ENTRADA si n_confirmaciones ≥ min_conf

CAPA 4 — GESTIÓN DE LA OPERACIÓN
  Stop loss    = entrada ∓ atr_sl × ATR14
  Take profit  = entrada ± atr_sl × R:R × ATR14
  Salida extra = inversión del signo de la señal
  Tamaño       = objetivo de volatilidad 10% anual / vol realizada 60d, tope 3×
```

Backtest sobre 22 activos, 25 años, barras diarias, señal desplazada 1 barra, costes por clase de activo del `CostModel` del repositorio.

### E.2 Experimento central — ¿más confirmaciones producen mejor resultado?

Esta es la pregunta que decide si la confluencia aporta algo o solo reduce el número de operaciones. Cartera *pooled* equirriesgo de los 22 activos, sin régimen ni stops, para aislar el efecto de las confirmaciones:

| Confirmaciones exigidas | SR pooled | t | Operaciones/activo | % activos con SR > 0 |
|---:|---:|---:|---:|---:|
| 1 | **−0.35** | −1.91 | 1.078 | 32% |
| 2 | −0.35 | −1.91 | 1.078 | 32% |
| 3 | −0.27 | −1.47 | 969 | 27% |
| 4 | −0.04 | −0.20 | 730 | 50% |
| 5 | +0.17 | 0.92 | 624 | 55% |
| **6** | **+0.43** | **2.32** | 460 | **82%** |
| 7 | +0.07 | 0.38 | 215 | 86% |
| 8 | n/d | — | 34 | 59% |

**El Sharpe sube de forma monótona de 1 a 6 confirmaciones: de −0.35 a +0.43, un recorrido de 0.78.** Y el porcentaje de activos con resultado positivo pasa de 32% a 82%. A partir de 7 confirmaciones el sistema opera tan poco (215 y 34 operaciones) que el estimador pierde sentido.

**Esto es evidencia directa a favor de la tesis del producto**, y contrasta con todo lo medido en el Anexo D: allí ninguna estrategia individual llegaba a un Sharpe pooled de 0.11. La diferencia no es el indicador, es la exigencia de acuerdo entre indicadores.

Dos matices que el resultado obliga a señalar:

- **Una sola confirmación es activamente destructiva** (−0.35 con t=−1.91, casi significativo en negativo). Operar cada señal de cada indicador pierde dinero de forma sistemática. Esto explica retroactivamente por qué las 7 estrategias del Anexo D fallaban: cada una es, esencialmente, un sistema de 1–2 confirmaciones.
- **La curva tiene un máximo interior**, no es monótona hasta el final. Eso es lo que se espera de un efecto real (confirmación vs. escasez de muestra) y no de un artefacto de búsqueda, que tendería a premiar el extremo.

### E.3 Aportación de cada capa

| Configuración | SR pooled | t | vs. base |
|---|---:|---:|---:|
| 1. Confluencia sola, min_conf=3 (base) | −0.27 | −1.47 | — |
| 2. + condicionado por régimen (Hurst) | +0.11 | 0.61 | +0.38 |
| 3. + stops ATR 2.0 y TP con R:R 2.0 | +0.11 | 0.61 | +0.38 |
| 4. min_conf=6, sin régimen ni stops | +0.43 | 2.32 | +0.70 |
| 5. min_conf=6 + régimen | +0.26 | 1.41 | +0.53 |
| 6. min_conf=6 + régimen + stops ATR2/RR2 | +0.46 | 2.51 | +0.73 |
| 7. min_conf=6 + régimen + stops ATR2/**RR3** | +0.50 | 2.69 | +0.77 |
| **8. min_conf=6 + régimen + stops ATR1.5/RR2** | **+0.55** | **2.98** | **+0.82** |

**La capa que más aporta, con diferencia, es la exigencia de confirmaciones (+0.70).** El régimen y los stops añaden otro +0.12 combinados.

**Un hallazgo incómodo que hay que declarar:** las capas **no son aditivas**. El condicionamiento por régimen ayuda con min_conf=3 (−0.27 → +0.11) pero **perjudica** con min_conf=6 (+0.43 → +0.26). Solo vuelve a ser útil cuando se añaden los stops. Esa inconsistencia es una señal de advertencia: sugiere que la capa de régimen no está capturando un efecto estable, sino interactuando con las otras de forma dependiente de la muestra. **La lectura prudente es que el sistema tiene una capa sólida (confirmaciones) y dos capas de aportación dudosa (régimen, stops).**

### E.4 Resultado por activo — sistema completo

Configuración min_conf=6 + régimen + stops ATR2/RR2:

| Activo | Clase | SR | t | Operaciones | vs. buy&hold | vs. mejor aislada (Anexo D) |
|---|---|---:|---:|---:|---:|---:|
| **BNBUSDT** | CRYPTO | **1.00** | **3.56** | 137 | +0.03 | +0.32 |
| **BTCUSDT** | CRYPTO | **0.92** | **3.31** | 140 | **+0.26** | **+0.44** |
| **SOLUSDT** | CRYPTO | **0.89** | 2.61 | 83 | +0.04 | +0.05 |
| **ETHUSDT** | CRYPTO | **0.86** | **3.11** | 138 | **+0.30** | +0.18 |
| **XAUUSD** | COMMOD | **0.73** | **3.66** | 308 | +0.03 | **+0.60** |
| **US500** | INDICES | **0.60** | **3.02** | 266 | +0.12 | −0.01 |
| **NAS100** | INDICES | **0.51** | 2.56 | 250 | −0.09 | +0.12 |
| EURUSD | FOREX | 0.48 | 2.33 | 117 | +0.44 | +0.19 |
| JP225 | INDICES | 0.43 | 2.12 | 284 | +0.02 | +0.45 |
| DE40 | INDICES | 0.39 | 1.95 | 296 | +0.01 | +0.39 |
| USOIL | COMMOD | 0.37 | 1.82 | 250 | +0.05 | +0.12 |
| XAGUSD | COMMOD | 0.34 | 1.67 | 359 | −0.16 | +0.12 |
| UKOIL | COMMOD | 0.33 | 1.41 | 196 | +0.13 | −0.13 |
| USDJPY | FOREX | 0.31 | 1.58 | 165 | +0.17 | −0.20 |
| USDCAD | FOREX | 0.27 | 1.32 | 137 | +0.21 | +0.15 |
| US30 | INDICES | 0.22 | 1.09 | 285 | −0.24 | −0.08 |
| AUDUSD | FOREX | 0.22 | 1.02 | 99 | +0.19 | −0.12 |
| GBPUSD | FOREX | 0.11 | 0.52 | 116 | +0.17 | +0.01 |
| NATGAS | COMMOD | 0.03 | 0.13 | 272 | −0.27 | −0.35 |
| USDCHF | FOREX | −0.01 | −0.07 | 110 | +0.15 | −0.25 |
| WHEAT | COMMOD | −0.03 | −0.15 | 272 | −0.30 | +0.06 |
| UK100 | INDICES | −0.11 | −0.56 | 287 | −0.35 | −0.32 |

**Resumen:**

| Métrica | Sistema compuesto | Mejor estrategia aislada (Anexo D) |
|---|---:|---:|
| SR medio de los 22 activos | **0.40** | 0.32 |
| Activos que baten al buy & hold | **16/22** | 10/22 |
| Activos con t > 2.0 | **9/22** | 0/22 |

Por clase de activo:

| Clase | Sistema compuesto | Buy & hold | Mejor aislada |
|---|---:|---:|---:|
| **CRYPTO** | **0.92** | 0.76 | 0.67 |
| INDICES | 0.34 | 0.43 | 0.25 |
| COMMOD | 0.29 | 0.38 | 0.22 |
| FOREX | 0.23 | 0.01 | 0.27 |

**Dónde el sistema compuesto gana de verdad: cripto** (0.92 medio, los cuatro activos con t entre 2.6 y 3.6, y batiendo al buy & hold en los cuatro). **Y resuelve el caso XAUUSD**: donde las estrategias aisladas daban 0.13 frente a un buy & hold de 0.70, el sistema compuesto da **0.73 con t=3.66** — por primera vez una estrategia activa sobre oro no destruye la deriva del activo.

**Donde sigue sin ganar: índices y commodities**, que continúan por debajo de su propio buy & hold (0.34 vs 0.43 y 0.29 vs 0.38). El diagnóstico del Anexo D se mantiene: en activos con deriva estructural, entrar y salir cuesta más de lo que aporta la señal.

### E.5 Las divergencias, por separado, no funcionan

| Señal | SR pooled | t |
|---|---:|---:|
| Divergencia precio/RSI | −0.23 | −1.25 |
| Divergencia precio/MACD | −0.04 | −0.23 |
| Ambas combinadas | −0.14 | −0.77 |

**Como señal autónoma, la detección de divergencias pierde dinero.** Solo aporta valor como 2 votos de 13 dentro del sistema de confluencia. Es un resultado útil de cara al producto: las divergencias deben presentarse al usuario como *contexto y confirmación*, nunca como disparador de operación por sí solas.

### E.6 Veredicto y honestidad estadística

| Configuración | SR | t | Umbral de ruido (N=30, 29.4 a) | Veredicto |
|---|---:|---:|---:|---|
| Confluencia min_conf=6 (simple) | 0.43 | 2.32 | 0.38 | ✅ supera |
| Sistema completo (mejor config) | **0.55** | **2.98** | 0.38 | ✅ **supera** |
| Cripto, sistema completo | 0.92 | 2.6–3.6 | 0.38 | ✅ supera con holgura |
| Confluencia min_conf=1 | −0.35 | −1.91 | — | ❌ destruye valor |

*Declaración de multiplicidad:* se evaluaron ~30 configuraciones (8 umbrales de confirmación × 8 combinaciones de capas y parámetros de stop). El umbral de 0.38 ya lo tiene en cuenta.

**Las tres reservas que impiden declarar esto resuelto:**

1. **El óptimo min_conf=6 se eligió mirando toda la muestra.** → **Resuelta en §E.7, y el resultado es parcialmente negativo.**
2. **Las capas no son aditivas** (§E.3): el régimen ayuda o perjudica según el umbral. Eso es más propio de un ajuste a la muestra que de un mecanismo estable.
3. **El resultado se concentra en cripto**, la clase con menos historia (6–9 años frente a 25). Los cuatro activos cripto están además fuertemente correlacionados entre sí, así que no son cuatro confirmaciones independientes sino aproximadamente una y media.

### E.7 Validación out-of-sample — la prueba decisiva

Protocolo: elegir `min_conf` **únicamente** con el 70% inicial (hasta 2020-06-20) y evaluarlo en el 30% final (2020-06 → 2026-08, **8.9 años nunca vistos**).

| min_conf | SR train | t train | **SR HOLDOUT** | **t holdout** |
|---:|---:|---:|---:|---:|
| 3 | 0.02 | 0.09 | +0.39 | 1.15 |
| 4 | 0.33 | 1.49 | **+0.68** | **2.03** |
| 5 | 0.59 | 2.66 | +0.48 | 1.42 |
| **6** ← elegido por train | **0.62** | **2.82** | **+0.42** | 1.25 |
| 7 | 0.27 | 1.24 | **+1.06** | **3.16** |

**Veredicto sobre la configuración elegida honestamente: no pasa.** El `min_conf=6` que selecciona el entrenamiento rinde 0.42 en holdout —justo por encima del umbral de ruido (0.40)— pero con **t = 1.25**, que no permite rechazar la hipótesis nula.

Lo que este experimento enseña, en orden de importancia:

1. **La ubicación del óptimo NO es estable.** En entrenamiento el mejor es 6; en holdout el mejor es 7 (1.06) y el segundo es 4 (0.68), mientras que 6 queda cuarto. La correlación de rangos entre train y holdout es prácticamente nula. **Conclusión operativa: `min_conf` no se puede ajustar. Hay que fijarlo a priori y aceptar un rango.**

2. **Pero el efecto sí sobrevive en dirección.** Los **cinco** umbrales dan Sharpe positivo en holdout (+0.39 a +1.06, media ≈ +0.61). Un sistema sin edge produciría signos repartidos. Que las cinco variantes sean positivas sobre 8.9 años no vistos es la evidencia más sólida a favor de la confluencia de todo el anexo — más que el pico de +0.55 del §E.3, que era in-sample.

3. **Desglose del holdout por clase — aquí está la señal real:**

| Clase | SR holdout | t | Activos individuales |
|---|---:|---:|---|
| **CRYPTO** | **+1.10** | **3.28** | BTC +0.90 · ETH +0.90 · SOL +0.83 · BNB +0.72 |
| INDICES | +0.67 | 1.68 | US500 +0.77 · NAS100 +0.81 · DE40 +0.36 · JP225 +0.31 · US30 +0.06 · UK100 −0.26 |
| COMMOD | +0.64 | 1.59 | XAUUSD +0.76 · XAGUSD +0.54 · UKOIL +0.31 · USOIL +0.12 · WHEAT +0.04 · NATGAS −0.01 |
| FOREX | +0.11 | 0.28 | EURUSD +0.55 · USDJPY +0.46 · AUDUSD +0.36 · USDCAD +0.31 · GBPUSD +0.21 · USDCHF +0.12 |

**Cripto en holdout: SR 1.10 con t = 3.28, y los cuatro activos entre +0.72 y +0.90.** Ese es el único resultado de todo el estudio en el que una estrategia activa, con parámetros fijados fuera de muestra, supera con holgura el umbral de ruido en datos nunca vistos. Índices (0.67) y commodities (0.64) quedan por encima del umbral pero sin significancia (t≈1.6).

4. **Una anomalía metodológica propia que hay que declarar:** el pooled de FOREX da 0.11 cuando sus **seis** componentes son positivos (media 0.335). Eso es incoherente y apunta a un defecto de mi ponderación: los pesos son 1/volatilidad calculados sobre los retornos *de la estrategia*, que valen exactamente cero cuando el sistema está fuera de mercado. Un activo mucho tiempo plano tiene volatilidad artificialmente baja y recibe un peso desproporcionado. **El número de FOREX no debe leerse como resultado; la ponderación hay que corregirla (usar la volatilidad del activo, no la de la estrategia) antes de volver a medirlo.** Los pooled de las otras tres clases están menos afectados porque operan más, pero la corrección aplica a todos.

### E.8 El bucle de iteración

Con el motor construido y medido, esto es lo que hace falta para iterar sobre las configuraciones más efectivas sin repetir el error que la Sección 0 documenta:

```
1. REGISTRAR      Toda configuración evaluada entra en el TrialRegistry (§6.1),
                  incluidas las descartadas. El contador de ensayos es el que
                  fija el umbral de ruido: sin él, la iteración es autoengaño.

2. PROPONER       Cada iteración modifica UNA capa: añadir un voto, cambiar la
                  ponderación de régimen, ajustar el R:R. Cambiar varias a la vez
                  impide atribuir la mejora.

3. MEDIR          Contra el umbral E[max SR | H0, N] con el N acumulado, nunca
                  contra cero y nunca contra la iteración anterior.

4. ACEPTAR        Solo si: SR_holdout > umbral · t > 2.0 · mejora ≥ +0.10 sobre
                  la configuración vigente · y el voto nuevo no está correlacionado
                  > 0.7 con uno existente (un voto redundante sube el recuento de
                  confirmaciones sin añadir información — inflaría min_conf
                  artificialmente).

5. PODAR          Todo voto cuya eliminación no baje el Sharpe se elimina. Trece
                  votos son ya un espacio de búsqueda considerable; el objetivo
                  de cada iteración debe ser tanto quitar como añadir.

6. PARAR          Tras 3 iteraciones consecutivas sin aceptación, la línea está
                  agotada. El presupuesto de ensayos es finito y cada iteración
                  lo consume.
```

**Próximas tres iteraciones recomendadas**, en orden de valor esperado:

| # | Hipótesis | Por qué | Coste |
|---|---|---|---|
| **1** | Corregir la ponderación de cartera (vol del activo, no de la estrategia) | Defecto identificado en §E.7.4 — invalida los pooled actuales, sobre todo el de FOREX | 0 ensayos (es un bug) |
| **2** | Fijar `min_conf` a priori en 5–6 (≈45% de los votos) y no volver a tocarlo | §E.7 demuestra que ajustarlo no funciona: el óptimo no replica. Fijarlo elimina un grado de libertad y sube el umbral de confianza | 0 ensayos |
| **3** | Concentrar el sistema en cripto y validar en paper | Es la única clase con edge fuera de muestra (SR 1.10, t=3.28). El foco vale más que la cobertura | 1 ensayo |
| **4** | Votos ponderados por su IC histórico en vez de peso igual | Los 13 votos no valen lo mismo; ponderar por información esperada es la mejora más directa | 2 ensayos |
| **5** | Añadir los votos macro ya descargados (VIX term structure, DXY) | Son las dos features con IC medido más alto del catálogo (§Capa 4.2: t=−9.11) y no están en el motor | 2 ensayos |

Y **una línea que no debe iterarse**: añadir más indicadores técnicos de la misma familia. La matriz de correlaciones del Anexo D.4 ya mostró que siete estrategias técnicas eran en realidad dos ideas. Trece votos técnicos probablemente sean tres o cuatro. El margen de mejora está en añadir **información distinta** (macro, microestructura, posicionamiento), no más variantes de media móvil.

---

## Anexo F — Ejecución del bucle de iteración

*5 de agosto de 2026. Aplicación del protocolo del §E.8 al motor de confluencia, con registro de multiplicidad y validación final sobre universo intacto.*

### F.1 ITER 0 — La corrección del bug de ponderación cambia todas las cifras

El defecto declarado en §E.7.4 (pesos por volatilidad de la *estrategia*, que vale cero cuando el sistema está fuera de mercado) estaba deprimiendo todas las mediciones. Corregido a volatilidad **del activo**:

| min_conf | SR train | **SR holdout** | **t holdout** | Antes (con el bug) |
|---:|---:|---:|---:|---:|
| 4 | 0.49 | **1.00** | 2.98 | 0.68 |
| 5 | 0.75 | **1.08** | 3.22 | 0.48 |
| 6 | 0.94 | **1.37** | 4.07 | 0.42 |
| 7 | 0.61 | **1.47** | 4.37 | 1.06 |

**Los cuatro umbrales pasan ahora, con t entre 2.98 y 4.37.** Con el bug, el umbral seleccionado por entrenamiento fallaba (t=1.25). Y lo más relevante: train y holdout ya **coinciden en dirección**, lo que antes no ocurría.

El bug era objetivamente un bug —un activo mucho tiempo plano recibía peso desproporcionado— y su diagnóstico vino del absurdo aritmético del §E.7.4 (pooled 0.11 con seis componentes positivos de media 0.335), no de que diera mejores números. Aun así conviene declarar la secuencia: se detectó y corrigió **después** de ver resultados.

**ITER 1:** `min_conf` se fija en **5** a priori (regla: ~45% de los 13 votos), no se elige por resultado. §E.7 demostró que ajustarlo no funciona.

### F.2 ITER 2 — La poda, y lo que revela sobre el motor

Quitar cada familia de votos y medir. Si el sistema no empeora, la familia sobra:

| Configuración | SR holdout | t | Δ vs. base (1.08) | Decisión |
|---|---:|---:|---:|---|
| Sin familia **tendencia** | **−0.21** | −0.63 | **−1.29** | ❌ imprescindible |
| Sin familia **reversión** | 1.18 | 3.53 | **+0.10** | ✅ **podar** |
| Sin familia **volumen** | 1.29 | 3.84 | **+0.21** | ✅ **podar** |
| Sin familia divergencias | 1.11 | 3.29 | +0.02 | mantener (bajo el listón de +0.10) |

**Los recortes se componen:**

| Configuración | SR train | SR holdout | t |
|---|---:|---:|---:|
| Base: 13 votos | 0.75 | 1.08 | 3.22 |
| Sin volumen | 0.82 | 1.29 | 3.84 |
| **Sin volumen ni reversión (7 votos)** | **0.86** | **1.38** | **4.11** |
| Sin volumen, reversión ni divergencias (5 votos) | 0.90 | 1.28 | 3.82 |

**El motor óptimo tiene 7 votos, no 13: los 5 de tendencia más los 2 de divergencias.** Quitar también las divergencias baja a 1.28, así que en el sistema podado sí aportan (+0.10) aunque en el de 13 votos fueran neutras.

Es el mismo patrón que el Anexo D.4 encontró en las estrategias del repositorio: **añadir indicadores de familias redundantes no suma, resta.** La familia de volumen era ruido y la de reversión estaba peleando con la de tendencia.

### F.3 ITER 3 y 4 — Dos hipótesis rechazadas

| Iteración | Resultado | Δ | Decisión |
|---|---:|---:|---|
| **Votos macro** (VIX term structure + DXY), min_conf=5 | 1.08 | −0.00 | ❌ rechazada |
| Votos macro, min_conf=6 | 1.27 | −0.10 vs. 1.37 sin macro | ❌ rechazada |
| **Votos ponderados por IC histórico** | 1.07 | −0.01 | ❌ rechazada |

Sorprende que el VIX term structure no aporte, siendo la feature con mayor IC medido del catálogo (t=−9.11 en §Capa 4.2). La explicación probable: como *voto binario* dentro de trece, su información se diluye; su valor está en modular el **tamaño** de la posición, no en votar la dirección. Queda como hipótesis para una iteración futura.

El IC medido por voto (solo en entrenamiento) es informativo por sí mismo:

| Voto | IC (5 días) | | Voto | IC (5 días) |
|---|---:|---|---|---:|
| **div_rsi** | **+0.0330** | | obv | +0.0065 |
| **vix_ts** | **+0.0319** | | ema_slow | −0.0062 |
| **div_macd** | **+0.0278** | | dxy | +0.0050 |
| ema_fast | +0.0166 | | bb | +0.0039 |
| **vol_confirm** | **−0.0127** | | price_ma | +0.0034 |
| rsi7 | +0.0114 | | zscore | −0.0015 |

**Las divergencias tienen el IC más alto de los quince votos** — pese a que como estrategia autónoma pierden dinero (§E.5, SR −0.23). No es contradictorio: el IC mide correlación de rango con el retorno futuro; el Sharpe de una regla de trading incorpora además la lógica de mantenimiento y salida. Una señal puede ser informativa y aun así no ser operable por sí sola. **Ése es precisamente el argumento a favor de la confluencia.**

Y `vol_confirm` tiene IC **negativo**, lo que confirma por una vía independiente el resultado de la poda: la familia de volumen sobraba.

### F.4 ITER 5 — La diversificación gana al foco

| Universo | SR holdout | t | Δ vs. 22 activos |
|---|---:|---:|---:|
| **Los 22 activos** | **1.08** | 3.22 | — |
| Todo menos FOREX | 1.00 | 2.97 | −0.08 |
| Solo CRYPTO | 0.92 | 2.74 | −0.16 |
| CRYPTO + ÍNDICES | 0.84 | 2.50 | −0.24 |

**Esto corrige una recomendación que yo mismo había hecho.** Tras el §E.7 propuse concentrar el sistema en cripto, la única clase con edge fuera de muestra. Medido: **cualquier subconjunto rinde peor que el universo completo.** El forex, que aisladamente era la clase más floja, aporta diversificación al conjunto. La conclusión del §9.2 —cuatro fuentes mediocres poco correlacionadas superan a una buena— se verifica también dentro de una sola estrategia.

### F.5 La validación honesta: el holdout está quemado

Llegado este punto hay que aplicar al propio trabajo la disciplina del §6.6. **El holdout temporal se ha usado 20 veces** para decidir podas, umbrales y variantes. Según el protocolo que este documento propone, su valor probatorio decae como $1/\sqrt{k}$: ya no es una prueba, es un conjunto de validación más. El SR de 1.38 **no puede presentarse como una estimación insesgada**.

Queda una prueba genuinamente limpia: aplicar la configuración **congelada** a instrumentos que no participaron en ningún experimento de confluencia. SPY, QQQ y DIA se descargaron en el Sprint 1 y nunca entraron en el universo de 22. Una sola evaluación, sin ajustar nada después:

```
CONFIGURACIÓN CONGELADA
  votos     = 5 de tendencia + 2 de divergencias (volumen y reversión podados)
  min_conf  = 5
  régimen   = ponderación por Hurst
  stops     = ATR 1.5 · R:R 2.0
  sizing    = objetivo de volatilidad 10% anual
```

| Instrumento | Años | **SR** | **t** | Operaciones | Buy & hold | **Max DD** |
|---|---:|---:|---:|---:|---:|---:|
| SPY | 25.0 | 0.57 | 2.83 | 256 | 0.58 | **13.1%** |
| QQQ | 25.0 | 0.58 | 2.88 | 238 | 0.63 | **12.8%** |
| DIA | 25.0 | 0.33 | 1.67 | 257 | 0.57 | 21.4% |
| **Cartera** | **24.8** | **0.57** | **2.86** | — | ~0.59 | **12.7%** |

**Veredicto: SUPERA** el umbral de ruido (0.10 para una sola evaluación sobre 24.8 años), con t=2.86.

**Y la lección que justifica todo el aparato metodológico de este documento:**

$$SR_{\text{holdout quemado}} = 1.38 \qquad \longrightarrow \qquad SR_{\text{universo intacto}} = 0.57$$

**El número obtenido tras veinte decisiones sobre el mismo holdout estaba inflado unas 2.4 veces respecto a la medición limpia.** No por mala fe ni por un error de código: por el mecanismo que la Sección 0 describe, aplicado esta vez a mi propio trabajo. Si el sistema se hubiera presentado con el 1.38, la decepción habría llegado con capital comprometido.

Dos matices que impiden leer el 0.57 como el veredicto definitivo, uno en cada dirección:

- **A la baja para el 1.38:** SPY, QQQ y DIA son tres instrumentos de renta variable estadounidense fuertemente correlacionados entre sí — es una sola apuesta, no tres. El universo de 22 activos está diversificado en cuatro clases. Parte de la diferencia entre 1.38 y 0.57 es diversificación perdida, no sobreajuste.
- **A favor del sistema:** el Sharpe queda a la par del buy & hold (0.57 vs ~0.59), pero **el drawdown máximo es de 12.7% frente al ~56% del S&P en el mismo periodo**. El Calmar pasa de ~0.18 a ~0.45. **El valor del sistema no está en el retorno, está en el perfil de riesgo** — exactamente lo que la §7.6 identificaba como la propuesta de valor defendible.

### F.6 Estado del motor tras el bucle

| Elemento | Antes del bucle | Después |
|---|---|---|
| Votos | 13 | **7** (5 tendencia + 2 divergencias) |
| min_conf | ajustado (6) | **fijado a priori (5)** |
| Ponderación de cartera | vol de la estrategia (buggy) | **vol del activo** |
| Universo | 22 activos | **22 activos** (confirmado mejor que cualquier subconjunto) |
| Familias descartadas | — | volumen (IC −0.013), reversión |
| Hipótesis rechazadas | — | votos macro, ponderación por IC, foco en cripto |
| Ensayos acumulados | 30 | **50** |
| Mejor estimación honesta del Sharpe | — | **≈ 0.57**, con Max DD ~13% |

**Las tres iteraciones siguientes**, con el holdout ya agotado y por tanto ejecutables solo contra datos nuevos:

| # | Hipótesis | Cómo validarla sin holdout |
|---|---|---|
| 1 | VIX term structure como modulador de **tamaño** en vez de voto direccional | Paper trading — es la hipótesis con mejor fundamento no probado (IC t=−9.11) |
| 2 | Sustituir el ATR por Yang-Zhang en stops y sizing (§Capa 3.1) | Cambio mecánico sin grado de libertad nuevo; medible en paper |
| 3 | Reponer la familia de reversión **solo** en activos con Hurst < 0.47 | La poda la eliminó globalmente; el mapa del Anexo D.5 sugiere que en índices y forex sí debería aportar |

**Y la regla que se deriva de §F.5:** ninguna de las tres se valida ya sobre datos históricos. El siguiente conjunto de validación legítimo es el **paper trading hacia adelante**, que es el único holdout que no se puede quemar porque aún no existe.

---

*Documento generado el 4–5 de agosto de 2026. Los cálculos estadísticos de las Secciones 0, 6, 7 y de los Anexos B, C, D, E y F son reproducibles sobre los datos de `data/raw/` y `data/processed/` del repositorio.*

