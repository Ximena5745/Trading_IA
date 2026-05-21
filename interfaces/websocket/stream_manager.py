"""
Module: interfaces/websocket/stream_manager.py
Responsibility: Abstract WebSocket interface for multi-exchange streaming
M2.6: WebSocket streaming - Multi-exchange support
"""
from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Callable

import redis.asyncio as aioredis

from core.models import MarketData
from core.observability.logger import get_logger

logger = get_logger(__name__)


class StreamType(str, Enum):
    KLINE = "kline"
    TICKER = "ticker"
    DEPTH = "depth"
    TRADE = "trade"


class Exchange(str, Enum):
    BINANCE = "binance"
    BYBIT = "bybit"
    OANDA = "oanda"
    IB = "ib"
    MT5 = "mt5"


@dataclass
class StreamConfig:
    exchange: Exchange
    symbol: str
    stream_type: StreamType
    interval: str = "1h"
    depth_levels: int = 20


@dataclass
class StreamStats:
    messages_received: int = 0
    messages_processed: int = 0
    errors: int = 0
    last_message_time: datetime | None = None
    connected: bool = False


class BaseWebSocketStream(ABC):
    def __init__(
        self,
        config: StreamConfig,
        redis_url: str | None = None,
        on_message: Callable[[MarketData], None] | None = None,
    ):
        self.config = config
        self.redis_url = redis_url
        self.on_message = on_message
        self._running = False
        self._redis: aioredis.Redis | None = None
        self._stats = StreamStats()
        self._reconnect_delay = 1.0

    @abstractmethod
    async def connect(self) -> None:
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        pass

    @abstractmethod
    async def _handle_message(self, msg: dict) -> None:
        pass

    async def start(self) -> None:
        if self.redis_url:
            self._redis = await aioredis.from_url(self.redis_url)
        self._running = True
        self._stats.connected = True
        logger.info("stream_started", exchange=self.config.exchange.value, symbol=self.config.symbol)

    async def stop(self) -> None:
        self._running = False
        self._stats.connected = False
        if self._redis:
            await self._redis.aclose()
        logger.info("stream_stopped", exchange=self.config.exchange.value, symbol=self.config.symbol)

    async def _publish_to_redis(self, data: MarketData) -> None:
        if not self._redis:
            return
        stream_key = f"market_data:{data.symbol}"
        payload = {
            "timestamp": data.timestamp.isoformat(),
            "symbol": data.symbol,
            "open": str(data.open),
            "high": str(data.high),
            "low": str(data.low),
            "close": str(data.close),
            "volume": str(data.volume),
            "exchange": self.config.exchange.value,
        }
        await self._redis.xadd(stream_key, payload, maxlen=1000)

    def get_stats(self) -> StreamStats:
        return self._stats


class BinanceKlineStream(BaseWebSocketStream):
    def __init__(self, config: StreamConfig, **kwargs):
        super().__init__(config, **kwargs)
        self._ws = None

    async def connect(self) -> None:
        from binance import AsyncClient, BinanceSocketManager

        client = await AsyncClient.create()
        bsm = BinanceSocketManager(client)
        stream = bsm.kline_socket(self.config.symbol, self.config.interval)
        self._ws = stream
        logger.info("binance_ws_connected", symbol=self.config.symbol)

    async def disconnect(self) -> None:
        self._ws = None
        await self.stop()

    async def _handle_message(self, msg: dict) -> None:
        self._stats.messages_received += 1

        if msg.get("e") != "kline":
            return

        k = msg["k"]
        if not k.get("x"):
            return

        data = MarketData(
            timestamp=datetime.utcfromtimestamp(k["t"] / 1000),
            symbol=k["s"],
            open=Decimal(k["o"]),
            high=Decimal(k["h"]),
            low=Decimal(k["l"]),
            close=Decimal(k["c"]),
            volume=Decimal(k["v"]),
            quote_volume=Decimal(k["q"]),
            trades_count=int(k["n"]),
            taker_buy_volume=Decimal(k.get("V", "0")),
        )

        self._stats.messages_processed += 1
        self._stats.last_message_time = datetime.utcnow()

        if self.on_message:
            await self.on_message(data)

        if self._redis:
            await self._publish_to_redis(data)


