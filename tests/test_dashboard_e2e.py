"""
End-to-End Tests for Dashboard
Validates: HTML rendering, chart elements, API endpoints, zoom sync
"""
import pytest
import requests
import json
from pathlib import Path
from time import sleep

BASE_URL = "http://127.0.0.1:8000"
DASHBOARD_URL = f"{BASE_URL}/dashboard"
HEALTH_URL = f"{BASE_URL}/health"


class TestDashboardHealth:
    """Verify server and health endpoints"""
    
    def test_server_health(self):
        """Health endpoint returns 200"""
        resp = requests.get(HEALTH_URL, timeout=5)
        assert resp.status_code == 200
    
    def test_dashboard_loads(self):
        """Dashboard HTML returns 200 and contains expected elements"""
        resp = requests.get(DASHBOARD_URL, timeout=10)
        assert resp.status_code == 200
        assert "candlestickChart" in resp.text
        assert "rsiChart" in resp.text
        assert "macdChart" in resp.text
        assert "bbChart" in resp.text
    
    def test_plotly_cdn_script(self):
        """Dashboard includes Plotly.js library"""
        resp = requests.get(DASHBOARD_URL, timeout=10)
        assert "plotly-2.26.0" in resp.text or "cdn.plot.ly/plotly" in resp.text


class TestAPIEndpoints:
    """Verify all public API endpoints"""
    
    @pytest.mark.parametrize("endpoint", [
        "/market/symbols",
        "/market/EURUSD/data?limit=50&timeframe=1d",
        "/market/EURUSD/features",
        "/signals?limit=10",
        "/portfolio/public",
        "/portfolio/positions/public",
        "/portfolio/history/public?limit=50",
        "/risk/status/public"
    ])
    def test_public_endpoints_200(self, endpoint):
        """All public endpoints return HTTP 200"""
        url = f"{BASE_URL}{endpoint}"
        resp = requests.get(url, timeout=5)
        assert resp.status_code == 200, f"Failed: {endpoint} returned {resp.status_code}"
    
    def test_market_data_contains_ohlcv(self):
        """Market data endpoint returns valid OHLCV"""
        resp = requests.get(
            f"{BASE_URL}/market/EURUSD/data?limit=10&timeframe=1d",
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "symbol" in data
        assert "timeframe" in data
        assert "count" in data
        assert "data" in data
        
        # Verify candles have OHLCV
        candles = data["data"]
        assert len(candles) > 0
        candle = candles[0]
        assert all(k in candle for k in ["open", "high", "low", "close", "volume"])
    
    def test_market_symbols_list(self):
        """Symbols endpoint returns list of symbols"""
        resp = requests.get(f"{BASE_URL}/market/symbols", timeout=5)
        assert resp.status_code == 200
        symbols = resp.json()
        assert isinstance(symbols, list)
        assert "EURUSD" in symbols
        assert len(symbols) >= 6  # At least 6 symbols
    
    def test_risk_status_contains_kill_switch(self):
        """Risk status endpoint contains kill switch info"""
        resp = requests.get(f"{BASE_URL}/risk/status/public", timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "kill_switch" in data
        assert "daily_loss_current" in data
        assert "daily_loss_limit" in data


class TestDataIntegrity:
    """Verify data consistency and completeness"""
    
    def test_eurusd_1d_has_candles(self):
        """EURUSD 1d has expected number of candles"""
        resp = requests.get(
            f"{BASE_URL}/market/EURUSD/data?limit=9999&timeframe=1d",
            timeout=5
        )
        data = resp.json()
        count = data["count"]
        assert count >= 100, f"Expected 100+ candles, got {count}"
    
    def test_eurusd_1h_has_intraday_data(self):
        """EURUSD 1h has intraday candles"""
        resp = requests.get(
            f"{BASE_URL}/market/EURUSD/data?limit=9999&timeframe=1h",
            timeout=5
        )
        data = resp.json()
        count = data["count"]
        assert count >= 5000, f"Expected 5000+ intraday candles, got {count}"
    
    def test_all_symbols_have_1d_data(self):
        """All symbols have at least some 1d data"""
        symbols = requests.get(f"{BASE_URL}/market/symbols", timeout=5).json()
        
        for symbol in symbols:
            resp = requests.get(
                f"{BASE_URL}/market/{symbol}/data?limit=100&timeframe=1d",
                timeout=5
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["count"] >= 10, f"{symbol} has only {data['count']} candles"


class TestDashboardFeatures:
    """Verify frontend features (requires browser interaction)"""
    
    def test_dashboard_has_chart_sync_function(self):
        """Dashboard includes setupChartSync function"""
        resp = requests.get(DASHBOARD_URL, timeout=10)
        assert "setupChartSync" in resp.text
        assert "plotly_relayout" in resp.text
    
    def test_dashboard_has_timeframe_selector(self):
        """Dashboard includes timeframe buttons (1D, 1W, 1M)"""
        resp = requests.get(DASHBOARD_URL, timeout=10)
        text = resp.text
        assert "data-tf=" in text  # timeframe button attribute
        assert "1d" in text.lower()
        assert "1wk" in text.lower() or "1w" in text.lower()
        assert "1mo" in text.lower() or "1m" in text.lower()
    
    def test_dashboard_has_error_handling(self):
        """Dashboard includes try/catch error handling"""
        resp = requests.get(DASHBOARD_URL, timeout=10)
        assert "try {" in resp.text or "try{" in resp.text
        assert "catch" in resp.text


# ── Run with: pytest tests/test_dashboard_e2e.py -v
# ── Or: pytest tests/test_dashboard_e2e.py::TestDashboardHealth -v
