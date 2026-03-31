# Indicadores Técnicos

> 17 indicadores calculados por FeatureEngine

## Archivo Principal

`core/features/indicators.py` - Calcula todos los indicadores desde OHLCV

---

## Lista de Indicadores

| # | Indicador | Categoría | Período | Descripción |
|---|-----------|-----------|---------|-------------|
| 1 | RSI 14 | Momentum | 14 | Relative Strength Index |
| 2 | RSI 7 | Momentum | 7 | RSI acelerado |
| 3 | EMA 9 | Trend | 9 | Exponential Moving Average |
| 4 | EMA 21 | Trend | 21 | Exponential Moving Average |
| 5 | EMA 50 | Trend | 50 | Exponential Moving Average |
| 6 | EMA 200 | Trend | 200 | Exponential Moving Average |
| 7 | MACD Line | Momentum | 12/26 | MACD principal |
| 8 | MACD Signal | Momentum | 9 | Línea de señal |
| 9 | MACD Histogram | Momentum | - | Diferencia Line - Signal |
| 10 | ATR 14 | Volatility | 14 | Average True Range |
| 11 | BB Upper | Volatility | 20 | Bollinger Band superior |
| 12 | BB Lower | Volatility | 20 | Bollinger Band inferior |
| 13 | BB Width | Volatility | - | Ancho normalizado |
| 14 | VWAP | Volume | 20 | Volume Weighted Avg Price |
| 15 | Volume Ratio | Volume | 20 | Volumen vs media |
| 16 | OBV | Volume | - | On Balance Volume |
| 17 | Trend Direction | Trend | - | Bullish/Bearish/Sideways |
| 18 | Volatility Regime | Volatility | - | Low/Medium/High/Extreme |

---

## Momentum Indicators

### RSI (Relative Strength Index)

```python
def _calc_rsi(df: pd.DataFrame, period: int) -> pd.Series:
    """
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    
    Interpretación:
    - RSI < 30: Sobreventa (posible BUY)
    - RSI > 70: Sobrecompra (posible SELL)
    """
```

**Implementación:**

```python
# Con pandas-ta
df["rsi_14"] = ta.rsi(df["close"], length=14)

# Manual
delta = series.diff()
gain = delta.clip(lower=0).ewm(span=period, adjust=False).mean()
loss = (-delta.clip(upper=0)).ewm(span=period, adjust=False).mean()
rs = gain / loss.replace(0, np.nan)
rsi = 100 - (100 / (1 + rs))
```

**Señales de Trading:**

| Condición | Señal |
|-----------|-------|
| RSI < 30 | Sobreventa - posible reversión alcista |
| RSI > 70 | Sobrecompra - posible reversión bajista |
| RSI cruza 30 hacia arriba | BUY |
| RSI cruza 70 hacia abajo | SELL |

---

### MACD (Moving Average Convergence Divergence)

```python
def _calc_macd(df: pd.DataFrame) -> None:
    """
    MACD Line = EMA(12) - EMA(26)
    Signal Line = EMA(MACD Line, 9)
    Histogram = MACD Line - Signal Line
    """
```

**Implementación:**

```python
ema12 = df["close"].ewm(span=12, adjust=False).mean()
ema26 = df["close"].ewm(span=26, adjust=False).mean()
df["macd_line"] = ema12 - ema26
df["macd_signal"] = df["macd_line"].ewm(span=9, adjust=False).mean()
df["macd_histogram"] = df["macd_line"] - df["macd_signal"]
```

**Señales de Trading:**

| Condición | Señal |
|-----------|-------|
| MACD cruza Signal hacia arriba | BUY |
| MACD cruza Signal hacia abajo | SELL |
| Histogram positivo y creciente | Momentum alcista |
| Histogram negativo y decreciente | Momentum bajista |

---

## Trend Indicators

### EMA (Exponential Moving Average)

```python
def _calc_ema(df: pd.DataFrame) -> None:
    """
    EMA = α × Price + (1-α) × EMA_prev
    α = 2 / (period + 1)
    """
```

**Implementación:**

```python
for period in (9, 21, 50, 200):
    df[f"ema_{period}"] = df["close"].ewm(
        span=period, adjust=False
    ).mean()
```

**Señales de Trading:**

| Condición | Señal |
|-----------|-------|
| EMA 9 > EMA 21 | Tendencia alcista corto plazo |
| EMA 50 > EMA 200 | Tendencia alcista largo plazo (Golden Cross) |
| EMA 50 < EMA 200 | Tendencia bajista largo plazo (Death Cross) |
| Precio > EMA 50 | Confirmación alcista |
| Precio < EMA 50 | Confirmación bajista |

**Cruces Clásicos:**

```
Golden Cross: EMA 50 cruza EMA 200 hacia arriba → BUY fuerte
Death Cross: EMA 50 cruza EMA 200 hacia abajo → SELL fuerte
```

---

### Trend Direction

```python
def _calc_trend_direction(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica tendencia basado en EMAs:
    
    Bullish: EMA50 > EMA200 AND close > EMA50
    Bearish: EMA50 < EMA200 AND close < EMA50
    Sideways: Otro caso
    """
```

**Implementación:**

```python
def trend(row: pd.Series) -> str:
    if row["ema_50"] > row["ema_200"] and row["close"] > row["ema_50"]:
        return "bullish"
    if row["ema_50"] < row["ema_200"] and row["close"] < row["ema_50"]:
        return "bearish"
    return "sideways"

df["trend_direction"] = df.apply(trend, axis=1)
```

---

## Volatility Indicators

### ATR (Average True Range)

```python
def _calc_atr(df: pd.DataFrame) -> None:
    """
    TR = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
    ATR = EMA(TR, 14)
    
    Usado para:
    - Stop Loss: entry - ATR × multiplier
    - Take Profit: entry + ATR × multiplier
    - Position sizing
    """
```

