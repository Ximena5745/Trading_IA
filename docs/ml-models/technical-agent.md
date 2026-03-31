# TechnicalAgent - Modelo LightGBM

> Modelo de machine learning para predicción técnica

## Archivo Principal

`core/agents/technical_agent.py`

---

## Visión General

```
┌─────────────────────────────────────────────────────────────────┐
│                    TECHNICAL AGENT                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Input: FeatureSet (17 indicadores)                            │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              LIGHTGBM CLASSIFIER                        │   │
│  │                                                         │   │
│  │  Training:                                              │   │
│  │  - n_estimators=200                                     │   │
│  │  - learning_rate=0.05                                   │   │
│  │  - num_leaves=31                                        │   │
│  │                                                         │   │
│  │  Output: [P(SELL), P(BUY)]                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  Score = P(BUY) - P(SELL)  # Rango: -1.0 a +1.0              │
│         │                                                       │
│         ▼                                                       │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              SHAP TREE EXPLAINER                         │   │
│  │                                                         │   │
│  │  Genera contribución de cada feature:                   │   │
│  │  {"rsi_14": 0.25, "macd_histogram": 0.18, ...}         │   │
│  └─────────────────────────────────────────────────────────┘   │
│         │                                                       │
│         ▼                                                       │
│  AgentOutput (score, direction, shap_values)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Features de Entrada (17)

```python
FEATURE_ORDER = [
    # Momentum (5)
    "rsi_14",           # RSI 14-period
    "rsi_7",            # RSI 7-period (acelerado)
    "macd_line",        # MACD principal
    "macd_signal",      # Línea de señal
    "macd_histogram",   # Diferencia Line - Signal
    
    # Trend (4)
    "ema_9",            # EMA corto plazo
    "ema_21",           # EMA medio plazo
    "ema_50",           # EMA largo plazo
    "ema_200",          # EMA muy largo plazo
    
    # Volatility (4)
    "atr_14",           # Average True Range
    "bb_upper",         # Bollinger Band superior
    "bb_lower",         # Bollinger Band inferior
    "bb_width",         # Ancho normalizado
    
    # Volume (4)
    "vwap",             # Volume Weighted Average Price
    "volume_sma_20",    # SMA del volumen
    "volume_ratio",     # Volumen vs media
    "obv"               # On Balance Volume
]
```

---

## Predicción

### Flujo

```python
def predict(self, features: FeatureSet) -> AgentOutput:
    # 1. Convertir features a array
    feature_vector = self._features_to_array(features)
    
    # 2. Predecir con modelo (o fallback)
    if self._model is not None:
        score = self._predict_with_model(feature_vector)
        shap_values = self._compute_shap(feature_vector)
    else:
        score = self._rule_based_score(features)
        shap_values = self._rule_based_shap(features)
    
    # 3. Convertir score a dirección
    direction = self._score_to_direction(score)
    
    # 4. Calcular confidence
    confidence = min(abs(score) * 1.5, 1.0)
    
    return AgentOutput(...)
```

### Score Calculation

```python
def _predict_with_model(self, X: np.ndarray) -> float:
    proba = self._model.predict_proba(X)[0]
    # Class 0 = SELL, Class 1 = BUY
    return float(proba[1] - proba[0])
```

### Threshold de Dirección

```python
SCORE_THRESHOLD = 0.30

def _score_to_direction(score: float) -> str:
    if score >= SCORE_THRESHOLD:
        return "BUY"
    if score <= -SCORE_THRESHOLD:
        return "SELL"
    return "NEUTRAL"
```

---

## SHAP Values

### Generación

```python
def _compute_shap(self, X: np.ndarray) -> dict[str, float]:
    if self._explainer is None:
        return {f: 0.0 for f in FEATURE_ORDER}
    
    shap_vals = self._explainer.shap_values(X)
    values = shap_vals[1][0] if isinstance(shap_vals, list) else shap_vals[0]
    return {f: round(float(v), 6) for f, v in zip(FEATURE_ORDER, values)}
