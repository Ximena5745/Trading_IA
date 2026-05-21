# Módulo: Observability

> Sistema de logging, métricas y tracing

---

## 1. OBJETIVO

Proveer un sistema completo de observabilidad que permita monitorear,debuggear y auditar el sistema en producción con logging estructurado, métricas Prometheus y tracing distribuido.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Structured logging | Logs con formato JSON estructurado |
| Metrics | Métricas Prometheus |
| Tracing | Distributed tracing |
| Alerting | Alertas automáticas |
| Dashboards | Visualización Grafana |

---

## 3. ARQUITECTURA

```
┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   StructuredLogger                        │ │
│  │  - JSON output                                           │ │
│  │  - Correlation IDs                                       │ │
│  │  - Context enrichment                                     │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │                    MetricsExporter                        │ │
│  │  - Prometheus metrics                                     │ │
│  │  - Custom metrics                                         │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │                    DecisionTracer                         │ │
│  │  - Decision logging                                       │ │
│  │  - XAI tracking                                           │ │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 StructuredLogger

**Archivo:** `core/observability/logger.py`

**Configuración:**
```python
import structlog

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    logger_factory=structlog.PrintLoggerFactory(),
)
```

**Uso:**
```python
log = structlog.get_logger()

# Con correlation ID
log.info(
    "order_executed",
    order_id="ord_123",
    symbol="BTCUSDT",
    quantity=0.1,
    correlation_id="req_abc123"
)

# Output JSON
{
  "event": "order_executed",
  "order_id": "ord_123",
  "timestamp": "2026-05-16T10:30:00Z",
  "level": "info"
}
```

### 4.2 MetricsExporter

**Archivo:** `core/monitoring/` (referenced)

**Métricas disponibles:**

| Categoría | Métricas |
|-----------|----------|
| Trading | signals_generated, orders_executed, pnl, drawdown |
| Risk | risk_validations, kill_switch_triggered, position_sizes |
| Performance | latency_p50, latency_p95, latency_p99, errors |
| System | cpu_usage, memory_usage, request_count |

```python
from prometheus_client import Counter, Histogram, Gauge

# Counters
signals_generated = Counter(
    'signals_generated_total',
    'Total signals generated',
    ['agent', 'action']
)

# Histograms
latency = Histogram(
    'request_latency_seconds',
    'Request latency',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0]
)

# Gauges
active_positions = Gauge(
    'portfolio_active_positions',
    'Current active positions'
)
```

### 4.3 DecisionTracer

**Archivo:** `core/observability/decision_tracer.py`

**Propósito:** Logging de decisiones de trading para debugging.

```python
class DecisionTracer:
    def trace_decision(
        self,
        decision_id: str,
        signal: Signal,
        risk_validation: dict,
        final_result: dict,
        execution: dict
    ) -> None:
        log.info(
            "trading_decision",
            decision_id=decision_id,
            signal_id=signal.id,
            action=signal.action,
            confidence=signal.confidence,
            risk_approved=risk_validation["approved"],
            executed=final_result["executed"],
            correlation_id=decision_id
        )
```

---

## 5. CORRELATION IDS

### 5.1 Generación

```python
import uuid

def generate_correlation_id() -> str:
    return f"req_{uuid.uuid4().hex[:12]}"
```

### 5.2 Propagación

```python
# Middleware
@app.middleware("http")
async def add_correlation_id(request: Request, call_next):
    correlation_id = request.headers.get("X-Correlation-ID")
    if not correlation_id:
        correlation_id = generate_correlation_id()
    
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        correlation_id=correlation_id
    )
    
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response
```

---

## 6. GRAFANA DASHBOARDS

### 6.1 Dashboards disponibles

| Dashboard | Descripción |
|-----------|-------------|
| Trading Overview | Signals, orders, P&L |
| Risk Monitor | Risk metrics, kill switch |
| System Health | CPU, memory, latency |
| Strategy Performance | Por estrategia |

### 6.2 Configuración

**Archivo:** `docker/grafana/provisioning/`

```yaml
# Dashboards config
apiVersion: 1

providers:
  - name: 'Trading AI'
    folder: 'Trading'
    type: file
    options:
      path: /etc/grafana/provisioning/dashboards
```

---

## 7. ALERTING

### 7.1 Reglas de alerta

| Alerta | Condición | Severidad |
|--------|-----------|-----------|
| High error rate | errors/min > 10 | critical |
| Kill switch | triggered | critical |
| Drawdown warning | drawdown > 15% | warning |
| Latency high | p99 > 1s | warning |
| API down | no response | critical |

### 7.2 AlertManager config

```yaml
# alertmanager.yml
routes:
  - match:
      severity: critical
    receiver: 'pager-duty'
  - match:
      severity: warning
    receiver: 'slack'
```

---

## 8. LOGGING STRUCTURE

### 8.1 Niveles

| Nivel | Uso |
|-------|-----|
| DEBUG | Development, detailed flow |
| INFO | Normal operation |
| WARNING | Recoverable issues |
| ERROR | Failures that need attention |
| CRITICAL | System down |

### 8.2 Sensitive Data

```python
# MAL
log.info(f"API key: {api_key}")

# BIEN
log.info(f"API key: {api_key[:8]}...")
```

**Datos sensibles a proteger:**
- API keys
- JWT tokens
- Passwords
- Credit cards
- Personal info

---

## 9. OBSERVABILIDAD POR COMPONENTE

### 9.1 API Layer

| Métrica | Tipo |
|--------|------|
| `api.requests.total` | Counter |
| `api.requests.errors` | Counter |
| `api.latency` | Histogram |

### 9.2 Core Engine

| Métrica | Tipo |
|--------|------|
| `engine.signals.generated` | Counter |
| `engine.orders.executed` | Counter |
| `engine.risk.validations` | Counter |

### 9.3 ML

| Métrica | Tipo |
|--------|------|
| `ml.inference.latency` | Histogram |
| `ml.predictions.total` | Counter |
| `ml.drift.detected` | Counter |

---

## 10. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Logger unavailable | Log to stderr, continue |
| Metrics export fails | Increment error counter, retry |
| High volume | Sampling for expensive logs |

---

## 11. TESTING

| Test | Cobertura objetivo |
|------|---------------------|
| test_log_output | 90% |
| test_metrics_export | 80% |
| test_correlation_id | 100% |

---

## 12. EJEMPLOS

```python
# Logging estructurado
log = structlog.get_logger()

log.info(
    "signal_generated",
    symbol="BTCUSDT",
    action="BUY",
    confidence=0.78,
    agents=["Technical", "Regime"],
    risk_validated=True,
    correlation_id=correlation_id
)

# Métricas
with latency.labels(endpoint="signals").time():
    result = await generate_signals(...)
```

---

## 13. KPIs

| KPI | Target |
|-----|--------|
| Log coverage | 100% |
| Metric coverage | > 90% |
| Dashboard uptime | 99.9% |
| Alert accuracy | > 95% |

---

*Volver al [INDEX](../INDEX.md)*