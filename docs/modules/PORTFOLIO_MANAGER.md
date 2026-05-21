# Módulo: Portfolio Manager

> Gestión de capital, posiciones y rebalanceo

---

## 1. OBJETIVO

Proveer un sistema de gestión de portfolio que gestione capital, posiciones abiertas, P&L, y proporcione rebalanceo automático de estrategias.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| Capital management | Tracking de capital disponible |
| Position tracking | Seguimiento de posiciones abiertas |
| P&L calculation | Cálculo de profit/loss |
| Rebalancing | Ajuste de exposiciones |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                     PORTFOLIO LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  PortfolioManager                         │ │
│  │  - Capital tracking                                       │ │
│  │  - Position management                                    │ │
│  │  - P&L calculation                                         │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │                    Rebalancer                              │  │
│  │  - Strategy rebalancing                                    │  │
│  │  - Exposure limits                                         │  │
│  │  - Risk redistribution                                     │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │   Optimizer  │ │  Factory     │ │ Redis Impl   │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 PortfolioManager

**Archivo:** `core/portfolio/portfolio_manager.py`

**Propósito:** Gestor central de portfolio.

```python
class PortfolioManager:
    def __init__(self, initial_capital: float = 10000.0):
        self._capital = initial_capital
        self._positions: dict[str, Position] = {}
        self._closed_trades: list[Trade] = []
    
    @property
    def total_capital(self) -> float: ...
    
    @property
    def available_capital(self) -> float: ...
    
    @property
    def positions(self) -> dict[str, Position]: ...
    
    @property
    def total_pnl(self) -> float: ...
    
    @property
    def daily_pnl(self) -> float: ...
    
    @property
    def drawdown(self) -> float: ...
    
    async def open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: float,
        take_profit: float
    ) -> Position: ...
    
    async def close_position(
        self,
        symbol: str,
        exit_price: float,
        reason: str = "manual"
    ) -> Trade: ...
    
    async def update_positions(
        self,
        prices: dict[str, float]
    ) -> None: ...
```

### 4.2 Position

**Archivo:** `domain/entities/portfolio.py`

```python
class Position(BaseModel):
    id: str
    symbol: str
    side: str  # LONG / SHORT
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    
    # Calculated
    unrealized_pnl: float
    pnl_pct: float
    risk_reward: float
    age: timedelta
    
    # Timestamps
    opened_at: datetime
    updated_at: datetime
```

### 4.3 Rebalancer

**Archivo:** `core/portfolio/rebalancer.py`

**Propósito:** Rebalanceo de portfolio basado en weights objetivo.

```python
class Rebalancer:
    async def rebalance(
        self,
        portfolio: Portfolio,
        target_weights: dict[str, float]
    ) -> list[Order]: ...
    
    async def get_rebalance_orders(
        self,
        portfolio: Portfolio,
        target_weights: dict[str, float]
    ) -> list[RebalanceOrder]: ...
```

**Rebalancing triggers:**
| Trigger | Threshold |
|---------|-----------|
| Drift | > 5% drift |
| Time | Daily/Weekly |
| Signal | New strategy |

### 4.4 PortfolioOptimizer

**Archivo:** `core/portfolio/portfolio_optimizer.py`

**Propósito:** Optimización de portfolio (Markowitz).

```python
class PortfolioOptimizer:
    def optimize(
        self,
        returns: pd.DataFrame,
        risk_aversion: float = 1.0
    ) -> PortfolioWeights: ...
    
    def efficient_frontier(
        self,
        returns: pd.DataFrame
    ) -> list[PortfolioWeights]: ...
```

### 4.5 PortfolioFactory

**Archivo:** `core/portfolio/portfolio_factory.py`

```python
class PortfolioFactory:
    @staticmethod
    def create(
        mode: str,  # redis, memory
        initial_capital: float,
        config: dict
    ) -> PortfolioManager: ...
```

---

## 5. P&L CALCULATION

### 5.1 Unrealized P&L

