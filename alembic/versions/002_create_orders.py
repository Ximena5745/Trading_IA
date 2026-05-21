"""002_create_orders

Revision ID: 002
Revises: 001
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('exchange_order_id', sa.String(64)),
        sa.Column('idempotency_key', sa.String(64), unique=True, nullable=False),
        sa.Column('signal_id', sa.String(36), sa.ForeignKey('signals.id')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('asset_class', sa.String(20), server_default='crypto'),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('order_type', sa.String(20), nullable=False),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('price', sa.Numeric(20, 8)),
        sa.Column('stop_loss', sa.Numeric(20, 8), nullable=False),
        sa.Column('take_profit', sa.Numeric(20, 8), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('fill_price', sa.Numeric(20, 8)),
        sa.Column('fill_quantity', sa.Numeric(20, 8)),
        sa.Column('commission', sa.Numeric(10, 6)),
        sa.Column('slippage', sa.Numeric(10, 6)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('execution_mode', sa.String(20), server_default='paper'),
        sa.Column('error_message', sa.String(500)),
    )
    op.create_index('idx_orders_signal_id', 'orders', ['signal_id'])
    op.create_index('idx_orders_symbol', 'orders', ['symbol'])
    op.create_index('idx_orders_status', 'orders', ['status'])


def downgrade() -> None:
    op.drop_table('orders')