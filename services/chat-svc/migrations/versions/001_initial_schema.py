"""Initial chat service schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2024-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create threads table
    op.create_table(
        'threads',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('learner_id', sa.String(36), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_by', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False),
    )
    
    # Create indexes for threads
    op.create_index('idx_threads_tenant_learner', 'threads', ['tenant_id', 'learner_id'])
    op.create_index('idx_threads_created_at', 'threads', ['created_at'])
    op.create_index('idx_threads_updated_at', 'threads', ['updated_at'])
    
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('thread_id', sa.String(36), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('sender_id', sa.String(36), nullable=False),
        sa.Column('sender_type', sa.String(50), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=False, default='text'),
        sa.Column('metadata', postgresql.JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=True),
        sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for messages
    op.create_index('idx_messages_thread_id', 'messages', ['thread_id'])
    op.create_index('idx_messages_created_at', 'messages', ['created_at'])
    op.create_index('idx_messages_sender', 'messages', ['sender_id'])
    
    # Create chat export logs table
    op.create_table(
        'chat_export_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('learner_id', sa.String(36), nullable=False),
        sa.Column('requested_by', sa.String(36), nullable=False),
        sa.Column('export_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes for export logs
    op.create_index('idx_export_tenant_learner', 'chat_export_logs', ['tenant_id', 'learner_id'])
    op.create_index('idx_export_status', 'chat_export_logs', ['status'])
    
    # Create chat deletion logs table
    op.create_table(
        'chat_deletion_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('learner_id', sa.String(36), nullable=False),
        sa.Column('requested_by', sa.String(36), nullable=False),
        sa.Column('deletion_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False),
        sa.Column('completed_at', sa.DateTime, nullable=True),
    )
    
    # Create indexes for deletion logs
    op.create_index('idx_deletion_tenant_learner', 'chat_deletion_logs', ['tenant_id', 'learner_id'])
    op.create_index('idx_deletion_status', 'chat_deletion_logs', ['status'])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('chat_deletion_logs')
    op.drop_table('chat_export_logs')
    op.drop_table('messages')
    op.drop_table('threads')
