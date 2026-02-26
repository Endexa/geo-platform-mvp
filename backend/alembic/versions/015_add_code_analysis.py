"""add code_analyses and code_recommendations tables

Revision ID: 015
Revises: 014
Create Date: 2026-02-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create code_analyses table first (referenced by code_recommendations FK)
    op.create_table(
        "code_analyses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("raw_output", sa.Text(), nullable=False),
        sa.Column("raw_output_size_bytes", sa.Integer(), nullable=False),
        sa.Column("detected_framework", sa.String(), nullable=True),
        sa.Column("parsed_findings", JSONB, nullable=True),
        sa.Column("prompt_categories_used", JSONB, nullable=True),
        sa.Column("model_used", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_code_analyses_audit_id", "code_analyses", ["audit_id"]
    )
    op.create_index(
        "idx_code_analyses_user_id", "code_analyses", ["user_id"]
    )

    # Create code_recommendations table (FK to code_analyses)
    op.create_table(
        "code_recommendations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "code_analysis_id",
            UUID(as_uuid=True),
            sa.ForeignKey("code_analyses.id"),
            nullable=False,
        ),
        sa.Column(
            "audit_id",
            UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column("criterion_id", sa.String(), nullable=True),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("severity", sa.String(), nullable=False),
        sa.Column("finding", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=True),
        sa.Column("suggestion", sa.Text(), nullable=False),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "idx_code_recs_code_analysis_id",
        "code_recommendations",
        ["code_analysis_id"],
    )
    op.create_index(
        "idx_code_recs_audit_id", "code_recommendations", ["audit_id"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("idx_code_recs_audit_id", table_name="code_recommendations")
    op.drop_index(
        "idx_code_recs_code_analysis_id", table_name="code_recommendations"
    )
    op.drop_table("code_recommendations")

    op.drop_index("idx_code_analyses_user_id", table_name="code_analyses")
    op.drop_index("idx_code_analyses_audit_id", table_name="code_analyses")
    op.drop_table("code_analyses")
