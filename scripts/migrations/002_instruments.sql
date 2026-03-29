-- Migration 002: instruments table + seed data
-- Run with: docker exec -i trader_db psql -U trader -d trader_ai < scripts/migrations/002_instruments.sql

-- Instruments catalogue (IC Markets verified symbols — PROYECTO.md §1.2)
CREATE TABLE IF NOT EXISTS instruments (
    symbol          VARCHAR(20)     PRIMARY KEY,
    mt5_symbol      VARCHAR(20)     NOT NULL,
    asset_class     VARCHAR(20)     NOT NULL, -- crypto | forex | indices | commodities
    description     VARCHAR(100),
    pip_value       NUMERIC(10, 4)  NOT NULL, -- USD value of 1 pip per standard lot
    lot_size        NUMERIC(15, 2)  NOT NULL, -- contract size
    min_lots        NUMERIC(8, 2)   NOT NULL DEFAULT 0.01,
    lot_step        NUMERIC(8, 2)   NOT NULL DEFAULT 0.01,
    spread_pips     NUMERIC(8, 4)   DEFAULT 0,
    point           NUMERIC(12, 8)  NOT NULL DEFAULT 0.00001,
    swap_long       NUMERIC(10, 4)  DEFAULT 0, -- refreshed at runtime from broker
    swap_short      NUMERIC(10, 4)  DEFAULT 0,
    is_active       BOOLEAN         NOT NULL DEFAULT TRUE,
    phase           VARCHAR(10)     DEFAULT 'E',    -- 'crypto' | 'E' (MT5)
    updated_at      TIMESTAMPTZ     DEFAULT NOW()
);

-- Seed: 11 active IC Markets instruments (FASE E)
INSERT INTO instruments (symbol, mt5_symbol, asset_class, description, pip_value, lot_size, min_lots, lot_step, spread_pips, point, is_active, phase)
VALUES
  -- Forex majors
  ('EURUSD', 'EURUSD', 'forex',       'Euro vs US Dollar',            10.0,     100000, 0.01, 0.01, 0.6,  0.00001, TRUE, 'E'),
  ('GBPUSD', 'GBPUSD', 'forex',       'Great Britain Pound vs USD',   10.0,     100000, 0.01, 0.01, 0.9,  0.00001, TRUE, 'E'),
  ('USDJPY', 'USDJPY', 'forex',       'US Dollar vs Japanese Yen',    9.09,     100000, 0.01, 0.01, 0.7,  0.001,   TRUE, 'E'),
  ('USDCHF', 'USDCHF', 'forex',       'US Dollar vs Swiss Franc',     10.94,    100000, 0.01, 0.01, 0.8,  0.00001, TRUE, 'E'),
  ('USDCAD', 'USDCAD', 'forex',       'US Dollar vs Canadian Dollar', 7.47,     100000, 0.01, 0.01, 0.8,  0.00001, TRUE, 'E'),
  ('AUDUSD', 'AUDUSD', 'forex',       'Australian Dollar vs USD',     10.0,     100000, 0.01, 0.01, 0.8,  0.00001, TRUE, 'E'),
  -- Commodity
  ('XAUUSD', 'XAUUSD', 'commodities', 'Gold vs US Dollar',            1.0,      100,    0.01, 0.01, 0.25, 0.01,    TRUE, 'E'),
  -- Indices CFD
  ('US500',  'US500',  'indices',     'US SPX 500 Index',             1.0,      1,      0.1,  0.1,  0.4,  0.1,     TRUE, 'E'),
  ('US30',   'US30',   'indices',     'US Wall Street 30 Index',      1.0,      1,      0.1,  0.1,  2.0,  1.0,     TRUE, 'E'),
  ('UK100',  'UK100',  'indices',     'UK 100 Index',                 1.0,      1,      0.1,  0.1,  1.0,  1.0,     TRUE, 'E'),
  -- Crypto CFD via MT5
  ('BTCUSD', 'BTCUSD', 'crypto',      'Bitcoin (USD) CFD',            1.0,      1,      0.01, 0.01, 15.0, 1.0,     TRUE, 'E')
ON CONFLICT (symbol) DO UPDATE SET
  mt5_symbol   = EXCLUDED.mt5_symbol,
  asset_class  = EXCLUDED.asset_class,
  pip_value    = EXCLUDED.pip_value,
  lot_size     = EXCLUDED.lot_size,
  spread_pips  = EXCLUDED.spread_pips,
  is_active    = EXCLUDED.is_active,
  updated_at   = NOW();

-- Seed: crypto spot (Binance) — tracked in DB for completeness
INSERT INTO instruments (symbol, mt5_symbol, asset_class, description, pip_value, lot_size, min_lots, lot_step, point, is_active, phase)
VALUES
  ('BTCUSDT', 'BTCUSDT', 'crypto', 'Bitcoin vs USDT (Binance spot)', 1.0, 1, 0.001, 0.001, 1.0, TRUE, 'crypto'),
  ('ETHUSDT', 'ETHUSDT', 'crypto', 'Ethereum vs USDT (Binance spot)', 1.0, 1, 0.001, 0.001, 0.01, TRUE, 'crypto')
ON CONFLICT (symbol) DO NOTHING;
