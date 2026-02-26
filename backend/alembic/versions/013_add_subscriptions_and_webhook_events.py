"""add subscriptions and webhook_events tables

Revision ID: 013
Revises: 012
Create Date: 2026-02-26

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column(
            "tier", sa.String(), nullable=False, server_default="pro"
        ),
        sa.Column(
            "status", sa.String(), nullable=False, server_default="active"
        ),
        sa.Column(
            "current_period_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_subscriptions_stripe_customer_id",
        "subscriptions",
        ["stripe_customer_id"],
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )

    op.create_table(
        "webhook_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "stripe_event_id",
            sa.String(),
            unique=True,
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column(
            "status",
            sa.String(),
            nullable=False,
            server_default="received",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_webhook_events_stripe_event_id",
        "webhook_events",
        ["stripe_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("webhook_events")
    op.drop_table("subscriptions")
