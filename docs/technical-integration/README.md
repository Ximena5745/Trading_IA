# Lógica Técnica de Integración

> APIs, ingestion de datos, pipeline y despliegue

## Contenido

| Archivo | Descripción |
|---------|-------------|
| [api-routes.md](api-routes.md) | Endpoints REST API FastAPI |
| [data-ingestion.md](data-ingestion.md) | Clientes de exchange y streaming |
| [pipeline-scheduler.md](pipeline-scheduler.md) | Pipeline automático multi-activo |
| [docker-deployment.md](docker-deployment.md) | Infraestructura Docker y despliegue |

---

## Arquitectura de Integración

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    TECHNICAL INTEGRATION LAYER                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐              │
│  │  HTML/JS    │     │   FASTAPI   │     │  DATABASES  │              │
│  │  Dashboard  │◄───►│   Backend   │◄───►│  Postgres   │              │
│  │  (4 pages)  │     │  (15+ routes)│    │  + Redis    │              │
│  └─────────────┘     └──────┬──────┘     └─────────────┘              │
│  ┌─────────────┐            │                                          │
│  │  STREAMLIT  │            │                                          │
│  │  (7 pages)  │            │                                          │
│  │  (legacy)   │            │                                          │
│  └─────────────┘            │                                          │
│                             ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                     DATA SOURCES                                  │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │ │
│  │  │    Binance      │  │     MT5         │  │   Parquet       │ │ │
│  │  │   (Crypto)      │  │  (Forex/CFD)    │  │   (6 symbols)   │ │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘ │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                    SCHEDULER                                      │ │
│  │  APScheduler → 12 símbolos → cada 5 min staggered               │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Tecnologías

| Capa | Tecnología | Puerto |
|------|------------|--------|
| Frontend (activo) | HTML/JS + Plotly.js | 8000 (servido por FastAPI) |
| Frontend (legacy) | Streamlit | 8501 |
| Backend API | FastAPI | 8000 |
| Metrics | Prometheus | 9090 |
| Monitoring | Grafana | 3000 |
| Database | PostgreSQL/TimescaleDB | 5432 |
| Cache | Redis | 6379 |

---

## Cambios Recientes (2026-04-04)

### Dashboard HTML/JS Nativo
- Nuevo dashboard servido directamente por FastAPI en `http://localhost:8000/`
- 4 páginas: Market View, Signals, Portfolio, Risk
- Selector de temporalidad: 1W, 1M, 6M
- Datos reales desde parquet para 6 símbolos (EURUSD, GBPUSD, USDJPY, US30, US500, XAUUSD)
- Mock para crypto (BTCUSDT, ETHUSDT)
- Endpoints GET de `/market/*` son públicos (sin auth)

### Carga de Datos al Startup
- `_load_parquet_data()` en `api/main.py` carga todos los parquet disponibles
- Features calculadas automáticamente vía `calculate_all()` (20 indicadores)
- Cache estructurado: `{symbol: {timeframe: [records]}}`
- Timeframes 1mo y 6mo no cargan features (insuficientes velas para ≥200 requeridas)

---

*Volver al [índice principal](../README.md)*
