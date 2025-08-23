"""
Add adapter reset request table (S5-08)

Migration to add support for per-subject adapter reset functionality
with approval workflow and execution tracking.

Revision ID: add_adapter_reset_table
Revises: previous_migration
Create Date: 2024-01-xx xx:xx:xx.xxxxxx
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_adapter_reset_table'
down_revision = 'previous_migration'  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add adapter reset request table and update event log table."""
    
    # Create adapter_reset_requests table
    op.create_table(
        'adapter_reset_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('learner_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requester_role', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('approval_request_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rejected_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=True),
        sa.Column('current_stage', sa.String(100), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('events_replayed', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for adapter_reset_requests
    op.create_index('idx_adapter_reset_learner_id', 'adapter_reset_requests', ['learner_id'])
    op.create_index('idx_adapter_reset_subject', 'adapter_reset_requests', ['subject'])
    op.create_index('idx_adapter_reset_status', 'adapter_reset_requests', ['status'])
    op.create_index('idx_adapter_reset_approval_id', 'adapter_reset_requests', ['approval_request_id'])
    op.create_index('idx_adapter_reset_created_at', 'adapter_reset_requests', ['created_at'])
    
    # Add subject column to event_logs table for better filtering during replay
    op.add_column('event_logs', sa.Column('subject', sa.String(50), nullable=True))
    op.create_index('idx_event_logs_subject', 'event_logs', ['subject'])
    
    # Add timestamp column to event_logs for proper ordering during replay
    op.add_column('event_logs', sa.Column('timestamp', sa.DateTime(timezone=True), nullable=True))
    op.create_index('idx_event_logs_timestamp', 'event_logs', ['timestamp'])
    
    # Set default values for existing event_logs records
    op.execute("""
        UPDATE event_logs 
        SET timestamp = created_at 
        WHERE timestamp IS NULL
    """)
    
    # Make timestamp column NOT NULL after setting defaults
    op.alter_column('event_logs', 'timestamp', nullable=False)


def downgrade() -> None:
    """Remove adapter reset request table and revert event log changes."""
    
    # Drop indexes for adapter_reset_requests
    op.drop_index('idx_adapter_reset_created_at', 'adapter_reset_requests')
    op.drop_index('idx_adapter_reset_approval_id', 'adapter_reset_requests')
    op.drop_index('idx_adapter_reset_status', 'adapter_reset_requests')
    op.drop_index('idx_adapter_reset_subject', 'adapter_reset_requests')
    op.drop_index('idx_adapter_reset_learner_id', 'adapter_reset_requests')
    
    # Drop adapter_reset_requests table
    op.drop_table('adapter_reset_requests')
    
    # Remove added columns from event_logs
    op.drop_index('idx_event_logs_timestamp', 'event_logs')
    op.drop_index('idx_event_logs_subject', 'event_logs')
    op.drop_column('event_logs', 'timestamp')
    op.drop_column('event_logs', 'subject')
