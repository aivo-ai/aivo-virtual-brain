"""
Database migration: Initial tables for Private Foundation Model Orchestrator.

Revision ID: 001_initial_tables
Revises: 
Create Date: 2024-01-15 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import text


# revision identifiers
revision = '001_initial_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create initial tables for the private FM orchestrator."""
    
    # Create namespaces table
    op.create_table(
        'learner_namespaces',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False, unique=True, index=True),
        sa.Column('status', sa.Enum('active', 'merging', 'corrupted', 'suspended', name='namespacestatus'), nullable=False, index=True),
        sa.Column('base_fm_version', sa.String(50), nullable=False),
        sa.Column('version_count', sa.Integer, nullable=False, default=1),
        sa.Column('current_checkpoint_hash', sa.String(128), nullable=False),
        sa.Column('encryption_key_hash', sa.String(128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_merge_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('guardian_deletable_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
    )
    
    # Create merge operations table
    op.create_table(
        'merge_operations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('namespace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('operation_type', sa.String(50), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'completed', 'failed', name='mergestatus'), nullable=False, index=True),
        sa.Column('source_checkpoint_hash', sa.String(128), nullable=False),
        sa.Column('target_checkpoint_hash', sa.String(128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('metadata', sa.JSON, nullable=True),
    )
    
    # Create event logs table
    op.create_table(
        'event_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('namespace_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column('event_type', sa.String(100), nullable=False, index=True),
        sa.Column('event_data', sa.JSON, nullable=False),
        sa.Column('checkpoint_hash', sa.String(128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_merge_operations_namespace',
        'merge_operations',
        'learner_namespaces',
        ['namespace_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'fk_event_logs_namespace',
        'event_logs',
        'learner_namespaces',
        ['namespace_id'],
        ['id'],
        ondelete='CASCADE'
    )
    
    # Create indexes for common query patterns
    op.create_index('idx_merge_ops_created_at', 'merge_operations', ['created_at'])
    op.create_index('idx_merge_ops_status_created', 'merge_operations', ['status', 'created_at'])
    op.create_index('idx_event_logs_type_created', 'event_logs', ['event_type', 'created_at'])
    op.create_index('idx_namespaces_updated_at', 'learner_namespaces', ['updated_at'])
    op.create_index('idx_namespaces_status_updated', 'learner_namespaces', ['status', 'updated_at'])
    
    # Create partial indexes for active namespaces (most common queries)
    op.execute(
        text("CREATE INDEX idx_active_namespaces ON learner_namespaces (learner_id, updated_at) WHERE status = 'active'")
    )
    
    # Create composite index for merge operations by namespace and status
    op.create_index('idx_merge_ops_ns_status', 'merge_operations', ['namespace_id', 'status'])


def downgrade():
    """Drop all tables and constraints."""
    
    # Drop indexes first
    op.drop_index('idx_merge_ops_ns_status')
    op.execute(text("DROP INDEX IF EXISTS idx_active_namespaces"))
    op.drop_index('idx_namespaces_status_updated')
    op.drop_index('idx_namespaces_updated_at')
    op.drop_index('idx_event_logs_type_created')
    op.drop_index('idx_merge_ops_status_created')
    op.drop_index('idx_merge_ops_created_at')
    
    # Drop foreign key constraints
    op.drop_constraint('fk_event_logs_namespace', 'event_logs', type_='foreignkey')
    op.drop_constraint('fk_merge_operations_namespace', 'merge_operations', type_='foreignkey')
    
    # Drop tables
    op.drop_table('event_logs')
    op.drop_table('merge_operations')
    op.drop_table('learner_namespaces')
    
    # Drop enums
    sa.Enum(name='namespacestatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='mergestatus').drop(op.get_bind(), checkfirst=True)