**Implementación:**

```python
hl = df["high"] - df["low"]
hc = (df["high"] - df["close"].shift(1)).abs()
lc = (df["low"] - df["close"].shift(1)).abs()
tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
df["atr_14"] = tr.ewm(span=14, adjust=False).mean()
```

**Uso en SL/TP:**

```python
# Configuración del sistema
ATR_STOP_LOSS_MULTIPLIER = 2.0
ATR_TAKE_PROFIT_MULTIPLIER = 3.0

# Cálculo
stop_loss = entry_price - (ATR × 2.0)  # Para BUY
take_profit = entry_price + (ATR × 3.0)  # Para BUY

# Ejemplo:
# Entry: $50,000
# ATR: $1,000
# SL: $50,000 - $2,000 = $48,000
# TP: $50,000 + $3,000 = $53,000
# R:R = 3:2 = 1.5
```

---

### Bollinger Bands

```python
def _calc_bollinger(df: pd.DataFrame) -> None:
    """
    Middle Band = SMA(20)
    Upper Band = SMA(20) + 2 × STD(20)
    Lower Band = SMA(20) - 2 × STD(20)
    Width = (Upper - Lower) / Close
    """
```

**Implementación:**

```python
sma20 = df["close"].rolling(20).mean()
std20 = df["close"].rolling(20).std()
df["bb_upper"] = sma20 + 2 * std20
df["bb_lower"] = sma20 - 2 * std20
df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["close"]
```

**Señales de Trading:**

| Condición | Señal |
|-----------|-------|
| Precio toca BB Lower | Posible reversión alcista (BUY) |
| Precio toca BB Upper | Posible reversión bajista (SELL) |
| BB Width bajo | Baja volatilidad - posible explosión |
| BB Width alto | Alta volatilidad - posible consolidación |

---

### Volatility Regime

```python
def _calc_volatility_regime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clasifica volatilidad basado en ATR percentil:
    
    - ATR ≤ P25: low
    - ATR ≤ P75: medium
    - ATR ≤ P90: high
    - ATR > P90: extreme
    """
```

**Implementación:**

```python
atr_pct = df["atr_14"] / df["close"]
q25 = atr_pct.quantile(0.25)
q75 = atr_pct.quantile(0.75)
q90 = atr_pct.quantile(0.90)

def regime(v: float) -> str:
    if v <= q25: return "low"
    if v <= q75: return "medium"
    if v <= q90: return "high"
    return "extreme"
```

**Uso:**

```python
# Estrategias pueden filtrar por régimen:
if features.volatility_regime == "extreme":
    return None  # No operar en volatilidad extrema
```

---

## Volume Indicators

### VWAP (Volume Weighted Average Price)

```python
def _calc_volume_indicators(df: pd.DataFrame) -> None:
    """
    VWAP = Σ(Price × Volume) / Σ(Volume)
    
    Rolling approximation (20 periods)
    """
```

**Implementación:**

```python
df["vwap"] = (df["close"] * df["volume"]).rolling(20).sum() / \
             df["volume"].rolling(20).sum()
```

**Señales de Trading:**

| Condición | Señal |
|-----------|-------|
| Precio > VWAP | Alcista intradía |
| Precio < VWAP | Bajista intradía |
| Precio cruza VWAP arriba | BUY |
| Precio cruza VWAP abajo | SELL |

---

### Volume Ratio

```python
def _calc_volume_indicators(df: pd.DataFrame) -> None:
    """
    Volume Ratio = Current Volume / SMA(Volume, 20)
    
    Interpretación:
    - > 1.0: Volumen por encima del promedio
    - > 1.5: Volumen significativamente alto
    - < 1.0: Volumen por debajo del promedio
    """
```

**Implementación:**

```python
df["volume_sma_20"] = df["volume"].rolling(20).mean()
df["volume_ratio"] = df["volume"] / df["volume_sma_20"].replace(0, np.nan)
```

---

### OBV (On Balance Volume)

```python
def _calc_volume_indicators(df: pd.DataFrame) -> None:
    """
    Si Close > Prev Close: OBV = Prev OBV + Volume
    Si Close < Prev Close: OBV = Prev OBV - Volume
    Si Close = Prev Close: OBV = Prev OBV
    """
```

**Implementación:**

```python
obv = [0.0]
for i in range(1, len(df)):
    if df["close"].iloc[i] > df["close"].iloc[i - 1]:
        obv.append(obv[-1] + df["volume"].iloc[i])
    elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
        obv.append(obv[-1] - df["volume"].iloc[i])
    else:
        obv.append(obv[-1])
df["obv"] = obv
```

---

## Validación de NaN

```python
def _validate_nan(df: pd.DataFrame) -> None:
    """
    Valida que los indicadores críticos no tengan太多 NaN.
    
    Indicadores críticos:
    - rsi_14
    - ema_50
    - ema_200
    - atr_14
    - macd_line
    
    Máximo 5% NaN en últimos 100 candles.
    """
```

---

## Configuración

### Constantes

```python
MIN_CANDLES = 200    # Mínimo de velas para calcular indicadores
MAX_NAN_PCT = 0.05   # Máximo 5% NaN permitido
```

### Validación

```python
if len(df) < MIN_CANDLES:
    raise FeatureCalculationError(
        f"Need at least {MIN_CANDLES} candles, got {len(df)}"
    )
```

---

## Testing

### Tests Unitarios

```bash
# Tests de indicadores
pytest tests/unit/test_indicators.py -v

# Tests de feature engineering
pytest tests/unit/test_feature_engine.py -v
```

---

*Volver al [índice de estrategias e indicadores](README.md)*
