# Gestión de Portafolio

> Sistema de asignación de capital, seguimiento de posiciones y métricas

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/portfolio/portfolio_manager.py` | Gestión central del portafolio |
| `core/portfolio/rebalancer.py` | Rebalanceo automático entre estrategias |

---

## PortfolioManager

### Ubicación
`core/portfolio/portfolio_manager.py`

### Responsabilidad
- Asignar capital usando criterio Kelly
- Trackear posiciones abiertas
- Calcular métricas de performance (PnL, drawdown, etc.)

### Modelo del Portafolio

```python
class Portfolio(BaseModel):
    id: str
    total_capital: float           # Capital total (disponible + posiciones)
    available_capital: float       # Capital disponible para trading
    positions: list[Position]      # Posiciones abiertas
    risk_exposure: float           # % del capital en riesgo
    daily_pnl: float               # PnL del día actual
    daily_pnl_pct: float           # PnL del día en %
    total_pnl: float               # PnL total acumulado
    drawdown_current: float        # Drawdown actual
    drawdown_max: float            # Drawdown máximo histórico
    updated_at: datetime           # Última actualización
```

### Modelo de Posición

```python
class Position(BaseModel):
    symbol: str                    # Ej: "BTCUSDT", "EURUSD"
    asset_class: str               # crypto, forex, indices, commodities
    quantity: float                # Cantidad abierta
    entry_price: float             # Precio de entrada
    current_price: float           # Precio actual
    unrealized_pnl: float          # PnL no realizado
    unrealized_pnl_pct: float      # PnL no realizado en %
    strategy_id: str               # Estrategia que abrió la posición
    opened_at: datetime            # Timestamp de apertura
```

---

## Métodos Principales

### Abrir Posición

```python
def open_position(signal: Signal, quantity: float, fill_price: float) -> Position:
    """
    Abre una nueva posición y actualiza el capital disponible.
    
    Args:
        signal: Señal generada por el sistema
        quantity: Cantidad a operar
        fill_price: Precio de ejecución
    
    Returns:
        Position: La posición creada
    """
```

**Lógica:**
1. Crea objeto Position con datos de entrada
2. Descuenta costo (`fill_price × quantity`) del capital disponible
3. Agrega posición a la lista activa
4. Actualiza métricas de riesgo

**Ejemplo:**
```python
signal = Signal(
    symbol="BTCUSDT",
    action="BUY",
    entry_price=50000.0,
    strategy_id="ema_rsi_v1"
)

position = portfolio.open_position(
    signal=signal,
    quantity=0.2,
    fill_price=50000.0
)

# Resultado:
# - available_capital -= 10000 (50000 × 0.2)
# - positions.append(nueva_posición)
# - risk_exposure actualizado
```

### Cerrar Posición

```python
def close_position(symbol: str, exit_price: float, strategy_id: str) -> Optional[float]:
    """
    Cierra una posición existente y realiza PnL.
    
    Returns:
        float: PnL realizado, o None si posición no encontrada
    """
```

**Lógica:**
1. Busca posición por símbolo y estrategia
2. Calcula PnL: `(exit_price - entry_price) × quantity`
3. Agrega proceeds (`exit_price × quantity`) al capital disponible
4. Actualiza PnL total y diario
5. Remueve posición de la lista

**Ejemplo:**
```python
# Position abierta: 0.2 BTC @ $50,000
# Cerramos a $52,000

pnl = portfolio.close_position(
    symbol="BTCUSDT",
    exit_price=52000.0,
    strategy_id="ema_rsi_v1"
)

# Resultado:
# - PnL = (52000 - 50000) × 0.2 = $400
# - available_capital += 10400 (52000 × 0.2)
# - total_pnl += 400
# - daily_pnl += 400
# - Posición removida de la lista
```

### Actualizar Precios

```python
def update_prices(prices: dict[str, float]) -> None:
    """
    Actualiza precios actuales de todas las posiciones abiertas.
    
    Args:
        prices: Dict con {symbol: current_price}
    """
