"""
Payment Service API Routes
FastAPI routes for trials, billing, quotes, checkout, and webhooks
"""

import structlog
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Request, status, Depends

from app.config import settings
from app.schemas import (
    TrialStartRequest, TrialStartResponse,
    PlanQuoteRequest, PlanQuoteResponse,
    PlanCheckoutRequest, PlanCheckoutResponse,
    DistrictInvoiceRequest, DistrictInvoiceResponse,
    PaymentErrorResponse
)
from app.stripe_service import stripe_service
from app.webhook_handler import webhook_handler
from app.subscription_service import subscription_service
from app.routes.tax import router as tax_router
from app.routes.po_invoices import router as po_invoices_router

logger = structlog.get_logger(__name__)

router = APIRouter()

# Include sub-routers
router.include_router(tax_router, prefix="/tax", tags=["Tax"])
router.include_router(po_invoices_router, prefix="/po", tags=["PO Invoices"])


@router.post(
    "/trial/start",
    response_model=TrialStartResponse,
    status_code=201,
    summary="Start Trial Subscription",
    description="Creates a 30-day trial subscription for a guardian and learner"
)
async def start_trial(request: TrialStartRequest) -> TrialStartResponse:
    """
    Start a 30-day trial subscription
    
    Creates Stripe customer and trial subscription with:
    - 30-day trial period  
    - No immediate charge
    - Automatic billing after trial unless canceled
    """
    try:
        logger.info(
            "Starting trial subscription",
            guardian_id=request.guardian_id,
            learner_id=request.learner_id
        )
        
        # Create trial subscription via Stripe
        response = await stripe_service.start_trial(request)
        
        # Create local subscription record
        await subscription_service.create_subscription_record(
            response.subscription_id,
            request.guardian_id,
            request.learner_id,
            response.customer_id
        )
        
        logger.info(
            "Trial subscription created successfully",
            subscription_id=response.subscription_id,
            trial_end=response.trial_end
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to start trial subscription",
            guardian_id=request.guardian_id,
            learner_id=request.learner_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PaymentErrorResponse(
                error_code="trial_creation_failed",
                message="Failed to create trial subscription",
                details={"error": str(e)}
            ).dict()
        )


@router.post(
    "/plan/quote",
    response_model=PlanQuoteResponse,
    summary="Get Pricing Quote",
    description="Calculate pricing with term and sibling discounts"
)
async def get_plan_quote(request: PlanQuoteRequest) -> PlanQuoteResponse:
    """
    Calculate pricing quote with discounts
    
    Applies the following discounts:
    - Quarterly (3 months): 20% off
    - Half-yearly (6 months): 30% off  
    - Yearly (12 months): 50% off
    - Sibling discount: 10% off for additional siblings
    """
    try:
        logger.info(
            "Calculating pricing quote",
            seats=request.seats,
            term=request.term,
            siblings=request.siblings
        )
        
        # Validate sibling logic
        if request.siblings > request.seats - 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=PaymentErrorResponse(
                    error_code="invalid_sibling_count",
                    message="Sibling count cannot exceed seats - 1"
                ).dict()
            )
        
        quote = await stripe_service.calculate_quote(request)
        
        logger.info(
            "Quote calculated successfully",
            total_cents=quote.total_cents,
            term_discount=quote.term_discount_cents,
            sibling_discount=quote.sibling_discount_cents
        )
        
        return quote
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to calculate quote",
            request=request.dict(),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PaymentErrorResponse(
                error_code="quote_calculation_failed",
                message="Failed to calculate pricing quote",
                details={"error": str(e)}
            ).dict()
        )


@router.post(
    "/plan/checkout",
    response_model=PlanCheckoutResponse,
    summary="Create Checkout Session",
    description="Create Stripe checkout session for plan purchase"
)
async def create_plan_checkout(request: PlanCheckoutRequest) -> PlanCheckoutResponse:
    """
    Create Stripe checkout session
    
    Creates a Stripe Checkout session with:
    - Calculated pricing with discounts
    - Subscription billing setup
    - Success/cancel URL redirects
    - 24-hour session expiration
    """
    try:
        logger.info(
            "Creating checkout session",
            learner_id=request.learner_id,
            guardian_id=request.guardian_id,
            term=request.term,
            seats=request.seats
        )
        
        response = await stripe_service.create_checkout_session(request)
        
        logger.info(
            "Checkout session created successfully",
            session_id=response.session_id,
            expires_at=response.expires_at
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to create checkout session",
            request=request.dict(),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PaymentErrorResponse(
                error_code="checkout_creation_failed",
                message="Failed to create checkout session",
                details={"error": str(e)}
            ).dict()
        )


