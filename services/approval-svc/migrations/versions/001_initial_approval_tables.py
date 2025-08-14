"""Initial approval service tables

Revision ID: 001_initial_approval_tables
Revises: 
Create Date: 2024-12-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid

# revision identifiers, used by Alembic.
revision = '001_initial_approval_tables'
down_revision = None
branch_labels = None
depends_on = None

# Enum definitions
approval_status_enum = sa.Enum(
    'PENDING', 'APPROVED', 'REJECTED', 'EXPIRED',
    name='approval_status_enum',
    create_type=False
)

approver_role_enum = sa.Enum(
    'GUARDIAN', 'TEACHER', 'CASE_MANAGER', 'DISTRICT_ADMIN', 'ADMINISTRATOR', 'SERVICE_PROVIDER',
    name='approver_role_enum', 
    create_type=False
)

approval_type_enum = sa.Enum(
    'LEVEL_CHANGE', 'IEP_CHANGE', 'CONSENT_SENSITIVE', 'PLACEMENT_CHANGE', 'SERVICE_CHANGE',
    name='approval_type_enum',
    create_type=False
)


def upgrade() -> None:
    """Create approval service tables."""
    
    # Create enum types
    approval_status_enum.create(op.get_bind(), checkfirst=True)
    approver_role_enum.create(op.get_bind(), checkfirst=True) 
    approval_type_enum.create(op.get_bind(), checkfirst=True)
    
    # Create approval_requests table
    op.create_table(
        'approval_requests',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False, index=True),
        
        # Request metadata
        sa.Column('approval_type', approval_type_enum, nullable=False),
        sa.Column('resource_id', sa.String(255), nullable=False, index=True),
        sa.Column('resource_type', sa.String(100), nullable=False),
        
        # Approval details
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('context_data', JSON, nullable=True),
        
        # State machine
        sa.Column('status', approval_status_enum, nullable=False, default='PENDING'),
        
        # Timing and TTL
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        
        # Requester information
        sa.Column('requested_by', sa.String(255), nullable=False),
        sa.Column('requested_by_role', sa.String(100), nullable=True),
        
        # Final decision metadata
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision_reason', sa.Text, nullable=True),
        
        # Webhook configuration
        sa.Column('webhook_url', sa.String(1000), nullable=True),
        sa.Column('webhook_headers', JSON, nullable=True),
        sa.Column('webhook_sent', sa.Boolean, default=False),
        sa.Column('webhook_sent_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    # Create approval_decisions table
    op.create_table(
        'approval_decisions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('request_id', UUID(as_uuid=True), sa.ForeignKey('approval_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Approver information
        sa.Column('approver_id', sa.String(255), nullable=False),
        sa.Column('approver_role', approver_role_enum, nullable=False),
        sa.Column('approver_name', sa.String(255), nullable=True),
        
        # Decision
        sa.Column('approved', sa.Boolean, nullable=False),
        sa.Column('comments', sa.Text, nullable=True),
        
        # Timing
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        
        # Metadata
        sa.Column('decision_metadata', JSON, nullable=True),
    )
    
    # Create approval_reminders table
    op.create_table(
        'approval_reminders',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('request_id', UUID(as_uuid=True), sa.ForeignKey('approval_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Reminder details
        sa.Column('recipient_role', approver_role_enum, nullable=False),
        sa.Column('recipient_id', sa.String(255), nullable=False),
        
        # Timing
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        
        # Content
        sa.Column('reminder_type', sa.String(50), nullable=False, default='standard'),
        sa.Column('message', sa.Text, nullable=True),
        
        # Status
        sa.Column('sent', sa.Boolean, default=False),
        sa.Column('notification_id', sa.String(255), nullable=True),
    )
    
    # Create approval_audit_logs table
    op.create_table(
        'approval_audit_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('request_id', UUID(as_uuid=True), sa.ForeignKey('approval_requests.id', ondelete='CASCADE'), nullable=False, index=True),
        
        # Event details
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('actor_id', sa.String(255), nullable=False),
        sa.Column('actor_role', sa.String(100), nullable=True),
        
        # Event data
        sa.Column('event_data', JSON, nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        
        # Timing
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
    )
    
    # Create indexes for better query performance
    op.create_index('idx_approval_requests_tenant_type', 'approval_requests', ['tenant_id', 'approval_type'])
    op.create_index('idx_approval_requests_status_expires', 'approval_requests', ['status', 'expires_at'])
    op.create_index('idx_approval_requests_requested_by', 'approval_requests', ['requested_by'])
    op.create_index('idx_approval_requests_created_at', 'approval_requests', ['created_at'])
    
    op.create_index('idx_approval_decisions_request_role', 'approval_decisions', ['request_id', 'approver_role'])
    op.create_index('idx_approval_decisions_approver', 'approval_decisions', ['approver_id'])
    
    op.create_index('idx_approval_reminders_scheduled', 'approval_reminders', ['scheduled_for', 'sent'])
    op.create_index('idx_approval_reminders_recipient', 'approval_reminders', ['recipient_id', 'recipient_role'])
    
    op.create_index('idx_audit_logs_timestamp', 'approval_audit_logs', ['timestamp'])
    op.create_index('idx_audit_logs_event_type', 'approval_audit_logs', ['event_type'])


def downgrade() -> None:
    """Drop approval service tables."""
    
    # Drop indexes
    op.drop_index('idx_audit_logs_event_type')
    op.drop_index('idx_audit_logs_timestamp')
    op.drop_index('idx_approval_reminders_recipient')
    op.drop_index('idx_approval_reminders_scheduled')
    op.drop_index('idx_approval_decisions_approver')
    op.drop_index('idx_approval_decisions_request_role')
    op.drop_index('idx_approval_requests_created_at')
    op.drop_index('idx_approval_requests_requested_by')
    op.drop_index('idx_approval_requests_status_expires')
    op.drop_index('idx_approval_requests_tenant_type')
    
    # Drop tables
    op.drop_table('approval_audit_logs')
    op.drop_table('approval_reminders')
    op.drop_table('approval_decisions')
    op.drop_table('approval_requests')
    
    # Drop enum types
    approval_type_enum.drop(op.get_bind(), checkfirst=True)
    approver_role_enum.drop(op.get_bind(), checkfirst=True)
    approval_status_enum.drop(op.get_bind(), checkfirst=True)
