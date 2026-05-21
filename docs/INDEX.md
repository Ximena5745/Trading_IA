# DOCUMENTATION MASTER INDEX — TRADER AI

**Versión:** 2.0 | **Fecha:** 2026-05-16 | **Estado:** PRODUCTION

---

## 1. VISIÓN GENERAL DEL SISTEMA

### Propósito
Plataforma de trading algorítmico multi-activo con IA explicable que genera señales de trading, las valida contra reglas de riesgo estrictas y ejecuta órdenes automáticamente.

### Objetivos
- Generar señales de trading con alta precisión usando modelos de ML
- Proporcionar explicabilidad completa (SHAP) para cada decisión
- Gestionar riesgo en tiempo real con límites hard-coded
- Soportar múltiples activos: Crypto, Forex, Índices, Commodities
- Ejecutar en modo paper o live con seguridad

### Capacidades Principales
| Capacidad | Descripción |
|-----------|-------------|
| Multi-Agente IA | 4 agentes independientes (Technical, Regime, Microstructure, Fundamental) |
| Consensus Engine | Votación ponderada con conflict detection |
| Risk Management | Kill Switch, Position Sizing, Drawdown Protection |
| Backtesting | Walk-forward con costos reales |
| Explainability | SHAP values por cada señal |
| Multi-Asset | 12+ símbolos soportados |

---

## 2. ESTRUCTURA DEL PROYECTO

```
trader-ai/
├── api/                    # FastAPI REST API
│   ├── routes/             # Endpoint definitions (15+ routes)
│   ├── dependencies.py     # Auth dependencies
│   └── main.py            # App entry point + lifespan
├── core/                  # Core business logic
│   ├── agents/             # AI agent system
│   ├── consensus/         # Voting engine
│   ├── signals/           # Signal generation
│   ├── risk/              # Risk management
│   ├── execution/         # Order execution
│   ├── portfolio/         # Portfolio management
│   ├── strategies/        # Trading strategies
│   ├── features/          # Feature engineering
│   ├── ingestion/         # Data ingestion
│   ├── ml/                # ML pipelines
│   ├── backtesting/       # Backtest engine
│   ├── auth/              # JWT + RBAC
│   ├── observability/     # Logging + tracing
│   ├── config/            # Settings
│   └── db/                # Database layer
├── domain/                # Domain entities (Clean Architecture)
│   ├── entities/          # Signal, Order, Portfolio, Position
│   ├── value_objects/    # Price, Quantity, RiskLevel, MarketRegime
│   └── exceptions/       # Domain exceptions
├── application/           # Application layer (Use Cases + Ports)
│   ├── services/          # Application services
│   ├── use_cases/        # Use case implementations
│   └── ports/            # Port interfaces (Hexagonal)
├── infrastructure/       # Infrastructure adapters
│   ├── adapters/          # Exchange adapters
│   ├── repositories/      # Data repositories
│   └── ml_models/        # ML model storage
├── interfaces/            # Interface adapters
│   ├── api/              # API interfaces
│   ├── dashboard/        # Dashboard interface
│   └── websocket/        # WebSocket interface
├── app/                   # Streamlit dashboard (legacy)
│   └── pages/            # Dashboard pages
├── tests/                 # Test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── e2e/              # E2E tests
│   └── quant/            # Quant tests
├── docs/                  # Documentation
│   ├── architecture/     # Architecture docs
│   ├── modules/         # Module docs
│   ├── quant/           # Quant documentation
│   ├── ml/              # ML documentation
│   ├── security/        # Security docs
│   ├── devops/          # DevOps docs
│   ├── testing/         # Testing docs
│   ├── governance/      # Governance docs
│   ├── runbooks/        # Operation runbooks
│   ├── api/             # API reference
│   ├── adr/             # Architecture decision records
│   └── specs/           # Technical specs
├── scripts/               # Operational scripts
├── alembic/              # Database migrations
├── docker/               # Docker configuration
├── static/               # Dashboard static files
└── data/                 # Data storage
```

---

## 3. ARQUITECTURA

### 3.1 Arquitectura Lógica (Capas)

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│  • Streamlit Dashboard (legacy)                                │
│  • HTML/JS Dashboard (modern)                                  │
│  • Grafana Monitoring                                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API LAYER (FastAPI)                       │
│  • REST Endpoints (15+)                                        │
│  • JWT Authentication                                          │
│  • Rate Limiting (slowapi)                                     │
│  • Input Validation (Pydantic)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   APPLICATION LAYER                            │
│  • Use Cases                                                   │
│  • Application Services                                        │
│  • Port Interfaces (Hexagonal Architecture)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CORE ENGINE LAYER                          │
│  • Agent System (4 agents)                                     │
│  • Consensus Engine                                            │
│  • Signal Engine                                              │
│  • Risk Manager                                                │
│  • Execution Engine                                            │
│  • Portfolio Manager                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      DOMAIN LAYER                               │
│  • Entities (Signal, Order, Portfolio, Position)                │
│  • Value Objects (Price, Quantity, RiskLevel)                  │
│  • Domain Exceptions                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INFRASTRUCTURE LAYER                          │
│  • Exchange Adapters (Binance, MT5, Bybit)                     │
│  • Database (PostgreSQL + TimescaleDB)                         │
│  • Redis (Cache, Sessions)                                    │
│  • ML Model Storage                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Arquitectura Física

