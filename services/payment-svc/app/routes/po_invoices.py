"""
Purchase Order (PO) invoicing for district/enterprise customers
Handles Net-30 billing, PDF invoice generation, and dunning reminders
"""

import structlog
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal
from enum import Enum
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/po", tags=["Purchase Orders"])


# Enums and Models

class POInvoiceStatus(str, Enum):
    """PO Invoice status"""
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class PaymentTerms(str, Enum):
    """Payment terms for PO invoices"""
    NET_15 = "net_15"
    NET_30 = "net_30"
    NET_60 = "net_60"
    NET_90 = "net_90"


class InvoiceLineItem(BaseModel):
    """Line item for PO invoice"""
    description: str = Field(..., description="Item description")
    quantity: int = Field(..., description="Quantity")
    unit_price: Decimal = Field(..., description="Unit price in dollars")
    total_price: Decimal = Field(..., description="Total price (quantity × unit_price)")
    tax_rate: Optional[Decimal] = Field(None, description="Tax rate as decimal")
    tax_amount: Optional[Decimal] = Field(None, description="Tax amount")
    
    @validator('total_price')
    def validate_total_price(cls, v, values):
        if 'quantity' in values and 'unit_price' in values:
            expected = values['quantity'] * values['unit_price']
            if abs(v - expected) > Decimal('0.01'):
                raise ValueError('Total price must equal quantity × unit_price')
        return v


class BillingContact(BaseModel):
    """Billing contact information"""
    name: str = Field(..., description="Contact name")
    email: str = Field(..., description="Contact email")
    phone: Optional[str] = Field(None, description="Contact phone")
    title: Optional[str] = Field(None, description="Contact title")


class POInvoiceRequest(BaseModel):
    """Request to create PO invoice"""
    tenant_id: str = Field(..., description="Tenant/District ID")
    po_number: Optional[str] = Field(None, description="Customer PO number")
    billing_contact: BillingContact = Field(..., description="Billing contact")
    billing_address: Dict[str, Any] = Field(..., description="Billing address")
    line_items: List[InvoiceLineItem] = Field(..., description="Invoice line items")
    payment_terms: PaymentTerms = Field(default=PaymentTerms.NET_30, description="Payment terms")
    notes: Optional[str] = Field(None, description="Additional notes")
    due_date: Optional[datetime] = Field(None, description="Custom due date (overrides payment terms)")


class POInvoiceResponse(BaseModel):
    """PO Invoice response"""
    invoice_id: str = Field(..., description="Internal invoice ID")
    invoice_number: str = Field(..., description="Public invoice number (PO-####)")
    tenant_id: str = Field(..., description="Tenant/District ID")
    po_number: Optional[str] = Field(None, description="Customer PO number")
    status: POInvoiceStatus = Field(..., description="Invoice status")
    subtotal: Decimal = Field(..., description="Subtotal before tax")
    tax_total: Decimal = Field(..., description="Total tax amount")
    total: Decimal = Field(..., description="Total amount")
    payment_terms: PaymentTerms = Field(..., description="Payment terms")
    issue_date: datetime = Field(..., description="Invoice issue date")
    due_date: datetime = Field(..., description="Invoice due date")
    pdf_url: Optional[str] = Field(None, description="PDF download URL")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class POInvoiceListResponse(BaseModel):
    """List of PO invoices with pagination"""
    invoices: List[POInvoiceResponse] = Field(..., description="List of invoices")
    total_count: int = Field(..., description="Total number of invoices")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Page size")


class PaymentRequest(BaseModel):
    """Payment recording request"""
    invoice_id: str = Field(..., description="Invoice ID")
    payment_amount: Decimal = Field(..., description="Payment amount")
    payment_date: datetime = Field(..., description="Payment date")
    payment_method: str = Field(..., description="Payment method (check, wire, etc)")
    reference_number: Optional[str] = Field(None, description="Payment reference number")
    notes: Optional[str] = Field(None, description="Payment notes")


class DunningReminderRequest(BaseModel):
    """Dunning reminder request"""
    invoice_id: str = Field(..., description="Invoice ID")
    reminder_type: str = Field(..., description="Reminder type (gentle, firm, final)")
    custom_message: Optional[str] = Field(None, description="Custom reminder message")


