"""
Integration tests: tests/integration/test_api_sltp_config.py
Responsibility: FastAPI endpoint tests for the SL/TP dynamic config override
(GET/PUT/DELETE /risk/sltp-config), added for the dashboard "SL/TP dinámico
editable" panel (Fase 1b prioridad media).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.auth.jwt_handler import JWTHandler
from core.config.settings import get_settings
from core.models import AssetClass
from core.risk.mtf_sl_tp_manager import Timeframe, clear_sltp_override


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    """Overrides live in a module-level dict — clear before/after each test
    so tests don't leak state into each other."""
    clear_sltp_override(AssetClass.FOREX, Timeframe.H1)
    yield
    clear_sltp_override(AssetClass.FOREX, Timeframe.H1)


@pytest.fixture
def trader_token():
    settings = get_settings()
    handler = JWTHandler(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expire_minutes=60,
    )
    return handler.create_access_token(user_id="test_trader", role="trader")


@pytest.fixture
def trader_headers(trader_token):
    return {"Authorization": f"Bearer {trader_token}"}


class TestGetSltpConfig:
    def test_get_returns_default_when_no_override(self, client):
        r = client.get("/risk/sltp-config?symbol=EURUSD&timeframe=1h")
        assert r.status_code == 200
        body = r.json()
        assert body["asset_class"] == "forex"
        assert body["is_override"] is False
        assert body["atr_sl_multiplier"] == 2.0
        assert body["atr_tp_multiplier"] == 3.0

    def test_get_maps_symbol_to_asset_class(self, client):
        r = client.get("/risk/sltp-config?symbol=BTCUSDT&timeframe=1h")
        assert r.status_code == 200
        assert r.json()["asset_class"] == "crypto"

    def test_get_rejects_invalid_timeframe(self, client):
        r = client.get("/risk/sltp-config?symbol=EURUSD&timeframe=3h")
        assert r.status_code == 422

    def test_get_is_public_no_auth_required(self, client):
        r = client.get("/risk/sltp-config?symbol=EURUSD&timeframe=1h")
        assert r.status_code == 200


class TestPutSltpConfig:
    def test_put_requires_auth(self, client):
        r = client.put(
            "/risk/sltp-config",
            json={
                "symbol": "EURUSD",
                "timeframe": "1h",
                "atr_sl_multiplier": 3.0,
                "atr_tp_multiplier": 4.0,
                "atr_fib_weight": 0.6,
                "min_rr_ratio": 1.5,
                "max_sl_pct": 0.01,
            },
        )
        assert r.status_code in (401, 403)

    def test_put_sets_override_visible_on_get(self, client, trader_headers):
        put_r = client.put(
            "/risk/sltp-config",
            headers=trader_headers,
            json={
                "symbol": "EURUSD",
                "timeframe": "1h",
                "atr_sl_multiplier": 3.3,
                "atr_tp_multiplier": 4.4,
                "atr_fib_weight": 0.65,
                "min_rr_ratio": 1.6,
                "max_sl_pct": 0.015,
            },
        )
        assert put_r.status_code == 200
        assert put_r.json()["asset_class"] == "forex"

        get_r = client.get("/risk/sltp-config?symbol=EURUSD&timeframe=1h")
        body = get_r.json()
        assert body["is_override"] is True
        assert body["atr_sl_multiplier"] == 3.3
        assert body["atr_tp_multiplier"] == 4.4
        assert body["atr_fib_weight"] == 0.65

    def test_put_override_applies_to_whole_asset_class_not_just_one_symbol(
        self, client, trader_headers
    ):
        """The backend indexes SLTPConfig by (asset_class, timeframe), not by
        symbol — saving an override for EURUSD must also affect GBPUSD (also
        FOREX) at the same timeframe. This is the behavior documented in the
        dashboard panel's warning text."""
        client.put(
            "/risk/sltp-config",
            headers=trader_headers,
            json={
                "symbol": "EURUSD",
                "timeframe": "1h",
                "atr_sl_multiplier": 3.3,
                "atr_tp_multiplier": 4.4,
                "atr_fib_weight": 0.65,
                "min_rr_ratio": 1.6,
                "max_sl_pct": 0.015,
            },
        )
        gbp = client.get("/risk/sltp-config?symbol=GBPUSD&timeframe=1h").json()
        assert gbp["is_override"] is True
        assert gbp["atr_sl_multiplier"] == 3.3

    @pytest.mark.parametrize(
        "field,value",
        [
            ("atr_sl_multiplier", 0),
            ("atr_sl_multiplier", 15),
            ("atr_fib_weight", 1.5),
            ("atr_fib_weight", -0.1),
            ("max_sl_pct", 0.5),
        ],
    )
    def test_put_rejects_out_of_range_values(self, client, trader_headers, field, value):
        payload = {
            "symbol": "EURUSD",
            "timeframe": "1h",
            "atr_sl_multiplier": 3.0,
            "atr_tp_multiplier": 4.0,
            "atr_fib_weight": 0.6,
            "min_rr_ratio": 1.5,
            "max_sl_pct": 0.01,
        }
        payload[field] = value
        r = client.put("/risk/sltp-config", headers=trader_headers, json=payload)
        assert r.status_code == 422


class TestDeleteSltpConfig:
    def test_delete_requires_auth(self, client):
        r = client.delete("/risk/sltp-config?symbol=EURUSD&timeframe=1h")
        assert r.status_code in (401, 403)

    def test_delete_clears_override(self, client, trader_headers):
        client.put(
            "/risk/sltp-config",
            headers=trader_headers,
            json={
                "symbol": "EURUSD",
                "timeframe": "1h",
                "atr_sl_multiplier": 3.3,
                "atr_tp_multiplier": 4.4,
                "atr_fib_weight": 0.65,
                "min_rr_ratio": 1.6,
                "max_sl_pct": 0.015,
            },
        )
        assert client.get(
            "/risk/sltp-config?symbol=EURUSD&timeframe=1h"
        ).json()["is_override"] is True

        del_r = client.delete(
            "/risk/sltp-config?symbol=EURUSD&timeframe=1h", headers=trader_headers
        )
        assert del_r.status_code == 200
        assert del_r.json()["atr_sl_multiplier"] == 2.0

        get_r = client.get("/risk/sltp-config?symbol=EURUSD&timeframe=1h")
        body = get_r.json()
        assert body["is_override"] is False
        assert body["atr_sl_multiplier"] == 2.0


class TestSltpOverrideIntegratesWithManager:
    """The whole point of the override is that it actually changes what
    MTFSLTPManager.calculate_sl_tp() would compute — not just what the API
    echoes back. Verify at the get_sltp_config() level that manager.py
    consumes."""

    def test_override_is_seen_by_get_sltp_config(self, client, trader_headers):
        from core.risk.mtf_sl_tp_manager import get_sltp_config

        before = get_sltp_config(AssetClass.FOREX, Timeframe.H1)
        assert before.atr_sl_multiplier == 2.0

        client.put(
            "/risk/sltp-config",
            headers=trader_headers,
            json={
                "symbol": "EURUSD",
                "timeframe": "1h",
                "atr_sl_multiplier": 3.3,
                "atr_tp_multiplier": 4.4,
                "atr_fib_weight": 0.65,
                "min_rr_ratio": 1.6,
                "max_sl_pct": 0.015,
            },
        )
        after = get_sltp_config(AssetClass.FOREX, Timeframe.H1)
        assert after.atr_sl_multiplier == 3.3
        assert after.atr_tp_multiplier == 4.4
