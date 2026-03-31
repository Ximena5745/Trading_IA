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
│  │  STREAMLIT  │     │   FASTAPI   │     │  DATABASES  │              │
│  │   Frontend  │◄───►│   Backend   │◄───►│  Postgres   │              │
│  │  (7 pages)  │     │  (12 routes)│     │  + Redis    │              │
│  └─────────────┘     └──────┬──────┘     └─────────────┘              │
│                             │                                          │
│                             ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐ │
│  │                     DATA SOURCES                                  │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │ │
│  │  │    Binance      │  │     MT5         │  │   WebSocket     │ │ │
│  │  │   (Crypto)      │  │  (Forex/CFD)    │  │   Streaming     │ │ │
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
| Frontend | Streamlit | 8501 |
| Backend API | FastAPI | 8000 |
| Metrics | Prometheus | 9090 |
| Monitoring | Grafana | 3000 |
| Database | PostgreSQL/TimescaleDB | 5432 |
| Cache | Redis | 6379 |

---

*Volver al [índice principal](../README.md)*
