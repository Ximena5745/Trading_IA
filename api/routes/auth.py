"""
Module: api/routes/auth.py
Responsibility: Authentication endpoints — login, refresh, logout, me
Dependencies: jwt_handler, dependencies
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_current_user, get_jwt_handler
from core.auth.jwt_handler import JWTHandler

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory user store for MVP — replace with DB in production
_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "trader": {"password": "trader123", "role": "trader"},
    "viewer": {"password": "viewer123", "role": "viewer"},
}


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
    user = _USERS.get(body.username)
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=jwt.create_access_token(body.username, user["role"]),
        refresh_token=jwt.create_refresh_token(body.username),
        expires_in=3600,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, jwt: JWTHandler = Depends(get_jwt_handler)):
    user_id = jwt.decode_refresh(body.refresh_token)
    user = _USERS.get(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenResponse(
        access_token=jwt.create_access_token(user_id, user["role"]),
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
