"""create base tables and auth fields

Revision ID: 001
Revises:
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('subscription_tier', sa.String(), server_default='free'),
        sa.Column('stripe_customer_id', sa.String(), nullable=True),
    )

    # Create profiles table (with auth fields)
    op.create_table(
        'profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('role', sa.String(), server_default='member'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
    )
    op.create_index(op.f('ix_profiles_email'), 'profiles', ['email'], unique=True)

    # Create websites table
    op.create_table(
        'websites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=True),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('sitemap_url', sa.String(), nullable=True),
        sa.Column('last_crawled_at', sa.DateTime(), nullable=True),
    )

    # Create analyses table
    op.create_table(
        'analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('website_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('websites.id'), nullable=False),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('geo_score', sa.Integer(), nullable=True),
        sa.Column('visibility_score', sa.Integer(), nullable=True),
        sa.Column('readability_score', sa.Integer(), nullable=True),
        sa.Column('authority_score', sa.Integer(), nullable=True),
        sa.Column('raw_data', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # Create recommendations table
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('analysis_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('analyses.id'), nullable=False),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('issue', sa.Text(), nullable=False),
        sa.Column('action_plan', sa.Text(), nullable=False),
        sa.Column('impact_score', sa.String(), nullable=True),
        sa.Column('implemented', sa.Boolean(), server_default='false'),
        sa.Column('jira_ticket_id', sa.String(), nullable=True),
    )

    # Create brand_voice_configs table
    op.create_table(
        'brand_voice_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
    )

    # Create voice_vectors table (uses pgvector)
    op.create_table(
        'voice_vectors',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brand_voice_configs.id'), nullable=False),
        sa.Column('content_chunk', sa.Text(), nullable=False),
    )
    op.execute('ALTER TABLE voice_vectors ADD COLUMN embedding vector(1536)')

    # Create voice_rules table
    op.create_table(
        'voice_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('config_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('brand_voice_configs.id'), nullable=False),
        sa.Column('rule_type', sa.String(), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('voice_rules')
    op.drop_table('voice_vectors')
    op.drop_table('brand_voice_configs')
    op.drop_table('recommendations')
    op.drop_table('analyses')
    op.drop_table('websites')
    op.drop_index(op.f('ix_profiles_email'), table_name='profiles')
    op.drop_table('profiles')
    op.drop_table('organizations')
    op.execute('DROP EXTENSION IF EXISTS vector')
