"""
Module: core/db/user_repository.py
Responsibility: User CRUD with bcrypt password hashing.
  Replaces the hardcoded _USERS dict in api/routes/auth.py.
Dependencies: asyncpg, passlib[bcrypt], session
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.db.session import get_pool
from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class UserRecord:
    id: str
    email: str
    hashed_password: str
    role: str          # admin | trader | viewer
    is_active: bool


def _bcrypt():
    """Lazy import to avoid hard dependency at module load time."""
    from passlib.context import CryptContext
    return CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return _bcrypt().hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _bcrypt().verify(plain, hashed)
    except Exception:
        return False


async def get_user_by_email(email: str) -> Optional[UserRecord]:
    sql = """
        SELECT id, email, hashed_password, role, is_active
        FROM users WHERE email = $1
    """
    try:
        row = await get_pool().fetchrow(sql, email)
        if row is None:
            return None
        return UserRecord(**dict(row))
    except Exception as e:
        logger.error("get_user_failed", email=email, error=str(e))
        return None


async def create_user(email: str, plain_password: str, role: str = "viewer") -> UserRecord:
    sql = """
        INSERT INTO users (email, hashed_password, role, is_active)
        VALUES ($1, $2, $3, true)
        RETURNING id, email, hashed_password, role, is_active
    """
    hashed = hash_password(plain_password)
    try:
        row = await get_pool().fetchrow(sql, email, hashed, role)
        logger.info("user_created", email=email, role=role)
        return UserRecord(**dict(row))
    except Exception as e:
        logger.error("user_create_failed", email=email, error=str(e))
        raise


async def user_exists(email: str) -> bool:
    sql = "SELECT 1 FROM users WHERE email = $1"
    try:
        row = await get_pool().fetchrow(sql, email)
        return row is not None
    except Exception:
        return False
