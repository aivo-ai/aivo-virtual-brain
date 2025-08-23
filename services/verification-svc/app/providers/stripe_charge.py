"""
Stripe Micro-Charge Provider for Guardian Identity Verification
COPPA-compliant $0.10 charge verification with auto-refund
"""

import stripe
import structlog
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
import hashlib
import json

from app.config import settings
from app.models import ChargeVerification, VerificationStatus, FailureReason
from app.schemas import MicroChargeResponse

logger = structlog.get_logger(__name__)

# Configure Stripe
if settings.stripe_config:
    stripe.api_key = settings.stripe_config.secret_key
    stripe.api_version = "2023-10-16"


class StripeChargeProvider:
    """Stripe integration for micro-charge identity verification"""
    
    def __init__(self):
        self.config = settings.stripe_config
        if not self.config:
            logger.warning("Stripe not configured - micro-charge verification unavailable")
        else:
            logger.info("Stripe charge provider initialized", 
                       amount_cents=self.config.micro_charge_amount_cents,
                       auto_refund=self.config.auto_refund)
    
    @property
    def is_available(self) -> bool:
        """Check if Stripe is properly configured"""
        return self.config is not None
    
    async def create_verification_intent(
        self,
        verification_id: str,
        guardian_user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[MicroChargeResponse, ChargeVerification]:
        """
        Create Stripe PaymentIntent for micro-charge verification
        
        Args:
            verification_id: Verification record ID
            guardian_user_id: Guardian user ID
            metadata: Additional metadata for the charge
            
        Returns:
            Tuple of MicroChargeResponse and ChargeVerification record
        """
        if not self.is_available:
            raise ValueError("Stripe not configured for micro-charge verification")
        
        try:
            # Prepare charge metadata (COPPA-compliant)
            charge_metadata = {
                "verification_id": verification_id,
                "guardian_user_id": guardian_user_id,
                "purpose": "identity_verification",
                "coppa_compliant": "true",
                "auto_refund": str(self.config.auto_refund).lower(),
                "service": "aivo-verification-svc",
                **(metadata or {})
            }
            
            # Create PaymentIntent for micro-charge
            payment_intent = stripe.PaymentIntent.create(
                amount=self.config.micro_charge_amount_cents,
                currency="usd",
                automatic_payment_methods={
                    'enabled': True,
                },
                metadata=charge_metadata,
                description=f"Guardian identity verification - ${self.config.micro_charge_amount_cents/100:.2f}",
                statement_descriptor="AIVO ID VERIFY",
                receipt_email=None,  # No email for privacy
                setup_future_usage=None,  # Don't store payment method
                confirmation_method='automatic',
                capture_method='automatic'
            )
            
            logger.info("Stripe PaymentIntent created",
                       payment_intent_id=payment_intent.id,
                       verification_id=verification_id,
                       amount_cents=self.config.micro_charge_amount_cents)
            
            # Create local charge verification record
            charge_verification = ChargeVerification(
                verification_id=verification_id,
                stripe_payment_intent_id=payment_intent.id,
                charge_amount_cents=self.config.micro_charge_amount_cents,
                currency="USD",
                charge_status="requires_payment_method"
            )
            
            # Create response
            response = MicroChargeResponse(
                client_secret=payment_intent.client_secret,
                publishable_key=self.config.publishable_key,
                amount_cents=self.config.micro_charge_amount_cents,
                currency="USD"
            )
            
            return response, charge_verification
            
        except stripe.StripeError as e:
            logger.error("Failed to create Stripe PaymentIntent",
                        error=str(e),
                        verification_id=verification_id,
                        error_code=getattr(e, 'code', 'unknown'))
            raise
    
    async def process_webhook_event(
        self,
        event_data: Dict[str, Any],
        signature: str,
        raw_body: bytes
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        Process Stripe webhook event for verification status updates
        
        Args:
            event_data: Stripe event data
            signature: Webhook signature
            raw_body: Raw webhook body for signature verification
            
        Returns:
            Tuple of (success, verification_id, processed_data)
        """
        if not self.is_available:
            return False, None, {"error": "Stripe not configured"}
        
        try:
            # Verify webhook signature
            if not await self._verify_webhook_signature(raw_body, signature):
                logger.error("Stripe webhook signature verification failed")
                return False, None, {"error": "Invalid webhook signature"}
            
            event_type = event_data.get('type')
            event_object = event_data.get('data', {}).get('object', {})
            
            # Extract verification ID from metadata
            metadata = event_object.get('metadata', {})
            verification_id = metadata.get('verification_id')
            
            if not verification_id:
                logger.warning("Stripe webhook missing verification_id", event_type=event_type)
                return False, None, {"error": "Missing verification_id"}
            
            logger.info("Processing Stripe webhook",
                       event_type=event_type,
                       verification_id=verification_id,
                       payment_intent_id=event_object.get('id'))
            
            # Process different event types
            if event_type == 'payment_intent.succeeded':
                return await self._handle_payment_succeeded(event_object, verification_id)
            elif event_type == 'payment_intent.payment_failed':
                return await self._handle_payment_failed(event_object, verification_id)
            elif event_type == 'payment_intent.canceled':
                return await self._handle_payment_canceled(event_object, verification_id)
            else:
                logger.info("Unhandled Stripe event type", event_type=event_type)
                return True, verification_id, {"event_type": event_type, "processed": False}
        
        except Exception as e:
            logger.error("Error processing Stripe webhook",
                        error=str(e),
                        event_type=event_data.get('type'),
                        exc_info=True)
            return False, None, {"error": str(e)}
    
    async def _handle_payment_succeeded(
        self,
        payment_intent: Dict[str, Any],
        verification_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle successful payment verification"""
        payment_intent_id = payment_intent.get('id')
        payment_method = payment_intent.get('payment_method')
        
        # Extract minimal payment method details for fraud detection
        card_details = {}
        if payment_method:
            try:
                pm = stripe.PaymentMethod.retrieve(payment_method)
                if pm.card:
                    card_details = {
                        "fingerprint": pm.card.fingerprint,
                        "last_four": pm.card.last4,
                        "brand": pm.card.brand,
                        "funding": pm.card.funding
                    }
            except stripe.StripeError as e:
                logger.warning("Failed to retrieve payment method details", error=str(e))
        
        processed_data = {
            "status": "verified",
            "payment_intent_id": payment_intent_id,
            "charged_at": datetime.utcnow().isoformat(),
            "card_details": card_details,
            "verification_method": "micro_charge"
        }
        
        # Schedule auto-refund if enabled
        if self.config.auto_refund:
            await self._schedule_auto_refund(payment_intent_id, verification_id)
        
        logger.info("Guardian verification successful via micro-charge",
                   verification_id=verification_id,
                   payment_intent_id=payment_intent_id)
        
        return True, verification_id, processed_data
    
    async def _handle_payment_failed(
        self,
        payment_intent: Dict[str, Any],
        verification_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle failed payment verification"""
        payment_intent_id = payment_intent.get('id')
        last_payment_error = payment_intent.get('last_payment_error', {})
        
        # Map Stripe error codes to our failure reasons
        error_code = last_payment_error.get('code', '')
        failure_reason = self._map_stripe_error_to_failure_reason(error_code)
        
        processed_data = {
            "status": "failed",
            "payment_intent_id": payment_intent_id,
            "failure_reason": failure_reason.value,
            "error_code": error_code,
            "error_message": last_payment_error.get('message', ''),
            "verification_method": "micro_charge"
        }
        
        logger.warning("Guardian verification failed via micro-charge",
                      verification_id=verification_id,
                      payment_intent_id=payment_intent_id,
                      error_code=error_code,
                      failure_reason=failure_reason.value)
        
        return True, verification_id, processed_data
    
    async def _handle_payment_canceled(
        self,
        payment_intent: Dict[str, Any],
        verification_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Handle canceled payment verification"""
        payment_intent_id = payment_intent.get('id')
        
        processed_data = {
            "status": "failed",
            "payment_intent_id": payment_intent_id,
            "failure_reason": "canceled",
            "verification_method": "micro_charge"
        }
        
        logger.info("Guardian verification canceled via micro-charge",
                   verification_id=verification_id,
                   payment_intent_id=payment_intent_id)
        
        return True, verification_id, processed_data
    
    async def _verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, signature, self.config.webhook_secret
            )
            return True
        except (stripe.SignatureVerificationError, ValueError) as e:
            logger.error("Webhook signature verification failed", error=str(e))
            return False
    
    def _map_stripe_error_to_failure_reason(self, stripe_error_code: str) -> FailureReason:
        """Map Stripe error codes to internal failure reasons"""
        error_mapping = {
            'insufficient_funds': FailureReason.INSUFFICIENT_FUNDS,
            'card_declined': FailureReason.CARD_DECLINED,
            'expired_card': FailureReason.CARD_DECLINED,
            'incorrect_cvc': FailureReason.CARD_DECLINED,
            'processing_error': FailureReason.PROVIDER_ERROR,
            'rate_limit': FailureReason.TOO_MANY_ATTEMPTS,
        }
        return error_mapping.get(stripe_error_code, FailureReason.PROVIDER_ERROR)
    
    async def _schedule_auto_refund(self, payment_intent_id: str, verification_id: str):
        """Schedule automatic refund for micro-charge after delay"""
        try:
            # For now, we'll refund immediately after verification
            # In production, this could be queued for delayed processing
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                metadata={
                    "verification_id": verification_id,
                    "reason": "identity_verification_complete",
                    "auto_refund": "true"
                }
            )
            
            logger.info("Auto-refund processed for verification",
                       verification_id=verification_id,
                       payment_intent_id=payment_intent_id,
                       refund_id=refund.id)
        
        except stripe.StripeError as e:
            logger.error("Failed to process auto-refund",
                        verification_id=verification_id,
                        payment_intent_id=payment_intent_id,
                        error=str(e))
    
    async def manually_refund_charge(
        self,
        payment_intent_id: str,
        reason: str = "manual_refund"
    ) -> bool:
        """Manually refund a charge (admin function)"""
        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                metadata={
                    "reason": reason,
                    "manual_refund": "true"
                }
            )
            
            logger.info("Manual refund processed",
                       payment_intent_id=payment_intent_id,
                       refund_id=refund.id,
                       reason=reason)
            return True
        
        except stripe.StripeError as e:
            logger.error("Failed to process manual refund",
                        payment_intent_id=payment_intent_id,
                        error=str(e))
            return False
    
    async def get_charge_details(self, payment_intent_id: str) -> Optional[Dict[str, Any]]:
        """Get charge details for verification (admin function)"""
        try:
            payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            # Return minimal, privacy-compliant details
            return {
                "id": payment_intent.id,
                "status": payment_intent.status,
                "amount": payment_intent.amount,
                "currency": payment_intent.currency,
                "created": payment_intent.created,
                "metadata": payment_intent.metadata
            }
        
        except stripe.StripeError as e:
            logger.error("Failed to retrieve charge details",
                        payment_intent_id=payment_intent_id,
                        error=str(e))
            return None


# Global provider instance
stripe_charge_provider = StripeChargeProvider()
