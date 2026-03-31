# REST API Routes

> Documentación completa de todos los endpoints FastAPI

## Información General

| Propiedad | Valor |
|-----------|-------|
| Base URL | `http://localhost:8000` |
| Version | 2.0.0 |
| Auth | JWT Bearer Token |
| Rate Limit | 100 req/min (default) |
| Docs | `/docs` (Swagger UI) |

---

## Endpoints por Módulo

### 🔐 Autenticación (`/auth`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/auth/login` | Login y obtener token |
| POST | `/auth/register` | Registrar usuario |
| GET | `/auth/me` | Obtener usuario actual |

#### Login

```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}

Response 200:
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

---

### 📊 Market Data (`/market`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/market/candles/{symbol}` | OHLCV histórico |
| GET | `/market/quote/{symbol}` | Precio actual |
| GET | `/market/orderbook/{symbol}` | Order book |

#### Obtener Velas

```http
GET /market/candles/BTCUSDT?timeframe=1h&limit=100
Authorization: Bearer <token>

Response 200:
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

#### Obtener Quote

```http
GET /market/quote/EURUSD
Authorization: Bearer <token>

Response 200:
{
    "symbol": "EURUSD",
    "bid": 1.0850,
    "ask": 1.0852,
    "timestamp": "2026-03-30T12:00:00Z"
}
```

---

### 📡 Señales (`/signals`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/signals` | Listar señales |
| GET | `/signals/{id}` | Detalle de señal |
| GET | `/signals/latest` | Última señal |
| GET | `/signals/stats` | Estadísticas de señales |

#### Listar Señales

```http
GET /signals?symbol=BTCUSDT&status=pending&limit=20
Authorization: Bearer <token>

Response 200:
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
            "explanation": [
                {
                    "factor": "RSI_14",
                    "weight": 0.35,
                    "direction": "BUY",
                    "description": "RSI en sobreventa (28)"
                }
            ],
            "summary": "Señal BUY por cruce EMA + RSI sobreventa"
        }
    ],
    "total": 45,
    "page": 1
}
```

#### Estadísticas

```http
GET /signals/stats?period=7d
Authorization: Bearer <token>

Response 200:
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

### 📈 Estrategias (`/strategies`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/strategies` | Listar estrategias |
| GET | `/strategies/{id}` | Detalle de estrategia |
| POST | `/strategies/custom` | Crear estrategia custom |
| PATCH | `/strategies/{id}/status` | Cambiar estado |
| DELETE | `/strategies/{id}` | Eliminar estrategia |

#### Listar Estrategias

```http
GET /strategies
Authorization: Bearer <token>

Response 200:
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
            "max_capital_pct": 0.20,
            "risk_per_trade_pct": 0.01,
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

#### Crear Estrategia Custom

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

Response 201:
{
    "strategy_id": "my_custom_v1",
    "status": "active",
    "created_at": "2026-03-30T12:00:00Z"
}
```

#### Cambiar Estado

```http
PATCH /strategies/ema_rsi_v1/status
Authorization: Bearer <token>
Content-Type: application/json

{
    "status": "paused"
}

Response 200:
{
    "strategy_id": "ema_rsi_v1",
    "previous_status": "active",
    "new_status": "paused",
    "updated_at": "2026-03-30T12:00:00Z"
}
```

---

### 💼 Portfolio (`/portfolio`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/portfolio` | Estado del portafolio |
| GET | `/portfolio/positions` | Posiciones abiertas |
| DELETE | `/portfolio/positions/{symbol}` | Cerrar posición |

#### Estado del Portafolio

```http
GET /portfolio
Authorization: Bearer <token>

Response 200:
{
    "id": "uuid",
    "total_capital": 10500.0,
    "available_capital": 7500.0,
    "positions": [
        {
            "symbol": "BTCUSDT",
            "quantity": 0.05,
            "entry_price": 50000.0,
            "current_price": 52000.0,
            "unrealized_pnl": 100.0,
            "unrealized_pnl_pct": 0.04,
            "strategy_id": "ema_rsi_v1"
        }
    ],
    "risk_exposure": 0.08,
    "daily_pnl": 150.0,
    "total_pnl": 500.0,
    "drawdown_current": 0.02,
    "drawdown_max": 0.05
}
```

