"""add user status and role checks

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18 17:16:04.887615

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004'
down_revision: Union[str, Sequence[str], None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('status', sa.String(length=20), server_default='active', nullable=False))
    op.create_check_constraint('ck_users_status', 'users', "status IN ('active', 'suspended', 'inactive')")
    op.create_check_constraint('ck_users_role', 'users', "role IN ('customer', 'admin', 'operator')")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_users_role', 'users', type_='check')
    op.drop_constraint('ck_users_status', 'users', type_='check')
    op.drop_column('users', 'status')
