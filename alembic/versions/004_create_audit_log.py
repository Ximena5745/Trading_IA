"""004_create_audit_log

Revision ID: 004
Revises: 003
Create Date: 2026-05-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('user_id', sa.String(64), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('entity_id', sa.String(64)),
        sa.Column('old_value', sa.JSON),
        sa.Column('new_value', sa.JSON),
    )
    op.create_index('idx_audit_timestamp', 'audit_log', ['timestamp'])
    op.create_index('idx_audit_user_id', 'audit_log', ['user_id'])
    op.create_index('idx_audit_entity', 'audit_log', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_action', 'audit_log', ['action'])


def downgrade() -> None:
    op.drop_table('audit_log')