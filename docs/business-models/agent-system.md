# Sistema Multi-Agente IA

> Sistema de 4 agentes independientes con votación ponderada

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/agents/base_agent.py` | Interfaz abstracta |
| `core/agents/technical_agent.py` | Análisis técnico (LightGBM) |
| `core/agents/regime_agent.py` | Clasificación de régimen |
| `core/agents/microstructure_agent.py` | Análisis de order book |
| `core/agents/fundamental_agent.py` | Datos fundamentales |

---

## Arquitectura Multi-Agente

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MULTI-AGENT SYSTEM                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐      │
│  │  TECHNICAL AGENT  │  │   REGIME AGENT    │  │MICROSTRUCTURE AGT │      │
│  │                   │  │                   │  │                   │      │
│  │  • LightGBM       │  │  • Market state   │  │  • Order book     │      │
│  │  • 17 features    │  │  • 5 regimes      │  │  • Bid-ask spread │      │
│  │  • SHAP values    │  │  • Gate logic     │  │  • Imbalance      │      │
│  │                   │  │                   │  │                   │      │
│  │  Weight: 45-55%   │  │  Weight: 35-45%   │  │  Weight: 0-20%    │      │
│  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘      │
│            │                       │                       │                │
│            └───────────────────────┼───────────────────────┘                │
│                                    │                                        │
│                                    ▼                                        │
│                        ┌───────────────────────┐                           │
│                        │   CONSENSUS ENGINE    │                           │
│                        │  Weighted Voting +    │                           │
│                        │  Regime Gate          │                           │
│                        └───────────┬───────────┘                           │
│                                    │                                        │
│  ┌───────────────────┐            │                                        │
│  │ FUNDAMENTAL AGENT │◄───────────┘                                        │
│  │                   │  (Filtro - sin peso en votación)                   │
│  │  • Fear & Greed   │                                                     │
│  │  • Sentimiento    │                                                     │
│  │  • Eventos macro  │                                                     │
│  │                   │                                                     │
│  │  Role: FILTER     │                                                     │
│  └───────────────────┘                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Pesos por Clase de Activo

| Agente | Crypto | Forex/Indices/Commodities |
|--------|--------|---------------------------|
| **Technical** | 45% | 55% |
| **Regime** | 35% | 45% |
| **Microstructure** | 20% | 0% (sin L2) |
| **Fundamental** | Filtro | Filtro |

> MicrostructureAgent tiene 0% para MT5 porque no expone datos L2 del order book.

---

## BaseAgent

### Interfaz Abstracta

```python
class BaseAgent(ABC):
    @abstractmethod
    def predict(self, features: FeatureSet) -> AgentOutput:
        """Genera predicción basada en features."""
        pass
    
    @abstractmethod
    def is_ready(self) -> bool:
        """Retorna True si el agente está listo para predecir."""
        pass
```

---

## TechnicalAgent

### Ubicación
`core/agents/technical_agent.py`

### Descripción
Modelo LightGBM entrenado sobre features técnicos. Predice el signo del retorno de la siguiente vela.

### Modelo

```python
class TechnicalAgent(AbcAgent):
    agent_id = "technical_v1"
    model_version = "v1.0.0"
    
    def __init__(self, model_path: str = "data/models/technical_agent_v1.pkl"):
        self._model_path = model_path
        self._model = None
        self._explainer = None  # SHAP TreeExplainer
        self._load_model()
```

### Features Utilizadas (17)

```python
FEATURE_ORDER = [
    "rsi_14", "rsi_7",
    "ema_9", "ema_21", "ema_50", "ema_200",
    "macd_line", "macd_signal", "macd_histogram",
    "atr_14",
    "bb_upper", "bb_lower", "bb_width",
    "vwap",
    "volume_sma_20", "volume_ratio",
    "obv"
]
```

### Predicción

```python
def predict(self, features: FeatureSet) -> AgentOutput:
    """
    1. Convertir features a array numpy
    2. Si modelo entrenado: predict_proba + SHAP
    3. Si no: fallback rule-based
    4. Convertir score a dirección (BUY/SELL/NEUTRAL)
    """
```

### Score Calculation

```python
# Con modelo:
proba = model.predict_proba(X)[0]
score = proba[1] - proba[0]  # Class 1 = BUY, Class 0 = SELL

# Fallback rule-based:
score = 0.0
if rsi_14 < 30: score += 0.4
elif rsi_14 > 70: score -= 0.4
if trend_direction == "bullish": score += 0.3
if macd_histogram > 0: score += 0.2
# ...
```

### Threshold de Dirección

```python
SCORE_THRESHOLD = 0.30

def _score_to_direction(score: float) -> str:
    if score >= SCORE_THRESHOLD: return "BUY"
    if score <= -SCORE_THRESHOLD: return "SELL"
    return "NEUTRAL"
```

### Entrenamiento

```python
def train(self, X: np.ndarray, y: np.ndarray) -> None:
    """
    Entrena LightGBM:
    - n_estimators=200
    - learning_rate=0.05
    - num_leaves=31
    - Guarda modelo + SHAP explainer en .pkl
    """
