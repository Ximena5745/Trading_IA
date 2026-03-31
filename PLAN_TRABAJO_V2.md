# TRADER IA — Plan de Trabajo Integral v3.0
> **Versión:** 3.0.0 | **Fecha:** Marzo 2026 | **Horizonte:** 16 semanas
> 
> Cubre: integración de propuestas por viabilidad · entorno de testing · rediseño UI corporativo

---

## Tabla de Contenidos

1. [Resumen del Plan](#1-resumen-del-plan)
2. [Mapa de Fases](#2-mapa-de-fases)
3. [FASE 0 — Entorno de Testing y CI/CD Robusto](#3-fase-0--entorno-de-testing-y-cicd-robusto)
4. [FASE 1 — Quick Wins: Propuestas de Alta Viabilidad](#4-fase-1--quick-wins-propuestas-de-alta-viabilidad)
5. [FASE 2 — Nuevos Agentes: StatisticalArbAgent](#5-fase-2--nuevos-agentes-statisticalarbagent)
6. [FASE 3 — Propuestas Condicionales](#6-fase-3--propuestas-condicionales)
7. [FASE 4 — Propuestas Futuras: RL + Meta-aprendizaje](#7-fase-4--propuestas-futuras-rl--meta-aprendizaje)
8. [FASE 5 — Rediseño UI Corporativo](#8-fase-5--redise%C3%B1o-ui-corporativo)
9. [Infraestructura de Entornos](#9-infraestructura-de-entornos)
10. [Métricas de Aceptación](#10-m%C3%A9tricas-de-aceptaci%C3%B3n)
11. [Checklist Maestro](#11-checklist-maestro)

---

## 1. Resumen del Plan

### Principios guía

- **No romper lo que funciona.** Cada fase tiene rollback explícito antes de fusionarse a `main`.
- **Paper trading primero.** Ninguna mejora se valida sin al menos 2 semanas de datos paper.
- **Baseline antes que deep learning.** LightGBM debe estar entrenado y validado antes de introducir LSTM/TFT.
- **Testing continuo.** Fase 0 es prerrequisito de todo lo demás — sin entorno de testing, no hay integración.

### Resumen de tiempos

| Fase | Contenido | Duración | Semanas |
|------|-----------|----------|---------|
| **FASE 0** | Entorno testing + staging | 1 semana | 1 |
| **FASE 1** | Quick wins (alta viabilidad) | 2 semanas | 2-3 |
| **FASE 2** | StatisticalArbAgent | 2 semanas | 4-5 |
| **FASE 3** | Propuestas condicionales | 3 semanas | 6-8 |
| **FASE 4** | RL + Meta-aprendizaje | 4 semanas | 9-12 |
| **FASE 5** | Rediseño UI corporativo | 2 semanas | 13-14 |
| **Buffer** | Ajustes + validación final | 2 semanas | 15-16 |

---

## 2. Mapa de Fases

```
SEMANA →    1     2     3     4     5     6     7     8     9    10    11    12    13    14    15    16
            │     │     │     │     │     │     │     │     │     │     │     │     │     │     │     │
FASE 0      ████  │     │     │     │     │     │     │     │     │     │     │     │     │     │     │
FASE 1            ████  ████  │     │     │     │     │     │     │     │     │     │     │     │     │
FASE 2                        ████  ████  │     │     │     │     │     │     │     │     │     │     │
FASE 3                                    ████  ████  ████  │     │     │     │     │     │     │     │
FASE 4                                                       ████  ████  ████  ████  │     │     │     │
FASE 5                                                                               ████  ████  │     │
BUFFER                                                                                           ████  ████
            │     │     │     │     │     │     │     │     │     │     │     │     │     │     │     │
Paper       │           ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░│
Trading     │           (mínimo 2 semanas por agente antes de validar)                               │
```

---

## 3. FASE 0 — Entorno de Testing y CI/CD Robusto

**Duración:** 5-7 días  
**Prerrequisito de:** todas las fases siguientes  
**Branch:** `feature/testing-infra`

### 3.1 Problema actual

El proyecto tiene 76 tests (39 unit + 37 integration) pero carece de:
- Entorno de staging separado de producción
- Tests de contrato para la API REST
- Fixtures de datos de mercado para tests deterministas
- Coverage mínimo enforceado en CI
- Entorno Docker para tests de integración completos

### 3.2 Estructura de entornos objetivo

```
┌─────────────────────────────────────────────────────────┐
│                    ENTORNOS TRADER IA                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  DEV (local)           STAGING               PROD        │
│  ┌────────────┐        ┌────────────┐        ┌────────┐  │
│  │ .env.dev   │        │ .env.stg   │        │ .env   │  │
│  │ DB: local  │  ────► │ DB: docker │  ────► │ DB:VPS │  │
│  │ Binance    │        │ Binance    │        │ Binance│  │
│  │ testnet    │        │ testnet    │        │ live   │  │
│  │ MT5: demo  │        │ MT5: demo  │        │ MT5:   │  │
│  │            │        │            │        │ live   │  │
│  └────────────┘        └────────────┘        └────────┘  │
│       │                     │                    │        │
│  Tests unitarios       Tests e2e           Paper/Live     │
│  Tests integration     Smoke tests         Monitoring     │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Tareas

#### 3.3.1 Separación de entornos

- [ ] Crear `docker-compose.staging.yml` con servicios aislados (puertos distintos a prod)
- [ ] Crear `.env.staging` con Binance testnet + MT5 demo
- [ ] Crear `.env.test` para tests deterministas (sin llamadas externas reales)
- [ ] Script `scripts/setup_staging.sh` que levanta el entorno completo limpio
- [ ] Crear base de datos `trader_ai_staging` separada de `trader_ai`

#### 3.3.2 Fixtures y mocks

```python
# tests/fixtures/market_data.py — estructura requerida
@pytest.fixture
def btc_ohlcv_fixture():
    """500 velas 1h BTCUSDT con régimen mixto (bull + sideways + crash)"""
    ...

@pytest.fixture
def binance_client_mock():
    """Mock del cliente Binance que retorna fixtures sin red"""
    ...

@pytest.fixture
def mt5_client_mock():
    """Mock del cliente MT5"""
    ...
```

- [ ] Crear `tests/fixtures/` con datos históricos OHLCV embebidos (no llamadas live)
- [ ] Mock de `BinanceClient` y `MT5Client` para tests unitarios
- [ ] Fixtures de señales precalculadas para tests del `RiskManager`
- [ ] Fixtures de portafolio para tests del `PortfolioManager`

#### 3.3.3 Tests nuevos requeridos

| Módulo | Tests actuales | Tests a agregar | Coverage objetivo |
|--------|---------------|-----------------|-------------------|
| `VotingEngine` | Básicos | Pesos dinámicos por régimen | 90% |
| `RiskManager` | 7 condiciones | Edge cases Kill Switch | 95% |
| `PortfolioManager` | Básicos | Correlación BTC-ETH | 85% |
| `FundamentalAgent` | Básicos | Bloqueo por evento + asset_class | 85% |
| API endpoints | Smoke | Contract tests (Pydantic schemas) | 80% |
| `FeatureEngine` | Unitarios | Regresión con fixtures deterministas | 90% |

- [ ] Agregar `pytest-cov` con umbral mínimo `--cov-fail-under=80`
- [ ] Agregar `pytest-asyncio` para tests de endpoints FastAPI
- [ ] Agregar `httpx` para tests de contrato de API sin servidor real
- [ ] Test de smoke end-to-end: ingesta → agentes → consenso → risk → paper execution

#### 3.3.4 CI/CD actualizado

```yaml
# .github/workflows/ci.yml — checks a agregar
jobs:
  test:
    steps:
      - unit-tests          # pytest tests/unit/ --cov=core
      - integration-tests   # pytest tests/integration/ con docker-compose.test.yml
      - api-contract-tests  # pytest tests/api/
      - coverage-check      # falla si < 80%
      - lint                # ruff + mypy
      - security-scan       # bandit
  
  staging-deploy:           # Solo en merge a main
    needs: test
    steps:
      - deploy-staging
      - smoke-test-staging  # Ciclo completo con datos reales testnet
      - notify-telegram
```

- [ ] Separar job de unit tests (rápido, sin docker) de integration tests (con docker)
- [ ] Agregar job de deploy automático a staging en cada merge a `main`
- [ ] Smoke test automático en staging: ejecutar 1 ciclo completo por símbolo
- [ ] Notificación Telegram al finalizar deploy (si está configurado)

#### 3.3.5 Herramientas de observabilidad en staging

- [ ] Panel Grafana dedicado a staging con métricas separadas de prod
- [ ] Log de comparación de señales staging vs prod (mismos datos, ¿misma decisión?)
- [ ] Alert Prometheus si la latencia del pipeline > 5s por símbolo

---

## 4. FASE 1 — Quick Wins: Propuestas de Alta Viabilidad

**Duración:** 2 semanas  
**Branch:** `feature/quick-wins`  
**Prerequisito:** FASE 0 completa

### 4.1 Pesos de Consenso Dinámicos

**Tiempo estimado:** 2-3 días  
**Archivo:** `core/consensus/voting_engine.py`

#### Lógica objetivo

```python
# Pesos actuales (estáticos)
WEIGHTS_CRYPTO = {"technical": 0.45, "regime": 0.35, "microstructure": 0.20}
WEIGHTS_FOREX  = {"technical": 0.55, "regime": 0.45, "microstructure": 0.00}

# Pesos dinámicos objetivo
def get_dynamic_weights(asset_class: str, regime: MarketRegime) -> dict:
    base = WEIGHTS_CRYPTO if asset_class == "crypto" else WEIGHTS_FOREX
    
    if regime == MarketRegime.SIDEWAYS_LOW_VOL:
        # Mercado lateral: reducir TechnicalAgent, aumentar régimen
        return {
            "technical":      max(base["technical"] - 0.15, 0.20),
            "regime":         min(base["regime"] + 0.10, 0.55),
            "microstructure": base["microstructure"] + 0.05,
        }
    
    if regime == MarketRegime.VOLATILE_CRASH:
        # Crash: el risk engine ya bloquea, pero reducir al máximo
        return {"technical": 0.20, "regime": 0.70, "microstructure": 0.10}
    
    if regime == MarketRegime.BULL_TRENDING:
        # Tendencia fuerte: dar más peso a técnico
        return {
            "technical":      min(base["technical"] + 0.10, 0.65),
            "regime":         base["regime"],
            "microstructure": base["microstructure"],
        }
    
    return base  # BEAR_TRENDING, SIDEWAYS_HIGH_VOL: pesos base
```

#### Tareas

- [ ] Implementar `get_dynamic_weights(asset_class, regime)` en `voting_engine.py`
- [ ] Exponer los pesos efectivos usados en cada señal (para XAI y dashboard)
- [ ] Agregar campo `dynamic_weights_used` en el schema de `SignalResult`
- [ ] Tests: verificar que en régimen SIDEWAYS el técnico baja al ≤30%
- [ ] Tests: verificar que los pesos siempre suman 1.0

### 4.2 Filtro Macro por Asset Class (E8 extendido)

**Tiempo estimado:** 1 día  
**Archivo:** `core/agents/fundamental_agent.py`

#### Lógica objetivo

```python
# Filtro diferenciado por asset_class
MACRO_BLOCK_RULES = {
    "forex":    ["NFP", "FOMC", "ECB_RATE", "BOE_RATE", "CPI", "GDP"],
    "indices":  ["NFP", "FOMC", "CPI", "GDP", "EARNINGS_SEASON"],
    "crypto":   [],              # Crypto no bloquea por macro (24/7, descentralizado)
    "commodities": ["CPI", "GDP", "FOMC"],  # Oro reacciona a macro
}

BLOCK_WINDOW_MINUTES = {
    "NFP": 45, "FOMC": 60, "ECB_RATE": 30,
    "BOE_RATE": 30, "CPI": 30, "GDP": 30,
    "EARNINGS_SEASON": 15,
}
```

#### Tareas

- [ ] Refactorizar `FundamentalAgent.should_block_signal()` para recibir `asset_class`
- [ ] Agregar `MACRO_BLOCK_RULES` por clase de activo
- [ ] Configurar ventanas individuales por tipo de evento (no todas ±30 min)
- [ ] Tests: crypto no debe bloquearse por NFP; EUR/USD sí
- [ ] Tests: ventana de bloqueo respeta los minutos configurados

### 4.3 Control de Correlación en PortfolioManager

**Tiempo estimado:** 1-2 días  
**Archivo:** `core/portfolio/portfolio_manager.py`

#### Lógica objetivo

```python
CORRELATION_RULES = {
    # Par: umbral de correlación máxima permitida simultáneamente
    ("BTCUSDT", "ETHUSDT"):   0.90,
    ("EURUSD",  "GBPUSD"):    0.85,
    ("XAUUSD",  "XAGUSD"):    0.80,
    ("US500",   "NAS100"):    0.92,
}
CORRELATION_WINDOW = 30  # últimas 30 velas para calcular correlación rolling

def can_open_position(self, symbol: str, direction: str) -> tuple[bool, str]:
    for (sym_a, sym_b), max_corr in CORRELATION_RULES.items():
        if symbol not in (sym_a, sym_b):
            continue
        other = sym_b if symbol == sym_a else sym_a
        if not self.has_open_position(other):
            continue
        corr = self.calculate_rolling_correlation(symbol, other, CORRELATION_WINDOW)
        if abs(corr) > max_corr:
            return False, f"Correlación {corr:.2f} > {max_corr} con {other}"
    return True, ""
```

#### Tareas

- [ ] Implementar `calculate_rolling_correlation()` usando datos de `FeatureEngine`
- [ ] Implementar `can_open_position()` con validación de correlación
- [ ] Integrar validación en el flujo de ejecución (antes de `place_order`)
- [ ] Exponer correlaciones actuales en endpoint `/api/portfolio/correlations`
- [ ] Tests: BTC + ETH con corr=0.95 → segunda posición bloqueada
- [ ] Tests: BTC + ETH con corr=0.70 → segunda posición permitida

### 4.4 Auditoría y documentación: LOGICA_CORE.md

**Tiempo estimado:** 2 días  
**Archivo:** `LOGICA_CORE.md` (nuevo, en raíz)

- [ ] Diagrama de flujo completo: ingesta → 4 agentes → consenso → risk → ejecución
- [ ] Tabla detallada de cada agente: input, modelo, output, peso, fallback
- [ ] Fórmula matemática exacta del `VotingEngine` (ahora con pesos dinámicos)
- [ ] 7 condiciones del `RiskManager` + Kill Switch documentadas con código
- [ ] Flujo XAI: cómo se genera la explicación SHAP en lenguaje natural
- [ ] Tabla comparativa `VENTAJA_COMPETITIVA.md`: vs bots retail actuales

### 4.5 Estrategia de Alpha por Asset Class

**Tiempo estimado:** 2 días  
**Archivos:** `core/strategies/`, `core/agents/technical_agent.py`

| Activo | Estrategia Alpha | Features a priorizar |
|--------|-----------------|---------------------|
| **Forex** | Reversión a la media + sesiones | RSI periodos largos (21), BB, correlaciones entre divisas |
| **Commodities (XAU)** | Refugio seguro + volatilidad | ATR dinámico, volumen futuros MT5 |
| **Índices (US500)** | Trend following | EMA 50/200, MACD, volume profile |
| **Bitcoin** | Momentum + ineficiencias liquidez | OBI, VWAP, sentiment ratio |

- [ ] Crear `InstrumentAlphaConfig` en `core/config.py` con features por asset_class
- [ ] Ponderar features de SHAP diferenciadas por clase en el `TechnicalAgent`
- [ ] Agregar `Donchian Channels` (20/55 períodos) como feature adicional
- [ ] Agregar `ADX` (14) para confirmar fuerza de tendencia
- [ ] Agregar `Momentum` multi-timeframe (1h + 4h) como feature compuesta

---

## 5. FASE 2 — Nuevos Agentes: StatisticalArbAgent

**Duración:** 2 semanas  
**Branch:** `feature/stat-arb-agent`  
**Prerequisito:** FASE 1 completa + modelos LightGBM entrenados

### 5.1 Diseño del agente

```
StatisticalArbAgent
├── Input:  OHLCV de par_A y par_B (series sincronizadas)
├── Test:   Johansen cointegration test (statsmodels)
├── Filter: Solo opera si p-value < 0.05 (cointegrados)
├── Ratio:  Kalman Filter para hedge ratio dinámico
├── Signal: z-score del spread → BUY/SELL/HOLD
└── Output: score [-1.0, +1.0] + p_value + half_life
```

### 5.2 Pares a operar

| Par | Justificación | Mercado |
|-----|--------------|---------|
| BTC / ETH | Alta cointegración histórica | Crypto |
| EUR/USD / GBP/USD | Par de divisas con política monetaria correlacionada | Forex |
| XAU / XAG | Metales preciosos (ratio histórico ~80:1) | Commodities |
| US500 / NAS100 | Índices con componentes compartidos | Índices |

### 5.3 Tareas

#### Semana 1: Implementación core

- [ ] Crear `core/agents/statistical_arb_agent.py` siguiendo schema de `technical_agent.py`
- [ ] Implementar `run_cointegration_test(series_a, series_b)` con Johansen
- [ ] Implementar `KalmanHedgeRatio` (filtro adaptativo para hedge ratio)
- [ ] Implementar `calculate_spread_zscore(spread, window=30)` 
- [ ] Implementar `calculate_half_life(spread)` para validar mean-reversion
- [ ] Lógica de señal: z-score > 2.0 → SELL spread; z-score < -2.0 → BUY spread
- [ ] Fallback: si test p-value > 0.05 → abstenerse (output = 0.0)

#### Semana 2: Integración y validación

- [ ] Registrar agente en `VotingEngine` con peso inicial 20-25% en forex/crypto
- [ ] Actualizar pesos por asset_class para incluir `stat_arb`:
  ```
  Crypto: technical=40%, regime=30%, microstructure=15%, stat_arb=15%
  Forex:  technical=45%, regime=35%, microstructure=0%,  stat_arb=20%
  ```
- [ ] Actualizar `SignalResult` schema para incluir métricas de cointegración
- [ ] Extender `xai_module.py` para explicar señales de spread en lenguaje natural
- [ ] Backtest walk-forward del agente: debe alcanzar Sharpe ≥ 1.2 en el período validado
- [ ] Tests unitarios: cointegración detectada correctamente en datos sintéticos
- [ ] Tests: z-score extremo genera señal correcta; p-value alto no genera señal
- [ ] 2 semanas de paper trading antes de incluir en consenso real

#### Dependencias

```
statsmodels>=0.14.0     # Johansen cointegration
pykalman>=0.9.7         # Kalman filter
scipy>=1.11.0           # Ya debería estar instalado
```

---

## 6. FASE 3 — Propuestas Condicionales

**Duración:** 3 semanas  
**Branch:** `feature/conditional-improvements`  
**Prerrequisito:** FASE 2 completa + mínimo 4 semanas paper trading activo

### 6.1 Smart Money Concepts (MSB + FVG)

**Tiempo estimado:** 4-6 días  
**Archivo:** `core/features/feature_engine.py`

Los conceptos de Smart Money (Market Structure Breaks y Fair Value Gaps) son detectables algorítmicamente y encajan en el `FeatureEngine` como features adicionales para el `TechnicalAgent`.

#### Features a implementar

```python
def detect_market_structure_break(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    MSB alcista: precio rompe por encima del último swing high
    MSB bajista: precio rompe por debajo del último swing low
    Retorna: 1 (bullish MSB), -1 (bearish MSB), 0 (sin ruptura)
    """

def detect_fair_value_gap(df: pd.DataFrame) -> pd.DataFrame:
    """
    FVG alcista: gap entre high[i-2] y low[i] (vela i-1 impulso alcista)
    FVG bajista: gap entre low[i-2] y high[i] (vela i-1 impulso bajista)
    Retorna columnas: fvg_bullish, fvg_bearish, fvg_size_pct
    """

def detect_order_block(df: pd.DataFrame, window: int = 5) -> pd.Series:
    """
    Order Block: última vela bajista antes de impulso alcista fuerte (y viceversa)
    """
```

#### Tareas

- [ ] Implementar `detect_market_structure_break()` con swing highs/lows adaptativos
- [ ] Implementar `detect_fair_value_gap()` para las 3 velas previas
- [ ] Implementar `detect_order_block()` como señal de soporte/resistencia dinámica
- [ ] Agregar las 5 nuevas features al `FeatureEngine` con nombres estandarizados
- [ ] Re-entrenar `TechnicalAgent` incluyendo las nuevas features
- [ ] Analizar SHAP values: si las features no son top-5, descartarlas
- [ ] Tests: FVG detectado correctamente en datos sintéticos conocidos
- [ ] Backtest comparativo: LightGBM con y sin SMC features (Sharpe delta)

### 6.2 HMM + Bayesian Change Point para RegimeAgent

**Tiempo estimado:** 7-10 días  
**Archivo:** `core/agents/regime_agent.py`

#### Modelo objetivo

```python
# Reemplazar clasificación manual de 5 regímenes por HMM probabilístico
from hmmlearn import hmm
import ruptures as rpt  # Bayesian Change Point Detection

class HMMRegimeDetector:
    """
    HMM con 5 estados latentes (mismo número que clasificación actual)
    Features de entrada: volatilidad realizada, skewness, retorno rolling, 
                         correlación con BTC/SPX, spread bid-ask
    """
    n_components = 5
    
    def fit(self, features_matrix: np.ndarray):
        self.model = hmm.GaussianHMM(n_components=self.n_components, 
                                      covariance_type="full", n_iter=100)
        self.model.fit(features_matrix)
    
    def predict_regime(self, features: np.ndarray) -> tuple[int, float]:
        """Retorna (regime_id, confidence_probability)"""
        regime = self.model.predict(features)[-1]
        confidence = self.model.predict_proba(features)[-1].max()
        return regime, confidence
```

#### Tareas

- [ ] Instalar `hmmlearn>=0.3.0` y `ruptures>=1.1.7`
- [ ] Implementar `HMMRegimeDetector` como alternativa al clasificador manual
- [ ] Feature vector para HMM: `[realized_vol_24h, vol_7d, return_24h, skewness, adx, spread]`
- [ ] Mapear los 5 estados HMM a los 5 regímenes existentes (alineación con lógica actual)
- [ ] Implementar `BayesianChangePointDetector` para detectar transiciones abruptas
- [ ] Exposer `regime_confidence` en el output del agente (ya está en schema)
- [ ] Modo A/B: ejecutar HMM y clasificador manual en paralelo durante 2 semanas
- [ ] Comparar `regime_accuracy` de ambos contra retorno real siguiente vela
- [ ] Migrar a HMM solo si accuracy HMM ≥ accuracy manual + 5%
- [ ] Tests: HMM entrenado en datos sintéticos con regímenes conocidos

### 6.3 FinBERT + Datos Macroeconómicos para FundamentalAgent

**Tiempo estimado:** 7-10 días  
**Archivo:** `core/agents/fundamental_agent.py`

#### Estrategia de datos (costo consciente)

| Fuente | Dato | Costo | Prioridad |
|--------|------|-------|-----------|
| NewsAPI (free tier) | Titulares financieros | Gratis (1000 req/día) | Alta |
| CoinGecko (ya integrado) | Sentiment, dominance | Gratis | Alta |
| FRED API | PMI, tasas, empleo | Gratis | Media |
| Glassnode Basic | MVRV, exchange flows | Gratis (retraso 24h) | Media |
| Glassnode Pro | Métricas real-time | $$$ | Solo si Sharpe mejora ≥ 0.3 |

#### Tareas

- [ ] Integrar `FinBERT` (o `ProsusAI/finbert` via HuggingFace) para scoring de noticias
- [ ] Crear `NewsIngestionClient` que consume NewsAPI (free tier)
- [ ] Implementar pipeline: noticia → FinBERT → sentiment_score [-1, +1] → promedio rolling
- [ ] Integrar FRED API para datos macroeconómicos (PMI, tasas, CPI, employment)
- [ ] Crear feature `macro_conditions_score` compuesta de indicadores FRED
- [ ] Integrar Glassnode Basic (MVRV ratio, exchange reserve) con delay 24h
- [ ] Implementar cache de 30 minutos para evitar re-procesar noticias
- [ ] Test A/B: FundamentalAgent con y sin NLP (2 semanas paper trading)
- [ ] Dar peso de votación (5-10%) al FundamentalAgent si NLP mejora el Sharpe

---

## 7. FASE 4 — Propuestas Futuras: RL + Meta-aprendizaje

**Duración:** 4 semanas  
**Branch:** `feature/advanced-agents`  
**Prerrequisito:** Mínimo 8 semanas de paper trading + datos reales de señales

### 7.1 RLAgent (PPO) para Position Sizing

**Tiempo estimado:** 10-14 días  
**Rol en el sistema:** No reemplaza el consenso — opera *después* del consenso para optimizar el tamaño de posición y el timing de entrada.

#### Arquitectura RL

```
Consenso genera señal BUY/SELL
          │
          ▼
    RLAgent recibe:
    ├── signal_score (del consenso)
    ├── current_portfolio_exposure
    ├── regime_confidence
    ├── recent_drawdown_pct
    ├── volatility_normalized
    └── time_of_day (sesión)
          │
          ▼
    PPO Policy decide:
    ├── action: {trade, skip, reduce_size}
    ├── size_pct: fracción del capital (0.0 - max_allowed)
    └── confidence: 0.0 - 1.0
          │
          ▼
    RiskManager valida igualmente (Kill Switch no se bypasea)
```

#### Tareas

#### Semana 1-2: Entorno de entrenamiento

- [ ] Instalar `stable-baselines3>=2.2.0` y `gymnasium>=0.29.0`
- [ ] Crear `core/simulation/rl_environment.py` (gym.Env) con:
  - Estado: vector de 12 features (señal, exposición, régimen, DD, vol, sesión, etc.)
  - Acción: 3 discretas (trade_full, trade_half, skip) o continua (size 0-1)
  - Recompensa: Sharpe rolling 20 operaciones — penalización por drawdown > 10%
- [ ] Usar datos históricos con señales paper para entrenamiento (no datos futuros)
- [ ] Implementar `walk-forward training`: entrenar en 2 años, validar en 3 meses

#### Semana 3: Entrenamiento y validación

- [ ] Entrenar agente PPO con `stable-baselines3.PPO` en datos históricos
- [ ] Validar en período out-of-sample: Sharpe ≥ 1.0, DD ≤ 15%
- [ ] Comparar contra Kelly sizing actual: ¿el RL mejora el Sharpe ajustado?
- [ ] Implementar `RLAgent.get_position_size(signal, state)` como interfaz al sistema

#### Semana 4: Integración

- [ ] Integrar `RLAgent` en `core/execution/executor.py` (post-consenso, pre-order)
- [ ] Modo A/B: Kelly sizing vs RL sizing en paper trading simultáneo
- [ ] Extender XAI: explicar por qué el RL eligió trade_full vs trade_half
- [ ] Guardar política entrenada en `data/models/rl_agent_ppo.zip`
- [ ] Retraining pipeline: re-entrenar mensualmente con nuevos datos paper

#### GPU y computación

```yaml
# docker-compose.gpu.yml — para entrenamiento
services:
  trainer:
    image: pytorch/pytorch:2.2.0-cuda11.8-cudnn8-runtime
    volumes:
      - ./data:/app/data
      - ./core:/app/core
    command: python scripts/train_rl_agent.py
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Si no hay GPU disponible: usar CPU con `n_steps=512` y `batch_size=64` (más lento pero funcional).

### 7.2 Meta-aprendizaje: Pesos Dinámicos por Desempeño

**Tiempo estimado:** 10 días  
**Archivo:** `core/consensus/meta_learner.py`

#### Concepto

```python
class MetaLearner:
    """
    Ajusta los pesos del VotingEngine basado en el desempeño reciente de cada agente.
    Requiere historial real de señales y retornos (mínimo 100 operaciones).
    """
    LOOKBACK_TRADES = 50    # Ventana de evaluación
    DECAY_FACTOR = 0.95     # Peso exponencial a señales más recientes
    MIN_WEIGHT = 0.10       # Piso mínimo por agente (evitar colapso)
    MAX_WEIGHT = 0.70       # Techo máximo (evitar monopolio)
    
    def calculate_agent_weights(self, signal_history: list[AgentSignalRecord]) -> dict:
        """
        Calcula sharpe rolling por agente en últimas N operaciones.
        Normaliza para que sumen 1.0. Aplica piso/techo.
        """
        weights = {}
        for agent_name in ["technical", "regime", "microstructure", "stat_arb"]:
            agent_signals = [s for s in signal_history if s.agent == agent_name]
            if len(agent_signals) < 10:
                weights[agent_name] = 1/4  # Igual peso si no hay historial
                continue
            sharpe = self._calculate_rolling_sharpe(agent_signals[-self.LOOKBACK_TRADES:])
            weights[agent_name] = max(self.MIN_WEIGHT, sharpe) 
        
        # Normalizar
        total = sum(weights.values())
        return {k: v/total for k, v in weights.items()}
```

#### Tareas

- [ ] Implementar tabla `agent_signal_history` en PostgreSQL (agente, señal, retorno_real)
- [ ] Crear `MetaLearner.calculate_agent_weights()` con Sharpe rolling ponderado
- [ ] Integrar en `VotingEngine` como capa adicional (sobrescribe pesos estáticos + dinámicos)
- [ ] Modo conservador: pesos meta-learner tienen peso 30%, pesos dinámicos 70% (gradual)
- [ ] Dashboard: gráfico de evolución de pesos por agente en el tiempo
- [ ] Tests: con historial sintético donde agente A siempre gana → peso A aumenta

---

## 8. FASE 5 — Rediseño UI Corporativo

**Duración:** 2 semanas  
**Branch:** `feature/ui-redesign`  
**Prerrequisito:** Fases 1-2 completas (para incluir métricas nuevas en el dashboard)

### 8.1 Filosofía de diseño

**Identidad visual:** Trading institucional. No retail. No crypto colorido.

| Elemento | Decisión |
|----------|---------|
| **Paleta** | Negro carbón `#0A0A0F` + Azul profundo `#0D1B2A` + Dorado `#C9A84C` |
| **Acentos** | Azul eléctrico `#1E6FD9` (señales activas) + Rojo `#C0392B` (alertas/short) |
| **Tipografía** | `IBM Plex Mono` (datos/números) + `Inter` (UI) — sin serif |
| **Estilo** | Flat dark. Sin gradientes. Bordes finos `#1E2A3A`. Sin sombras decorativas. |
| **Densidad** | Alta densidad de información. Paneles colapsables. No whitespace vacío. |

### 8.2 Paleta completa CSS

```css
:root {
  /* Fondos */
  --bg-primary:    #0A0A0F;   /* Negro carbón — fondo principal */
  --bg-secondary:  #0D1421;   /* Azul-negro — paneles */
  --bg-tertiary:   #111827;   /* Gris oscuro — cards */
  --bg-elevated:   #1A2332;   /* Bordes elevados, hover */

  /* Dorado — acciones principales, headers, KPIs positivos */
  --gold-primary:  #C9A84C;
  --gold-light:    #E8C97A;
  --gold-dark:     #8B6914;
  --gold-muted:    #4A3510;   /* Fondos dorado muy tenue */

  /* Azul — información, señales, links */
  --blue-primary:  #1E6FD9;
  --blue-light:    #4A9FFF;
  --blue-dark:     #0A3D7A;
  --blue-muted:    #0D2545;

  /* Semánticos */
  --success:       #16A34A;   /* BUY / profit */
  --danger:        #DC2626;   /* SELL / loss */
  --warning:       #D97706;   /* Atención / neutral */
  --info:          #0EA5E9;   /* Información */

  /* Texto */
  --text-primary:  #F1F5F9;
  --text-secondary:#94A3B8;
  --text-muted:    #475569;

  /* Bordes */
  --border:        #1E2A3A;
  --border-gold:   #C9A84C33;
  --border-active: #C9A84C;
}
```

### 8.3 Componentes nuevos a implementar

#### Barra de navegación lateral

```
┌─────────────────┐
│  ◈ TRADER IA    │  ← Logo + nombre (dorado)
│  v2.0           │
├─────────────────┤
│ ● Market View   │  ← Punto de color = estado live
│ ● Signals       │
│ ● Portfolio     │
│ ● Strategies    │
│ ● Backtesting   │
│ ● Risk Monitor  │
│ ● Simulator     │
├─────────────────┤
│ 🔴 KILL SWITCH  │  ← Botón prominente siempre visible
├─────────────────┤
│ Paper Mode ●    │  ← Indicador de modo (verde=paper, rojo=live)
│ Equity: $10,000 │
└─────────────────┘
```

#### Header con métricas globales

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│  Equity  │  Daily   │  Sharpe  │ Win Rate │  DD Max  │
│ $10,240  │  +2.4%   │   1.42   │  64.3%   │  -8.1%   │
│  ▲ +240  │  ████░   │  ●●●●○   │  ████░   │  ●●○○○   │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

#### Cards de señales activas

```
┌────────────────────────────────────────┐
│ ▲ BUY · BTCUSDT              [PAPER]  │
│                                         │
│ Entry:  $67,420.00    Conf: ████░ 82%  │
│ SL:     $65,800.00    R:R:  1:2.1      │
│ TP:     $70,100.00                     │
│                                         │
│ Técnico:42% ▪ Régimen:35% ▪ Arb:23%   │
│ "RSI sobreventa + EMA alcista + spread │
│  BTC-ETH en -2.3σ" ← explicación SHAP │
│                                         │
│ [Ver XAI completo]    [2m ago]          │
└────────────────────────────────────────┘
```

### 8.4 Páginas a rediseñar (por orden de prioridad)

#### 8.4.1 Dashboard principal (nueva página de inicio)

- [ ] Crear `app/pages/dashboard_home.py` como landing page
- [ ] KPI strip: Equity / Daily PnL / Sharpe / Win Rate / Max DD / Open Positions
- [ ] Gráfico de equity curve (Plotly, tema oscuro, línea dorada)
- [ ] Grid de señales activas (máximo 6 cards visibles, scroll interno)
- [ ] Panel de régimen actual por símbolo (mapa de calor 4×3)
- [ ] Feed de eventos recientes (últimas 10 acciones del sistema)
- [ ] Indicador de modo: PAPER / LIVE con color prominente

#### 8.4.2 Market View

- [ ] Reemplazar tablas planas por cards con sparklines integrados
- [ ] Color coding: verde/rojo para cambio porcentual (no solo texto)
- [ ] Indicador de régimen visual por símbolo (bullet indicator)
- [ ] Filtros por asset_class con tabs (Crypto / Forex / Índices / Commodities)

#### 8.4.3 Signals

- [ ] Cards de señales con anatomía completa (ver diseño arriba)
- [ ] Acordeón de XAI: contribución SHAP por feature con barras horizontales
- [ ] Historial de señales con filtros: símbolo / resultado / agente dominante
- [ ] Exportar historial a CSV desde el dashboard

#### 8.4.4 Risk Monitor

- [ ] Kill Switch con confirmación modal (no accidental click)
- [ ] Gauges circulares para: exposición total / drawdown / positions count
- [ ] Tabla de condiciones de riesgo (✓/✗ en tiempo real, las 7 condiciones)
- [ ] Alert timeline: últimas 20 alertas con timestamp y severidad

#### 8.4.5 Portfolio

- [ ] Distribución de capital: donut chart por asset_class
- [ ] Posiciones abiertas: tabla con P&L en tiempo real (verde/rojo)
- [ ] Matriz de correlaciones: heatmap de Plotly (con umbral visual de 0.85)
- [ ] Historial de operaciones cerradas con filtros

### 8.5 Theming en Streamlit

```python
# app/config/theme.py
import streamlit as st

def apply_corporate_theme():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Inter:wght@400;500;600&display=swap');
    
    :root {
        --primary-color: #C9A84C;
        --background-color: #0A0A0F;
        --secondary-background-color: #0D1421;
        --text-color: #F1F5F9;
        --font: 'Inter', sans-serif;
    }
    
    /* Override Streamlit defaults */
    .stApp { background-color: #0A0A0F; }
    .stSidebar { background-color: #0D1421; border-right: 1px solid #1E2A3A; }
    
    /* Métricas doradas */
    [data-testid="metric-container"] {
        background: #0D1421;
        border: 1px solid #1E2A3A;
        border-top: 2px solid #C9A84C;
        border-radius: 4px;
        padding: 12px;
    }
    
    /* Tablas */
    .dataframe { 
        border-collapse: collapse; 
        font-family: 'IBM Plex Mono', monospace;
        font-size: 13px;
    }
    
    /* Botón Kill Switch */
    .kill-switch-btn {
        background: #7B0000 !important;
        border: 1px solid #DC2626 !important;
        color: #FF4444 !important;
        font-weight: 600;
    }
    </style>
    """, unsafe_allow_html=True)
```

- [ ] Crear `app/config/theme.py` con todas las overrides CSS
- [ ] Crear `app/components/kpi_card.py` — componente reutilizable de métricas
- [ ] Crear `app/components/signal_card.py` — card de señal con XAI integrado
- [ ] Crear `app/components/regime_indicator.py` — indicador visual de régimen
- [ ] Crear `app/components/correlation_heatmap.py` — heatmap de correlaciones
- [ ] Integrar `apply_corporate_theme()` en `app/dashboard.py` (punto de entrada)
- [ ] Validar contraste de colores (WCAG AA mínimo para accesibilidad)

### 8.6 Plotly Charts — Estilo corporativo

```python
# app/config/chart_theme.py

CHART_LAYOUT = {
    "template": "plotly_dark",
    "paper_bgcolor": "#0A0A0F",
    "plot_bgcolor": "#0D1421",
    "font": {"family": "IBM Plex Mono, monospace", "color": "#94A3B8", "size": 12},
    "xaxis": {"gridcolor": "#1E2A3A", "linecolor": "#1E2A3A"},
    "yaxis": {"gridcolor": "#1E2A3A", "linecolor": "#1E2A3A"},
    "colorway": ["#C9A84C", "#1E6FD9", "#16A34A", "#DC2626", "#0EA5E9"],
}

EQUITY_CURVE_STYLE = {
    "line": {"color": "#C9A84C", "width": 2},
    "fill": "tozeroy",
    "fillcolor": "rgba(201, 168, 76, 0.08)",
}
```

---

## 9. Infraestructura de Entornos

### 9.1 Separación completa dev / staging / prod

```yaml
# docker-compose.staging.yml
version: "3.9"
services:
  app-staging:
    build: .
    env_file: .env.staging
    ports: ["8100:8000", "8501:8501"]   # Puertos distintos a prod
    depends_on: [db-staging, redis-staging]
  
  db-staging:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_DB: trader_ai_staging
      POSTGRES_USER: trader
      POSTGRES_PASSWORD: ${DB_PASS_STAGING}
    ports: ["5433:5432"]                # Puerto diferente a prod (5432)
    volumes: ["staging-db:/var/lib/postgresql/data"]
  
  redis-staging:
    image: redis:7-alpine
    ports: ["6380:6379"]                # Puerto diferente a prod

volumes:
  staging-db:
```

### 9.2 Scripts de gestión

```bash
# scripts/manage_envs.sh

# Levantar staging limpio
staging-up() {
    docker-compose -f docker-compose.staging.yml up -d
    sleep 5
    docker-compose -f docker-compose.staging.yml exec app-staging \
        python scripts/init_db.py --env staging
    echo "Staging disponible en :8100 (API) y :8501 (Dashboard)"
}

# Reset completo de staging
staging-reset() {
    docker-compose -f docker-compose.staging.yml down -v
    staging-up
}

# Correr smoke test en staging
staging-smoke() {
    python scripts/smoke_test.py --env staging --symbols BTCUSDT EURUSD --cycles 1
}
```

### 9.3 Variables de entorno por entorno

| Variable | Dev | Staging | Prod |
|----------|-----|---------|------|
| `EXECUTION_MODE` | paper | paper | paper → live |
| `BINANCE_TESTNET` | true | true | false |
| `MT5_SERVER` | Demo | Demo | Live |
| `DATABASE_URL` | local:5432 | local:5433 | VPS:5432 |
| `LOG_LEVEL` | DEBUG | INFO | WARNING |
| `SCHEDULER_ENABLED` | false | true | true |
| `TELEGRAM_ENABLED` | false | false | true |

---

## 10. Métricas de Aceptación

Cada fase debe cumplir estas métricas antes de fusionarse a `main`:

### FASE 0

| Métrica | Umbral |
|---------|--------|
| Test coverage total | ≥ 80% |
| Tiempo suite de tests | ≤ 3 min (unit) + ≤ 8 min (integration) |
| Smoke test staging completa sin errores | 100% |
| 0 errores en mypy strict | ✓ |

### FASE 1

| Métrica | Umbral |
|---------|--------|
| Pesos dinámicos suman 1.0 siempre | ✓ |
| Filtro macro bloquea correctamente por asset_class | ✓ |
| Correlación BTC-ETH bloqueada si > 0.90 | ✓ |
| Tests nuevos del módulo | ≥ 15 tests nuevos |

### FASE 2 (StatisticalArbAgent)

| Métrica | Umbral |
|---------|--------|
| Backtest walk-forward Sharpe | ≥ 1.2 |
| Max Drawdown en backtest | ≤ 20% |
| Win rate en datos OOS | ≥ 55% |
| Paper trading 2 semanas sin errores | ✓ |
| Cointegración detectada correctamente en test sintético | 100% |

### FASE 3 (Condicionales)

| Métrica | Umbral |
|---------|--------|
| HMM accuracy vs clasificador manual | ≥ manual + 3% |
| FinBERT mejora Sharpe en paper | ≥ 0.1 de Sharpe |
| SMC features en top-10 SHAP | ≥ 3 de 5 |

### FASE 4 (RL + Meta-aprendizaje)

| Métrica | Umbral |
|---------|--------|
| RL vs Kelly Sharpe delta | ≥ 0.2 positivo |
| RL Max Drawdown | ≤ 15% |
| Meta-learner estabilidad (varianza de pesos) | Converge en ≤ 50 ops |

### FASE 5 (UI)

| Métrica | Umbral |
|---------|--------|
| Tiempo de carga dashboard | ≤ 2.5s |
| Contraste de colores (WCAG AA) | ≥ 4.5:1 |
| 0 errores de consola en producción | ✓ |
| Dashboard responsive en móvil | ✓ |

---

## 11. Checklist Maestro

### FASE 0 — Testing Infrastructure

- [ ] `docker-compose.staging.yml` creado y funcional
- [ ] `.env.staging` y `.env.test` configurados
- [ ] `tests/fixtures/` con datos de mercado embebidos
- [ ] Mocks de `BinanceClient` y `MT5Client`
- [ ] 15+ tests nuevos (correlación, pesos dinámicos, filtro macro)
- [ ] `pytest-cov` con umbral ≥ 80%
- [ ] CI/CD actualizado con job de integration tests y staging deploy
- [ ] Smoke test automático en staging

### FASE 1 — Quick Wins

- [ ] `VotingEngine.get_dynamic_weights()` implementado
- [ ] `FundamentalAgent` refactorizado con `MACRO_BLOCK_RULES` por asset_class
- [ ] `PortfolioManager.can_open_position()` con correlación rolling
- [ ] `LOGICA_CORE.md` completo en raíz del proyecto
- [ ] `VENTAJA_COMPETITIVA.md` con tabla comparativa
- [ ] `InstrumentAlphaConfig` con features priorizadas por activo
- [ ] `ADX` y `Donchian Channels` agregados a `FeatureEngine`
- [ ] Todos los tests nuevos pasando en CI

### FASE 2 — StatisticalArbAgent

- [ ] `core/agents/statistical_arb_agent.py` implementado
- [ ] Test de cointegración Johansen integrado
- [ ] Kalman Filter para hedge ratio dinámico
- [ ] Pares configurados: BTC-ETH, EUR-GBP, XAU-XAG, US500-NAS100
- [ ] Agente registrado en `VotingEngine` con pesos por asset_class
- [ ] XAI extendido para señales de spread
- [ ] Backtest walk-forward: Sharpe ≥ 1.2, DD ≤ 20%
- [ ] 2 semanas paper trading sin errores críticos

### FASE 3 — Condicionales

- [ ] `HMMRegimeDetector` implementado y en modo A/B
- [ ] `BayesianChangePointDetector` implementado
- [ ] MSB, FVG, Order Block detectados en `FeatureEngine`
- [ ] Re-entrenamiento LightGBM con SMC features
- [ ] `NewsIngestionClient` + FinBERT pipeline
- [ ] FRED API integrado para datos macro
- [ ] Glassnode Basic integrado (MVRV, exchange reserve)
- [ ] Test A/B de todas las mejoras (2 semanas paper cada una)

### FASE 4 — RL + Meta-aprendizaje

- [ ] `core/simulation/rl_environment.py` (gymnasium.Env)
- [ ] PPO policy entrenada con walk-forward
- [ ] `RLAgent` integrado en executor post-consenso
- [ ] A/B Kelly vs RL en paper trading
- [ ] `MetaLearner.calculate_agent_weights()` implementado
- [ ] Tabla `agent_signal_history` en PostgreSQL
- [ ] Dashboard: gráfico de evolución de pesos por agente
- [ ] Retraining pipeline mensual documentado

### FASE 5 — UI Corporativo

- [ ] `app/config/theme.py` con paleta completa (negro/azul/dorado)
- [ ] `app/config/chart_theme.py` con CHART_LAYOUT y EQUITY_CURVE_STYLE
- [ ] Componente `kpi_card.py` reutilizable
- [ ] Componente `signal_card.py` con XAI integrado
- [ ] Componente `regime_indicator.py` visual
- [ ] Componente `correlation_heatmap.py`
- [ ] Dashboard home: equity curve + KPI strip + signal grid + regime map
- [ ] Market View: cards con sparklines + filtros por asset_class
- [ ] Signals: acordeón XAI + historial filtrable + exportar CSV
- [ ] Risk Monitor: gauges + Kill Switch modal + alert timeline
- [ ] Portfolio: donut chart + posiciones P&L real-time + correlation heatmap
- [ ] Validación WCAG AA (contraste ≥ 4.5:1)
- [ ] Tiempo de carga ≤ 2.5s

---

*Documento generado: 30 de Marzo, 2026 · TRADER IA v3.0 · Revisión: Plan Integral*
