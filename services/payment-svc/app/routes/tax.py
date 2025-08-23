"""
Tax calculation and management API routes
"""

import structlog
from datetime import datetime
from typing import Dict, Any, List, Optional
from decimal import Decimal
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field, validator

from app.tax.stripe_tax import tax_calculator, TaxableItem, BillingAddress
from app.tax.validators import TaxIDValidator, BillingAddressValidator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/tax", tags=["Tax"])


# Request/Response Models

class TaxIDRequest(BaseModel):
    """Request to validate tax ID"""
    tax_id: str = Field(..., description="Tax identification number")
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")
    
    @validator('country')
    def validate_country(cls, v):
        return v.upper()


class TaxIDResponse(BaseModel):
    """Tax ID validation response"""
    tax_id: str = Field(..., description="Tax identification number")
    country: str = Field(..., description="Country code")
    valid: bool = Field(..., description="Whether tax ID is valid")
    tax_id_type: Optional[str] = Field(None, description="Detected tax ID type")
    requirements: Dict[str, Any] = Field(..., description="Tax ID requirements for country")


class BillingAddressRequest(BaseModel):
    """Billing address for tax calculation"""
    line1: str = Field(..., description="Address line 1")
    line2: Optional[str] = Field(None, description="Address line 2")
    city: str = Field(..., description="City")
    state: Optional[str] = Field(None, description="State/Province")
    postal_code: str = Field(..., description="Postal/ZIP code")
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")
    
    @validator('country')
    def validate_country(cls, v):
        return v.upper()


class TaxCalculationItem(BaseModel):
    """Item for tax calculation"""
    amount: Decimal = Field(..., description="Item amount in dollars")
    description: str = Field(..., description="Item description")
    reference: str = Field(..., description="Item reference/ID")
    tax_code: Optional[str] = Field(None, description="Stripe tax code")


class TaxCalculationRequest(BaseModel):
    """Request for tax calculation"""
    items: List[TaxCalculationItem] = Field(..., description="Items to calculate tax for")
    billing_address: BillingAddressRequest = Field(..., description="Billing address")
    customer_id: Optional[str] = Field(None, description="Stripe customer ID")
    tax_ids: Optional[List[str]] = Field(None, description="Customer tax IDs")


class TaxLineItemResponse(BaseModel):
    """Tax line item in response"""
    tax_type: str = Field(..., description="Type of tax")
    rate: Decimal = Field(..., description="Tax rate as percentage")
    amount: Decimal = Field(..., description="Tax amount in dollars")
    jurisdiction: str = Field(..., description="Tax jurisdiction")


class TaxCalculationResponse(BaseModel):
    """Tax calculation response"""
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    total_tax: Decimal = Field(..., description="Total tax amount")
    total: Decimal = Field(..., description="Total including tax")
    tax_lines: List[TaxLineItemResponse] = Field(..., description="Tax breakdown")
    currency: str = Field(..., description="Currency code")
    calculation_id: Optional[str] = Field(None, description="Tax calculation ID for reference")


class CustomerTaxProfileRequest(BaseModel):
    """Request to update customer tax profile"""
    customer_id: str = Field(..., description="Customer ID")
    billing_address: BillingAddressRequest = Field(..., description="Billing address")
    tax_ids: Optional[List[str]] = Field(None, description="Tax identification numbers")
    tax_exempt: bool = Field(default=False, description="Whether customer is tax exempt")
    tax_exempt_reason: Optional[str] = Field(None, description="Reason for tax exemption")


class CustomerTaxProfileResponse(BaseModel):
    """Customer tax profile response"""
    customer_id: str = Field(..., description="Customer ID")
    billing_address: BillingAddressRequest = Field(..., description="Current billing address")
    tax_ids: List[str] = Field(..., description="Validated tax IDs")
    tax_exempt: bool = Field(..., description="Tax exemption status")
    tax_exempt_reason: Optional[str] = Field(None, description="Tax exemption reason")
    updated_at: datetime = Field(..., description="Last update timestamp")


# API Endpoints

@router.post(
    "/validate-id",
    response_model=TaxIDResponse,
    summary="Validate Tax ID",
    description="Validate tax identification number format and get requirements"
)
async def validate_tax_id(request: TaxIDRequest) -> TaxIDResponse:
    """Validate tax ID format and return requirements for the country"""
    
    try:
        # Validate format
        is_valid, tax_id_type = TaxIDValidator.validate_format(
            request.tax_id, 
            request.country
        )
        
        # Get requirements for country
        requirements = TaxIDValidator.get_tax_id_requirements(request.country)
        
        # Additional validation via Stripe if format is valid
        if is_valid and tax_id_type:
            stripe_valid = await tax_calculator.validate_tax_id(
                request.tax_id, 
                request.country
            )
            is_valid = is_valid and stripe_valid
        
        logger.info("Tax ID validated",
                   tax_id=request.tax_id[:4] + "****",  # Mask for privacy
                   country=request.country,
                   valid=is_valid,
                   tax_id_type=tax_id_type)
        
        return TaxIDResponse(
            tax_id=request.tax_id,
            country=request.country,
            valid=is_valid,
            tax_id_type=tax_id_type,
            requirements=requirements
        )
        
    except Exception as e:
        logger.error("Tax ID validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tax ID validation failed"
        )


