"""
Tests for tax calculation and PO invoicing functionality
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.tax.stripe_tax import TaxCalculator, TaxableItem, BillingAddress
from app.tax.validators import TaxIDValidator, BillingAddressValidator
from app.routes.po_invoices import POInvoiceStatus, PaymentTerms

client = TestClient(app)


class TestTaxCalculation:
    """Test tax calculation functionality"""
    
    def test_tax_id_validation_us_ein(self):
        """Test US EIN validation"""
        # Valid EIN
        valid, tax_type = TaxIDValidator.validate_format("12-3456789", "US")
        assert valid is True
        assert tax_type == "us_ein"
        
        # Invalid EIN
        valid, tax_type = TaxIDValidator.validate_format("12-34567", "US") 
        assert valid is False
        assert tax_type is None
    
    def test_tax_id_validation_eu_vat(self):
        """Test EU VAT validation"""
        # Valid German VAT
        valid, tax_type = TaxIDValidator.validate_format("DE123456789", "DE")
        assert valid is True
        assert tax_type == "eu_vat"
        
        # Invalid format
        valid, tax_type = TaxIDValidator.validate_format("DE123", "DE")
        assert valid is False
    
    def test_billing_address_validation_us(self):
        """Test US billing address validation"""
        address_data = {
            "line1": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105",
            "country": "US"
        }
        
        valid, errors = BillingAddressValidator.validate_address(address_data)
        assert valid is True
        assert len(errors) == 0
    
    def test_billing_address_validation_missing_state(self):
        """Test US address validation with missing state"""
        address_data = {
            "line1": "123 Main St",
            "city": "San Francisco", 
            "postal_code": "94105",
            "country": "US"
        }
        
        valid, errors = BillingAddressValidator.validate_address(address_data)
        assert valid is False
        assert "State/Province is required for US" in errors
    
    def test_postal_code_validation(self):
        """Test postal code validation for different countries"""
        # US ZIP code
        assert BillingAddressValidator.validate_postal_code("94105", "US") is True
        assert BillingAddressValidator.validate_postal_code("94105-1234", "US") is True
        assert BillingAddressValidator.validate_postal_code("9410", "US") is False
        
        # Canadian postal code
        assert BillingAddressValidator.validate_postal_code("A1A 1A1", "CA") is True
        assert BillingAddressValidator.validate_postal_code("A1A1A1", "CA") is False
        
        # UK postcode
        assert BillingAddressValidator.validate_postal_code("SW1A 1AA", "GB") is True
        assert BillingAddressValidator.validate_postal_code("SW1A1AA", "GB") is False
    
    @pytest.mark.asyncio
    @patch('app.tax.stripe_tax.stripe')
    async def test_tax_calculation_with_stripe(self, mock_stripe):
        """Test tax calculation using Stripe Tax API"""
        # Mock Stripe response
        mock_calculation = Mock()
        mock_calculation.id = "taxcalc_123"
        mock_calculation.amount_total = 11000  # $110.00
        mock_calculation.tax_amount_exclusive = 1000  # $10.00 tax
        mock_calculation.tax_breakdown = [
            Mock(
                tax_rate_details=Mock(
                    tax_type="sales_tax",
                    percentage_decimal=0.1
                ),
                tax_amount=1000,
                jurisdiction=Mock(display_name="California")
            )
        ]
        mock_stripe.tax.Calculation.create.return_value = mock_calculation
        
        calculator = TaxCalculator()
        
        items = [
            TaxableItem(amount=Decimal('100.00'), reference="subscription", tax_code="txcd_10000000")
        ]
        
        billing_address = BillingAddress(
            line1="123 Main St",
            city="San Francisco",
            state="CA", 
            postal_code="94105",
            country="US"
        )
        
        result = await calculator.calculate_tax(items, billing_address)
        
        assert result.subtotal == Decimal('110.00')
        assert result.total_tax == Decimal('10.00')
        assert result.total == Decimal('120.00')
        assert len(result.tax_lines) == 1
        assert result.tax_lines[0].tax_type == "sales_tax"
        assert result.tax_lines[0].rate == Decimal('0.1')
    
    def test_tax_api_validate_tax_id(self):
        """Test tax ID validation API endpoint"""
        response = client.post("/tax/validate-id", json={
            "tax_id": "12-3456789",
            "country": "US"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["tax_id_type"] == "us_ein"
        assert "requirements" in data
    
    def test_tax_api_validate_address(self):
        """Test address validation API endpoint"""
        response = client.post("/tax/validate-address", json={
            "line1": "123 Main St",
            "city": "San Francisco",
            "state": "CA",
            "postal_code": "94105", 
            "country": "US"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert len(data["errors"]) == 0
    
    def test_tax_api_calculate_tax(self):
        """Test tax calculation API endpoint"""
        with patch('app.tax.stripe_tax.tax_calculator.calculate_tax') as mock_calc:
            # Mock calculation result
            from app.tax.stripe_tax import TaxCalculationResult, TaxLineItem
            mock_calc.return_value = TaxCalculationResult(
                subtotal=Decimal('100.00'),
                total_tax=Decimal('8.50'),
                total=Decimal('108.50'),
                tax_lines=[
                    TaxLineItem(
                        tax_type="sales_tax",
                        rate=Decimal('0.085'),
                        amount=Decimal('8.50'),
                        jurisdiction="California"
                    )
                ],
                currency="usd",
                tax_calculation_id="taxcalc_123"
            )
            
            response = client.post("/tax/calculate", json={
                "items": [
                    {
                        "amount": 100.00,
                        "description": "Monthly subscription",
                        "reference": "sub_123",
                        "tax_code": "txcd_10000000"
                    }
                ],
                "billing_address": {
                    "line1": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "postal_code": "94105",
                    "country": "US"
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["subtotal"] == 100.00
            assert data["total_tax"] == 8.50
            assert data["total"] == 108.50
            assert len(data["tax_lines"]) == 1


class TestPOInvoicing:
    """Test PO invoicing functionality"""
    
    def test_create_po_invoice(self):
        """Test creating a PO invoice"""
        invoice_data = {
            "tenant_id": "district_123",
            "po_number": "PO-2025-001",
            "billing_contact": {
                "name": "John Smith",
                "email": "billing@district.edu",
                "phone": "(555) 123-4567",
                "title": "Finance Director"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City",
                "state": "CA",
                "postal_code": "94105",
                "country": "US"
            },
            "line_items": [
                {
                    "description": "AIVO Platform Subscription - 100 students",
                    "quantity": 1,
                    "unit_price": 5000.00,
                    "total_price": 5000.00,
                    "tax_rate": 0.0875,
                    "tax_amount": 437.50
                }
            ],
            "payment_terms": "net_30",
            "notes": "Annual subscription for 2025-2026 school year"
        }
        
        response = client.post("/po/invoices", json=invoice_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["tenant_id"] == "district_123"
        assert data["po_number"] == "PO-2025-001"
        assert data["status"] == "draft"
        assert data["subtotal"] == 5000.00
        assert data["tax_total"] == 437.50
        assert data["total"] == 5437.50
        assert data["payment_terms"] == "net_30"
        assert data["invoice_number"].startswith("PO-")
        
        # Verify due date is 30 days from issue date
        issue_date = datetime.fromisoformat(data["issue_date"])
        due_date = datetime.fromisoformat(data["due_date"])
        assert (due_date - issue_date).days == 30
    
    def test_get_po_invoice(self):
        """Test retrieving a PO invoice"""
        # Create invoice first
        invoice_data = {
            "tenant_id": "district_123",
            "billing_contact": {
                "name": "John Smith", 
                "email": "billing@district.edu"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City",
                "state": "CA",
                "postal_code": "94105",
                "country": "US"
            },
            "line_items": [
                {
                    "description": "Test item",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "total_price": 100.00
                }
            ]
        }
        
        create_response = client.post("/po/invoices", json=invoice_data)
        invoice_id = create_response.json()["invoice_id"]
        
        # Get invoice
        response = client.get(f"/po/invoices/{invoice_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["invoice_id"] == invoice_id
        assert data["tenant_id"] == "district_123"
    
    def test_list_po_invoices(self):
        """Test listing PO invoices with filtering"""
        response = client.get("/po/invoices?tenant_id=district_123&page=1&page_size=10")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "invoices" in data
        assert "total_count" in data
        assert data["page"] == 1
        assert data["page_size"] == 10
    
    def test_record_payment(self):
        """Test recording payment for invoice"""
        # Create invoice first
        invoice_data = {
            "tenant_id": "district_123",
            "billing_contact": {
                "name": "John Smith",
                "email": "billing@district.edu"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City", 
                "state": "CA",
                "postal_code": "94105",
                "country": "US"
            },
            "line_items": [
                {
                    "description": "Test subscription",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "total_price": 1000.00
                }
            ]
        }
        
        create_response = client.post("/po/invoices", json=invoice_data)
        invoice_id = create_response.json()["invoice_id"]
        
        # Record payment
        payment_data = {
            "invoice_id": invoice_id,
            "payment_amount": 1000.00,
            "payment_date": datetime.utcnow().isoformat(),
            "payment_method": "check",
            "reference_number": "CHK-001"
        }
        
        response = client.post(f"/po/invoices/{invoice_id}/payment", json=payment_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["payment_amount"] == 1000.00
        assert data["total_payments"] == 1000.00
        assert data["remaining_balance"] == 0.00
        assert data["status"] == "paid"
    
    def test_partial_payment(self):
        """Test partial payment recording"""
        # Create invoice first
        invoice_data = {
            "tenant_id": "district_123", 
            "billing_contact": {
                "name": "John Smith",
                "email": "billing@district.edu"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City",
                "state": "CA", 
                "postal_code": "94105",
                "country": "US"
            },
            "line_items": [
                {
                    "description": "Test subscription",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "total_price": 1000.00
                }
            ]
        }
        
        create_response = client.post("/po/invoices", json=invoice_data)
        invoice_id = create_response.json()["invoice_id"]
        
        # Record partial payment
        payment_data = {
            "invoice_id": invoice_id,
            "payment_amount": 500.00,
            "payment_date": datetime.utcnow().isoformat(),
            "payment_method": "check",
            "reference_number": "CHK-001"
        }
        
        response = client.post(f"/po/invoices/{invoice_id}/payment", json=payment_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["payment_amount"] == 500.00
        assert data["total_payments"] == 500.00
        assert data["remaining_balance"] == 500.00
        assert data["status"] != "paid"  # Should not be paid yet
    
    def test_get_overdue_invoices(self):
        """Test getting overdue invoices"""
        response = client.get("/po/invoices/overdue?days_overdue=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "invoices" in data
        assert "total_count" in data
    
    def test_send_dunning_reminder(self):
        """Test sending dunning reminder"""
        # Create overdue invoice (would need to mock date/time)
        invoice_data = {
            "tenant_id": "district_123",
            "billing_contact": {
                "name": "John Smith",
                "email": "billing@district.edu"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City",
                "state": "CA",
                "postal_code": "94105", 
                "country": "US"
            },
            "line_items": [
                {
                    "description": "Test subscription",
                    "quantity": 1,
                    "unit_price": 1000.00,
                    "total_price": 1000.00
                }
            ],
            "due_date": (datetime.utcnow() - timedelta(days=5)).isoformat()
        }
        
        create_response = client.post("/po/invoices", json=invoice_data)
        invoice_id = create_response.json()["invoice_id"]
        
        # Send dunning reminder
        reminder_data = {
            "invoice_id": invoice_id,
            "reminder_type": "gentle",
            "custom_message": "Please remit payment at your earliest convenience"
        }
        
        response = client.post(f"/po/invoices/{invoice_id}/dunning", json=reminder_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert data["reminder_type"] == "gentle"
    
    def test_export_invoices_csv(self):
        """Test CSV export for accounting"""
        response = client.get("/po/export/csv?tenant_id=district_123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "message" in data
        assert "invoice_count" in data
        assert "csv_data" in data
        assert "export_date" in data
    
    def test_line_item_validation(self):
        """Test line item total validation"""
        invoice_data = {
            "tenant_id": "district_123",
            "billing_contact": {
                "name": "John Smith",
                "email": "billing@district.edu"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City",
                "state": "CA",
                "postal_code": "94105",
                "country": "US"
            },
            "line_items": [
                {
                    "description": "Test item",
                    "quantity": 2,
                    "unit_price": 100.00,
                    "total_price": 150.00  # Incorrect total
                }
            ]
        }
        
        response = client.post("/po/invoices", json=invoice_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_payment_terms_due_date_calculation(self):
        """Test due date calculation for different payment terms"""
        invoice_data = {
            "tenant_id": "district_123",
            "billing_contact": {
                "name": "John Smith",
                "email": "billing@district.edu"
            },
            "billing_address": {
                "line1": "123 School District Blvd",
                "city": "Education City",
                "state": "CA",
                "postal_code": "94105",
                "country": "US"
            },
            "line_items": [
                {
                    "description": "Test item",
                    "quantity": 1,
                    "unit_price": 100.00,
                    "total_price": 100.00
                }
            ],
            "payment_terms": "net_60"
        }
        
        response = client.post("/po/invoices", json=invoice_data)
        
        assert response.status_code == 201
        data = response.json()
        
        issue_date = datetime.fromisoformat(data["issue_date"])
        due_date = datetime.fromisoformat(data["due_date"])
        
        # Should be 60 days difference
        assert (due_date - issue_date).days == 60
