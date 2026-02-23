"""add brands table and brand_id FK to audits

Revision ID: 009
Revises: 008
Create Date: 2026-02-23

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create brands table
    op.create_table(
        "brands",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
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
        sa.UniqueConstraint("user_id", "domain", name="uq_brands_user_domain"),
    )
    op.create_index("ix_brands_user_id", "brands", ["user_id"])

    # Add brand_id FK column to audits
    op.add_column(
        "audits",
        sa.Column(
            "brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brands.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_audits_brand_id", "audits", ["brand_id"])


def downgrade() -> None:
    op.drop_index("ix_audits_brand_id", table_name="audits")
    op.drop_column("audits", "brand_id")
    op.drop_index("ix_brands_user_id", table_name="brands")
    op.drop_table("brands")
