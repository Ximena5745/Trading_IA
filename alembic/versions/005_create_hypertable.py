"""005_create_hypertable

Revision ID: 005
Revises: 004
Create Date: 2026-05-16

Description: Create TimescaleDB hypertables for time-series tables

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert signals table to hypertable
    op.execute("""
        SELECT create_hypertable('signals', 'timestamp',
            if_not_exists => TRUE,
            migrate_data => TRUE
        )
    """)

    # Convert orders table to hypertable
    op.execute("""
        SELECT create_hypertable('orders', 'created_at',
            if_not_exists => TRUE,
            migrate_data => TRUE
        )
    """)

    # Convert audit_log table to hypertable
    op.execute("""
        SELECT create_hypertable('audit_log', 'timestamp',
            if_not_exists => TRUE,
            migrate_data => TRUE
        )
    """)

    # Add compression to older data (> 30 days)
    op.execute("""
        ALTER TABLE signals SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'symbol,status'
        )
    """)

    op.execute("""
        SELECT add_compression_policy('signals', INTERVAL '30 days')
    """)

    # Add indexes for common queries
    op.execute("CREATE INDEX IF NOT EXISTS idx_signals_symbol_timestamp ON signals (symbol, timestamp DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_symbol_created ON orders (symbol, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON audit_log (user_id, timestamp DESC)")


def downgrade() -> None:
    # Remove compression policies
    op.execute("SELECT remove_compression_policy('signals', if_exists => TRUE)")

    # Drop hypertables (converts back to regular tables)
    op.execute("DROP TABLE IF EXISTS signals CASCADE")
    op.execute("DROP TABLE IF EXISTS orders CASCADE")
    op.execute("DROP TABLE IF EXISTS audit_log CASCADE")