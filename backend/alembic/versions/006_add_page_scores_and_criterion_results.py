"""add page_scores and criterion_results tables, optimization_score to audits

Revision ID: 006
Revises: 005
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create page_scores table
    op.create_table(
        "page_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column("page_url", sa.String(), nullable=False),
        sa.Column("page_title", sa.String(), nullable=True),
        sa.Column("crawl_data", postgresql.JSONB(), nullable=True),
        sa.Column("crawlability_score", sa.Integer(), nullable=True),
        sa.Column("content_structure_score", sa.Integer(), nullable=True),
        sa.Column("structured_data_score", sa.Integer(), nullable=True),
        sa.Column("authority_score", sa.Integer(), nullable=True),
        sa.Column("overall_page_score", sa.Integer(), nullable=True),
        sa.Column(
            "internal_link_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "was_scored",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_page_scores_audit_id",
        "page_scores",
        ["audit_id"],
    )

    # Create criterion_results table
    op.create_table(
        "criterion_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "page_score_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("page_scores.id"),
            nullable=False,
        ),
        sa.Column("criterion_id", sa.String(), nullable=False),
        sa.Column("criterion_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "max_score",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "is_binary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("human_summary", sa.Text(), nullable=False),
        sa.Column("technical_detail", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column(
            "checked",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_criterion_results_page_score_id",
        "criterion_results",
        ["page_score_id"],
    )

    # Add optimization_score column to audits table
    op.add_column(
        "audits",
        sa.Column("optimization_score", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audits", "optimization_score")
    op.drop_index(
        "ix_criterion_results_page_score_id", table_name="criterion_results"
    )
    op.drop_table("criterion_results")
    op.drop_index("ix_page_scores_audit_id", table_name="page_scores")
    op.drop_table("page_scores")
