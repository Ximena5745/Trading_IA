# Motor de Ejecución

> Sistema de ejecución de órdenes en modo Paper y Live

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/execution/base_executor.py` | Interfaz abstracta |
| `core/execution/paper_executor.py` | Ejecución simulada |
| `core/execution/live_executor.py` | Ejecución real (Binance) |
| `core/execution/mt5_executor.py` | Ejecución MT5 (Forex/Índices) |
| `core/execution/order_tracker.py` | Tracking de órdenes |

---

## Arquitectura de Ejecutores

```
                    BaseExecutor (ABC)
                          │
          ┌───────────────┼───────────────┐
          │               │               │
    PaperExecutor   LiveExecutor    MT5Executor
    (Simulación)    (Binance)      (IC Markets)
```

---

## BaseExecutor

### Interfaz Abstracta

```python
class BaseExecutor(ABC):
    @abstractmethod
    async def execute(self, signal: dict, quantity: float) -> dict:
        """Ejecuta una orden basada en la señal."""
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancela una orden pendiente."""
        pass
    
    @abstractmethod
    async def get_order_status(self, order_id: str) -> dict:
        """Obtiene el estado actual de una orden."""
        pass
```

---

## PaperExecutor

### Ubicación
`core/execution/paper_executor.py`

### Responsabilidad
Simular trading realista sin tocar dinero real.

### Configuración

```python
PAPER_SLIPPAGE_PCT = 0.0005     # 0.05% slippage
PAPER_COMMISSION_PCT = 0.001    # 0.1% comisión
PAPER_LATENCY_MS_MIN = 50       # Latencia mínima
PAPER_LATENCY_MS_MAX = 200      # Latencia máxima
```

### Lógica de Ejecución

```python
async def execute(self, signal: dict, quantity: float) -> dict:
    """
    1. Verificar idempotency key (evitar duplicados)
    2. Aplicar slippage al precio de entrada
    3. Simular latencia de red
    4. Calcular comisión
    5. Retornar orden ejecutada
    """
```

### Cálculo de Slippage

```python
# Slippage direction según orden
if action == "BUY":
    # Compra sube el precio
    fill_price = entry_price * (1 + slippage_pct)
else:
    # Venta baja el precio
    fill_price = entry_price * (1 - slippage_pct)

# Ejemplo:
# Entry: $50,000
# Slippage: 0.05%
# Fill BUY: $50,000 × 1.0005 = $50,025
# Fill SELL: $50,000 × 0.9995 = $49,975
```

### Cálculo de Comisión

```python
commission = quantity * fill_price * commission_pct

# Ejemplo:
# Quantity: 0.2 BTC
# Fill: $50,025
# Commission: 0.2 × $50,025 × 0.001 = $10.005
```

### Idempotency

```python
# La key se genera del hash de (symbol, timestamp, direction)
# Evita duplicar órdenes si el sistema recibe la misma señal dos veces

idempotency_key = hashlib.sha256(
    f"{symbol}:{timestamp}:{direction}".encode()
).hexdigest()[:16]
```

### Estructura de Orden Retornada

```python
{
    "id": "uuid",
    "idempotency_key": "a1b2c3d4e5f6g7h8",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "order_type": "MARKET",
    "quantity": 0.2,
    "price": 50000.0,
    "fill_price": 50025.0,        # Con slippage
    "fill_quantity": 0.2,
    "commission": 10.005,          # Comisión aplicada
    "slippage": 25.0,              # Slippage en $
    "status": "filled",
    "created_at": "2026-03-30T12:00:00Z",
    "updated_at": "2026-03-30T12:00:00Z",
    "execution_mode": "paper"
}
```

---

## LiveExecutor (Binance)

### Ubicación
`core/execution/live_executor.py`

### Responsabilidad
Ejecutar órdenes reales en Binance (testnet o mainnet).

### Guards de Seguridad

```python
async def execute(self, signal: dict, quantity: float) -> dict:
    """
    Guards (en orden):
    1. EXECUTION_MODE debe ser 'live'
    2. TRADING_ENABLED debe ser true
    3. Kill Switch debe estar inactivo
    4. Idempotency key no debe existir
    """
```

### Configuración

```env
EXECUTION_MODE=paper  # Solo cambiar a 'live' tras validación
TRADING_ENABLED=false # Habilitar explícitamente
BINANCE_TESTNET=true  # Usar testnet primero
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
```

### Flujo de Ejecución

```
Execute called
     │
     ▼
┌─────────────────────────┐
│ Check: EXECUTION_MODE   │
│ Must be 'live'          │
└────────────┬────────────┘
             │ OK
             ▼
┌─────────────────────────┐
│ Check: TRADING_ENABLED  │
│ Must be true            │
└────────────┬────────────┘
             │ OK
             ▼
┌─────────────────────────┐
│ Check: Kill Switch      │
│ Must be inactive        │
└────────────┬────────────┘
             │ OK
             ▼
┌─────────────────────────┐
│ Check: Idempotency      │
│ Key must be new         │
└────────────┬────────────┘
             │ OK
             ▼
┌─────────────────────────┐
│ Create Binance Order    │
│ MARKET order type       │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Wait for Fill           │
│ Poll order status       │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ Return Order Object     │
└─────────────────────────┘
```

---

## MT5Executor (Forex/Índices)

### Ubicación
`core/execution/mt5_executor.py`

### Responsabilidad
Ejecutar órdenes en MetaTrader 5 via IC Markets.

### Configuración

```env
MT5_LOGIN=12345678
MT5_PASSWORD=xxx
MT5_SERVER=ICMarketsSC-Demo
```

### Diferencias con Binance

| Aspecto | Binance | MT5 |
|---------|---------|-----|
| Order types | MARKET, LIMIT | MARKET, LIMIT, STOP, SL/TP |
| Lot sizing | Cantidad del asset | Lotes (0.01 mínimo) |
| Spread | Variable | Fijo por instrumento |
| SL/TP | Opcional | Nativo en orden |

### Flujo de Ejecución

```python
async def execute(self, signal: dict, quantity: float) -> dict:
    """
    1. Traducir signal a orden MT5
    2. Usar lotes en lugar de cantidad directa
    3. Enviar orden con SL/TP incluidos
    4. Esperar confirmación
    """
```

### Ejemplo de Orden MT5

```python
# Señal:
signal = {
    "action": "BUY",
    "entry_price": 1.0850,      # EURUSD
    "stop_loss": 1.0800,        # 50 pips
    "take_profit": 1.0950       # 100 pips
}

# Cálculo de lotes:
instrument = InstrumentConfig(
    symbol="EURUSD",
    pip_value=10.0,             # $10/lot/pip
    min_lots=0.01,
    lot_step=0.01
)

# Order MT5:
mt5_order = {
    "symbol": "EURUSD",
    "action": "BUY",
    "volume": 0.1,              # 0.1 lots
    "sl": 1.0800,
    "tp": 1.0950,
    "type": "MARKET"
}
```

---

## OrderTracker

### Ubicación
`core/execution/order_tracker.py`

### Responsabilidad
Tracking de todas las órdenes ejecutadas.

### Modelo de Orden

```python
class Order(BaseModel):
    id: str
    exchange_order_id: Optional[str]     # ID en el exchange
    idempotency_key: str                 # Key de idempotencia
    signal_id: str                       # ID de la señal original
    symbol: str
    asset_class: str
    side: str                            # BUY / SELL
    order_type: str                      # MARKET / LIMIT
    quantity: float
    price: Optional[float]               # Precio límite (si aplica)
    stop_loss: float
    take_profit: float
    status: OrderStatus                  # PENDING → SUBMITTED → FILLED
    fill_price: Optional[float]
    fill_quantity: Optional[float]
    commission: Optional[float]
    slippage: Optional[float]
    created_at: datetime
    updated_at: datetime
    execution_mode: str                  # paper / live
    error_message: Optional[str]
```

### Estados de Orden

```python
class OrderStatus(str, Enum):
    PENDING = "pending"       # Creada, no enviada
    SUBMITTED = "submitted"   # Enviada al exchange
    PARTIAL = "partial"       # Fill parcial
    FILLED = "filled"         # Completamente ejecutada
    CANCELLED = "cancelled"   # Cancelada por usuario
    REJECTED = "rejected"     # Rechazada por exchange
    EXPIRED = "expired"       # Expirada (órdenes límite)
```

### Flujo de Estados

```
PENDING
   │
   ▼ (execute())
SUBMITTED
   │
   ├─► (partial fill) PARTIAL
   │        │
   │        ▼ (full fill)
   │       FILLED
   │
   ├─► (full fill) FILLED
   │
   ├─► (cancelled) CANCELLED
   │
   ├─► (rejected) REJECTED
   │
   └─► (timeout) EXPIRED
```

---

## API Endpoints

### Ejecutar Orden

```http
POST /execution/order
Authorization: Bearer <token>
Body:
{
    "signal_id": "uuid",
    "quantity": 0.2
}

Response:
{
    "order_id": "uuid",
    "status": "filled",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.2,
    "fill_price": 50025.0,
    "commission": 10.005,
    "execution_mode": "paper",
    "created_at": "2026-03-30T12:00:00Z"
}
```

### Ver Estado de Orden

```http
GET /execution/order/{order_id}
Authorization: Bearer <token>

Response:
{
    "order_id": "uuid",
    "status": "filled",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.2,
    "fill_price": 50025.0,
    "commission": 10.005,
    "slippage": 25.0,
    "created_at": "2026-03-30T12:00:00Z",
    "updated_at": "2026-03-30T12:00:01Z"
}
```

### Cancelar Orden

```http
DELETE /execution/order/{order_id}
Authorization: Bearer <token>

Response:
{
    "order_id": "uuid",
    "status": "cancelled",
    "cancelled_at": "2026-03-30T12:00:30Z"
}
```

### Historial de Órdenes

```http
GET /execution/orders?symbol=BTCUSDT&status=filled&limit=20
Authorization: Bearer <token>

Response:
{
    "orders": [...],
    "total": 45,
    "page": 1,
    "limit": 20
}
```

---

## Testing

### Tests Unitarios

```bash
# Tests de PaperExecutor
pytest tests/unit/test_paper_executor.py -v

# Tests de MT5Executor
pytest tests/unit/test_mt5_executor.py -v
```

### Tests de Integración

```bash
# Test completo de ejecución
pytest tests/integration/test_api_execution.py -v
```

---

## Configuración de Ejecución

### Variables de Entorno

```env
# Modo de ejecución
EXECUTION_MODE=paper           # paper o live
TRADING_ENABLED=false          # Habilitar trading

# Binance
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
BINANCE_TESTNET=true           # Usar testnet

# MT5 (IC Markets)
MT5_LOGIN=12345678
MT5_PASSWORD=xxx
MT5_SERVER=ICMarketsSC-Demo

# Paper (valores por defecto)
PAPER_SLIPPAGE_PCT=0.0005
PAPER_COMMISSION_PCT=0.001
PAPER_LATENCY_MS_MIN=50
PAPER_LATENCY_MS_MAX=200
```

---

*Volver al [índice de lógica empresarial](README.md)*
