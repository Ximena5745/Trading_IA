# Módulo: Feature Engineering

> Generación y gestión de features técnicos y algorítmicos para ML

---

## 1. OBJETIVO

Proveer un motor de features que calcule indicadores técnicos, genere features para modelos ML, gestione el feature store en Redis y valide la calidad de features.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|-----------------|-------------|
| Cálculo de indicadores | EMA, RSI, MACD, Bollinger, etc. |
| Feature generation | Crear features derivadas |
| Feature store | Cacheo en Redis |
| Feature validation | Validación de calidad |
| Feature importance | Cálculo de importancia |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                      FEATURE LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  FeatureEngineering                       │ │
│  │  - Technical indicators (20+)                            │ │
│  │  - Custom indicators                                      │ │
│  │  - Composite features                                    │ │
│  └──────────────────────┬───────────────────────────────────┘ │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │               FeatureStore                                │  │
│  │  - Redis cache                                           │  │
│  │  - TTL management                                        │  │
│  │  - Invalidation                                          │  │
│  └──────────────────────┼───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │            FeatureValidator                               │  │
│  │  - Null checks                                           │ │
│  │  - Outlier detection                                     │ │
│  │  - Stationarity                                          │ │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 FeatureEngineering

**Archivo:** `core/features/feature_engineering.py`

**Indicadores técnicos soportados:**

| Categoría | Indicadores |
|-----------|-------------|
| Trend | EMA, SMA, WMA, DEMA, TEMA, VWAP, Ichimoku |
| Momentum | RSI, Stochastic, CCI, ROC, Williams %R |
| Volatility | ATR, Bollinger Bands, Keltner, StdDev |
| Volume | OBV, VWMA, ADL, CMF |
| Patterns | Higher High, Higher Low, Head & Shoulders |
| Custom | Hurst Exponent, Regime Features |

**Interfaz:**
```python
class FeatureEngine:
    def calculate_all(
        self,
        df: pd.DataFrame,
        indicators: list[str] | None = None
    ) -> pd.DataFrame: ...
    
    def calculate_single(
        self,
        df: pd.DataFrame,
        indicator: str,
        **params
    ) -> pd.Series: ...
    
    def get_available_indicators(self) -> list[str]: ...
```

### 4.2 FeatureStore

**Archivo:** `core/features/feature_store.py`

**Propósito:** Cacheo de features calculados en Redis para evitar recalculo.

```python
class FeatureStore:
    async def get(
        self,
        symbol: str,
        interval: str,
        features: list[str]
    ) -> pd.DataFrame | None: ...
    
    async def set(
        self,
        symbol: str,
        interval: str,
        df: pd.DataFrame,
        ttl: int = 300
    ) -> None: ...
    
    async def invalidate(
        self,
        symbol: str,
        interval: str
    ) -> None: ...
```

**Configuración TTL:**
| Feature Type | TTL |
|--------------|-----|
| Live (1m) | 60s |
| Intraday (5m, 15m) | 300s |
| Daily+ | 3600s |

### 4.3 FeatureValidator

**Archivo:** `core/features/feature_validator.py`

**Validaciones:**

| Validación | Descripción | Acción en fail |
|------------|-------------|----------------|
| Null check | % de NaN > 10% | Warn + drop |
| Outlier | > 5 std deviations | Clip + warn |
| Stationarity | ADF test p-value | Warn |
| Correlation | Feature correlation > 0.95 | Drop one |

### 4.4 HurstEngine

**Archivo:** `core/features/hurst_engine.py`

**Propósito:** Calcular exponent de Hurst para identificar tendencia vs mean reversion.

```python
class HurstEngine:
    def calculate_hurst(self, prices: pd.Series, lags: int = 20) -> float: ...
    # Returns: 0-0.5 (mean reversion), 0.5 (random), 0.5-1 (trend)
```

---

## 5. EVENTOS

### 5.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `features.calculated` | Features calculadas | `{symbol, interval, feature_count}` |
| `features.invalidated` | Cache invalidado | `{symbol, interval}` |
| `features.quality.alert` | Problema de calidad | `{symbol, issue}` |

### 5.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `market_data.updated` | Trigger recalculo |

---

## 6. INPUTS/OUTPUTS

### 6.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| OHLCV Data | pd.DataFrame | Datos de mercado |
| Indicator config | dict | Parámetros por indicador |
| Symbol | str | Símbolo a procesar |

### 6.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Features | Redis | Features cacheadas |
| Features | pd.DataFrame | Para ML pipeline |
| Quality report | Logs | Validación de calidad |

---

## 7. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Insufficient data | Calcula con disponibles, warn |
| Division by zero | Returns NaN, handled by validator |
| NaN in indicator | Fill forward, then fill backward |
| Unknown indicator | Raise ValueError |
| Redis unavailable | Fallback a cálculo directo |

---

## 8. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Feature drift | Alto | Validation layer |
| Memory explosion | Medio | Limit history |
| Calculation errors | Alto | Try-except + validation |

---

## 9. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Calculation time (100 candles) | < 100ms |
| Cache hit rate | > 80% |
| Memory per symbol | < 10MB |

---

## 10. OBSERVABILIDAD

### 10.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `features.calculation.time` | Histogram | Tiempo de cálculo |
| `features.cache.hit_rate` | Gauge | Hit rate |
| `features.quality.null_pct` | Gauge | % nulls |
| `features.count` | Counter | Features calculadas |

### 10.2 Logs

```json
{
  "event": "features_calculated",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 45,
  "null_pct": 2.1,
  "time_ms": 45
}
```

---

## 11. CONFIGURACIÓN

```python
# Feature config
FEATURES = {
    "trend": {
        "ema": [9, 21, 55, 200],
        "sma": [20, 50, 200],
    },
    "momentum": {
        "rsi": [7, 14, 21],
        "stochastic": [14, 3],
    },
    "volatility": {
        "atr": [14],
        "bbands": [20, 2],
    },
    "volume": {
        "obv": True,
        "cmf": [20],
    }
}
```

---

## 12. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_indicators | Unit | 90% |
| test_feature_store | Unit | 80% |
| test_validation | Unit | 90% |
| test_integration | Integration | 70% |

---

## 13. EJEMPLOS DE USO

```python
# Calcular features
engine = FeatureEngine()
df_features = engine.calculate_all(
    df_ohlcv,
    indicators=["rsi_14", "ema_21", "atr_14", "bbands_20"]
)

# Usar con cache
store = FeatureStore()
cached = await store.get("BTCUSDT", "1h", ["rsi", "ema"])
if not cached:
    cached = engine.calculate(df)
    await store.set("BTCUSDT", "1h", cached)
```

---

## 14. KPIs

| KPI | Target |
|-----|--------|
| Calculation accuracy | 100% |
| Cache hit rate | > 80% |
| Validation coverage | 100% |

---

*Volver al [INDEX](../INDEX.md)*