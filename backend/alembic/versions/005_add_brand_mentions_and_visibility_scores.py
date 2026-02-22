"""add brand_mentions and visibility_scores tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create brand_mentions table
    op.create_table(
        "brand_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "engine_response_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("engine_responses.id"),
            nullable=False,
        ),
        sa.Column("matched_text", sa.String(), nullable=False),
        sa.Column("match_type", sa.String(), nullable=False),
        sa.Column("confidence", sa.Integer(), nullable=False),
        sa.Column("char_offset", sa.Integer(), nullable=False),
        sa.Column("context_quote", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_brand_mentions_engine_response_id",
        "brand_mentions",
        ["engine_response_id"],
    )

    # Create visibility_scores table
    op.create_table(
        "visibility_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("per_engine_scores", postgresql.JSONB(), nullable=False),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("query_mention_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("algorithm_version", sa.String(), nullable=False, server_default=sa.text("'v1'")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_visibility_scores_audit_id",
        "visibility_scores",
        ["audit_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_visibility_scores_audit_id", table_name="visibility_scores")
    op.drop_table("visibility_scores")
    op.drop_index("ix_brand_mentions_engine_response_id", table_name="brand_mentions")
    op.drop_table("brand_mentions")
