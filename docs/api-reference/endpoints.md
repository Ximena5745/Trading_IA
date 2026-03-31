# API Endpoints Reference

> Documentación completa de todos los endpoints

---

## Autenticación

### POST /auth/login

Login y obtener token JWT.

**Request:**
```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

**Response 200:**
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

### POST /auth/register

Registrar nuevo usuario.

**Request:**
```http
POST /auth/register
Content-Type: application/json

{
    "username": "trader1",
    "email": "trader@example.com",
    "password": "securepass123",
    "role": "trader"
}
```

### GET /auth/me

Obtener información del usuario actual.

**Request:**
```http
GET /auth/me
Authorization: Bearer <token>
```

---

## Market Data

### GET /market/candles/{symbol}

Obtener velas OHLCV históricas.

**Request:**
```http
GET /market/candles/BTCUSDT?timeframe=1h&limit=100
Authorization: Bearer <token>
```

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| timeframe | string | 1h | 1m, 5m, 15m, 1h, 4h, 1d |
| limit | int | 100 | Número de velas (max 1000) |
| from_ts | datetime | - | Fecha inicio (opcional) |
| to_ts | datetime | - | Fecha fin (opcional) |

**Response 200:**
```json
{
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "candles": [
        {
            "timestamp": "2026-03-30T10:00:00Z",
            "open": 50000.0,
            "high": 50500.0,
            "low": 49800.0,
            "close": 50200.0,
            "volume": 1250.5
        }
    ]
}
```

### GET /market/quote/{symbol}

Obtener precio actual (bid/ask).

**Response 200:**
```json
{
    "symbol": "EURUSD",
    "bid": 1.0850,
    "ask": 1.0852,
    "spread": 0.0002,
    "timestamp": "2026-03-30T12:00:00Z"
}
```

### GET /market/orderbook/{symbol}

Obtener order book.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| depth | int | 20 | Profundidad (5, 10, 20, 50, 100) |

**Response 200:**
```json
{
    "symbol": "BTCUSDT",
    "bids": [[50000.0, 0.5], [49999.0, 1.2]],
    "asks": [[50001.0, 0.3], [50002.0, 0.8]],
    "timestamp": "2026-03-30T12:00:00Z"
}
```

---

## Signals

### GET /signals

Listar señales generadas.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | - | Filtrar por símbolo |
| status | string | - | pending, executed, cancelled |
| strategy_id | string | - | Filtrar por estrategia |
| limit | int | 20 | Límite de resultados |
| offset | int | 0 | Offset para paginación |

**Response 200:**
```json
{
    "signals": [
        {
            "id": "uuid",
            "timestamp": "2026-03-30T12:00:00Z",
            "symbol": "BTCUSDT",
            "action": "BUY",
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 53000.0,
            "risk_reward_ratio": 3.0,
            "confidence": 0.75,
            "strategy_id": "ema_rsi_v1",
            "status": "pending",
            "summary": "Señal BUY por RSI sobreventa + cruce EMA"
        }
    ],
    "total": 45,
    "limit": 20,
    "offset": 0
}
```

### GET /signals/{id}

Obtener detalle de una señal.

**Response 200:**
```json
{
    "id": "uuid",
    "timestamp": "2026-03-30T12:00:00Z",
    "symbol": "BTCUSDT",
    "action": "BUY",
    "entry_price": 50000.0,
    "stop_loss": 49000.0,
    "take_profit": 53000.0,
    "risk_reward_ratio": 3.0,
    "confidence": 0.75,
    "explanation": [
        {
            "factor": "RSI_14",
            "weight": 0.35,
            "direction": "BUY",
            "description": "RSI en sobreventa (28)"
        },
        {
            "factor": "MACD_HISTOGRAM",
            "weight": 0.25,
            "direction": "BUY",
            "description": "MACD histogram positivo"
        }
    ],
    "summary": "Señal BUY por RSI sobreventa + cruce alcista EMA",
    "regime": "bull_trending",
    "strategy_id": "ema_rsi_v1",
    "status": "pending"
}
```

### GET /signals/latest

Obtener la última señal.

### GET /signals/stats

Obtener estadísticas de señales.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| period | string | 7d | 1d, 7d, 30d, 90d |

**Response 200:**
```json
{
    "period": "7d",
    "total_signals": 150,
    "buy_signals": 80,
    "sell_signals": 70,
    "avg_confidence": 0.68,
    "avg_risk_reward": 2.5,
    "by_strategy": {
        "ema_rsi_v1": 90,
        "mean_reversion_v1": 60
    }
}
```

---

## Strategies

### GET /strategies

Listar todas las estrategias.

**Response 200:**
```json
{
    "strategies": [
        {
            "strategy_id": "ema_rsi_v1",
            "name": "EMA Crossover + RSI",
            "version": "1.0.0",
            "description": "EMA crossover with RSI confirmation",
            "status": "active",
            "timeframe": "1h",
            "symbols": ["BTCUSDT", "ETHUSDT", "EURUSD"],
            "parameters": {
                "rsi_oversold": 30.0,
                "rsi_overbought": 70.0,
                "min_volume_ratio": 1.2
            }
        }
    ],
    "total": 2,
    "active": 2
}
```

### GET /strategies/{id}

Obtener detalle de una estrategia.

### POST /strategies/custom

Crear estrategia custom (admin only).

**Request:**
```http
POST /strategies/custom
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "strategy_id": "my_custom_v1",
    "name": "My Custom Strategy",
    "description": "Custom RSI + MACD strategy",
    "entry_conditions": [
        {"feature": "rsi_14", "operator": "lt", "value": 30},
        {"feature": "macd_histogram", "operator": "gt", "value": 0}
    ],
    "exit_conditions": [
        {"feature": "rsi_14", "operator": "gt", "value": 70}
    ],
    "default_action": "BUY"
}
```

**Response 201:**
```json
{
    "strategy_id": "my_custom_v1",
    "name": "My Custom Strategy",
    "status": "active",
    "created_at": "2026-03-30T12:00:00Z"
}
```

### PATCH /strategies/{id}/status

Cambiar estado de una estrategia.

**Request:**
```http
PATCH /strategies/ema_rsi_v1/status
Authorization: Bearer <token>
Content-Type: application/json

