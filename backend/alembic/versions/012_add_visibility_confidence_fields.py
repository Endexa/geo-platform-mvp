"""add confidence_level, engines_queried, engines_skipped to visibility_scores

Revision ID: 012
Revises: 011
Create Date: 2026-02-26

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visibility_scores",
        sa.Column(
            "confidence_level",
            sa.String(),
            nullable=False,
            server_default="low",
        ),
    )
    op.add_column(
        "visibility_scores",
        sa.Column(
            "engines_queried",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "visibility_scores",
        sa.Column(
            "engines_skipped",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("visibility_scores", "engines_skipped")
    op.drop_column("visibility_scores", "engines_queried")
    op.drop_column("visibility_scores", "confidence_level")
