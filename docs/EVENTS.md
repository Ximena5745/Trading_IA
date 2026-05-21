# Events & Messaging

> Sistema de eventos del sistema y patrones de mensajería

---

## 1. OVERVIEW

El sistema TRADER AI utiliza un patrón de eventos para la comunicación desacoplada entre componentes. Este documento define los eventos del sistema, sus contratos, y las políticas de publicación/consumo.

---

## 2. EVENT TAXONOMY

### 2.1 Categorías

| Categoría | Descripción | Ejemplos |
|-----------|-------------|----------|
| Market | Datos de mercado | `market_data.updated` |
| Signal | Señales de trading | `signal.generated`, `signal.validated` |
| Execution | Ejecución de órdenes | `order.submitted`, `order.filled` |
| Risk | Gestión de riesgo | `risk.kill_triggered` |
| Portfolio | Portfolio y posiciones | `position.opened`, `position.closed` |
| ML | ML ymodelos | `model.trained`, `drift.detected` |
| Auth | Autenticación | `login.success`, `login.failed` |
| System | Sistema | `system.startup`, `system.error` |

---

## 3. EVENT CONTRACTS

### 3.1 Market Events

#### market_data.updated

```json
{
  "event": "market_data.updated",
  "timestamp": "2026-05-16T10:30:00Z",
  "payload": {
    "symbol": "BTCUSDT",
    "interval": "1h",
    "ohlcv": {
      "open": 45000.0,
      "high": 45200.0,
      "low": 44800.0,
      "close": 45100.0,
      "volume": 1234.5
    },
    "source": "binance"
  },
  "metadata": {
    "correlation_id": "req_abc123",
    "trace_id": "span_xyz"
  }
}
```

### 3.2 Signal Events

#### signal.generated

```json
{
  "event": "signal.generated",
  "timestamp": "2026-05-16T10:30:00Z",
  "payload": {
    "signal_id": "sig_123",
    "symbol": "BTCUSDT",
    "action": "BUY",
    "entry_price": 45100.0,
    "stop_loss": 44000.0,
    "take_profit": 47000.0,
    "confidence": 0.78,
    "regime": "trending_up",
    "strategy_id": "technical_agent",
    "agents": {
      "technical": "BUY",
      "regime": "BUY",
      "microstructure": "HOLD"
    }
  },
  "metadata": {
    "correlation_id": "req_abc123"
  }
}
```

#### signal.validated

```json
{
  "event": "signal.validated",
  "timestamp": "2026-05-16T10:30:01Z",
  "payload": {
    "signal_id": "sig_123",
    "approved": true,
    "rejection_reason": null,
    "risk_metrics": {
      "risk_per_trade": 0.015,
      "portfolio_risk": 0.08,
      "position_size": 0.1
    }
  }
}
```

### 3.3 Execution Events

#### order.submitted

```json
{
  "event": "order.submitted",
  "timestamp": "2026-05-16T10:30:02Z",
  "payload": {
    "order_id": "ord_456",
    "signal_id": "sig_123",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.1,
    "price": 45100.0,
    "stop_loss": 44000.0,
    "take_profit": 47000.0,
    "execution_mode": "paper"
  }
}
```

#### order.filled

```json
{
  "event": "order.filled",
  "timestamp": "2026-05-16T10:30:02.5Z",
  "payload": {
    "order_id": "ord_456",
    "fill_price": 45100.0,
    "fill_quantity": 0.1,
    "commission": 0.0,
    "slippage": 0.0,
    "latency_ms": 45
  }
}
```

### 3.4 Risk Events

#### risk.kill_triggered

```json
{
  "event": "risk.kill_triggered",
  "timestamp": "2026-05-16T10:30:00Z",
  "payload": {
    "trigger": "daily_loss",
    "current_value": 0.105,
    "limit": 0.10,
    "positions_affected": 3,
    "auto_close": true,
    "triggered_at": "2026-05-16T10:30:00Z"
  }
}
```

### 3.5 Portfolio Events

#### position.opened

```json
{
  "event": "position.opened",
  "timestamp": "2026-05-16T10:30:02.5Z",
  "payload": {
    "position_id": "pos_789",
    "symbol": "BTCUSDT",
    "side": "LONG",
    "quantity": 0.1,
    "entry_price": 45100.0,
    "stop_loss": 44000.0,
    "take_profit": 47000.0,
    "capital_used": 4510.0,
    "remaining_capital": 5490.0
  }
}
```

#### position.closed

```json
{
  "event": "position.closed",
  "timestamp": "2026-05-16T12:45:00Z",
  "payload": {
    "position_id": "pos_789",
    "exit_price": 46000.0,
    "pnl": 90.0,
    "pnl_pct": 2.0,
    "holding_duration": "2h15m",
    "close_reason": "take_profit"
  }
}
```

---