# Mock data store (in real implementation, this would be a database)
_invoice_store: Dict[str, Dict[str, Any]] = {}
_invoice_counter = 1000


def _generate_invoice_number() -> str:
    """Generate PO invoice number"""
    global _invoice_counter
    _invoice_counter += 1
    return f"PO-{_invoice_counter}"


def _calculate_due_date(issue_date: datetime, payment_terms: PaymentTerms) -> datetime:
    """Calculate due date based on payment terms"""
    days_map = {
        PaymentTerms.NET_15: 15,
        PaymentTerms.NET_30: 30,
        PaymentTerms.NET_60: 60,
        PaymentTerms.NET_90: 90,
    }
    return issue_date + timedelta(days=days_map[payment_terms])


def _calculate_totals(line_items: List[InvoiceLineItem]) -> tuple:
    """Calculate invoice totals"""
    subtotal = sum(item.total_price for item in line_items)
    tax_total = sum(item.tax_amount or Decimal('0') for item in line_items)
    total = subtotal + tax_total
    return subtotal, tax_total, total


async def _generate_pdf_invoice(invoice_data: Dict[str, Any]) -> str:
    """
    Generate PDF invoice (mock implementation)
    In real implementation, this would use a PDF generation library
    """
    # Mock PDF generation
    pdf_filename = f"invoice_{invoice_data['invoice_number']}.pdf"
    pdf_url = f"https://billing.aivo.com/invoices/{pdf_filename}"
    
    logger.info("PDF invoice generated",
               invoice_id=invoice_data['invoice_id'],
               invoice_number=invoice_data['invoice_number'],
               pdf_url=pdf_url)
    
    return pdf_url


async def _send_invoice_email(invoice_data: Dict[str, Any], pdf_url: str):
    """
    Send invoice email to billing contact
    """
    billing_contact = invoice_data['billing_contact']
    
    # Mock email sending
    logger.info("Invoice email sent",
               invoice_id=invoice_data['invoice_id'], 
               invoice_number=invoice_data['invoice_number'],
               recipient=billing_contact['email'])


async def _send_dunning_reminder(invoice_data: Dict[str, Any], reminder_type: str):
    """
    Send dunning reminder email
    """
    billing_contact = invoice_data['billing_contact']
    
    # Mock dunning email
    logger.info("Dunning reminder sent",
               invoice_id=invoice_data['invoice_id'],
               invoice_number=invoice_data['invoice_number'],
               reminder_type=reminder_type,
               recipient=billing_contact['email'])


# API Endpoints

@router.post(
    "/invoices",
    response_model=POInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create PO Invoice",
    description="Create a new Purchase Order invoice for district/enterprise billing"
)
async def create_po_invoice(
    request: POInvoiceRequest,
    background_tasks: BackgroundTasks
) -> POInvoiceResponse:
    """Create a new PO invoice for Net-30 billing"""
    
    try:
        # Generate invoice identifiers
        invoice_id = str(uuid.uuid4())
        invoice_number = _generate_invoice_number()
        
        # Calculate dates
        issue_date = datetime.utcnow()
        due_date = request.due_date or _calculate_due_date(issue_date, request.payment_terms)
        
        # Calculate totals
        subtotal, tax_total, total = _calculate_totals(request.line_items)
        
        # Create invoice record
        invoice_data = {
            "invoice_id": invoice_id,
            "invoice_number": invoice_number,
            "tenant_id": request.tenant_id,
            "po_number": request.po_number,
            "status": POInvoiceStatus.DRAFT,
            "billing_contact": request.billing_contact.dict(),
            "billing_address": request.billing_address,
            "line_items": [item.dict() for item in request.line_items],
            "payment_terms": request.payment_terms,
            "notes": request.notes,
            "subtotal": subtotal,
            "tax_total": tax_total,
            "total": total,
            "issue_date": issue_date,
            "due_date": due_date,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "payments": []
        }
        
        # Store invoice (in real implementation, save to database)
        _invoice_store[invoice_id] = invoice_data
        
        # Generate PDF and send email in background
        background_tasks.add_task(_generate_and_send_invoice, invoice_id)
        
        logger.info("PO invoice created",
                   invoice_id=invoice_id,
                   invoice_number=invoice_number,
                   tenant_id=request.tenant_id,
                   total=float(total))
        
        return POInvoiceResponse(**invoice_data)
        
    except Exception as e:
        logger.error("Failed to create PO invoice", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create PO invoice"
        )


