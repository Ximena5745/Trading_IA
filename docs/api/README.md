# API Contracts & Reference

> Documentación completa de endpoints, contratos y especificaciones

---

## 1. API OVERVIEW

### 1.1 Base URL

```
Development: http://localhost:8000
Production:  https://api.trader-ai.example.com
```

### 1.2 Authentication

```bash
# JWT Bearer Token
Authorization: Bearer <token>

# API Key
X-API-Key: <api_key>
```

### 1.3 Response Format

```json
{
  "data": { ... },
  "meta": {
    "timestamp": "2026-05-16T10:30:00Z",
    "request_id": "req_abc123"
  }
}
```

### 1.4 Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid parameters",
    "details": [
      {"field": "symbol", "message": "Invalid symbol"}
    ]
  }
}
```

---

## 2. ENDPOINTS

### 2.1 Authentication

#### POST /auth/login

```bash
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "..."}'
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

#### POST /auth/refresh

```bash
curl -X POST http://localhost:8000/auth/refresh \
  -H "Authorization: Bearer <old_token>"
```

#### POST /auth/logout

```bash
curl -X POST http://localhost:8000/auth/logout \
  -H "Authorization: Bearer <token>"
```

---

### 2.2 Market Data

#### GET /market/candles/{symbol}

```bash
curl "http://localhost:8000/market/candles/BTCUSDT?interval=1h&limit=100" \
  -H "Authorization: Bearer <token>"
```

**Parameters:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| symbol | str | Yes | Symbol (BTCUSDT, EURUSD) |
| interval | str | Yes | 1m, 5m, 15m, 1h, 4h, 1d |
| start | datetime | No | Start time |
| end | datetime | No | End time |
| limit | int | No | Max candles (default 100) |

**Response:**
```json
{
  "data": {
    "symbol": "BTCUSDT",
    "interval": "1h",
    "candles": [
      {
        "timestamp": "2026-05-16T10:00:00Z",
        "open": 45000.0,
        "high": 45200.0,
        "low": 44800.0,
        "close": 45100.0,
        "volume": 1234.5
      }
    ]
  }
}
```

#### GET /market/orderbook/{symbol}

```bash
curl "http://localhost:8000/market/orderbook/BTCUSDT?limit=20" \
  -H "Authorization: Bearer <token>"
```

---

### 2.3 Signals

#### GET /signals

```bash
curl "http://localhost:8000/signals?symbol=BTCUSDT&status=pending&limit=50" \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "data": {
    "signals": [
      {
        "id": "sig_123",
        "symbol": "BTCUSDT",
        "action": "BUY",
        "entry_price": 45100.0,
        "stop_loss": 44000.0,
        "take_profit": 47000.0,
        "confidence": 0.78,
        "status": "pending",
        "created_at": "2026-05-16T10:30:00Z"
      }
    ]
  }
}
```

#### POST /signals

```bash
curl -X POST http://localhost:8000/signals \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "BTCUSDT",
    "action": "BUY",
    "entry_price": 45100.0,
    "stop_loss": 44000.0,
    "take_profit": 47000.0,
    "confidence": 0.8
  }'
```

---

### 2.4 Execution

#### POST /execution/order

```bash
curl -X POST http://localhost:8000/execution/order \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "signal_id": "sig_123",
    "quantity": 0.1,
    "execution_mode": "paper"
  }'
```

**Response:**
```json
{
  "data": {
    "order_id": "ord_456",
    "status": "filled",
    "fill_price": 45100.0,
    "commission": 0.0
  }
}
```

#### GET /execution/orders

```bash
curl "http://localhost:8000/execution/orders?status=open" \
  -H "Authorization: Bearer <token>"
```

#### DELETE /execution/orders/{order_id}

```bash
curl -X DELETE http://localhost:8000/execution/orders/ord_456 \
  -H "Authorization: Bearer <token>"
```

---

### 2.5 Portfolio

#### GET /portfolio

```bash
curl http://localhost:8000/portfolio \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "data": {
    "total_value": 10500.0,
    "available_capital": 5000.0,
    "positions_value": 5500.0,
    "daily_pnl": 150.0,
    "total_pnl": 500.0,
    "drawdown": 0.02,
    "positions": [
      {
        "symbol": "BTCUSDT",
        "side": "LONG",
        "quantity": 0.1,
        "entry_price": 45000.0,
        "current_price": 45500.0,
        "unrealized_pnl": 50.0
      }
    ]
  }
}
```

#### GET /portfolio/history

```bash
curl "http://localhost:8000/portfolio/history?from=2026-01-01&to=2026-05-16" \
  -H "Authorization: Bearer <token>"
```

---

### 2.6 Risk

#### GET /risk/status

```bash
curl http://localhost:8000/risk/status \
  -H "Authorization: Bearer <token>"
```

**Response:**
```json
{
  "data": {
    "kill_switch_active": false,
    "daily_loss_pct": 0.02,
    "drawdown_pct": 0.05,
    "consecutive_losses": 2,
    "max_risk_per_trade": 0.02,
    "current_risk": 0.015
  }
}
```

#### POST /risk/kill-switch

```bash
curl -X POST http://localhost:8000/risk/kill-switch \
  -H "Authorization: Bearer <token>" \
  -d '{"action": "activate", "reason": "Manual intervention"}'
```

---

### 2.7 Backtesting

#### POST /backtesting/run

```bash
curl -X POST http://localhost:8000/backtesting/run \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_id": "ema_rsi",
    "symbol": "BTCUSDT",
    "from": "2025-01-01",
    "to": "2025-12-31",
    "initial_capital": 10000
  }'
```

**Response:**
```json
{
  "data": {
    "backtest_id": "bt_123",
    "status": "running",
    "progress": 0.45
  }
}
```

#### GET /backtesting/{backtest_id}

```bash
curl http://localhost:8000/backtesting/bt_123 \
  -H "Authorization: Bearer <token>"
```

---

## 3. ERROR CODES

### 3.1 HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 422 | Validation Error |
| 429 | Rate Limited |
| 500 | Internal Error |
| 503 | Service Unavailable |

### 3.2 Application Error Codes

| Code | Description |
|------|-------------|
| VALIDATION_ERROR | Invalid input parameters |
| AUTH_ERROR | Authentication failed |
| PERMISSION_DENIED | Not authorized |
| NOT_FOUND | Resource not found |
| DUPLICATE | Resource already exists |
| RATE_LIMITED | Too many requests |
| RISK_REJECTED | Risk validation failed |
| EXECUTION_ERROR | Order execution failed |

---

## 4. RATE LIMITS

| Endpoint | Limit |
|----------|-------|
| /auth/login | 10/min |
| /market/candles | 60/min |
| /signals | 30/min |
| /execution/* | 10/min |
| Default | 100/min |

---

## 5. VERSIONING

### 5.1 API Versioning

```
URL: /api/v1/...
Header: Accept: application/vnd.trader-ai.v1+json
```

### 5.2 Deprecation Policy

- Deprecated endpoints: 12 months notice
- Migration guide provided
- Legacy support during transition

---

*Volver al [INDEX](INDEX.md)*