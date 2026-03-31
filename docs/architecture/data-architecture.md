# Arquitectura de Datos

> Diseño de datos y almacenamiento

---

## Esquema de Base de Datos

### Tablas Principales

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DATABASE SCHEMA                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│  │     users       │     │    signals      │     │     orders      │      │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤      │
│  │ id              │◄────│ user_id         │     │ id              │      │
│  │ username        │     │ id              │◄────│ signal_id       │      │
│  │ email           │     │ symbol          │     │ symbol          │      │
│  │ hashed_password │     │ action          │     │ side            │      │
│  │ role            │     │ entry_price     │     │ quantity        │      │
│  │ created_at      │     │ stop_loss       │     │ fill_price      │      │
│  └─────────────────┘     │ take_profit     │     │ commission      │      │
│                          │ confidence      │     │ status          │      │
│                          │ strategy_id     │     │ created_at      │      │
│                          │ status          │     └─────────────────┘      │
│                          │ created_at      │                               │
│                          └─────────────────┘                               │
│                                                                             │
│  ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐      │
│  │    candles      │     │    strategies   │     │ portfolio_      │      │
│  │  (TimescaleDB)  │     │                 │     │   snapshots     │      │
│  ├─────────────────┤     ├─────────────────┤     ├─────────────────┤      │
│  │ timestamp       │     │ strategy_id     │     │ id              │      │
│  │ symbol          │     │ name            │     │ total_capital   │      │
│  │ open            │     │ config          │     │ available       │      │
│  │ high            │     │ status          │     │ positions       │      │
│  │ low             │     │ created_at      │     │ daily_pnl       │      │
│  │ close           │     └─────────────────┘     │ drawdown        │      │
│  │ volume          │                             │ created_at      │      │
│  └─────────────────┘                             └─────────────────┘      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Definición SQL

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'trader',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Signals
CREATE TABLE signals (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(4) NOT NULL,  -- BUY, SELL
    entry_price DECIMAL(20, 8) NOT NULL,
    stop_loss DECIMAL(20, 8) NOT NULL,
    take_profit DECIMAL(20, 8) NOT NULL,
    risk_reward_ratio DECIMAL(10, 4),
    confidence DECIMAL(5, 4),
    strategy_id VARCHAR(50),
    explanation JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Orders
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    signal_id UUID REFERENCES signals(id),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(4) NOT NULL,
    order_type VARCHAR(20) DEFAULT 'MARKET',
    quantity DECIMAL(20, 8) NOT NULL,
    fill_price DECIMAL(20, 8),
    commission DECIMAL(20, 8),
    slippage DECIMAL(20, 8),
    status VARCHAR(20) NOT NULL,
    execution_mode VARCHAR(20) DEFAULT 'paper',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Portfolio Snapshots
CREATE TABLE portfolio_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    total_capital DECIMAL(20, 8) NOT NULL,
    available_capital DECIMAL(20, 8) NOT NULL,
    positions_count INTEGER DEFAULT 0,
    daily_pnl DECIMAL(20, 8) DEFAULT 0,
    total_pnl DECIMAL(20, 8) DEFAULT 0,
    drawdown_current DECIMAL(10, 6) DEFAULT 0,
    drawdown_max DECIMAL(10, 6) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Candles (TimescaleDB hypertable)
CREATE TABLE candles (
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    PRIMARY KEY (timestamp, symbol)
);

-- Convert to TimescaleDB hypertable
SELECT create_hypertable('candles', 'timestamp');

-- Strategies
CREATE TABLE strategies (
    strategy_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    config JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## Almacenamiento Redis

### Keys y TTL

| Pattern | TTL | Descripción |
|---------|-----|-------------|
| `features:{symbol}:{timestamp}` | 1 hora | Features calculados |
| `session:{token}` | 1 hora | Sesiones de usuario |
| `rate_limit:{ip}:{endpoint}` | 1 min | Rate limiting |

### Ejemplo

```python
# Guardar features
key = f"features:{symbol}:{timestamp}"
await redis.setex(key, 3600, json.dumps(features.dict()))

# Obtener features
features_json = await redis.get(key)
features = FeatureSet.parse_raw(features_json)
```

---

## Archivos Parquet

### Estructura

```
data/
├── raw/
│   ├── BTCUSDT_1h.parquet
│   ├── ETHUSDT_1h.parquet
│   ├── EURUSD_1h.parquet
│   └── ...
├── processed/
│   ├── BTCUSDT_features.parquet
│   └── ...
└── models/
    ├── technical_crypto_v1.pkl
    └── technical_forex_v1.pkl
```

### Schema Parquet

```
timestamp: timestamp[us]
symbol: string
open: double
high: double
low: double
close: double
volume: double
```

---

## Retención de Datos

| Datos | Retención | Acción |
|-------|-----------|--------|
| Candles | 2 años | Compresión automática |
| Features (Redis) | 1 hora | TTL automático |
| Signals | Permanente | - |
| Orders | Permanente | - |
| Portfolio Snapshots | 90 días | Archivar |
| Logs | 30 días | Rotación |
| Prometheus Metrics | 15 días | Retention policy |

---

## Backup

### Estrategia

| Tipo | Frecuencia | Retención |
|------|------------|-----------|
| Full DB | Diario | 30 días |
| Incremental | Cada 6 horas | 7 días |
| Modelos | Semanal | 4 semanas |

### Comandos

```bash
# Backup completo
docker-compose exec db pg_dump -U trader trader_ai | gzip > backup_$(date +%Y%m%d).sql.gz

# Restaurar
gunzip < backup_20260330.sql.gz | docker-compose exec -T db psql -U trader trader_ai
```

---

*Volver al [índice de arquitectura](README.md)*
