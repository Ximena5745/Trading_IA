# Autenticación

> Sistema de autenticación JWT

---

## Flujo de Autenticación

```
┌─────────────────────────────────────────────────────────────────┐
│                 AUTHENTICATION FLOW                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Client                          Server                         │
│    │                               │                             │
│    │  POST /auth/login             │                             │
│    │  {username, password}         │                             │
│    │──────────────────────────────►│                             │
│    │                               │                             │
│    │                               │  Validate credentials      │
│    │                               │  Generate JWT token        │
│    │                               │                             │
│    │  200 OK                       │                             │
│    │  {access_token, expires_in}   │                             │
│    │◄──────────────────────────────│                             │
│    │                               │                             │
│    │  GET /portfolio               │                             │
│    │  Authorization: Bearer <jwt>  │                             │
│    │──────────────────────────────►│                             │
│    │                               │                             │
│    │                               │  Verify JWT signature      │
│    │                               │  Check expiration          │
│    │                               │  Extract user info         │
│    │                               │                             │
│    │  200 OK                       │                             │
│    │  {portfolio data}             │                             │
│    │◄──────────────────────────────│                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Endpoints

### POST /auth/login

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
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

**Error 401:**
```json
{
    "detail": "Invalid credentials"
}
```

### POST /auth/register

**Request:**
```http
POST /auth/register
Content-Type: application/json

{
    "username": "trader1",
    "email": "trader@example.com",
    "password": "securepass123"
}
```

**Response 201:**
```json
{
    "user_id": "uuid",
    "username": "trader1",
    "email": "trader@example.com",
    "role": "trader",
    "created_at": "2026-03-30T12:00:00Z"
}
```

### GET /auth/me

**Request:**
```http
GET /auth/me
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

**Response 200:**
```json
{
    "user_id": "uuid",
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin",
    "created_at": "2026-03-30T10:00:00Z"
}
```

---

## Token JWT

### Estructura

```
eyJhbGciOiJIUzI1NiJ9.        ← Header (algoritmo)
eyJzdWIiOiIxMjM0NTY3ODkwIiwi  ← Payload (claims)
bmFtZSI6IkpvaG4gRG9lIiwiaWF0
IjoxNTE2MjM5MDIyfQ.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c  ← Signature
```

### Payload

```json
{
    "sub": "user-uuid",
    "username": "admin",
    "role": "admin",
    "exp": 1717123456,
    "iat": 1717119856
}
```

### Expiración por Rol

| Rol | Expiración |
|-----|------------|
| admin | 24 horas |
| trader | 1 hora |

---

## Uso de Token

### En Request Headers

```http
GET /portfolio
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### Guardar en Cliente

```javascript
// localStorage
localStorage.setItem('access_token', token);

// En cada request
headers: {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
}
```

---

## Roles y Permisos

### Roles

| Rol | Descripción |
|-----|-------------|
| admin | Acceso total, puede resetear kill switch |
| trader | Acceso operativo, ejecutar órdenes |
| viewer | Solo lectura |

### Permisos por Endpoint

| Endpoint | admin | trader | viewer |
|----------|-------|--------|--------|
| GET /* | ✅ | ✅ | ✅ |
| POST /auth/login | ✅ | ✅ | ✅ |
| POST /execution/order | ✅ | ✅ | ❌ |
| POST /strategies/custom | ✅ | ❌ | ❌ |
| PATCH /strategies/*/status | ✅ | ❌ | ❌ |
| POST /risk/kill-switch/* | ✅ | ❌ | ❌ |
| DELETE /portfolio/positions/* | ✅ | ✅ | ❌ |

---

## Token Refresh

```http
POST /auth/refresh
Authorization: Bearer <old_token>

Response:
{
    "access_token": "<new_token>",
    "expires_in": 3600
}
```

---

## Errores de Autenticación

| Código | Mensaje | Causa |
|--------|---------|-------|
| 401 | Invalid credentials | Username/password incorrecto |
| 401 | Token expired | Token expirado |
| 401 | Invalid token | Token malformado o inválido |
| 403 | Insufficient permissions | Rol no tiene permiso |

---

*Volver al [índice de API](README.md)*
