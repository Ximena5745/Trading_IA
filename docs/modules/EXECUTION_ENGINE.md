# Módulo: Execution Engine

> Motor de ejecución de órdenes (paper/live)

---

## 1. OBJETIVO

Proveer un sistema de ejecución que gestione el ciclo completo de órdenes: desde la señal validada hasta la ejecución en exchange, incluyendo tracking, gestión de errores y modos paper/live.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Order execution | Ejecutar órdenes en exchange |
| Order tracking | Seguimiento de estado |
| Mode switching | Paper vs Live |
| Error handling | Retry, fallback |
| Cost modeling | Comisiones, slippage |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                     EXECUTION LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                      BaseExecutor                         │  │
│  │  - Abstract interface                                     │  │
│  │  - Common logic                                           │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│         ┌───────────────┼───────────────┐                     │
│         ▼               ▼               ▼                     │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐           │
│  │  Paper     │   │   Live     │   │   MT5      │           │
│  │  Executor  │   │  Executor  │   │  Executor  │           │
│  │ (Binance)  │   │ (Binance)  │   │            │           │
│  └────────────┘   └────────────┘   └────────────┘           │
│                         │                                      │
│  ┌──────────────────────┴───────────────────────────────────┐  │
│  │                   OrderTracker                            │  │
│  │  - State management                                       │  │
│  │  - Position tracking                                      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 BaseExecutor

**Archivo:** `core/execution/base_executor.py`

**Interfaz abstracta:**

```python
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(
        self,
        signal: Signal,
        quantity: float
    ) -> ExecutionResult: ...
    
    @abstractmethod
    async def cancel(
        self,
        order_id: str
    ) -> CancelResult: ...
    
    @abstractmethod
    async def get_status(
        self,
        order_id: str
    ) -> OrderStatus: ...
    
    async def validate_can_execute(self) -> bool: ...
```

### 4.2 PaperExecutor

**Archivo:** `core/execution/paper_executor.py`

**Descripción:** Simulación de trading sin conexión real a exchange.

```python
class PaperExecutor(BaseExecutor):
    def __init__(self, initial_balance: float = 10000.0):
        self._balance = initial_balance
        self._orders = []
    
    async def execute(
        self,
        signal: Signal,
        quantity: float
    ) -> ExecutionResult:
        # Simular fill inmediato al precio actual
        fill_price = await self._get_current_price(signal.symbol)
        
        return ExecutionResult(
            order_id=gen_id(),
            status=OrderStatus.FILLED,
            fill_price=fill_price,
            fill_quantity=quantity,
            commission=0.0,  # Sin comisiones en paper
            slippage=0.0
        )
```

**Características:**
- Sin comisiones
- Slippage opcional (configurable)
- Fill inmediato
- Registro completo de "ejecuciones"

### 4.3 LiveExecutor (Binance)

**Archivo:** `core/execution/live_executor.py`

**Descripción:** Ejecución real en Binance.

```python
class LiveExecutor(BaseExecutor):
    def __init__(self, api_key: str, secret: str, testnet: bool = True):
        self._client = BinanceClient(api_key, secret, testnet)
        self._mode = "testnet" if testnet else "live"
    
    async def execute(
        self,
        signal: Signal,
        quantity: float
    ) -> ExecutionResult:
        # Verificar modo
        if settings.EXECUTION_MODE != "live":
            raise ExecutionError("Not in live mode")
        
        # Crear orden
        order = await self._client.create_order(
            symbol=signal.symbol,
            side=signal.action,
            quantity=quantity,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit
        )
        
        return ExecutionResult(
            order_id=order.id,
            status=OrderStatus.SUBMITTED,
            # ...
        )
```

**Guardas de seguridad:**
```python
# Doble verificación para live
assert settings.EXECUTION_MODE == "live", "Must be live mode"
assert settings.TRADING_ENABLED, "Trading must be enabled"
assert not kill_switch.is_active(), "Kill switch must be inactive"
assert not settings.BINANCE_TESTNET, "Must not be testnet"
```

### 4.4 MT5Executor

**Archivo:** `core/execution/mt5_executor.py`

**Descripción:** Ejecución en MetaTrader 5 (Forex, Índices).

```python
class MT5Executor(BaseExecutor):
    async def execute(
        self,
        signal: Signal,
        quantity: float
    ) -> ExecutionResult:
        # Solo Forex, Índices, Commodities en MT5
        assert signal.asset_class != "crypto", "MT5 no crypto"
        
        # Trading real
        result = await mt5.order_send(
            symbol=signal.symbol,
            action=mt5.TRADE_ACTION_DEAL,
            type=ORDER_TYPE_BUY if signal.action == "BUY" else ORDER_TYPE_SELL,
            volume=quantity,
            price=signal.entry_price,
            sl=signal.stop_loss,
            tp=signal.take_profit
        )
```

