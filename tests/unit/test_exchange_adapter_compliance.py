"""
Tests for core/ingestion/exchange_adapter.py + exchange_registry.py

Paso 7 del plan maestro (unificar interfaz de exchange). Antes de este fix,
OandaClient y AlphaVantageClient no se podian instanciar (TypeError, faltaban
metodos abstractos de ExchangeAdapter), y MT5Client tampoco deberia haber
podido instanciarse (is_connected() nunca implementado). Estos tests hacen
explicito que las 5 implementaciones (IBClient aparte, requiere ib_insync no
instalado en este entorno) son sustituibles por ExchangeAdapter.
"""
from __future__ import annotations

import pytest

from core.ingestion.exchange_adapter import ExchangeAdapter
from core.ingestion.exchange_registry import ExchangeConfig, ExchangeRegistry


class TestClientsAreInstantiableAdapters:
    """Cada cliente debe poder instanciarse y ser un ExchangeAdapter valido."""

    def test_binance_client_is_exchange_adapter(self):
        from core.ingestion.binance_client import BinanceClient

        client = BinanceClient(api_key="k", secret_key="s", testnet=True)
        assert isinstance(client, ExchangeAdapter)
        assert client.is_connected() is False

    def test_bybit_client_is_exchange_adapter(self):
        from core.ingestion.bybit_client import BybitClient

        client = BybitClient(api_key="k", api_secret="s", testnet=True)
        assert isinstance(client, ExchangeAdapter)
        assert client.is_connected() is False

    def test_oanda_client_is_exchange_adapter(self):
        """Antes del fix: TypeError, faltaban place_order/cancel_order/get_order_status."""
        from core.ingestion.oanda_client import OandaClient

        client = OandaClient(api_key="k", account_id="acc", environment="practice")
        assert isinstance(client, ExchangeAdapter)
        assert client.is_connected() is False

    def test_alpha_vantage_client_is_exchange_adapter(self):
        """Antes del fix: TypeError, faltaban 5 de los 7 metodos abstractos."""
        from core.ingestion.alpha_vantage_client import AlphaVantageClient

        client = AlphaVantageClient(api_key="k")
        assert isinstance(client, ExchangeAdapter)
        assert client.is_connected() is False

    def test_mt5_client_is_exchange_adapter(self):
        """Antes del fix: is_connected() era abstracto y nunca se implementaba."""
        from core.ingestion.providers.mt5_client import MT5Client

        client = MT5Client(server="Demo", account_number=123, password="pw")
        assert isinstance(client, ExchangeAdapter)
        assert client.is_connected() is False

    def test_ib_client_is_exchange_adapter(self):
        pytest.importorskip("ib_insync")
        from core.ingestion.providers.ib_client import IBClient

        client = IBClient()
        assert isinstance(client, ExchangeAdapter)


class TestDataOnlyAndUnsupportedOperationsRaise:
    """Operaciones no soportadas por diseno deben fallar explicitamente, no silenciosamente."""

    @pytest.mark.asyncio
    async def test_alpha_vantage_place_order_not_implemented(self):
        from core.ingestion.alpha_vantage_client import AlphaVantageClient

        client = AlphaVantageClient(api_key="k")
        with pytest.raises(NotImplementedError):
            await client.place_order("BTCUSDT", "BUY", 1.0)

    @pytest.mark.asyncio
    async def test_oanda_place_order_not_implemented(self):
        from core.ingestion.oanda_client import OandaClient

        client = OandaClient(api_key="k", account_id="acc")
        with pytest.raises(NotImplementedError):
            await client.place_order("EURUSD", "BUY", 1.0)

    @pytest.mark.asyncio
    async def test_binance_place_order_not_implemented(self):
        from core.ingestion.binance_client import BinanceClient

        client = BinanceClient(api_key="k", secret_key="s")
        with pytest.raises(NotImplementedError):
            await client.place_order("BTCUSDT", "BUY", 1.0)


class TestExchangeRegistryInstantiateClient:
    """La fabrica del registry debe armar los kwargs correctos para cada exchange."""

    def test_instantiate_binance(self):
        from core.ingestion.binance_client import BinanceClient

        config = ExchangeConfig(exchange="binance", api_key="k", secret_key="s", testnet=True)
        client = ExchangeRegistry._instantiate_client(BinanceClient, config)
        assert isinstance(client, ExchangeAdapter)

    def test_instantiate_oanda(self):
        from core.ingestion.oanda_client import OandaClient

        config = ExchangeConfig(exchange="oanda", api_key="k", account_id="acc")
        client = ExchangeRegistry._instantiate_client(OandaClient, config)
        assert isinstance(client, ExchangeAdapter)

    def test_instantiate_mt5_maps_password_and_account_number(self):
        """Antes del fix: pasaba account=/server= (no existen en el constructor) y nunca password=."""
        from core.ingestion.providers.mt5_client import MT5Client

        config = ExchangeConfig(
            exchange="mt5", account_id="123456", password="secret", host="ICMarkets-Demo"
        )
        client = ExchangeRegistry._instantiate_client(MT5Client, config)
        assert isinstance(client, ExchangeAdapter)
        assert client._account_number == 123456
        assert client._password == "secret"
        assert client._server == "ICMarkets-Demo"

    def test_instantiate_alpha_vantage(self):
        from core.ingestion.alpha_vantage_client import AlphaVantageClient

        config = ExchangeConfig(exchange="alpha_vantage", api_key="k", timeout=30)
        client = ExchangeRegistry._instantiate_client(AlphaVantageClient, config)
        assert isinstance(client, ExchangeAdapter)


class TestRegistryStatusWithoutDuckTyping:
    """get_status/is_healthy/health_check ya no dependen de hasattr(); deben
    funcionar contra instancias reales sin AttributeError."""

    def setup_method(self):
        ExchangeRegistry._clients.clear()
        ExchangeRegistry._client_classes.clear()

    def teardown_method(self):
        ExchangeRegistry._clients.clear()
        ExchangeRegistry._client_classes.clear()

    def test_get_status_reports_disconnected_real_clients(self):
        from core.ingestion.binance_client import BinanceClient
        from core.ingestion.oanda_client import OandaClient

        ExchangeRegistry.register("binance", BinanceClient)
        ExchangeRegistry.register("oanda", OandaClient)
        ExchangeRegistry.create_client(
            ExchangeConfig(exchange="binance", api_key="k", secret_key="s")
        )
        ExchangeRegistry.create_client(
            ExchangeConfig(exchange="oanda", api_key="k", account_id="acc")
        )

        status = ExchangeRegistry.get_status()
        assert status["binance"] == {"connected": False, "has_client": True}
        assert status["oanda"] == {"connected": False, "has_client": True}
        assert ExchangeRegistry.is_healthy() is False

    @pytest.mark.asyncio
    async def test_health_check_reflects_connection_state(self):
        from core.ingestion.binance_client import BinanceClient

        ExchangeRegistry.register("binance", BinanceClient)
        ExchangeRegistry.create_client(
            ExchangeConfig(exchange="binance", api_key="k", secret_key="s")
        )

        results = await ExchangeRegistry.health_check()
        assert results["binance"]["healthy"] is False
