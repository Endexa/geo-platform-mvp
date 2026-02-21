"""add auth fields to profile

Revision ID: 001
Revises:
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add auth fields to profiles table
    op.add_column('profiles', sa.Column('email', sa.String(), nullable=False))
    op.add_column('profiles', sa.Column('password_hash', sa.String(), nullable=False))
    op.add_column('profiles', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=True))
    op.create_index(op.f('ix_profiles_email'), 'profiles', ['email'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_profiles_email'), table_name='profiles')
    op.drop_column('profiles', 'is_active')
    op.drop_column('profiles', 'password_hash')
    op.drop_column('profiles', 'email')
