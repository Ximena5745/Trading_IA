"""
Module: api/routes/auth.py
Responsibility: Authentication endpoints — login, refresh, logout, me
Dependencies: jwt_handler, dependencies
"""

from __future__ import annotations

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_current_user, get_jwt_handler
from core.auth.jwt_handler import JWTHandler

router = APIRouter(prefix="/auth", tags=["auth"])

_PASSWORDS: dict[str, str] = {
    "admin": bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode(),
    "trader": bcrypt.hashpw(b"trader123", bcrypt.gensalt()).decode(),
    "viewer": bcrypt.hashpw(b"viewer123", bcrypt.gensalt()).decode(),
}

_ROLES: dict[str, str] = {
    "admin": "admin",
    "trader": "trader",
    "viewer": "viewer",
}


def verify_password(username: str, password: str) -> bool:
    if username not in _PASSWORDS:
        return False
    return bcrypt.checkpw(password.encode(), _PASSWORDS[username].encode())


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, jwt: JWTHandler = Depends(get_jwt_handler)):
    user_role = _ROLES.get(body.username)
    if not user_role or not verify_password(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    return TokenResponse(
        access_token=jwt.create_access_token(body.username, user_role),
        refresh_token=jwt.create_refresh_token(body.username),
        expires_in=3600,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, jwt: JWTHandler = Depends(get_jwt_handler)):
    user_id = jwt.decode_refresh(body.refresh_token)
    user_role = _ROLES.get(user_id)
    if not user_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return TokenResponse(
        access_token=jwt.create_access_token(user_id, user_role),
        refresh_token=jwt.create_refresh_token(user_id),
        expires_in=3600,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    # JWT is stateless — client discards token
    return None


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
