"""
Tests for F1.7 — security floor (SPEC-A01 subset, closes F-01 / F-08):
  * JWT secret validator always active
  * public /auth/register: 404 unless enabled, and can only mint a `viewer`
  * POST /auth/users requires admin
  * weak passwords rejected (422)
"""
from __future__ import annotations

import contextlib
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

import api.main as main
import api.routes.auth as auth
from api.dependencies import require_admin
from core.config.settings import Settings
from core.db.user_repository import UserRecord


# ── JWT secret validator (F-08) ──────────────────────────────────────────
def test_settings_rejects_short_or_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("ALLOW_INSECURE_JWT", "false")
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY="too-short")
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY="change-me-in-production")
    ok = Settings(JWT_SECRET_KEY="x" * 48)
    assert ok.JWT_SECRET_KEY == "x" * 48


def test_settings_escape_hatch_allows_insecure(monkeypatch):
    monkeypatch.setenv("ALLOW_INSECURE_JWT", "true")
    assert Settings(JWT_SECRET_KEY="change-me-in-production").JWT_SECRET_KEY


# ── HTTP endpoints ──────────────────────────────────────────────────────
@contextlib.contextmanager
def _client():
    async def _noop(*a, **k):
        return None

    with patch.object(main, "init_pool", _noop), patch.object(
        main, "run_migrations", lambda: None
    ), patch.object(main, "_load_parquet_data", lambda: None), patch.object(
        main, "start_metrics_server", lambda *a, **k: None
    ):
        with TestClient(main.app) as c:
            yield c


def test_register_disabled_by_default(monkeypatch):
    monkeypatch.setattr(auth.settings, "REGISTRATION_ENABLED", False)
    with _client() as c:
        r = c.post(
            "/auth/register",
            json={"email": "a@b.com", "password": "longenough123"},
        )
    assert r.status_code == 404


def test_public_register_cannot_set_role(monkeypatch):
    monkeypatch.setattr(auth.settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(auth, "get_user_by_email", AsyncMock(return_value=None))
    created = {}

    async def _create(email, password, role):
        created["role"] = role
        return UserRecord(id="u1", email=email, hashed_password="x", role=role, is_active=True)

    monkeypatch.setattr(auth, "create_user", _create)

    with _client() as c:
        r = c.post(
            "/auth/register",
            json={"email": "x@y.com", "password": "longenough123", "role": "admin"},
        )
    assert r.status_code == 201
    assert created["role"] == "viewer"  # body role ignored


def test_admin_endpoint_requires_admin(monkeypatch):
    monkeypatch.setattr(auth, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth, "create_user", AsyncMock(
        return_value=UserRecord(id="u1", email="e@e.com", hashed_password="x",
                                role="trader", is_active=True)))

    with _client() as c:
        # no token at all
        r_anon = c.post("/auth/users", json={
            "email": "e@e.com", "password": "longenough123", "role": "trader"})
        assert r_anon.status_code in (401, 403)

        # trader token — not enough
        main.app.dependency_overrides[require_admin] = _forbidden
        try:
            r_trader = c.post("/auth/users", json={
                "email": "e@e.com", "password": "longenough123", "role": "trader"})
        finally:
            main.app.dependency_overrides.clear()
        assert r_trader.status_code == 403

        # admin token
        main.app.dependency_overrides[require_admin] = lambda: {"role": "admin"}
        try:
            r_admin = c.post("/auth/users", json={
                "email": "e@e.com", "password": "longenough123", "role": "trader"})
        finally:
            main.app.dependency_overrides.clear()
        assert r_admin.status_code == 201


async def _forbidden():
    from fastapi import HTTPException

    raise HTTPException(status_code=403, detail="Admin role required")


def test_weak_password_rejected(monkeypatch):
    monkeypatch.setattr(auth.settings, "REGISTRATION_ENABLED", True)
    monkeypatch.setattr(auth, "get_user_by_email", AsyncMock(return_value=None))
    monkeypatch.setattr(auth, "create_user", AsyncMock())
    with _client() as c:
        r = c.post("/auth/register", json={"email": "a@b.com", "password": "short"})
    assert r.status_code == 422
