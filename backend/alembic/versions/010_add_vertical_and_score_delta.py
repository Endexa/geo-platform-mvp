"""add vertical and estimated_score_delta columns

Revision ID: 010
Revises: 009
Create Date: 2026-02-26

Adds:
- audits.vertical (String, nullable) -- detected site vertical for recommendation filtering
- audit_recommendations.estimated_score_delta (Numeric(4,1), nullable) -- estimated score improvement
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "audits",
        sa.Column("vertical", sa.String(), nullable=True),
    )
    op.add_column(
        "audit_recommendations",
        sa.Column(
            "estimated_score_delta",
            sa.Numeric(precision=4, scale=1),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("audit_recommendations", "estimated_score_delta")
    op.drop_column("audits", "vertical")
