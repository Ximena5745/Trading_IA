"""
Module: core/db/session.py
Responsibility: asyncpg connection pool — single shared instance per process.
Dependencies: asyncpg, settings
"""
from __future__ import annotations

from typing import AsyncIterator

import asyncpg

from core.observability.logger import get_logger

logger = get_logger(__name__)

_pool: asyncpg.Pool | None = None


def _pg_url(database_url: str) -> str:
    """Convert SQLAlchemy-style URL to asyncpg-compatible URL."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://")


async def init_pool(database_url: str) -> None:
    """Create the global connection pool. Call once at startup."""
    global _pool
    if _pool is not None:
        return
    url = _pg_url(database_url)
    _pool = await asyncpg.create_pool(
        url,
        min_size=2,
        max_size=10,
        command_timeout=30,
        statement_cache_size=0,  # required for PgBouncer compatibility
    )
    logger.info("db_pool_initialized", min=2, max=10)


async def close_pool() -> None:
    """Drain and close the pool. Call at shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("db_pool_closed")


def get_pool() -> asyncpg.Pool:
    """Return the active pool. Raises if not initialized."""
    if _pool is None:
        raise RuntimeError("DB pool not initialized — call init_pool() first")
    return _pool


async def acquire() -> AsyncIterator[asyncpg.Connection]:
    """Async context manager: acquire a connection from the pool."""
    async with get_pool().acquire() as conn:
        yield conn