## 4. EVENT PUBLISHERS

### 4.1 Publishers por Módulo

| Módulo | Eventos publicados |
|--------|-------------------|
| Ingestion | `market_data.updated` |
| Signal Engine | `signal.generated` |
| Risk Manager | `signal.validated`, `risk.kill_triggered` |
| Execution | `order.submitted`, `order.filled`, `order.failed` |
| Portfolio | `position.opened`, `position.closed`, `portfolio.rebalanced` |
| ML | `model.trained`, `model.deployed`, `drift.detected` |
| Auth | `login.success`, `login.failed`, `token.created` |

### 4.2 Interfaz de Publicación

```python
class EventPublisher(ABC):
    async def publish(
        self,
        event_type: str,
        payload: dict,
        metadata: dict | None = None
    ) -> None: ...
    
    async def publish_batch(
        self,
        events: list[Event]
    ) -> None: ...
```

---

## 5. EVENT CONSUMERS

### 5.1 Consumers por Evento

| Evento | Consumers |
|--------|-----------|
| `market_data.updated` | FeatureEngine, Agents |
| `signal.generated` | RiskManager |
| `risk.signal_approved` | Execution |
| `order.filled` | Portfolio, PositionTracker |
| `position.closed` | Backtest, Notifications |

### 5.2 Patrón de Consumo

```python
class EventConsumer(ABC):
    @abstractmethod
    async def handle(self, event: Event) -> None: ...
    
    async def start(self) -> None: ...
    
    async def stop(self) -> None: ...
```

---

## 6. RETRY POLICIES

### 6.1 Retry Config

| Event Type | Max Retries | Backoff | Dead Letter Queue |
|------------|--------------|---------|-------------------|
| Market Data | 3 | exponential | No |
| Execution | 5 | exponential | Yes |
| Risk | 2 | linear | Yes |
| ML | 3 | exponential | No |

### 6.2 Retry Example

```python
async def publish_with_retry(
    event: Event,
    max_retries: int = 3
) -> None:
    for attempt in range(max_retries):
        try:
            await publisher.publish(event)
            return
        except Exception as e:
            if attempt == max_retries - 1:
                await dead_letter_queue.send(event, str(e))
            await asyncio.sleep(2 ** attempt)
```

---

## 7. IDEMPOTENCY

### 7.1 Keys

```python
# Cada evento debe tener idempotency_key
event = {
    "idempotency_key": "sig_BTCUSDT_BUY_20260516T103000Z",
    "event_type": "signal_generated",
    "payload": {...}
}
```

### 7.2 Handling

```python
async def handle_event(event: Event) -> None:
    # Check if already processed
    processed = await redis.get(f"processed:{event.idempotency_key}")
    if processed:
        return  # Skip duplicate
    
    # Process event
    await process(event)
    
    # Mark as processed
    await redis.set(
        f"processed:{event.idempotency_key}",
        "1",
        ex=86400  # 24h
    )
```

---

## 8. EVENT ORDERING

### 8.1 Guarantees

| Event Category | Ordering Guarantee |
|----------------|-------------------|
| Market Data | FIFO per symbol |
| Execution | FIFO per order |
| Portfolio | FIFO global |

### 8.2 Handling Out-of-Order

```python
async def handle_signal(event: Event) -> None:
    # Check timestamp
    if event.timestamp < last_processed_timestamp:
        log.warning("Out-of-order event", event_id=event.id)
        # Reorder or skip based on business logic
```

---

## 9. DISTRIBUTED COORDINATION

### 9.1 Saga Pattern

Para transacciones distribuidas:

```python
# Compensating transactions
async def execute_trade(signal: Signal):
    try:
        # Step 1: Validate
        await risk_manager.validate(signal)
        
        # Step 2: Execute
        result = await executor.execute(signal)
        
        # Step 3: Track
        await portfolio.track_position(result)
        
    except Exception as e:
        # Compensate
        await executor.cancel(result.order_id)
        await portfolio.rollback()
```

---

## 10. OBSERVABILIDAD

### 10.1 Metrics

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `events.published.total` | Counter | Eventos publicados |
| `events.consumed.total` | Counter | Eventos consumidos |
| `events.failed.total` | Counter | Eventos fallidos |
| `events.retry.count` | Counter | Reintentos |
| `events.latency` | Histogram | Latencia |

### 10.2 Logs

```json
{
  "event": "event_published",
  "event_type": "signal_generated",
  "publisher": "signal_engine",
  "payload_size": 1024
}
```

---

## 11. EVENT SCHEMA REGISTRY

### 11.1 Schema Storage

```
docs/events/schemas/
├── market_data.updated.json
├── signal.generated.json
├── signal.validated.json
├── order.submitted.json
├── order.filled.json
├── position.opened.json
└── ...
```

---

*Volver al [INDEX](INDEX.md)*