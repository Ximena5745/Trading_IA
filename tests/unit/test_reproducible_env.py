"""
F1.9 — reproducible environment: compose brings up api (no jobs) + worker
(1 owner) + db + redis with migrations applied via a one-shot `migrate` service.
"""
from __future__ import annotations

from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load(
    (REPO / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
)
SERVICES = COMPOSE["services"]


def test_compose_has_core_services():
    for name in ("db", "redis", "migrate", "app", "worker"):
        assert name in SERVICES, f"compose missing service: {name}"


def test_migrate_is_one_shot_and_gates_app_and_worker():
    mig = SERVICES["migrate"]
    assert "core.db.migrate" in mig["command"]
    assert mig.get("restart") == "no"
    for svc in ("app", "worker"):
        dep = SERVICES[svc]["depends_on"]["migrate"]
        assert dep["condition"] == "service_completed_successfully"


def test_worker_runs_pipeline_api_does_not():
    assert "run_pipeline.py" in SERVICES["worker"]["command"]
    # api uses the image default CMD (uvicorn) — no `command:` override
    assert "command" not in SERVICES["app"]


def test_redis_url_carries_password():
    for svc in ("app", "worker", "migrate"):
        env = SERVICES[svc]["environment"]
        redis_url = next(e for e in env if e.startswith("REDIS_URL="))
        assert "${REDIS_PASSWORD}" in redis_url


def test_alembic_env_reads_database_url_from_environment():
    src = (REPO / "alembic" / "env.py").read_text(encoding="utf-8")
    assert 'os.getenv("DATABASE_URL")' in src
    assert "async_engine_from_config" in src  # asyncpg path, no psycopg2 needed


def test_runbook_exists():
    rb = (REPO / "docs" / "RUN_CORE_VALIDATION.md").read_text(encoding="utf-8")
    assert "docker compose" in rb
    assert "/health" in rb and "db_initialized" in rb
    assert "scheduler_owner_acquired" in rb
