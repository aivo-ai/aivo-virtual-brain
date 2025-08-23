"""
Stripe Tax integration for payment service
Handles tax calculation, rate lookup, and compliance
"""

import stripe
import structlog
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from pydantic import BaseModel, Field
from fastapi import HTTPException

from app.config import settings

logger = structlog.get_logger(__name__)

# Configure Stripe
stripe.api_key = settings.stripe_secret_key


class TaxLineItem(BaseModel):
    """Tax line item breakdown"""
    tax_type: str = Field(..., description="Type of tax (VAT, sales, etc)")
    rate: Decimal = Field(..., description="Tax rate as decimal")
    amount: Decimal = Field(..., description="Tax amount")
    jurisdiction: str = Field(..., description="Tax jurisdiction")


class TaxCalculationResult(BaseModel):
    """Result of tax calculation"""
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    total_tax: Decimal = Field(..., description="Total tax amount")
    total: Decimal = Field(..., description="Total including tax")
    tax_lines: List[TaxLineItem] = Field(..., description="Tax breakdown")
    currency: str = Field(..., description="Currency code")
    tax_calculation_id: Optional[str] = Field(None, description="Stripe tax calculation ID")


class BillingAddress(BaseModel):
    """Billing address for tax calculation"""
    line1: str = Field(..., description="Address line 1")
    line2: Optional[str] = Field(None, description="Address line 2")
    city: str = Field(..., description="City")
    state: Optional[str] = Field(None, description="State/Province")
    postal_code: str = Field(..., description="Postal/ZIP code")
    country: str = Field(..., description="Country code (ISO 3166-1 alpha-2)")


class TaxableItem(BaseModel):
    """Item for tax calculation"""
    amount: Decimal = Field(..., description="Item amount in cents")
    reference: str = Field(..., description="Item reference/ID")
    tax_code: Optional[str] = Field(None, description="Stripe tax code")


