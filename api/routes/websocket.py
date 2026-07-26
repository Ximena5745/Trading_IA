"""
Module: api/routes/websocket.py
Responsibility: WebSocket price streaming to dashboard (M2.6).
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.dependencies import get_jwt_handler
from api.routes.market import get_market_data_cache
from core.config.settings import get_settings
from core.exceptions import AuthenticationError
from core.observability.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["websocket"])

_connections: dict[str, set[WebSocket]] = {}

WS_POLICY_VIOLATION = 1008


def _authenticate(token: str | None) -> dict | None:
    """Decode+validate a JWT passed via ?token=. Returns the payload or None."""
    if not token:
        return None
    try:
        return get_jwt_handler().decode(token)
    except AuthenticationError:
        return None


@router.websocket("/ws/prices/{symbol}")
async def stream_prices(websocket: WebSocket, symbol: str, token: str | None = None) -> None:
    """Stream cached OHLCV updates to the dashboard with auto-reconnect support on client.

    Requires a valid JWT passed as the `token` query param — rejected before
    accept() otherwise (any authenticated connection may unbind an event
    loop slot indefinitely via `asyncio.sleep(2)`, and this data is treated
    as authenticated-only regardless of REST market endpoints being public).
    """
    user = _authenticate(token)
    if user is None:
        logger.warning("ws_auth_rejected", symbol=symbol.upper())
        await websocket.close(code=WS_POLICY_VIOLATION, reason="Invalid or missing token")
        return

    await websocket.accept()
    symbol = symbol.upper()
    if symbol not in _connections:
        _connections[symbol] = set()
    _connections[symbol].add(websocket)
    logger.info("ws_client_connected", symbol=symbol)

    try:
        while True:
            cache = get_market_data_cache(symbol)
            if cache:
                payload = {
                    "type": "candle",
                    "symbol": symbol,
                    "data": cache[-1] if isinstance(cache, list) else cache,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                await websocket.send_text(json.dumps(payload, default=str))
            else:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "heartbeat",
                            "symbol": symbol,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                )
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        pass
    finally:
        _connections[symbol].discard(websocket)
        logger.info("ws_client_disconnected", symbol=symbol)


async def broadcast_price(symbol: str, candle: dict) -> None:
    """Push a price update to all subscribers for a symbol."""
    clients = _connections.get(symbol.upper(), set())
    if not clients:
        return
    message = json.dumps(
        {"type": "candle", "symbol": symbol.upper(), "data": candle},
        default=str,
    )
    dead: list[WebSocket] = []
    for ws in clients:
        try:
            await ws.send_text(message)
        except Exception:
            dead.append(ws)
    for ws in dead:
        clients.discard(ws)
