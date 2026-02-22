"""add audits and audit_queries tables

Revision ID: 003
Revises: 002
Create Date: 2026-02-22

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create audits table
    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=False,
        ),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="pending"
        ),
        sa.Column("crawl_data", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create audit_queries table
    op.create_table(
        "audit_queries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audits.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("query_text", sa.String(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_audit_queries_audit_id",
        "audit_queries",
        ["audit_id"],
    )

    # Add FK from existing audit_cost_ledger.audit_id to audits.id
    # NOTE: This will fail if orphan rows exist in audit_cost_ledger
    # (rows with audit_id values that don't exist in audits).
    # If that happens, clean orphan rows first:
    #   DELETE FROM audit_cost_ledger WHERE audit_id NOT IN (SELECT id FROM audits);
    try:
        op.create_foreign_key(
            "fk_audit_cost_ledger_audit_id",
            "audit_cost_ledger",
            "audits",
            ["audit_id"],
            ["id"],
        )
    except Exception as e:
        logger.warning(
            "Could not create FK from audit_cost_ledger.audit_id to audits.id: %s. "
            "This likely means orphan rows exist in audit_cost_ledger. "
            "Clean them with: DELETE FROM audit_cost_ledger WHERE audit_id NOT IN (SELECT id FROM audits);",
            e,
        )


def downgrade() -> None:
    # Drop FK constraint (may not exist if upgrade failed on that step)
    try:
        op.drop_constraint(
            "fk_audit_cost_ledger_audit_id",
            "audit_cost_ledger",
            type_="foreignkey",
        )
    except Exception:
        pass

    op.drop_index("ix_audit_queries_audit_id", table_name="audit_queries")
    op.drop_table("audit_queries")
    op.drop_table("audits")
