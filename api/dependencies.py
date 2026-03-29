"""
Module: api/dependencies.py
Responsibility: FastAPI dependency injection — auth, db session, rate limiter
Dependencies: jwt_handler, permissions, settings
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from core.auth.jwt_handler import JWTHandler
from core.auth.permissions import Role, has_permission
from core.config.settings import get_settings
from core.exceptions import AuthenticationError

settings = get_settings()
_jwt_handler = JWTHandler(
    secret_key=settings.JWT_SECRET_KEY,
    algorithm=settings.JWT_ALGORITHM,
    expire_minutes=settings.JWT_EXPIRE_MINUTES,
)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = _jwt_handler.decode(credentials.credentials)
        return {"user_id": payload["sub"], "role": payload["role"]}
    except AuthenticationError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


async def require_trader(user: dict = Depends(get_current_user)) -> dict:
    if not has_permission(user["role"], Role.TRADER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Trader role required")
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not has_permission(user["role"], Role.ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def get_jwt_handler() -> JWTHandler:
    return _jwt_handler
