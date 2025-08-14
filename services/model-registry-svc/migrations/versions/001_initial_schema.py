"""
AIVO Model Registry - Initial Schema Migration
S2-02 Implementation

Revision ID: 001_initial_schema  
Revises: 
Create Date: 2025-01-12 18:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create initial model registry schema"""
    
    # Create models table
    op.create_table('models',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('task', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create indexes for models table
    op.create_index('idx_model_task_subject', 'models', ['task', 'subject'])
    op.create_index('idx_model_created', 'models', ['created_at'])
    op.create_index(op.f('ix_models_name'), 'models', ['name'], unique=True)
    op.create_index(op.f('ix_models_task'), 'models', ['task'])
    op.create_index(op.f('ix_models_subject'), 'models', ['subject'])
    
    # Create model_versions table
    op.create_table('model_versions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('hash', sa.String(length=64), nullable=False),
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('region', sa.String(length=50), nullable=False),
        sa.Column('cost_per_1k', sa.Float(), nullable=True),
        sa.Column('eval_score', sa.Float(), nullable=True),
        sa.Column('slo_ok', sa.Boolean(), nullable=False),
        sa.Column('artifact_uri', sa.String(length=500), nullable=True),
        sa.Column('archive_uri', sa.String(length=500), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('model_type', sa.String(length=100), nullable=True),
        sa.Column('framework', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('archived_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['models.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id', 'hash', name='uq_model_version_hash'),
        sa.UniqueConstraint('model_id', 'version', name='uq_model_version')
    )
    
    # Create indexes for model_versions table
    op.create_index('idx_version_model_created', 'model_versions', ['model_id', 'created_at'])
    op.create_index('idx_version_eval_score', 'model_versions', ['eval_score'])
    op.create_index('idx_version_cost', 'model_versions', ['cost_per_1k'])
    op.create_index('idx_version_region', 'model_versions', ['region'])
    op.create_index(op.f('ix_model_versions_model_id'), 'model_versions', ['model_id'])
    op.create_index(op.f('ix_model_versions_hash'), 'model_versions', ['hash'])
    
    # Create provider_bindings table
    op.create_table('provider_bindings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('version_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_model_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('config', sa.Text(), nullable=True),
        sa.Column('endpoint_url', sa.String(length=500), nullable=True),
        sa.Column('avg_latency_ms', sa.Float(), nullable=True),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['version_id'], ['model_versions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('version_id', 'provider', name='uq_version_provider')
    )
    
    # Create indexes for provider_bindings table
    op.create_index('idx_binding_provider_status', 'provider_bindings', ['provider', 'status'])
    op.create_index('idx_binding_success_rate', 'provider_bindings', ['success_rate'])
    op.create_index('idx_binding_last_used', 'provider_bindings', ['last_used_at'])
    op.create_index(op.f('ix_provider_bindings_version_id'), 'provider_bindings', ['version_id'])
    op.create_index(op.f('ix_provider_bindings_provider'), 'provider_bindings', ['provider'])
    op.create_index(op.f('ix_provider_bindings_status'), 'provider_bindings', ['status'])


def downgrade() -> None:
    """Drop all model registry tables"""
    
    # Drop indexes first
    op.drop_index(op.f('ix_provider_bindings_status'), table_name='provider_bindings')
    op.drop_index(op.f('ix_provider_bindings_provider'), table_name='provider_bindings')
    op.drop_index(op.f('ix_provider_bindings_version_id'), table_name='provider_bindings')
    op.drop_index('idx_binding_last_used', table_name='provider_bindings')
    op.drop_index('idx_binding_success_rate', table_name='provider_bindings')
    op.drop_index('idx_binding_provider_status', table_name='provider_bindings')
    
    op.drop_index(op.f('ix_model_versions_hash'), table_name='model_versions')
    op.drop_index(op.f('ix_model_versions_model_id'), table_name='model_versions')
    op.drop_index('idx_version_region', table_name='model_versions')
    op.drop_index('idx_version_cost', table_name='model_versions')
    op.drop_index('idx_version_eval_score', table_name='model_versions')
    op.drop_index('idx_version_model_created', table_name='model_versions')
    
    op.drop_index(op.f('ix_models_subject'), table_name='models')
    op.drop_index(op.f('ix_models_task'), table_name='models')
    op.drop_index(op.f('ix_models_name'), table_name='models')
    op.drop_index('idx_model_created', table_name='models')
    op.drop_index('idx_model_task_subject', table_name='models')
    
    # Drop tables
    op.drop_table('provider_bindings')
    op.drop_table('model_versions')
    op.drop_table('models')
