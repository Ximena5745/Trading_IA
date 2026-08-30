"""
Tests for SPEC-A03 — packaging + DB fail policy (F-05, D-05, D-22).

  * test_startup_live_without_db_exits — EXECUTION_MODE=live + unreachable DB ⇒
    the lifespan raises, the process never becomes "up".
  * test_health_reports_db_state — /health exposes db_initialized, and paper mode
    degrades (stays up) when the DB is unreachable.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

import api.main as main


async def _raise_init_pool(*_a, **_kw):
    raise RuntimeError("connection refused (simulated)")


async def _ok_init_pool(*_a, **_kw):
    return None


def _patched_env():
    """Patch the heavy / port-binding startup steps to no-ops."""
    return [
        patch.object(main, "_load_parquet_data", lambda: None),
        patch.object(main, "start_metrics_server", lambda *a, **k: None),
        patch.object(main, "run_migrations", lambda: None),
    ]


def test_startup_live_without_db_exits(monkeypatch):
    monkeypatch.setattr(main.settings, "EXECUTION_MODE", "live")
    ctxs = _patched_env() + [patch.object(main, "init_pool", _raise_init_pool)]
    for c in ctxs:
        c.start()
    try:
        with pytest.raises(Exception) as exc_info:
            with TestClient(main.app):
                pass
        assert "connection refused (simulated)" in str(exc_info.value)
    finally:
        for c in ctxs:
            c.stop()


def test_health_reports_db_state_degraded_in_paper(monkeypatch):
    monkeypatch.setattr(main.settings, "EXECUTION_MODE", "paper")
    ctxs = _patched_env() + [patch.object(main, "init_pool", _raise_init_pool)]
    for c in ctxs:
        c.start()
    try:
        with TestClient(main.app) as client:
            body = client.get("/health").json()
        assert body["status"] == "ok"
        assert body["db_initialized"] is False
    finally:
        for c in ctxs:
            c.stop()


def test_health_reports_db_state_ok_when_db_up(monkeypatch):
    monkeypatch.setattr(main.settings, "EXECUTION_MODE", "paper")
    ctxs = _patched_env() + [patch.object(main, "init_pool", _ok_init_pool)]
    for c in ctxs:
        c.start()
    try:
        with TestClient(main.app) as client:
            body = client.get("/health").json()
        assert body["db_initialized"] is True
        assert "execution_mode" in body
    finally:
        for c in ctxs:
            c.stop()