```

**Lógica:**
1. Para cada posición abierta
2. Si símbolo está en prices:
   - Actualiza `current_price`
   - Recalcula `unrealized_pnl`
   - Recalcula `unrealized_pnl_pct`
3. Actualiza métricas globales

---

## Criterio Kelly

### Fórmula

```python
def kelly_fraction(win_rate: float, avg_win: float, avg_loss: float) -> float:
    """
    Criterio Kelly completo:
    
    f* = (p × b - q) / b
    
    Donde:
    - p = win rate (probabilidad de ganar)
    - q = 1 - p (probabilidad de perder)
    - b = avg_win / avg_loss (ratio ganancia/pérdida)
    
    Retorna half-Kelly (×0.5) por seguridad.
    """
```

### Ejemplo de Cálculo

```python
# Estrategia con los siguientes stats:
win_rate = 0.55      # 55% de trades ganadores
avg_win = 300.0      # Ganancia promedio
avg_loss = 200.0     # Pérdida promedio

b = avg_win / avg_loss    # 300 / 200 = 1.5
q = 1 - win_rate          # 1 - 0.55 = 0.45

kelly = (win_rate * b - q) / b
kelly = (0.55 * 1.5 - 0.45) / 1.5
kelly = (0.825 - 0.45) / 1.5
kelly = 0.375 / 1.5
kelly = 0.25

# Half-Kelly (aplicado):
kelly_safe = 0.25 * 0.5 = 0.125

# Capped al hard limit:
final = min(0.125, 0.02) = 0.02  # 2%
```

### Interpretación

| Kelly % | Significado | Acción |
|---------|-------------|--------|
| > 0.25 | Estrategia muy fuerte | Usar half-Kelly |
| 0.10 - 0.25 | Estrategia buena | Usar full Kelly |
| 0.05 - 0.10 | Estrategia moderada | Usar full Kelly |
| < 0.05 | Estrategia débil | Reducir o pausar |

---

## Asignación entre Estrategias

### Método `allocate_to_strategies`

```python
def allocate_to_strategies(self, strategy_ids: list[str]) -> dict[str, float]:
    """
    Asignación equal-weight entre estrategias activas.
    
    Reglas:
    - Capital total / número de estrategias
    - Máximo 30% por estrategia
    
    Returns:
        Dict[str, float]: {strategy_id: allocated_capital}
    """
```

### Ejemplo

```python
# Capital total: $10,000
# Estrategias activas: ["ema_rsi_v1", "mean_reversion_v1", "custom_v1"]

allocation = portfolio.allocate_to_strategies([
    "ema_rsi_v1",
    "mean_reversion_v1",
    "custom_v1"
])

# Resultado:
# {
#     "ema_rsi_v1": 3333.33,
#     "mean_reversion_v1": 3333.33,
#     "custom_v1": 3333.33
# }

# Si hay 5 estrategias:
# Per strategy: $10,000 / 5 = $2,000
# Máximo: $10,000 × 0.30 = $3,000
# Result: $2,000 cada una (por debajo del máximo)
```

---

## Rebalancer

### Ubicación
`core/portfolio/rebalancer.py`

### Responsabilidad
Rebalancear capital entre estrategias basado en performance.

### Lógica

```python
def rebalance(
    strategy_sharpe: dict[str, float],
    total_capital: float
) -> dict[str, float]:
    """
    Asigna peso proporcional al Sharpe ratio.
    
    Reglas:
    - Solo estrategias con Sharpe >= 0.5 reciben capital
    - Peso proporcional al Sharpe ratio
    - Mínimo 90% del capital desplegado
    
    Returns:
        Dict[str, float]: {strategy_id: new_allocation}
    """
```

### Ejemplo

```python
# Sharpe ratios:
# ema_rsi_v1: 1.2
# mean_reversion_v1: 0.8
# custom_v1: 0.3  (por debajo del umbral)

