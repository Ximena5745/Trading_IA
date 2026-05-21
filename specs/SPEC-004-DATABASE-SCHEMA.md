# SPEC — Database Schema
**Fecha:** 2026-05-16 | **Versión:** 1.0 | **Estado:** DRAFT

---

## 1. RESUMEN EJECUTIVO

Definir el esquema de base de datos para TimescaleDB (PostgreSQL) incluyendo tablas de signals, orders, portfolio y audit log. Implementar migraciones Alembic para gestión de versiones del esquema.

**Pertenece a:** Fase 1 - Secure Core Foundation | **Depende de:** SPEC-001 (Domain Entities)
**Bloquea:** SPEC-005 (Pipeline Scheduler)

---

## 2. OBJETIVOS

| # | Objetivo | Métrica de éxito |
|---|----------|------------------|
| O1 | Tabla signals con campos completos | Esquema con todos los campos de Signal |
| O2 | Tabla orders con estados | Esquema con OrderStatus enum |
| O3 | Tabla portfolio con posiciones | Esquema con relación a positions |
| O4 | Tabla audit_log para cambios de riesgo | Registro inmutable |
| O5 | Hypertables para timeseries (TimescaleDB) | Optimizado para time-series |

---

## 3. ESPECIFICACIÓN TÉCNICA

### 3.1 Esquema

```sql
-- signals table
CREATE TABLE signals (
    id UUID PRIMARY KEY,
    idempotency_key VARCHAR(64) UNIQUE NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    action VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20, 8) NOT NULL,
    stop_loss DECIMAL(20, 8) NOT NULL,
    take_profit DECIMAL(20, 8) NOT NULL,
    confidence DECIMAL(5, 4) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    signal_id UUID REFERENCES signals(id),
    exchange_order_id VARCHAR(64),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    quantity DECIMAL(20, 8) NOT NULL,
    status VARCHAR(20) NOT NULL,
    fill_price DECIMAL(20, 8),
    commission DECIMAL(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- portfolio table
CREATE TABLE portfolio (
    id UUID PRIMARY KEY,
    total_capital DECIMAL(20, 2) NOT NULL,
    available_capital DECIMAL(20, 2) NOT NULL,
    risk_exposure DECIMAL(5, 4) NOT NULL DEFAULT 0,
    daily_pnl DECIMAL(20, 2) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- audit_log table
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_id VARCHAR(64) NOT NULL,
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id VARCHAR(64),
    old_value JSONB,
    new_value JSONB
);
```

### 3.2 Migraciones Alembic

| Migration | Descripción |
|-----------|-------------|
| 001 | Create signals table |
| 002 | Create orders table |
| 003 | Create portfolio table |
| 004 | Create audit_log table |
| 005 | Create timescaledb hypertables |

---

## 4. CRITERIOS DE ACEPTACIÓN

| ID | Criterio | Test asociado |
|----|----------|---------------|
| CA-1 | Tabla signals tiene todos los campos | tests/integration/test_db_schema.py |
| CA-2 | Tabla orders tiene estados correctos | tests/integration/test_db_schema.py |
| CA-3 | Portfolio con invariant available <= total | tests/integration/test_db_schema.py |
| CA-4 | Audit log registra cambios de riesgo | tests/integration/test_audit.py |
| CA-5 | Hypertables creadas en TimescaleDB | tests/integration/test_hypertable.py |

---

## 5. TRAZABILIDAD

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-05-16 | Versión inicial | TRADER AI |

**ESTADO:** APPROVED