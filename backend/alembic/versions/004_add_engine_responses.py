"""add engine_responses table

Revision ID: 004
Revises: 003
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "engine_responses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_query_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_queries.id"),
            nullable=False,
        ),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("model_version", sa.String(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("cost_usd", sa.Numeric(10, 6), nullable=False, server_default=sa.text("0")),
        sa.Column("cached", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_engine_responses_audit_query_id",
        "engine_responses",
        ["audit_query_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_engine_responses_audit_query_id", table_name="engine_responses")
    op.drop_table("engine_responses")