| Componente | Tecnología | Propósito |
|------------|------------|-----------|
| API Server | FastAPI + Uvicorn | REST API |
| Web Server | Nginx + Let's Encrypt | Reverse proxy + SSL |
| Database | PostgreSQL + TimescaleDB | Relational + Time-series |
| Cache | Redis | Features + Sessions |
| ML Runtime | Python 3.11+ | Model inference |
| Dashboard | Streamlit | Legacy UI |
| Monitoring | Prometheus + Grafana | Observability |
| Container | Docker | Deployment |

### 3.3 Flujo de Datos

```
Sources           Processing              Storage              Output
───────           ──────────              ───────              ──────

Binance ─────┐                          ┌─ Redis (Features)
              │                          │
MT5    ──────┼──► Pipeline ────────────┤  ── PostgreSQL
              │                          │
WebSocket ───┘                          └─ TimescaleDB
                                              │
                                              ▼
                                      Alerts (Telegram)
```

---

## 4. MÓDULOS

### 4.1 Agent System

| Módulo | Archivo | Descripción |
|--------|---------|-------------|
| BaseAgent | `core/agents/base_agent.py` | Interfaz abstracta |
| TechnicalAgent | `core/agents/technical_agent.py` | LightGBM + SHAP |
| RegimeAgent | `core/agents/regime_agent.py` | Clasificación de régimen |
| MicrostructureAgent | `core/agents/microstructure_agent.py` | Order book analysis |
| FundamentalAgent | `core/agents/fundamental_agent.py` | Events + sentiment |

### 4.2 Risk Management

| Módulo | Archivo | Descripción |
|--------|---------|-------------|
| RiskManager | `core/risk/risk_manager.py` | Validación de señales |
| KillSwitch | `core/risk/kill_switch.py` | Emergency stop |
| PositionSizer | `core/risk/position_sizer.py` | Position sizing |
| AutoAdaptation | `core/risk/auto_adaptation.py` | Auto-tuning |
| UserProfileEngine | `core/risk/user_profile_engine.py` | Perfil de riesgo |

### 4.3 Execution

| Módulo | Archivo | Descripción |
|--------|---------|-------------|
| BaseExecutor | `core/execution/base_executor.py` | Interfaz abstracta |
| PaperExecutor | `core/execution/paper_executor.py` | Paper trading |
| LiveExecutor | `core/execution/live_executor.py` | Live (Binance) |
| MT5Executor | `core/execution/mt5_executor.py` | MT5 execution |
| OrderTracker | `core/execution/order_tracker.py` | Order tracking |

### 4.4 Data Ingestion

| Módulo | Archivo | Descripción |
|--------|---------|-------------|
| BinanceClient | `core/ingestion/binance_client.py` | Binance API |
| BybitClient | `core/ingestion/bybit_client.py` | Bybit API |
| MT5Client | `core/ingestion/providers/mt5_client.py` | MT5 API |
| ExchangeAdapter | `core/ingestion/exchange_adapter.py` | Unified interface |
| WebSocketStream | `core/ingestion/websocket_stream.py` | Real-time streaming |

---

## 5. CORE CUANTITATIVO

### 5.1 Estrategias

| Estrategia | Descripción |
|------------|-------------|
| Momentum | Tendencias con EMA + RSI |
| Mean Reversion | Bollinger Bands |
| Breakout | Resistencia/Soporte |
| Volatility | ATR-based |
| AI-Driven | Modelos ML |

### 5.2 Gestión de Riesgo

- **Sizing**: Fixed fraction, Kelly criterion, Volatility-based
- **Exposure**: Max risk per trade (2%), Max portfolio risk (15%)
- **Leverage**: No leverage por defecto
- **Stop Logic**: SL/TP basados en risk-reward ratio > 1.5
- **Drawdown Protection**: Max 20% drawdown, auto-close

### 5.3 Adaptación

- **Regime Detection**: HMM para cambios de mercado
- **Strategy Switching**: Rotation basada en performance
- **Adaptive Weighting**: Meta-learning para pesos de agentes

---

## 6. IA Y ML

### 6.1 Modelos

| Modelo | Descripción | Tipo |
|--------|-------------|------|
| Technical Agent | LightGBM multiclass | Classification |
| Regime Agent | HMM | State detection |
| Meta Agent | Ensemble | Aggregation |
| RL Agent | PPO | Reinforcement |

