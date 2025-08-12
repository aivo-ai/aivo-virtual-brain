"""
Pact Contract Tests for Payment Service
Consumer-driven contract testing for external service integration
"""

import pytest
from pact import Consumer, Provider, Like, Term
from datetime import datetime, date
import requests

from app.schemas import BillingTerm, SubscriptionStatus


class TestPaymentServiceContracts:
    """Contract tests for payment service as consumer"""
    
    @pytest.fixture(scope="session") 
    def pact(self):
        """Pact configuration for contract testing"""
        return Consumer("payment-svc").has_pact_with(
            Provider("stripe-api"),
            host_name="localhost",
            port=1234,
            pact_dir="pacts"
        )
    
    def test_stripe_customer_creation(self, pact):
        """Test contract for Stripe customer creation"""
        expected_customer = {
            "id": Like("cus_test123"),
            "email": Like("test@example.com"),
            "metadata": {
                "guardian_id": Like("guardian_123"),
                "service": "aivo-payment-svc"
            },
            "created": Like(1692720000)
        }
        
        (pact
         .given("valid customer data")
         .upon_receiving("a customer creation request")
         .with_request(
             method="POST",
             path="/v1/customers",
             headers={"Authorization": Like("Bearer sk_test_...")},
             body={
                 "email": "test@example.com",
                 "metadata": {
                     "guardian_id": "guardian_123",
                     "service": "aivo-payment-svc"
                 }
             }
         )
         .will_respond_with(200, body=expected_customer))
        
        with pact:
            # Test the actual integration
            # This would call our StripeService.create_customer method
            pass
    
    def test_stripe_subscription_creation(self, pact):
        """Test contract for trial subscription creation"""
        expected_subscription = {
            "id": Like("sub_test123"),
            "customer": Like("cus_test123"),
            "status": "trialing",
            "trial_end": Like(1695312000),
            "current_period_start": Like(1692720000),
            "current_period_end": Like(1695312000),
            "metadata": {
                "guardian_id": Like("guardian_123"),
                "learner_id": Like("learner_123"),
                "type": "trial"
            }
        }
        
        (pact
         .given("valid customer exists")
         .upon_receiving("a trial subscription creation request")
         .with_request(
             method="POST",
             path="/v1/subscriptions",
             headers={"Authorization": Like("Bearer sk_test_...")},
             body={
                 "customer": Like("cus_test123"),
                 "items": Like([{
                     "price_data": {
                         "currency": "usd",
                         "product_data": {
                             "name": "AIVO Learning Platform"
                         },
                         "unit_amount": 2999,
                         "recurring": {"interval": "month"}
                     }
                 }]),
                 "trial_end": Like(1695312000),
                 "metadata": {
                     "guardian_id": "guardian_123",
                     "learner_id": "learner_123",
                     "type": "trial"
                 }
             }
         )
         .will_respond_with(200, body=expected_subscription))
        
        with pact:
            # Test the actual subscription creation
            pass
    
    def test_stripe_checkout_session_creation(self, pact):
        """Test contract for checkout session creation"""
        expected_session = {
            "id": Like("cs_test123"),
            "url": Like("https://checkout.stripe.com/pay/cs_test123"),
            "expires_at": Like(1692806400),
            "metadata": {
                "guardian_id": Like("guardian_123"),
                "learner_id": Like("learner_123"),
                "seats": Like("1"),
                "term": Like("monthly")
            }
        }
        
        (pact
         .given("valid checkout data")
         .upon_receiving("a checkout session creation request")
         .with_request(
             method="POST",
             path="/v1/checkout/sessions",
             headers={"Authorization": Like("Bearer sk_test_...")},
             body={
                 "payment_method_types": ["card"],
                 "line_items": Like([{
                     "price_data": {
                         "currency": "usd",
                         "product_data": {
                             "name": Like("AIVO Learning Platform - monthly (1 seats)")
                         },
                         "unit_amount": Like(2999),
                         "recurring": {
                             "interval": "month",
                             "interval_count": 1
                         }
                     },
                     "quantity": 1
                 }]),
                 "mode": "subscription",
                 "success_url": Like("https://app.aivo.com/success"),
                 "cancel_url": Like("https://app.aivo.com/cancel"),
                 "metadata": {
                     "guardian_id": "guardian_123",
                     "learner_id": "learner_123",
                     "seats": "1",
                     "siblings": "0",
                     "term": "monthly"
                 }
             }
         )
         .will_respond_with(200, body=expected_session))
        
        with pact:
            # Test checkout session creation
            pass
    
    def test_stripe_invoice_creation(self, pact):
        """Test contract for district invoice creation"""
        expected_invoice = {
            "id": Like("in_test123"),
            "customer": Like("cus_district123"),
            "amount_due": Like(89970),  # 2999 * 30 seats
            "currency": "usd",
            "status": "open",
            "hosted_invoice_url": Like("https://invoice.stripe.com/i/in_test123"),
            "metadata": {
                "tenant_id": Like("district_001"),
                "seats": Like("30")
            }
        }
        
        (pact
         .given("valid district customer")
         .upon_receiving("an invoice creation request")
         .with_request(
             method="POST",
             path="/v1/invoices",
             headers={"Authorization": Like("Bearer sk_test_...")},
             body={
                 "customer": Like("cus_district123"),
                 "auto_advance": False,
                 "collection_method": "send_invoice",
                 "days_until_due": 30,
                 "metadata": {
                     "tenant_id": "district_001",
                     "seats": "30"
                 }
             }
         )
         .will_respond_with(200, body=expected_invoice))
        
        with pact:
            # Test district invoice creation
            pass