@router.post(
    "/district/invoice",
    response_model=DistrictInvoiceResponse,
    summary="Create District Invoice",
    description="Generate invoice for district/institutional billing"
)
async def create_district_invoice(request: DistrictInvoiceRequest) -> DistrictInvoiceResponse:
    """
    Create district invoice
    
    Generates Stripe invoice for district/school billing:
    - Fixed institutional pricing (no discounts)
    - 30-day payment terms
    - Manual payment collection
    - PO number tracking
    """
    try:
        logger.info(
            "Creating district invoice",
            tenant_id=request.tenant_id,
            seats=request.seats,
            po_number=request.po_number
        )
        
        response = await stripe_service.create_district_invoice(request)
        
        logger.info(
            "District invoice created successfully",
            invoice_id=response.invoice_id,
            amount_cents=response.amount_cents
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Failed to create district invoice",
            request=request.dict(),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=PaymentErrorResponse(
                error_code="invoice_creation_failed",
                message="Failed to create district invoice",
                details={"error": str(e)}
            ).dict()
        )


@router.post(
    "/webhooks/stripe",
    summary="Stripe Webhook Endpoint",
    description="Handles Stripe webhook events for payment processing"
)
async def handle_stripe_webhook(request: Request) -> Dict[str, Any]:
    """
    Handle Stripe webhook events
    
    Processes the following webhook events:
    - invoice.payment_failed: Triggers dunning process
    - customer.subscription.updated: Updates subscription status
    - checkout.session.completed: Activates new subscriptions
    
    All webhook requests are verified using Stripe signature.
    """
    try:
        return await webhook_handler.process_webhook(request)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook processing failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "Webhook processing failed"}
        )


# Health and service info endpoints

@router.get(
    "/health",
    summary="Service Health Check",
    description="Returns service health status"
)
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "payment-svc",
        "version": settings.version,
        "timestamp": datetime.utcnow().isoformat(),
        "stripe_configured": bool(settings.stripe_secret_key),
        "environment": settings.environment
    }


@router.get(
    "/",
    summary="Service Information",
    description="Returns payment service capabilities and configuration"
)
async def service_info() -> Dict[str, Any]:
    """Service information endpoint"""
    return {
        "service": "Payment Service",
        "version": settings.version,
        "description": "Stripe-based billing service with trials, subscriptions, and dunning",
        "capabilities": [
            "30-day trial subscriptions",
            "Term-based billing with discounts",
            "Sibling discounts",
            "District/institutional invoicing", 
            "Payment failure handling",
            "Automated dunning process",
            "Stripe webhook processing"
        ],
        "billing_terms": {
            "monthly": "No discount",
            "quarterly": f"{int(settings.quarterly_discount * 100)}% discount",
            "half_yearly": f"{int(settings.half_year_discount * 100)}% discount", 
            "yearly": f"{int(settings.yearly_discount * 100)}% discount"
        },
        "discounts": {
            "sibling": f"{int(settings.sibling_discount * 100)}% per sibling"
        },
        "dunning_policy": {
            "grace_period_days": settings.grace_period_days,
            "reminder_days": settings.dunning_failure_days,
            "cancellation_day": settings.cancellation_day
        },
        "endpoints": {
            "trial_start": "POST /trial/start",
            "plan_quote": "POST /plan/quote", 
            "plan_checkout": "POST /plan/checkout",
            "district_invoice": "POST /district/invoice",
            "webhooks": "POST /webhooks/stripe",
            "health": "GET /health"
        }
    }


# Admin/debugging endpoints (would be protected in production)

@router.get(
    "/subscriptions/{subscription_id}",
    summary="Get Subscription Details",
    description="Retrieve subscription information (admin endpoint)"
)
async def get_subscription_details(subscription_id: str) -> Dict[str, Any]:
    """Get subscription details (admin/debug endpoint)"""
    try:
        subscription = await subscription_service.get_subscription_status(subscription_id)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subscription not found"
            )
        
        return subscription.dict() if subscription else {"error": "not_found"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get subscription details", 
                    subscription_id=subscription_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscription"
        )
