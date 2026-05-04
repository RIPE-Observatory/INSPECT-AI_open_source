"""add_processing_time_seconds_to_jobs

Revision ID: bcd8c4e76504
Revises: c5ff50a895dc
Create Date: 2025-10-06 19:12:10.591292

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcd8c4e76504'
down_revision: Union[str, None] = 'c5ff50a895dc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jobs', sa.Column('processing_time_seconds', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'processing_time_seconds')