# Pesos:
# ema_rsi_v1: 1.2 / (1.2 + 0.8) = 60%
# mean_reversion_v1: 0.8 / (1.2 + 0.8) = 40%

# Capital: $10,000
# Resultado:
# {
#     "ema_rsi_v1": 6000.0,
#     "mean_reversion_v1": 4000.0
#     # custom_v1: 0 (Sharpe < 0.5)
# }
```

---

## Métricas del Portafolio

### Métricas Calculadas

| Métrica | Fórmula | Descripción |
|---------|---------|-------------|
| Total Capital | Available + Σ(positions × current_price) | Capital total |
| Risk Exposure | Σ(at_risk) / total_capital | % capital en riesgo |
| Daily PnL | Suma de trades del día | PnL diario |
| Daily PnL % | daily_pnl / daily_start_capital | PnL diario en % |
| Total PnL | Suma acumulada de trades | PnL total |
| Drawdown Current | (peak - current) / peak | Drawdown actual |
| Drawdown Max | Máximo histórico | Drawdown máximo |

### Fórmulas Detalladas

#### Risk Exposure

```python
total_at_risk = sum(
    abs(position.entry_price - position.stop_loss) * position.quantity
    for position in portfolio.positions
)

risk_exposure = total_at_risk / portfolio.total_capital
```

#### Drawdown

```python
# Actualizar pico de capital
if portfolio.total_capital > peak_capital:
    peak_capital = portfolio.total_capital

# Calcular drawdown actual
drawdown_current = (peak_capital - portfolio.total_capital) / peak_capital

# Actualizar drawdown máximo
drawdown_max = max(drawdown_max, drawdown_current)
```

---

## Reset Diario

```python
def reset_daily(self) -> None:
    """
    Reset métricas diarias (llamado a medianoche UTC).
    
    Resetea:
    - daily_pnl → 0
    - daily_pnl_pct → 0
    - daily_start_capital → total_capital actual
    """
```

---

## API Endpoints

### Ver Portafolio

```http
GET /portfolio
Authorization: Bearer <token>

Response:
{
    "id": "uuid",
    "total_capital": 10500.00,
    "available_capital": 7500.00,
    "positions": [
        {
            "symbol": "BTCUSDT",
            "quantity": 0.05,
            "entry_price": 50000.0,
            "current_price": 52000.0,
            "unrealized_pnl": 100.0,
            "unrealized_pnl_pct": 0.04,
            "strategy_id": "ema_rsi_v1",
            "opened_at": "2026-03-30T10:00:00Z"
        }
    ],
    "risk_exposure": 0.08,
    "daily_pnl": 150.0,
    "daily_pnl_pct": 0.015,
    "total_pnl": 500.0,
    "drawdown_current": 0.02,
    "drawdown_max": 0.05,
    "updated_at": "2026-03-30T12:00:00Z"
}
```

### Ver Posiciones

```http
GET /portfolio/positions
Authorization: Bearer <token>

Response:
{
    "positions": [
        {
            "symbol": "BTCUSDT",
            "asset_class": "crypto",
            "quantity": 0.05,
            "entry_price": 50000.0,
            "current_price": 52000.0,
            "unrealized_pnl": 100.0,
            "unrealized_pnl_pct": 0.04,
            "strategy_id": "ema_rsi_v1",
            "opened_at": "2026-03-30T10:00:00Z"
        }
    ],
    "total_positions": 1,
    "total_unrealized_pnl": 100.0
}
```

### Cerrar Posición Manualmente

```http
DELETE /portfolio/positions/{symbol}
Authorization: Bearer <token>
Body:
{
    "strategy_id": "ema_rsi_v1"
}

Response:
{
    "symbol": "BTCUSDT",
    "pnl_realized": 100.0,
    "closed_at": "2026-03-30T12:00:00Z"
}
```

---

## Testing

### Tests Unitarios

```bash
# Tests de PortfolioManager
pytest tests/unit/test_portfolio_manager.py -v
```

---

*Volver al [índice de lógica empresarial](README.md)*
