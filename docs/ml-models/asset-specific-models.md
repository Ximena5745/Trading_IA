# Modelos Específicos por Activo

## Resumen

Este módulo implementa la **arquitectura multi-modelo específica por activo** según las propuestas de mejora. Cada clase de activo (CRYPTO, FOREX, INDICES, COMMODITIES) tiene modelos especializados optimizados para sus características únicas.

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    AssetSpecificAgent                       │
│                    (Orquestador Principal)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
        ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   Modelo 1   │ │   Modelo 2   │ │   Modelo N   │
│  (Trend)     │ │(Mean Revert) │ │(Volatility)  │
└──────┬───────┘ └──────┬───────┘ └──────┬───────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
                        ▼
              ┌──────────────────┐
              │   Meta-Modelo    │
              │    (Stacking)    │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Filtros Decisión │
              │  - Umbral        │
              │  - Retorno       │
              │  - Riesgo        │
              └────────┬─────────┘
                       │
                       ▼
              ┌──────────────────┐
              │ Señal Final      │
              └──────────────────┘
```

## Configuración por Tipo de Activo

### 🟡 CRYPTO (BTC, ETH)

**Características:**
- Alta volatilidad
- Momentum fuerte
- Ciclos de mercado pronunciados

**Modelos Configurados:**
| Modelo | Estrategia | Peso | Descripción |
|--------|-----------|------|-------------|
| LightGBM | Momentum | 35% | Optimizado para momentum crypto |
| LSTM | Trend Following | 30% | Captura tendencias largo plazo |
| Temporal Fusion Transformer | Volatility Breakout | 25% | Modelo avanzado temporal |
| CatBoost | Mean Reversion | 10% | Para rangos laterales |

**Features Específicas:**
- Indicadores técnicos: RSI múltiples períodos, EMAs, MACD, Bollinger Bands
- Features de tiempo: Hora, día de semana
- Market structure: Higher highs/lower lows, break of structure
- Microestructura: Order book imbalance, volume delta
- Crypto-specific: BTC dominance, funding rate, open interest

**Umbrales:**
- Signal threshold: 0.65
- Min expected return: 0.5%
- Max risk per trade: 2%

---

### 🔵 FOREX (EURUSD, GBPUSD, USDJPY)

**Características:**
- Mean reversion + tendencias
- Sesiones temporales críticas
- Volatilidad por sesión

**Modelos Configurados:**
| Modelo | Estrategia | Peso | Descripción |
|--------|-----------|------|-------------|
| LightGBM | Mean Reversion | 40% | Con features temporales |
| HMM | Range Trading | 25% | Detección de regímenes |
| Logistic Regression | Trend Following | 20% | Baseline robusto |
| SVM | Momentum | 15% | Para momentum en FX |

**Features Específicas:**
- Features temporales: Hora, sesiones (London, NY, Asian), overlaps
- Eventos macro: NFP day, FOMC week
- Pivot points, support/resistance
- DXY index, VIX como features macro

**Umbrales:**
- Signal threshold: 0.60
- Min expected return: 0.03%
- Max risk per trade: 2%

---

### 🟠 INDICES (US500, US30)

**Características:**
- Tendencias limpias
- Momentum sostenido
- Influencia macro

**Modelos Configurados:**
| Modelo | Estrategia | Peso | Descripción |
|--------|-----------|------|-------------|
| LightGBM | Trend Following | 35% | Para seguimiento de tendencia |
| XGBoost | Momentum | 30% | Baseline fuerte |
| Random Forest | Mean Reversion | 20% | Robustez |
| Reinforcement Learning | Trend Following | 15% | Fase avanzada |

**Features Específicas:**
- ADX, DI+/- para fuerza de tendencia
- EMA crosses (golden/death cross)
- VIX level y regime
- Gap analysis
- Advance-decline line

**Umbrales:**
- Signal threshold: 0.60
- Min expected return: 0.1%
- Max risk per trade: 2%

---

### 🟤 COMMODITIES (GOLD/XAUUSD)

**Características:**
- Macro-driven
- Safe haven
- Volatilidad por eventos geopolíticos

**Modelos Configurados:**
| Modelo | Estrategia | Peso | Descripción |
|--------|-----------|------|-------------|
| LightGBM | Macro Driven | 40% | Con features macro |
| HMM | Volatility Breakout | 30% | Regime switching |
| CatBoost | Mean Reversion | 20% | Para rangos |
| Gaussian Mixture | Range Trading | 10% | Clustering de mercado |

**Features Específicas:**
- Real yield, inflation expectations
- Gold futures OI, ETF flows
- Central bank activity
- Geopolitical risk index
- Gold/silver ratio

**Umbrales:**
- Signal threshold: 0.60
- Min expected return: 0.05%
- Max risk per trade: 2%

---

## Uso

### 1. Entrenar Modelos

```bash
# CRYPTO
python scripts/train_asset_specific_models.py --asset-class crypto --symbol BTCUSD --timeframe 1h

