"""Add citability, llmstxt, and platform presence tables

Revision ID: 016_citability_llmstxt_brand
Revises: 015_add_code_analysis
Create Date: 2026-03-26 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '016_citability_llmstxt_brand'
down_revision = '015_add_code_analysis'
branch_labels = None
depends_on = None


def upgrade():
    # Create citability_scores table
    op.create_table(
        'citability_scores',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_url', sa.String(length=2048), nullable=False),
        sa.Column('heading', sa.String(length=500), nullable=True),
        sa.Column('content_preview', sa.Text(), nullable=True),
        sa.Column('word_count', sa.Integer(), nullable=False),
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('grade', sa.String(length=1), nullable=False),
        sa.Column('label', sa.String(length=50), nullable=False),
        sa.Column('breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_citability_scores_audit_id'), 'citability_scores', ['audit_id'], unique=False)
    op.create_index(op.f('ix_citability_scores_id'), 'citability_scores', ['id'], unique=False)

    # Create page_citability_analyses table
    op.create_table(
        'page_citability_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('page_url', sa.String(length=2048), nullable=False),
        sa.Column('total_blocks_analyzed', sa.Integer(), nullable=False),
        sa.Column('average_citability_score', sa.Float(), nullable=False),
        sa.Column('optimal_length_passages', sa.Integer(), nullable=False),
        sa.Column('grade_distribution', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('top_5_citable', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('bottom_5_citable', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('page_url')
    )
    op.create_index(op.f('ix_page_citability_analyses_audit_id'), 'page_citability_analyses', ['audit_id'], unique=False)
    op.create_index(op.f('ix_page_citability_analyses_id'), 'page_citability_analyses', ['id'], unique=False)

    # Create llms_txt_analyses table
    op.create_table(
        'llms_txt_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('website_url', sa.String(length=2048), nullable=False),
        sa.Column('llms_txt_url', sa.String(length=2048), nullable=False),
        sa.Column('llms_txt_exists', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('format_valid', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_title', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_description', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_sections', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_links', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('section_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('link_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('existing_content', sa.Text(), nullable=True),
        sa.Column('issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('llms_full_txt_exists', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('generated_llmstxt', sa.Text(), nullable=True),
        sa.Column('generated_llmstxt_full', sa.Text(), nullable=True),
        sa.Column('pages_analyzed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sections', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_llms_txt_analyses_audit_id'), 'llms_txt_analyses', ['audit_id'], unique=False)
    op.create_index(op.f('ix_llms_txt_analyses_id'), 'llms_txt_analyses', ['id'], unique=False)

    # Create brand_scans table
    op.create_table(
        'brand_scans',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('brand_name', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=500), nullable=True),
        sa.Column('analysis_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('key_insight', sa.Text(), nullable=False, server_default="Brand mentions correlate 3x more strongly with AI visibility than backlinks (Ahrefs Dec 2025, 75K brands)"),
        sa.Column('overall_recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_brand_scans_audit_id'), 'brand_scans', ['audit_id'], unique=False)
    op.create_index(op.f('ix_brand_scans_id'), 'brand_scans', ['id'], unique=False)

    # Create platform_presences table
    op.create_table(
        'platform_presences',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('brand_scan_id', sa.Integer(), nullable=False),
        sa.Column('platform_name', sa.String(length=100), nullable=False),
        sa.Column('correlation', sa.Float(), nullable=True),
        sa.Column('weight', sa.String(length=10), nullable=True),
        sa.Column('has_official_presence', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('has_mentions', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('search_url', sa.String(length=2048), nullable=False),
        sa.Column('platform_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('check_instructions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['brand_scan_id'], ['brand_scans.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_platform_presences_brand_scan_id'), 'platform_presences', ['brand_scan_id'], unique=False)
    op.create_index(op.f('ix_platform_presences_id'), 'platform_presences', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_platform_presences_id'), table_name='platform_presences')
    op.drop_index(op.f('ix_platform_presences_brand_scan_id'), table_name='platform_presences')
    op.drop_table('platform_presences')

    op.drop_index(op.f('ix_brand_scans_id'), table_name='brand_scans')
    op.drop_index(op.f('ix_brand_scans_audit_id'), table_name='brand_scans')
    op.drop_table('brand_scans')

    op.drop_index(op.f('ix_llms_txt_analyses_id'), table_name='llms_txt_analyses')
    op.drop_index(op.f('ix_llms_txt_analyses_audit_id'), table_name='llms_txt_analyses')
    op.drop_table('llms_txt_analyses')

    op.drop_index(op.f('ix_page_citability_analyses_id'), table_name='page_citability_analyses')
    op.drop_index(op.f('ix_page_citability_analyses_audit_id'), table_name='page_citability_analyses')
    op.drop_table('page_citability_analyses')

    op.drop_index(op.f('ix_citability_scores_id'), table_name='citability_scores')
    op.drop_index(op.f('ix_citability_scores_audit_id'), table_name='citability_scores')
    op.drop_table('citability_scores')
