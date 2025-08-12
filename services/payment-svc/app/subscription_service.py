"""
Subscription and Dunning Management Service
Handles subscription lifecycle, payment failures, and dunning process
"""

import structlog
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from enum import Enum

from app.config import settings
from app.schemas import (
    SubscriptionStatus, DunningStatus, PaymentStatus,
    SubscriptionRecord, PaymentRecord, DunningRecord
)

logger = structlog.get_logger(__name__)


class DunningService:
    """Service for managing payment failures and dunning process"""
    
    def __init__(self):
        self.grace_period_days = settings.grace_period_days
        self.dunning_days = settings.dunning_failure_days  # [3, 7, 14]
        self.cancellation_day = settings.cancellation_day  # 21
        logger.info("Dunning service initialized", 
                   grace_period=self.grace_period_days,
                   dunning_schedule=self.dunning_days,
                   cancellation_day=self.cancellation_day)
    
    async def handle_payment_failure(self, subscription_id: str, invoice_id: str, 
                                   failure_reason: Optional[str] = None) -> bool:
        """Handle payment failure and initiate dunning process"""
        try:
            logger.warning(
                "Processing payment failure",
                subscription_id=subscription_id,
                invoice_id=invoice_id,
                reason=failure_reason
            )
            
            # Record payment failure
            payment_record = PaymentRecord(
                id=f"pay_{subscription_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                stripe_invoice_id=invoice_id,
                subscription_id=subscription_id,
                amount_cents=0,  # Would get from Stripe invoice
                status=PaymentStatus.FAILED,
                failure_reason=failure_reason,
                attempt_count=1  # Would track from database
            )
            
            # Update subscription to past_due
            await self._update_subscription_status(
                subscription_id, 
                SubscriptionStatus.PAST_DUE
            )
            
            # Start grace period
            grace_end = datetime.utcnow() + timedelta(days=self.grace_period_days)
            
            logger.info(
                "Grace period started",
                subscription_id=subscription_id,
                grace_end=grace_end
            )
            
            # Schedule dunning emails
            await self._schedule_dunning_emails(subscription_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to handle payment failure", 
                        subscription_id=subscription_id, error=str(e))
            return False
    
    async def process_dunning_schedule(self, subscription_id: str, days_past_due: int) -> bool:
        """Process dunning schedule based on days past due"""
        try:
            dunning_status = self._get_dunning_status(days_past_due)
            
            if dunning_status == DunningStatus.NONE:
                return True
                
            logger.info(
                "Processing dunning",
                subscription_id=subscription_id,
                days_past_due=days_past_due,
                dunning_status=dunning_status
            )
            
            if days_past_due >= self.cancellation_day:
                # Cancel subscription
                await self._cancel_subscription(subscription_id, "payment_failure")
                return True
            
            # Send appropriate dunning email
            email_sent = await self._send_dunning_email(
                subscription_id, 
                dunning_status, 
                days_past_due
            )
            
            if email_sent:
                # Record dunning email
                dunning_record = DunningRecord(
                    id=f"dun_{subscription_id}_{days_past_due}",
                    subscription_id=subscription_id,
                    dunning_status=dunning_status,
                    days_past_due=days_past_due
                )
                
                # Update subscription dunning status
                await self._update_subscription_dunning_status(
                    subscription_id, 
                    dunning_status
                )
                
            return email_sent
            
        except Exception as e:
            logger.error("Failed to process dunning", 
                        subscription_id=subscription_id, error=str(e))
            return False
    
    def _get_dunning_status(self, days_past_due: int) -> DunningStatus:
        """Determine dunning status based on days past due"""
        if days_past_due >= self.cancellation_day:
            return DunningStatus.GRACE_EXPIRED
        elif days_past_due >= 14:
            return DunningStatus.FINAL_NOTICE
        elif days_past_due >= 7:
            return DunningStatus.WARNING_2
        elif days_past_due >= 3:
            return DunningStatus.WARNING_1
        else:
            return DunningStatus.NONE
    
    async def _send_dunning_email(self, subscription_id: str, 
                                dunning_status: DunningStatus, 
                                days_past_due: int) -> bool:
        """Send appropriate dunning email"""
        email_templates = {
            DunningStatus.WARNING_1: "payment_reminder_day_3",
            DunningStatus.WARNING_2: "payment_reminder_day_7", 
            DunningStatus.FINAL_NOTICE: "payment_final_notice_day_14"
        }
        
        template = email_templates.get(dunning_status)
        if not template:
            return True
            
        logger.info(
            "Sending dunning email",
            subscription_id=subscription_id,
            template=template,
            days_past_due=days_past_due
        )
        
        # Here you would integrate with your email service
        # For now, just log the action
        logger.info("Dunning email sent", 
                   subscription_id=subscription_id,
                   template=template)
        
        return True
    
    async def _schedule_dunning_emails(self, subscription_id: str) -> bool:
        """Schedule dunning emails based on configuration"""
        logger.info(
            "Scheduling dunning emails",
            subscription_id=subscription_id,
            schedule=self.dunning_days
        )
        
        # This would integrate with a task queue like Celery
        # For each day in dunning_days, schedule a task
        for day in self.dunning_days:
            schedule_time = datetime.utcnow() + timedelta(days=day)
            logger.info(
                "Dunning email scheduled",
                subscription_id=subscription_id,
                day=day,
                scheduled_for=schedule_time
            )
        
        return True
    
    async def _update_subscription_status(self, subscription_id: str, 
                                        status: SubscriptionStatus) -> bool:
        """Update subscription status in database"""
        logger.info(
            "Updating subscription status",
            subscription_id=subscription_id,
            new_status=status
        )
        
        # Database update would go here
        return True
    
    async def _update_subscription_dunning_status(self, subscription_id: str, 
                                                dunning_status: DunningStatus) -> bool:
        """Update subscription dunning status"""
        logger.info(
            "Updating dunning status",
            subscription_id=subscription_id,
            dunning_status=dunning_status
        )
        
        # Database update would go here
        return True
    
    async def _cancel_subscription(self, subscription_id: str, reason: str) -> bool:
        """Cancel subscription due to payment failure"""
        logger.warning(
            "Canceling subscription",
            subscription_id=subscription_id,
            reason=reason
        )
        
        # This would cancel the Stripe subscription
        # and update local database
        await self._update_subscription_status(
            subscription_id, 
            SubscriptionStatus.CANCELED
        )
        
        return True


