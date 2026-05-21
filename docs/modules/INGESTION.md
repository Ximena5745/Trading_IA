# Módulo: Data Ingestion

> Ingestión de datos de mercado desde múltiples fuentes

---

## 1. OBJETIVO

Proveer una capa de abstracción unificada para la ingestión de datos de mercado desde múltiples exchanges (Binance, Bybit, MT5) con validación, normalización y almacenamiento en tiempo real y batch.

---

## 2. RESPONSABILIDADES

| Responsabilidad | Descripción |
|-----------------|-------------|
| Fetching | Obtención de datos OHLCV, order book, trades |
| Normalization | Estandarización de formatos entre exchanges |
| Validation | Validación de integridad de datos |
| Streaming | WS para datos en tiempo real |
| Caching | Redis para datos frecuentemente accedidos |

---

## 3. ARQUITECTURA INTERNA

```
┌─────────────────────────────────────────────────────────────────┐
│                        INGESTION LAYER                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ BinanceClient│  │  BybitClient │  │  MT5Client   │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                │                │                  │
│         └────────────────┼────────────────┘                  │
│                          ▼                                     │
│               ┌────────────────────┐                          │
│               │  ExchangeAdapter   │                          │
│               │  (Unified Interface)│                         │
│               └──────────┬─────────┘                          │
│                          │                                     │
│         ┌────────────────┼────────────────┐                  │
│         ▼                ▼                ▼                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │DataValidator │ │WebSocket    │ │ MarketCalendar│        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. COMPONENTES

### 4.1 BinanceClient

**Archivo:** `core/ingestion/binance_client.py`

| Propiedad | Valor |
|-----------|-------|
| Tipo | Exchange Client |
| Dependencias | aiohttp, python-binance |
| Estado | PRODUCTION |

**Responsabilidades:**
- Fetch de candles (REST)
- Fetch de order book
- WebSocket streaming para precios
- Manejo de rate limits

**Interfaces:**
```python
class BinanceClient(ABC):
    async def get_candles(
        self,
        symbol: str,
        interval: str,
        start_time: int | None = None,
        end_time: int | None = None,
        limit: int = 1000
    ) -> list[dict]: ...
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> dict: ...
    
    async def stream_klines(
        self,
        symbol: str,
        interval: str,
        callback: Callable[[dict], None]
    ) -> AsyncIterator[dict]: ...
```

### 4.2 BybitClient

**Archivo:** `core/ingestion/bybit_client.py`

| Propiedad | Valor |
|-----------|-------|
| Tipo | Exchange Client |
| Dependencias | aiohttp |
| Estado | PRODUCTION |

**Responsabilidades:**
- Fetch de candles (REST)
- Fetch de order book
- Similar API a Binance

### 4.3 MT5Client

**Archivo:** `core/ingestion/providers/mt5_client.py`

| Propiedad | Valor |
|-----------|-------|
| Tipo | Exchange Client |
| Dependencias | MetaTrader5 |
| Estado | PRODUCTION |

**Responsabilidades:**
- Conexión a MT5 terminal
- Fetch de ticks y candles
- Trading real (a través de executor)

**Notas:**
- Requiere MT5 terminal corriendo
- Solo funciona en Windows
- Limitado a Forex, Índices, Commodities

### 4.4 ExchangeAdapter

**Archivo:** `core/ingestion/exchange_adapter.py`

**Propósito:** Interfaz unificada que abstrae las diferencias entre exchanges.

```python
class ExchangeAdapter(ABC):
    async def get_historical(
        self,
        symbol: str,
        interval: str,
        start: datetime,
        end: datetime
    ) -> pd.DataFrame: ...
    
    async def get_latest(
        self,
        symbol: str,
        interval: str,
        limit: int = 1
    ) -> pd.DataFrame: ...
    
    async def get_order_book(self, symbol: str) -> OrderBook: ...
