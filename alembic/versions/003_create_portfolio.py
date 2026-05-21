"""003_create_portfolio

Revision ID: 003
Revises: 002
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'portfolio',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('total_capital', sa.Numeric(20, 2), nullable=False),
        sa.Column('available_capital', sa.Numeric(20, 2), nullable=False),
        sa.Column('risk_exposure', sa.Numeric(5, 4), server_default='0'),
        sa.Column('daily_pnl', sa.Numeric(20, 2), server_default='0'),
        sa.Column('daily_pnl_pct', sa.Numeric(10, 6), server_default='0'),
        sa.Column('total_pnl', sa.Numeric(20, 2), server_default='0'),
        sa.Column('drawdown_current', sa.Numeric(10, 6), server_default='0'),
        sa.Column('drawdown_max', sa.Numeric(10, 6), server_default='0'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'positions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('portfolio_id', sa.String(36), sa.ForeignKey('portfolio.id')),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('asset_class', sa.String(20), server_default='crypto'),
        sa.Column('quantity', sa.Numeric(20, 8), nullable=False),
        sa.Column('entry_price', sa.Numeric(20, 8), nullable=False),
        sa.Column('current_price', sa.Numeric(20, 8)),
        sa.Column('unrealized_pnl', sa.Numeric(20, 2), server_default='0'),
        sa.Column('unrealized_pnl_pct', sa.Numeric(10, 6), server_default='0'),
        sa.Column('stop_loss', sa.Numeric(20, 8)),
        sa.Column('take_profit', sa.Numeric(20, 8)),
        sa.Column('strategy_id', sa.String(50), server_default='manual'),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_positions_portfolio_id', 'positions', ['portfolio_id'])
    op.create_index('idx_positions_symbol', 'positions', ['symbol'])


def downgrade() -> None:
    op.drop_table('positions')
    op.drop_table('portfolio')