---

### ⚠️ Risk (`/risk`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/risk/status` | Estado del riesgo |
| POST | `/risk/kill-switch/trigger` | Activar kill switch |
| POST | `/risk/kill-switch/reset` | Reset kill switch |

#### Estado del Riesgo

```http
GET /risk/status
Authorization: Bearer <token>

Response 200:
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

#### Reset Kill Switch

```http
POST /risk/kill-switch/reset
Authorization: Bearer <admin_token>

Response 200:
{
    "status": "reset",
    "reset_by": "admin",
    "reset_at": "2026-03-30T12:00:00Z"
}
```

---

### 🔁 Backtesting (`/backtest`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/backtest` | Ejecutar backtest |
| GET | `/backtest/{job_id}` | Estado del job |
| GET | `/backtest/{job_id}/results` | Resultados |

#### Ejecutar Backtest

```http
POST /backtest
Authorization: Bearer <token>
Content-Type: application/json

{
    "strategy_id": "ema_rsi_v1",
    "symbol": "BTCUSDT",
    "from_ts": "2025-01-01T00:00:00",
    "to_ts": "2026-03-30T23:59:59",
    "walk_forward": true
}

Response 202:
{
    "job_id": "uuid",
    "status": "pending",
    "estimated_time": "60s"
}
```

#### Obtener Resultados

```http
GET /backtest/{job_id}/results
Authorization: Bearer <token>

Response 200:
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
    },
    "windows": [
        {
            "window": 0,
            "train_size": 500,
            "test_size": 100,
            "sharpe_ratio": 1.2
        }
    ]
}
```

---

### ⚙️ Ejecución (`/execution`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/execution/order` | Ejecutar orden |
| GET | `/execution/orders` | Historial de órdenes |
| GET | `/execution/order/{id}` | Detalle de orden |
| DELETE | `/execution/order/{id}` | Cancelar orden |

---

### 📊 Simulación (`/simulation`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/simulation/run` | Ejecutar simulación |
| GET | `/simulation/{run_id}` | Estado de simulación |
| GET | `/simulation/{run_id}/results` | Resultados |

---

### 🛒 Marketplace (`/marketplace`)

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/marketplace` | Listar estrategias en marketplace |
| GET | `/marketplace/{id}` | Detalle de estrategia |
| POST | `/marketplace/publish` | Publicar estrategia |
| POST | `/marketplace/{id}/subscribe` | Suscribirse a estrategia |

---

## Sistema de Autenticación

### Obtener Token

```http
POST /auth/login
Content-Type: application/json

{
    "username": "admin",
    "password": "admin123"
}
```

### Usar Token

```http
GET /portfolio
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Token Expiración

| Rol | Expiración |
|-----|------------|
| admin | 24 horas |
| trader | 1 hora |

---

## Rate Limiting

### Límites por Endpoint

| Endpoint | Límite |
|----------|--------|
| `/auth/login` | 10 req/min |
| `/market/*` | 60 req/min |
| `/signals/*` | 30 req/min |
| `/strategies/*` | 20 req/min |
| `/execution/*` | 10 req/min |
| Default | 100 req/min |

### Headers de Rate Limit

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1617123456
```

---

## Errores

### Formato de Error

```json
{
    "detail": "Error message",
    "status_code": 400,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/endpoint"
}
```

### Códigos de Error Comunes

| Código | Descripción |
|--------|-------------|
| 400 | Bad Request - Parámetros inválidos |
| 401 | Unauthorized - Token inválido o expirado |
| 403 | Forbidden - Sin permisos |
| 404 | Not Found - Recurso no encontrado |
| 429 | Too Many Requests - Rate limit excedido |
| 500 | Internal Server Error |

---

## WebSocket (Futuro)

### Señales en Tiempo Real

```javascript
ws://localhost:8000/ws/signals

// Mensajes recibidos:
{
    "type": "signal",
    "data": {
        "symbol": "BTCUSDT",
        "action": "BUY",
        "confidence": 0.75
    }
}
```

---

*Volver al [índice de integración técnica](README.md)*