class TestWebhookContracts:
    """Contract tests for webhook event processing"""
    
    @pytest.fixture(scope="session")
    def webhook_pact(self):
        """Pact for webhook events from Stripe"""
        return Consumer("payment-svc").has_pact_with(
            Provider("stripe-webhooks"),
            host_name="localhost",
            port=1235,
            pact_dir="pacts"
        )
    
    def test_payment_failed_webhook(self, webhook_pact):
        """Test contract for payment failed webhook"""
        payment_failed_event = {
            "id": Like("evt_test123"),
            "type": "invoice.payment_failed",
            "data": {
                "object": {
                    "id": Like("in_test123"),
                    "subscription": Like("sub_test123"),
                    "customer": Like("cus_test123"),
                    "amount_due": Like(2999),
                    "attempt_count": Like(1),
                    "last_payment_error": {
                        "message": Like("Your card was declined.")
                    }
                }
            },
            "created": Like(1692720000)
        }
        
        (webhook_pact
         .given("payment failure occurred")
         .upon_receiving("a payment failed webhook")
         .with_request(
             method="POST",
             path="/webhooks/stripe",
             headers={
                 "stripe-signature": Like("t=1692720000,v1=signature...")
             },
             body=payment_failed_event
         )
         .will_respond_with(200, body={
             "status": "processed",
             "event_type": "invoice.payment_failed"
         }))
        
        with webhook_pact:
            # Test webhook processing
            pass
    
    def test_subscription_updated_webhook(self, webhook_pact):
        """Test contract for subscription updated webhook"""
        subscription_updated_event = {
            "id": Like("evt_test456"),
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": Like("sub_test123"),
                    "customer": Like("cus_test123"),
                    "status": Like("active"),
                    "current_period_start": Like(1692720000),
                    "current_period_end": Like(1695398400),
                    "trial_end": None
                }
            },
            "created": Like(1692720000)
        }
        
        (webhook_pact
         .given("subscription status changed")
         .upon_receiving("a subscription updated webhook")
         .with_request(
             method="POST",
             path="/webhooks/stripe",
             headers={
                 "stripe-signature": Like("t=1692720000,v1=signature...")
             },
             body=subscription_updated_event
         )
         .will_respond_with(200, body={
             "status": "processed", 
             "event_type": "customer.subscription.updated"
         }))
        
        with webhook_pact:
            # Test webhook processing
            pass
    
    def test_checkout_completed_webhook(self, webhook_pact):
        """Test contract for checkout completed webhook"""
        checkout_completed_event = {
            "id": Like("evt_test789"),
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": Like("cs_test123"),
                    "customer": Like("cus_test123"),
                    "subscription": Like("sub_test123"),
                    "payment_status": "paid",
                    "amount_total": Like(2999),
                    "metadata": {
                        "guardian_id": Like("guardian_123"),
                        "learner_id": Like("learner_123")
                    }
                }
            },
            "created": Like(1692720000)
        }
        
        (webhook_pact
         .given("checkout session completed")
         .upon_receiving("a checkout completed webhook")
         .with_request(
             method="POST",
             path="/webhooks/stripe",
             headers={
                 "stripe-signature": Like("t=1692720000,v1=signature...")
             },
             body=checkout_completed_event
         )
         .will_respond_with(200, body={
             "status": "processed",
             "event_type": "checkout.session.completed"
         }))
        
        with webhook_pact:
            # Test webhook processing
            pass


class TestExternalServiceContracts:
    """Contract tests with other AIVO services"""
    
    @pytest.fixture(scope="session")
    def tenant_service_pact(self):
        """Pact with tenant service"""
        return Consumer("payment-svc").has_pact_with(
            Provider("tenant-svc"),
            host_name="localhost", 
            port=8002,
            pact_dir="pacts"
        )
    
    def test_tenant_seat_allocation(self, tenant_service_pact):
        """Test contract for tenant seat allocation"""
        expected_response = {
            "tenant_id": Like("district_001"),
            "seats_available": Like(100),
            "seats_allocated": Like(30),
            "status": "success"
        }
        
        (tenant_service_pact
         .given("district has available seats")
         .upon_receiving("a seat allocation request")
         .with_request(
             method="POST",
             path="/tenants/district_001/allocate",
             headers={"Content-Type": "application/json"},
             body={
                 "seats": 30,
                 "subscription_id": Like("sub_test123")
             }
         )
         .will_respond_with(200, body=expected_response))
        
        with tenant_service_pact:
            # Test tenant service integration
            pass
    
    @pytest.fixture(scope="session") 
    def user_service_pact(self):
        """Pact with user service"""
        return Consumer("payment-svc").has_pact_with(
            Provider("user-svc"),
            host_name="localhost",
            port=8001,
            pact_dir="pacts"
        )
    
    def test_user_subscription_update(self, user_service_pact):
        """Test contract for user subscription updates"""
        expected_response = {
            "user_id": Like("guardian_123"),
            "subscription_status": Like("active"),
            "access_level": Like("premium"),
            "updated_at": Like("2025-08-12T10:00:00Z")
        }
        
        (user_service_pact
         .given("user exists and subscription is active")
         .upon_receiving("a subscription status update")
         .with_request(
             method="PUT",
             path="/users/guardian_123/subscription",
             headers={"Content-Type": "application/json"},
             body={
                 "subscription_id": Like("sub_test123"),
                 "status": "active",
                 "billing_term": "monthly"
             }
         )
         .will_respond_with(200, body=expected_response))
        
        with user_service_pact:
            # Test user service integration
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