{
    "status": "paused"
}
```

**Options:** `active`, `paused`, `disabled`

### DELETE /strategies/{id}

Eliminar una estrategia (admin only).

---

## Portfolio

### GET /portfolio

Obtener estado del portafolio.

**Response 200:**
```json
{
    "id": "uuid",
    "total_capital": 10500.0,
    "available_capital": 7500.0,
    "positions_count": 2,
    "risk_exposure": 0.08,
    "daily_pnl": 150.0,
    "daily_pnl_pct": 0.015,
    "total_pnl": 500.0,
    "drawdown_current": 0.02,
    "drawdown_max": 0.05,
    "updated_at": "2026-03-30T12:00:00Z"
}
```

### GET /portfolio/positions

Obtener posiciones abiertas.

**Response 200:**
```json
{
    "positions": [
        {
            "symbol": "BTCUSDT",
            "asset_class": "crypto",
            "quantity": 0.2,
            "entry_price": 50000.0,
            "current_price": 52000.0,
            "unrealized_pnl": 400.0,
            "unrealized_pnl_pct": 0.04,
            "strategy_id": "ema_rsi_v1",
            "opened_at": "2026-03-30T10:00:00Z"
        }
    ],
    "total_positions": 1,
    "total_unrealized_pnl": 400.0
}
```

### DELETE /portfolio/positions/{symbol}

Cerrar posición manualmente.

**Request:**
```http
DELETE /portfolio/positions/BTCUSDT
Authorization: Bearer <token>
Content-Type: application/json

{
    "strategy_id": "ema_rsi_v1"
}
```

---

## Risk

### GET /risk/status

Obtener estado del riesgo.

**Response 200:**
```json
{
    "kill_switch_active": false,
    "daily_loss_pct": 0.02,
    "daily_loss_limit": 0.10,
    "drawdown_current": 0.05,
    "drawdown_limit": 0.20,
    "risk_exposure": 0.08,
    "risk_exposure_limit": 0.15,
    "consecutive_losses": 2,
    "max_consecutive_losses": 7,
    "limits": {
        "max_risk_per_trade_pct": 0.02,
        "min_risk_reward_ratio": 1.5
    }
}
```

### POST /risk/kill-switch/trigger

Activar kill switch manualmente (admin only).

**Request:**
```http
POST /risk/kill-switch/trigger
Authorization: Bearer <admin_token>
Content-Type: application/json

