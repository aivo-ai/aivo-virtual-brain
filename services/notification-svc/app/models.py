# AIVO Notification Service - Database Models
# S1-12 Implementation - WebSocket Hub + Push Subscribe + Daily Digest

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
import uuid
import enum

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, Text, 
    JSON, ForeignKey, Index, UniqueConstraint, Enum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func
import redis
import json

Base = declarative_base()

class NotificationType(enum.Enum):
    """Types of notifications supported by the system."""
    SYSTEM = "system"
    IEP_UPDATE = "iep_update"
    ASSESSMENT_COMPLETE = "assessment_complete"
    SIGNATURE_REQUEST = "signature_request"
    SIGNATURE_COMPLETE = "signature_complete"
    DAILY_DIGEST = "daily_digest"
    USER_MENTION = "user_mention"
    DEADLINE_REMINDER = "deadline_reminder"
    COLLABORATION_INVITE = "collaboration_invite"

class NotificationPriority(enum.Enum):
    """Priority levels for notifications."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"

class NotificationStatus(enum.Enum):
    """Status of notification delivery."""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"

class DeliveryChannel(enum.Enum):
    """Channels for notification delivery."""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    IN_APP = "in_app"

class Notification(Base):
    """Core notification model with delivery tracking."""
    
    __tablename__ = "notifications"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Notification content
    title = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(Enum(NotificationType), nullable=False, index=True)
    priority = Column(Enum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL)
    
    # Delivery configuration
    channels = Column(JSON, nullable=False, default=list)  # List of delivery channels
    delivery_config = Column(JSON, nullable=False, default=dict)  # Channel-specific config
    
    # Status tracking
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    
    # Metadata and context
    metadata = Column(JSON, nullable=False, default=dict)
    context_data = Column(JSON, nullable=False, default=dict)  # Related entity data
    action_url = Column(String(1000), nullable=True)  # Deep link URL
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    deliveries = relationship("NotificationDelivery", back_populates="notification", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_notifications_user_status", "user_id", "status"),
        Index("idx_notifications_tenant_type", "tenant_id", "notification_type"),
        Index("idx_notifications_scheduled", "scheduled_at"),
        Index("idx_notifications_created_at", "created_at"),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary for JSON serialization."""
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type.value,
            "priority": self.priority.value,
            "channels": self.channels,
            "status": self.status.value,
            "metadata": self.metadata,
            "context_data": self.context_data,
            "action_url": self.action_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None
        }

class NotificationDelivery(Base):
    """Tracks delivery attempts per channel."""
    
    __tablename__ = "notification_deliveries"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notifications.id"), nullable=False)
    
    # Delivery details
    channel = Column(Enum(DeliveryChannel), nullable=False)
    status = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.PENDING)
    attempt_count = Column(Integer, nullable=False, default=0)
    
    # Channel-specific data
    channel_config = Column(JSON, nullable=False, default=dict)
    delivery_response = Column(JSON, nullable=True)  # Response from delivery service
    error_message = Column(Text, nullable=True)
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True), nullable=True)
    attempted_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    notification = relationship("Notification", back_populates="deliveries")
    
    # Indexes
    __table_args__ = (
        Index("idx_deliveries_notification_channel", "notification_id", "channel"),
        Index("idx_deliveries_status_scheduled", "status", "scheduled_at"),
    )

