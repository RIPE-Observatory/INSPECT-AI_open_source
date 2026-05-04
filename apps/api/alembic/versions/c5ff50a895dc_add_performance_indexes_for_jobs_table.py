"""Add performance indexes for jobs table

Revision ID: c5ff50a895dc
Revises: 418fe11b4307
Create Date: 2025-07-23 17:23:41.151825

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c5ff50a895dc"
down_revision: Union[str, None] = "418fe11b4307"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for jobs table."""
    # Add index on created_at for temporal queries
    op.create_index("ix_jobs_created_at", "jobs", ["created_at"])

    # Add index on updated_at for recent job lookups
    op.create_index("ix_jobs_updated_at", "jobs", ["updated_at"])

    # Add index on source for filtering by job source
    op.create_index("ix_jobs_source", "jobs", ["source"])

    # Add composite index for status + created_at (common query pattern)
    op.create_index("ix_jobs_status_created_at", "jobs", ["status", "created_at"])


def downgrade() -> None:
    """Remove performance indexes for jobs table."""
    # Remove indexes in reverse order
    op.drop_index("ix_jobs_status_created_at", table_name="jobs")
    op.drop_index("ix_jobs_source", table_name="jobs")
    op.drop_index("ix_jobs_updated_at", table_name="jobs")
    op.drop_index("ix_jobs_created_at", table_name="jobs")