class SubscriptionService:
    """Service for managing subscription lifecycle"""
    
    def __init__(self):
        self.dunning_service = DunningService()
        logger.info("Subscription service initialized")
    
    async def create_subscription_record(self, stripe_subscription_id: str, 
                                       guardian_id: str, learner_id: str,
                                       stripe_customer_id: str) -> SubscriptionRecord:
        """Create local subscription record"""
        record = SubscriptionRecord(
            id=f"sub_{stripe_subscription_id}",
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=stripe_customer_id,
            guardian_id=guardian_id,
            learner_id=learner_id,
            status=SubscriptionStatus.TRIALING,
            trial_start=datetime.utcnow(),
            trial_end=datetime.utcnow() + timedelta(days=settings.trial_duration_days),
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=settings.trial_duration_days),
            seats=1,
            term=BillingTerm.MONTHLY,
            dunning_status=DunningStatus.NONE
        )
        
        logger.info(
            "Subscription record created",
            subscription_id=stripe_subscription_id,
            guardian_id=guardian_id,
            learner_id=learner_id
        )
        
        return record
    
    async def handle_subscription_update(self, stripe_subscription_id: str, 
                                       new_status: str, 
                                       period_start: datetime,
                                       period_end: datetime) -> bool:
        """Handle subscription status updates from Stripe"""
        try:
            status = SubscriptionStatus(new_status)
            
            logger.info(
                "Handling subscription update",
                subscription_id=stripe_subscription_id,
                new_status=status,
                period_start=period_start,
                period_end=period_end
            )
            
            # Update local record
            # Database update would go here
            
            # Handle specific status changes
            if status == SubscriptionStatus.PAST_DUE:
                await self.dunning_service.handle_payment_failure(
                    stripe_subscription_id, 
                    "unknown_invoice"  # Would get from webhook
                )
            
            return True
            
        except Exception as e:
            logger.error("Failed to handle subscription update", 
                        subscription_id=stripe_subscription_id, error=str(e))
            return False
    
    async def get_subscription_status(self, subscription_id: str) -> Optional[SubscriptionRecord]:
        """Get subscription status and details"""
        # Database query would go here
        logger.info("Retrieving subscription status", subscription_id=subscription_id)
        return None
    
    async def list_overdue_subscriptions(self) -> List[SubscriptionRecord]:
        """List subscriptions that are overdue for dunning processing"""
        # Database query for past_due subscriptions
        logger.info("Retrieving overdue subscriptions")
        return []


# Global service instances
dunning_service = DunningService()
subscription_service = SubscriptionService()