class BybitKlineStream(BaseWebSocketStream):
    def __init__(self, config: StreamConfig, testnet: bool = True, **kwargs):
        super().__init__(config, **kwargs)
        self._testnet = testnet
        self._stream = None

    async def connect(self) -> None:
        from core.ingestion.bybit_websocket_stream import BybitWebsocketStream
        self._stream = BybitWebsocketStream(
            symbols=[self.config.symbol],
            redis_url=self.redis_url or "",
            testnet=self._testnet,
            on_price=self._on_price_handler,
        )
        await self._stream.start()
        logger.info("bybit_ws_connected", symbol=self.config.symbol)

    async def disconnect(self) -> None:
        if self._stream:
            await self._stream.stop()
            self._stream = None

    async def _on_price_handler(self, data: MarketData) -> None:
        self._stats.messages_received += 1
        self._stats.messages_processed += 1
        self._stats.last_message_time = datetime.utcnow()
        if self.on_message:
            await self.on_message(data)

    async def _handle_message(self, msg: dict) -> None:
        self._stats.messages_received += 1

        if self.on_message:
            await self.on_message(data)


class OandaKlineStream(BaseWebSocketStream):
    def __init__(self, config: StreamConfig, api_key: str = "", account_id: str = "", **kwargs):
        super().__init__(config, **kwargs)
        self._ws = None
        self._api_key = api_key
        self._account_id = account_id
        self._environment = "practice"
        self._ws_url = "wss://stream-fxpractice.oanda.com/v3/accounts/{accountId}/prices"
        self._session = None

    async def connect(self) -> None:
        import aiohttp
        self._session = aiohttp.ClientSession()
        self._ws_url = self._ws_url.format(accountId=self._account_id)
        headers = {"Authorization": f"Bearer {self._api_key}"}
        self._ws = await self._session.ws_connect(self._ws_url, headers=headers)
        subscribe_msg = {"type": "subscribe", "instruments": [self.config.symbol.replace("_", "-")]}
        await self._ws.send_json(subscribe_msg)
        logger.info("oanda_ws_connected", symbol=self.config.symbol)

    async def disconnect(self) -> None:
        if self._ws:
            await self._ws.close()
        if self._session:
            await self._session.close()
        self._ws = None
        self._session = None

    async def _handle_message(self, msg: dict) -> None:
        self._stats.messages_received += 1

        if msg.get("type") != "price":
            return

        bids = msg.get("bids", [])
        asks = msg.get("asks", [])

        if not bids or not asks:
            return

        bid_price = Decimal(bids[0]["price"])
        ask_price = Decimal(asks[0]["price"])
        mid_price = (bid_price + ask_price) / 2

        timestamp = datetime.fromisoformat(msg.get("time", "").replace("Z", "+00:00"))

        data = MarketData(
            timestamp=timestamp,
            symbol=self.config.symbol,
            open=mid_price,
            high=ask_price,
            low=bid_price,
            close=mid_price,
            volume=Decimal(0),
            source="oanda",
        )

        self._stats.messages_processed += 1
        self._stats.last_message_time = datetime.utcnow()

        if self.on_message:
            await self.on_message(data)


class IBKlineStream(BaseWebSocketStream):
    def __init__(self, config: StreamConfig, host: str = "127.0.0.1", port: int = 7498, client_id: int = 1, **kwargs):
        super().__init__(config, **kwargs)
        self._host = host
        self._port = port
        self._client_id = client_id
        self._ib = None

    async def connect(self) -> None:
        from ib_insync import IB
        self._ib = IB()
        await self._ib.connectAsync(self._host, self._port, self._client_id, readonly=True)
        logger.info("ib_ws_connected", host=self._host, port=self._port)

    async def disconnect(self) -> None:
        if self._ib and self._ib.isConnected():
            self._ib.disconnect()
        self._ib = None

    async def _handle_message(self, msg: dict) -> None:
        self._stats.messages_received += 1
        # IB uses callbacks, not message handling
        self._stats.messages_processed += 1
        self._stats.last_message_time = datetime.utcnow()


