"""
Tests for api/routes/websocket.py — WebSocket streaming must reject unauthenticated clients.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.routes import websocket as ws_module
from core.auth.jwt_handler import JWTHandler


@pytest.fixture
def jwt_handler():
    return JWTHandler(secret_key="test-secret", algorithm="HS256", expire_minutes=60)


@pytest.fixture(autouse=True)
def patch_jwt_handler(monkeypatch, jwt_handler):
    monkeypatch.setattr(ws_module, "get_jwt_handler", lambda: jwt_handler)


def _valid_token(jwt_handler) -> str:
    return jwt_handler.create_access_token(user_id="u1", role="viewer")


class TestAuthenticateHelper:
    def test_none_token_rejected(self):
        assert ws_module._authenticate(None) is None

    def test_empty_token_rejected(self):
        assert ws_module._authenticate("") is None

    def test_garbage_token_rejected(self):
        assert ws_module._authenticate("not-a-jwt") is None

    def test_valid_token_accepted(self, jwt_handler):
        token = _valid_token(jwt_handler)
        payload = ws_module._authenticate(token)
        assert payload is not None
        assert payload["sub"] == "u1"


class TestStreamPricesRejection:
    @pytest.mark.asyncio
    async def test_missing_token_closes_before_accept(self):
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        await ws_module.stream_prices(mock_ws, "BTCUSDT", token=None)

        mock_ws.close.assert_awaited_once()
        assert mock_ws.close.await_args.kwargs["code"] == ws_module.WS_POLICY_VIOLATION
        mock_ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_token_closes_before_accept(self):
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        mock_ws.close = AsyncMock()

        await ws_module.stream_prices(mock_ws, "BTCUSDT", token="garbage")

        mock_ws.close.assert_awaited_once()
        mock_ws.accept.assert_not_called()

    @pytest.mark.asyncio
    async def test_valid_token_accepts_connection(self, jwt_handler, monkeypatch):
        token = _valid_token(jwt_handler)

        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()
        # First loop iteration sends one message then disconnects to end the test.
        mock_ws.send_text = AsyncMock(side_effect=ws_module.WebSocketDisconnect())
        monkeypatch.setattr(ws_module, "get_market_data_cache", lambda symbol: [])

        await ws_module.stream_prices(mock_ws, "BTCUSDT", token=token)

        mock_ws.accept.assert_awaited_once()
        mock_ws.close.assert_not_called()
