"""add audit_recommendations, mention_sentiments tables, content_gaps to audits

Revision ID: 008
Revises: 007
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audit_recommendations table
    op.create_table(
        "audit_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column("page_url", sa.String(), nullable=True),
        sa.Column("criterion_id", sa.String(), nullable=False),
        sa.Column("criterion_name", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("impact_label", sa.String(), nullable=False),
        sa.Column("impact_pct", sa.Integer(), nullable=True),
        sa.Column("user_score", sa.Integer(), nullable=False),
        sa.Column("competitor_avg", sa.Integer(), nullable=True),
        sa.Column("gap_score", sa.Integer(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "action_steps",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("code_snippet", sa.Text(), nullable=True),
        sa.Column("evidence_source", sa.String(), nullable=False),
        sa.Column("recommendation_hash", sa.String(16), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default=sa.text("'open'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_audit_recommendations_audit_id",
        "audit_recommendations",
        ["audit_id"],
    )
    op.create_index(
        "ix_audit_recommendations_recommendation_hash",
        "audit_recommendations",
        ["recommendation_hash"],
    )

    # Create mention_sentiments table
    op.create_table(
        "mention_sentiments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column(
            "brand_mention_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brand_mentions.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("context_quote", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_mention_sentiments_audit_id",
        "mention_sentiments",
        ["audit_id"],
    )

    # Add content_gaps JSONB column to audits
    op.add_column(
        "audits",
        sa.Column("content_gaps", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("audits", "content_gaps")
    op.drop_index(
        "ix_mention_sentiments_audit_id",
        table_name="mention_sentiments",
    )
    op.drop_table("mention_sentiments")
    op.drop_index(
        "ix_audit_recommendations_recommendation_hash",
        table_name="audit_recommendations",
    )
    op.drop_index(
        "ix_audit_recommendations_audit_id",
        table_name="audit_recommendations",
    )
    op.drop_table("audit_recommendations")
