"""add analysis fields to feedback table

Revision ID: 002_add_analysis_fields
Revises: 001_create_feedback
Create Date: 2026-09-14 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_add_analysis_fields'
down_revision: Union[str, None] = '001_create_feedback'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema to persist feedback intelligence and priority results."""
    # 1. Alter department and semester to nullable=True
    # Allows feedback submitted through the analysis workflow to be stored cleanly without fake placeholders
    op.alter_column('feedback', 'department', existing_type=sa.String(length=100), nullable=True)
    op.alter_column('feedback', 'semester', existing_type=sa.String(length=20), nullable=True)

    # 2. Add nullable columns for analysis and priority scoring results
    op.add_column('feedback', sa.Column('clean_text', sa.Text(), nullable=True))
    op.add_column('feedback', sa.Column('sentiment_label', sa.Integer(), nullable=True))
    op.add_column('feedback', sa.Column('sentiment_name', sa.String(length=50), nullable=True))
    op.add_column('feedback', sa.Column('sentiment_confidence', sa.Float(), nullable=True))
    op.add_column('feedback', sa.Column('category_name', sa.String(length=100), nullable=True))
    op.add_column('feedback', sa.Column('category_confidence', sa.Float(), nullable=True))
    op.add_column('feedback', sa.Column('priority_score', sa.Integer(), nullable=True))
    op.add_column('feedback', sa.Column('priority_level', sa.String(length=20), nullable=True))
    op.add_column('feedback', sa.Column('priority_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    """Revert analysis columns while protecting records containing NULL values from corruption."""
    # 1. Drop analysis columns added in Step 9.3
    op.drop_column('feedback', 'priority_reason')
    op.drop_column('feedback', 'priority_level')
    op.drop_column('feedback', 'priority_score')
    op.drop_column('feedback', 'category_confidence')
    op.drop_column('feedback', 'category_name')
    op.drop_column('feedback', 'sentiment_confidence')
    op.drop_column('feedback', 'sentiment_name')
    op.drop_column('feedback', 'sentiment_label')
    op.drop_column('feedback', 'clean_text')

    # 2. Reverting department and semester nullability:
    # PRECONDITION: In Step 9.3+, feedback records may legitimately contain NULL values for
    # 'department' or 'semester'. To prevent data loss and avoid silently inserting fake/misleading
    # placeholder strings (e.g. 'Unknown' or 'General'), this migration does NOT fabricate data.
    # If any records with NULL department or semester exist, reverting to NOT NULL will fail at the
    # database level. Administrators must manually triage or resolve NULL rows before enforcing NOT NULL.
    bind = op.get_bind()
    null_dept_count = bind.execute(
        sa.text("SELECT COUNT(*) FROM feedback WHERE department IS NULL OR semester IS NULL")
    ).scalar()

    if null_dept_count and null_dept_count > 0:
        raise RuntimeError(
            f"Cannot restore NOT NULL constraint on 'department' and 'semester': {null_dept_count} "
            "feedback record(s) contain NULL values. To protect data integrity and avoid injecting "
            "fake placeholder values, manual administrative review is required prior to downgrading."
        )

    op.alter_column('feedback', 'semester', existing_type=sa.String(length=20), nullable=False)
    op.alter_column('feedback', 'department', existing_type=sa.String(length=100), nullable=False)
