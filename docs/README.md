# TRADER AI - Documentación Técnica 360°

> Documentación consolidada del sistema de trading algorítmico multi-activo con IA explicable

## Estructura de Documentación

### 📋 Lógica Empresarial
Contiene toda la lógica de negocio: gestión de riesgos, portafolio y ejecución.

| Archivo | Descripción |
|---------|-------------|
| [risk-management.md](business-logic/risk-management.md) | Sistema de gestión de riesgos, Kill Switch y position sizing |
| [portfolio-management.md](business-logic/portfolio-management.md) | Asignación de capital, criterio Kelly y rebalanceo |
| [execution-engine.md](business-logic/execution-engine.md) | Motores de ejecución Paper y Live |

### 🔧 Lógica Técnica de Integración
Documentación de integración frontend-backend, APIs y despliegue.

| Archivo | Descripción |
|---------|-------------|
| [api-routes.md](technical-integration/api-routes.md) | Endpoints REST API FastAPI |
| [data-ingestion.md](technical-integration/data-ingestion.md) | Clientes de exchange y streaming |
| [pipeline-scheduler.md](technical-integration/pipeline-scheduler.md) | Pipeline automático multi-activo |
| [docker-deployment.md](technical-integration/docker-deployment.md) | Infraestructura Docker y despliegue |

### 💼 Lógica de Negocio (Modelos)
Modelos de datos, agentes de IA y motor de consenso.

| Archivo | Descripción |
|---------|-------------|
| [data-models.md](business-models/data-models.md) | Modelos Pydantic del dominio |
| [agent-system.md](business-models/agent-system.md) | Sistema multi-agente IA |
| [consensus-engine.md](business-models/consensus-engine.md) | Motor de votación ponderada |

### 📈 Estrategias e Indicadores
Estrategias de trading y análisis técnico.

| Archivo | Descripción |
|---------|-------------|
| [indicators.md](strategies-indicators/indicators.md) | 17 indicadores técnicos |
| [strategies.md](strategies-indicators/strategies.md) | Estrategias implementadas y framework |

### 🤖 Modelos ML
Documentación de modelos de machine learning.

| Archivo | Descripción |
|---------|-------------|
| [technical-agent.md](ml-models/technical-agent.md) | Modelo LightGBM con SHAP |

### 🔄 Flujo de Datos
Arquitectura de datos y pipeline.

| Archivo | Descripción |
|---------|-------------|
| [pipeline-flow.md](data-flow/pipeline-flow.md) | Flujo completo del pipeline |

---

## Vista Rápida del Sistema

```
┌─────────────────────────────────────────────────────────────────────┐
│                      TRADER AI ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │   FRONTEND   │    │   BACKEND    │    │   DATABASE   │         │
│  │ HTML/JS (4p) │◄──►│   FastAPI    │◄──►│ TimescaleDB  │         │
│  │ Streamlit(7p)│    │  (15+ routes)│    │   + Redis    │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│                            │                                        │
│                            ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    CORE ENGINE                               │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │   │
│  │  │Technical│  │ Regime  │  │Microstr │  │Fundamen │       │   │
│  │  │ Agent   │  │ Agent   │  │ Agent   │  │ Agent   │       │   │
│  │  │  (45%)  │  │  (35%)  │  │  (20%)  │  │(filter) │       │   │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │   │
│  │       └─────────────┼─────────────┼────────────┘            │   │
│  │                     ▼             ▼                          │   │
│  │              ┌────────────────────────┐                      │   │
│  │              │    CONSENSUS ENGINE    │                      │   │
│  │              │  Weighted Voting +     │                      │   │
│  │              │  Regime Gate           │                      │   │
│  │              └───────────┬────────────┘                      │   │
│  │                          ▼                                   │   │
│  │              ┌────────────────────────┐                      │   │
│  │              │    SIGNAL ENGINE       │                      │   │
│  │              │  SL = Entry - ATR×1.5  │                      │   │
│  │              │  TP = Entry + ATR×3.0  │                      │   │
│  │              └───────────┬────────────┘                      │   │
│  │                          ▼                                   │   │
│  │              ┌────────────────────────┐                      │   │
│  │              │    RISK MANAGER        │                      │   │
│  │              │  • Kill Switch         │                      │   │
│  │              │  • Drawdown Check      │                      │   │
│  │              │  • R:R Validation      │                      │   │
│  │              └───────────┬────────────┘                      │   │
│  │                          ▼                                   │   │
│  │              ┌────────────────────────┐                      │   │
│  │              │    EXECUTOR            │                      │   │
│  │              │  Paper / Live (MT5)    │                      │   │
│  │              └───────────┬────────────┘                      │   │
│  │                          ▼                                   │   │
│  │              ┌────────────────────────┐                      │   │
│  │              │  PORTFOLIO MANAGER     │                      │   │
│  │              │  Kelly Criterion       │                      │   │
│  │              └────────────────────────┘                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    DATA SOURCES                              │   │
│  │  Crypto: Binance    Forex/Indices: MT5 (IC Markets)        │   │
│  │  Parquet: data/raw/parquet/ (6 símbolos × 3 timeframes)    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Métricas Clave del Sistema

| Métrica | Valor |
|---------|-------|
| Símbolos soportados | 12 (2 crypto + 10 MT5) |
| Símbolos con datos reales | 6 (EURUSD, GBPUSD, USDJPY, US30, US500, XAUUSD) |
| Indicadores técnicos | 20 |
| Agentes IA | 4 (3 con peso + 1 filtro) |
| Estrategias builtin | 2 (EMA-RSI, Mean Reversion) |
| Rutas API | 15+ |
| Dashboard HTML | 4 páginas (Market View, Signals, Portfolio, Risk) |
| Dashboard Streamlit | 7 páginas (legacy) |
| Tests | 76 (39 unit + 37 integration) |

---

## Enlaces Rápidos

- [Estado del Proyecto](../ESTADO_PROYECTO.md)
- [Plan de Trabajo](../PLAN_TRABAJO.md)
- [Setup Manual](../SETUP_MANUAL.md)
- [Deployment Guide](../DEPLOYMENT.md)

---

*Última actualización: 2026-04-04*
