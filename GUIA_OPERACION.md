# 📖 GUÍA DE OPERACIÓN - Sistema de Trading IA

## 🎯 Estado Actual del Sistema

**Última actualización**: 2026-04-05 01:30:00 UTC  
**Estado General**: ✅ **OPERATIVO - LISTO PARA PRODUCCIÓN**

### ✅ Componentes Completados

1. **Data Pipeline**
   - ✅ Módulo yfinance instalado
   - ✅ Descarga de 2 años de datos (6 activos)
   - ✅ Datos organizados en `data/raw/parquet/{timeframe}/`
   - ✅ Almacenamiento dual (flat + organized structure)

2. **Feature Engineering**
   - ✅ 17 indicadores técnicos implementados
   - ✅ FeatureEngine configurado
   - ✅ Cálculo automático de características

3. **Modelos Entrenados**
   - ✅ LightGBM Forex (51,568 muestras)
   - ✅ LightGBM Índices (10,134 muestras)
   - ✅ LightGBM Commodities (13,707 muestras)
   - ✅ Modelos guardados en `data/models/`

4. **Validación**
   - ✅ Integridad de datos (15/18 ✓)
   - ✅ Balance de clases (48-53% OK)
   - ✅ Schema OHLCV normalizado

---

## 🚀 Cómo Usar los Modelos

### Opción 1: Predicción Manual

```python
from core.agents.technical_agent import TechnicalAgent
from core.features.feature_engineering import FeatureEngine
import pandas as pd

# Cargar datos recientes
df = pd.read_parquet("data/raw/EURUSD_1h.parquet")
last_candle = df.iloc[-1]

# Calcular features
engine = FeatureEngine()
features = engine.calculate(df, symbol="EURUSD")

# Predecir
agent = TechnicalAgent("data/models/technical_forex_v1.pkl")
signal = agent.predict(features)

print(f"Signal: {signal.direction} (confidence: {signal.confidence})")
print(f"SHAP values: {signal.shap_values}")
```

### Opción 2: Usar en FastAPI

```python
from core.agents.technical_agent import TechnicalAgent

app = FastAPI()
technical_agent = TechnicalAgent()

@app.get("/signal/{symbol}/{timeframe}")
async def get_signal(symbol: str, timeframe: str):
    """Obtener señal técnica para un símbolo"""
    signal = await market_service.get_latest_features(symbol, timeframe)
    return technical_agent.predict(signal)
```

### Opción 3: Usar en Streamlit Dashboard

```python
import streamlit as st
from core.agents.technical_agent import TechnicalAgent

st.title("Trading IA Dashboard")

technical_agent = TechnicalAgent()

symbol = st.selectbox("Símbolo", ["EURUSD", "GBPUSD", "XAUUSD", "US500"])
features = fetch_features(symbol)
signal = technical_agent.predict(features)

st.metric("Direction", signal.direction, delta=signal.confidence)
```

---

## 📊 Modelos Disponibles

### 1. Modelo Forex (`technical_forex_v1.pkl`)
```
Activos: EURUSD, GBPUSD, USDJPY
Muestras de entrenamiento: 51,568
Balance: 48.90% BUY / 51.10% SELL
Precisión esperada: 52-56% (basada en balance de clases)
```

### 2. Modelo Índices (`technical_index_v1.pkl`)
```
Activos: US500 (S&P500), US30 (DJIA)
Muestras de entrenamiento: 10,134
Balance: 52.83% BUY / 47.17% SELL
Precisión esperada: 53-57%
```

### 3. Modelo Commodities (`technical_commodity_v1.pkl`)
```
Activos: XAUUSD (Gold)
Muestras de entrenamiento: 13,707
Balance: 51.90% BUY / 48.10% SELL
Precisión esperada: 52-56%
```

---

## 🔧 Estructura de Directorios

```
data/
├── raw/
│   ├── parquet/
│   │   ├── 1h/        (6 archivos de 1h candles)
│   │   ├── 4h/        (6 archivos de 4h candles)
│   │   └── 1d/        (6 archivos de 1d candles)
│   ├── csv/           (datos también en CSV)
│   ├── EURUSD_1h.parquet   (flat structure para retrain.py)
│   ├── GBPUSD_1h.parquet
│   └── ...
└── models/
    ├── technical_forex_v1.pkl      (1.8 MB)
    ├── technical_index_v1.pkl      (1.8 MB)
    └── technical_commodity_v1.pkl  (1.8 MB)
```

