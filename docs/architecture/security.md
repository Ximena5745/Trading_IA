# Arquitectura de Seguridad

> Medidas de seguridad implementadas en el sistema

---

## Resumen de Seguridad

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      SECURITY ARCHITECTURE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      NETWORK LAYER                                  │   │
│  │  • HTTPS (Nginx + Let's Encrypt)                                    │   │
│  │  • Firewall (solo puertos 80, 443, SSH)                             │   │
│  │  • Rate Limiting (slowapi)                                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    APPLICATION LAYER                                │   │
│  │  • JWT Authentication                                               │   │
│  │  • Role-Based Access Control (RBAC)                                 │   │
│  │  • Input Validation (Pydantic)                                      │   │
│  │  • CORS Whitelist                                                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                      DATA LAYER                                     │   │
│  │  • Secrets in Environment Variables                                 │   │
│  │  • No API Keys in Code                                              │   │
│  │  • Database Credentials Encrypted                                   │   │
│  │  • TLS for DB Connections                                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    │                                        │
│                                    ▼                                        │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                   TRADING SAFETY                                    │   │
│  │  • Paper Mode by Default                                            │   │
│  │  • Kill Switch (Emergency Stop)                                     │   │
│  │  • Risk Limits (Hard-coded)                                         │   │
│  │  • Idempotency Keys                                                 │   │
│  │  • Double-Check for Live Mode                                       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Autenticación

### JWT Configuration

```python
# Configuración JWT
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")  # 64+ chars aleatorios
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE = {
    "admin": 24 * 60 * 60,  # 24 horas
    "trader": 60 * 60,       # 1 hora
}
```

### Generar Secret Key

```bash
# Generar clave segura
openssl rand -hex 32
```

---

## Control de Acceso (RBAC)

### Roles

| Rol | Permisos |
|-----|----------|
| admin | Todo + Kill Switch + Estrategias |
| trader | Trading + Portfolio + Lectura |
| viewer | Solo lectura |

### Decorators

```python
from api.dependencies import require_admin, require_trader

@router.post("/strategies/custom")
async def create_strategy(user: dict = Depends(require_admin)):
    # Solo admin puede crear estrategias
    pass

@router.post("/execution/order")
async def execute_order(user: dict = Depends(require_trader)):
    # Trader puede ejecutar órdenes
    pass
```

---

## Rate Limiting

### Configuración

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Por endpoint
@router.get("/market/candles/{symbol}")
@limiter.limit("60/minute")
async def get_candles(request: Request):
    pass
```

### Límites

| Endpoint | Límite |
|----------|--------|
| /auth/login | 10/min |
| /market/* | 60/min |
| /signals/* | 30/min |
| /execution/* | 10/min |
| Default | 100/min |

---

## Seguridad de Trading

### Paper Mode por Defecto

```env
# .env por defecto - MODO PAPEL
EXECUTION_MODE=paper
TRADING_ENABLED=false
BINANCE_TESTNET=true
```

### Doble Verificación para Live

```python
# En LiveExecutor
async def execute(self, signal: dict, quantity: float) -> dict:
    # Guard 1: Modo debe ser 'live'
    if self._settings.EXECUTION_MODE != "live":
        raise ExecutionError("Not in live mode")
    
    # Guard 2: Trading habilitado
    if not self._settings.TRADING_ENABLED:
        raise ExecutionError("Trading disabled")
    
    # Guard 3: Kill switch inactivo
    if self._kill_switch.is_active():
        raise ExecutionError("Kill switch active")
    
    # Guard 4: Testnet deshabilitado
    if self._settings.BINANCE_TESTNET:
        raise ExecutionError("Testnet mode - cannot execute live")
```

### Kill Switch

```python
class KillSwitch:
    """
    Freno de emergencia que detiene TODO trading.
    
    Triggers:
    - Pérdida diaria > 10%
    - Drawdown > 20%
    - 7+ pérdidas consecutivas
    - Manual (admin only)
    
    Reset:
    - daily_loss: automático a medianoche
    - consecutive: automático tras 1 win
    - drawdown: solo manual
    - manual: solo manual
    """
```

### Hard Limits (No Modificables)

```python
# core/config/constants.py
HARD_LIMITS = {
    "max_risk_per_trade_pct": 0.02,
    "max_portfolio_risk_pct": 0.15,
    "max_daily_loss_pct": 0.10,
    "max_drawdown_pct": 0.20,
    "max_consecutive_losses": 7,
    "min_risk_reward_ratio": 1.5,
}
```

> Estos límites solo pueden modificarse con code review.

---

## Protección de Datos

### Variables de Entorno

```bash
# Nunca commitear .env
echo ".env" >> .gitignore

# Usar .env.example como plantilla
cp .env.example .env
nano .env  # Editar valores
```

### Secrets que Nunca Deben ser Loggeados

- JWT_SECRET_KEY
- BINANCE_SECRET_KEY
- MT5_PASSWORD
- DATABASE_URL
- TELEGRAM_BOT_TOKEN

### Logging Seguro

```python
# MAL - expone secrets
logger.info(f"Connecting with key: {api_key}")

# BIEN - enmascara secrets
logger.info(f"Connecting with key: {api_key[:8]}...")
```

---

## Validación de Input

### Pydantic Validation

```python
class BacktestRequest(BaseModel):
    strategy_id: str
    symbol: str
    from_ts: datetime
    to_ts: datetime
    
    @model_validator(mode="after")
    def validate_dates(self):
        if self.to_ts <= self.from_ts:
            raise ValueError("to_ts must be after from_ts")
        return self
```

### SQL Injection Prevention

```python
# MAL - vulnerable
query = f"SELECT * FROM signals WHERE symbol = '{symbol}'"

# BIEN - parameterized
query = "SELECT * FROM signals WHERE symbol = :symbol"
result = await session.execute(query, {"symbol": symbol})
```

---

## Seguridad en Producción

### Checklist

- [ ] HTTPS configurado (Let's Encrypt)
- [ ] Firewall activo (solo 80, 443, SSH)
- [ ] JWT_SECRET_KEY rotado regularmente
- [ ] Rate limiting activo
- [ ] CORS restringido a dominios específicos
- [ ] Grafana password cambiada
- [ ] SSH con key authentication (no password)
- [ ] Fail2ban configurado
- [ ] Logs auditados regularmente

### Configuración Nginx

```nginx
server {
    listen 443 ssl;
    server_name trader-ai.example.com;
    
    ssl_certificate /etc/letsencrypt/live/trader-ai.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/trader-ai.example.com/privkey.pem;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    
    location / {
        proxy_pass http://localhost:8000;
    }
}
```

---

## Auditoría

### Eventos Auditados

| Evento | Nivel | Descripción |
|--------|-------|-------------|
| Login | INFO | Intento de login |
| Login Failed | WARN | Login fallido |
| Kill Switch | WARN | Activación/desactivación |
| Order Executed | INFO | Orden ejecutada |
| Strategy Created | INFO | Nueva estrategia |
| Admin Action | INFO | Acciones de admin |

### Ejemplo de Log

```json
{
    "event": "login_success",
    "username": "admin",
    "ip": "192.168.1.100",
    "timestamp": "2026-03-30T12:00:00Z",
    "user_agent": "Mozilla/5.0..."
}
```

---

*Volver al [índice de arquitectura](README.md)*