async def _generate_and_send_invoice(invoice_id: str):
    """Background task to generate PDF and send invoice"""
    try:
        invoice_data = _invoice_store.get(invoice_id)
        if not invoice_data:
            logger.error("Invoice not found for PDF generation", invoice_id=invoice_id)
            return
        
        # Generate PDF
        pdf_url = await _generate_pdf_invoice(invoice_data)
        
        # Update invoice with PDF URL and status
        invoice_data["pdf_url"] = pdf_url
        invoice_data["status"] = POInvoiceStatus.SENT
        invoice_data["updated_at"] = datetime.utcnow()
        
        # Send email
        await _send_invoice_email(invoice_data, pdf_url)
        
        logger.info("Invoice PDF generated and sent",
                   invoice_id=invoice_id,
                   invoice_number=invoice_data["invoice_number"])
        
    except Exception as e:
        logger.error("Failed to generate and send invoice", 
                    invoice_id=invoice_id, error=str(e))


@router.get(
    "/invoices/{invoice_id}",
    response_model=POInvoiceResponse,
    summary="Get PO Invoice",
    description="Get PO invoice details by ID"
)
async def get_po_invoice(invoice_id: str) -> POInvoiceResponse:
    """Get PO invoice by ID"""
    
    invoice_data = _invoice_store.get(invoice_id)
    if not invoice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    return POInvoiceResponse(**invoice_data)


@router.get(
    "/invoices",
    response_model=POInvoiceListResponse,
    summary="List PO Invoices",
    description="List PO invoices with filtering and pagination"
)
async def list_po_invoices(
    tenant_id: Optional[str] = None,
    status: Optional[POInvoiceStatus] = None,
    page: int = 1,
    page_size: int = 20
) -> POInvoiceListResponse:
    """List PO invoices with optional filtering"""
    
    # Filter invoices
    filtered_invoices = []
    for invoice_data in _invoice_store.values():
        if tenant_id and invoice_data["tenant_id"] != tenant_id:
            continue
        if status and invoice_data["status"] != status:
            continue
        filtered_invoices.append(invoice_data)
    
    # Sort by creation date (newest first)
    filtered_invoices.sort(key=lambda x: x["created_at"], reverse=True)
    
    # Paginate
    start = (page - 1) * page_size
    end = start + page_size
    page_invoices = filtered_invoices[start:end]
    
    invoices = [POInvoiceResponse(**invoice) for invoice in page_invoices]
    
    return POInvoiceListResponse(
        invoices=invoices,
        total_count=len(filtered_invoices),
        page=page,
        page_size=page_size
    )


@router.post(
    "/invoices/{invoice_id}/payment",
    summary="Record Payment",
    description="Record payment for PO invoice"
)
async def record_payment(
    invoice_id: str,
    request: PaymentRequest
) -> Dict[str, Any]:
    """Record payment for PO invoice"""
    
    invoice_data = _invoice_store.get(invoice_id)
    if not invoice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Add payment record
    payment_record = {
        "payment_amount": request.payment_amount,
        "payment_date": request.payment_date,
        "payment_method": request.payment_method,
        "reference_number": request.reference_number,
        "notes": request.notes,
        "recorded_at": datetime.utcnow()
    }
    
    invoice_data["payments"].append(payment_record)
    
    # Calculate total payments
    total_payments = sum(p["payment_amount"] for p in invoice_data["payments"])
    
    # Update invoice status
    if total_payments >= invoice_data["total"]:
        invoice_data["status"] = POInvoiceStatus.PAID
    
    invoice_data["updated_at"] = datetime.utcnow()
    
    logger.info("Payment recorded",
               invoice_id=invoice_id,
               invoice_number=invoice_data["invoice_number"],
               payment_amount=float(request.payment_amount),
               total_payments=float(total_payments))
    
    return {
        "message": "Payment recorded successfully",
        "payment_amount": request.payment_amount,
        "total_payments": total_payments,
        "remaining_balance": invoice_data["total"] - total_payments,
        "status": invoice_data["status"]
    }