```

### Interpretación

```python
# Ejemplo de output:
{
    "rsi_14": 0.25,        # +0.25 favorece BUY
    "macd_histogram": 0.18, # +0.18 favorece BUY
    "ema_9": 0.12,         # +0.12 favorece BUY
    "ema_21": 0.08,        # +0.08 favorece BUY
    "atr_14": -0.02,       # -0.02 favorece ligeramente SELL
    "volume_ratio": 0.05,  # +0.05 favorece BUY
    # ... resto ≈ 0
}
```

### Uso en Explicación

```
Señal BUY generada con confianza 0.78

Factores principales:
1. RSI_14 en sobreventa (28) - Contribución: +0.25
2. MACD histogram positivo y creciente - Contribución: +0.18
3. Cruce alcista EMA 9/21 - Contribución: +0.12
4. Precio sobre EMA 50 - Contribución: +0.08
```

---

## Fallback Rule-Based

### Cuando se Usa

```python
# Cuando el modelo .pkl no existe
if self._model is None:
    score = self._rule_based_score(features)
    shap_values = self._rule_based_shap(features)
```

### Lógica

```python
def _rule_based_score(self, features: FeatureSet) -> float:
    score = 0.0
    
    # RSI signals
    if features.rsi_14 < 30:
        score += 0.4
    elif features.rsi_14 > 70:
        score -= 0.4
    
    # Trend
    if features.trend_direction == "bullish":
        score += 0.3
    elif features.trend_direction == "bearish":
        score -= 0.3
    
    # MACD
    if features.macd_histogram > 0:
        score += 0.2
    else:
        score -= 0.2
    
    # Volume confirmation
    if features.volume_ratio > 1.5:
        score *= 1.2
    
    return max(-1.0, min(1.0, score))
```

---

## Entrenamiento

### Script

```bash
python scripts/retrain.py --symbol BTCUSDT --timeframe 1h
```

### Implementación

```python
def train(self, X: np.ndarray, y: np.ndarray) -> None:
    import lightgbm as lgb
    import shap
    
    self._model = lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        min_child_samples=20,
        random_state=42,
    )
    self._model.fit(X, y)
    self._explainer = shap.TreeExplainer(self._model)
    
    # Guardar modelo
    os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
    with open(self._model_path, "wb") as f:
        pickle.dump({"model": self._model, "explainer": self._explainer}, f)
```

### Datos de Entrenamiento

```python
# X: Feature vector (17 features)
# y: Target (0 = SELL, 1 = BUY)

# Target calculation:
# y = 1 if next_candle_return > 0 else 0
```

### Métricas Esperadas

| Métrica | Target |
|---------|--------|
| Accuracy | > 55% |
| F1 Score | > 0.50 |
| Sharpe Ratio | > 1.0 (en backtest) |

---

## Configuración

### Paths de Modelos

```python
# Crypto (Binance)
MODEL_CRYPTO = "data/models/technical_crypto_v1.pkl"

# Forex/MT5
MODEL_FOREX = "data/models/technical_forex_v1.pkl"
```

### Carga

```python
def _load_model(self) -> None:
    if os.path.exists(self._model_path):
        with open(self._model_path, "rb") as f:
            payload = pickle.load(f)
            self._model = payload.get("model")
            self._explainer = payload.get("explainer")
```

---

## Testing

### Tests Unitarios

```bash
pytest tests/unit/test_technical_agent.py -v
```

### Test Manual

```python
from core.agents.technical_agent import TechnicalAgent

agent = TechnicalAgent()

# Verificar si está listo
print(agent.is_ready())  # False si no hay modelo

# Predecir
features = FeatureSet(...)  # Crear features
output = agent.predict(features)

print(f"Direction: {output.direction}")
print(f"Score: {output.score}")
print(f"Confidence: {output.confidence}")
print(f"SHAP: {output.shap_values}")
```

---

*Volver al [índice de modelos ML](README.md)*
