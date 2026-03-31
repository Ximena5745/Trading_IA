# Ingestión de Datos

> Clientes de exchange, WebSocket streaming y validación

## Archivos Principales

| Archivo | Responsabilidad |
|---------|-----------------|
| `core/ingestion/base_client.py` | Interfaz abstracta |
| `core/ingestion/binance_client.py` | Cliente Binance (Crypto) |
| `core/ingestion/bybit_client.py` | Cliente Bybit (Crypto) |
| `core/ingestion/providers/mt5_client.py` | Cliente MetaTrader 5 |
| `core/ingestion/websocket_stream.py` | Streaming WebSocket |
| `core/ingestion/data_validator.py` | Validación de datos |
| `core/ingestion/exchange_adapter.py` | Adaptador unificado |

---

## Arquitectura de Ingestión

```
              BaseClient (ABC)
                    │
      ┌─────────────┼─────────────┐
      │             │             │
 BinanceClient  BybitClient   MT5Client
   (Crypto)      (Crypto)    (Forex/CFD)
      │             │             │
      └─────────────┼─────────────┘
                    │
                    ▼
            ExchangeAdapter
          (Interfaz unificada)
                    │
                    ▼
            WebSocketStream
         (Streaming en tiempo real)
                    │
                    ▼
            DataValidator
          (Validación de datos)
```

---

## BaseClient

### Interfaz Abstracta

```python
class BaseClient(ABC):
    @abstractmethod
    async def connect(self) -> None:
        """Establecer conexión con el exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Cerrar conexión."""
        pass
    
    @abstractmethod
    async def get_historical_klines(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 500
    ) -> list[MarketData]:
        """Obtener velas históricas."""
        pass
    
    @abstractmethod
    async def get_order_book(
        self,
        symbol: str,
        depth: int = 20
    ) -> dict:
        """Obtener order book."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> dict:
        """Obtener precio actual."""
        pass
```

---

## BinanceClient

### Ubicación
`core/ingestion/binance_client.py`

### Responsabilidad
Cliente para Binance spot y futures.

### Configuración

```env
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
BINANCE_TESTNET=true  # Usar testnet para pruebas
```

### Métodos

#### Conexión

```python
client = BinanceClient(
    api_key=settings.BINANCE_API_KEY,
    secret_key=settings.BINANCE_SECRET_KEY,
    testnet=settings.BINANCE_TESTNET
)

await client.connect()
```

#### Obtener Velas

```python
candles = await client.get_historical_klines(
    symbol="BTCUSDT",
    timeframe="1h",     # 1m, 5m, 15m, 1h, 4h, 1d
    limit=500
)

# Retorna list[MarketData]:
# [
#   MarketData(
#       timestamp=datetime(...),
#       symbol="BTCUSDT",
#       open=Decimal("50000"),
#       high=Decimal("50500"),
#       low=Decimal("49800"),
#       close=Decimal("50200"),
#       volume=Decimal("1250.5")
#   ),
#   ...
# ]
```

#### Obtener Order Book

```python
order_book = await client.get_order_book(
    symbol="BTCUSDT",
    depth=20  # 5, 10, 20, 50, 100, 500
)

# Retorna:
# {
#     "bids": [[price, quantity], ...],
#     "asks": [[price, quantity], ...],
#     "lastUpdateId": 123456789
# }
```

#### Obtener Precio

```python
ticker = await client.get_ticker("BTCUSDT")

# Retorna:
# {
#     "symbol": "BTCUSDT",
#     "price": "50200.00",
#     "priceChangePercent": "2.5"
# }
```

### Símbolos Soportados

```python
CRYPTO_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT",
    "SOLUSDT",
    "BNBUSDT"
]
```

---

## MT5Client

### Ubicación
`core/ingestion/providers/mt5_client.py`

### Responsabilidad
Cliente para MetaTrader 5 (IC Markets).

### Configuración

```env
MT5_LOGIN=12345678
MT5_PASSWORD=xxx
MT5_SERVER=ICMarketsSC-Demo
```

### Conexión

```python
from core.ingestion.providers.mt5_client import MT5Client

client = MT5Client(
    server="ICMarketsSC-Demo",
    login=12345678,
    password="xxx"
)

await client.connect()
```

### Obtener Velas

```python
candles = await client.get_historical_klines(
    symbol="EURUSD",
    timeframe="1h",
    limit=500
)

# Retorna list[MarketData] igual que Binance
```

### Símbolos Soportados

```python
MT5_SYMBOLS = {
    # Forex
    "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD",
    # Commodities
    "XAUUSD", "XAGUSD", "USOIL", "UKOIL",
    # Indices
    "US500", "US30", "UK100", "DE40"
}
```

---

## ExchangeAdapter

### Ubicación
`core/ingestion/exchange_adapter.py`

### Responsabilidad
Interfaz unificada para todos los exchanges.

### Uso