class TaxCalculator:
    """Stripe Tax integration for calculating taxes on subscriptions and invoices"""
    
    def __init__(self):
        self.enabled = True  # Would check if Stripe Tax is enabled in settings
        
    async def calculate_tax(
        self,
        items: List[TaxableItem],
        billing_address: BillingAddress,
        customer_id: Optional[str] = None,
        tax_ids: Optional[List[str]] = None
    ) -> TaxCalculationResult:
        """
        Calculate tax for given items and billing address
        
        Args:
            items: List of taxable items
            billing_address: Customer billing address
            customer_id: Stripe customer ID (optional)
            tax_ids: Customer tax IDs (optional)
            
        Returns:
            Tax calculation result with breakdown
        """
        try:
            if not self.enabled:
                # Return zero tax if Stripe Tax is disabled
                subtotal = sum(item.amount for item in items)
                return TaxCalculationResult(
                    subtotal=subtotal,
                    total_tax=Decimal('0'),
                    total=subtotal,
                    tax_lines=[],
                    currency="usd"
                )
            
            # Convert items to Stripe format
            stripe_items = []
            for item in items:
                stripe_item = {
                    "amount": int(item.amount * 100),  # Convert to cents
                    "reference": item.reference,
                }
                if item.tax_code:
                    stripe_item["tax_code"] = item.tax_code
                stripe_items.append(stripe_item)
            
            # Prepare calculation parameters
            calc_params = {
                "currency": "usd",
                "line_items": stripe_items,
                "customer_details": {
                    "address": {
                        "line1": billing_address.line1,
                        "city": billing_address.city,
                        "country": billing_address.country,
                        "postal_code": billing_address.postal_code,
                    },
                    "address_source": "billing",
                }
            }
            
            # Add optional fields
            if billing_address.line2:
                calc_params["customer_details"]["address"]["line2"] = billing_address.line2
            if billing_address.state:
                calc_params["customer_details"]["address"]["state"] = billing_address.state
                
            if customer_id:
                calc_params["customer"] = customer_id
                
            if tax_ids:
                calc_params["customer_details"]["tax_ids"] = [
                    {"type": self._detect_tax_id_type(tax_id), "value": tax_id}
                    for tax_id in tax_ids
                ]
            
            # Calculate tax using Stripe Tax
            calculation = stripe.tax.Calculation.create(**calc_params)
            
            # Parse results
            subtotal = Decimal(str(calculation.amount_total)) / 100
            total_tax = Decimal(str(calculation.tax_amount_exclusive)) / 100
            total = subtotal + total_tax
            
            # Parse tax breakdown
            tax_lines = []
            for tax_breakdown in calculation.tax_breakdown:
                tax_lines.append(TaxLineItem(
                    tax_type=tax_breakdown.tax_rate_details.tax_type,
                    rate=Decimal(str(tax_breakdown.tax_rate_details.percentage_decimal)),
                    amount=Decimal(str(tax_breakdown.tax_amount)) / 100,
                    jurisdiction=tax_breakdown.jurisdiction.display_name
                ))
            
            logger.info("Tax calculation completed",
                       subtotal=float(subtotal),
                       total_tax=float(total_tax),
                       total=float(total),
                       calculation_id=calculation.id)
            
            return TaxCalculationResult(
                subtotal=subtotal,
                total_tax=total_tax,
                total=total,
                tax_lines=tax_lines,
                currency="usd",
                tax_calculation_id=calculation.id
            )
            
        except stripe.StripeError as e:
            logger.error("Stripe tax calculation failed", error=str(e))
            # Fallback to zero tax on error
            subtotal = sum(item.amount for item in items)
            return TaxCalculationResult(
                subtotal=subtotal,
                total_tax=Decimal('0'),
                total=subtotal,
                tax_lines=[],
                currency="usd"
            )
        except Exception as e:
            logger.error("Tax calculation error", error=str(e))
            raise HTTPException(
                status_code=500,
                detail="Tax calculation failed"
            )
    
    async def validate_tax_id(self, tax_id: str, country: str) -> bool:
        """
        Validate tax ID using Stripe Tax ID validation
        
        Args:
            tax_id: Tax identification number
            country: Country code
            
        Returns:
            True if valid, False otherwise
        """
        try:
            validation = stripe.tax.TaxId.create(
                type=self._detect_tax_id_type(tax_id, country),
                value=tax_id,
                owner={
                    "type": "account",
                }
            )
            return validation.verification.status == "verified"
        except stripe.StripeError:
            return False
    
    def _detect_tax_id_type(self, tax_id: str, country: Optional[str] = None) -> str:
        """
        Detect tax ID type based on format and country
        
        Args:
            tax_id: Tax ID string
            country: Country code (optional)
            
        Returns:
            Stripe tax ID type
        """
        tax_id = tax_id.replace(" ", "").replace("-", "").upper()
        
        # US EIN
        if country == "US" and len(tax_id) == 9 and tax_id.isdigit():
            return "us_ein"
        
        # EU VAT IDs
        if tax_id.startswith(("AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "ES", "FI", "FR", "GR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK")):
            return "eu_vat"
        
        # UK VAT
        if tax_id.startswith("GB"):
            return "gb_vat"
        
        # Canada GST/HST
        if country == "CA" and len(tax_id) == 9:
            return "ca_gst_hst"
        
        # Australia ABN
        if country == "AU" and len(tax_id) == 11:
            return "au_abn"
        
        # Default to generic
        return "unknown"
    
    async def create_tax_invoice(
        self,
        calculation_id: str,
        customer_id: str,
        invoice_metadata: Dict[str, Any]
    ) -> str:
        """
        Create a tax-compliant invoice using Stripe Tax calculation
        
        Args:
            calculation_id: Stripe tax calculation ID
            customer_id: Stripe customer ID
            invoice_metadata: Additional invoice metadata
            
        Returns:
            Stripe invoice ID
        """
        try:
            # Create invoice with tax calculation
            invoice = stripe.Invoice.create(
                customer=customer_id,
                auto_advance=True,
                metadata=invoice_metadata,
                tax_calculation=calculation_id
            )
            
            logger.info("Tax invoice created",
                       invoice_id=invoice.id,
                       customer_id=customer_id,
                       calculation_id=calculation_id)
            
            return invoice.id
            
        except stripe.StripeError as e:
            logger.error("Tax invoice creation failed", error=str(e))
            raise HTTPException(
                status_code=500,
                detail="Invoice creation failed"
            )


# Global tax calculator instance
tax_calculator = TaxCalculator()
