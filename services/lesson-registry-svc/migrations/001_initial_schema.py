"""
Database migration: Create lesson registry tables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-08-14 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial lesson registry schema."""
    
    # Create lesson table
    op.create_table(
        'lesson',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('subject', sa.String(100), nullable=False),
        sa.Column('grade_level', sa.String(20)),
        sa.Column('topic', sa.String(200)),
        sa.Column('curriculum_standard', sa.String(100)),
        sa.Column('difficulty_level', sa.String(20), default='intermediate'),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('published_at', sa.DateTime()),
    )
    
    # Create version table
    op.create_table(
        'version',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('lesson_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version_number', sa.String(20), nullable=False),
        sa.Column('version_name', sa.String(100)),
        sa.Column('changelog', sa.Text()),
        sa.Column('content_type', sa.String(50), default='interactive'),
        sa.Column('duration_minutes', sa.Integer()),
        sa.Column('learning_objectives', sa.Text()),
        sa.Column('status', sa.String(20), default='draft'),
        sa.Column('is_current', sa.Boolean, default=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('published_at', sa.DateTime()),
        sa.Column('manifest_checksum', sa.String(64)),
        sa.Column('total_assets', sa.Integer, default=0),
        sa.Column('total_size_bytes', sa.BigInteger, default=0),
        sa.ForeignKeyConstraint(['lesson_id'], ['lesson.id'], ondelete='CASCADE'),
    )
    
    # Create asset table
    op.create_table(
        'asset',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('s3_key', sa.String(500), nullable=False),
        sa.Column('asset_path', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.BigInteger, nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('asset_type', sa.String(50), nullable=False),
        sa.Column('is_entry_point', sa.Boolean, default=False),
        sa.Column('is_required', sa.Boolean, default=True),
        sa.Column('cache_duration_seconds', sa.Integer, default=3600),
        sa.Column('compression_enabled', sa.Boolean, default=True),
        sa.Column('uploaded_at', sa.DateTime, server_default=sa.func.now()),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('validated_at', sa.DateTime()),
        sa.Column('validation_status', sa.String(20), default='pending'),
        sa.ForeignKeyConstraint(['version_id'], ['version.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for performance
    
    # Lesson indexes
    op.create_index('idx_lesson_title', 'lesson', ['title'])
    op.create_index('idx_lesson_subject', 'lesson', ['subject'])
    op.create_index('idx_lesson_grade_level', 'lesson', ['grade_level'])
    op.create_index('idx_lesson_topic', 'lesson', ['topic'])
    op.create_index('idx_lesson_status', 'lesson', ['status'])
    op.create_index('idx_lesson_created_by', 'lesson', ['created_by'])
    op.create_index('idx_lesson_created_at', 'lesson', ['created_at'])
    op.create_index('idx_lesson_is_active', 'lesson', ['is_active'])
    op.create_index('idx_lesson_published_at', 'lesson', ['published_at'])
    op.create_index('idx_lesson_subject_grade', 'lesson', ['subject', 'grade_level'])
    op.create_index('idx_lesson_status_active', 'lesson', ['status', 'is_active'])
    op.create_index('idx_lesson_created_by_date', 'lesson', ['created_by', 'created_at'])
    
    # Version indexes
    op.create_index('idx_version_lesson_id', 'version', ['lesson_id'])
    op.create_index('idx_version_status', 'version', ['status'])
    op.create_index('idx_version_is_current', 'version', ['is_current'])
    op.create_index('idx_version_created_by', 'version', ['created_by'])
    op.create_index('idx_version_created_at', 'version', ['created_at'])
    op.create_index('idx_version_published_at', 'version', ['published_at'])
    op.create_index('idx_version_lesson_number', 'version', ['lesson_id', 'version_number'], unique=True)
    op.create_index('idx_version_current', 'version', ['lesson_id', 'is_current'])
    op.create_index('idx_version_status_published', 'version', ['status', 'published_at'])
    
    # Asset indexes
    op.create_index('idx_asset_version_id', 'asset', ['version_id'])
    op.create_index('idx_asset_s3_key', 'asset', ['s3_key'])
    op.create_index('idx_asset_checksum', 'asset', ['checksum'])
    op.create_index('idx_asset_asset_type', 'asset', ['asset_type'])
    op.create_index('idx_asset_uploaded_at', 'asset', ['uploaded_at'])
    op.create_index('idx_asset_uploaded_by', 'asset', ['uploaded_by'])
    op.create_index('idx_asset_validated_at', 'asset', ['validated_at'])
    op.create_index('idx_asset_version_path', 'asset', ['version_id', 'asset_path'], unique=True)
    op.create_index('idx_asset_type_required', 'asset', ['asset_type', 'is_required'])
    op.create_index('idx_asset_checksum_size', 'asset', ['checksum', 'size_bytes'])
    op.create_index('idx_asset_uploaded', 'asset', ['uploaded_at', 'uploaded_by'])


def downgrade():
    """Drop lesson registry schema."""
    op.drop_table('asset')
    op.drop_table('version')
    op.drop_table('lesson')