```

### 4.5 DataValidator

**Archivo:** `core/ingestion/data_validator.py`

**Validaciones:**
| Validación | Descripción |
|------------|-------------|
| OHLC Order | Open <= High, Low <= Close, Low <= High |
| Time Continuity | No gaps en timestamps |
| Price Sanity | No negativos, no ceros |
| Volume | No negativos |

### 4.6 MarketCalendar

**Archivo:** `core/ingestion/market_calendar.py`

**Horarios soportados:**
| Mercado | Horario (UTC) |
|---------|---------------|
| Crypto | 24/7 |
| Forex |周一 22:00 -周五 22:00 |
| US Indices | 14:30 - 21:00 |
| Commodities | Varían |

---

## 5. EVENTOS

### 5.1 Eventos Publicados

| Evento | Descripción | Payload |
|--------|-------------|---------|
| `market_data.updated` | Nuevo dato de mercado | `{symbol, interval, data}` |
| `price.alert` | Precio cruza umbral | `{symbol, price, direction}` |

### 5.2 Eventos Consumidos

| Evento | Descripción |
|--------|-------------|
| (ninguno) | Este módulo es source de datos |

---

## 6. INPUTS/OUTPUTS

### 6.1 Inputs

| Input | Tipo | Descripción |
|-------|------|-------------|
| API Keys | dict | Credenciales de exchange |
| Symbols | list[str] | Símbolos a monitorear |
| Intervals | list[str] | Timeframes (1m, 5m, 1h, etc.) |

### 6.2 Outputs

| Output | Destino | Descripción |
|--------|---------|-------------|
| OHLCV Data | PostgreSQL/TimescaleDB | Datos históricos |
| Latest Price | Redis Cache | Último precio |
| Order Book | Memory | Order book actual |

---

## 7. CASOS EDGE

| Caso | Manejo |
|------|--------|
| Rate limit excedido | Exponential backoff, retry |
| Exchange unavailable | Fallback a datos cacheados |
| Datos corruptos | Drop + log warning |
| WebSocket disconnect | Auto-reconnect con backoff |
| symbol no existe | Raise ValueError |

---

## 8. RIESGOS

| Riesgo | Impacto | Mitigación |
|--------|---------|-------------|
| Data latency | Medio | Multiple sources, caching |
| API failures | Alto | Retry logic, circuit breaker |
| Wrong data | Alto | Validation layer |

---

## 9. PERFORMANCE

| Métrica | Target |
|---------|--------|
| Latency fetching | < 500ms |
| Latency ws processing | < 50ms |
| Memory usage | < 200MB |

---

## 10. OBSERVABILIDAD

### 10.1 Métricas

| Métrica | Tipo | Descripción |
|---------|------|-------------|
| `ingestion.requests.total` | Counter | Total requests |
| `ingestion.requests.errors` | Counter | Total errores |
| `ingestion.latency` | Histogram | Latencia de requests |
| `ingestion.cache.hit_rate` | Gauge | Cache hit rate |

### 10.2 Logs

```json
{
  "event": "candle_fetched",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "count": 100,
  "latency_ms": 234
}
```

---

## 11. SEGURIDAD

- API keys en environment variables
- No logging de secrets
- IP whitelisting recomendado
- Rate limiting por API key

---

## 12. TESTING REQUERIDO

| Test | Tipo | Cobertura objetivo |
|------|------|---------------------|
| test_fetch_candles | Unit | 90% |
| test_validation | Unit | 90% |
| test_normalization | Unit | 90% |
| test_retry_logic | Integration | 100% |
| test_real_client | Manual | N/A |

---

## 13. EJEMPLOS DE USO

```python
# Obtener datos históricos
adapter = ExchangeAdapter("binance")
candles = await adapter.get_historical(
    symbol="BTCUSDT",
    interval="1h",
    start=datetime(2024, 1, 1),
    end=datetime(2024, 12, 31)
)

# Streaming en tiempo real
async for kline in client.stream_klines("BTCUSDT", "1h"):
    process(kline)
```

---

## 14. KPIs

| KPI | Target |
|-----|--------|
| Uptime | 99.9% |
| Data availability | 99.5% |
| Fetch success rate | 99% |

---

*Volver al [INDEX](../INDEX.md)*