# Flujo de Datos - Pipeline

> Arquitectura completa de datos del sistema

## Archivos Principales

| Archivo | Descripción |
|---------|-------------|
| [pipeline-flow.md](pipeline-flow.md) | Flujo completo del pipeline |

---

## Resumen del Flujo de Datos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATA FLOW ARCHITECTURE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  SOURCES          PROCESSING           STORAGE          OUTPUT             │
│  ───────          ──────────           ───────          ──────             │
│                                                                             │
│  Binance ──┐                    ┌─── FeatureStore ──┐                     │
│            │                    │      (Redis)      │                     │
│  MT5 ──────┼──► Pipeline ──────┤                   ├──► Alerts           │
│            │    Engine          │                   │    (Telegram)       │
│  WebSocket ┘                    └─── Repository ────┘                     │
│                                    (PostgreSQL)                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Capas de Datos

### 1. Ingestión (Sources)

| Fuente | Datos | Frecuencia |
|--------|-------|------------|
| Binance REST | OHLCV histórico | On-demand |
| Binance WebSocket | Ticks, Trades | Real-time |
| MT5 | OHLCV forex/índices | On-demand |
| ForexFactory | Eventos macro | Cada 4 horas |
| CoinGecko | Fear & Greed | Cada 30 min |

### 2. Procesamiento (Pipeline)

```
OHLCV (250 velas)
    │
    ▼
Feature Engineering (17 indicadores)
    │
    ▼
Agent Predictions (4 agentes)
    │
    ▼
Consensus (votación ponderada)
    │
    ▼
Signal Generation (SL/TP)
    │
    ▼
Risk Validation
    │
    ▼
Execution
```

### 3. Almacenamiento (Storage)

| Store | Tecnología | Datos | TTL |
|-------|------------|-------|-----|
| FeatureStore | Redis | Features calculados | 1 hora |
| Repository | PostgreSQL | Señales, órdenes, snapshots | Permanente |
| Model Store | Filesystem | Modelos .pkl | Permanente |

### 4. Output (Consumers)

| Consumer | Datos | Uso |
|----------|-------|-----|
| Telegram | Señales, alerts | Notificaciones |
| Dashboard | Métricas, posiciones | Visualización |
| Prometheus | Métricas sistema | Monitoreo |
| Grafana | Dashboards | Observabilidad |

---

## Retención de Datos

| Tipo | Retención |
|------|-----------|
| Velas OHLCV | 2 años |
| Features | 1 hora (Redis) |
| Señales | Permanente |
| Órdenes | Permanente |
| Snapshots portfolio | Permanente |
| Logs | 30 días |
| Métricas Prometheus | 15 días |

---

*Volver al [índice principal](../README.md)*
