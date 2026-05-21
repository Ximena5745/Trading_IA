"""006_create_users_and_snapshots

Revision ID: 006
Revises: 005
Create Date: 2026-05-16

Description: Create users table for auth and portfolio_snapshots for historical tracking

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table for authentication
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('role', sa.String(20), nullable=False, server_default='trader'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_users_email', 'users', ['email'])

    # Portfolio snapshots for historical tracking
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('portfolio_id', sa.String(36), sa.ForeignKey('portfolio.id')),
        sa.Column('capital_total', sa.Numeric(20, 2), nullable=False),
        sa.Column('capital_available', sa.Numeric(20, 2), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(20, 2), server_default='0'),
        sa.Column('realized_pnl', sa.Numeric(20, 2), server_default='0'),
        sa.Column('daily_pnl', sa.Numeric(20, 2), server_default='0'),
        sa.Column('daily_pnl_pct', sa.Numeric(10, 6), server_default='0'),
        sa.Column('total_pnl_pct', sa.Numeric(10, 6), server_default='0'),
        sa.Column('max_drawdown_pct', sa.Numeric(10, 6), server_default='0'),
        sa.Column('open_positions', sa.Integer(), server_default='0'),
        sa.Column('positions', sa.JSON),
        sa.Column('base_currency', sa.String(10), server_default='USD'),
    )
    op.create_index('idx_portfolio_snapshots_captured', 'portfolio_snapshots', ['captured_at'])
    op.create_index('idx_portfolio_snapshots_portfolio', 'portfolio_snapshots', ['portfolio_id'])

    # Backtest results table
    op.create_table(
        'backtest_results',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('strategy_id', sa.String(50), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sharpe_ratio', sa.Numeric(10, 4)),
        sa.Column('sortino_ratio', sa.Numeric(10, 4)),
        sa.Column('max_drawdown_pct', sa.Numeric(10, 4)),
        sa.Column('win_rate', sa.Numeric(5, 4)),
        sa.Column('total_return_pct', sa.Numeric(10, 4)),
        sa.Column('total_trades', sa.Integer()),
        sa.Column('profit_factor', sa.Numeric(10, 4)),
        sa.Column('metrics', sa.JSON),
        sa.Column('passed_quality_gate', sa.Boolean(), server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('idx_backtest_strategy', 'backtest_results', ['strategy_id'])
    op.create_index('idx_backtest_symbol', 'backtest_results', ['symbol'])
    op.create_index('idx_backtest_dates', 'backtest_results', ['start_date', 'end_date'])


def downgrade() -> None:
    op.drop_table('backtest_results')
    op.drop_table('portfolio_snapshots')
    op.drop_table('users')