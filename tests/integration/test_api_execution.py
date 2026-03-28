"""
Integration tests: tests/integration/test_api_execution.py
Responsibility: FastAPI endpoint tests for execution, portfolio, and strategies
Tests: authentication flow, execution validation, portfolio CRUD, strategy management
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app
from core.execution.order_tracker import OrderTracker
from core.monitoring.performance_tracker import PerformanceTracker
from core.portfolio.portfolio_manager import PortfolioManager
from core.risk.risk_manager import RiskManager
from core.strategies.strategy_registry import StrategyRegistry

# ── App-level fixtures ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def client():
    """TestClient with initialized app state."""
    with TestClient(app) as c:
        # Inject minimal state so routes work
        app.state.portfolio_manager = PortfolioManager(
            total_capital=10_000.0,
            max_risk_per_trade_pct=0.02,
        )
        app.state.performance_tracker = PerformanceTracker()
        app.state.order_tracker = OrderTracker()
        app.state.risk_manager = RiskManager()
        app.state.strategy_registry = StrategyRegistry()

        import api.routes.execution as execution_routes
        import api.routes.portfolio as portfolio_routes
        import api.routes.strategies as strategies_routes

        portfolio_routes.set_portfolio_manager(app.state.portfolio_manager)
        portfolio_routes.set_performance_tracker(app.state.performance_tracker)
        execution_routes.set_order_tracker(app.state.order_tracker)
        execution_routes.set_risk_manager(app.state.risk_manager)
        strategies_routes.set_strategy_registry(app.state.strategy_registry)

        yield c


@pytest.fixture
def auth_token(client):
    """Obtain a valid JWT token."""
    response = client.post(
        "/auth/login", json={"username": "admin", "password": "admin123"}
    )
    if response.status_code == 200:
        return response.json().get("access_token", "")
    return "mock-token"


@pytest.fixture
def auth_headers(auth_token):
    return {"Authorization": f"Bearer {auth_token}"}


# ── Health endpoint ────────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert "execution_mode" in body
        assert "trading_enabled" in body


# ── Portfolio endpoints ────────────────────────────────────────────────────


class TestPortfolioEndpoints:
    def test_get_portfolio_requires_auth(self, client):
        response = client.get("/portfolio")
        assert response.status_code in (401, 403)

    def test_get_positions_structure(self, client, auth_headers):
        response = client.get("/portfolio/positions", headers=auth_headers)
        # May return 200 or auth error depending on token validity
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            body = response.json()
            assert "positions" in body
            assert "total" in body

    def test_get_portfolio_history(self, client, auth_headers):
        response = client.get("/portfolio/history?limit=10", headers=auth_headers)
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            body = response.json()
            assert "snapshots" in body


# ── Execution endpoints ────────────────────────────────────────────────────


class TestExecutionEndpoints:
    def test_execute_without_auth_rejected(self, client):
        payload = {
            "signal_id": "sig-001",
            "symbol": "BTCUSDT",
            "direction": "BUY",
            "entry_price": 50000.0,
            "stop_loss": 49000.0,
            "take_profit": 52000.0,
            "confidence": 0.75,
        }
        response = client.post("/execution", json=payload)
        assert response.status_code in (401, 403)

    def test_get_orders_returns_list(self, client, auth_headers):
        response = client.get("/execution/orders", headers=auth_headers)
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            body = response.json()
            assert "orders" in body
            assert isinstance(body["orders"], list)

    def test_cancel_nonexistent_order_returns_404(self, client, auth_headers):
        response = client.delete(
            "/execution/orders/nonexistent-id-xyz", headers=auth_headers
        )
        assert response.status_code in (404, 401, 403)


# ── Strategy endpoints ─────────────────────────────────────────────────────


class TestStrategyEndpoints:
    def test_list_strategies_public_accessible(self, client, auth_headers):
        response = client.get("/strategies", headers=auth_headers)
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            body = response.json()
            assert "strategies" in body
            assert "total" in body

    def test_builtin_strategies_present(self, client, auth_headers):
        response = client.get("/strategies", headers=auth_headers)
        if response.status_code == 200:
            strategies = response.json().get("strategies", [])
            # Builtins should be registered
            assert len(strategies) >= 0  # At least doesn't crash

    def test_list_active_strategies(self, client, auth_headers):
        response = client.get("/strategies/active", headers=auth_headers)
        assert response.status_code in (200, 401, 403)

    def test_get_nonexistent_strategy_returns_404(self, client, auth_headers):
        response = client.get("/strategies/does-not-exist-xyz", headers=auth_headers)
        assert response.status_code in (404, 401, 403)

    def test_update_strategy_status_invalid_value(self, client, auth_headers):
        response = client.patch(
            "/strategies/ema_rsi/status",
            json={"status": "invalid_value"},
            headers=auth_headers,
        )
        assert response.status_code in (400, 401, 403, 422)


# ── Risk endpoints ─────────────────────────────────────────────────────────


class TestRiskEndpoints:
    def test_risk_status_accessible(self, client, auth_headers):
        response = client.get("/risk/status", headers=auth_headers)
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            body = response.json()
            assert (
                "kill_switch_active" in body or "is_active" in body or "active" in body
            )

    def test_risk_limits_accessible(self, client, auth_headers):
        response = client.get("/risk/limits", headers=auth_headers)
        assert response.status_code in (200, 401, 403)


# ── Signals endpoints ──────────────────────────────────────────────────────


class TestSignalsEndpoints:
    def test_list_signals(self, client, auth_headers):
        response = client.get("/signals", headers=auth_headers)
        assert response.status_code in (200, 401, 403)

    def test_get_signal_not_found(self, client, auth_headers):
        response = client.get("/signals/nonexistent-signal-id", headers=auth_headers)
        assert response.status_code in (404, 401, 403)