```python
from core.ingestion.exchange_adapter import ExchangeAdapter

# Inicializar con clientes
adapter = ExchangeAdapter(
    binance=binance_client,
    mt5=mt5_client
)

# Obtener velas - selecciona cliente automáticamente
candles = await adapter.get_historical_klines(
    symbol="BTCUSDT",  # → usa Binance
    timeframe="1h",
    limit=500
)

candles = await adapter.get_historical_klines(
    symbol="EURUSD",   # → usa MT5
    timeframe="1h",
    limit=500
)
```

### Routing por Símbolo

```python
def _get_client(self, symbol: str) -> BaseClient:
    asset_class = detect_asset_class(symbol)
    
    if asset_class == AssetClass.CRYPTO:
        return self._binance
    else:
        return self._mt5
```

---

## WebSocketStream

### Ubicación
`core/ingestion/websocket_stream.py`

### Responsabilidad
Streaming de datos en tiempo real.

### Configuración

```python
stream = WebSocketStream(
    urls={
        "binance": "wss://stream.binance.com:9443/ws",
        "bybit": "wss://stream.bybit.com/v5/public/spot"
    }
)

await stream.connect()
```

### Suscribir a Streams

```python
# Suscribir a velas
await stream.subscribe(
    channel="btcusdt@kline_1m",
    callback=on_candle_update
)

# Suscribir a trades
await stream.subscribe(
    channel="btcusdt@trade",
    callback=on_trade_update
)

# Suscribir a order book
await stream.subscribe(
    channel="btcusdt@depth20@100ms",
    callback=on_depth_update
)
```

### Callbacks

```python
async def on_candle_update(data: dict):
    """
    {
        "e": "kline",
        "s": "BTCUSDT",
        "k": {
            "t": 1617123456000,
            "o": "50000.00",
            "h": "50500.00",
            "l": "49800.00",
            "c": "50200.00",
            "v": "1250.50"
        }
    }
    """
    candle = parse_candle(data)
    await feature_store.update(candle)
```

---

## DataValidator

### Ubicación
`core/ingestion/data_validator.py`

### Responsabilidad
Validar integridad de datos de mercado.

### Validaciones

```python
class DataValidator:
    def validate_candle(self, candle: MarketData) -> bool:
        """
        Validaciones:
        1. high >= max(open, close)
        2. low <= min(open, close)
        3. volume > 0
        4. timestamp no en futuro
        5. timestamp no duplicado
        """
        
    def validate_candle_series(self, candles: list[MarketData]) -> list[MarketData]:
        """
        Validaciones adicionales:
        1. Sin gaps mayores a 2× timeframe
        2. Sin timestamps duplicados
        3. Orden cronológico
        """
```

### Ejemplo de Validación

```python
validator = DataValidator()

# Validar vela individual
is_valid = validator.validate_candle(candle)

# Validar serie
valid_candles = validator.validate_candle_series(candles)

# Obtener issues
issues = validator.get_validation_issues()
# ['gap detected at 2026-03-30T10:00:00Z', ...]
```

---

## MarketCalendar

### Ubicación
`core/ingestion/market_calendar.py`

### Responsabilidad
Determinar si un mercado está abierto.

### Lógica por Clase de Activo

```python
class MarketCalendar:
    def is_market_open(self, symbol: str) -> bool:
        """
        Crypto: Siempre abierto (24/7)
        Forex:  Lunes 00:00 - Viernes 24:00 UTC ( excluye fines de semana)
        Indices: Horario de bolsa regional
        """
```

### Horarios de Mercado

| Mercado | Horario (UTC) | Excepciones |
|---------|---------------|-------------|
| Crypto | 24/7 | - |
| Forex | Lun-Vie 00:00-24:00 | - |
| US Indices | Lun-Vie 14:30-21:00 | Feriados US |
| EU Indices | Lun-Vie 08:00-16:30 | Feriados EU |

### Verificación en Pipeline

```python
if not calendar.is_market_open(symbol):
    logger.info("cycle_skipped_market_closed", symbol=symbol)
    return  # Skip este ciclo
```

---

## Conversión de Datos

### MarketData a DataFrame

```python
def market_data_to_df(candles: list[MarketData], symbol: str) -> pd.DataFrame:
    rows = [
        {
            "timestamp": c.timestamp,
            "symbol": c.symbol,
            "open": float(c.open),
            "high": float(c.high),
            "low": float(c.low),
            "close": float(c.close),
            "volume": float(c.volume),
        }
        for c in candles
    ]
    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
```

---

## Testing

### Tests Unitarios

```bash
# Tests de BinanceClient
pytest tests/unit/test_binance_client.py -v

# Tests de DataValidator
pytest tests/unit/test_data_validator.py -v
```

### Tests de Integración

```bash
# Test completo de ingesta
pytest tests/integration/test_data_ingestion.py -v
```

---

## Configuración

### Variables de Entorno

```env
# Binance
BINANCE_API_KEY=xxx
BINANCE_SECRET_KEY=xxx
BINANCE_TESTNET=true

# MT5
MT5_LOGIN=12345678
MT5_PASSWORD=xxx
MT5_SERVER=ICMarketsSC-Demo

# WebSocket
WS_RECONNECT_INTERVAL=5
WS_MAX_RETRIES=10
```

---

*Volver al [índice de integración técnica](README.md)*
