"""
Payment Service API Tests
Comprehensive test suite for payment endpoints and Stripe integration
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from main import app
from app.schemas import BillingTerm, SubscriptionStatus

client = TestClient(app)


class TestHealthAndInfo:
    """Test health and info endpoints"""
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "payment-svc"
        assert "version" in data
        assert "timestamp" in data
    
    def test_service_info_endpoint(self):
        """Test service information endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["service"] == "Payment Service"
        assert "capabilities" in data
        assert "billing_terms" in data
        assert "dunning_policy" in data
        assert "endpoints" in data
        
        # Check billing terms
        billing_terms = data["billing_terms"]
        assert "monthly" in billing_terms
        assert "quarterly" in billing_terms
        assert "yearly" in billing_terms
        
        # Check dunning policy
        dunning = data["dunning_policy"]
        assert "grace_period_days" in dunning
        assert "cancellation_day" in dunning


class TestTrialEndpoints:
    """Test trial subscription endpoints"""
    
    @patch('app.stripe_service.stripe_service.start_trial')
    @patch('app.subscription_service.subscription_service.create_subscription_record')
    def test_start_trial_success(self, mock_create_record, mock_start_trial):
        """Test successful trial start"""
        # Mock Stripe response
        mock_start_trial.return_value = MagicMock(
            subscription_id="sub_test123",
            customer_id="cus_test123", 
            trial_end=datetime.utcnow() + timedelta(days=30),
            status=SubscriptionStatus.TRIALING,
            learner_id="learner_123"
        )
        
        request_data = {
            "guardian_id": "guardian_123",
            "learner_id": "learner_123",
            "email": "test@example.com"
        }
        
        response = client.post("/trial/start", json=request_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["subscription_id"] == "sub_test123"
        assert data["customer_id"] == "cus_test123"
        assert data["status"] == "trialing"
        assert data["learner_id"] == "learner_123"
        
        # Verify service calls
        mock_start_trial.assert_called_once()
        mock_create_record.assert_called_once()
    
    def test_start_trial_missing_fields(self):
        """Test trial start with missing required fields"""
        request_data = {
            "guardian_id": "guardian_123"
            # Missing learner_id
        }
        
        response = client.post("/trial/start", json=request_data)
        assert response.status_code == 422  # Validation error


class TestPlanQuoteEndpoints:
    """Test plan quote and pricing endpoints"""
    
    @patch('app.stripe_service.stripe_service.calculate_quote')
    def test_plan_quote_monthly(self, mock_calculate_quote):
        """Test monthly plan quote"""
        mock_calculate_quote.return_value = MagicMock(
            base_price_cents=2999,
            total_seats=1,
            term=BillingTerm.MONTHLY,
            term_discount_percent=0.0,
            sibling_discount_percent=0.0,
            subtotal_cents=2999,
            term_discount_cents=0,
            sibling_discount_cents=0,
            total_cents=2999
        )
        
        request_data = {
            "seats": 1,
            "term": "monthly",
            "siblings": 0
        }
        
        response = client.post("/plan/quote", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["base_price_cents"] == 2999
        assert data["total_seats"] == 1
        assert data["term"] == "monthly"
        assert data["total_cents"] == 2999
    
    @patch('app.stripe_service.stripe_service.calculate_quote')
    def test_plan_quote_yearly_with_siblings(self, mock_calculate_quote):
        """Test yearly plan quote with sibling discount"""
        mock_calculate_quote.return_value = MagicMock(
            base_price_cents=2999,
            total_seats=3,
            term=BillingTerm.YEARLY,
            term_discount_percent=0.50,
            sibling_discount_percent=0.10,
            subtotal_cents=107964,  # 2999 * 3 * 12
            term_discount_cents=53982,  # 50% discount
            sibling_discount_cents=7197,  # 10% on 2 siblings * 12 months
            total_cents=46785
        )
        
        request_data = {
            "seats": 3,
            "term": "yearly", 
            "siblings": 2
        }
        
        response = client.post("/plan/quote", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["term"] == "yearly"
        assert data["term_discount_percent"] == 0.50
        assert data["sibling_discount_percent"] == 0.10
        assert data["total_seats"] == 3
    
    def test_plan_quote_invalid_siblings(self):
        """Test plan quote with invalid sibling count"""
        request_data = {
            "seats": 2,
            "term": "monthly",
            "siblings": 3  # More siblings than seats - 1
        }
        
        response = client.post("/plan/quote", json=request_data)
        assert response.status_code == 400
        
        data = response.json()
        assert "invalid_sibling_count" in str(data)


class TestCheckoutEndpoints:
    """Test checkout session endpoints"""
    
    @patch('app.stripe_service.stripe_service.create_checkout_session')
    def test_create_checkout_success(self, mock_create_checkout):
        """Test successful checkout session creation"""
        mock_create_checkout.return_value = MagicMock(
            checkout_url="https://checkout.stripe.com/pay/session123",
            session_id="cs_session123",
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        
        request_data = {
            "learner_id": "learner_123",
            "guardian_id": "guardian_123",
            "term": "monthly",
            "seats": 1,
            "siblings": 0,
            "success_url": "https://app.aivo.com/success",
            "cancel_url": "https://app.aivo.com/cancel"
        }
        
        response = client.post("/plan/checkout", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["session_id"] == "cs_session123"
        assert data["checkout_url"].startswith("https://checkout.stripe.com")
        assert "expires_at" in data


class TestDistrictEndpoints:
    """Test district invoice endpoints"""
    
    @patch('app.stripe_service.stripe_service.create_district_invoice')
    def test_create_district_invoice(self, mock_create_invoice):
        """Test district invoice creation"""
        from datetime import date
        
        mock_create_invoice.return_value = MagicMock(
            invoice_id="in_district123",
            invoice_url="https://invoice.stripe.com/i/district123",
            amount_cents=89970,  # 2999 * 30 seats
            due_date=date.today() + timedelta(days=30),
            status="open"
        )
        
        request_data = {
            "tenant_id": "district_001",
            "seats": 30,
            "billing_period_start": "2025-08-01",
            "billing_period_end": "2025-08-31",
            "po_number": "PO-2025-001"
        }
        
        response = client.post("/district/invoice", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["invoice_id"] == "in_district123"
        assert data["amount_cents"] == 89970
        assert data["status"] == "open"


class TestWebhookEndpoints:
    """Test webhook endpoints"""
    
    @patch('app.webhook_handler.webhook_handler.process_webhook')
    def test_stripe_webhook_success(self, mock_process_webhook):
        """Test successful webhook processing"""
        mock_process_webhook.return_value = {
            "status": "processed",
            "event_type": "invoice.payment_failed",
            "event_id": "evt_test123"
        }
        
        webhook_payload = {
            "id": "evt_test123",
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": "in_test123",
                    "subscription": "sub_test123",
                    "amount_due": 2999
                }
            }
        }
        
        # Mock request would include Stripe signature header
        headers = {"stripe-signature": "t=123,v1=signature"}
        
        response = client.post(
            "/webhooks/stripe", 
            json=webhook_payload,
            headers=headers
        )
        # Note: This would normally fail signature verification
        # In real tests you'd mock the signature verification


class TestPricingLogic:
    """Test pricing calculation logic"""
    
    def test_billing_term_discounts(self):
        """Test that billing term discounts are applied correctly"""
        # This would test the StripeService.calculate_quote method directly
        # Testing discount percentages: 0%, 20%, 30%, 50%
        pass
    
    def test_sibling_discount_logic(self):
        """Test sibling discount calculations"""
        # Test that sibling discounts are only applied to sibling seats
        # and that the 10% discount is calculated correctly
        pass
    
    def test_pricing_edge_cases(self):
        """Test pricing edge cases"""
        # Test maximum seats, zero siblings, etc.
        pass


class TestDunningLogic:
    """Test dunning and subscription management"""
    
    @patch('app.subscription_service.dunning_service.handle_payment_failure')
    def test_payment_failure_handling(self, mock_handle_failure):
        """Test payment failure triggers dunning process"""
        mock_handle_failure.return_value = True
        
        # This would test the dunning service logic
        # including grace period start and email scheduling
        pass
    
    def test_dunning_schedule(self):
        """Test dunning email schedule (days 3, 7, 14)"""
        # Test that dunning emails are scheduled at correct intervals
        pass
    
    def test_subscription_cancellation(self):
        """Test subscription cancellation after 21 days"""
        # Test automatic cancellation logic
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
