# TRADER AI - Sistema de Trading Algorítmico Inteligente

## 🚀 **Overview**

TRADER AI es una plataforma de trading algorítmico avanzada que utiliza inteligencia artificial explicable (XAI) para generar señales de trading con múltiples agentes, gestión de riesgos robusta y ejecución automatizada en tiempo real.

### **Características Principales**

- 🤖 **Múltiples Agentes de IA**: Technical, Fundamental, Regime, y Microstructure agents
- 🔄 **Sistema de Consenso**: Votación ponderada entre agentes para decisiones más confiables
- 🛡️ **Gestión de Riesgos Avanzada**: Kill switch automático, límites dinámicos, position sizing
- 📊 **Ejecución Dual**: Paper trading para pruebas y live trading para producción
- 🔍 **Explicabilidad**: SHAP values para entender las decisiones del modelo
- 📈 **Monitoring**: Prometheus metrics, logging estructurado, alertas Telegram
- 🧪 **Testing Integral**: Unit tests, integration tests, property-based testing

## 🏗️ **Arquitectura**

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Market Data   │───▶│  Feature Engine  │───▶│   AI Agents     │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                        │
┌─────────────────┐    ┌──────────────────┐            ▼
│   Portfolio     │◀───│   Risk Manager   │◀───┌─────────────────┐
│   Manager       │    └──────────────────┘    │ Consensus Engine│
└─────────────────┘                            └─────────────────┘
         │                                               │
         ▼                                               ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Order Tracker │◀───│   Executor       │◀───│  Signal Engine  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📦 **Instalación**

### **Prerrequisitos**
- Python 3.9+
- PostgreSQL 14+ (TimescaleDB recomendado)
- Redis 6+
- Docker & Docker Compose (opcional)

### **Setup Rápido**

```bash
# 1. Clonar el repositorio
git clone <repository-url>
cd trading-ia

# 2. Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate  # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
cp .env.example .env
# Editar .env con tus configuraciones

# 5. Iniciar base de datos (Docker)
docker-compose up -d postgres redis

# 6. Migraciones de base de datos
alembic upgrade head

# 7. Iniciar API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

## ⚙️ **Configuración**

### **Variables de Entorno Clave**

```bash
# Modo de ejecución - MANTENER EN 'paper' para desarrollo
EXECUTION_MODE=paper
TRADING_ENABLED=false

# Binance API (para live trading)
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
BINANCE_TESTNET=true  # Usar testnet para desarrollo

# Base de datos
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/trader_ai
REDIS_URL=redis://localhost:6379

# Seguridad
JWT_SECRET_KEY=generate-strong-random-key
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# Límites de riesgo
MAX_RISK_PER_TRADE_PCT=0.01  # 1% por trade
MAX_PORTFOLIO_RISK_PCT=0.10   # 10% máximo del portfolio
DAILY_LOSS_LIMIT_PCT=0.05    # 5% pérdida diaria máxima
MAX_DRAWDOWN_PCT=0.15         # 15% drawdown máximo
```

## 🔐 **Seguridad**

### **Autenticación**
- JWT tokens con expiración configurable
- Roles de usuario: admin, trader, viewer
- Hash de contraseñas con bcrypt
- Rate limiting con SlowAPI

### **Validación de Datos**
- Validación Pydantic para todos los inputs
- Detección de anomalías en market data
- Verificación de consistencia de precios

### **Gestión de Riesgos**
- Kill switch automático por múltiples triggers
- Validación de señales antes de ejecución
- Position sizing con Kelly criterion
- Límites hard-coded no modificables en runtime

## 🚀 **Uso**

### **API Endpoints**

#### **Autenticación**
```bash
# Login
curl -X POST "http://localhost:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Obtener token JWT y usarlo en headers
Authorization: Bearer <jwt_token>
```

#### **Ejecución de Trading**
```bash
# Ejecutar señal (requiere rol trader)
curl -X POST "http://localhost:8000/execution" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "signal_id": "signal-001",
    "symbol": "BTCUSDT",
    "direction": "BUY",
    "entry_price": 50000.0,
    "stop_loss": 49500.0,
    "take_profit": 51000.0,
    "confidence": 0.75
  }'
```

#### **Portfolio**
```bash
# Ver estado del portfolio
curl -X GET "http://localhost:8000/portfolio" \
  -H "Authorization: Bearer <token>"
```

### **Streamlit Dashboard**

```bash
# Iniciar dashboard
streamlit run app/dashboard.py --server.port 8501
```

El dashboard incluye:
- Vista en tiempo real del portfolio
- Gráficos de P&L y drawdown
- Señales activas y su explicación
- Métricas de riesgo
- Monitor de agentes

## 🧪 **Testing**

### **Ejecutar Tests**

```bash
# Todos los tests
pytest

