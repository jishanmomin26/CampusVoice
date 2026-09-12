"""create feedback table

Revision ID: 001_create_feedback
Revises: 
Create Date: 2026-09-12 21:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_create_feedback'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'feedback',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('department', sa.String(length=100), nullable=False),
        sa.Column('semester', sa.String(length=20), nullable=False),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_table('feedback')
