# Códigos de Error

> Referencia de códigos de error y manejo

---

## Formato de Error

```json
{
    "detail": "Error description",
    "status_code": 400,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/api/endpoint"
}
```

---

## Códigos por Categoría

### 4xx - Client Errors

| Código | Nombre | Descripción |
|--------|--------|-------------|
| 400 | Bad Request | Parámetros inválidos o faltantes |
| 401 | Unauthorized | Token inválido o expirado |
| 403 | Forbidden | Sin permisos para este recurso |
| 404 | Not Found | Recurso no encontrado |
| 409 | Conflict | Conflicto con estado actual |
| 422 | Unprocessable Entity | Validación de datos fallida |
| 429 | Too Many Requests | Rate limit excedido |

### 5xx - Server Errors

| Código | Nombre | Descripción |
|--------|--------|-------------|
| 500 | Internal Server Error | Error interno del servidor |
| 502 | Bad Gateway | Exchange externo no disponible |
| 503 | Service Unavailable | Servicio temporalmente no disponible |

---

## Errores Detallados

### 400 Bad Request

```json
{
    "detail": "Invalid timeframe. Must be one of: 1m, 5m, 15m, 1h, 4h, 1d",
    "status_code": 400,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/market/candles/BTCUSDT"
}
```

**Causas comunes:**
- Parámetro `timeframe` inválido
- Formato de fecha incorrecto
- JSON malformado

### 401 Unauthorized

```json
{
    "detail": "Could not validate credentials",
    "status_code": 401,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/portfolio"
}
```

**Causas comunes:**
- Token no proporcionado
- Token expirado
- Token malformado

### 403 Forbidden

```json
{
    "detail": "Insufficient permissions. Required role: admin",
    "status_code": 403,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/risk/kill-switch/reset"
}
```

### 404 Not Found

```json
{
    "detail": "Strategy not found: unknown_strategy",
    "status_code": 404,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/strategies/unknown_strategy"
}
```

### 422 Unprocessable Entity

```json
{
    "detail": [
        {
            "loc": ["body", "entry_conditions"],
            "msg": "value is not a valid list",
            "type": "type_error.list"
        }
    ],
    "status_code": 422,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/strategies/custom"
}
```

### 429 Too Many Requests

```json
{
    "detail": "Rate limit exceeded. Try again in 60 seconds",
    "status_code": 429,
    "timestamp": "2026-03-30T12:00:00Z",
    "path": "/market/candles/BTCUSDT",
    "headers": {
        "X-RateLimit-Limit": "60",
        "X-RateLimit-Remaining": "0",
        "X-RateLimit-Reset": "1717123456"
    }
}
```

---

## Errores de Dominio

### Risk Errors

| Código | Error | Descripción |
|--------|-------|-------------|
| 400 | kill_switch_active | Kill switch activo, trading bloqueado |
| 400 | max_risk_exceeded | Exposición de riesgo al máximo |
| 400 | max_drawdown_reached | Drawdown máximo alcanzado |
| 400 | low_risk_reward | R:R ratio inferior al mínimo (1.5) |
| 400 | consecutive_losses | Máximo de pérdidas consecutivas |

### Strategy Errors

| Código | Error | Descripción |
|--------|-------|-------------|
| 404 | strategy_not_found | Estrategia no encontrada |
| 400 | invalid_conditions | Condiciones JSON inválidas |
| 409 | strategy_active | No puede eliminar estrategia activa |

### Execution Errors

| Código | Error | Descripción |
|--------|-------|-------------|
| 400 | order_not_found | Orden no encontrada |
| 400 | order_already_filled | Orden ya ejecutada |
| 502 | exchange_error | Error en exchange externo |

### Data Errors

| Código | Error | Descripción |
|--------|-------|-------------|
| 400 | insufficient_data | No hay suficientes datos históricos |
| 400 | market_closed | Mercado cerrado para este símbolo |
| 502 | data_provider_error | Error en proveedor de datos |

---

## Rate Limiting

### Límites por Endpoint

| Endpoint | Límite |
|----------|--------|
| POST /auth/login | 10/min |
| GET /market/* | 60/min |
| GET /signals/* | 30/min |
| POST /execution/* | 10/min |
| Default | 100/min |

### Headers de Rate Limit

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1717123456
```

### Manejo de Rate Limit

```javascript
async function fetchWithRetry(url, options, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
        const response = await fetch(url, options);
        
        if (response.status === 429) {
            const resetTime = response.headers.get('X-RateLimit-Reset');
            const waitTime = (resetTime * 1000) - Date.now();
            await sleep(waitTime);
            continue;
        }
        
        return response;
    }
    throw new Error('Max retries exceeded');
}
```

---

## Ejemplo de Manejo en Cliente

```javascript
async function apiCall(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Authorization': `Bearer ${getToken()}`,
                'Content-Type': 'application/json',
                ...options.headers
            }
        });
        
        if (!response.ok) {
            const error = await response.json();
            
            switch (response.status) {
                case 401:
                    // Redirigir a login
                    redirectToLogin();
                    break;
                case 429:
                    // Esperar y reintentar
                    await handleRateLimit(response);
                    break;
                default:
                    throw new Error(error.detail);
            }
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}
```

---

*Volver al [índice de API](README.md)*