# Con coverage
pytest --cov=core --cov=api --cov-report=html

# Tests específicos
pytest tests/unit/test_risk_manager.py -v
pytest tests/integration/test_pipeline_paper.py -v

# Property-based testing
pytest tests/unit/test_risk_manager.py::TestPositionSizing::test_position_size_never_exceeds_risk_limit -v
```

### **Tipos de Tests**

- **Unit Tests**: Testing de componentes individuales
- **Integration Tests**: Testing end-to-end del pipeline
- **Property-Based Testing**: Verificación de invariantes con Hypothesis
- **Performance Tests**: Testing de carga y latency

## 📊 **Monitoring**

### **Prometheus Metrics**

```bash
# Iniciar metrics server
python -c "from core.monitoring.prometheus_metrics import start_metrics_server; start_metrics_server(8001)"

# Acceder a métricas
curl http://localhost:8001/metrics
```

### **Métricas Clave**
- `trader_signals_total`: Número total de señales generadas
- `trader_trades_total`: Número total de trades ejecutados
- `trader_portfolio_value`: Valor actual del portfolio
- `trader_risk_exposure`: Exposición al riesgo actual
- `trader_agent_predictions_total`: Predicciones por agente
- `trader_errors_total`: Errores por tipo

### **Alertas Telegram**

Configurar bot token y chat ID para recibir alertas:
- Kill switch activado
- Pérdidas diarias excesivas
- Errores críticos del sistema
- Agentes con performance pobre

## 🔧 **Development**

### **Estructura del Código**

```
trading-ia/
├── api/                    # FastAPI application
│   ├── main.py            # Application entry point
│   └── routes/            # API endpoints
├── core/                  # Business logic
│   ├── agents/            # AI agents
│   ├── auth/              # Authentication
│   ├── execution/         # Order execution
│   ├── portfolio/         # Portfolio management
│   ├── risk/              # Risk management
│   └── models.py          # Pydantic models
├── app/                   # Streamlit dashboard
├── tests/                 # Test suite
├── docker/                # Docker configurations
└── scripts/              # Utility scripts
```

### **Contributing**

1. Fork el repositorio
2. Crear feature branch: `git checkout -b feature/amazing-feature`
3. Commit cambios: `git commit -m 'Add amazing feature'`
4. Push: `git push origin feature/amazing-feature`
5. Pull Request

### **Code Style**

- Black para formatting
- Ruff para linting
- mypy para type checking
- Pre-commit hooks configurados

## 🚨 **Advertencias de Seguridad**

⚠️ **MANTENER TRADING_ENABLED=false EN PRODUCCIÓN HASTA VALIDACIÓN COMPLETA**

- Nunca cambiar `EXECUTION_MODE=live` sin testing extensivo
- Usar siempre `BINANCE_TESTNET=true` para desarrollo
- Mantener límites de riesgo conservadores
- Monitorear constantemente el sistema
- Tener kill switch manual disponible

## 📈 **Performance**

### **Métricas Objetivo**
- Latencia de señal < 100ms
- Throughput > 100 señales/segundo
- Uptime > 99.9%
- Memory usage < 2GB
- CPU usage < 50%

### **Optimizaciones**
- Async/await para I/O operations
- Connection pooling para base de datos
- Caching con Redis
- Batch processing para market data

## 🆘 **Troubleshooting**

### **Problemas Comunes**

**API no responde**
```bash
# Verificar logs
uvicorn api.main:app --log-level debug

# Verificar dependencias
pip install -r requirements.txt --upgrade
```

**Conexión a Binance falla**
```bash
# Verificar API keys
echo $BINANCE_API_KEY
echo $BINANCE_SECRET_KEY

# Probar conexión
python -c "
from binance import AsyncClient
import asyncio
async def test():
    client = await AsyncClient.create(api_key, secret_key, testnet=True)
    print(await client.get_server_time())
    await client.close_connection()
asyncio.run(test())
"
```

**Base de datos no conecta**
```bash
# Verificar PostgreSQL
docker-compose logs postgres

# Test connection
psql $DATABASE_URL
```

## 📞 **Soporte**

- 📧 Email: support@trader-ai.com
- 💬 Discord: [link]
- 📖 Docs: [documentation-link]
- 🐛 Issues: [github-issues]

## 📄 **Licencia**

MIT License - ver archivo LICENSE para detalles.

---

**⚠️ ADVERTENCIA**: Este software es para fines educativos y de investigación. El trading conlleva riesgos significativos. Nunca arriesgue más de lo que puede permitirse perder.
