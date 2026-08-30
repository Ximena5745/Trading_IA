"""
Module: api/routes/auth.py
Responsibility: Authentication endpoints — login, refresh, logout, me, register.
  Users are stored in PostgreSQL (users table) with bcrypt hashed passwords.
  No hardcoded credentials.
Dependencies: jwt_handler, user_repository, dependencies
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field

from api.dependencies import get_current_user, get_jwt_handler, require_admin
from core.auth.jwt_handler import JWTHandler
from core.config.settings import get_settings
from core.db.user_repository import get_user_by_email, verify_password, create_user
from core.auth.permissions import Role
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


class LoginRequest(BaseModel):
    username: str  # treated as email
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    # NOTE: no `role` — public registration always creates a viewer (SPEC-A01).


class CreateUserRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12)
    role: str = Role.VIEWER.value


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def register(request: Request, body: RegisterRequest, jwt: JWTHandler = Depends(get_jwt_handler)):
    # SPEC-A01 / F-01: public self-registration is opt-in and, when on, can only
    # ever create a `viewer`. Elevated roles go through POST /auth/users (admin).
    if not settings.REGISTRATION_ENABLED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    existing = await get_user_by_email(body.email)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = await create_user(body.email, body.password, Role.VIEWER.value)
    return TokenResponse(
        access_token=jwt.create_access_token(user.email, user.role),
        refresh_token=jwt.create_refresh_token(user.email),
        expires_in=3600,
    )


@router.post(
    "/users",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
@limiter.limit("10/minute")
async def create_user_admin(request: Request, body: CreateUserRequest):
    """Admin-only account creation for any role (SPEC-A01)."""
    try:
        role = Role(body.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role. Must be one of: {[r.value for r in Role]}",
        )

    if await get_user_by_email(body.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = await create_user(body.email, body.password, role.value)
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(request: Request, body: LoginRequest, jwt: JWTHandler = Depends(get_jwt_handler)):
    user = await get_user_by_email(body.username)
    if (
        user is None
        or not user.is_active
        or not verify_password(body.password, user.hashed_password)
    ):
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return TokenResponse(
        access_token=jwt.create_access_token(user.email, user.role),
        refresh_token=jwt.create_refresh_token(user.email),
        expires_in=3600,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, jwt: JWTHandler = Depends(get_jwt_handler), user: dict = Depends(get_current_user)):
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        jwt.add_to_blacklist(token)
    return None


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return user
