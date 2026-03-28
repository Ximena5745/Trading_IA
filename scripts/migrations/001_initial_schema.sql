-- Initial schema for TRADER AI
-- Run with: psql -U trader -d trader_ai -f 001_initial_schema.sql

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Market data (hypertable for time-series performance)
CREATE TABLE IF NOT EXISTS market_data (
    timestamp       TIMESTAMPTZ     NOT NULL,
    symbol          VARCHAR(20)     NOT NULL,
    open            NUMERIC(20, 8)  NOT NULL,
    high            NUMERIC(20, 8)  NOT NULL,
    low             NUMERIC(20, 8)  NOT NULL,
    close           NUMERIC(20, 8)  NOT NULL,
    volume          NUMERIC(30, 8)  NOT NULL,
    quote_volume    NUMERIC(30, 8),
    trades_count    INTEGER,
    taker_buy_volume NUMERIC(30, 8),
    source          VARCHAR(20)     DEFAULT 'binance',
    feature_version VARCHAR(20)     DEFAULT 'v1'
);
SELECT create_hypertable('market_data', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_market_data_symbol_ts ON market_data (symbol, timestamp DESC);

-- Retention and compression
SELECT add_retention_policy('market_data', INTERVAL '2 years', if_not_exists => TRUE);
SELECT add_compression_policy('market_data', INTERVAL '7 days', if_not_exists => TRUE);

-- Features (versioned)
CREATE TABLE IF NOT EXISTS features (
    timestamp       TIMESTAMPTZ     NOT NULL,
    symbol          VARCHAR(20)     NOT NULL,
    feature_version VARCHAR(20)     NOT NULL,
    data            JSONB           NOT NULL
);
SELECT create_hypertable('features', 'timestamp', if_not_exists => TRUE);
CREATE INDEX IF NOT EXISTS idx_features_symbol_ts ON features (symbol, timestamp DESC);

-- Signals
CREATE TABLE IF NOT EXISTS signals (
    id              UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    idempotency_key VARCHAR(64)     UNIQUE NOT NULL,
    created_at      TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(20),
    action          VARCHAR(10),
    entry_price     NUMERIC(20, 8),
    stop_loss       NUMERIC(20, 8),
    take_profit     NUMERIC(20, 8),
    risk_reward_ratio FLOAT,
    confidence      FLOAT,
    explanation     JSONB,
    summary         TEXT,
    status          VARCHAR(20)     DEFAULT 'pending',
    strategy_id     VARCHAR(50),
    regime          VARCHAR(30)
);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_status ON signals (status);

-- Orders (full audit trail)
CREATE TABLE IF NOT EXISTS orders (
    id                UUID            PRIMARY KEY DEFAULT gen_random_uuid(),
    exchange_order_id VARCHAR(100),
    idempotency_key   VARCHAR(64)     UNIQUE NOT NULL,
    signal_id         UUID            REFERENCES signals(id),
    symbol            VARCHAR(20),
    side              VARCHAR(10),
    order_type        VARCHAR(20),
    quantity          NUMERIC(20, 8),
    price             NUMERIC(20, 8),
    fill_price        NUMERIC(20, 8),
    fill_quantity     NUMERIC(20, 8),
    commission        NUMERIC(20, 8),
    slippage          NUMERIC(20, 8),
    status            VARCHAR(20),
    execution_mode    VARCHAR(10)     DEFAULT 'paper',
    error_message     TEXT,
    created_at        TIMESTAMPTZ     DEFAULT NOW(),
    updated_at        TIMESTAMPTZ     DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders (status);

-- Strategies
CREATE TABLE IF NOT EXISTS strategies (
    id              VARCHAR(50)     PRIMARY KEY,
    name            VARCHAR(100)    NOT NULL,
    description     TEXT,
    entry_conditions JSONB,
    exit_conditions  JSONB,
    parameters      JSONB,
    timeframe       VARCHAR(10),
    symbols         JSONB,
    max_capital_pct FLOAT,
    risk_per_trade_pct FLOAT,
    status          VARCHAR(20)     DEFAULT 'active',
    version         VARCHAR(20),
    backtest_metrics JSONB,
    created_at      TIMESTAMPTZ     DEFAULT NOW(),
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);