```

### SHAP Values

```python
# Para cada predicción, genera contribución de cada feature:
shap_values = {
    "rsi_14": 0.25,        # +0.25 → favorece BUY
    "macd_histogram": 0.18, # +0.18 → favorece BUY
    "ema_9": 0.12,
    "ema_21": 0.08,
    # ... resto ≈ 0
}
```

---

## RegimeAgent

### Ubicación
`core/agents/regime_agent.py`

### Descripción
Clasifica el estado del mercado en 5 regímenes.

### Estados

```python
class MarketRegime(str, Enum):
    BULL_TRENDING = "bull_trending"       # Score ≥ 0.5
    BEAR_TRENDING = "bear_trending"       # Score ≤ -0.5
    SIDEWAYS_LOW_VOL = "sideways_low_vol" # -0.5 < score < 0.5
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"
    VOLATILE_CRASH = "volatile_crash"     # score ≤ -0.9 OR confidence < 0.5
```

### Lógica de Clasificación

```python
def predict(self, features: FeatureSet) -> AgentOutput:
    """
    1. Analizar tendencia (EMA cross + price position)
    2. Analizar volatilidad (ATR percentil)
    3. Calcular confidence
    4. Determinar si señales están permitidas
    """
```

### Gate Logic

```python
# El RegimeAgent puede BLOQUEAR señales:
signal_allowed = (
    regime != VOLATILE_CRASH and
    confidence >= 0.50 and
    score > -0.9
)

# Si signal_allowed = False:
# → Consensus retorna NEUTRAL sin importar otros agentes
```

### Score Interpretation

| Score | Regime | Signal Allowed |
|-------|--------|----------------|
| ≥ 0.5 | BULL_TRENDING | ✅ |
| -0.5 to 0.5 | SIDEWAYS | ✅ |
| ≤ -0.5 | BEAR_TRENDING | ✅ |
| ≤ -0.9 | VOLATILE_CRASH | ❌ |

---

## MicrostructureAgent

### Ubicación
`core/agents/microstructure_agent.py`

### Descripción
Analiza datos L2 del order book para detectar presión compradora/vendedora.

### Features

```python
class MicrostructureAgent(AbcAgent):
    agent_id = "microstructure_v1"
    
    def analyze_order_book(self, order_book: dict) -> dict:
        """
        Calcula:
        - bid_ask_spread: (ask[0] - bid[0]) / mid
        - order_book_imbalance: (bid_vol - ask_vol) / total_vol
        """
```

### Cálculo de Imbalance

```python
def _calculate_imbalance(self, bids: list, asks: list) -> float:
    """
    Imbalance = (Total Bid Volume - Total Ask Volume) / Total Volume
    
    Resultado:
    - +1.0: Solo compradores (presión alcista)
    - 0.0: Equilibrio
    - -1.0: Solo vendedores (presión bajista)
    """
```

### Disponibilidad

| Asset Class | Order Book Disponible |
|-------------|----------------------|
| Crypto | ✅ Binance L2 |
| Forex | ❌ MT5 no expone L2 |
| Indices | ❌ |
| Commodities | ❌ |

---

## FundamentalAgent

### Ubicación
`core/agents/fundamental_agent.py`

### Descripción
Analiza datos fundamentales y eventos macroeconómicos.

### Funciones

```python
class FundamentalAgent:
    def refresh(self) -> None:
        """Actualiza datos cada 30 minutos."""
        
    def is_blocked_by_event(self, symbol: str) -> bool:
        """
        Retorna True si hay evento macro dentro de ±30 min.
        Bloquea trading en Forex/Índices durante alta volatilidad.
        """
        
    def get_sentiment(self) -> dict:
        """
        Retorna:
        - fear_greed_index: 0-100
        - sentiment: "extreme_fear" | "fear" | "neutral" | "greed" | "extreme_greed"
        """
```

### Eventos Monitoreados

| Evento | Impacto | Bloqueo |
|--------|---------|---------|
| NFP | Alto | ±30 min |
| FOMC | Alto | ±60 min |
| ECB Rate | Alto | ±30 min |
| CPI | Medio | ±30 min |
| GDP | Medio | ±30 min |

### Rol en Sistema

```
FundamentalAgent NO tiene peso en votación.

Su rol es:
1. Bloquear trading durante eventos macro (gate)
2. Proporcionar contexto de sentimiento (XAI)
3. Filtrar señales en condiciones extremas
```

---

## Flujo de Predicción

```
FeatureSet
    │
    ▼
┌─────────────────────────────────────────────────────────────┐
│                    AGENTS EXECUTION                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  TechnicalAgent.predict(features)                           │
│       │                                                     │
│       ▼                                                     │
│  AgentOutput(agent_id="technical_v1",                       │
│              score=0.65, direction="BUY",                   │
│              shap_values={...})                             │
│                                                             │
│  RegimeAgent.predict(features)                              │
│       │                                                     │
│       ▼                                                     │
│  AgentOutput(agent_id="regime_v1",                          │
│              score=0.45, direction="BUY",                   │
│              confidence=0.72)                               │
│                                                             │
│  MicrostructureAgent.predict(features)                      │
│       │                                                     │
│       ▼                                                     │
│  AgentOutput(agent_id="microstructure_v1",                  │
│              score=0.30, direction="BUY")                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
    │
    ▼
Consensus Engine (weighted voting)
    │
    ▼
ConsensusOutput (final_direction, weighted_score)
```

---

## Testing

### Tests Unitarios

```bash
# Technical Agent
pytest tests/unit/test_technical_agent.py -v

# Regime Agent
pytest tests/unit/test_regime_agent.py -v

# Microstructure Agent
pytest tests/unit/test_microstructure_agent.py -v

# Voting Engine
pytest tests/unit/test_voting_engine_mt5.py -v
```

---

*Volver al [índice de modelos](README.md)*
