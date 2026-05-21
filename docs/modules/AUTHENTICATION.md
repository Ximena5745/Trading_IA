# Módulo: Authentication & Authorization

> Sistema de autenticación JWT y control de acceso (RBAC)

---

## 1. OBJETIVO

Proveer un sistema de seguridad robusto con autenticación JWT, autorización basada en roles, y gestión de API keys para acceso programático.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|----------------|-------------|
| JWT authentication | Login, token generation, validation |
| RBAC | Role-based access control |
| API key management | Keys para acceso programático |
| Permissions | Sistema de permisos granular |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    JWTAuthHandler                         │ │
│  │  - Token generation                                       │ │
│  │  - Token validation                                       │ │
│  │  - Token refresh                                          │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┼───────────────────────────────────┐  │
│  │                  RBACEngine                               │ │
│  │  - Role management                                        │ │
│  │  - Permission checks                                      │ │
│  │  - Decorators                                             │ │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                      │
│  ┌──────────────────────┴───────────────────────────────────┐  │
│  │                   APIKeyManager                           │  │
│  │  - Key generation                                         │  │
│  │  - Key validation                                          │  │
│  │  - Key rotation                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 JWTAuthHandler

**Archivo:** `core/auth/jwt_handler.py`

**Configuración:**
```python
# .env
JWT_SECRET_KEY=<64-char-random-string>
JWT_ALGORITHM=HS256

# Tiempos de expiración por rol
JWT_ACCESS_TOKEN_EXPIRE = {
    "admin": 24 * 60 * 60,   # 24 horas
    "trader": 60 * 60,       # 1 hora
    "viewer": 30 * 60,       # 30 minutos
}
```

**Generación de token:**
```python
def create_access_token(
    data: dict,
    role: str
) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(
        seconds=JWT_ACCESS_TOKEN_EXPIRE[role]
    )
    to_encode.update({"exp": expire, "role": role})
    
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )
```

**Validación de token:**
```python
def verify_token(token: str) -> TokenData:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return TokenData(**payload)
    except jwt.ExpiredSignatureError:
        raise AuthError("Token expired")
    except jwt.InvalidTokenError:
        raise AuthError("Invalid token")
```

### 4.2 RBACEngine

**Archivo:** `core/auth/permissions.py`

**Roles definidos:**
| Rol | Permisos |
|-----|----------|
| admin | todo:read, todo:write, strategies:*, execution:*, risk:*, kill_switch:* |
| trader | market:read, signals:read, signals:write, portfolio:*, execution:trade |
| viewer | market:read, signals:read, portfolio:read |

**Permisos granulares:**
```python
PERMISSIONS = {
    "admin": [
        "market:read", "market:write",
        "signals:read", "signals:write",
        "portfolio:read", "portfolio:write",
        "execution:read", "execution:write",
        "strategies:read", "strategies:write",
        "risk:read", "risk:write",
        "kill_switch:trigger",
        "admin:*",
    ],
    "trader": [
        "market:read",
        "signals:read", "signals:write",
        "portfolio:read", "portfolio:write",
        "execution:read", "execution:trade",
    ],
    "viewer": [
        "market:read",
        "signals:read",
        "portfolio:read",
    ],
}
```

**Decoradores de autorización:**
```python
from api.dependencies import require_admin, require_trader, require_permission

@router.post("/strategies")
@require_admin  # Solo admin
async def create_strategy(...): ...

@router.post("/execution/order")
@require_permission("execution:trade")  # Requiere permiso específico
async def execute_order(...): ...
```

### 4.3 APIKeyManager

**Archivo:** `core/auth/api_key_manager.py`

**Propósito:** Acceso programático sin JWT.

