"""Shared pytest fixtures."""
from __future__ import annotations

import os

# SPEC-A01: the JWT-secret validator is always active. Tests run with the
# documented escape hatch so Settings() with the default secret still builds.
os.environ.setdefault("ALLOW_INSECURE_JWT", "true")

import pytest
from unittest.mock import MagicMock

from core.config.settings import Settings


@pytest.fixture
def mock_settings() -> Settings:
    s = MagicMock(spec=Settings)
    s.EXECUTION_MODE = "paper"
    s.TRADING_ENABLED = False
    s.MAX_RISK_PER_TRADE_PCT = 0.01
    s.MAX_PORTFOLIO_RISK_PCT = 0.10
    s.DAILY_LOSS_LIMIT_PCT = 0.05
    s.MAX_CONSECUTIVE_LOSSES = 5
    s.MAX_DRAWDOWN_PCT = 0.15
    s.JWT_SECRET_KEY = "test-secret"
    s.JWT_ALGORITHM = "HS256"
    s.JWT_EXPIRE_MINUTES = 60
    return s


@pytest.fixture
def sample_signal() -> dict:
    return {
        "id": "test-signal-001",
        "idempotency_key": "abc123",
        "symbol": "BTCUSDT",
        "action": "BUY",
        "entry_price": 50000.0,
        "stop_loss": 47500.0,
        "take_profit": 57500.0,
        "risk_reward_ratio": 3.0,
        "confidence": 0.78,
    }


@pytest.fixture
def sample_portfolio() -> dict:
    return {
        "total_capital": 10000.0,
        "available_capital": 9000.0,
        "risk_exposure": 0.05,
        "daily_pnl_pct": 0.0,
        "drawdown_current": 0.02,
    }


# ── Hermetic integration fixtures (SPEC-B01) ──────────────────────────────
@pytest.fixture(scope="session")
def docker_services():
    """Ephemeral Postgres + Redis for integration tests.

    Resolution order:
      1. Real services already pointed at by env (CI `services:` block) → use them.
      2. testcontainers + a working Docker daemon → spin ephemeral containers.
      3. Otherwise → skip the requesting test.
    Yields ``{"database_url": ..., "redis_url": ...}`` and restores env on teardown.
    """
    pre_db, pre_redis = os.environ.get("DATABASE_URL"), os.environ.get("REDIS_URL")

    if os.environ.get("CI_DB_READY") == "1" and pre_db and pre_redis:
        yield {"database_url": pre_db, "redis_url": pre_redis}
        return

    try:
        from testcontainers.postgres import PostgresContainer
        from testcontainers.redis import RedisContainer
    except ImportError:
        pytest.skip("testcontainers not installed (pip install testcontainers)")

    try:
        pg = PostgresContainer("postgres:15-alpine")
        rd = RedisContainer("redis:7-alpine")
        pg.start()
        rd.start()
    except Exception as exc:  # noqa: BLE001 — Docker daemon missing / unreachable
        pytest.skip(f"Docker not available for testcontainers: {exc}")

    db_url = pg.get_connection_url().replace("psycopg2", "asyncpg")
    redis_url = f"redis://{rd.get_container_host_ip()}:{rd.get_exposed_port(6379)}/0"
    os.environ["DATABASE_URL"], os.environ["REDIS_URL"] = db_url, redis_url
    try:
        yield {"database_url": db_url, "redis_url": redis_url}
    finally:
        for key, val in (("DATABASE_URL", pre_db), ("REDIS_URL", pre_redis)):
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val
        rd.stop()
        pg.stop()


@pytest.fixture(scope="session")
def live_server():
    """Run `api.main:app` under uvicorn on a free port for the test session.

    Yields the base URL (e.g. ``http://127.0.0.1:54123``). Used by
    tests/test_dashboard_e2e.py, which previously assumed a server was already
    listening on :8000 and always failed.
    """
    import socket
    import threading
    import time
    from unittest.mock import patch

    import httpx
    import uvicorn

    import api.main as main

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    # Keep startup fast and deterministic — the dashboard tests only need HTML +
    # public read endpoints, not migrations / parquet warmup / the metrics port.
    async def _noop_async(*_a, **_kw):
        return None

    patches = [
        patch.object(main, "init_pool", _noop_async),
        patch.object(main, "run_migrations", lambda: None),
        patch.object(main, "_load_parquet_data", lambda: None),
        patch.object(main, "start_metrics_server", lambda *a, **k: None),
    ]
    for p in patches:
        p.start()

    config = uvicorn.Config(
        main.app, host="127.0.0.1", port=port, log_level="warning", lifespan="on"
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base = f"http://127.0.0.1:{port}"
    ready = False
    for _ in range(150):
        try:
            httpx.get(f"{base}/health", timeout=1.0)
            ready = True
            break
        except Exception:  # noqa: BLE001
            time.sleep(0.1)

    if not ready:
        server.should_exit = True
        thread.join(timeout=5)
        for p in patches:
            p.stop()
        pytest.skip("live_server did not become ready")

    try:
        yield base
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        for p in patches:
            p.stop()
