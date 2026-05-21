"""
Module: core/ingestion/exchange_registry.py
Responsibility: Factory and registry for exchange clients
M2.14: Exchange Registry
Dependencies: exchange clients, logger
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Type

from core.observability.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExchangeConfig:
    """Configuration for exchange client initialization."""
    exchange: str
    api_key: str = ""
    secret_key: str = ""
    testnet: bool = True
    account_id: str = ""
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    is_paper: bool = True
    environment: str = "practice"
    timeout: int = 30
    redis_url: str = "redis://localhost:6379"


class ExchangeRegistry:
    """Factory and registry for exchange clients.

    Provides:
    - Centralized client creation
    - Health checking
    - Client lifecycle management
    """

    _clients: dict[str, any] = {}
    _client_classes: dict[str, Type] = {}

    @classmethod
    def register(cls, exchange: str, client_class: Type) -> None:
        """Register a client class for an exchange."""
        cls._client_classes[exchange] = client_class
        logger.info("exchange_registered", exchange=exchange)

    @classmethod
    def create_client(cls, config: ExchangeConfig) -> any:
        """Create a client for the specified exchange."""
        exchange = config.exchange.lower()

        if exchange not in cls._client_classes:
            raise ValueError(
                f"Unsupported exchange: {exchange}. "
                f"Available: {list(cls._client_classes.keys())}"
            )

        client_class = cls._client_classes[exchange]
        client = cls._instantiate_client(client_class, config)

        cls._clients[exchange] = client
        logger.info("client_created", exchange=exchange)

        return client

    @classmethod
    def _instantiate_client(cls, client_class: Type, config: ExchangeConfig) -> any:
        """Instantiate client based on exchange type."""
        if exchange := config.exchange.lower():
            pass

        if exchange == "binance":
            return client_class(
                api_key=config.api_key,
                secret_key=config.secret_key,
                testnet=config.testnet,
            )
        elif exchange == "bybit":
            return client_class(
                api_key=config.api_key,
                secret_key=config.secret_key,
                testnet=config.testnet,
            )
        elif exchange == "oanda":
            return client_class(
                api_key=config.api_key,
                account_id=config.account_id,
                environment=config.environment,
            )
        elif exchange == "ib":
            return client_class(
                host=config.host,
                port=config.port,
                client_id=config.client_id,
                is_paper=config.is_paper,
            )
        elif exchange == "mt5":
            return client_class(
                account=config.account_id,
                server=config.host,
            )
        elif exchange == "alpha_vantage":
            return client_class(
                api_key=config.api_key,
                timeout=config.timeout,
            )
        else:
            return client_class()

    @classmethod
    def get_client(cls, exchange: str) -> Optional[any]:
        """Get existing client for exchange."""
        return cls._clients.get(exchange.lower())

    @classmethod
    def get_or_create(cls, config: ExchangeConfig) -> any:
        """Get existing client or create new one."""
        exchange = config.exchange.lower()

        if exchange in cls._clients:
            return cls._clients[exchange]

        return cls.create_client(config)

    @classmethod
    async def connect_client(cls, exchange: str) -> bool:
        """Connect a specific client."""
        client = cls._clients.get(exchange.lower())

        if not client:
            logger.warning("client_not_found", exchange=exchange)
            return False

        try:
            if hasattr(client, "connect"):
                await client.connect()
                logger.info("client_connected", exchange=exchange)
                return True
        except Exception as e:
            logger.error("client_connect_failed", exchange=exchange, error=str(e))

        return False

    @classmethod
    async def disconnect_client(cls, exchange: str) -> bool:
        """Disconnect a specific client."""
        client = cls._clients.get(exchange.lower())

        if not client:
            return False

        try:
            if hasattr(client, "disconnect"):
                await client.disconnect()
                logger.info("client_disconnected", exchange=exchange)
                return True
        except Exception as e:
            logger.error("client_disconnect_failed", exchange=exchange, error=str(e))

        return False

    @classmethod
    def get_status(cls) -> dict:
        """Get connection status for all clients."""
        status = {}

        for exchange, client in cls._clients.items():
            connected = False

            if hasattr(client, "is_connected"):
                connected = client.is_connected()
            elif hasattr(client, "_connected"):
                connected = getattr(client, "_connected", False)

            status[exchange] = {
                "connected": connected,
                "has_client": True,
            }

        for exchange in cls._client_classes:
            if exchange not in status:
                status[exchange] = {
                    "connected": False,
                    "has_client": False,
                }

        return status

    @classmethod
    def list_available_exchanges(cls) -> list[str]:
        """List all registered exchanges."""
        return list(cls._client_classes.keys())

    @classmethod
    def is_healthy(cls) -> bool:
        """Check if any client is connected."""
        for client in cls._clients.values():
            if hasattr(client, "is_connected"):
                if client.is_connected():
                    return True
            elif hasattr(client, "_connected"):
                if client._connected:
                    return True
        return False

    @classmethod
    async def health_check(cls) -> dict:
        """Perform health check on all clients."""
        results = {}

        for exchange, client in cls._clients.items():
            healthy = False
            latency_ms = 0

            try:
                import time
                start = time.time()

                if hasattr(client, "get_klines"):
                    pass

                latency_ms = int((time.time() - start) * 1000)
                healthy = True

            except Exception as e:
                logger.warning("health_check_failed", exchange=exchange, error=str(e))

            results[exchange] = {
                "healthy": healthy,
                "latency_ms": latency_ms,
            }

        return results


def register_default_exchanges() -> None:
    """Register all default exchange clients."""
    try:
        from core.ingestion.binance_client import BinanceClient
        ExchangeRegistry.register("binance", BinanceClient)
    except ImportError:
        pass

    try:
        from core.ingestion.bybit_client import BybitClient
        ExchangeRegistry.register("bybit", BybitClient)
    except ImportError:
        pass

    try:
        from core.ingestion.oanda_client import OandaClient
        ExchangeRegistry.register("oanda", OandaClient)
    except ImportError:
        pass

    try:
        from core.ingestion.providers.ib_client import IBClient
        ExchangeRegistry.register("ib", IBClient)
    except ImportError:
        pass

    try:
        from core.ingestion.providers.mt5_client import MT5Client
        ExchangeRegistry.register("mt5", MT5Client)
    except ImportError:
        pass

    try:
        from core.ingestion.alpha_vantage_client import AlphaVantageClient
        ExchangeRegistry.register("alpha_vantage", AlphaVantageClient)
    except ImportError:
        pass

    logger.info("default_exchanges_registered")


register_default_exchanges()