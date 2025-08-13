# AIVO Notification Service - Database Migration
# S1-12 Implementation - Initial Database Schema

"""
Initial Notification Service Schema
Creates tables for notifications, push subscriptions, WebSocket connections, and digest preferences.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON
import uuid


# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Create initial notification service schema."""
    
    # Create enum types
    notification_type_enum = sa.Enum(
        'system', 'iep_update', 'assessment_complete', 'signature_request', 
        'signature_complete', 'daily_digest', 'user_mention', 'deadline_reminder',
        'collaboration_invite',
        name='notificationtype'
    )
    
    notification_priority_enum = sa.Enum(
        'low', 'normal', 'high', 'urgent',
        name='notificationpriority'
    )
    
    notification_status_enum = sa.Enum(
        'pending', 'sent', 'delivered', 'read', 'failed',
        name='notificationstatus'
    )
    
    delivery_channel_enum = sa.Enum(
        'websocket', 'email', 'sms', 'push', 'in_app',
        name='deliverychannel'
    )
    
    # Create enums
    notification_type_enum.create(op.get_bind())
    notification_priority_enum.create(op.get_bind())
    notification_status_enum.create(op.get_bind())
    delivery_channel_enum.create(op.get_bind())
    
    # Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        
        # Content
        sa.Column('title', sa.String(500), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('notification_type', notification_type_enum, nullable=False, index=True),
        sa.Column('priority', notification_priority_enum, nullable=False, default='normal'),
        
        # Delivery
        sa.Column('channels', JSON, nullable=False, default=list),
        sa.Column('delivery_config', JSON, nullable=False, default=dict),
        sa.Column('status', notification_status_enum, nullable=False, default='pending', index=True),
        sa.Column('attempts', sa.Integer, nullable=False, default=0),
        sa.Column('max_attempts', sa.Integer, nullable=False, default=3),
        
        # Metadata
        sa.Column('metadata', JSON, nullable=False, default=dict),
        sa.Column('context_data', JSON, nullable=False, default=dict),
        sa.Column('action_url', sa.String(1000), nullable=True),
        
        # Scheduling
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Create notification deliveries table
    op.create_table(
        'notification_deliveries',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('notification_id', UUID(as_uuid=True), sa.ForeignKey('notifications.id'), nullable=False),
        
        # Delivery details
        sa.Column('channel', delivery_channel_enum, nullable=False),
        sa.Column('status', notification_status_enum, nullable=False, default='pending'),
        sa.Column('attempt_count', sa.Integer, nullable=False, default=0),
        
        # Channel-specific data
        sa.Column('channel_config', JSON, nullable=False, default=dict),
        sa.Column('delivery_response', JSON, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        
        # Timing
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now())
    )
    
    # Create push subscriptions table
    op.create_table(
        'push_subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        
        # Push subscription details
        sa.Column('endpoint', sa.String(1000), nullable=False),
        sa.Column('p256dh_key', sa.String(255), nullable=False),
        sa.Column('auth_key', sa.String(255), nullable=False),
        
        # Metadata
        sa.Column('user_agent', sa.String(1000), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('device_info', JSON, nullable=False, default=dict),
        
        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        
        # Preferences
        sa.Column('notification_preferences', JSON, nullable=False, default=dict),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        
        # Unique constraint
        sa.UniqueConstraint('user_id', 'endpoint', name='uq_user_endpoint')
    )
    
    # Create websocket connections table
    op.create_table(
        'websocket_connections',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('connection_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.String(255), nullable=False, index=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        
        # Connection details
        sa.Column('server_instance', sa.String(255), nullable=False),
        sa.Column('session_data', JSON, nullable=False, default=dict),
        
        # Status
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_ping', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('connected_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('disconnected_at', sa.DateTime(timezone=True), nullable=True)
    )
    
    # Create digest subscriptions table
    op.create_table(
        'digest_subscriptions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
        sa.Column('user_id', sa.String(255), nullable=False, unique=True, index=True),
        sa.Column('tenant_id', sa.String(255), nullable=False, index=True),
        
        # Digest configuration
        sa.Column('is_enabled', sa.Boolean, nullable=False, default=True),
        sa.Column('delivery_time', sa.String(5), nullable=False, default='07:00'),
        sa.Column('timezone', sa.String(50), nullable=False, default='America/New_York'),
        sa.Column('frequency', sa.String(20), nullable=False, default='daily'),
        
        # Content preferences
        sa.Column('include_types', JSON, nullable=False, default=list),
        sa.Column('exclude_weekends', sa.Boolean, nullable=False, default=False),
        sa.Column('min_priority', notification_priority_enum, nullable=False, default='normal'),
        
        # Delivery tracking
        sa.Column('last_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_scheduled_at', sa.DateTime(timezone=True), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.func.now())
    )
    
    # Create indexes for performance
    
    # Notifications indexes
    op.create_index('idx_notifications_user_status', 'notifications', ['user_id', 'status'])
    op.create_index('idx_notifications_tenant_type', 'notifications', ['tenant_id', 'notification_type'])
    op.create_index('idx_notifications_scheduled', 'notifications', ['scheduled_at'])
    op.create_index('idx_notifications_created_at', 'notifications', ['created_at'])
    
    # Notification deliveries indexes
    op.create_index('idx_deliveries_notification_channel', 'notification_deliveries', ['notification_id', 'channel'])
    op.create_index('idx_deliveries_status_scheduled', 'notification_deliveries', ['status', 'scheduled_at'])
    
    # Push subscriptions indexes
    op.create_index('idx_push_subscriptions_active', 'push_subscriptions', ['is_active', 'user_id'])
    
    # WebSocket connections indexes
    op.create_index('idx_ws_connections_user_active', 'websocket_connections', ['user_id', 'is_active'])
    op.create_index('idx_ws_connections_server', 'websocket_connections', ['server_instance', 'is_active'])
    
    # Digest subscriptions indexes
    op.create_index('idx_digest_enabled_scheduled', 'digest_subscriptions', ['is_enabled', 'next_scheduled_at'])


def downgrade():
    """Drop all notification service tables."""
    
    # Drop indexes first
    op.drop_index('idx_digest_enabled_scheduled', 'digest_subscriptions')
    op.drop_index('idx_ws_connections_server', 'websocket_connections')
    op.drop_index('idx_ws_connections_user_active', 'websocket_connections')
    op.drop_index('idx_push_subscriptions_active', 'push_subscriptions')
    op.drop_index('idx_deliveries_status_scheduled', 'notification_deliveries')
    op.drop_index('idx_deliveries_notification_channel', 'notification_deliveries')
    op.drop_index('idx_notifications_created_at', 'notifications')
    op.drop_index('idx_notifications_scheduled', 'notifications')
    op.drop_index('idx_notifications_tenant_type', 'notifications')
    op.drop_index('idx_notifications_user_status', 'notifications')
    
    # Drop tables
    op.drop_table('digest_subscriptions')
    op.drop_table('websocket_connections')
    op.drop_table('push_subscriptions')
    op.drop_table('notification_deliveries')
    op.drop_table('notifications')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS deliverychannel')
    op.execute('DROP TYPE IF EXISTS notificationstatus')
    op.execute('DROP TYPE IF EXISTS notificationpriority')
    op.execute('DROP TYPE IF EXISTS notificationtype')
