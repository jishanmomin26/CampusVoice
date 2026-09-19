"""add google identity to users

Revision ID: 004_add_google_identity_to_users
Revises: 003_create_users
Create Date: 2026-09-19 18:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_add_google_identity_to_users'
down_revision: Union[str, None] = '003_create_users'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add nullable google_sub column and unique index to users table."""
    op.add_column('users', sa.Column('google_sub', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_users_google_sub'), 'users', ['google_sub'], unique=True)


def downgrade() -> None:
    """Drop google_sub index and column to safely revert to revision 003."""
    op.drop_index(op.f('ix_users_google_sub'), table_name='users')
    op.drop_column('users', 'google_sub')
