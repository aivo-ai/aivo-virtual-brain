# AIVO Admin Service Tests

import pytest
import asyncio
from httpx import AsyncClient
from fastapi.testclient import TestClient
import jwt
from datetime import datetime, timedelta

from app.main import app
from app.config import settings
from app.auth import generate_jwt_token


@pytest.fixture
def client():
    """Test client fixture"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async test client fixture"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def staff_token():
    """Generate staff user token for testing"""
    return generate_jwt_token(
        user_id="staff_001",
        email="staff@example.com",
        roles=["staff"],
        tenant_id="test_tenant"
    )


@pytest.fixture
def admin_token():
    """Generate admin user token for testing"""
    return generate_jwt_token(
        user_id="admin_001",
        email="admin@example.com",
        roles=["tenant_admin"],
        tenant_id="test_tenant"
    )


@pytest.fixture
def system_admin_token():
    """Generate system admin token for testing"""
    return generate_jwt_token(
        user_id="sysadmin_001",
        email="sysadmin@example.com",
        roles=["system_admin"]
    )


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "admin-svc"
    
    def test_readiness_check(self, client):
        response = client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestAuthentication:
    """Test authentication and authorization"""
    
    def test_admin_status_requires_auth(self, client):
        response = client.get("/admin/status")
        assert response.status_code == 401
    
    def test_admin_status_with_valid_token(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["admin_user"]["user_id"] == "staff_001"
        assert "staff" in data["admin_user"]["roles"]
    
    def test_invalid_token_rejected(self, client):
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/admin/status", headers=headers)
        assert response.status_code == 401
    
    def test_expired_token_rejected(self, client):
        # Generate expired token
        expired_token = jwt.encode(
            {
                "sub": "user_001",
                "email": "user@example.com",
                "roles": ["staff"],
                "exp": int((datetime.utcnow() - timedelta(hours=1)).timestamp())
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/admin/status", headers=headers)
        assert response.status_code == 401


class TestSystemEndpoints:
    """Test system monitoring endpoints"""
    
    def test_get_system_stats(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_learners" in data
        assert "active_sessions" in data
        assert "pending_approvals" in data
    
    def test_get_service_health(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/health", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_feature_flags(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/flags", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "emergency_access" in data
        assert "queue_management" in data


class TestApprovalEndpoints:
    """Test approval queue endpoints"""
    
    def test_get_approval_queue(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/approvals", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_approval_stats(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/approvals/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_pending" in data
        assert "total_approved" in data
    
    def test_get_approval_details(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/approvals/app_001", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "app_001"


class TestQueueEndpoints:
    """Test job queue endpoints"""
    
    def test_get_job_queues(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/queues", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_queue_stats(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/queues/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_queues" in data
    
    def test_requeue_job_requires_admin(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.post(
            "/admin/jobs/job_001/requeue",
            headers=headers,
            json={"action": "requeue", "reason": "Test requeue"}
        )
        assert response.status_code == 403  # Staff can't manage jobs
    
    def test_requeue_job_with_admin(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post(
            "/admin/jobs/job_001/requeue",
            headers=headers,
            json={"action": "requeue", "reason": "Test requeue"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "requeue"
        assert data["job_id"] == "job_001"


class TestSupportEndpoints:
    """Test support session endpoints"""
    
    def test_request_support_session(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.post(
            "/admin/support-session/request",
            headers=headers,
            json={
                "learner_id": "learner_123",
                "purpose": "Test support request",
                "urgency": "normal",
                "estimated_duration_minutes": 30
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
    
    def test_get_support_sessions(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/support-sessions", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAuditEndpoints:
    """Test audit and compliance endpoints"""
    
    def test_query_audit_events(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/audit/events", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_audit_summary(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/audit/summary", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "by_event_type" in data
    
    def test_compliance_report_requires_system_admin(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.get(
            "/admin/audit/compliance-report",
            headers=headers,
            params={
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59"
            }
        )
        assert response.status_code == 403  # Tenant admin can't access
    
    def test_compliance_report_with_system_admin(self, client, system_admin_token):
        headers = {"Authorization": f"Bearer {system_admin_token}"}
        response = client.get(
            "/admin/audit/compliance-report",
            headers=headers,
            params={
                "start_date": "2024-01-01T00:00:00",
                "end_date": "2024-01-31T23:59:59"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "report_period" in data
        assert "summary" in data


class TestRoleBasedAccess:
    """Test role-based access control"""
    
    def test_non_staff_user_rejected(self, client):
        # Generate token for non-staff user
        non_staff_token = generate_jwt_token(
            user_id="user_001",
            email="user@example.com",
            roles=["learner"],  # Not a staff role
            tenant_id="test_tenant"
        )
        
        headers = {"Authorization": f"Bearer {non_staff_token}"}
        response = client.get("/admin/status", headers=headers)
        assert response.status_code == 403
    
    def test_staff_can_view_data(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/stats", headers=headers)
        assert response.status_code == 200
    
    def test_staff_cannot_manage_jobs(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.post(
            "/admin/jobs/job_001/cancel",
            headers=headers,
            json={"action": "cancel", "reason": "Test"}
        )
        assert response.status_code == 403
    
    def test_tenant_admin_can_manage_jobs(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = client.post(
            "/admin/jobs/job_001/cancel",
            headers=headers,
            json={"action": "cancel", "reason": "Test"}
        )
        assert response.status_code == 200


class TestSecurity:
    """Test security measures"""
    
    def test_security_headers_present(self, client):
        response = client.get("/health")
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-Admin-Service"] == "aivo-admin-svc"
    
    def test_request_id_header(self, client, staff_token):
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = client.get("/admin/status", headers=headers)
        assert "X-Request-ID" in response.headers
        assert "X-Process-Time" in response.headers
    
    def test_cors_headers_configured(self, client):
        response = client.options("/admin/status")
        # CORS headers should be present for OPTIONS requests


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