```python
def calculate_unrealized_pnl(position: Position, current_price: float) -> float:
    if position.side == "LONG":
        return (current_price - position.entry_price) * position.quantity
    else:  # SHORT
        return (position.entry_price - current_price) * position.quantity
```

### 5.2 Realized P&L

```python
def calculate_realized_pnl(trade: Trade) -> float:
    return (trade.exit_price - trade.entry_price) * trade.quantity - trade.commission
```

### 5.3 Drawdown

```python
def calculate_drawdown(portfolio: Portfolio) -> float:
    peak = max(historical_values)
    current = portfolio.total_value
    return (peak - current) / peak
```

---

## 6. EVENTOS

### 6.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `portfolio.position_opened` | Posición abierta | `{position}` |
| `portfolio.position_closed` | Posición cerrada | `{trade}` |
| `portfolio.rebalanced` | Rebalanceo ejecutado | `{changes}` |
| `portfolio.pnl_update` | Actualización P&L | `{pnl}` |
| `portfolio.drawdown_warning` | Drawdown warning | `{drawdown}` |

### 6.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| `execution.order_filled` | Actualizar posición |
| `risk.kill_switch_triggered` | Cerrar posiciones |

---

## 7. INPUTS/OUTPUTS

### 7.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| Initial capital | float | Capital inicial |
| Orders | list[Order] | Órdenes a ejecutar |
| Prices | dict[str, float] | Precios actuales |

### 7.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Portfolio state | API | Estado actual |
| Position updates | Risk | Actualización |

---

## 8. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Insufficient capital | REJECT order |
| Negative P&L | Allow, track |
| Max positions reached | REJECT new |
| Position not found | Log error + skip |

---

## 9. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Over-leveraging | Crítico | Limits |
| Drawdown exceed | Alto | Kill switch |
| Double position | Crítico | Idempotency |

---

## 10. PERFORMANCE

| Métrica | Target |
|---------|--------|
| P&L calculation time | < 1ms |
| Position update time | < 5ms |
| Rebalance time | < 100ms |

---

## 11. OBSERVABILIDAD

### 11.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `portfolio.total_value` | Gauge | Valor total |
| `portfolio.available_capital` | Gauge | Capital disponible |
| `portfolio.daily_pnl` | Gauge | P&L diario |
| `portfolio.drawdown` | Gauge | Drawdown |
| `portfolio.positions.count` | Gauge | # posiciones |
| `portfolio.positions.by_symbol` | Gauge | Por símbolo |

### 11.2 Logs

```json
{
  "event": "position_opened",
  "symbol": "BTCUSDT",
  "side": "LONG",
  "quantity": 0.1,
  "entry_price": 45000.0,
  "capital_used": 4500.0,
  "available": 5500.0
}
```

```json
{
  "event": "position_closed",
  "symbol": "BTCUSDT",
  "pnl": 250.0,
  "pnl_pct": 5.5,
  "holding_period": "2h30m"
}
```

---

## 12. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_pnl_calculation | Unit | 100% |
| test_position_tracking | Unit | 90% |
| test_rebalancing | Unit | 80% |
| test_edge_cases | Unit | 90% |

---

## 13. EJEMPLOS DE USO

```python
# Crear portfolio
portfolio = PortfolioManager(initial_capital=10000)

# Abrir posición
pos = await portfolio.open_position(
    symbol="BTCUSDT",
    side="LONG",
    quantity=0.1,
    entry_price=45000,
    stop_loss=44000,
    take_profit=47000
)

# Actualizar precios
await portfolio.update_prices({"BTCUSDT": 45500})

# Obtener estado
print(f"Total: {portfolio.total_value}")
print(f"P&L: {portfolio.total_pnl}")
```

---

## 14. KPIs

| KPI | Target |
|-----|--------|
| P&L accuracy | 100% |
| Position tracking | 100% |
| Uptime | 99.9% |

---

*Volver al [INDEX](../INDEX.md)*