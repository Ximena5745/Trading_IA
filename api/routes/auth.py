"""
Module: api/routes/auth.py
Responsibility: Authentication endpoints — login, refresh, logout, me.
  Users are stored in PostgreSQL (users table) with bcrypt hashed passwords.
  No hardcoded credentials.
Dependencies: jwt_handler, user_repository, dependencies
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from api.dependencies import get_current_user, get_jwt_handler
from core.auth.jwt_handler import JWTHandler
from core.db.user_repository import get_user_by_email, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str   # treated as email
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
    user = await get_user_by_email(body.username)
    if user is None or not user.is_active or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return TokenResponse(
        access_token=jwt.create_access_token(user.email, user.role),
        refresh_token=jwt.create_refresh_token(user.email),
        expires_in=3600,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, jwt: JWTHandler = Depends(get_jwt_handler)):
    email = jwt.decode_refresh(body.refresh_token)
    user = await get_user_by_email(email)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return TokenResponse(
        access_token=jwt.create_access_token(user.email, user.role),
        refresh_token=jwt.create_refresh_token(user.email),
        expires_in=3600,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout():
    return None


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