@router.post(
    "/invoices/{invoice_id}/dunning",
    summary="Send Dunning Reminder",
    description="Send dunning reminder for overdue invoice"
)
async def send_dunning_reminder(
    invoice_id: str,
    request: DunningReminderRequest,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """Send dunning reminder for overdue invoice"""
    
    invoice_data = _invoice_store.get(invoice_id)
    if not invoice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    
    # Check if invoice is overdue
    if datetime.utcnow() <= invoice_data["due_date"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice is not yet overdue"
        )
    
    # Send reminder in background
    background_tasks.add_task(
        _send_dunning_reminder,
        invoice_data,
        request.reminder_type
    )
    
    logger.info("Dunning reminder scheduled",
               invoice_id=invoice_id,
               invoice_number=invoice_data["invoice_number"],
               reminder_type=request.reminder_type)
    
    return {
        "message": "Dunning reminder scheduled",
        "invoice_number": invoice_data["invoice_number"],
        "reminder_type": request.reminder_type
    }


@router.get(
    "/invoices/overdue",
    response_model=POInvoiceListResponse,
    summary="Get Overdue Invoices",
    description="Get list of overdue invoices for dunning process"
)
async def get_overdue_invoices(
    days_overdue: Optional[int] = None
) -> POInvoiceListResponse:
    """Get overdue invoices for dunning process"""
    
    current_time = datetime.utcnow()
    overdue_invoices = []
    
    for invoice_data in _invoice_store.values():
        # Skip if already paid or cancelled
        if invoice_data["status"] in [POInvoiceStatus.PAID, POInvoiceStatus.CANCELLED]:
            continue
            
        # Check if overdue
        if current_time > invoice_data["due_date"]:
            # Calculate days overdue
            days_past_due = (current_time - invoice_data["due_date"]).days
            
            # Filter by days overdue if specified
            if days_overdue is None or days_past_due >= days_overdue:
                # Update status to overdue
                invoice_data["status"] = POInvoiceStatus.OVERDUE
                invoice_data["days_overdue"] = days_past_due
                overdue_invoices.append(invoice_data)
    
    # Sort by days overdue (most overdue first)
    overdue_invoices.sort(key=lambda x: x.get("days_overdue", 0), reverse=True)
    
    invoices = [POInvoiceResponse(**invoice) for invoice in overdue_invoices]
    
    return POInvoiceListResponse(
        invoices=invoices,
        total_count=len(overdue_invoices),
        page=1,
        page_size=len(overdue_invoices)
    )


@router.get(
    "/export/csv",
    summary="Export Invoices CSV",
    description="Export invoices to CSV for accounting"
)
async def export_invoices_csv(
    tenant_id: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> Dict[str, Any]:
    """Export invoices to CSV for accounting integration"""
    
    # Filter invoices by criteria
    filtered_invoices = []
    for invoice_data in _invoice_store.values():
        if tenant_id and invoice_data["tenant_id"] != tenant_id:
            continue
        if start_date and invoice_data["issue_date"] < start_date:
            continue
        if end_date and invoice_data["issue_date"] > end_date:
            continue
        filtered_invoices.append(invoice_data)
    
    # In real implementation, generate actual CSV file
    csv_data = []
    for invoice in filtered_invoices:
        csv_data.append({
            "invoice_number": invoice["invoice_number"],
            "tenant_id": invoice["tenant_id"],
            "po_number": invoice.get("po_number", ""),
            "status": invoice["status"],
            "issue_date": invoice["issue_date"].strftime("%Y-%m-%d"),
            "due_date": invoice["due_date"].strftime("%Y-%m-%d"),
            "subtotal": float(invoice["subtotal"]),
            "tax_total": float(invoice["tax_total"]),
            "total": float(invoice["total"]),
            "payments": len(invoice.get("payments", [])),
            "payment_terms": invoice["payment_terms"]
        })
    
    logger.info("Invoice CSV export requested",
               tenant_id=tenant_id,
               invoice_count=len(csv_data))
    
    return {
        "message": "CSV export generated",
        "invoice_count": len(csv_data),
        "csv_data": csv_data,  # In real implementation, return download URL
        "export_date": datetime.utcnow()
    }
