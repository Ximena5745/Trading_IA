"""
Tests for SPEC-A02 — API / worker split of the pipeline scheduler (F-04).

  * test_api_lifespan_starts_no_scheduler — the API process must not create an
    APScheduler nor register pipeline jobs on app.state.
  * test_scheduler_single_owner — two concurrent lock acquisitions ⇒ exactly one
    winner (the basis for "1 cycle per symbol per window" with N uvicorn workers).
"""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from core.infrastructure.scheduler_lock import SchedulerLock


# ── Minimal in-memory Redis supporting SET NX EX / GET ─────────────────────
class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    def ping(self) -> bool:
        return True

    def set(self, key, value, *, nx=False, ex=None):  # noqa: ANN001
        if nx and key in self.store:
            return None
        self.store[key] = value
        return True

    def get(self, key):  # noqa: ANN001
        return self.store.get(key)

    def eval(self, script, numkeys, *args):  # noqa: ANN001 — compare-and-* Lua
        key = args[0]
        owner = args[1]
        if self.store.get(key) != owner:
            return 0
        if "expire" in script:
            return 1
        if "del" in script:
            self.store.pop(key, None)
            return 1
        return 0


# ── test_scheduler_single_owner ───────────────────────────────────────────
def test_scheduler_single_owner():
    shared = FakeRedis()
    a = SchedulerLock("redis://x", redis_client=shared, owner_id="worker-A")
    b = SchedulerLock("redis://x", redis_client=shared, owner_id="worker-B")

    results = [a.acquire(), b.acquire()]

    assert results.count(True) == 1, "exactly one process may own the scheduler"
    assert results.count(False) == 1
    assert shared.get("trader:scheduler:owner") in {"worker-A", "worker-B"}

    # The loser can take over only after the winner releases.
    winner, loser = (a, b) if results[0] else (b, a)
    assert loser.acquire() is False
    winner.release()
    assert loser.acquire() is True


def test_scheduler_single_owner_concurrent():
    """Same guarantee under real concurrency (thread pool of acquirers)."""
    shared = FakeRedis()

    async def _run():
        locks = [
            SchedulerLock("redis://x", redis_client=shared, owner_id=f"w{i}")
            for i in range(8)
        ]
        return await asyncio.gather(
            *(asyncio.to_thread(lock.acquire) for lock in locks)
        )

    outcomes = asyncio.run(_run())
    assert outcomes.count(True) == 1


def test_renew_only_while_owner():
    shared = FakeRedis()
    a = SchedulerLock("redis://x", redis_client=shared, owner_id="A")
    b = SchedulerLock("redis://x", redis_client=shared, owner_id="B")

    assert a.acquire() is True
    assert a.renew() is True          # A still owns it
    assert b.renew() is False         # B never owned it
    a.release()
    assert a.renew() is False         # key gone ⇒ ownership lost


def test_renew_seconds_must_be_below_ttl():
    with pytest.raises(ValueError):
        SchedulerLock("redis://x", ttl_seconds=30, renew_seconds=30)


# ── test_api_lifespan_starts_no_scheduler ─────────────────────────────────
@pytest.mark.parametrize("attr", ["scheduler", "pipeline_scheduler", "_scheduler"])
def test_api_state_has_no_scheduler_attr(attr):
    """Structural guard: the API never stashes a scheduler on app.state."""
    from starlette.testclient import TestClient

    import api.main as main

    async def _noop_async(*_a, **_kw):
        return None

    with patch.object(main, "init_pool", _noop_async), patch.object(
        main, "run_migrations", lambda: None
    ), patch.object(main, "_load_parquet_data", lambda: None), patch.object(
        main, "start_metrics_server", lambda *a, **k: None
    ):
        with TestClient(main.app) as client:
            assert client.get("/health").status_code == 200
            assert not hasattr(main.app.state, attr)

    # And the module must not even import APScheduler symbols anymore.
    import inspect

    src = inspect.getsource(main.lifespan)
    assert "AsyncIOScheduler" not in src
    assert "add_job" not in src
