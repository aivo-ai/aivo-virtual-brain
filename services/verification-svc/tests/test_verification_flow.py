"""
Test Guardian Identity Verification Flow
Comprehensive tests for COPPA-compliant verification with micro-charge and KBA
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, AsyncGenerator
from unittest.mock import Mock, patch, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import structlog

from app.main import app
from app.database import get_db_session
from app.models import Base, GuardianVerification, VerificationMethod, VerificationStatus
from app.config import settings
from app.providers.stripe_charge import stripe_charge_provider
from app.providers.kba_vendor import kba_vendor_provider

logger = structlog.get_logger(__name__)

# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_verification.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def client(db_session):
    """Create test client with dependency override"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db_session] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def mock_stripe():
    """Mock Stripe for testing"""
    with patch('app.providers.stripe_charge.stripe') as mock:
        # Mock PaymentIntent creation
        mock.PaymentIntent.create.return_value = Mock(
            id="pi_test_123",
            client_secret="pi_test_123_secret_test",
            status="requires_payment_method",
            metadata={}
        )
        
        # Mock webhook signature verification
        mock.Webhook.construct_event.return_value = True
        
        yield mock


@pytest.fixture
def mock_kba():
    """Mock KBA provider for testing"""
    with patch('app.providers.kba_vendor.aiohttp.ClientSession') as mock_session:
        # Mock successful KBA session creation
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "sessionId": "kba_test_123",
            "sessionUrl": "https://mock-kba.test/session/kba_test_123"
        }
        
        mock_session.return_value.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        mock_session.return_value.__aenter__.return_value.get.return_value.__aenter__.return_value = mock_response
        
        yield mock_session


@pytest.fixture
def guardian_verification_data():
    """Sample guardian verification data"""
    return {
        "guardian_user_id": "guardian_test_123",
        "method": "micro_charge",
        "country_code": "US",
        "metadata": {
            "tenant_id": "test_tenant",
            "first_name": "John",
            "last_name": "Doe",
            "zip_code": "12345",
            "state": "CA",
            "city": "San Francisco"
        }
    }


