# SPEC — Authentication System
**Fecha:** 2026-05-16 | **Versión:** 1.0 | **Estado:** DRAFT

---

## 1. RESUMEN EJECUTIVO

Sistema de autenticación JWT con validación de tokens, blacklist para logout efectivo, y control de acceso basado en roles (RBAC). Implementa los principios de seguridad del Prompt Maestro.

**Pertenece a:** Fase 1 - Secure Core Foundation | **Depende de:** SPEC-001 (Domain Entities)
**Blode:** M1.3 (Auth completa)

---

## 2. OBJETIVOS

| # | Objetivo | Métrica de éxito |
|---|----------|------------------|
| O1 | JWT con validación real (no `and False`) | Tokens inválidos son rechazados |
| O2 | Token blacklist para logout | Logout efectivo |
| O3 | RBAC con roles granulares | admin/trader/viewer |
| O4 | Rate limiting en /auth/login | Max 5 req/min |
| O5 | POST /auth/register implementado | Registro de usuarios |

---

## 3. ESPECIFICACIÓN TÉCNICA

### 3.1 Interfaz pública

```python
class AuthService:
    async def authenticate(self, username: str, password: str) -> TokenPair:
        """Autentica usuario y retorna tokens JWT."""
        ...

    async def verify_token(self, token: str) -> dict:
        """Verifica token JWT."""
        ...

    async def blacklist_token(self, token: str) -> None:
        """Añade token a blacklist."""
        ...

    async def register(self, username: str, password: str, role: str) -> User:
        """Registra nuevo usuario."""
        ...

class RBAC:
    def require_role(self, roles: list[str]) -> Callable:
        """Dependency para endpoints con roles específicos."""
        ...
```

### 3.2 Roles

| Rol | Permisos |
|-----|-----------|
| admin | Leer, escribir, ejecutar, gestionar usuarios, gestionar risk |
| trader | Leer, escribir, ejecutar, ver portfolio |
| viewer | Solo lectura |

### 3.3 Endpoints

| Endpoint | Método | Rol requerido |
|----------|--------|----------------|
| /auth/login | POST | Público |
| /auth/register | POST | Público |
| /auth/logout | POST | Cualquiera |
| /execution | POST | trader, admin |
| /risk/kill-switch/activate | POST | admin |
| /portfolio | GET | trader, admin, viewer |

---

## 4. CRITERIOS DE ACEPTACIÓN

| ID | Criterio | Test asociado |
|----|----------|---------------|
| CA-1 | JWT con secret real valida correctamente | tests/unit/test_auth.py::test_jwt_validation |
| CA-2 | Tokens en blacklist son rechazados | tests/unit/test_auth.py::test_blacklist |
| CA-3 | Roles tienen permisos correctos | tests/unit/test_auth.py::test_rbac |
| CA-4 | Rate limiting activo en /auth/login | tests/unit/test_auth.py::test_rate_limit |
| CA-5 | Registro crea usuario correctamente | tests/integration/test_auth.py::test_register |

---

## 5. TRAZABILIDAD

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-05-16 | Versión inicial | TRADER AI |

**ESTADO:** APPROVED