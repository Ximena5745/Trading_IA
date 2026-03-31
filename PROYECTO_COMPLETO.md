# TRADER IA - Documentación Completa del Proyecto

> Sistema de Trading Algorítmico Multi-activo con IA Explicable
> 
> **Versión:** 2.0.0 | **Fecha:** Marzo 2026 | **Estado:** En desarrollo activo

---

## Tabla de Contenidos

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Arquitectura del Sistema](#arquitectura-del-sistema)
3. [Sistema Multi-Agente IA](#sistema-multi-agente-ia)
4. [Indicadores Técnicos](#indicadores-técnicos)
5. [Estrategias de Trading](#estrategias-de-trading)
6. [Gestión de Riesgo](#gestión-de-riesgo)
7. [Gestión de Portafolio](#gestión-de-portafolio)
8. [Motor de Ejecución](#motor-de-ejecución)
9. [Pipeline de Datos](#pipeline-de-datos)
10. [API REST](#api-rest)
11. [Dashboard](#dashboard)
12. [Infraestructura](#infraestructura)
13. [Configuración](#configuración)
14. [Estado Actual](#estado-actual)

---

## Resumen Ejecutivo

### ¿Qué es TRADER IA?

Plataforma de trading algorítmico que **genera señales de compra/venta** usando un sistema multi-agente de IA, valida cada señal contra reglas de riesgo estrictas y ejecuta órdenes automáticamente. Opera en **modo papel por defecto** — sin tocar dinero real hasta activación explícita.

### Características Principales

| Característica | Descripción |
|----------------|-------------|
| **Multi-activo** | Crypto, Forex, Índices, Commodities (12 símbolos) |
| **Multi-agente** | 4 agentes IA con votación ponderada |
| **Explainable AI** | Explicaciones SHAP para cada decisión |
| **Risk Management** | Kill switch, drawdown limits, position sizing Kelly |
| **Paper Trading** | Modo simulado con slippage y comisiones reales |
| **Backtesting** | Walk-forward con costos reales |

### Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| Frontend | Streamlit + Plotly |
| Backend | FastAPI + Pydantic |
| ML | LightGBM + SHAP |
| Database | TimescaleDB + Redis |
| Monitoring | Prometheus + Grafana |
| Infrastructure | Docker + Nginx |
| Data Sources | Binance API + MT5 (IC Markets) |

---

## Arquitectura del Sistema

### Vista General

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      TRADER AI - SYSTEM ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      PRESENTATION LAYER                             │   │
│  │     Streamlit Dashboard (:8501)    Grafana Monitoring (:3000)       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       API LAYER (FastAPI :8000)                     │   │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐           │   │
│  │  │Auth  │ │Market│ │Signal│ │Exec  │ │Risk  │ │Portf │           │   │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       CORE ENGINE                                   │   │
│  │                                                                      │   │
│  │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐              │   │
│  │   │Technical│  │ Regime  │  │Microstr │  │Fundamen │              │   │
│  │   │  45%    │  │  35%    │  │  20%    │  │ Filter  │              │   │
│  │   └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘              │   │
│  │        └─────────────┼─────────────┼────────────┘                  │   │
│  │                      ▼             ▼                               │   │
│  │            ┌────────────────────────────┐                          │   │
│  │            │    CONSENSUS ENGINE        │                          │   │
│  │            └────────────┬───────────────┘                          │   │
│  │                         ▼                                           │   │
│  │            ┌────────────────────────────┐                          │   │
│  │            │    SIGNAL ENGINE           │                          │   │
│  │            └────────────┬───────────────┘                          │   │
│  │                         ▼                                           │   │
│  │            ┌────────────────────────────┐                          │   │
│  │            │    RISK MANAGER            │                          │   │
│  │            └────────────┬───────────────┘                          │   │
│  │                         ▼                                           │   │
│  │            ┌────────────────────────────┐                          │   │
│  │            │    EXECUTOR                │                          │   │
│  │            └────────────┬───────────────┘                          │   │
│  │                         ▼                                           │   │
│  │            ┌────────────────────────────┐                          │   │
│  │            │  PORTFOLIO MANAGER         │                          │   │
│  │            └────────────────────────────┘                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       DATA LAYER                                    │   │
│  │    PostgreSQL/TimescaleDB (:5432)    Redis (:6379)                  │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   EXTERNAL SERVICES                                 │   │
│  │    Binance (Crypto)    MT5/IC Markets (Forex)    Telegram (Alerts) │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Módulos del Sistema

| Módulo | Ubicación | Responsabilidad |
|--------|-----------|-----------------|
| **Agents** | `core/agents/` | 4 agentes IA independientes |
| **Consensus** | `core/consensus/` | Votación ponderada entre agentes |
| **Signals** | `core/signals/` | Generación de señales + XAI |
| **Risk** | `core/risk/` | Validación de riesgo + Kill Switch |
| **Execution** | `core/execution/` | Ejecución Paper/Live |
| **Portfolio** | `core/portfolio/` | Gestión de capital |
| **Features** | `core/features/` | Indicadores técnicos |
| **Ingestion** | `core/ingestion/` | Clientes de exchange |
| **Strategies** | `core/strategies/` | Framework de estrategias |
| **Backtesting** | `core/backtesting/` | Motor walk-forward |
| **API** | `api/` | REST API FastAPI |
| **Dashboard** | `app/` | Streamlit UI |

---

## Sistema Multi-Agente IA

### Arquitectura

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
│                        └───────────┬───────────┘                           │
│                                    │                                        │
│  ┌───────────────────┐            │                                        │
│  │ FUNDAMENTAL AGENT │◄───────────┘                                        │
│  │                   │  (Filtro - sin peso)                                │
│  │  • Fear & Greed   │                                                     │
│  │  • Sentimiento    │                                                     │
│  │  • Eventos macro  │                                                     │
│  └───────────────────┘                                                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Agentes Detallados

#### 1. TechnicalAgent (45-55%)

| Propiedad | Valor |
|-----------|-------|
| **Modelo** | LightGBM Classifier |
| **Features** | 17 indicadores técnicos |
| **Target** | Signo del retorno siguiente vela |
| **Output** | Score -1.0 a +1.0 |
| **Explicabilidad** | SHAP TreeExplainer |
| **Fallback** | Rule-based scoring |
| **Archivo** | `core/agents/technical_agent.py` |

**Features utilizadas:**
```
RSI(7,14), MACD(line,signal,histogram), EMA(9,21,50,200), 
ATR(14), Bollinger(upper,lower,width), VWAP, Volume(ratio,sma), OBV
```

#### 2. RegimeAgent (35-45%)

| Propiedad | Valor |
|-----------|-------|
| **Modelo** | Rule-based + clasificación |
| **Regímenes** | 5 estados de mercado |
| **Gate** | Bloquea en VOLATILE_CRASH |
| **Archivo** | `core/agents/regime_agent.py` |

**Regímenes:**
```
BULL_TRENDING    → Score ≥ 0.5   → Señales permitidas
BEAR_TRENDING    → Score ≤ -0.5  → Señales permitidas
SIDEWAYS_LOW_VOL → -0.5 a 0.5    → Señales permitidas
SIDEWAYS_HIGH_VOL → -0.5 a 0.5   → Señales permitidas
VOLATILE_CRASH   → score ≤ -0.9  → SEÑALES BLOQUEADAS
```

#### 3. MicrostructureAgent (0-20%)

| Propiedad | Valor |
|-----------|-------|
| **Modelo** | Análisis de order book |
| **Features** | Bid-ask spread, imbalance |
| **Disponible** | Solo Crypto (Binance L2) |
| **Peso en MT5** | 0% (no hay datos L2) |
| **Archivo** | `core/agents/microstructure_agent.py` |

#### 4. FundamentalAgent (Filtro)

| Propiedad | Valor |
|-----------|-------|
| **Fuentes** | ForexFactory, CoinGecko |
| **Función** | Bloqueo durante eventos macro |
| **Actualización** | Cada 30 minutos |
| **Archivo** | `core/agents/fundamental_agent.py` |

**Eventos bloqueados:**
```
NFP (US)     → ±30 minutos
FOMC         → ±60 minutos
ECB Rate     → ±30 minutos
CPI          → ±30 minutos
GDP          → ±30 minutos
```

### Pesos por Clase de Activo

| Agente | Crypto | Forex/Índices/Commodities |
|--------|--------|---------------------------|
| Technical | 45% | 55% |
| Regime | 35% | 45% |
| Microstructure | 20% | 0% |
| Fundamental | Filtro | Filtro |

---

## Indicadores Técnicos

### Tabla Resumen

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

### Señales por Indicador

| Indicador | Señal BUY | Señal SELL |
|-----------|-----------|------------|
| RSI | < 30 (sobreventa) | > 70 (sobrecompra) |
| MACD | Cruza Signal arriba | Cruza Signal abajo |
| EMA | EMA9 > EMA21 + EMA50 > EMA200 | EMA9 < EMA21 + EMA50 < EMA200 |
| Bollinger | Precio toca BB Lower | Precio toca BB Upper |
| ATR | - | - (usado para SL/TP) |
| Volume Ratio | > 1.5 (confirmación) | > 1.5 (confirmación) |

### Fórmulas Clave

**RSI:**
```python
RSI = 100 - (100 / (1 + RS))
RS = Average Gain / Average Loss
```

**MACD:**
```python
MACD Line = EMA(12) - EMA(26)
Signal = EMA(MACD Line, 9)
Histogram = MACD Line - Signal
```

**Bollinger Bands:**
```python
Upper = SMA(20) + 2 × STD(20)
Lower = SMA(20) - 2 × STD(20)
Width = (Upper - Lower) / Close
```

**ATR (usado para SL/TP):**
```python
SL = Entry - ATR × 2.0
TP = Entry + ATR × 3.0
R:R = 1.5
```

---

## Estrategias de Trading

### 1. EMA Crossover + RSI

| Propiedad | Valor |
|-----------|-------|
| **ID** | `ema_rsi_v1` |
| **Tipo** | Trend Following |
| **Timeframe** | 1h |
| **Símbolos** | BTC, ETH, EUR, GBP, JPY, SPX, NAS, XAU, OIL |

**Condiciones de Entrada:**

```
BUY:
  - EMA9 > EMA21
  - EMA50 > EMA200
  - RSI14 entre 30 y 65
  - MACD Histogram > 0
  - Volume Ratio > 1.2
  - Volatility Regime != extreme

SELL:
  - EMA9 < EMA21
  - EMA50 < EMA200
  - RSI14 entre 35 y 70
  - MACD Histogram < 0
  - Volume Ratio > 1.2
  - Volatility Regime != extreme
```

**Condiciones de Salida:**
```
BUY exit: RSI14 > 70 OR EMA9 < EMA21
SELL exit: RSI14 < 30 OR EMA9 > EMA21
```

**Parámetros:**
```python
rsi_oversold = 30.0
rsi_overbought = 70.0
min_volume_ratio = 1.2
max_capital_pct = 0.20
risk_per_trade_pct = 0.01
```

### 2. Bollinger Bands Mean Reversion

| Propiedad | Valor |
|-----------|-------|
| **ID** | `mean_reversion_v1` |
| **Tipo** | Mean Reversion |
| **Timeframe** | 1h |
| **Símbolos** | BTC, ETH, XAU, XAG, OIL, EUR, GBP, CHF |

**Condiciones de Entrada:**

```
BUY:
  - Close < BB Lower
  - RSI14 < 28
  - Volume Ratio > 1.0

SELL:
  - Close > BB Upper
  - RSI14 > 72
  - Volume Ratio > 1.0
```

**Condiciones de Salida:**
```
BUY exit: Close >= Midband OR RSI14 > 55
SELL exit: Close <= Midband OR RSI14 < 45
Target: VWAP (reversión a la media)
```

### 3. Strategy Builder (Custom)

Framework para crear estrategias dinámicas desde JSON sin código:

```python
config = {
    "id": "my_strategy_v1",
    "name": "My Custom Strategy",
    "entry_conditions": [
        {"feature": "rsi_14", "operator": "lt", "value": 30},
        {"feature": "macd_histogram", "operator": "gt", "value": 0}
    ],
    "exit_conditions": [
        {"feature": "rsi_14", "operator": "gt", "value": 70}
    ],
    "default_action": "BUY"
}
```

**Operadores soportados:** `lt`, `gt`, `lte`, `gte`, `eq`

---

## Gestión de Riesgo

### Flujo de Validación

```
Signal Received
     │
     ▼
┌─────────────────────────────────┐
│ 1. Kill Switch Active?          │──YES──► REJECT
└────────────────┬────────────────┘
                 │ NO
                 ▼
┌─────────────────────────────────┐
│ 2. Risk Exposure > 15%?         │──YES──► REJECT
└────────────────┬────────────────┘
                 │ NO
                 ▼
┌─────────────────────────────────┐
│ 3. Drawdown > 20%?              │──YES──► KILL SWITCH + REJECT
└────────────────┬────────────────┘
                 │ NO
                 ▼
┌─────────────────────────────────┐
│ 4. R:R Ratio < 1.5?             │──YES──► REJECT
└────────────────┬────────────────┘
                 │ NO
                 ▼
┌─────────────────────────────────┐
│ 5. Consecutive Losses > 7?      │──YES──► KILL SWITCH + REJECT
└────────────────┬────────────────┘
                 │ NO
                 ▼
           ✅ APPROVED → Execute
```

### Hard Limits

```python
HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,        # 2% por trade
    "max_portfolio_risk_pct": 0.15,         # 15% exposición total
    "max_daily_loss_pct": 0.10,             # 10% pérdida diaria
    "max_drawdown_pct": 0.20,               # 20% drawdown máximo
    "max_consecutive_losses": 7,            # 7 pérdidas consecutivas
    "min_risk_reward_ratio": 1.5,           # R:R mínimo
    "max_position_single_symbol_pct": 0.20, # 20% por símbolo
}
```

> ⚠️ Estos límites solo pueden modificarse con code review.

### Kill Switch

**Triggers automáticos:**

| Trigger | Threshold | Reset |
|---------|-----------|-------|
| Pérdida diaria | > 10% | Automático a medianoche UTC |
| Drawdown total | > 20% | Solo manual (admin) |
| Pérdidas consecutivas | > 7 | Automático tras 1 win |
| Manual | Admin | Solo manual (admin) |

### Position Sizing

**Crypto:**
```python
qty = (total_capital × max_risk%) / (entry_price - stop_loss)

Ejemplo:
  Capital: $10,000 | Riesgo: 2% | Entry: $50,000 | SL: $49,000
  qty = (10000 × 0.02) / (50000 - 49000) = 0.2 BTC
```

**Forex:**
```python
lots = (total_capital × max_risk%) / (stop_pips × pip_value)

Ejemplo (EURUSD):
  Capital: $10,000 | Riesgo: 2% | Stop: 50 pips | Pip value: $10/lot
  lots = (10000 × 0.02) / (50 × 10) = 0.4 lots
```

---

## Gestión de Portafolio

### Modelo de Portafolio

```python
class Portfolio:
    total_capital: float          # Capital total
    available_capital: float      # Capital disponible
    positions: list[Position]     # Posiciones abiertas
    risk_exposure: float          # % en riesgo
    daily_pnl: float              # PnL del día
    total_pnl: float              # PnL acumulado
    drawdown_current: float       # Drawdown actual
    drawdown_max: float           # Drawdown máximo
```

### Criterio Kelly

```python
f* = (p × b - q) / b

Donde:
  p = win rate
  q = 1 - p
  b = avg_win / avg_loss

# Half-Kelly aplicado por seguridad:
kelly_safe = kelly × 0.5
```

**Ejemplo:**
```
Win Rate: 55% | Avg Win: $300 | Avg Loss: $200
b = 300/200 = 1.5
kelly = (0.55 × 1.5 - 0.45) / 1.5 = 0.25
kelly_safe = 0.125 (capped al 2%)
```

### Asignación entre Estrategias

```python
# Equal-weight con máximo 30% por estrategia
allocation = min(total_capital / n_strategies, total_capital × 0.30)
```

### Rebalancing

- Frecuencia: cada 7 días
- Criterio: Sharpe ratio proporcional
- Mínimo Sharpe: 0.5 para recibir capital
- Mínimo desplegado: 90%

---

## Motor de Ejecución

### Paper Executor

| Propiedad | Valor |
|-----------|-------|
| Slippage | 0.05% |
| Comisión | 0.10% |
| Latencia | 50-200ms |
| Idempotency | SHA-256 hash |

**Cálculo:**
```python
# BUY
fill_price = entry × (1 + slippage)     # $50,000 × 1.0005 = $50,025
commission = qty × fill × commission    # 0.2 × $50,025 × 0.001 = $10.01

# SELL
fill_price = entry × (1 - slippage)     # $50,000 × 0.9995 = $49,975
```

### Live Executor (Binance)

**Guards de seguridad:**
```
1. EXECUTION_MODE = 'live'
2. TRADING_ENABLED = true
3. Kill Switch inactivo
4. BINANCE_TESTNET = false
5. Idempotency key nuevo
```

### MT5 Executor (IC Markets)

**Diferencias:**
- Usa lotes en lugar de cantidad directa
- SL/TP nativos en la orden
- Spread fijo por instrumento

---

## Pipeline de Datos

### Flujo Completo

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PIPELINE SCHEDULER                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  APScheduler (UTC)                                                          │
│       │                                                                     │
│       ├── :00  BTCUSDT     ─┐                                              │
│       ├── :05  ETHUSDT      │ Crypto (Binance)                             │
│       ├── :10  EURUSD      ─┤                                              │
│       ├── :15  GBPUSD       │ Forex (MT5)                                  │
│       ├── :20  USDJPY       │                                              │
│       ├── :25  AUDUSD       │                                              │
│       ├── :30  USDCHF      ─┤                                              │
│       ├── :35  USDCAD       │                                              │
│       ├── :40  XAUUSD      ─┤ Commodities (MT5)                            │
│       ├── :45  US500       ─┤                                              │
│       ├── :50  US30         │ Indices (MT5)                                │
│       └── :55  UK100       ─┘                                              │
│                                                                             │
│  Cada job ejecuta _pipeline_cycle(symbol, components)                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Ciclo por Símbolo

```
1. Market Calendar Check     → ¿Mercado abierto?
2. Macro Event Check         → ¿Evento ±30min? (Forex)
3. Fetch OHLCV (250 velas)
4. Feature Engineering       → 17 indicadores
5. Order Book (crypto only)  → Microstructure
6. Agents Execution          → 4 agentes
7. Consensus                 → Weighted voting
8. Signal Generation         → SL/TP + R:R
9. Risk Validation           → Kill switch, limits
10. Execution                → Paper/Live
11. Portfolio Update
12. Persist (Redis + PostgreSQL)
13. Alert (Telegram)
```

---

## API REST

### Endpoints

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/login` | Login y obtener token |
| GET | `/market/candles/{symbol}` | OHLCV histórico |
| GET | `/market/quote/{symbol}` | Precio actual |
| GET | `/signals` | Listar señales |
| GET | `/signals/{id}` | Detalle de señal |
| GET | `/strategies` | Listar estrategias |
| POST | `/strategies/custom` | Crear estrategia |
| GET | `/portfolio` | Estado del portafolio |
| GET | `/portfolio/positions` | Posiciones abiertas |
| GET | `/risk/status` | Estado del riesgo |
| POST | `/risk/kill-switch/reset` | Reset kill switch |
| POST | `/execution/order` | Ejecutar orden |
| GET | `/execution/orders` | Historial órdenes |
| POST | `/backtest` | Ejecutar backtest |
| GET | `/health` | Health check |

### Autenticación

```http
POST /auth/login
{
    "username": "admin",
    "password": "admin123"
}

Response:
{
    "access_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

### Uso de Token

```http
GET /portfolio
Authorization: Bearer eyJ...
```

### Roles

| Rol | Expiración | Permisos |
|-----|------------|----------|
| admin | 24h | Todo + Kill Switch |
| trader | 1h | Trading + Portfolio |
| viewer | 1h | Solo lectura |

---

## Dashboard

### Páginas

| Página | Archivo | Contenido |
|--------|---------|-----------|
| Market View | `market_view.py` | Datos de mercado en tiempo real |
| Signals | `signals.py` | Historial de señales + XAI |
| Strategies | `strategies.py` | Gestión de estrategias |
| Portfolio | `portfolio.py` | Estado del portafolio |
| Backtesting | `backtesting.py` | Resultados de backtests |
| Risk Monitor | `risk_monitor.py` | Monitor de riesgo + Kill Switch |
| Simulator | `simulator.py` | Simulador histórico interactivo |

### Ejecución

```bash
# Dashboard
streamlit run app/dashboard.py --server.port 8501

# API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## Infraestructura

### Docker Compose

```yaml
Servicios:
  app:        FastAPI + Streamlit (:8000, :8501)
  db:         TimescaleDB (:5432)
  redis:      Redis (:6379)
  grafana:    Grafana (:3000)
  prometheus: Prometheus (:9090)
```

### Comandos

```bash
# Iniciar todo
docker-compose up -d

# Ver logs
docker-compose logs -f app

# Ejecutar pipeline un ciclo
docker-compose exec app python scripts/run_pipeline.py --once BTCUSDT
```

### URLs de Acceso

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Streamlit | http://localhost:8501 |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |

---

## Configuración

### Variables de Entorno

```env
# ─── Execution ─────────────────────────────────────────────────
EXECUTION_MODE=paper           # paper o live
TRADING_ENABLED=false          # Habilitar trading real

# ─── Database ──────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://trader:trader@db:5432/trader_ai
REDIS_URL=redis://redis:6379/0

# ─── Security ──────────────────────────────────────────────────
JWT_SECRET_KEY=<generar-64-chars>

# ─── Binance ───────────────────────────────────────────────────
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
BINANCE_TESTNET=true

# ─── MT5 (IC Markets) ─────────────────────────────────────────
MT5_LOGIN=0
MT5_PASSWORD=
MT5_SERVER=ICMarketsSC-Demo

# ─── Telegram ──────────────────────────────────────────────────
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
```

---

## Estado Actual

### Componentes Completados ✅

| Componente | Estado |
|------------|--------|
| Agentes IA (4) | ✅ Completo |
| Motor de consenso | ✅ Completo |
| Gestión de riesgo | ✅ Completo |
| Kill Switch | ✅ Completo |
| Ejecución papel | ✅ Completo |
| Motor backtesting | ✅ Completo |
| Gestión portafolio | ✅ Completo |
| Ingeniería features | ✅ Completo |
| XAI con SHAP | ✅ Completo |
| Clientes Binance/MT5 | ✅ Completo |
| Framework estrategias | ✅ Completo |
| Dashboard (7 páginas) | ✅ Completo |
| API FastAPI (12 rutas) | ✅ Completo |
| Docker Compose | ✅ Completo |
| CI/CD (6 checks) | ✅ Completo |

### Lo que Falta ❌

| Componente | Impacto |
|------------|---------|
| Modelos ML entrenados (.pkl) | Sin modelos reales |
| Pipeline automático | No hay scheduler activo |
| Persistencia DB operativa | Datos en memoria |
| Autenticación real | Users hardcodeados |
| Variables entorno reales | Solo placeholders |
| Telegram bot activo | No configurado |

### Checklist para Producción

**FASE A - Infraestructura:**
- [ ] Levantar PostgreSQL + Redis (docker-compose)
- [ ] Crear base de datos (schema SQL)
- [ ] Configurar .env con valores reales

**FASE B - Datos y Modelos:**
- [ ] Descargar datos históricos
- [ ] Entrenar modelos LightGBM
- [ ] Verificar archivos .pkl en data/models/

**FASE C - Pipeline:**
- [ ] Activar scheduler automático
- [ ] Verificar ciclo completo por símbolo

**FASE D - Autenticación:**
- [ ] Implementar tabla users en PostgreSQL
- [ ] Reemplazar auth hardcodeado

**FASE E - Despliegue:**
- [ ] Configurar VPS (Hetzner/DigitalOcean)
- [ ] Instalar Docker
- [ ] Configurar Nginx + HTTPS
- [ ] Verificar firewall

**FASE F - Validación Papel:**
- [ ] Sistema corriendo 2+ semanas en papel
- [ ] Sharpe sostenido ≥ 1.0
- [ ] Kill Switch funciona correctamente
- [ ] Alertas Telegram llegan

**FASE G - Live Trading:**
- [ ] Activar EXECUTION_MODE=live
- [ ] Empezar con 5% del capital
- [ ] Escalar según performance

---

## Métricas Clave del Sistema

| Métrica | Valor |
|---------|-------|
| Símbolos soportados | 12 |
| Agentes IA | 4 |
| Indicadores técnicos | 17 |
| Estrategias builtin | 2 |
| API Endpoints | 12 |
| Dashboard Pages | 7 |
| Tests totales | 76 (39 unit + 37 integration) |
| Límites hardcodeados | 7 |

---

## Enlaces Útiles

| Recurso | Ubicación |
|---------|-----------|
| Documentación técnica | `docs/README.md` |
| Estado del proyecto | `ESTADO_PROYECTO.md` |
| Plan de trabajo | `PLAN_TRABAJO.md` |
| Setup manual | `SETUP_MANUAL.md` |
| Deployment guide | `DEPLOYMENT.md` |
| API Docs (Swagger) | http://localhost:8000/docs |

---

**Última actualización:** 30 de Marzo, 2026
**Versión:** 2.0.0
**Licencia:** Privado
