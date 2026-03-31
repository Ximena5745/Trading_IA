# Modelos de Machine Learning

> Documentación de modelos ML utilizados en el sistema

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [technical-agent.md](technical-agent.md) | Modelo LightGBM del TechnicalAgent |

---

## Resumen de Modelos

### TechnicalAgent

| Propiedad | Valor |
|-----------|-------|
| Modelo | LightGBM Classifier |
| Features | 17 indicadores técnicos |
| Target | Signo del retorno siguiente vela |
| Output | Score -1.0 a +1.0 |
| Explicabilidad | SHAP TreeExplainer |
| Path | `data/models/technical_agent_v1.pkl` |

### RegimeAgent

| Propiedad | Valor |
|-----------|-------|
| Modelo | Rule-based (fallback) |
| Clases | 5 regímenes de mercado |
| Output | Regime + confidence |

### MicrostructureAgent

| Propiedad | Valor |
|-----------|-------|
| Modelo | Rule-based |
| Features | Order book imbalance, spread |
| Output | Score microestructura |

### FundamentalAgent

| Propiedad | Valor |
|-----------|-------|
| Modelo | Data fetching + event detection |
| Fuentes | ForexFactory, CoinGecko |
| Output | Event blocking, sentiment |

---

## Entrenamiento

### Script de Reentrenamiento

```bash
# Entrenar para Crypto
python scripts/retrain.py --symbol BTCUSDT --timeframe 1h

# Entrenar para Forex
python scripts/retrain.py --symbol EURUSD --timeframe 1h
```

### Datos de Entrenamiento

```
data/
├── raw/
│   ├── BTCUSDT_1h.parquet
│   ├── ETHUSDT_1h.parquet
│   ├── EURUSD_1h.parquet
│   └── ...
└── models/
    ├── technical_crypto_v1.pkl
    └── technical_forex_v1.pkl
```

---

*Volver al [índice principal](../README.md)*
