# AIVO Notification Service - API Routes
# S1-12 Implementation - Push Subscribe + Notification Management

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
import uuid
import logging

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import jwt

from .database import get_db
from .models import (
    Notification, PushSubscription, DigestSubscription,
    NotificationType, NotificationPriority, NotificationStatus,
    create_notification, get_user_notifications, mark_notification_read
)
from .push_service import PushNotificationService
from .ws import get_ws_manager

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)

# Pydantic models for API
class PushSubscriptionCreate(BaseModel):
    endpoint: str = Field(..., max_length=1000)
    p256dh_key: str = Field(..., max_length=255)
    auth_key: str = Field(..., max_length=255)
    user_agent: Optional[str] = Field(None, max_length=1000)
    device_info: Dict[str, Any] = Field(default_factory=dict)
    notification_preferences: Dict[str, Any] = Field(default_factory=dict)

class PushSubscriptionResponse(BaseModel):
    id: str
    endpoint: str
    is_active: bool
    created_at: datetime
    last_used_at: Optional[datetime]

class NotificationCreate(BaseModel):
    title: str = Field(..., max_length=500)
    message: str = Field(..., min_length=1)
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.NORMAL
    channels: List[str] = Field(default=["in_app", "websocket"])
    metadata: Dict[str, Any] = Field(default_factory=dict)
    context_data: Dict[str, Any] = Field(default_factory=dict)
    action_url: Optional[str] = Field(None, max_length=1000)
    scheduled_at: Optional[datetime] = None

class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    notification_type: str
    priority: str
    status: str
    created_at: datetime
    read_at: Optional[datetime]
    action_url: Optional[str]
    metadata: Dict[str, Any]