# FOREX
python scripts/train_asset_specific_models.py --asset-class forex --symbol EURUSD --timeframe 1h

# INDICES
python scripts/train_asset_specific_models.py --asset-class indices --symbol US500 --timeframe 1h

# COMMODITIES
python scripts/train_asset_specific_models.py --asset-class commodities --symbol XAUUSD --timeframe 1h
```

### 2. Usar el Agente

```python
from core.agents.asset_specific_agent import create_asset_agent
from core.models import FeatureSet

# Crear agente para un símbolo específico
agent = create_asset_agent(symbol="EURUSD")

# Verificar estado
print(agent.get_model_status())

# Realizar predicción
features = FeatureSet(
    timestamp=datetime.now(),
    symbol="EURUSD",
    rsi_14=45.2,
    ema_9=1.0850,
    # ... otros features
)

prediction = agent.predict(features)
print(f"Direction: {prediction.direction}")
print(f"Score: {prediction.score}")
print(f"Confidence: {prediction.confidence}")
```

### 3. Configuración Personalizada

```python
from core.models.asset_specific_models import (
    AssetModelConfig,
    ModelSpec,
    ModelType,
    StrategyType,
    TargetType,
)

# Crear configuración personalizada
custom_config = AssetModelConfig(
    asset_class=AssetClass.FOREX,
    feature_config=FOREX_FEATURES,
    models=[
        ModelSpec(
            model_type=ModelType.LIGHTGBM,
            strategy_type=StrategyType.MEAN_REVERSION,
            target_type=TargetType.TERNARY,
            hyperparams={"n_estimators": 500, "learning_rate": 0.05},
            weight=0.5,
        ),
        # ... más modelos
    ],
    signal_threshold=0.65,
    min_expected_return=0.0005,
)
```

---

## Estructura de Archivos

```
core/
├── models/
│   ├── __init__.py
│   └── asset_specific_models.py    # Configuraciones y modelos Pydantic
├── agents/
│   ├── base_agent.py
│   ├── technical_agent.py
│   ├── regime_agent.py
│   └── asset_specific_agent.py     # Agente multi-modelo por activo
scripts/
└── train_asset_specific_models.py  # Script de entrenamiento
data/
└── models/
    └── asset_specific/
        ├── crypto_momentum_lightgbm.pkl
        ├── crypto_trend_following_lstm.pkl
        ├── crypto_volatility_breakout_tft.pkl
        ├── crypto_mean_reversion_catboost.pkl
        ├── crypto_meta_model.pkl
        ├── forex_mean_reversion_lightgbm.pkl
        ├── forex_range_trading_hmm.pkl
        └── ...
```

---

## Impacto Esperado

Según las propuestas de mejora:

| Mejora | Impacto Esperado |
|--------|-----------------|
| Nuevo target (ternario) | +5-10% |
| Regime switching (HMM) | +10-20% |
| Feature engineering avanzado | +5-15% |
| Ensemble (stacking) | +5-10% |
| **Total Esperado** | **+15% a +35%** |

---

## Próximos Pasos

1. **Entrenar modelos base** para cada clase de activo
2. **Validar con backtesting** en datos históricos
3. **Ajustar pesos** del ensemble basado en performance
4. **Implementar RL** para índices (fase avanzada)
5. **Agregar TFT** para crypto (requiere implementación)

---

## Referencias

- `Propuestas_mejora_modelos.md` - Documento original de propuestas
- `core/models/asset_specific_models.py` - Configuraciones
- `core/agents/asset_specific_agent.py` - Implementación del agente
- `scripts/train_asset_specific_models.py` - Pipeline de entrenamiento
