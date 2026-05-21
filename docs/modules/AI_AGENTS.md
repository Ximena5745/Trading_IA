# Módulo: AI Agents

> Sistema multi-agente de IA para generación de señales

---

## 1. OBJETIVO

Proveer un sistema de múltiples agentes IA especializados que analicen el mercado desde diferentes perspectivas y generen señales de trading con explicabilidad.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Agent coordination | Gestión de múltiples agentes |
| Signal generation | Generación de señales por agente |
| SHAP explanation | Explicabilidad con SHAP |
| Regime detection | Clasificación de régimen |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                        AGENTS LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      BaseAgent (ABC)                     │  │
│  │  - Interfaz común                                         │  │
│  │  - Signal generation                                      │  │
│  │  - SHAP explanation                                      │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │                    AgentOrchestrator                     │  │
│  │  - Coordina agentes                                      │  │
│  │  - Collecta señales                                      │  │
│  │  - Parallel execution                                     │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌───────────┬───────────┬───────────┬───────────┐            │
│  │           │           │           │           │            │
│  │ Technical │  Regime   │Microstruc │Fundamenta │            │
│  │  Agent    │  Agent    │   Agent   │   Agent   │            │
│  │  (LightGBM│  (HMM)    │(OrderBook)│(Sentiment)│            │
│  └───────────┴───────────┴───────────┴───────────┘            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 BaseAgent

**Archivo:** `core/agents/base_agent.py`

**Interfaz abstracta:**

```python
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...
    
    @property
    def asset_classes(self) -> list[str]: ...
    
    @abstractmethod
    async def analyze(
        self,
        market_data: MarketData,
        features: pd.DataFrame
    ) -> AgentSignal: ...
    
    @abstractmethod
    def explain(self, signal: AgentSignal) -> AgentExplanation: ...
```

### 4.2 TechnicalAgent

**Archivo:** `core/agents/technical_agent.py`

**Descripción:** Agente basado en ML (LightGBM) con análisis técnico.

**Modelo:**
- Algoritmo: LightGBM Classifier
- Clases: BUY, SELL, HOLD
- Features: 45+ indicadores técnicos

**Pipeline:**
```python
class TechnicalAgent(BaseAgent):
    def __init__(self, model_path: str):
        self._model = load_model(model_path)
        self._explainer = shap.TreeExplainer(self._model)
    
    async def analyze(
        self,
        market_data: MarketData,
        features: pd.DataFrame
    ) -> AgentSignal:
        # 1. Preparar features
        X = self._prepare_features(features)
        
        # 2. Predecir
        proba = self._model.predict_proba(X)
        prediction = self._model.predict(X)
        
        # 3. Calcular confidence
        confidence = max(proba[0])
        
        # 4. Generar señal
        return AgentSignal(
            action=prediction,
            confidence=confidence,
            probabilities=proba[0]
        )
```

**SHAP Explanation:**
```python
def explain(self, signal: AgentSignal) -> AgentExplanation:
    shap_values = self._explainer.shap_values(X)
    
    return AgentExplanation(
        factors=[
            Factor(name="rsi_14", value=0.15, direction="positive"),
            Factor(name="ema_21_cross", value=0.12, direction="positive"),
            Factor(name="volume_spike", value=-0.08, direction="negative"),
        ],
        summary=self._generate_summary(shap_values)
    )
```

### 4.3 RegimeAgent

**Archivo:** `core/agents/regime_agent.py`

**Descripción:** Clasificador de régimen de mercado usando HMM.

**Régimenes:**
| Regime | Descripción | Trading style |
|--------|-------------|----------------|
| TRENDING_UP | Tendencia alcista | Momentum |
| TRENDING_DOWN | Tendencia bajista | Momentum |
| RANGING | rango lateral | Mean reversion |
| VOLATILE | Alta volatilidad | Reducción de exposición |
| CALM | Baja volatilidad | Normal |

**Modelo HMM:**
```python
class RegimeAgent(BaseAgent):
    def __init__(self, model_path: str):
        self._hmm = joblib.load(model_path)
    
    async def analyze(
        self,
        market_data: MarketData,
        features: pd.DataFrame
    ) -> AgentSignal:
        # Features para HMM
        X = features[["returns", "volatility", "volume_change"]]
        
        # Predecir régimen
        regime = self._hmm.predict(X)[-1]
        
        # Generar señal según régimen
        signal = self._regime_to_signal(regime)
        
        return signal
```

### 4.4 MicrostructureAgent

**Archivo:** `core/agents/microstructure_agent.py` (referenced)

**Descripción:** Análisis de order book y microstructure.

**Métricas:**
- Bid-Ask spread
- Order book imbalance
- Large order detection
- Liquidity analysis
- Spread evolution

```python
class MicrostructureAgent(BaseAgent):
    async def analyze(
        self,
        market_data: MarketData,
        order_book: OrderBook
    ) -> AgentSignal:
        # Calcular imbalance
        imbalance = self._calculate_imbalance(order_book)
        
        # Detectar presión
        pressure = self._detect_pressure(order_book)
        
        # Generar señal
        return AgentSignal(...)
```

### 4.5 FundamentalAgent

**Archivo:** `core/agents/fundamental_agent.py` (referenced)

**Descripción:** Análisis de eventos y sentimiento.

**Fuentes:**
- News sentiment (mock)
- Calendar events
- Macro indicators

### 4.6 MetaAgent

**Archivo:** `core/strategies/meta_agent.py`

**Propósito:** Ensemble de agentes con meta-learning.

---

## 5. SHAP EXPLANATION

### 5.1 Estructura de Explicación

```python
class AgentExplanation:
    factors: list[ExplanationFactor]
    summary: str
    shap_values: np.ndarray
    
class ExplanationFactor:
    name: str           # Feature name
    value: float        # SHAP value
    direction: str      # positive/negative
    description: str    # Human readable
```

### 5.2 Ejemplo

```json
{
  "agent": "technical",
  "decision": "BUY",
  "confidence": 0.78,
  "factors": [
    {"name": "rsi_14", "value": 0.15, "direction": "positive", "desc": "RSI en zona neutral"},
    {"name": "ema_9_21_cross", "value": 0.12, "direction": "positive", "desc": "EMA bullish cross"},
    {"name": "volume_spike", "value": -0.08, "direction": "negative", "desc": "Volumen bajó"}
  ],
  "summary": "La señal BUY se basa principalmente en el crossover bullish de EMAs y el RSI estable."
}
```

---

## 6. EVENTOS

### 6.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `agent.signal` | Señal de agente | `{agent, signal}` |
| `agent.error` | Error en agente | `{agent, error}` |

### 6.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `market_data.updated` | Trigger análisis |

---

## 7. INPUTS/OUTPUTS

### 7.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| Market data | MarketData | OHLCV + order book |
| Features | pd.DataFrame | Features calculadas |
| Symbol | str | Símbolo a analizar |

### 7.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Agent signal | Consensus | Señal del agente |
| Explanation | XAI Module | SHAP values |

---

## 8. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Model not loaded | Initialize lazily + cache |
| Prediction error | Return HOLD + log error |
| Low confidence | Return HOLD |
| SHAP error | Skip explanation |

---

## 9. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Analysis time | < 100ms |
| Parallel agents | 4 concurrent |
| Memory per agent | < 100MB |

---

## 10. OBSERVABILIDAD

### 10.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `agent.signals.total` | Counter | Señales por agente |
| `agent.confidence` | Histogram | Distribución |
| `agent.errors` | Counter | Errores por agente |
| `agent.latency` | Histogram | Latencia |

### 10.2 Logs

```json
{
  "event": "agent_signal",
  "agent": "technical",
  "symbol": "BTCUSDT",
  "action": "BUY",
  "confidence": 0.78,
  "regime": "trending_up",
  "time_ms": 45
}
```

---

## 11. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_signal_generation | Unit | 80% |
| test_shap_explanation | Unit | 80% |
| test_regime_detection | Unit | 90% |
| test_integration | Integration | 60% |

---

## 12. EJEMPLOS DE USO

```python
# Crear agentes
agents = [
    TechnicalAgent("models/technical_v1.pkl"),
    RegimeAgent("models/regime_hmm.pkl"),
    MicrostructureAgent(),
    FundamentalAgent(),
]

# Analizar mercado
signals = {}
for agent in agents:
    signal = await agent.analyze(market_data, features)
    signals[agent.name] = signal

# Obtener explicación
explanation = technical_agent.explain(signals["Technical"])
```

---

## 13. KPIs

| KPI | Target |
|-----|--------|
| Agent accuracy | > 50% |
| SHAP coverage | 100% |
| Uptime | 99.9% |

---

*Volver al [INDEX](../INDEX.md)*