class DigestSubscriptionUpdate(BaseModel):
    is_enabled: bool = True
    delivery_time: str = Field("07:00", regex=r"^([0-1][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field("America/New_York", max_length=50)
    frequency: str = Field("daily", regex=r"^(daily|weekly)$")
    include_types: List[str] = Field(default_factory=list)
    exclude_weekends: bool = False
    min_priority: NotificationPriority = NotificationPriority.NORMAL

class NotificationListResponse(BaseModel):
    notifications: List[NotificationResponse]
    total_count: int
    unread_count: int
    has_more: bool

# Authentication dependency
async def get_current_user(token: str = Depends(security)):
    """Extract user information from JWT token."""
    try:
        payload = jwt.decode(token.credentials, "your-secret-key", algorithms=["HS256"])
        return {
            "user_id": payload.get("user_id"),
            "tenant_id": payload.get("tenant_id"),
            "roles": payload.get("roles", [])
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Push Subscription Endpoints
@router.post("/push/subscribe", response_model=PushSubscriptionResponse)
async def create_push_subscription(
    subscription_data: PushSubscriptionCreate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create or update a push notification subscription.
    
    This endpoint registers a web push subscription for browser notifications.
    The subscription includes the endpoint URL and keys needed for push notifications.
    """
    try:
        # Check if subscription already exists
        existing = db.query(PushSubscription).filter(
            PushSubscription.user_id == user["user_id"],
            PushSubscription.endpoint == subscription_data.endpoint
        ).first()
        
        if existing:
            # Update existing subscription
            existing.p256dh_key = subscription_data.p256dh_key
            existing.auth_key = subscription_data.auth_key
            existing.user_agent = subscription_data.user_agent
            existing.device_info = subscription_data.device_info
            existing.notification_preferences = subscription_data.notification_preferences
            existing.is_active = True
            existing.updated_at = datetime.now(timezone.utc)
            
            db.commit()
            subscription = existing
        else:
            # Create new subscription
            subscription = PushSubscription(
                user_id=user["user_id"],
                tenant_id=user["tenant_id"],
                endpoint=subscription_data.endpoint,
                p256dh_key=subscription_data.p256dh_key,
                auth_key=subscription_data.auth_key,
                user_agent=subscription_data.user_agent,
                device_info=subscription_data.device_info,
                notification_preferences=subscription_data.notification_preferences
            )
            
            db.add(subscription)
            db.commit()
            db.refresh(subscription)
        
        return PushSubscriptionResponse(
            id=str(subscription.id),
            endpoint=subscription.endpoint,
            is_active=subscription.is_active,
            created_at=subscription.created_at,
            last_used_at=subscription.last_used_at
        )
        
    except Exception as e:
        logger.error(f"Error creating push subscription: {e}")
        raise HTTPException(status_code=500, detail="Failed to create subscription")

@router.get("/push/subscriptions", response_model=List[PushSubscriptionResponse])
async def get_push_subscriptions(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all push subscriptions for the current user."""
    subscriptions = db.query(PushSubscription).filter(
        PushSubscription.user_id == user["user_id"],
        PushSubscription.is_active == True
    ).all()
    
    return [
        PushSubscriptionResponse(
            id=str(sub.id),
            endpoint=sub.endpoint,
            is_active=sub.is_active,
            created_at=sub.created_at,
            last_used_at=sub.last_used_at
        )
        for sub in subscriptions
    ]

@router.delete("/push/subscriptions/{subscription_id}")
async def delete_push_subscription(
    subscription_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a push subscription."""
    result = db.query(PushSubscription).filter(
        PushSubscription.id == subscription_id,
        PushSubscription.user_id == user["user_id"]
    ).update({"is_active": False})
    
    db.commit()
    
    if result == 0:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    return {"status": "success", "message": "Subscription deleted"}

# Notification Management Endpoints
@router.post("/notifications", response_model=NotificationResponse)
async def create_user_notification(
    notification_data: NotificationCreate,
    background_tasks: BackgroundTasks,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new notification for a user.
    
    This can be used to create notifications programmatically.
    The notification will be delivered via the specified channels.
    """
    try:
        # Create notification in database
        notification = create_notification(
            db=db,
            user_id=user["user_id"],
            tenant_id=user["tenant_id"],
            title=notification_data.title,
            message=notification_data.message,
            notification_type=notification_data.notification_type,
            channels=notification_data.channels,
            priority=notification_data.priority,
            metadata=notification_data.metadata,
            context_data=notification_data.context_data,
            action_url=notification_data.action_url,
            scheduled_at=notification_data.scheduled_at
        )
        
        # Send via WebSocket if connected
        if "websocket" in notification_data.channels:
            ws_manager = get_ws_manager()
            background_tasks.add_task(
                ws_manager.notify_user,
                user["user_id"],
                notification.to_dict(),
                db
            )
        
        # Send push notification if enabled
        if "push" in notification_data.channels:
            push_service = PushNotificationService()
            background_tasks.add_task(
                push_service.send_to_user,
                user["user_id"],
                notification.to_dict(),
                db
            )
        
        return NotificationResponse(
            id=str(notification.id),
            title=notification.title,
            message=notification.message,
            notification_type=notification.notification_type.value,
            priority=notification.priority.value,
            status=notification.status.value,
            created_at=notification.created_at,
            read_at=notification.read_at,
            action_url=notification.action_url,
            metadata=notification.metadata
        )
        
    except Exception as e:
        logger.error(f"Error creating notification: {e}")
        raise HTTPException(status_code=500, detail="Failed to create notification")

@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    unread_only: bool = Query(False),
    notification_type: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get notifications for the current user.
    
    Supports pagination and filtering by read status and notification type.
    """
    query = db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.tenant_id == user["tenant_id"]
    )
    
    if unread_only:
        query = query.filter(Notification.read_at.is_(None))
    
    if notification_type:
        try:
            nt = NotificationType(notification_type)
            query = query.filter(Notification.notification_type == nt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid notification type")
    
    # Get total count
    total_count = query.count()
    
    # Get notifications with pagination
    notifications = query.order_by(
        Notification.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    # Get unread count
    unread_count = db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.tenant_id == user["tenant_id"],
        Notification.read_at.is_(None)
    ).count()
    
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=str(n.id),
                title=n.title,
                message=n.message,
                notification_type=n.notification_type.value,
                priority=n.priority.value,
                status=n.status.value,
                created_at=n.created_at,
                read_at=n.read_at,
                action_url=n.action_url,
                metadata=n.metadata
            )
            for n in notifications
        ],
        total_count=total_count,
        unread_count=unread_count,
        has_more=offset + limit < total_count
    )

@router.post("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a notification as read."""
    success = mark_notification_read(db, notification_id, user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"status": "success", "message": "Notification marked as read"}

@router.post("/notifications/read-all")
async def mark_all_notifications_read(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the current user."""
    updated_count = db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.tenant_id == user["tenant_id"],
        Notification.read_at.is_(None)
    ).update({
        "read_at": datetime.now(timezone.utc),
        "status": NotificationStatus.READ,
        "updated_at": datetime.now(timezone.utc)
    })
    
    db.commit()
    
    return {"status": "success", "message": f"Marked {updated_count} notifications as read"}

# Daily Digest Subscription Endpoints
@router.get("/digest/subscription")
async def get_digest_subscription(
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's digest subscription settings."""
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user["user_id"]
    ).first()
    
    if not subscription:
        # Create default subscription
        subscription = DigestSubscription(
            user_id=user["user_id"],
            tenant_id=user["tenant_id"]
        )
        db.add(subscription)
        db.commit()
        db.refresh(subscription)
    
    return {
        "id": str(subscription.id),
        "is_enabled": subscription.is_enabled,
        "delivery_time": subscription.delivery_time,
        "timezone": subscription.timezone,
        "frequency": subscription.frequency,
        "include_types": subscription.include_types,
        "exclude_weekends": subscription.exclude_weekends,
        "min_priority": subscription.min_priority.value,
        "last_sent_at": subscription.last_sent_at,
        "next_scheduled_at": subscription.next_scheduled_at
    }

@router.put("/digest/subscription")
async def update_digest_subscription(
    subscription_data: DigestSubscriptionUpdate,
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update digest subscription settings."""
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user["user_id"]
    ).first()
    
    if not subscription:
        subscription = DigestSubscription(
            user_id=user["user_id"],
            tenant_id=user["tenant_id"]
        )
        db.add(subscription)
    
    # Update subscription
    subscription.is_enabled = subscription_data.is_enabled
    subscription.delivery_time = subscription_data.delivery_time
    subscription.timezone = subscription_data.timezone
    subscription.frequency = subscription_data.frequency
    subscription.include_types = subscription_data.include_types
    subscription.exclude_weekends = subscription_data.exclude_weekends
    subscription.min_priority = subscription_data.min_priority
    subscription.updated_at = datetime.now(timezone.utc)
    
    # Calculate next scheduled delivery
    # This would be handled by the cron job scheduler
    
    db.commit()
    
    return {"status": "success", "message": "Digest subscription updated"}

# Notification Statistics
@router.get("/notifications/stats")
async def get_notification_stats(
    days: int = Query(7, ge=1, le=30),
    user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get notification statistics for the current user."""
    since_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    # Total notifications
    total = db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.created_at >= since_date
    ).count()
    
    # Unread notifications
    unread = db.query(Notification).filter(
        Notification.user_id == user["user_id"],
        Notification.read_at.is_(None)
    ).count()
    
    # Notifications by type
    type_stats = db.query(
        Notification.notification_type,
        db.func.count(Notification.id)
    ).filter(
        Notification.user_id == user["user_id"],
        Notification.created_at >= since_date
    ).group_by(Notification.notification_type).all()
    
    return {
        "period_days": days,
        "total_notifications": total,
        "unread_notifications": unread,
        "read_rate": (total - unread) / total if total > 0 else 0,
        "notifications_by_type": {
            str(nt.value): count for nt, count in type_stats
        }
    }