### 6.2 Pipelines

- **Training**: Feature engineering → Model training → Validation
- **Inference**: Feature extraction → Prediction → SHAP explanation
- **Monitoring**: Drift detection, A/B testing, Alpha decay

---

## 7. SEGURIDAD

### 7.1 Authentication

- JWT con HS256
- Secret key en environment variables
- Expiración por rol (24h admin, 1h trader)

### 7.2 Authorization (RBAC)

| Rol | Permisos |
|-----|----------|
| admin | Todo + Kill Switch |
| trader | Trading + Portfolio |
| viewer | Solo lectura |

### 7.3 Trading Safety

- Paper mode por defecto
- Kill Switch automático (10% daily loss, 20% drawdown)
- Hard limits no modificables
- Idempotency keys

---

## 8. OBSERVABILIDAD

### 8.1 Logging
- Structured logging con structlog
- Correlation IDs para tracing
- Log levels: DEBUG, INFO, WARN, ERROR

### 8.2 Metrics
- Prometheus + Grafana
- Business metrics: Signals, Orders, PnL
- Technical metrics: Latency, Errors

### 8.3 Tracing
- OpenTelemetry compatible
- Decision tracing para debugging

---

## 9. DEVSECOPS

### 9.1 CI/CD

- GitHub Actions / Local
- Quality gates: Ruff, Black, MyPy, Bandit, Tests

### 9.2 Testing

| Tipo | Cobertura objetivo |
|------|---------------------|
| Unit | 80% |
| Integration | 50% |
| E2E | Critical paths |

### 9.3 Deployment

- Docker + Docker Compose
- Environment: Dev, Staging, Production

---

## 10. GOVERNANCE

### 10.1 Roles

| Rol | Ownership |
|-----|------------|
| Architect | Arquitectura general |
| Quant Lead | Estrategias + ML |
| DevOps | Infra + Deployment |
| Security | Seguridad + Compliance |

### 10.2 Review Process

- Code review obligatorio
- Architecture review para cambios mayores
- Quant review para estrategias nuevas

---

## 11. REFERENCIAS RÁPIDAS

| Tema | Archivo |
|------|---------|
| API Reference | [docs/api/](docs/api/) |
| Architecture | [docs/architecture/](docs/architecture/) |
| Modules | [docs/modules/](docs/modules/) |
| Security | [docs/architecture/security.md](docs/architecture/security.md) |
| ML Models | [docs/ml-models/](docs/ml-models/) |
| Strategies | [docs/strategies-indicators/](docs/strategies-indicators/) |
| Specs | [specs/](specs/) |

---

## 12. ÍNDICE DETALLADO

### docs/architecture/
- [system-overview.md](architecture/system-overview.md)
- [components.md](architecture/components.md)
- [security.md](architecture/security.md)
- [data-architecture.md](architecture/data-architecture.md)

### docs/modules/
- (pending creation)

### docs/quant/
- [strategies-indicators/strategies.md](../strategies-indicators/strategies.md)
- [strategies-indicators/indicators.md](../strategies-indicators/indicators.md)

### docs/ml/
- [ml-models/README.md](../ml-models/README.md)
- [ml-models/asset-specific-models.md](../ml-models/asset-specific-models.md)
- [ml-models/technical-agent.md](../ml-models/technical-agent.md)

### docs/security/
- Hereda de [architecture/security.md](../architecture/security.md)

### docs/devops/
- [technical-integration/docker-deployment.md](../technical-integration/docker-deployment.md)
- [technical-integration/pipeline-scheduler.md](../technical-integration/pipeline-scheduler.md)

### docs/testing/
- [test_dashboard_e2e.py](../../tests/test_dashboard_e2e.py)
- Configuración en [pyproject.toml](../../pyproject.toml)

### docs/governance/
- (pending creation)

### docs/runbooks/
- (pending creation)

### docs/api/
- [api-routes.md](../technical-integration/api-routes.md)

### docs/adr/
- (pending creation - Architecture Decision Records)

### docs/specs/
- [SPEC-001-DOMAIN-ENTITIES.md](../../specs/SPEC-001-DOMAIN-ENTITIES.md)
- [SPEC-002-KILL-SWITCH.md](../../specs/SPEC-002-KILL-SWITCH.md)
- [SPEC-003-AUTH-SYSTEM.md](../../specs/SPEC-003-AUTH-SYSTEM.md)
- [SPEC-004-DATABASE-SCHEMA.md](../../specs/SPEC-004-DATABASE-SCHEMA.md)
- [SPEC-005-PIPELINE-SCHEDULER.md](../../specs/SPEC-005-PIPELINE-SCHEDULER.md)

---

*Para contribuciones: Crear PR contra `main`,requiere code review.*