"""
Stripe Webhook Handler
Processes Stripe webhook events for payment failures, subscription updates, and checkout completion
"""

import json
import structlog
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import Request, HTTPException, status

from app.config import settings
from app.stripe_service import stripe_service
from app.subscription_service import subscription_service, dunning_service
from app.schemas import (
    PaymentFailedEvent, SubscriptionUpdatedEvent, CheckoutCompletedEvent,
    SubscriptionStatus, PaymentStatus
)

logger = structlog.get_logger(__name__)


class WebhookHandler:
    """Handles Stripe webhook events with proper verification and processing"""
    
    def __init__(self):
        self.supported_events = {
            "invoice.payment_failed",
            "customer.subscription.updated", 
            "checkout.session.completed"
        }
        logger.info("Webhook handler initialized", supported_events=self.supported_events)
    
    async def process_webhook(self, request: Request) -> Dict[str, Any]:
        """Process incoming Stripe webhook with signature verification"""
        try:
            # Get raw body and signature
            body = await request.body()
            signature = request.headers.get("stripe-signature")
            
            if not signature:
                logger.warning("Missing Stripe signature header")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing stripe-signature header"
                )
            
            # Verify webhook signature
            if not await stripe_service.verify_webhook_signature(body, signature):
                logger.error("Webhook signature verification failed")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid webhook signature"
                )
            
            # Parse event
            try:
                event = json.loads(body.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error("Failed to parse webhook JSON", error=str(e))
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid JSON payload"
                )
            
            event_type = event.get("type")
            event_id = event.get("id")
            
            logger.info(
                "Processing webhook event",
                event_type=event_type,
                event_id=event_id
            )
            
            # Process supported events
            if event_type not in self.supported_events:
                logger.info("Unsupported event type, acknowledging", event_type=event_type)
                return {"status": "ignored", "event_type": event_type}
            
            # Route to appropriate handler
            success = False
            if event_type == "invoice.payment_failed":
                success = await self._handle_payment_failed(event)
            elif event_type == "customer.subscription.updated":
                success = await self._handle_subscription_updated(event)
            elif event_type == "checkout.session.completed":
                success = await self._handle_checkout_completed(event)
            
            if success:
                logger.info("Webhook event processed successfully", 
                           event_type=event_type, event_id=event_id)
                return {"status": "processed", "event_type": event_type, "event_id": event_id}
            else:
                logger.error("Failed to process webhook event", 
                            event_type=event_type, event_id=event_id)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to process webhook event"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Unexpected error processing webhook", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
    
    async def _handle_payment_failed(self, event: Dict[str, Any]) -> bool:
        """Handle invoice.payment_failed webhook"""
        try:
            invoice_data = event["data"]["object"]
            
            payment_failed = PaymentFailedEvent(
                subscription_id=invoice_data.get("subscription", ""),
                customer_id=invoice_data.get("customer", ""),
                invoice_id=invoice_data["id"],
                amount_cents=invoice_data.get("amount_due", 0),
                failure_reason=invoice_data.get("last_payment_error", {}).get("message"),
                attempt_count=invoice_data.get("attempt_count", 1)
            )
            
            logger.warning(
                "Payment failed event received",
                subscription_id=payment_failed.subscription_id,
                invoice_id=payment_failed.invoice_id,
                amount=payment_failed.amount_cents,
                attempt=payment_failed.attempt_count
            )
            
            # Handle payment failure and start dunning process
            success = await dunning_service.handle_payment_failure(
                payment_failed.subscription_id,
                payment_failed.invoice_id,
                payment_failed.failure_reason
            )
            
            # Calculate days past due for immediate dunning
            # This would typically come from subscription data
            days_past_due = 1  # First day of failure
            
            await dunning_service.process_dunning_schedule(
                payment_failed.subscription_id,
                days_past_due
            )
            
            return success
            
        except Exception as e:
            logger.error("Error handling payment failed event", error=str(e))
            return False
    
    async def _handle_subscription_updated(self, event: Dict[str, Any]) -> bool:
        """Handle customer.subscription.updated webhook"""
        try:
            subscription_data = event["data"]["object"]
            
            subscription_updated = SubscriptionUpdatedEvent(
                subscription_id=subscription_data["id"],
                customer_id=subscription_data["customer"],
                status=SubscriptionStatus(subscription_data["status"]),
                current_period_start=datetime.fromtimestamp(subscription_data["current_period_start"]),
                current_period_end=datetime.fromtimestamp(subscription_data["current_period_end"]),
                trial_end=datetime.fromtimestamp(subscription_data["trial_end"]) if subscription_data.get("trial_end") else None
            )
            
            logger.info(
                "Subscription updated event received",
                subscription_id=subscription_updated.subscription_id,
                status=subscription_updated.status,
                period_start=subscription_updated.current_period_start,
                period_end=subscription_updated.current_period_end
            )
            
            # Update local subscription record
            success = await subscription_service.handle_subscription_update(
                subscription_updated.subscription_id,
                subscription_updated.status.value,
                subscription_updated.current_period_start,
                subscription_updated.current_period_end
            )
            
            # Handle status-specific logic
            if subscription_updated.status == SubscriptionStatus.ACTIVE:
                logger.info("Subscription activated", 
                           subscription_id=subscription_updated.subscription_id)
                # Clear any dunning status
                # Reset grace period
                
            elif subscription_updated.status == SubscriptionStatus.CANCELED:
                logger.info("Subscription canceled", 
                           subscription_id=subscription_updated.subscription_id)
                # Send cancellation notification
                # Update user access
                
            return success
            
        except Exception as e:
            logger.error("Error handling subscription updated event", error=str(e))
            return False
    
    async def _handle_checkout_completed(self, event: Dict[str, Any]) -> bool:
        """Handle checkout.session.completed webhook"""
        try:
            session_data = event["data"]["object"]
            
            checkout_completed = CheckoutCompletedEvent(
                session_id=session_data["id"],
                customer_id=session_data.get("customer", ""),
                subscription_id=session_data.get("subscription"),
                payment_status=PaymentStatus(session_data.get("payment_status", "succeeded")),
                amount_total=session_data.get("amount_total", 0)
            )
            
            logger.info(
                "Checkout completed event received",
                session_id=checkout_completed.session_id,
                customer_id=checkout_completed.customer_id,
                subscription_id=checkout_completed.subscription_id,
                amount=checkout_completed.amount_total,
                payment_status=checkout_completed.payment_status
            )
            
            if checkout_completed.payment_status == PaymentStatus.SUCCEEDED:
                # Activate subscription
                if checkout_completed.subscription_id:
                    # Create or update subscription record
                    # Get metadata from session
                    metadata = session_data.get("metadata", {})
                    guardian_id = metadata.get("guardian_id")
                    learner_id = metadata.get("learner_id")
                    
                    if guardian_id and learner_id:
                        subscription_record = await subscription_service.create_subscription_record(
                            checkout_completed.subscription_id,
                            guardian_id,
                            learner_id,
                            checkout_completed.customer_id
                        )
                        
                        logger.info(
                            "Subscription record created from checkout",
                            subscription_id=checkout_completed.subscription_id,
                            guardian_id=guardian_id,
                            learner_id=learner_id
                        )
                
                # Send confirmation email
                # Update user access/permissions
                
            return True
            
        except Exception as e:
            logger.error("Error handling checkout completed event", error=str(e))
            return False


# Global webhook handler instance
webhook_handler = WebhookHandler()
