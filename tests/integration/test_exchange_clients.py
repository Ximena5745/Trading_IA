"""
Integration tests for exchange clients and streaming.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from core.ingestion.exchange_selector import ExchangeSelector


class TestExchangeSelector:
    """Test exchange selection logic."""

    def test_crypto_symbol_selects_binance(self):
        """Crypto symbols should select binance by default."""
        clients = {"binance": MagicMock(), "mt5": MagicMock()}
        selector = ExchangeSelector(clients)

        client, exchange = selector.get_client("BTCUSDT")

        assert exchange == "binance"
        assert client == clients["binance"]

    def test_forex_symbol_selects_mt5(self):
        """Forex symbols should select mt5 by default."""
        clients = {"binance": MagicMock(), "mt5": MagicMock()}
        selector = ExchangeSelector(clients)

        client, exchange = selector.get_client("EURUSD")

        assert exchange == "mt5"

    def test_indices_symbol_selects_mt5(self):
        """Index symbols should select mt5."""
        clients = {"binance": MagicMock(), "mt5": MagicMock()}
        selector = ExchangeSelector(clients)

        client, exchange = selector.get_client("SPX500")

        assert exchange == "mt5"

    def test_gold_symbol_selects_mt5(self):
        """Commodity symbols like XAU should select mt5."""
        clients = {"binance": MagicMock(), "mt5": MagicMock()}
        selector = ExchangeSelector(clients)

        client, exchange = selector.get_client("XAUUSD")

        assert exchange == "mt5"

    def test_fallback_to_bybit_when_primary_unavailable(self):
        """Should fall back to bybit when no primary crypto client available."""
        primary = {"mt5": MagicMock()}
        fallback = {"bybit": MagicMock()}
        selector = ExchangeSelector(primary, fallback)

        client, exchange = selector.get_client("BTCUSDT")

        assert exchange == "bybit"

    def test_returns_none_when_no_exchange_available(self):
        """Should return none when no client available."""
        clients = {}
        selector = ExchangeSelector(clients)

        client, exchange = selector.get_client("BTCUSDT")

        assert exchange == "none"
        assert client is None


class TestAssetClassInference:
    """Test asset class inference from symbol."""

    def test_infers_crypto_from_usdt(self):
        selector = ExchangeSelector({})
        asset_class = selector._infer_asset_class("BTCUSDT")
        assert asset_class == "crypto"

    def test_infers_forex_from_major_pairs(self):
        selector = ExchangeSelector({})
        assert selector._infer_asset_class("EURUSD") == "forex"
        assert selector._infer_asset_class("GBPUSD") == "forex"
        assert selector._infer_asset_class("USDJPY") == "forex"

    def test_infers_indices_from_known_symbols(self):
        selector = ExchangeSelector({})
        assert selector._infer_asset_class("SPX500") == "indices"
        assert selector._infer_asset_class("NAS100") == "indices"

    def test_infers_commodities_from_metals(self):
        selector = ExchangeSelector({})
        assert selector._infer_asset_class("XAUUSD") == "commodities"
        assert selector._infer_asset_class("XAGUSD") == "commodities"


class TestStreamManagerCreation:
    """Test WebSocketStreamManager creation."""

    def test_manager_creation(self):
        from interfaces.websocket.stream_manager import WebSocketStreamManager, Exchange, StreamType

        manager = WebSocketStreamManager(redis_url="redis://localhost:6379")

        assert manager is not None
        assert len(manager._streams) == 0

    def test_create_binances_stream(self):
        from interfaces.websocket.stream_manager import WebSocketStreamManager, Exchange, StreamType

        manager = WebSocketStreamManager()
        stream = manager.create_stream(Exchange.BINANCE, "BTCUSDT", StreamType.KLINE)

        assert stream is not None

    def test_create_bybit_stream(self):
        from interfaces.websocket.stream_manager import WebSocketStreamManager, Exchange, StreamType

        manager = WebSocketStreamManager()
        stream = manager.create_stream(Exchange.BYBIT, "BTCUSDT", StreamType.KLINE, testnet=True)

        assert stream is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])