"""add discovered_competitors, competitor_audits tables, citations to engine_responses, is_custom/is_editable to audit_queries

Revision ID: 007
Revises: 006
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create competitor_audits table first (referenced by discovered_competitors FK)
    op.create_table(
        "competitor_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parent_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column("competitor_name", sa.String(), nullable=False),
        sa.Column("competitor_url", sa.String(), nullable=False),
        sa.Column("crawl_data", postgresql.JSONB(), nullable=True),
        sa.Column("optimization_score", sa.Integer(), nullable=True),
        sa.Column("crawlability_avg", sa.Integer(), nullable=True),
        sa.Column("content_structure_avg", sa.Integer(), nullable=True),
        sa.Column("structured_data_avg", sa.Integer(), nullable=True),
        sa.Column("authority_avg", sa.Integer(), nullable=True),
        sa.Column(
            "pages_scored",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_competitor_audits_parent_audit_id",
        "competitor_audits",
        ["parent_audit_id"],
    )

    # Create discovered_competitors table
    op.create_table(
        "discovered_competitors",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column("entity_name", sa.String(), nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("mention_count", sa.Integer(), nullable=False),
        sa.Column("share_of_voice", sa.Numeric(5, 1), nullable=False),
        sa.Column("engines_mentioned_in", postgresql.JSONB(), nullable=True),
        sa.Column("queries_mentioned_in", postgresql.JSONB(), nullable=True),
        sa.Column("resolved_url", sa.String(), nullable=True),
        sa.Column(
            "is_crawled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_user_brand",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "competitor_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("competitor_audits.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_discovered_competitors_audit_id",
        "discovered_competitors",
        ["audit_id"],
    )

    # Add citations JSONB column to engine_responses
    op.add_column(
        "engine_responses",
        sa.Column("citations", postgresql.JSONB(), nullable=True),
    )

    # Add is_custom and is_editable columns to audit_queries
    op.add_column(
        "audit_queries",
        sa.Column(
            "is_custom",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "audit_queries",
        sa.Column(
            "is_editable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("audit_queries", "is_editable")
    op.drop_column("audit_queries", "is_custom")
    op.drop_column("engine_responses", "citations")
    op.drop_index(
        "ix_discovered_competitors_audit_id",
        table_name="discovered_competitors",
    )
    op.drop_table("discovered_competitors")
    op.drop_index(
        "ix_competitor_audits_parent_audit_id",
        table_name="competitor_audits",
    )
    op.drop_table("competitor_audits")
