"""
Module: core/db/migrate.py
Responsibility: Run Alembic migrations to head at application startup.
"""
from __future__ import annotations

import os

from alembic import command
from alembic.config import Config

from core.config.settings import get_settings
from core.observability.logger import get_logger

logger = get_logger(__name__)


def run_migrations(alembic_ini: str = "alembic.ini") -> None:
    """Apply all pending Alembic revisions.

    alembic/env.py reads DATABASE_URL from the environment; make sure it is set
    from settings when a caller (e.g. the API lifespan) did not export it.
    """
    os.environ.setdefault("DATABASE_URL", get_settings().DATABASE_URL)
    cfg = Config(alembic_ini)
    command.upgrade(cfg, "head")
    logger.info("alembic_migrations_applied", revision="head")


if __name__ == "__main__":  # `python -m core.db.migrate`
    run_migrations()