class PushSubscription(Base):
    """Web Push subscription endpoints for browser notifications."""
    
    __tablename__ = "push_subscriptions"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Push subscription details
    endpoint = Column(String(1000), nullable=False)
    p256dh_key = Column(String(255), nullable=False)  # Public key
    auth_key = Column(String(255), nullable=False)    # Auth secret
    
    # Metadata
    user_agent = Column(String(1000), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 support
    device_info = Column(JSON, nullable=False, default=dict)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    
    # Preferences
    notification_preferences = Column(JSON, nullable=False, default=dict)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Unique constraint on endpoint per user
    __table_args__ = (
        UniqueConstraint("user_id", "endpoint", name="uq_user_endpoint"),
        Index("idx_push_subscriptions_active", "is_active", "user_id"),
    )

class WebSocketConnection(Base):
    """Track active WebSocket connections for real-time notifications."""
    
    __tablename__ = "websocket_connections"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(String(255), nullable=False, unique=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Connection details
    server_instance = Column(String(255), nullable=False)  # For load balancing
    session_data = Column(JSON, nullable=False, default=dict)
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    last_ping = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    connected_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    disconnected_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("idx_ws_connections_user_active", "user_id", "is_active"),
        Index("idx_ws_connections_server", "server_instance", "is_active"),
    )

class DigestSubscription(Base):
    """User preferences for daily digest notifications."""
    
    __tablename__ = "digest_subscriptions"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, unique=True, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Digest configuration
    is_enabled = Column(Boolean, nullable=False, default=True)
    delivery_time = Column(String(5), nullable=False, default="07:00")  # HH:MM format
    timezone = Column(String(50), nullable=False, default="America/New_York")
    frequency = Column(String(20), nullable=False, default="daily")  # daily, weekly
    
    # Content preferences
    include_types = Column(JSON, nullable=False, default=list)  # Notification types to include
    exclude_weekends = Column(Boolean, nullable=False, default=False)
    min_priority = Column(Enum(NotificationPriority), nullable=False, default=NotificationPriority.NORMAL)
    
    # Delivery tracking
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    next_scheduled_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Indexes
    __table_args__ = (
        Index("idx_digest_enabled_scheduled", "is_enabled", "next_scheduled_at"),
    )

# Redis-based notification queue and pub/sub system
class NotificationQueue:
    """Redis-based notification queue for async processing."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.queue_key = "notification:queue"
        self.processing_key = "notification:processing"
        self.pubsub_channel = "notification:events"
    
    def enqueue(self, notification_data: Dict[str, Any]) -> bool:
        """Add notification to processing queue."""
        try:
            self.redis.lpush(self.queue_key, json.dumps(notification_data))
            return True
        except Exception as e:
            print(f"Failed to enqueue notification: {e}")
            return False
    
    def dequeue(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Get next notification from queue."""
        try:
            result = self.redis.brpoplpush(self.queue_key, self.processing_key, timeout=timeout)
            if result:
                return json.loads(result.decode('utf-8'))
            return None
        except Exception as e:
            print(f"Failed to dequeue notification: {e}")
            return None
    
    def complete(self, notification_data: Dict[str, Any]) -> bool:
        """Mark notification as processed."""
        try:
            self.redis.lrem(self.processing_key, 1, json.dumps(notification_data))
            return True
        except Exception as e:
            print(f"Failed to complete notification: {e}")
            return False
    
    def publish_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Publish real-time event to WebSocket subscribers."""
        try:
            event_data = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": data
            }
            self.redis.publish(self.pubsub_channel, json.dumps(event_data))
            return True
        except Exception as e:
            print(f"Failed to publish event: {e}")
            return False
    
    def subscribe_events(self):
        """Subscribe to real-time events."""
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.pubsub_channel)
        return pubsub

# Database utilities
def create_notification(
    db: Session,
    user_id: str,
    tenant_id: str,
    title: str,
    message: str,
    notification_type: NotificationType,
    channels: List[str] = None,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    metadata: Dict[str, Any] = None,
    context_data: Dict[str, Any] = None,
    action_url: str = None,
    scheduled_at: datetime = None
) -> Notification:
    """Create a new notification."""
    notification = Notification(
        user_id=user_id,
        tenant_id=tenant_id,
        title=title,
        message=message,
        notification_type=notification_type,
        channels=channels or ["in_app", "websocket"],
        priority=priority,
        metadata=metadata or {},
        context_data=context_data or {},
        action_url=action_url,
        scheduled_at=scheduled_at
    )
    
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification

def get_user_notifications(
    db: Session,
    user_id: str,
    tenant_id: str,
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False
) -> List[Notification]:
    """Get notifications for a user."""
    query = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.tenant_id == tenant_id
    )
    
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    
    return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()

def mark_notification_read(db: Session, notification_id: str, user_id: str) -> bool:
    """Mark notification as read."""
    result = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).update({
        "read_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    })
    
    db.commit()
    return result > 0
