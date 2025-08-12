"""
Payment Service Schemas
Pydantic models for Stripe billing, trials, and subscription management
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator


class BillingTerm(str, Enum):
    """Billing term options with associated discount rates"""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"     # 3 months, 20% discount
    HALF_YEARLY = "half_yearly" # 6 months, 30% discount
    YEARLY = "yearly"           # 12 months, 50% discount


class SubscriptionStatus(str, Enum):
    """Subscription status tracking"""
    TRIAL = "trial"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid" 
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"


class PaymentStatus(str, Enum):
    """Payment status for tracking"""
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PENDING = "pending"
    CANCELED = "canceled"


class DunningStatus(str, Enum):
    """Dunning process status"""
    NONE = "none"
    WARNING_1 = "warning_1"     # Day 3
    WARNING_2 = "warning_2"     # Day 7  
    FINAL_NOTICE = "final_notice" # Day 14
    GRACE_EXPIRED = "grace_expired" # Day 21


# Request/Response Models

class TrialStartRequest(BaseModel):
    """Request to start a trial subscription"""
    guardian_id: str = Field(..., description="Guardian user ID")
    learner_id: str = Field(..., description="Learner user ID")
    email: Optional[str] = Field(None, description="Guardian email for billing")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TrialStartResponse(BaseModel):
    """Response from trial start"""
    subscription_id: str = Field(..., description="Stripe subscription ID")
    customer_id: str = Field(..., description="Stripe customer ID")
    trial_end: datetime = Field(..., description="Trial end timestamp")
    status: SubscriptionStatus = Field(..., description="Subscription status")
    learner_id: str = Field(..., description="Associated learner ID")


class PlanQuoteRequest(BaseModel):
    """Request for pricing quote"""
    seats: int = Field(..., gt=0, description="Number of seats/learners")
    term: BillingTerm = Field(..., description="Billing term")
    siblings: int = Field(default=0, ge=0, description="Number of siblings")
    district_code: Optional[str] = Field(None, description="District for special pricing")


class PlanQuoteResponse(BaseModel):
    """Pricing quote response"""
    base_price_cents: int = Field(..., description="Base price per seat in cents")
    total_seats: int = Field(..., description="Total seats quoted")
    term: BillingTerm = Field(..., description="Billing term")
    term_discount_percent: float = Field(..., description="Term discount percentage")
    sibling_discount_percent: float = Field(..., description="Sibling discount percentage")
    subtotal_cents: int = Field(..., description="Subtotal before discounts")
    term_discount_cents: int = Field(..., description="Term discount amount")
    sibling_discount_cents: int = Field(..., description="Sibling discount amount")
    total_cents: int = Field(..., description="Final total in cents")
    currency: str = Field(default="usd", description="Currency code")


class PlanCheckoutRequest(BaseModel):
    """Request to create checkout session"""
    learner_id: str = Field(..., description="Primary learner ID")
    guardian_id: str = Field(..., description="Guardian user ID")
    term: BillingTerm = Field(..., description="Billing term")
    seats: int = Field(default=1, gt=0, description="Number of seats")
    siblings: int = Field(default=0, ge=0, description="Number of siblings")
    success_url: str = Field(..., description="Post-checkout success URL")
    cancel_url: str = Field(..., description="Checkout cancellation URL")


class PlanCheckoutResponse(BaseModel):
    """Checkout session response"""
    checkout_url: str = Field(..., description="Stripe checkout session URL")
    session_id: str = Field(..., description="Stripe checkout session ID")
    expires_at: datetime = Field(..., description="Session expiration")


class DistrictInvoiceRequest(BaseModel):
    """District billing request"""
    tenant_id: str = Field(..., description="District tenant ID")
    seats: int = Field(..., gt=0, description="Number of seats to bill")
    billing_period_start: date = Field(..., description="Billing period start")
    billing_period_end: date = Field(..., description="Billing period end")
    po_number: Optional[str] = Field(None, description="Purchase order number")


class DistrictInvoiceResponse(BaseModel):
    """District invoice response"""
    invoice_id: str = Field(..., description="Stripe invoice ID")
    invoice_url: str = Field(..., description="Invoice URL")
    amount_cents: int = Field(..., description="Invoice amount in cents")
    due_date: date = Field(..., description="Invoice due date")
    status: str = Field(..., description="Invoice status")


# Webhook Event Models

class StripeWebhookEvent(BaseModel):
    """Base Stripe webhook event"""
    id: str = Field(..., description="Event ID")
    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event data")
    created: int = Field(..., description="Event creation timestamp")


class PaymentFailedEvent(BaseModel):
    """Payment failed webhook data"""
    subscription_id: str = Field(..., description="Failed subscription ID")
    customer_id: str = Field(..., description="Customer ID")
    invoice_id: str = Field(..., description="Failed invoice ID")
    amount_cents: int = Field(..., description="Failed amount")
    failure_reason: Optional[str] = Field(None, description="Failure reason")
    attempt_count: int = Field(..., description="Payment attempt number")


class SubscriptionUpdatedEvent(BaseModel):
    """Subscription updated webhook data"""
    subscription_id: str = Field(..., description="Updated subscription ID")
    customer_id: str = Field(..., description="Customer ID")
    status: SubscriptionStatus = Field(..., description="New status")
    current_period_start: datetime = Field(..., description="Period start")
    current_period_end: datetime = Field(..., description="Period end")
    trial_end: Optional[datetime] = Field(None, description="Trial end if applicable")


class CheckoutCompletedEvent(BaseModel):
    """Checkout session completed webhook data"""
    session_id: str = Field(..., description="Completed session ID")
    customer_id: str = Field(..., description="Customer ID")
    subscription_id: Optional[str] = Field(None, description="Created subscription ID")
    payment_status: PaymentStatus = Field(..., description="Payment status")
    amount_total: int = Field(..., description="Total amount paid")


# Database Models for tracking

class SubscriptionRecord(BaseModel):
    """Subscription tracking record"""
    id: str = Field(..., description="Internal subscription ID")
    stripe_subscription_id: str = Field(..., description="Stripe subscription ID")
    stripe_customer_id: str = Field(..., description="Stripe customer ID")
    guardian_id: str = Field(..., description="Guardian user ID")
    learner_id: str = Field(..., description="Primary learner ID")
    status: SubscriptionStatus = Field(..., description="Current status")
    trial_start: Optional[datetime] = Field(None, description="Trial start")
    trial_end: Optional[datetime] = Field(None, description="Trial end")
    current_period_start: datetime = Field(..., description="Current period start")
    current_period_end: datetime = Field(..., description="Current period end")
    seats: int = Field(default=1, description="Number of seats")
    term: BillingTerm = Field(..., description="Billing term")
    dunning_status: DunningStatus = Field(default=DunningStatus.NONE)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PaymentRecord(BaseModel):
    """Payment attempt tracking"""
    id: str = Field(..., description="Internal payment ID")
    stripe_invoice_id: str = Field(..., description="Stripe invoice ID")
    subscription_id: str = Field(..., description="Associated subscription ID")
    amount_cents: int = Field(..., description="Payment amount")
    status: PaymentStatus = Field(..., description="Payment status")
    failure_reason: Optional[str] = Field(None, description="Failure reason")
    attempt_count: int = Field(default=1, description="Attempt number")
    processed_at: datetime = Field(default_factory=datetime.utcnow)


class DunningRecord(BaseModel):
    """Dunning email tracking"""
    id: str = Field(..., description="Internal dunning ID")
    subscription_id: str = Field(..., description="Associated subscription")
    dunning_status: DunningStatus = Field(..., description="Dunning stage")
    email_sent_at: datetime = Field(default_factory=datetime.utcnow)
    days_past_due: int = Field(..., description="Days past due when sent")


# Error Response Models

class PaymentErrorResponse(BaseModel):
    """Payment service error response"""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request tracking ID")


# Validation helpers

class PlanQuoteRequestValidator:
    """Validator for plan quote requests"""
    
    @staticmethod
    def validate_sibling_logic(values: Dict) -> Dict:
        """Validate sibling count logic"""
        seats = values.get('seats', 0)
        siblings = values.get('siblings', 0)
        
        if siblings > seats - 1:
            raise ValueError("Siblings cannot exceed seats - 1")
        
        return values


class StripeProductConfig(BaseModel):
    """Configuration for Stripe products and pricing"""
    base_monthly_price_cents: int = Field(default=2999, description=".99/month base price")
    currency: str = Field(default="usd", description="Currency")
    product_name: str = Field(default="AIVO Learning Platform", description="Product name")
    
    @property
    def quarterly_price_cents(self) -> int:
        """3-month price with 20% discount"""
        return int(self.base_monthly_price_cents * 3 * 0.8)
    
    @property
    def half_yearly_price_cents(self) -> int:
        """6-month price with 30% discount"""
        return int(self.base_monthly_price_cents * 6 * 0.7)
    
    @property
    def yearly_price_cents(self) -> int:
        """12-month price with 50% discount"""
        return int(self.base_monthly_price_cents * 12 * 0.5)
