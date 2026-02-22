"""add audit cost ledger

Revision ID: 002
Revises: 001
Create Date: 2026-02-22

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_cost_ledger",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("engine", sa.String(), nullable=False),
        sa.Column("model", sa.String(), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("cached", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_audit_cost_ledger_audit_id",
        "audit_cost_ledger",
        ["audit_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_cost_ledger_audit_id", table_name="audit_cost_ledger")
    op.drop_table("audit_cost_ledger")
