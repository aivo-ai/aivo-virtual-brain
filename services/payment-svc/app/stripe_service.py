"""
Stripe Integration Service
Handles all Stripe API interactions for billing, subscriptions, and webhooks
"""

import stripe
import structlog
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from decimal import Decimal

from app.config import settings
from app.schemas import (
    BillingTerm, SubscriptionStatus, PaymentStatus,
    TrialStartRequest, TrialStartResponse,
    PlanQuoteRequest, PlanQuoteResponse,
    PlanCheckoutRequest, PlanCheckoutResponse,
    DistrictInvoiceRequest, DistrictInvoiceResponse,
    StripeProductConfig
)

logger = structlog.get_logger(__name__)

# Configure Stripe
stripe.api_key = settings.stripe_secret_key
stripe.api_version = "2023-10-16"


class StripeService:
    """Stripe integration service for payment operations"""
    
    def __init__(self):
        self.product_config = StripeProductConfig()
        logger.info("Stripe service initialized", api_version=stripe.api_version)
    
    async def create_customer(self, guardian_id: str, email: str, metadata: Optional[Dict[str, Any]] = None) -> stripe.Customer:
        """Create a Stripe customer"""
        try:
            customer = stripe.Customer.create(
                email=email,
                metadata={
                    "guardian_id": guardian_id,
                    "service": "aivo-payment-svc",
                    **(metadata or {})
                }
            )
            logger.info("Stripe customer created", customer_id=customer.id, guardian_id=guardian_id)
            return customer
        except stripe.StripeError as e:
            logger.error("Failed to create Stripe customer", error=str(e), guardian_id=guardian_id)
            raise
    
    async def start_trial(self, request: TrialStartRequest) -> TrialStartResponse:
        """Start a 30-day trial subscription"""
        try:
            # Create customer if needed
            customer = stripe.Customer.create(
                email=request.email or f"{request.guardian_id}@temp.aivo.com",
                metadata={
                    "guardian_id": request.guardian_id,
                    "learner_id": request.learner_id,
                    "type": "trial"
                }
            )
            
            # Create trial subscription
            trial_end = datetime.utcnow() + timedelta(days=settings.trial_duration_days)
            
            subscription = stripe.Subscription.create(
                customer=customer.id,
                items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": self.product_config.product_name,
                            "metadata": {"type": "trial"}
                        },
                        "unit_amount": self.product_config.base_monthly_price_cents,
                        "recurring": {"interval": "month"}
                    }
                }],
                trial_end=int(trial_end.timestamp()),
                metadata={
                    "guardian_id": request.guardian_id,
                    "learner_id": request.learner_id,
                    "type": "trial"
                }
            )
            
            logger.info(
                "Trial subscription created",
                subscription_id=subscription.id,
                customer_id=customer.id,
                trial_end=trial_end,
                guardian_id=request.guardian_id,
                learner_id=request.learner_id
            )
            
            return TrialStartResponse(
                subscription_id=subscription.id,
                customer_id=customer.id,
                trial_end=trial_end,
                status=SubscriptionStatus.TRIALING,
                learner_id=request.learner_id
            )
            
        except stripe.StripeError as e:
            logger.error("Failed to start trial", error=str(e), request=request.dict())
            raise
    
    async def calculate_quote(self, request: PlanQuoteRequest) -> PlanQuoteResponse:
        """Calculate pricing quote with discounts"""
        base_price = self.product_config.base_monthly_price_cents
        
        # Calculate base subtotal
        subtotal_cents = base_price * request.seats
        
        # Apply term discounts
        term_discount_percent = self._get_term_discount(request.term)
        term_multiplier = self._get_term_multiplier(request.term)
        
        # Calculate term-adjusted subtotal
        term_subtotal = subtotal_cents * term_multiplier
        term_discount_cents = int(term_subtotal * term_discount_percent)
        
        # Apply sibling discount to sibling seats only
        sibling_discount_percent = settings.sibling_discount if request.siblings > 0 else 0.0
        sibling_discount_cents = int(
            base_price * request.siblings * term_multiplier * sibling_discount_percent
        )
        
        # Calculate final total
        total_cents = term_subtotal - term_discount_cents - sibling_discount_cents
        
        logger.info(
            "Quote calculated",
            seats=request.seats,
            siblings=request.siblings,
            term=request.term,
            subtotal=subtotal_cents,
            term_discount=term_discount_cents,
            sibling_discount=sibling_discount_cents,
            total=total_cents
        )
        
        return PlanQuoteResponse(
            base_price_cents=base_price,
            total_seats=request.seats,
            term=request.term,
            term_discount_percent=term_discount_percent,
            sibling_discount_percent=sibling_discount_percent,
            subtotal_cents=int(term_subtotal),
            term_discount_cents=term_discount_cents,
            sibling_discount_cents=sibling_discount_cents,
            total_cents=total_cents
        )
    
    async def create_checkout_session(self, request: PlanCheckoutRequest) -> PlanCheckoutResponse:
        """Create Stripe checkout session for plan purchase"""
        try:
            # Calculate pricing
            quote_request = PlanQuoteRequest(
                seats=request.seats,
                term=request.term,
                siblings=request.siblings
            )
            quote = await self.calculate_quote(quote_request)
            
            # Create checkout session
            session = stripe.checkout.Session.create(
                payment_method_types=["card"],
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{self.product_config.product_name} - {request.term.value} ({request.seats} seats)"
                        },
                        "unit_amount": quote.total_cents,
                        "recurring": {
                            "interval": self._get_stripe_interval(request.term),
                            "interval_count": self._get_interval_count(request.term)
                        }
                    },
                    "quantity": 1
                }],
                mode="subscription",
                success_url=request.success_url,
                cancel_url=request.cancel_url,
                metadata={
                    "guardian_id": request.guardian_id,
                    "learner_id": request.learner_id,
                    "seats": str(request.seats),
                    "siblings": str(request.siblings),
                    "term": request.term.value
                },
                expires_at=int((datetime.utcnow() + timedelta(hours=24)).timestamp())
            )
            
            logger.info(
                "Checkout session created",
                session_id=session.id,
                guardian_id=request.guardian_id,
                learner_id=request.learner_id,
                amount=quote.total_cents
            )
            
            return PlanCheckoutResponse(
                checkout_url=session.url,
                session_id=session.id,
                expires_at=datetime.fromtimestamp(session.expires_at)
            )
            
        except stripe.StripeError as e:
            logger.error("Failed to create checkout session", error=str(e), request=request.dict())
            raise
    
    async def create_district_invoice(self, request: DistrictInvoiceRequest) -> DistrictInvoiceResponse:
        """Create invoice for district billing"""
        try:
            # Calculate district pricing (no discounts for institutional)
            amount_cents = self.product_config.base_monthly_price_cents * request.seats
            
            # Create customer for district
            customer = stripe.Customer.create(
                email=f"billing@{request.tenant_id}.edu",
                metadata={
                    "tenant_id": request.tenant_id,
                    "type": "district"
                }
            )
            
            # Create invoice
            invoice = stripe.Invoice.create(
                customer=customer.id,
                auto_advance=False,  # Manual payment
                collection_method="send_invoice",
                days_until_due=30,
                metadata={
                    "tenant_id": request.tenant_id,
                    "seats": str(request.seats),
                    "billing_period_start": request.billing_period_start.isoformat(),
                    "billing_period_end": request.billing_period_end.isoformat(),
                    "po_number": request.po_number or ""
                }
            )
            
            # Add line item
            stripe.InvoiceItem.create(
                customer=customer.id,
                invoice=invoice.id,
                amount=amount_cents,
                currency="usd",
                description=f"AIVO Learning Platform - {request.seats} seats ({request.billing_period_start} to {request.billing_period_end})"
            )
            
            # Finalize invoice
            invoice = stripe.Invoice.finalize_invoice(invoice.id)
            
            logger.info(
                "District invoice created",
                invoice_id=invoice.id,
                tenant_id=request.tenant_id,
                seats=request.seats,
                amount=amount_cents
            )
            
            return DistrictInvoiceResponse(
                invoice_id=invoice.id,
                invoice_url=invoice.hosted_invoice_url,
                amount_cents=amount_cents,
                due_date=request.billing_period_end + timedelta(days=30),
                status=invoice.status
            )
            
        except stripe.StripeError as e:
            logger.error("Failed to create district invoice", error=str(e), request=request.dict())
            raise
    
    def _get_term_discount(self, term: BillingTerm) -> float:
        """Get discount rate for billing term"""
        discounts = {
            BillingTerm.MONTHLY: 0.0,
            BillingTerm.QUARTERLY: settings.quarterly_discount,
            BillingTerm.HALF_YEARLY: settings.half_year_discount,
            BillingTerm.YEARLY: settings.yearly_discount
        }
        return discounts[term]
    
    def _get_term_multiplier(self, term: BillingTerm) -> int:
        """Get month multiplier for billing term"""
        multipliers = {
            BillingTerm.MONTHLY: 1,
            BillingTerm.QUARTERLY: 3,
            BillingTerm.HALF_YEARLY: 6,
            BillingTerm.YEARLY: 12
        }
        return multipliers[term]
    
    def _get_stripe_interval(self, term: BillingTerm) -> str:
        """Get Stripe billing interval"""
        if term == BillingTerm.YEARLY:
            return "year"
        return "month"
    
    def _get_interval_count(self, term: BillingTerm) -> int:
        """Get Stripe interval count"""
        counts = {
            BillingTerm.MONTHLY: 1,
            BillingTerm.QUARTERLY: 3,
            BillingTerm.HALF_YEARLY: 6,
            BillingTerm.YEARLY: 1
        }
        return counts[term]
    
    async def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature"""
        try:
            stripe.Webhook.construct_event(
                payload, signature, settings.stripe_webhook_secret
            )
            return True
        except (stripe.SignatureVerificationError, ValueError) as e:
            logger.error("Webhook signature verification failed", error=str(e))
            return False
    
    async def process_webhook_event(self, event: Dict[str, Any]) -> bool:
        """Process Stripe webhook event"""
        event_type = event["type"]
        
        logger.info("Processing webhook event", event_type=event_type, event_id=event["id"])
        
        try:
            if event_type == "invoice.payment_failed":
                return await self._handle_payment_failed(event)
            elif event_type == "customer.subscription.updated":
                return await self._handle_subscription_updated(event)
            elif event_type == "checkout.session.completed":
                return await self._handle_checkout_completed(event)
            else:
                logger.info("Unhandled webhook event type", event_type=event_type)
                return True
                
        except Exception as e:
            logger.error("Error processing webhook event", event_type=event_type, error=str(e))
            return False
    
    async def _handle_payment_failed(self, event: Dict[str, Any]) -> bool:
        """Handle payment failure webhook"""
        invoice = event["data"]["object"]
        subscription_id = invoice.get("subscription")
        
        logger.warning(
            "Payment failed",
            subscription_id=subscription_id,
            invoice_id=invoice["id"],
            amount=invoice["amount_due"]
        )
        
        # This would trigger dunning process
        # Implementation depends on database and email service
        return True
    
    async def _handle_subscription_updated(self, event: Dict[str, Any]) -> bool:
        """Handle subscription update webhook"""
        subscription = event["data"]["object"]
        
        logger.info(
            "Subscription updated",
            subscription_id=subscription["id"],
            status=subscription["status"]
        )
        
        # Update subscription status in database
        return True
    
    async def _handle_checkout_completed(self, event: Dict[str, Any]) -> bool:
        """Handle checkout completion webhook"""
        session = event["data"]["object"]
        
        logger.info(
            "Checkout completed",
            session_id=session["id"],
            customer_id=session.get("customer"),
            amount_total=session.get("amount_total")
        )
        
        # Activate subscription and update database
        return True


# Global service instance
stripe_service = StripeService()
