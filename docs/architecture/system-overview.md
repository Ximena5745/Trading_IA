# Vista General del Sistema

> Descripción de alto nivel del sistema Trading IA

---

## ¿Qué es Trading IA?

Plataforma de trading algorítmico multi-activo que genera señales de compra/venta usando un sistema multi-agente de IA, valida cada señal contra reglas de riesgo estrictas y ejecuta órdenes automáticamente.

### Características Principales

- **Multi-activo**: Crypto, Forex, Índices, Commodities
- **Multi-agente**: 4 agentes IA independientes con votación ponderada
- **Explainable AI**: Explicaciones con SHAP para cada decisión
- **Risk Management**: Kill switch, drawdown limits, position sizing
- **Paper Trading**: Modo simulado por defecto
- **Backtesting**: Walk-forward con costos reales

---

## Stack Tecnológico

```
┌─────────────────────────────────────────────────────────────┐
│                     TECHNOLOGY STACK                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FRONTEND          │  BACKEND           │  DATA             │
│  ─────────         │  ───────           │  ────             │
│  • Streamlit       │  • FastAPI         │  • TimescaleDB    │
│  • Plotly          │  • Pydantic        │  • Redis          │
│  • Pandas          │  • SQLAlchemy      │  • Parquet        │
│                    │  • APScheduler     │                   │
│                    │                    │                   │
│  ML                │  INFRASTRUCTURE    │  INTEGRATION      │
│  ──                │  ──────────────    │  ───────────      │
│  • LightGBM        │  • Docker          │  • Binance API    │
│  • SHAP            │  • Nginx           │  • MT5 API        │
│  • Scikit-learn    │  • Prometheus      │  • Telegram Bot   │
│                    │  • Grafana         │                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Arquitectura de Capas

### 1. Presentation Layer

- **Streamlit Dashboard**: 7 páginas para visualización y control
- **Grafana**: Dashboards de monitoreo y métricas

### 2. API Layer

- **FastAPI**: 12 rutas REST con autenticación JWT
- **Rate Limiting**: Protección contra abuso
- **CORS**: Configurado para Streamlit

### 3. Core Engine

- **Agent System**: 4 agentes IA independientes
- **Consensus Engine**: Votación ponderada
- **Signal Engine**: Generación de señales con SL/TP
- **Risk Manager**: Validación de riesgo
- **Executor**: Paper/Live execution
- **Portfolio Manager**: Gestión de capital

### 4. Data Layer

- **TimescaleDB**: Almacenamiento de series temporales
- **Redis**: Cache de features y sesiones
- **Filesystem**: Modelos ML entrenados

### 5. External Services

- **Binance**: Crypto exchange
- **MT5 (IC Markets)**: Forex/Índices/Commodities
- **Telegram**: Notificaciones

---

## Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Sources              Processing              Storage         Output    │
│  ───────              ──────────              ───────         ──────    │
│                                                                         │
│  Binance     ──┐                    ┌── Redis (Features) ──┐           │
│                │                    │                       │           │
│  MT5        ───┼──► Pipeline ──────┤                       ├──► Alerts │
│                │                    │                       │           │
│  WebSocket  ───┘                    └── PostgreSQL (Historical) ─┘     │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Símbolos Soportados

| Clase | Símbolos | Exchange |
|-------|----------|----------|
| Crypto | BTCUSDT, ETHUSDT, SOLUSDT, BNBUSDT | Binance |
| Forex | EURUSD, GBPUSD, USDJPY, AUDUSD, USDCHF, USDCAD | MT5 |
| Indices | US500, US30, UK100, DE40 | MT5 |
| Commodities | XAUUSD, XAGUSD, USOIL, UKOIL | MT5 |

---

## Métricas del Sistema

| Métrica | Valor |
|---------|-------|
| Símbolos | 12 |
| Agentes IA | 4 |
| Indicadores | 17 |
| Estrategias builtin | 2 |
| API Endpoints | 12 |
| Dashboard Pages | 7 |
| Tests | 76 |

---

*Volver al [índice de arquitectura](README.md)*
