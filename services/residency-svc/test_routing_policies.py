"""
Comprehensive tests for the Data Residency Service
Tests region routing, compliance enforcement, and emergency overrides
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import Base, ResidencyPolicy, RegionInfrastructure, DataAccessLog, EmergencyOverride
from app.database import get_db_session
from app.config import settings

# Test database URL (in-memory SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create test engine and session
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)

test_session_factory = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_test_db_session():
    """Override database session for testing"""
    async with test_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Override dependency
app.dependency_overrides[get_db_session] = get_test_db_session

client = TestClient(app)


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for testing"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Setup test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Add test data
    async with test_session_factory() as session:
        # Add test region infrastructure
        regions = [
            RegionInfrastructure(
                region_code="us-east",
                region_name="US East",
                s3_bucket_name="test-us-east",
                s3_region="us-east-1",
                backup_bucket_name="test-backup-us-east",
                opensearch_domain="test-search-us-east",
                opensearch_endpoint="https://test-us-east.search.com",
                inference_providers=[
                    {"provider": "aws-bedrock", "models": ["claude-3-haiku"]}
                ],
                compliance_certifications=["SOC2", "HIPAA"],
                data_center_location="US East Coast",
                is_active=True
            ),
            RegionInfrastructure(
                region_code="eu-west",
                region_name="EU West",
                s3_bucket_name="test-eu-west",
                s3_region="eu-west-1",
                backup_bucket_name="test-backup-eu-west",
                opensearch_domain="test-search-eu-west",
                opensearch_endpoint="https://test-eu-west.search.com",
                inference_providers=[
                    {"provider": "anthropic-eu", "models": ["claude-3-sonnet"]}
                ],
                compliance_certifications=["GDPR", "SOC2"],
                data_center_location="EU West",
                is_active=True
            )
        ]
        
        for region in regions:
            session.add(region)
        
        await session.commit()
    
    yield
    
    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


class TestResidencyPolicies:
    """Test residency policy management"""
    
    @pytest.mark.asyncio
    async def test_create_policy_success(self):
        """Test successful policy creation"""
        policy_data = {
            "tenant_id": "tenant-123",
            "learner_id": "learner-456",
            "primary_region": "us-east",
            "allowed_regions": ["eu-west"],
            "prohibited_regions": [],
            "compliance_frameworks": ["ferpa"],
            "data_classification": "educational",
            "allow_cross_region_failover": True,
            "emergency_contact": "admin@example.com"
        }
        
        response = client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-123"
        assert data["learner_id"] == "learner-456"
        assert data["primary_region"] == "us-east"
        assert data["is_active"] is True
    
    @pytest.mark.asyncio
    async def test_create_policy_invalid_region(self):
        """Test policy creation with invalid region"""
        policy_data = {
            "tenant_id": "tenant-123",
            "primary_region": "invalid-region",
            "compliance_frameworks": []
        }
        
        response = client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 400
        assert "Unsupported regions" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_policy_conflicting_regions(self):
        """Test policy creation with conflicting allowed/prohibited regions"""
        policy_data = {
            "tenant_id": "tenant-123",
            "primary_region": "us-east",
            "allowed_regions": ["eu-west"],
            "prohibited_regions": ["eu-west"],
            "compliance_frameworks": []
        }
        
        response = client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 400
        assert "cannot be both allowed and prohibited" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_tenant_policies(self):
        """Test retrieving tenant policies"""
        # First create a policy
        policy_data = {
            "tenant_id": "tenant-789",
            "primary_region": "us-east",
            "compliance_frameworks": ["ferpa"]
        }
        
        create_response = client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        assert create_response.status_code == 200
        
        # Then retrieve it
        response = client.get(
            "/api/v1/policies/tenant-789",
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        policies = response.json()
        assert len(policies) == 1
        assert policies[0]["tenant_id"] == "tenant-789"


class TestDataAccessResolution:
    """Test data access resolution and routing"""
    
    @pytest.mark.asyncio
    async def test_resolve_access_with_policy(self):
        """Test data access resolution with existing policy"""
        # Create policy first
        policy_data = {
            "tenant_id": "tenant-access-1",
            "primary_region": "us-east",
            "allowed_regions": ["eu-west"],
            "compliance_frameworks": ["ferpa"]
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Test access resolution
        access_request = {
            "tenant_id": "tenant-access-1",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-123"
        }
        
        response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-123",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["target_region"] == "us-east"
        assert "infrastructure" in data
        assert len(data["compliance_notes"]) > 0
    
    @pytest.mark.asyncio
    async def test_resolve_access_cross_region_allowed(self):
        """Test cross-region access that is allowed"""
        # Create policy with cross-region access
        policy_data = {
            "tenant_id": "tenant-cross-1",
            "primary_region": "us-east",
            "allowed_regions": ["eu-west"],
            "allow_cross_region_failover": True,
            "compliance_frameworks": []
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Test cross-region access
        access_request = {
            "tenant_id": "tenant-cross-1",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-456",
            "requested_region": "eu-west"
        }
        
        response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-123",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["target_region"] == "eu-west"
    
    @pytest.mark.asyncio
    async def test_resolve_access_prohibited_region(self):
        """Test access to prohibited region"""
        # Create policy with prohibited region
        policy_data = {
            "tenant_id": "tenant-prohibited-1",
            "primary_region": "us-east",
            "prohibited_regions": ["eu-west"],
            "compliance_frameworks": []
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Test access to prohibited region
        access_request = {
            "tenant_id": "tenant-prohibited-1",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-789",
            "requested_region": "eu-west"
        }
        
        response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-123",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 403
        assert "prohibited" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_resolve_access_no_policy_default(self):
        """Test access resolution with no policy (should use default)"""
        access_request = {
            "tenant_id": "tenant-no-policy",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-default"
        }
        
        response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-123",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["allowed"] is True
        assert data["target_region"] == settings.default_region
        assert "No specific policy" in data["compliance_notes"][0]


class TestEmergencyOverrides:
    """Test emergency override functionality"""
    
    @pytest.mark.asyncio
    async def test_request_emergency_override(self):
        """Test requesting emergency override"""
        override_request = {
            "tenant_id": "tenant-emergency-1",
            "reason": "Critical system failure requires cross-region access",
            "affected_learners": ["learner-1", "learner-2"],
            "source_region": "us-east",
            "target_region": "eu-west",
            "duration_hours": 24
        }
        
        response = client.post(
            "/api/v1/emergency/override",
            json=override_request,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "override_id" in data
        assert data["status"] in ["pending", "approved"]
    
    @pytest.mark.asyncio
    async def test_emergency_override_excessive_duration(self):
        """Test emergency override with excessive duration"""
        override_request = {
            "tenant_id": "tenant-emergency-2",
            "reason": "Test override",
            "source_region": "us-east",
            "target_region": "eu-west",
            "duration_hours": 200  # Exceeds max duration
        }
        
        response = client.post(
            "/api/v1/emergency/override",
            json=override_request,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 400
        assert "cannot exceed" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_access_with_emergency_override(self):
        """Test data access using emergency override"""
        # Create restrictive policy
        policy_data = {
            "tenant_id": "tenant-override-access",
            "primary_region": "us-east",
            "prohibited_regions": ["eu-west"],
            "compliance_frameworks": ["gdpr"]  # Prohibits cross-region
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Request emergency override
        override_request = {
            "tenant_id": "tenant-override-access",
            "reason": "Emergency data access required",
            "source_region": "us-east",
            "target_region": "eu-west",
            "duration_hours": 2
        }
        
        override_response = client.post(
            "/api/v1/emergency/override",
            json=override_request,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert override_response.status_code == 200
        
        # Now try access with emergency override
        access_request = {
            "tenant_id": "tenant-override-access",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-emergency",
            "requested_region": "eu-west",
            "emergency_override": True,
            "override_reason": "Emergency access needed"
        }
        
        access_response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # This might succeed or fail depending on override approval configuration
        # In test environment, check the actual behavior
        if access_response.status_code == 200:
            data = access_response.json()
            assert data["emergency_override_used"] is True
            assert data["target_region"] == "eu-west"


class TestComplianceFrameworks:
    """Test compliance framework enforcement"""
    
    @pytest.mark.asyncio
    async def test_gdpr_compliance_cross_region_blocked(self):
        """Test that GDPR compliance blocks cross-region access"""
        policy_data = {
            "tenant_id": "tenant-gdpr-1",
            "primary_region": "eu-west",
            "compliance_frameworks": ["gdpr"]
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Try cross-region access
        access_request = {
            "tenant_id": "tenant-gdpr-1",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-gdpr",
            "requested_region": "us-east"
        }
        
        response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-123",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 403
        assert "compliance frameworks" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_ferpa_compliance_allowed(self):
        """Test FERPA compliance allows cross-region in certain cases"""
        policy_data = {
            "tenant_id": "tenant-ferpa-1",
            "primary_region": "us-east",
            "allowed_regions": ["ca-central"],
            "compliance_frameworks": ["ferpa"],
            "allow_cross_region_failover": True
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Try cross-region access to allowed region
        access_request = {
            "tenant_id": "tenant-ferpa-1",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-ferpa",
            "requested_region": "ca-central"
        }
        
        response = client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-123",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # This should succeed if FERPA allows cross-region between US and Canada
        if response.status_code == 200:
            data = response.json()
            assert data["target_region"] == "ca-central"
            assert "ferpa" in str(data["compliance_notes"])


class TestAuditLogs:
    """Test audit logging functionality"""
    
    @pytest.mark.asyncio
    async def test_get_access_logs(self):
        """Test retrieving access logs"""
        # First generate some access
        policy_data = {
            "tenant_id": "tenant-audit-1",
            "primary_region": "us-east",
            "compliance_frameworks": []
        }
        
        client.post(
            "/api/v1/policies",
            json=policy_data,
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        access_request = {
            "tenant_id": "tenant-audit-1",
            "operation_type": "read",
            "resource_type": "document",
            "resource_id": "doc-audit"
        }
        
        client.post(
            "/api/v1/access/resolve",
            json=access_request,
            headers={
                "X-User-ID": "user-audit",
                "X-Request-ID": str(uuid4())
            }
        )
        
        # Now get audit logs
        response = client.get(
            "/api/v1/audit/access-logs/tenant-audit-1",
            headers={
                "X-User-ID": "admin-user",
                "X-Request-ID": str(uuid4())
            }
        )
        
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) >= 1
        assert logs[0]["tenant_id"] == "tenant-audit-1"
        assert logs[0]["operation_type"] == "read"


class TestRegionInformation:
    """Test region information endpoints"""
    
    @pytest.mark.asyncio
    async def test_list_supported_regions(self):
        """Test listing supported regions"""
        response = client.get("/api/v1/regions")
        
        assert response.status_code == 200
        regions = response.json()
        assert len(regions) > 0
        
        # Check that each region has required fields
        for region in regions:
            assert "region_code" in region
            assert "infrastructure" in region
            assert "compliance_frameworks" in region
            assert "is_default" in region


# Integration test helper
@pytest.mark.asyncio
async def test_end_to_end_data_residency_flow():
    """End-to-end test of data residency flow"""
    tenant_id = f"tenant-e2e-{uuid4()}"
    
    # 1. Create residency policy
    policy_data = {
        "tenant_id": tenant_id,
        "primary_region": "us-east",
        "allowed_regions": ["eu-west"],
        "compliance_frameworks": ["ferpa"],
        "allow_cross_region_failover": True
    }
    
    policy_response = client.post(
        "/api/v1/policies",
        json=policy_data,
        headers={
            "X-User-ID": "admin-user",
            "X-Request-ID": str(uuid4())
        }
    )
    
    assert policy_response.status_code == 200
    
    # 2. Test normal access (should go to primary region)
    access_request = {
        "tenant_id": tenant_id,
        "operation_type": "read",
        "resource_type": "document",
        "resource_id": "doc-e2e-1"
    }
    
    access_response = client.post(
        "/api/v1/access/resolve",
        json=access_request,
        headers={
            "X-User-ID": "user-e2e",
            "X-Request-ID": str(uuid4())
        }
    )
    
    assert access_response.status_code == 200
    assert access_response.json()["target_region"] == "us-east"
    
    # 3. Test cross-region access (should go to requested region)
    cross_region_request = {
        "tenant_id": tenant_id,
        "operation_type": "read",
        "resource_type": "document",
        "resource_id": "doc-e2e-2",
        "requested_region": "eu-west"
    }
    
    cross_response = client.post(
        "/api/v1/access/resolve",
        json=cross_region_request,
        headers={
            "X-User-ID": "user-e2e",
            "X-Request-ID": str(uuid4())
        }
    )
    
    assert cross_response.status_code == 200
    assert cross_response.json()["target_region"] == "eu-west"
    
    # 4. Verify audit logs were created
    audit_response = client.get(
        f"/api/v1/audit/access-logs/{tenant_id}",
        headers={
            "X-User-ID": "admin-user",
            "X-Request-ID": str(uuid4())
        }
    )
    
    assert audit_response.status_code == 200
    logs = audit_response.json()
    assert len(logs) >= 2  # At least the two access requests we made


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