{
    "reason": "manual_override",
    "message": "Maintenance window"
}
```

### POST /risk/kill-switch/reset

Reset kill switch (admin only).

**Response 200:**
```json
{
    "status": "reset",
    "reset_by": "admin",
    "reset_at": "2026-03-30T12:00:00Z"
}
```

---

## Execution

### POST /execution/order

Ejecutar una orden.

**Request:**
```http
POST /execution/order
Authorization: Bearer <token>
Content-Type: application/json

{
    "signal_id": "uuid",
    "quantity": 0.2
}
```

**Response 201:**
```json
{
    "order_id": "uuid",
    "status": "filled",
    "symbol": "BTCUSDT",
    "side": "BUY",
    "quantity": 0.2,
    "fill_price": 50025.0,
    "commission": 10.005,
    "slippage": 25.0,
    "execution_mode": "paper",
    "created_at": "2026-03-30T12:00:00Z"
}
```

### GET /execution/orders

Historial de órdenes.

**Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| symbol | string | - | Filtrar por símbolo |
| status | string | - | filled, cancelled, pending |
| limit | int | 20 | Límite |
| offset | int | 0 | Offset |

### GET /execution/order/{id}

Detalle de una orden.

### DELETE /execution/order/{id}

Cancelar orden pendiente.

---

## Backtesting

### POST /backtest

Ejecutar backtest.

**Request:**
```http
POST /backtest
Authorization: Bearer <token>
Content-Type: application/json

{
    "strategy_id": "ema_rsi_v1",
    "symbol": "BTCUSDT",
    "from_ts": "2025-01-01T00:00:00",
    "to_ts": "2026-03-30T23:59:59",
    "walk_forward": true,
    "initial_capital": 10000.0
}
```

**Response 202:**
```json
{
    "job_id": "uuid",
    "status": "pending",
    "estimated_time": "60s"
}
```

### GET /backtest/{job_id}

Ver estado del job.

**Response 200:**
```json
{
    "job_id": "uuid",
    "status": "running",
    "progress": 0.45
}
```

### GET /backtest/{job_id}/results

Obtener resultados del backtest.

**Response 200:**
```json
{
    "job_id": "uuid",
    "strategy_id": "ema_rsi_v1",
    "symbol": "BTCUSDT",
    "period": {
        "from": "2025-01-01",
        "to": "2026-03-30"
    },
    "metrics": {
        "total_trades": 150,
        "winning_trades": 85,
        "losing_trades": 65,
        "win_rate": 0.567,
        "profit_factor": 1.85,
        "sharpe_ratio": 1.45,
        "sortino_ratio": 2.1,
        "max_drawdown": 0.15,
        "calmar_ratio": 1.2
    },
    "capital": {
        "initial": 10000.0,
        "final": 14500.0,
        "total_return": 0.45
    }
}
```

---

## Simulation

### POST /simulation/run

Ejecutar simulación histórica.

### GET /simulation/{run_id}

Estado de simulación.

### GET /simulation/{run_id}/results

Resultados de simulación.

---

## Marketplace

### GET /marketplace

Listar estrategias en marketplace.

### GET /marketplace/{id}

Detalle de estrategia en marketplace.

### POST /marketplace/publish

Publicar estrategia (admin only).

### POST /marketplace/{id}/subscribe

Suscribirse a una estrategia.

---

## Health & System

### GET /health

Health check del sistema.

**Response 200:**
```json
{
    "status": "ok",
    "version": "2.0.0",
    "execution_mode": "paper",
    "trading_enabled": false,
    "database": "connected",
    "redis": "connected"
}
```

### GET /metrics

Métricas Prometheus (puerto 8001).

---

*Volver al [índice de API](README.md)*
