"""Add reviewer table and job foreign key

Revision ID: d2b7ef9c0a5f
Revises: bcd8c4e76504
Create Date: 2025-10-20 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "d2b7ef9c0a5f"
down_revision = "bcd8c4e76504"
branch_labels = None
depends_on = None


KG_VISIBILITY_ENUM_NAME = "kg_visibility_enum"


def upgrade() -> None:
    # Create enum type using raw SQL to avoid SQLAlchemy auto-creation issues
    op.execute("CREATE TYPE kg_visibility_enum AS ENUM ('anonymous', 'public')")

    op.create_table(
        "reviewers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("clerk_user_id", sa.String(length=150), nullable=False),
        sa.Column("given_name", sa.String(length=150), nullable=True),
        sa.Column("family_name", sa.String(length=150), nullable=True),
        sa.Column("username", sa.String(length=150), nullable=True),
        sa.Column("affiliation_institution", sa.String(length=255), nullable=True),
        sa.Column("affiliation_department", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=150), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("orcid", sa.String(length=19), nullable=True),
        sa.Column("onboarding_complete", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "kg_visibility",
            postgresql.ENUM("anonymous", "public", name=KG_VISIBILITY_ENUM_NAME, create_type=False),
            nullable=False,
            server_default="anonymous",
        ),
        sa.Column("kg_visibility_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_reviewers_clerk_user_id", "reviewers", ["clerk_user_id"], unique=False)
    op.create_unique_constraint("uq_reviewers_clerk_user_id", "reviewers", ["clerk_user_id"])

    op.add_column(
        "jobs",
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_jobs_reviewer_id", "jobs", ["reviewer_id"], unique=False)
    op.create_foreign_key(
        "fk_jobs_reviewer_id",
        "jobs",
        "reviewers",
        ["reviewer_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint("fk_jobs_reviewer_id", "jobs", type_="foreignkey")
    op.drop_index("ix_jobs_reviewer_id", table_name="jobs")
    op.drop_column("jobs", "reviewer_id")

    op.drop_constraint("uq_reviewers_clerk_user_id", "reviewers", type_="unique")
    op.drop_index("ix_reviewers_clerk_user_id", table_name="reviewers")
    op.drop_table("reviewers")

    # Drop enum type using raw SQL
    op.execute("DROP TYPE IF EXISTS kg_visibility_enum")