```python
class APIKeyManager:
    async def create_key(
        self,
        user_id: str,
        name: str,
        permissions: list[str],
        expires_at: datetime | None = None
    ) -> APIKey:
        key = generateSecureKey()
        hashed = hash_key(key)
        
        await self._store(
            user_id=user_id,
            key_hash=hashed,
            name=name,
            permissions=permissions,
            expires_at=expires_at
        )
        
        return APIKey(id=..., key=key, ...)  # Solo se devuelve una vez
    
    async def validate_key(
        self,
        key: str
    ) -> APIKeyInfo | None:
        hashed = hash_key(key)
        return await self._get_by_hash(hashed)
```

**Uso de API Key:**
```python
# Header: X-API-Key: <key>
headers = {"X-API-Key": "tk_live_..."}
response = await client.get("/market/candles/BTCUSDT", headers=headers)
```

---

## 5. SECURITY CONFIGURATION

### 5.1 Dependency Injection

**Archivo:** `api/dependencies.py`

```python
from fastapi import Depends, HTTPException, status

async def get_current_user(
    token: str = Depends(reusable_oauth2)
) -> User:
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        user = await user_repository.get(payload["sub"])
        if not user:
            raise HTTPException(status_code=401)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")

async def require_admin(
    user: User = Depends(get_current_user)
) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    return user
```

### 5.2 Password Requirements

```python
# Mínimo:
# - 8 caracteres
# - 1 mayúscula
# - 1 minúscula
# - 1 número
# - 1 special char
```

---

## 6. EVENTOS

### 6.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `auth.login` | Login exitoso | `{user, ip}` |
| `auth.login_failed` | Login fallido | `{user, reason, ip}` |
| `auth.logout` | Logout | `{user}` |
| `auth.token_created` | Token creado | `{user, role, expires}` |
| `auth.api_key_created` | API key creada | `{user, key_id}` |
| `auth.api_key_revoked` | API key revocada | `{key_id}` |

### 6.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| (ninguno) | Eventos source |

---

## 7. INPUTS/OUTPUTS

### 7.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| Credentials | dict | username + password |
| Token | str | JWT token |
| API Key | str | API key |

### 7.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| Access token | Client | JWT token |
| User info | Client | User data |
| Permissions | Service | Permisos |

---

## 8. SEGURIDAD ADICIONAL

### 8.1 Rate Limiting

```python
# Por endpoint
@router.post("/auth/login")
@limiter.limit("10/minute")
async def login(...): ...

@router.get("/market/*")
@limiter.limit("60/minute")
async def get_market_data(...): ...
```

### 8.2 CORS

```python
# config
CORS_ORIGINS = [
    "http://localhost:3000",
    "https://trader-ai.example.com",
]
```

---

## 9. OBSERVABILIDAD

### 9.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `auth.login.total` | Counter | Login attempts |
| `auth.login.failed` | Counter | Failed attempts |
| `auth.token.created` | Counter | Tokens created |
| `auth.api_key.usage` | Counter | API key usage |

### 9.2 Logs

```json
{
  "event": "login_success",
  "user": "admin",
  "ip": "192.168.1.100",
  "role": "admin"
}
```

```json
{
  "event": "login_failed",
  "user": "admin",
  "reason": "invalid_password",
  "ip": "192.168.1.100"
}
```

---

## 10. RIESGOS

| Riesgo | Mitigación |
|--------|-------------|
| JWT secret weak | Generar con OpenSSL |
| Token leak | Expiración corta + HTTPS |
| Brute force | Rate limiting |
| API key leak | Rotation policy |

---

## 11. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_token_generation | Unit | 90% |
| test_token_validation | Unit | 90% |
| test_rbac | Unit | 90% |
| test_api_keys | Unit | 80% |

---

## 12. EJEMPLOS DE USO

```python
# Login
response = await client.post("/auth/login", json={
    "username": "admin",
    "password": "..."
})
token = response.json()["access_token"]

# Usar token
headers = {"Authorization": f"Bearer {token}"}
response = await client.get("/portfolio", headers=headers)
```

---

## 13. KPIs

| KPI | Target |
|-----|--------|
| Login success rate | > 90% |
| Token validation time | < 5ms |
| Uptime | 99.9% |

---

*Volver al [INDEX](../INDEX.md)*