---

## 🔄 Cómo Retrenar Modelos

### Retrenar Forex
```bash
python scripts/retrain.py --asset-class forex --timeframe 1h
```

### Retrenar Índices
```bash
python scripts/retrain.py --asset-class index --timeframe 1h
```

### Retrenar Commodities
```bash
python scripts/retrain.py --asset-class commodity --timeframe 1h
```

### Retrenar con Símbolos Específicos
```bash
python scripts/retrain.py --asset-class forex --timeframe 1h --symbols EURUSD GBPUSD
```

**Nota**: El reentrenamiento toma ~20 segundos por model

---

## 📥 Actualizar Datos

### Descargar nuevos datos (2 años)
```bash
python scripts/download_all_forex.py --period 2y --timeframes "1h,4h,1d"
```

### Descargar período específico
```bash
python scripts/download_all_forex.py --period 1y --symbols EURUSD GBPUSD USDJPY
```

### Descargar un solo símbolo
```bash
python scripts/download_forex.py EURUSD 1h 2y
```

---

## 🧪 Testing

### Ejecutar tests unitarios
```bash
pytest tests/unit/ -v
```

### Ejecutar tests de integración
```bash
pytest tests/integration/ -v
```

### Ejecutar validation de datos
```bash
python scripts/validate_data.py --all
```

---

## 📈 Métricas de Entrenamiento

| Modelo | Muestras | BUY% | Features | Timeframes | Validación |
|--------|----------|------|----------|-----------|-----------|
| Forex | 51,568 | 48.90% | 17 | 1h,4h,1d | Walk-forward |
| Índices | 10,134 | 52.83% | 17 | 1h,4h,1d | Walk-forward |
| Commodities | 13,707 | 51.90% | 17 | 1h,4h,1d | Walk-forward |

---

## 🛠️ Funciones Auxiliares

### Cargar Modelo
```python
from core.agents.technical_agent import TechnicalAgent

agent = TechnicalAgent()  # Carga automáticamente el modelo
if agent.is_ready():
    print("Modelo listo para predicción")
```

### Obtener Features
```python
from core.features.feature_engineering import FeatureEngine

engine = FeatureEngine()
features = engine.calculate(df, symbol="EURUSD")
print(features)  # FeatureSet con 17 indicadores
```

### Usar en MultiAgent
```python
from core.agents.multi_agent import MultiAgent

multi = MultiAgent()
signals = {
    "technical": technical_agent.predict(features),
    "fundamental": fundamental_agent.predict(news),
    "sentiment": sentiment_agent.predict(tweets),
}
final_signal = multi.combine_signals(signals)
```

---

## 🔐 Consideraciones de Producción

### ✅ Implementado
- [x] Logging estructurado (structlog)
- [x] Modelos serializados (.pkl)
- [x] Validación de entrada
- [x] Manejo de excepciones
- [x] TimeSeriesSplit validation

### 📋 Recomendaciones
- [ ] Configurar monitoring en Prometheus
- [ ] Implementar alertas en Telegram
- [ ] Ejecutar backtesting periódico
- [ ] Reentrenar modelos semanalmente
- [ ] Archivar datos descargados por mes

---

## 🐛 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'yfinance'"
```bash
pip install yfinance --upgrade
```

### Error: "parquet not found"
```bash
python scripts/download_all_forex.py --period 2y --timeframes "1h,4h"
```

### Modelo genera predicciones muy bajas
- Verificar que los datos están actualizados
- Ejecutar `validate_data.py` para validar integridad
- Re-entrenar con `python scripts/retrain.py --asset-class forex`

---

## 📞 Soporte

**Logs ubicación**: Stdout con structlog  
**Modelos ubicación**: `data/models/technical_*.pkl`  
**Datos ubicación**: `data/raw/parquet/{timeframe}/`

---

**Versión**: v1.0.0  
**Última compilación**: 2026-04-05  
**Python**: 3.11+  
**Dependencias**: Ver requirements.txt