### 4.5 OrderTracker

**Archivo:** `core/execution/order_tracker.py`

**Propósito:** Seguimiento de estado de órdenes y posiciones.

```python
class OrderTracker:
    async def track_order(self, order: Order) -> None: ...
    
    async def get_order(self, order_id: str) -> Order | None: ...
    
    async def get_open_positions(self) -> list[Position]: ...
    
    async def get_closed_pnl(self, since: datetime) -> float: ...
```

### 4.6 LiveOandaExecutor

**Archivo:** `core/execution/live_oanda_executor.py`

**Descripción:** Ejecución en OANDA (Forex).

---

## 5. MODOS DE EJECUCIÓN

| Modo | Descripción | Risk |
|------|-------------|------|
| Paper | Simulación, sin conexión real | Bajo |
| Live | Trading real | Alto |

### 5.1 Cambiar modo

```python
# .env
EXECUTION_MODE=paper  # Por defecto
# Para live:
EXECUTION_MODE=live
TRADING_ENABLED=true
BINANCE_TESTNET=false
```

---

## 6. EVENTOS

### 6.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `execution.order_submitted` | Orden enviada | `{order_id, details}` |
| `execution.order_filled` | Orden ejecutada | `{order_id, fill_price}` |
| `execution.order_failed` | Orden fallida | `{order_id, error}` |
| `execution.position_opened` | Posición abierta | `{position_id, details}` |
| `execution.position_closed` | Posición cerrada | `{position_id, pnl}` |

### 6.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `risk.signal_approved` | Señal validada, lista para ejecución |

---

## 7. INPUTS/OUTPUTS

### 7.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| Signal | Signal | Señal a ejecutar |
| Quantity | float | Tamaño de posición |
| Execution mode | str | paper/live |

### 7.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Execution result | Portfolio | Resultado de ejecución |
| Order status | OrderTracker | Tracking |
| Trade event | Notifications | Alerta |

---

## 8. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Network error | Retry 3x con exponential backoff |
| Rate limit | Backoff 60s + retry |
| Insufficient balance | REJECT + log |
| Order timeout | Check status + cancel si needed |
| Partial fill | Track remaining + retry |

---

## 9. COST MODELING

### 9.1 Comisiones

| Exchange | Maker | Taker |
|----------|-------|-------|
| Binance | 0.02% | 0.04% |
| MT5 | Variable | Variable |
| OANDA | Variable | Variable |

### 9.2 Slippage

```python
# Slippage model
def calculate_slippage(order_size: float, liquidity: float) -> float:
    if order_size < liquidity * 0.01:  # < 1% de liquidez
        return 0.001  # 0.1%
    elif order_size < liquidity * 0.05:  # < 5%
        return 0.005  # 0.5%
    else:
        return 0.01  # 1%
```

---

## 10. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Wrong execution | Crítico | Dry run first |
| Network failure | Alto | Retry logic |
| Order duplication | Crítico | Idempotency keys |

---

## 11. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Execution latency (paper) | < 10ms |
| Execution latency (live) | < 500ms |
| Success rate | > 99% |

---

## 12. OBSERVABILIDAD

### 12.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `execution.orders.total` | Counter | Órdenes totales |
| `execution.orders.filled` | Counter | Órdenes filling |
| `execution.orders.failed` | Counter | Órdenes fallidas |
| `execution.latency` | Histogram | Latencia |
| `execution.slippage` | Histogram | Slippage |
| `execution.cost.total` | Counter | Costo total |

### 12.2 Logs

```json
{
  "event": "order_filled",
  "order_id": "ord_123",
  "symbol": "BTCUSDT",
  "side": "BUY",
  "quantity": 0.1,
  "fill_price": 45000.0,
  "commission": 18.0,
  "slippage": 0.001,
  "latency_ms": 234
}
```

---

## 13. SEGURIDAD

- API keys en environment
- No logging de secrets
- Paper mode por defecto
- Kill switch compatible

---

## 14. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_execution | Unit | 90% |
| test_order_tracking | Unit | 90% |
| test_cost_model | Unit | 80% |
| test_error_handling | Unit | 80% |
| test_integration | Integration | 60% |

---

## 15. EJEMPLOS DE USO

```python
# Paper trading
executor = PaperExecutor()
result = await executor.execute(signal, quantity=0.1)

# Live trading
executor = LiveExecutor(api_key, secret, testnet=False)
result = await executor.execute(signal, quantity=0.1)

# Verificar resultado
if result.status == OrderStatus.FILLED:
    await tracker.track_order(result)
```

---

## 16. KPIs

| KPI | Target |
|-----|--------|
| Execution success rate | > 99% |
| Slippage < 0.1% | 95% |
| Latency < 500ms | 99% |

---

*Volver al [INDEX](../INDEX.md)*