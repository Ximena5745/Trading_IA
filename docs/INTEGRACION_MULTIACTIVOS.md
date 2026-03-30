# 🔗 Guía Técnica de Integración Multiactivos

**Última actualización**: 2026-03-30
**Versión**: 2.0.0
**Audiencia**: Desarrolladores

---

## 📋 Tabla de Contenidos

1. [Arquitectura](#arquitectura)
2. [ExchangeAdapter Pattern](#exchangeadapter-pattern)
3. [Implementación de Clientes](#implementación-de-clientes)
4. [Registry y Selección Automática](#registry-y-selección-automática)
5. [Integración en Pipeline](#integración-en-pipeline)
6. [Ejemplos de Código](#ejemplos-de-código)
7. [Testing](#testing)
8. [Troubleshooting Técnico](#troubleshooting-técnico)

---

## Arquitectura

### Diagrama General

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Dashboard                       │
│                   (app/main.py)                              │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    FastAPI Backend                           │
│              (api/main.py → api/routes/*)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Trading Engine / Pipeline                       │
│         (core/trading/, core/models/*)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         │               │               │
┌────────▼──┐    ┌────────▼──┐   ┌────────▼──┐
│  Data     │    │  Trading  │   │ Features  │
│ Ingestion │    │   Logic   │   │   Eng.   │
└────────┬──┘    └──────────┘    └──────────┘
         │
┌────────▼──────────────────────────────────────────────────┐
│         ExchangeAdapterRegistry (Singleton)                │
└────────┬──────────────────────────────────────────────────┘
         │
    ┌────┼────┐
    │    │    │
┌───▼──┐│    │└──────┐
│Binance││    │      │
│Client ││    │      │
└───────┘│    │      │
    ┌────▼──┐ │   ┌──▼──┐
    │  IB   │ │   │ MT5 │
    │Client │ │   │(Win)│
    └───────┘ │   └─────┘
         ┌────▼────┐
         │OANDA    │
         │Client   │
         └─────────┘

         ↓ ↓ ↓ ↓

    ┌──────────────────────────────────┐
    │  MarketData (Normalized Model)   │
    │  - symbol                        │
    │  - timestamp                     │
    │  - open, high, low, close        │
    │  - volume                        │
    └──────────────────────────────────┘
         │
    ┌────▼────────────────────────────┐
    │  PostgreSQL / Redis Cache       │
    └────────────────────────────────┘
```

---

## ExchangeAdapter Pattern

### Interfaz Base (core/ingestion/exchange_adapter.py)

```python
from abc import ABC, abstractmethod
from typing import Optional
from core.models import MarketData

class ExchangeAdapter(ABC):
    """Interfaz normalizada para cualquier exchange/broker."""

    exchange_id: str = ""
    supported_asset_classes: tuple[str, ...] = ()

    # ─── Ciclo de vida de conexión ──────────────────────
    @abstractmethod
    async def connect(self) -> None:
        """Conectar al exchange."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Desconectar."""
        ...

    @abstractmethod
    def is_connected(self) -> bool:
        """Verificar estado de conexión."""
        ...

    # ─── Datos de mercado ──────────────────────────────
    @abstractmethod
    async def get_klines(
        self,
        symbol: str,
        interval: str,        # "1m", "5m", "1h", "1d", etc
        limit: int = 500,     # Cantidad de candles
    ) -> list[MarketData]:
        """Obtener OHLCV histórico."""
        ...

    @abstractmethod
    async def get_order_book(
        self,
        symbol: str,
        depth: int = 20,
    ) -> dict:
        """Obtener order book actual."""
        ...

    # ─── Cuenta y trading ──────────────────────────────
    @abstractmethod
    async def get_balance(self, asset: str = "USD") -> float:
        """Obtener balance de cuenta."""
        ...

    @abstractmethod
    async def place_order(
        self,
        symbol: str,
        side: str,            # "BUY" o "SELL"
        quantity: float,
        order_type: str = "MARKET",  # "MARKET", "LIMIT", "STOP"
        client_order_id: Optional[str] = None,
    ) -> dict:
        """Colocar orden."""
        ...

    @abstractmethod
    async def cancel_order(
        self,
        symbol: str,
        order_id: str,
    ) -> dict:
        """Cancelar orden."""
        ...

    @abstractmethod
    async def get_order_status(
        self,
        symbol: str,
        order_id: str,
    ) -> dict:
        """Obtener estado de orden."""
        ...
```

### Métodos Helper Compartidos

```python
def normalise_symbol(self, symbol: str) -> str:
    """Normalizar símbolo a formato del exchange.

    Ejemplo:
        EURUSD → EUR_USD (para OANDA)
        EURUSD → EURUSD  (para IB)
    """
    return symbol.upper().replace("-", "").replace("/", "")

def log_request(self, method: str, endpoint: str) -> None:
    """Registrar requestHTTP para debugging."""
    logger.debug(
        "exchange_request",
        exchange=self.exchange_id,
        method=method,
        endpoint=endpoint,
    )
```

---

## Implementación de Clientes

### BinanceClient (Existente)

**Archivo**: `core/ingestion/providers/binance_client.py`
**Responsabilidad**: Criptomonedas
**Asset Classes**: `("crypto",)`

**Ejemplo de uso:**
```python
from core.ingestion.providers.binance_client import BinanceClient

client = BinanceClient(testnet=True)
await client.connect()

# Obtener OHLCV
klines = await client.get_klines("BTCUSDT", "1h", limit=100)

# Obtener balance
balance = await client.get_balance("USDT")

# Colocar orden
order = await client.place_order(
    symbol="BTCUSDT",
    side="BUY",
    quantity=0.01,
    order_type="MARKET"
)

await client.disconnect()
```

### IBClient (NUEVO) ⭐

**Archivo**: `core/ingestion/providers/ib_client.py`
**Responsabilidad**: Forex, Índices, Commodities, Acciones, Futuros
**Asset Classes**: `("forex", "indices", "commodities", "stocks", "futures")`

**Instalación:**
```bash
pip install ib_insync>=10.28.0
```

**Ejemplo de uso:**
```python
from core.ingestion.providers.ib_client import IBClient

# Paper trading en puerto 7498
client = IBClient(
    host="127.0.0.1",
    port=7498,           # 7498=paper, 7497=live
    client_id=1,
    is_paper=True
)

await client.connect()

# Forex
eurusd = await client.get_klines("EURUSD", "1h", limit=100)

# Índices
spx = await client.get_klines("SPX500", "1h", limit=100)

# Commodities (Oro)
gold = await client.get_klines("XAUUSD", "1h", limit=100)

# Acciones
apple = await client.get_klines("AAPL", "1h", limit=100)

# Futuros
es = await client.get_klines("ES", "1h", limit=100)

await client.disconnect()
```

**Símbolos soportados** (en `IB_SYMBOL_MAP`):
```python
# Forex (40+ pares)
EURUSD, GBPUSD, USDJPY, AUDUSD, NZDUSD, USDCHF, USDCAD,
EURJPY, GBPJPY, CADJPY, CHFJPY, EURAUD, EURCAD, EURGBP,
...

# Índices (6)
SPX500 (S&P 500), NAS100 (Nasdaq-100), US30 (Dow),
DE40 (DAX), UK100 (FTSE), JP225 (Nikkei)

# Commodities (11)
XAUUSD, XAGUSD, XPTUSD, USOIL, UKOIL, NATGAS,
WHEAT, CORN, SOYBEAN, + metales

# Acciones (ejemplos)
AAPL, MSFT, GOOGL, TSLA, + miles más

# Futuros
ES, NQ, YM (índices)
GC, CL, NG (commodities)
ZB, ZT (bonos)
```

### MT5Client (NUEVO - Windows only) ⭐

**Archivo**: `core/ingestion/providers/mt5_client.py`
**Responsabilidad**: Forex, Índices, Commodities (via MT5 brokers)
**Asset Classes**: `("forex", "indices", "commodities")`
**Requisitos**: Windows + MetaTrader 5 instalado

**Instalación:**
```bash
pip install MetaTrader5==5.0.5640  # Windows only!
```

**Ejemplo de uso:**
```python
from core.ingestion.providers.mt5_client import MT5Client

client = MT5Client(
    server="ICMarketsSC-Demo04",  # Nombre del servidor
    login=12345678,
    password="password"
)

await client.connect()

# Forex
eurusd = await client.get_klines("EURUSD", "1h", limit=100)

# Balance
balance = await client.get_balance("USD")

await client.disconnect()
```

---

## Registry y Selección Automática

### ExchangeAdapterRegistry (Patrón Singleton)

**Archivo**: `core/ingestion/exchange_adapter.py`

```python
class ExchangeAdapterRegistry:
    """Registro centralizado de adapters."""

    _adapters: dict[str, ExchangeAdapter] = {}

    @classmethod
    def register(cls, adapter: ExchangeAdapter) -> None:
        """Registrar un adapter."""
        cls._adapters[adapter.exchange_id] = adapter
        logger.info(f"Registered {adapter.exchange_id}")

    @classmethod
    def get(cls, exchange_id: str) -> ExchangeAdapter:
        """Obtener adapter por ID."""
        if exchange_id not in cls._adapters:
            raise KeyError(f"Unknown exchange: {exchange_id}")
        return cls._adapters[exchange_id]

    @classmethod
    def get_for_asset_class(cls, asset_class: str) -> ExchangeAdapter:
        """Obtener mejor adapter para una clase de activo."""
        preferred = ASSET_CLASS_ADAPTER.get(asset_class)
        if preferred and preferred in cls._adapters:
            return cls._adapters[preferred]
        # Fallback a cualquier adapter que lo soporte
        for adapter in cls._adapters.values():
            if asset_class in adapter.supported_asset_classes:
                return adapter
        raise KeyError(f"No adapter for {asset_class}")

    @classmethod
    def list_available(cls) -> list[str]:
        """Listar adapters disponibles."""
        return list(cls._adapters.keys())
```

### Preferencias Globales

```python
# En core/ingestion/exchange_adapter.py

ASSET_CLASS_ADAPTER: dict[str, str] = {
    "crypto":      "binance",     # Estándar para crypto
    "forex":       "ib",          # IB: mejor latencia, spreads
    "indices":     "ib",          # IB: cobertura global
    "commodities": "ib",          # IB: futuros de commodities
    "stocks":      "ib",          # IB: acciones múltiples mercados
    "futures":     "ib",          # IB: futuros líquidos
}
```

### Uso del Registry

```python
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

# Opción 1: Get específico
crypto_adapter = ExchangeAdapterRegistry.get("binance")
forex_adapter = ExchangeAdapterRegistry.get("ib")

# Opción 2: Get automático (recomendado)
adapter = ExchangeAdapterRegistry.get_for_asset_class("forex")
# → IB si está disponible, sino MT5, sino error

# Opción 3: Listar disponibles
available = ExchangeAdapterRegistry.list_available()
# → ["binance", "ib", "mt5", ...]
```

---

## Integración en Pipeline

### 1. Data Ingestion Layer

```python
# En un servicio de ingestion

from core.ingestion.exchange_adapter import ExchangeAdapterRegistry
from core.models import MarketData

async def fetch_market_data(
    symbol: str,
    asset_class: str,
    interval: str = "1h"
) -> list[MarketData]:
    """Obtener datos de mercado (agnóstico de exchange)."""

    # Seleccionar adapter automáticamente
    adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)

    try:
        await adapter.connect()
        data = await adapter.get_klines(symbol, interval)
        return data
    finally:
        await adapter.disconnect()
```

### 2. Trading Engine Integration

```python
# En core/trading/engine.py

async def place_market_order(
    symbol: str,
    side: str,
    quantity: float,
    asset_class: str
) -> dict:
    """Colocar orden (agnóstico de exchange)."""

    adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)

    try:
        await adapter.connect()
        order = await adapter.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type="MARKET"
        )
        return order
    finally:
        await adapter.disconnect()
```

### 3. FastAPI Endpoint

```python
# En api/routes/market.py

from fastapi import APIRouter
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

router = APIRouter(prefix="/api/market", tags=["market"])

@router.get("/klines/{symbol}")
async def get_klines(
    symbol: str,
    asset_class: str = "crypto",
    interval: str = "1h"
):
    """Obtener OHLCV de cualquier activo."""
    adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)
    await adapter.connect()
    try:
        data = await adapter.get_klines(symbol, interval)
        return {"symbol": symbol, "data": data}
    finally:
        await adapter.disconnect()

@router.get("/balance/{asset_class}")
async def get_balance(asset_class: str):
    """Obtener balance de cuenta."""
    adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)
    await adapter.connect()
    try:
        balance = await adapter.get_balance()
        return {"balance": balance}
    finally:
        await adapter.disconnect()
```

---

## Ejemplos de Código

### Ejemplo 1: Comparar Datos entre Exchanges

```python
import asyncio
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

async def compare_forex_data():
    """Obtener EURUSD de IB vs MT5 (en Windows)."""

    adapters = {
        "IB": ExchangeAdapterRegistry.get("ib"),
        "MT5": ExchangeAdapterRegistry.get("mt5"),
    }

    for name, adapter in adapters.items():
        try:
            await adapter.connect()
            data = await adapter.get_klines("EURUSD", "1h", limit=10)
            print(f"{name}: {len(data)} candles")
            for candle in data[-3:]:
                print(f"  {candle.timestamp}: O={candle.open}, C={candle.close}")
        except Exception as e:
            print(f"{name} error: {e}")
        finally:
            await adapter.disconnect()

asyncio.run(compare_forex_data())
```

### Ejemplo 2: Portfolio Multi-Activos

```python
import asyncio
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

async def fetch_portfolio():
    """Obtener datos para portfolio diversificado."""

    portfolio = {
        "BTCUSDT": "crypto",
        "EURUSD": "forex",
        "SPX500": "indices",
        "XAUUSD": "commodities",
    }

    tasks = []
    adapters = {}

    for symbol, asset_class in portfolio.items():
        adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)
        adapters[symbol] = adapter
        await adapter.connect()
        tasks.append(adapter.get_klines(symbol, "1h", limit=50))

    results = await asyncio.gather(*tasks)

    for adapter in set(adapters.values()):
        await adapter.disconnect()

    return {
        symbol: data
        for (symbol, _), data in zip(portfolio.items(), results)
    }

data = asyncio.run(fetch_portfolio())
for symbol, candles in data.items():
    print(f"{symbol}: {len(candles)} candles")
```

### Ejemplo 3: Monitoreo Continuo

```python
import asyncio
import time
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

async def monitor_prices():
    """Monitorear precios cada 60 segundos."""

    symbols = [
        ("BTCUSDT", "crypto"),
        ("EURUSD", "forex"),
        ("XAUUSD", "commodities"),
    ]

    adapters = {}
    for symbol, asset_class in symbols:
        adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)
        await adapter.connect()
        adapters[symbol] = adapter

    try:
        iteration = 0
        while iteration < 5:  # 5 iteraciones de ejemplo
            iteration += 1
            print(f"\n--- Iteración {iteration} ---")

            for symbol, asset_class in symbols:
                adapter = adapters[symbol]
                data = await adapter.get_klines(symbol, "1m", limit=1)
                if data:
                    candle = data[-1]
                    print(f"{symbol}: Close={candle.close}, Volume={candle.volume}")

            if iteration < 5:
                print("Esperando 60 segundos...")
                await asyncio.sleep(60)

    finally:
        for adapter in adapters.values():
            await adapter.disconnect()

# asyncio.run(monitor_prices())  # Comentado: tomaría 4+ minutos
```

---

## Testing

### Unit Tests para Adapters

**Archivo**: `tests/test_exchange_adapters.py`

```python
import pytest
from unittest.mock import AsyncMock, patch
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

class TestBinanceAdapter:
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test conexión a Binance."""
        adapter = ExchangeAdapterRegistry.get("binance")
        await adapter.connect()
        assert adapter.is_connected()
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_get_klines(self):
        """Test obtener OHLCV."""
        adapter = ExchangeAdapterRegistry.get("binance")
        await adapter.connect()
        data = await adapter.get_klines("BTCUSDT", "1h", limit=10)
        assert len(data) <= 10
        assert all(hasattr(d, 'close') for d in data)
        await adapter.disconnect()

class TestIBAdapter:
    @pytest.mark.asyncio
    async def test_ib_requires_running_server(self):
        """Test que IB requiere TWS/IB Gateway corriendo."""
        adapter = ExchangeAdapterRegistry.get("ib")
        with pytest.raises(Exception):
            await adapter.connect()  # Fallará sin servidor

class TestRegistry:
    def test_get_adapter_by_id(self):
        """Test obtener adapter por ID."""
        adapter = ExchangeAdapterRegistry.get("binance")
        assert adapter.exchange_id == "binance"

    def test_get_for_asset_class(self):
        """Test selección automática."""
        # Debe preferir IB para forex
        adapter = ExchangeAdapterRegistry.get_for_asset_class("forex")
        assert adapter.exchange_id in ["ib", "mt5"]

    def test_list_available(self):
        """Test listar adapters."""
        available = ExchangeAdapterRegistry.list_available()
        assert "binance" in available
        assert len(available) >= 1
```

### Integration Tests

```python
@pytest.mark.asyncio
async def test_multi_asset_fetch():
    """Test obtener múltiples activos en paralelo."""
    import asyncio
    from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

    symbols = {
        "BTCUSDT": "crypto",
        "EURUSD": "forex",
    }

    tasks = []
    adapters = {}

    for symbol, asset_class in symbols.items():
        adapter = ExchangeAdapterRegistry.get_for_asset_class(asset_class)
        adapters[symbol] = adapter
        await adapter.connect()
        tasks.append(adapter.get_klines(symbol, "1h", limit=5))

    results = await asyncio.gather(*tasks)

    assert len(results) == 2
    assert all(len(r) > 0 for r in results)

    for adapter in set(adapters.values()):
        await adapter.disconnect()
```

---

## Troubleshooting Técnico

### Error: "No adapter registered for exchange: ib"

**Causa**: El adapter IB no está registrado en el registry.

**Solución**:
```python
# En api/main.py o core/config/setup.py
from core.ingestion.providers.ib_client import IBClient
from core.ingestion.exchange_adapter import ExchangeAdapterRegistry

# Registrar
ib_client = IBClient()
ExchangeAdapterRegistry.register(ib_client)
```

### Error: "IB connection timeout"

**Causa**: TWS/IB Gateway no está corriendo o puerto es incorrecto.

**Solución**:
```bash
# Verificar que TWS/IB Gateway está corriendo
netstat -an | grep 7498  # macOS/Linux
netstat -an | find "7498"  # Windows

# Verificar puerto correcto
# Paper: 7498
# Live: 7497

# En .env:
IB_HOST=127.0.0.1
IB_PORT=7498
```

### Error: "MT5 is only available on Windows"

**Causa**: Intentando importar MetaTrader5 en macOS/Linux.

**Solución**:
```python
# Detectar OS
import sys

if sys.platform == "win32":
    from core.ingestion.providers.mt5_client import MT5Client
    # Usar MT5
else:
    # Usar IB o Binance
    pass
```

### Error: "Symbol not found in adapter"

**Causa**: El símbolo no está en el mapping del adapter.

**Solución**:
```python
# Para IB, ver IB_SYMBOL_MAP en ib_client.py
# Para Binance, el símbolo debe existir en Binance

# Validar símbolo
from core.ingestion.providers.ib_client import IB_SYMBOL_MAP

symbol = "EURUSD"
if symbol.upper() not in IB_SYMBOL_MAP:
    print(f"Symbol {symbol} not in IB mapping")
```

### Error: "Async event loop already running"

**Causa**: Intentando usar `asyncio.run()` dentro de una corrutina.

**Solución**:
```python
# ❌ INCORRECTO
async def my_function():
    result = asyncio.run(other_async_func())  # Error!

# ✅ CORRECTO
async def my_function():
    result = await other_async_func()

# O si necesitas ejecutar desde código sync:
import asyncio
result = asyncio.run(my_function())  # Solo en código sync
```

---

## Mejores Prácticas

### 1. Siempre Usar Context Managers (cuando sea posible)

```python
# ✅ Bueno
async with create_adapter("ib") as adapter:
    data = await adapter.get_klines("EURUSD", "1h")

# ✅ Aceptable
adapter = ExchangeAdapterRegistry.get("ib")
try:
    await adapter.connect()
    data = await adapter.get_klines("EURUSD", "1h")
finally:
    await adapter.disconnect()

# ❌ Malo
adapter = ExchangeAdapterRegistry.get("ib")
await adapter.connect()
data = await adapter.get_klines("EURUSD", "1h")
# ¡Olvidó disconnect()!
```

### 2. Usar Registry para Selección Automática

```python
# ✅ Bueno - agnóstico de broker
adapter = ExchangeAdapterRegistry.get_for_asset_class("forex")
data = await adapter.get_klines("EURUSD", "1h")

# ❌ Malo - acoplado a broker específico
from core.ingestion.providers.ib_client import IBClient
adapter = IBClient()  # ¿Qué si IB no está disponible?
```

### 3. Normalizar Símbolos

```python
# ✅ Bueno
symbol = adapter.normalise_symbol("EUR/USD")  # EURUSD

# ❌ Malo
symbol = "EUR/USD"  # Algunos adapters no lo aceptan
```

### 4. Logging y Debugging

```python
from core.observability.logger import get_logger

logger = get_logger(__name__)

async def fetch_data(symbol, adapter):
    logger.info(
        "fetching_data",
        symbol=symbol,
        exchange=adapter.exchange_id,
        asset_class=adapter.supported_asset_classes[0],
    )

    try:
        data = await adapter.get_klines(symbol, "1h")
        logger.info(
            "data_fetched",
            symbol=symbol,
            count=len(data),
        )
        return data
    except Exception as e:
        logger.error(
            "fetch_failed",
            symbol=symbol,
            error=str(e),
        )
        raise
```

---

## Referencias

- **ExchangeAdapter Base**: `core/ingestion/exchange_adapter.py`
- **BinanceClient**: `core/ingestion/providers/binance_client.py`
- **IBClient**: `core/ingestion/providers/ib_client.py` ⭐
- **MT5Client**: `core/ingestion/providers/mt5_client.py` ⭐
- **Tests**: `tests/test_exchange_adapters.py`
- **Ejemplos**: `scripts/examples_multiactivos.py`

---

**Última actualización**: 2026-03-30
**Status**: ✅ Completo
