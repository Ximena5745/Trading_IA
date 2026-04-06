# ⚡ PLAN DE EJECUCIÓN INMEDIATA

## Estado Actual

✅ **Código Base**: 95% completo (API, Agentes, Dashboard, todos los scripts)  
⚠️ **Datos**: 10% - Existen datos 1mo/1wk pero se necesitan datos 1h/4h  
❌ **Modelos**: 0% - No hay modelos .pkl entrenados  

---

## ¿Qué Hacer Ahora?

### PASO 1: Descargar Datos de 2 Años (Timeframes 1h, 4h)

**Ejecutar un solo comando:**

```bash
python scripts/download_all_forex.py --period 2y --timeframes "1h,4h,1d"
```

**¿Qué hace?**
- Descarga 2 años de datos históricos desde yfinance (GRATIS)
- 6 símbolos: EURUSD, GBPUSD, USDJPY, XAUUSD, US500, US30
- Timeframes: 1h (intraday), 4h (corto plazo), 1d (referencia)
- Crea archivos: `data/raw/EURUSD_1h.parquet`, `data/raw/GBPUSD_1h.parquet`, etc.
- **Tiempo estimado:** 15-20 minutos

**Salida esperada:**
```
Descargando EURUSD (EURUSD=X) en 1h...
  Descargadas 10000+ filas
  [OK] Guardado en data/raw/parquet/1h/eurusd_1h.parquet, data/raw/EURUSD_1h.parquet
```

---

### PASO 2: Validar Datos Descargados

**Ejecutar:**

```bash
python scripts/validate_data.py
```

**¿Qué hace?**
- Verifica integridad de archivos
- Chequea que no hay gaps en datos
- Suma de registros por símbolo
- Reporta cualquier error

---

### PASO 3: Entrenar Modelos LightGBM

**Opción A: Entrenar solo Forex (rápido, ~10 min)**

```bash
python scripts/retrain.py --asset-class forex --timeframe 1h--symbols EURUSD GBPUSD USDJPY
```

**Opción B: Entrenar TODO (completo, ~30 min)**

```bash
# Forex
python scripts/retrain.py --asset-class forex --timeframe 1h --symbols EURUSD GBPUSD USDJPY

# Commodities
python scripts/retrain.py --asset-class commodity --timeframe 1h --symbols XAUUSD

# Índices
python scripts/retrain.py --asset-class index --timeframe 1h --symbols US500 US30
```

**¿Qué hace?**
- Carga datos desde `data/raw/EURUSD_1h.parquet`, etc.
- Calcula 17 indicadores técnicos
- Entrena LightGBM con validación walk-forward (5 folds)
- Crea SHAP explainers
- Guarda modelos en `data/models/technical_forex_v1.pkl`, etc.

**Salida esperada:**
```
🤖 TRADER AI — Retraining TechnicalAgent
   Asset class : forex
   Timeframe   : 1h
   Symbols     : ['EURUSD', 'GBPUSD', 'USDJPY']
   Model output: data/models/technical_forex_v1.pkl

✅ Model trained successfully
   Accuracy: 54.2% | F1: 0.538 | Precision: 0.542
```

---

### PASO 4 (Opcional): Ejecutar Todo de Una Vez

**Si quieres automatizar los 3 pasos:**

```bash
python run_training_pipeline.py
```

Esto:
1. Descarga datos (15-20 min)
2. Valida datos (1 min)
3. Entrena todos los modelos (30 min)
4. **Total: ~45 minutos** → Tendrás el sistema completo funcionando

---

## Después de Esto...

Una vez completado, tendrás:

### 📁 Archivos Creados

```
data/
├── raw/
│   ├── EURUSD_1h.parquet      ✓ 10,000+ registros
│   ├── GBPUSD_1h.parquet      ✓
│   ├── USDJPY_1h.parquet      ✓
│   ├── XAUUSD_1h.parquet      ✓
│   ├── US500_1h.parquet       ✓
│   ├── US30_1h.parquet        ✓
│   └── parquet/               (datos organizados)
│
├── processed/
│   └── (features calculados)
│
└── models/
    ├── technical_forex_v1.pkl      ✓ Modelo Forex
    ├── technical_commodity_v1.pkl  ✓ Modelo Commodities
    └── technical_index_v1.pkl      ✓ Modelo Índices
```

### 🤖 Modelos Listos

- ✅ TechnicalAgent carga modelos automáticamente
- ✅ Predicciones con score -1 a +1
- ✅ SHAP values para explicabilidad

### 📊 Sistema Funcionando

- ✅ API devuelve señales con modelos reales
- ✅ Dashboard muestra datos actuales
- ✅ Listo para FASE 4 (Pipeline automático)
- ✅ Listo para FASE 5 (Paper trading)

---

## ⏱️ Timeline

```
Ahora (Hoy)
↓
[PASO 1] Descargar datos      (15-20 min)
↓
[PASO 2] Validar datos        (1-2 min)
↓
[PASO 3] Entrenar modelos     (30-45 min)
↓
✅ Sistema Completo Operativo (Total: ~50-70 minutos)
```

---

## 🆘 Si Algo Falla

### "yfinance.download timed out" o "Rate limit exceeded"

**Solución:** Esperar 5 minutos y reintentar. yfinance tiene límites de velocidad.

```bash
# Esperar y reintentar
python scripts/download_all_forex.py --period 2y --timeframes "1h,4h,1d"
```

### "Insufficient data for training"

**Motivo:** Los datos descargados no tienen suficientes registros (menos de 100)  
**Solución:** Verificar que download_all_forex.py completó exitosamente

```bash
# Ver cantidad de registros
python -c "
import pandas as pd
df = pd.read_parquet('data/raw/EURUSD_1h.parquet')
print(f'EURUSD_1h: {len(df)} registros')
"
```

### "Model accuracy < 52%"

**Es normal** - Los modelos iniciales no son perfectos. Se optimizan en FASE 6 (2 semanas después).

---

## ✅ Checklist

- [ ] He ejecutado `python scripts/download_all_forex.py --period 2y --timeframes "1h,4h,1d"`
- [ ] He ejecutado `python scripts/validate_data.py`
- [ ] He ejecutado `python scripts/retrain.py --asset-class forex --timeframe 1h`
- [ ] Archivos `.parquet` existen en `data/raw/`
- [ ] Modelos `.pkl` existen en `data/models/`
- [ ] Dashboard funciona: `streamlit run app/dashboard.py`

---

## ¿Preguntas?

Ver documentación:
- `ANALISIS_ESTADO.md` — Estado completo del proyecto
- `PLAN_TRABAJO_PROPUESTO.md` — Plan de 14 semanas
- `scripts/download_all_forex.py` — Cómo funciona la descarga
- `scripts/retrain.py` — Cómo funciona el entrenamiento
