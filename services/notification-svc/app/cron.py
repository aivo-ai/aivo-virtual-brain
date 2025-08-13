# AIVO Notification Service - Cron Jobs for Daily Digest
# S1-12 Implementation - Background Tasks and Scheduled Jobs

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import redis.asyncio as redis

from .database import get_db_session
from .models import (
    DigestSubscription, Notification, NotificationType, 
    NotificationPriority, NotificationStatus, create_notification
)
from .push_service import PushNotificationService

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None

class DigestService:
    """Service for generating and sending daily digest notifications."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.push_service = PushNotificationService()
    
    async def generate_daily_digest(self, user_id: str, tenant_id: str, db: Session) -> Dict[str, Any]:
        """Generate daily digest content for a user."""
        try:
            # Get user's digest subscription
            subscription = db.query(DigestSubscription).filter(
                DigestSubscription.user_id == user_id,
                DigestSubscription.is_enabled == True
            ).first()
            
            if not subscription:
                return None
            
            # Calculate date range for digest
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(days=1)
            
            # Get notifications from the last day
            query = db.query(Notification).filter(
                Notification.user_id == user_id,
                Notification.tenant_id == tenant_id,
                Notification.created_at >= yesterday,
                Notification.created_at < now
            )
            
            # Apply user preferences
            if subscription.include_types:
                # Filter by included notification types
                type_filters = []
                for type_str in subscription.include_types:
                    try:
                        type_filters.append(NotificationType(type_str))
                    except ValueError:
                        continue
                if type_filters:
                    query = query.filter(Notification.notification_type.in_(type_filters))
            
            # Filter by minimum priority
            priority_order = {
                NotificationPriority.LOW: 0,
                NotificationPriority.NORMAL: 1,
                NotificationPriority.HIGH: 2,
                NotificationPriority.URGENT: 3
            }
            min_priority_value = priority_order.get(subscription.min_priority, 1)
            
            notifications = []
            for notification in query.all():
                notification_priority_value = priority_order.get(notification.priority, 1)
                if notification_priority_value >= min_priority_value:
                    notifications.append(notification)
            
            if not notifications:
                return None
            
            # Group notifications by type
            grouped_notifications = {}
            for notification in notifications:
                type_key = notification.notification_type.value
                if type_key not in grouped_notifications:
                    grouped_notifications[type_key] = []
                grouped_notifications[type_key].append(notification)
            
            # Generate summary statistics
            total_count = len(notifications)
            unread_count = len([n for n in notifications if n.read_at is None])
            priority_counts = {}
            for notification in notifications:
                priority = notification.priority.value
                priority_counts[priority] = priority_counts.get(priority, 0) + 1
            
            # Create digest content
            digest_content = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "date": yesterday.date().isoformat(),
                "summary": {
                    "total_notifications": total_count,
                    "unread_notifications": unread_count,
                    "priority_breakdown": priority_counts
                },
                "notifications_by_type": {},
                "top_notifications": []
            }
            
            # Add notifications by type
            for type_key, type_notifications in grouped_notifications.items():
                digest_content["notifications_by_type"][type_key] = {
                    "count": len(type_notifications),
                    "notifications": [
                        {
                            "id": str(n.id),
                            "title": n.title,
                            "message": n.message[:200] + "..." if len(n.message) > 200 else n.message,
                            "priority": n.priority.value,
                            "created_at": n.created_at.isoformat(),
                            "action_url": n.action_url
                        }
                        for n in sorted(type_notifications, key=lambda x: x.created_at, reverse=True)[:5]
                    ]
                }
            
            # Get top 5 highest priority notifications
            sorted_notifications = sorted(
                notifications,
                key=lambda x: (priority_order.get(x.priority, 1), x.created_at),
                reverse=True
            )[:5]
            
            digest_content["top_notifications"] = [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "message": n.message[:150] + "..." if len(n.message) > 150 else n.message,
                    "priority": n.priority.value,
                    "type": n.notification_type.value,
                    "created_at": n.created_at.isoformat(),
                    "action_url": n.action_url
                }
                for n in sorted_notifications
            ]
            
            return digest_content
            
        except Exception as e:
            logger.error(f"Error generating daily digest for user {user_id}: {e}")
            return None
    
    async def send_digest_notification(self, user_id: str, digest_content: Dict[str, Any], db: Session):
        """Send digest as a notification."""
        try:
            summary = digest_content["summary"]
            total_count = summary["total_notifications"]
            unread_count = summary["unread_notifications"]
            
            # Create digest title
            if total_count == 0:
                return  # No notifications to digest
            elif total_count == 1:
                title = "📋 Your Daily Summary: 1 notification"
            else:
                title = f"📋 Your Daily Summary: {total_count} notifications"
            
            if unread_count > 0:
                title += f" ({unread_count} unread)"
            
            # Create digest message
            message_parts = [
                f"Here's your daily summary for {digest_content['date']}:",
                f"\n📊 Total notifications: {total_count}",
                f"📬 Unread: {unread_count}"
            ]
            
            if digest_content["notifications_by_type"]:
                message_parts.append("\n📂 By category:")
                for type_key, type_data in digest_content["notifications_by_type"].items():
                    type_name = type_key.replace("_", " ").title()
                    message_parts.append(f"   • {type_name}: {type_data['count']}")
            
            if digest_content["top_notifications"]:
                message_parts.append("\n⭐ Top notifications:")
                for i, notification in enumerate(digest_content["top_notifications"][:3], 1):
                    priority_emoji = {
                        "urgent": "🚨",
                        "high": "⚡",
                        "normal": "📝",
                        "low": "💬"
                    }.get(notification["priority"], "📝")
                    
                    message_parts.append(f"   {i}. {priority_emoji} {notification['title']}")
            
            message = "\n".join(message_parts)
            
            # Create digest notification
            digest_notification = create_notification(
                db=db,
                user_id=user_id,
                tenant_id=digest_content["tenant_id"],
                title=title,
                message=message,
                notification_type=NotificationType.DAILY_DIGEST,
                channels=["in_app", "websocket", "push"],
                priority=NotificationPriority.NORMAL,
                metadata={
                    "digest_date": digest_content["date"],
                    "summary": summary,
                    "is_digest": True
                },
                context_data=digest_content
            )
            
            # Send via push notification
            await self.push_service.send_to_user(
                user_id, 
                digest_notification.to_dict(),
                db
            )
            
            logger.info(f"Daily digest sent to user {user_id}: {total_count} notifications")
            
        except Exception as e:
            logger.error(f"Error sending digest notification for user {user_id}: {e}")
    
    async def process_daily_digests(self):
        """Process all daily digest subscriptions."""
        logger.info("Starting daily digest processing")
        
        try:
            # Get database session
            db = get_db_session()
            
            # Get current time in UTC
            now = datetime.now(timezone.utc)
            
            # Find subscriptions that need digest delivery
            # Look for subscriptions scheduled for the current hour
            current_hour = now.hour
            
            subscriptions = db.query(DigestSubscription).filter(
                DigestSubscription.is_enabled == True,
                DigestSubscription.delivery_time.like(f"{current_hour:02d}:%")
            ).all()
            
            processed_count = 0
            success_count = 0
            
            for subscription in subscriptions:
                try:
                    # Check if digest already sent today
                    if subscription.last_sent_at:
                        last_sent_date = subscription.last_sent_at.date()
                        today = now.date()
                        
                        if last_sent_date >= today:
                            continue  # Already sent today
                    
                    # Check weekend exclusion
                    if subscription.exclude_weekends and now.weekday() >= 5:  # Saturday = 5, Sunday = 6
                        continue
                    
                    # Generate and send digest
                    digest_content = await self.generate_daily_digest(
                        subscription.user_id,
                        subscription.tenant_id,
                        db
                    )
                    
                    if digest_content:
                        await self.send_digest_notification(
                            subscription.user_id,
                            digest_content,
                            db
                        )
                        success_count += 1
                    
                    # Update last sent timestamp
                    subscription.last_sent_at = now
                    subscription.updated_at = now
                    
                    processed_count += 1
                    
                except Exception as e:
                    logger.error(f"Error processing digest for user {subscription.user_id}: {e}")
                    continue
            
            db.commit()
            db.close()
            
            logger.info(f"Daily digest processing complete: {processed_count} processed, {success_count} sent")
            
        except Exception as e:
            logger.error(f"Error in daily digest processing: {e}")

    async def cleanup_old_notifications(self):
        """Clean up old notifications to prevent database bloat."""
        try:
            db = get_db_session()
            
            # Delete notifications older than 90 days
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
            
            deleted_count = db.query(Notification).filter(
                Notification.created_at < cutoff_date,
                Notification.notification_type != NotificationType.DAILY_DIGEST  # Keep digest history longer
            ).delete()
            
            # Delete very old digest notifications (older than 1 year)
            old_digest_cutoff = datetime.now(timezone.utc) - timedelta(days=365)
            digest_deleted = db.query(Notification).filter(
                Notification.created_at < old_digest_cutoff,
                Notification.notification_type == NotificationType.DAILY_DIGEST
            ).delete()
            
            db.commit()
            db.close()
            
            logger.info(f"Cleaned up {deleted_count} old notifications and {digest_deleted} old digests")
            
        except Exception as e:
            logger.error(f"Error in cleanup job: {e}")

# Cron job management
async def start_cron_jobs(redis_client: redis.Redis):
    """Start scheduled cron jobs."""
    global scheduler
    
    try:
        scheduler = AsyncIOScheduler()
        digest_service = DigestService(redis_client)
        
        # Daily digest job - runs every hour to check for scheduled digests
        scheduler.add_job(
            digest_service.process_daily_digests,
            trigger=CronTrigger(minute=0),  # Run at the top of every hour
            id="daily_digest_processor",
            name="Daily Digest Processor",
            max_instances=1,
            coalesce=True
        )
        
        # Cleanup job - runs daily at 2:00 AM
        scheduler.add_job(
            digest_service.cleanup_old_notifications,
            trigger=CronTrigger(hour=2, minute=0),
            id="notification_cleanup",
            name="Notification Cleanup",
            max_instances=1,
            coalesce=True
        )
        
        # Start the scheduler
        scheduler.start()
        logger.info("Cron jobs started successfully")
        
    except Exception as e:
        logger.error(f"Error starting cron jobs: {e}")
        raise

async def stop_cron_jobs():
    """Stop scheduled cron jobs."""
    global scheduler
    
    if scheduler:
        try:
            scheduler.shutdown(wait=True)
            logger.info("Cron jobs stopped")
        except Exception as e:
            logger.error(f"Error stopping cron jobs: {e}")

# Manual digest trigger (for testing)
async def trigger_digest_for_user(user_id: str, tenant_id: str, redis_client: redis.Redis):
    """Manually trigger digest generation for a user (for testing purposes)."""
    try:
        digest_service = DigestService(redis_client)
        db = get_db_session()
        
        digest_content = await digest_service.generate_daily_digest(user_id, tenant_id, db)
        
        if digest_content:
            await digest_service.send_digest_notification(user_id, digest_content, db)
            db.close()
            return {"status": "success", "message": "Digest sent successfully"}
        else:
            db.close()
            return {"status": "info", "message": "No notifications to digest"}
    
    except Exception as e:
        logger.error(f"Error in manual digest trigger: {e}")
        return {"status": "error", "message": str(e)}
