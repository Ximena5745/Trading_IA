"""
Module: core/db/migrate.py
Responsibility: Run Alembic migrations to head at application startup.
"""
from __future__ import annotations

from alembic import command
from alembic.config import Config

from core.observability.logger import get_logger

logger = get_logger(__name__)


def run_migrations(alembic_ini: str = "alembic.ini") -> None:
    """Apply all pending Alembic revisions (sync)."""
    cfg = Config(alembic_ini)
    command.upgrade(cfg, "head")
    logger.info("alembic_migrations_applied", revision="head")
