"""add is_competitor to brands and competitor_brand_id FK to discovered_competitors

Revision ID: 010
Revises: 009
Create Date: 2026-02-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add is_competitor column to brands table
    op.add_column(
        "brands",
        sa.Column(
            "is_competitor",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
    )

    # Add competitor_brand_id FK column to discovered_competitors table
    op.add_column(
        "discovered_competitors",
        sa.Column(
            "competitor_brand_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("brands.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_discovered_competitors_competitor_brand_id",
        "discovered_competitors",
        ["competitor_brand_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_discovered_competitors_competitor_brand_id",
        table_name="discovered_competitors",
    )
    op.drop_column("discovered_competitors", "competitor_brand_id")
    op.drop_column("brands", "is_competitor")