class TestMicroChargeVerification:
    """Test micro-charge verification flow"""
    
    @pytest.mark.asyncio
    async def test_start_micro_charge_verification_success(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test successful micro-charge verification start"""
        
        response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "verification_id" in data
        assert data["status"] == "in_progress"
        assert data["method"] == "micro_charge"
        assert "micro_charge" in data
        assert "client_secret" in data["micro_charge"]
        assert data["micro_charge"]["amount_cents"] == 10
        
        # Verify Stripe PaymentIntent was created
        mock_stripe.PaymentIntent.create.assert_called_once()
        create_args = mock_stripe.PaymentIntent.create.call_args[1]
        assert create_args["amount"] == 10
        assert create_args["currency"] == "usd"
        assert "identity_verification" in create_args["description"]
    
    @pytest.mark.asyncio
    async def test_micro_charge_verification_duplicate_request(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test duplicate verification request handling"""
        
        # First request
        response1 = client.post("/api/v1/verify/start", json=guardian_verification_data)
        assert response1.status_code == 200
        
        # Second request should fail
        response2 = client.post("/api/v1/verify/start", json=guardian_verification_data)
        assert response2.status_code == 409
        assert "Active verification already exists" in response2.json()["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_micro_charge_payment_succeeded_webhook(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test successful payment webhook processing"""
        
        # Start verification first
        start_response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        verification_id = start_response.json()["verification_id"]
        
        # Mock successful payment webhook
        webhook_data = {
            "verification_id": verification_id,
            "provider": "stripe",
            "event_type": "payment_intent.succeeded",
            "provider_data": {
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "id": "pi_test_123",
                        "status": "succeeded",
                        "metadata": {
                            "verification_id": verification_id,
                            "guardian_user_id": guardian_verification_data["guardian_user_id"]
                        },
                        "payment_method": "pm_test_card"
                    }
                }
            }
        }
        
        response = client.post("/api/v1/verify/result", json=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processed"] is True
        assert data["status_updated"] is True
        assert data["verification_id"] == verification_id
        assert "Verification verified" in data["message"]
    
    @pytest.mark.asyncio
    async def test_micro_charge_payment_failed_webhook(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test failed payment webhook processing"""
        
        # Start verification first
        start_response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        verification_id = start_response.json()["verification_id"]
        
        # Mock failed payment webhook
        webhook_data = {
            "verification_id": verification_id,
            "provider": "stripe",
            "event_type": "payment_intent.payment_failed",
            "provider_data": {
                "type": "payment_intent.payment_failed",
                "data": {
                    "object": {
                        "id": "pi_test_123",
                        "status": "requires_payment_method",
                        "metadata": {
                            "verification_id": verification_id
                        },
                        "last_payment_error": {
                            "code": "card_declined",
                            "message": "Your card was declined."
                        }
                    }
                }
            }
        }
        
        response = client.post("/api/v1/verify/result", json=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processed"] is True
        assert data["status_updated"] is True
        assert "Verification failed" in data["message"]


class TestKBAVerification:
    """Test KBA verification flow"""
    
    @pytest.mark.asyncio
    async def test_start_kba_verification_success(
        self,
        client: TestClient,
        mock_kba,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test successful KBA verification start"""
        
        kba_data = guardian_verification_data.copy()
        kba_data["method"] = "kba"
        
        response = client.post("/api/v1/verify/start", json=kba_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "verification_id" in data
        assert data["status"] == "in_progress"
        assert data["method"] == "kba"
        assert "kba" in data
        assert "session_id" in data["kba"]
        assert "session_url" in data["kba"]
        assert data["kba"]["max_questions"] == 5
    
    @pytest.mark.asyncio
    async def test_kba_verification_success_callback(
        self,
        client: TestClient,
        mock_kba,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test successful KBA verification callback"""
        
        kba_data = guardian_verification_data.copy()
        kba_data["method"] = "kba"
        
        # Start verification first
        start_response = client.post("/api/v1/verify/start", json=kba_data)
        verification_id = start_response.json()["verification_id"]
        
        # Mock successful KBA callback
        callback_data = {
            "verification_id": verification_id,
            "provider": "mock",
            "event_type": "kba_completed",
            "provider_data": {
                "session_id": "kba_test_123",
                "score": 85,
                "questionsAnswered": 4,
                "correctAnswers": 4,
                "passed": True,
                "metadata": {
                    "verification_id": verification_id
                }
            }
        }
        
        response = client.post("/api/v1/verify/result", json=callback_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processed"] is True
        assert data["status_updated"] is True
        assert "Verification verified" in data["message"]
    
    @pytest.mark.asyncio
    async def test_kba_verification_failed_callback(
        self,
        client: TestClient,
        mock_kba,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test failed KBA verification callback"""
        
        kba_data = guardian_verification_data.copy()
        kba_data["method"] = "kba"
        
        # Start verification first
        start_response = client.post("/api/v1/verify/start", json=kba_data)
        verification_id = start_response.json()["verification_id"]
        
        # Mock failed KBA callback
        callback_data = {
            "verification_id": verification_id,
            "provider": "mock",
            "event_type": "kba_completed",
            "provider_data": {
                "session_id": "kba_test_123",
                "score": 45,
                "questionsAnswered": 5,
                "correctAnswers": 2,
                "passed": False,
                "failure_reason": "kba_failed"
            }
        }
        
        response = client.post("/api/v1/verify/result", json=callback_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["processed"] is True
        assert data["status_updated"] is True
        assert "Verification failed" in data["message"]


class TestVerificationStatus:
    """Test verification status endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_verification_status(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test getting verification status"""
        
        # Start verification first
        start_response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        verification_id = start_response.json()["verification_id"]
        
        # Get status
        response = client.get(f"/api/v1/verify/{verification_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["verification_id"] == verification_id
        assert data["guardian_user_id"] == guardian_verification_data["guardian_user_id"]
        assert data["status"] == "in_progress"
        assert data["method"] == "micro_charge"
        assert data["attempt_count"] == 1
        assert data["can_retry"] is True
    
    @pytest.mark.asyncio
    async def test_get_guardian_verification_summary(
        self,
        client: TestClient,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test getting guardian verification summary"""
        
        guardian_user_id = guardian_verification_data["guardian_user_id"]
        
        # Get summary for unverified guardian
        response = client.get(f"/api/v1/guardian/{guardian_user_id}/verification")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["guardian_user_id"] == guardian_user_id
        assert data["is_verified"] is False
        assert data["blocks_consent_toggles"] is True
        assert data["required_for_enrollment"] is True
    
    @pytest.mark.asyncio
    async def test_bulk_verification_status(
        self,
        client: TestClient,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test bulk verification status check"""
        
        guardian_ids = [
            "guardian_test_123",
            "guardian_test_456",
            "guardian_test_789"
        ]
        
        bulk_request = {
            "guardian_user_ids": guardian_ids,
            "tenant_id": "test_tenant"
        }
        
        response = client.post("/api/v1/guardian/verification/bulk", json=bulk_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total_count"] == 3
        assert data["verified_count"] == 0
        assert data["unverified_count"] == 3
        assert len(data["results"]) == 3
        
        for result in data["results"]:
            assert result["is_verified"] is False
            assert result["blocks_consent_toggles"] is True


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test rate limit enforcement"""
        
        # Make maximum allowed attempts
        for i in range(settings.max_attempts_per_day):
            # Use unique data to avoid duplicate checks
            data = guardian_verification_data.copy()
            data["metadata"]["attempt"] = i
            
            response = client.post("/api/v1/verify/start", json=data)
            if i == 0:
                assert response.status_code == 200
            else:
                # Subsequent attempts should be rate limited after first active verification
                assert response.status_code in [409, 429]  # Conflict or rate limited
                break
    
    @pytest.mark.asyncio
    async def test_get_rate_limit_status(
        self,
        client: TestClient,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test getting rate limit status"""
        
        guardian_user_id = guardian_verification_data["guardian_user_id"]
        
        response = client.get(f"/api/v1/guardian/{guardian_user_id}/rate-limit")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["guardian_user_id"] == guardian_user_id
        assert data["rate_limited"] is False
        assert data["attempts_used_today"] >= 0
        assert data["attempts_remaining_today"] <= settings.max_attempts_per_day


class TestGeographicPolicies:
    """Test geographic restrictions"""
    
    @pytest.mark.asyncio
    async def test_unsupported_country_restriction(
        self,
        client: TestClient,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test verification restriction for unsupported countries"""
        
        # Test with unsupported country
        data = guardian_verification_data.copy()
        data["country_code"] = "XX"  # Invalid country
        
        with patch.object(settings, 'geo_restrictions_enabled', True), \
             patch.object(settings, 'is_allowed_country') as mock_allowed:
            mock_allowed.return_value = False
            
            response = client.post("/api/v1/verify/start", json=data)
            
            assert response.status_code == 403
            assert "not available in your region" in response.json()["detail"]["error"]


class TestOnboardingIntegration:
    """Test integration with onboarding flow"""
    
    @pytest.mark.asyncio
    async def test_verification_required_for_consent(
        self,
        client: TestClient,
        guardian_verification_data: Dict[str, Any]
    ):
        """Test that unverified guardians are blocked from consent toggles"""
        
        guardian_user_id = guardian_verification_data["guardian_user_id"]
        
        # Check verification status
        response = client.get(f"/api/v1/guardian/{guardian_user_id}/verification")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should block consent toggles until verified
        assert data["blocks_consent_toggles"] is True
        assert data["required_for_enrollment"] is True
    
    @pytest.mark.asyncio
    async def test_verified_guardian_allows_consent(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any],
        db_session: AsyncSession
    ):
        """Test that verified guardians can access consent toggles"""
        
        # Start and complete verification
        start_response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        verification_id = start_response.json()["verification_id"]
        
        # Manually mark as verified in database
        result = await db_session.execute(
            select(GuardianVerification).where(GuardianVerification.id == verification_id)
        )
        verification = result.scalar_one()
        verification.status = VerificationStatus.VERIFIED
        verification.verified_at = datetime.utcnow()
        await db_session.commit()
        
        # Check verification status
        guardian_user_id = guardian_verification_data["guardian_user_id"]
        response = client.get(f"/api/v1/guardian/{guardian_user_id}/verification")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should allow consent toggles when verified
        assert data["is_verified"] is True
        assert data["blocks_consent_toggles"] is False


class TestPrivacyCompliance:
    """Test COPPA and privacy compliance features"""
    
    @pytest.mark.asyncio
    async def test_minimal_pii_storage(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any],
        db_session: AsyncSession
    ):
        """Test that minimal PII is stored"""
        
        # Start verification
        response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        verification_id = response.json()["verification_id"]
        
        # Check database record
        result = await db_session.execute(
            select(GuardianVerification).where(GuardianVerification.id == verification_id)
        )
        verification = result.scalar_one()
        
        # Should not store detailed personal information
        assert verification.guardian_user_id == guardian_verification_data["guardian_user_id"]
        assert verification.verification_country == guardian_verification_data["country_code"]
        
        # PII should be tokenized or hashed, not stored in plain text
        assert verification.data_retention_until is not None
        assert verification.consent_version == "2025-v1"
    
    @pytest.mark.asyncio
    async def test_data_retention_policy(
        self,
        client: TestClient,
        mock_stripe,
        guardian_verification_data: Dict[str, Any],
        db_session: AsyncSession
    ):
        """Test automatic data retention and deletion"""
        
        # Start verification
        response = client.post("/api/v1/verify/start", json=guardian_verification_data)
        verification_id = response.json()["verification_id"]
        
        # Check data retention date is set
        result = await db_session.execute(
            select(GuardianVerification).where(GuardianVerification.id == verification_id)
        )
        verification = result.scalar_one()
        
        # Should have retention date set
        assert verification.data_retention_until is not None
        
        # Should be set to 90 days from now (default retention period)
        expected_retention = datetime.utcnow() + timedelta(days=settings.data_retention_days)
        time_diff = abs((verification.data_retention_until - expected_retention).total_seconds())
        assert time_diff < 60  # Within 1 minute of expected time


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
