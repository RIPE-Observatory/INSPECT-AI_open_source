"""add email to reviewers

Revision ID: e8f3d6a2b1c4
Revises: d2b7ef9c0a5f
Create Date: 2025-10-11 22:30:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e8f3d6a2b1c4"
down_revision = "d2b7ef9c0a5f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("reviewers", sa.Column("email", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_reviewers_email"), "reviewers", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reviewers_email"), table_name="reviewers")
    op.drop_column("reviewers", "email")