@router.post(
    "/validate-address", 
    summary="Validate Billing Address",
    description="Validate billing address format and completeness"
)
async def validate_billing_address(address: BillingAddressRequest) -> Dict[str, Any]:
    """Validate billing address format and completeness"""
    
    try:
        # Convert to dict for validation
        address_data = address.dict()
        
        # Validate address
        is_valid, errors = BillingAddressValidator.validate_address(address_data)
        
        # Get requirements for country
        requirements = BillingAddressValidator.get_address_requirements(address.country)
        
        logger.info("Billing address validated",
                   country=address.country,
                   valid=is_valid,
                   error_count=len(errors))
        
        return {
            "valid": is_valid,
            "errors": errors,
            "requirements": requirements
        }
        
    except Exception as e:
        logger.error("Address validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Address validation failed"
        )


@router.post(
    "/calculate",
    response_model=TaxCalculationResponse,
    summary="Calculate Tax",
    description="Calculate tax for items based on billing address and customer details"
)
async def calculate_tax(request: TaxCalculationRequest) -> TaxCalculationResponse:
    """Calculate tax for subscription or invoice items"""
    
    try:
        # Validate billing address first
        address_data = request.billing_address.dict()
        is_valid, errors = BillingAddressValidator.validate_address(address_data)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid billing address: {', '.join(errors)}"
            )
        
        # Convert items to taxable items
        taxable_items = [
            TaxableItem(
                amount=item.amount,
                reference=item.reference,
                tax_code=item.tax_code
            )
            for item in request.items
        ]
        
        # Convert billing address
        billing_address = BillingAddress(
            line1=request.billing_address.line1,
            line2=request.billing_address.line2,
            city=request.billing_address.city,
            state=request.billing_address.state,
            postal_code=request.billing_address.postal_code,
            country=request.billing_address.country
        )
        
        # Calculate tax
        calculation = await tax_calculator.calculate_tax(
            items=taxable_items,
            billing_address=billing_address,
            customer_id=request.customer_id,
            tax_ids=request.tax_ids
        )
        
        # Convert response
        tax_lines = [
            TaxLineItemResponse(
                tax_type=line.tax_type,
                rate=line.rate * 100,  # Convert to percentage
                amount=line.amount,
                jurisdiction=line.jurisdiction
            )
            for line in calculation.tax_lines
        ]
        
        logger.info("Tax calculation completed",
                   subtotal=float(calculation.subtotal),
                   total_tax=float(calculation.total_tax),
                   total=float(calculation.total),
                   items_count=len(request.items))
        
        return TaxCalculationResponse(
            subtotal=calculation.subtotal,
            total_tax=calculation.total_tax,
            total=calculation.total,
            tax_lines=tax_lines,
            currency=calculation.currency,
            calculation_id=calculation.tax_calculation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Tax calculation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tax calculation failed"
        )


@router.get(
    "/requirements/{country}",
    summary="Get Tax Requirements",
    description="Get tax ID and address requirements for a specific country"
)
async def get_tax_requirements(country: str) -> Dict[str, Any]:
    """Get tax requirements for a specific country"""
    
    try:
        country = country.upper()
        
        tax_id_requirements = TaxIDValidator.get_tax_id_requirements(country)
        address_requirements = BillingAddressValidator.get_address_requirements(country)
        
        return {
            "country": country,
            "tax_id": tax_id_requirements,
            "address": address_requirements
        }
        
    except Exception as e:
        logger.error("Failed to get tax requirements", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tax requirements"
        )


@router.put(
    "/customer-profile",
    response_model=CustomerTaxProfileResponse,
    summary="Update Customer Tax Profile", 
    description="Update customer's tax profile including billing address and tax IDs"
)
async def update_customer_tax_profile(
    request: CustomerTaxProfileRequest
) -> CustomerTaxProfileResponse:
    """Update customer tax profile with billing address and tax IDs"""
    
    try:
        # Validate billing address
        address_data = request.billing_address.dict()
        is_valid, errors = BillingAddressValidator.validate_address(address_data)
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid billing address: {', '.join(errors)}"
            )
        
        # Validate tax IDs if provided
        validated_tax_ids = []
        if request.tax_ids:
            for tax_id in request.tax_ids:
                is_valid, tax_id_type = TaxIDValidator.validate_format(
                    tax_id, 
                    request.billing_address.country
                )
                if is_valid:
                    validated_tax_ids.append(tax_id)
                else:
                    logger.warning("Invalid tax ID provided", 
                                 tax_id=tax_id[:4] + "****")
        
        # TODO: Store in database - for now return the request data
        # In a real implementation, this would update customer record
        
        logger.info("Customer tax profile updated",
                   customer_id=request.customer_id,
                   country=request.billing_address.country,
                   tax_ids_count=len(validated_tax_ids),
                   tax_exempt=request.tax_exempt)
        
        return CustomerTaxProfileResponse(
            customer_id=request.customer_id,
            billing_address=request.billing_address,
            tax_ids=validated_tax_ids,
            tax_exempt=request.tax_exempt,
            tax_exempt_reason=request.tax_exempt_reason,
            updated_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update customer tax profile", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update customer tax profile"
        )