class MT5KlineStream(BaseWebSocketStream):
    def __init__(self, config: StreamConfig, account: int = 0, server: str = "", **kwargs):
        super().__init__(config, **kwargs)
        self._account = account
        self._server = server
        self._stream = None

    async def connect(self) -> None:
        from core.ingestion.mt5_websocket_stream import MT5WebsocketStream
        self._stream = MT5WebsocketStream(
            symbols=[self.config.symbol],
            redis_url=self.redis_url or "",
            account=self._account,
            server=self._server,
            on_price=self._on_price_handler,
        )
        await self._stream.start()
        logger.info("mt5_ws_connected", account=self._account, server=self._server)

    async def disconnect(self) -> None:
        if self._stream:
            await self._stream.stop()
            self._stream = None

    async def _on_price_handler(self, data: MarketData) -> None:
        self._stats.messages_received += 1
        self._stats.messages_processed += 1
        self._stats.last_message_time = datetime.utcnow()
        if self.on_message:
            await self.on_message(data)

    async def _handle_message(self, msg: dict) -> None:
        self._stats.messages_received += 1


class WebSocketStreamManager:
    def __init__(self, redis_url: str | None = None):
        self._streams: dict[str, BaseWebSocketStream] = {}
        self._redis_url = redis_url
        self._running = False

    def create_stream(
        self,
        exchange: Exchange,
        symbol: str,
        stream_type: StreamType = StreamType.KLINE,
        interval: str = "1h",
        on_message: Callable[[MarketData], None] | None = None,
        oanda_api_key: str = "",
        oanda_account_id: str = "",
        testnet: bool = True,
        mt5_account: int = 0,
        mt5_server: str = "",
    ) -> BaseWebSocketStream:
        config = StreamConfig(
            exchange=exchange,
            symbol=symbol,
            stream_type=stream_type,
            interval=interval,
        )

        stream_key = f"{exchange.value}:{symbol}:{stream_type.value}"

        if exchange == Exchange.BINANCE:
            stream = BinanceKlineStream(
                config=config,
                redis_url=self._redis_url,
                on_message=on_message,
            )
        elif exchange == Exchange.BYBIT:
            stream = BybitKlineStream(
                config=config,
                redis_url=self._redis_url,
                on_message=on_message,
                testnet=testnet,
            )
        elif exchange == Exchange.OANDA:
            stream = OandaKlineStream(
                config=config,
                redis_url=self._redis_url,
                on_message=on_message,
                api_key=oanda_api_key,
                account_id=oanda_account_id,
            )
        elif exchange == Exchange.IB:
            stream = IBKlineStream(
                config=config,
                redis_url=self._redis_url,
                on_message=on_message,
                host="127.0.0.1",
                port=7498,
                client_id=1,
            )
        elif exchange == Exchange.MT5:
            stream = MT5KlineStream(
                config=config,
                redis_url=self._redis_url,
                on_message=on_message,
                account=mt5_account,
                server=mt5_server,
            )
        else:
            raise ValueError(f"Unsupported exchange: {exchange}")

        self._streams[stream_key] = stream
        return stream

    async def start_all(self) -> None:
        self._running = True
        for stream in self._streams.values():
            await stream.start()
        logger.info("all_streams_started", count=len(self._streams))

    async def stop_all(self) -> None:
        self._running = False
        for stream in self._streams.values():
            await stream.stop()
        logger.info("all_streams_stopped")

    def get_stream(self, exchange: Exchange, symbol: str, stream_type: StreamType) -> BaseWebSocketStream | None:
        stream_key = f"{exchange.value}:{symbol}:{stream_type.value}"
        return self._streams.get(stream_key)

    def get_all_stats(self) -> dict[str, StreamStats]:
        return {k: v.get_stats() for k, v in self._streams.items()}

    def is_healthy(self) -> bool:
        return all(s.get_stats().connected for s in self._streams.values())


async def create_default_manager(redis_url: str = "redis://localhost:6379") -> WebSocketStreamManager:
    return WebSocketStreamManager(redis_url=redis_url)