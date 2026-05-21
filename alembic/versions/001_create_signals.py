"""001_create_signals

Revision ID: 001
Revises:
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'signals',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('idempotency_key', sa.String(64), unique=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('asset_class', sa.String(20), server_default='crypto'),
        sa.Column('action', sa.String(10), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('stop_loss', sa.Numeric(20, 8), nullable=False),
        sa.Column('take_profit', sa.Numeric(20, 8), nullable=False),
        sa.Column('risk_reward_ratio', sa.Numeric(5, 2), nullable=False),
        sa.Column('confidence', sa.Numeric(5, 4), nullable=False),
        sa.Column('summary', sa.String(500), server_default=''),
        sa.Column('regime', sa.String(50)),
        sa.Column('strategy_id', sa.String(50), server_default='manual'),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_signals_symbol', 'signals', ['symbol'])
    op.create_index('idx_signals_timestamp', 'signals', ['timestamp'])
    op.create_index('idx_signals_status', 'signals', ['status'])


def downgrade() -> None:
    op.drop_table('signals')