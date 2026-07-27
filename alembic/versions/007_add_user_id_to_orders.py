"""007_add_user_id_to_orders

Revision ID: 007
Revises: 006
Create Date: 2026-07-26

Description: Add user_id to orders — closes IDOR on get_order/cancel_order
(order ownership was never tracked, so any authenticated user could
read/cancel any order by guessing/enumerating its ID).

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '007'
down_revision: Union[str, None] = '006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('orders', sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id')))
    op.create_index('idx_orders_user_id', 'orders', ['user_id'])


def downgrade() -> None:
    op.drop_index('idx_orders_user_id', table_name='orders')
    op.drop_column('orders', 'user_id')
