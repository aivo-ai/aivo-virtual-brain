# AIVO Approval Service - Comprehensive Tests
# S2-10 Implementation - Tests for approval workflow with state machine + TTL

import pytest
import asyncio
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import uuid
import json

# Set test environment variable
os.environ["TESTING"] = "1"

from app.main import app
from app.database import get_db, Base
from app.models import (
    ApprovalRequest, ApprovalDecision, ApprovalReminder, ApprovalAuditLog,
    ApprovalStatus, ApproverRole, ApprovalType
)
from app.schemas import ApprovalRequestCreate, ApprovalDecisionCreate

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture
def db_session():
    """Create a fresh database session for each test."""
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture
def sample_approval_request_data():
    """Sample approval request data for testing."""
    return {
        "tenant_id": str(uuid.uuid4()),
        "approval_type": "iep_change",
        "resource_id": "iep_12345",
        "resource_type": "iep",
        "title": "IEP Goals Update for Student John Doe",
        "description": "Updating annual goals based on latest assessment results",
        "context_data": {
            "student_id": "student_456",
            "changes": ["goal_1_modified", "goal_2_added"],
            "justification": "Based on Q2 progress data"
        },
        "expires_in_hours": 72,
        "requested_by": "teacher_789",
        "requested_by_role": "case_manager",
        "required_roles": ["guardian", "teacher"],
        "webhook_url": "https://orchestrator.example.com/webhooks/approval",
        "webhook_headers": {"Authorization": "Bearer test-token"}
    }


@pytest.fixture
def sample_decision_data():
    """Sample approval decision data for testing."""
    return {
        "approver_id": "guardian_123",
        "approver_role": "guardian",
        "approver_name": "Jane Doe (Parent)",
        "approved": True,
        "comments": "I approve these changes based on our discussion",
        "decision_metadata": {"meeting_date": "2024-12-15"}
    }


class TestApprovalRequests:
    """Test suite for approval request management."""
    
    def test_create_approval_request_success(self, sample_approval_request_data):
        """Test successful creation of approval request."""
        response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["approval_type"] == "iep_change"
        assert data["resource_id"] == "iep_12345"
        assert data["title"] == "IEP Goals Update for Student John Doe"
        assert data["status"] == "pending"
        assert data["requested_by"] == "teacher_789"
        assert data["required_approvals"] == ["guardian", "teacher"]
        assert data["pending_approvals"] == ["guardian", "teacher"]
        assert data["all_approvals_received"] is False
        assert data["webhook_sent"] is False
        
        # Verify timestamps
        assert data["created_at"] is not None
        assert data["expires_at"] is not None
        assert data["decided_at"] is None
    
    def test_create_approval_request_invalid_data(self):
        """Test creation with invalid data."""
        invalid_data = {
            "tenant_id": "invalid-uuid",
            "approval_type": "invalid_type",
            "required_roles": [],  # Empty roles not allowed
            "expires_in_hours": 0  # Invalid expiration
        }
        
        response = client.post("/api/v1/approvals/", json=invalid_data)
        assert response.status_code == 422
    
    def test_get_approval_request_success(self, sample_approval_request_data):
        """Test retrieving an approval request."""
        # First create a request
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # Then retrieve it
        response = client.get(f"/api/v1/approvals/{request_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == request_id
        assert data["approval_type"] == "iep_change"
        assert data["status"] == "pending"
    
    def test_get_approval_request_not_found(self):
        """Test retrieving non-existent approval request."""
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/approvals/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_list_approval_requests(self, sample_approval_request_data):
        """Test listing approval requests with pagination."""
        tenant_id = str(uuid.uuid4())
        
        # Create multiple requests
        for i in range(5):
            data = sample_approval_request_data.copy()
            data["tenant_id"] = tenant_id
            data["title"] = f"Request {i}"
            client.post("/api/v1/approvals/", json=data)
        
        # List requests for this tenant
        response = client.get(f"/api/v1/approvals/?tenant_id={tenant_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["total"] == 5
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["per_page"] == 50
        assert data["pages"] == 1
        assert data["has_next"] is False
        assert data["has_prev"] is False
    
    def test_list_approval_requests_with_filters(self, sample_approval_request_data):
        """Test listing with various filters."""
        tenant_id = str(uuid.uuid4())
        
        # Create requests with different types
        for approval_type in ["iep_change", "level_change", "consent_sensitive"]:
            data = sample_approval_request_data.copy()
            data["tenant_id"] = tenant_id
            data["approval_type"] = approval_type
            client.post("/api/v1/approvals/", json=data)
        
        # Filter by type
        response = client.get(f"/api/v1/approvals/?tenant_id={tenant_id}&approval_type=iep_change")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["approval_type"] == "iep_change"


class TestApprovalDecisions:
    """Test suite for approval decision making."""
    
    def test_make_approval_decision_success(self, sample_approval_request_data, sample_decision_data):
        """Test successful approval decision."""
        # Create approval request
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # Make approval decision
        response = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=sample_decision_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still be pending since we need both guardian and teacher approval
        assert data["status"] == "pending"
        assert len(data["approvals"]) == 1
        assert data["approvals"][0]["approved"] is True
        assert data["approvals"][0]["approver_role"] == "guardian"
        assert data["pending_approvals"] == ["teacher"]
        assert data["all_approvals_received"] is False
    
    def test_dual_approval_required_path(self, sample_approval_request_data):
        """Test that both guardian and teacher approval are required."""
        # Create request requiring both guardian and teacher approval
        sample_approval_request_data["required_roles"] = ["guardian", "teacher"]
        
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # First approval - guardian
        guardian_decision = {
            "approver_id": "guardian_123",
            "approver_role": "guardian",
            "approved": True,
            "comments": "I approve these changes"
        }
        
        response1 = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=guardian_decision
        )
        
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["status"] == "pending"  # Still pending teacher approval
        assert data1["pending_approvals"] == ["teacher"]
        
        # Second approval - teacher
        teacher_decision = {
            "approver_id": "teacher_456",
            "approver_role": "teacher",
            "approved": True,
            "comments": "Educational goals look appropriate"
        }
        
        response2 = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=teacher_decision
        )
        
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["status"] == "approved"  # Now fully approved
        assert data2["all_approvals_received"] is True
        assert data2["pending_approvals"] == []
        assert data2["decided_at"] is not None
    
    def test_rejection_immediately_rejects_request(self, sample_approval_request_data):
        """Test that any rejection immediately rejects the entire request."""
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # Make rejection decision
        rejection_data = {
            "approver_id": "guardian_123",
            "approver_role": "guardian",
            "approved": False,
            "comments": "I do not agree with these changes"
        }
        
        response = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=rejection_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "rejected"
        assert data["decided_at"] is not None
        assert "Rejected by guardian" in data["decision_reason"]
        assert len(data["approvals"]) == 1
        assert data["approvals"][0]["approved"] is False
    
    def test_make_decision_on_non_pending_request(self, sample_approval_request_data, sample_decision_data):
        """Test making decision on already decided request."""
        # Create and approve a request fully
        sample_approval_request_data["required_roles"] = ["guardian"]  # Only one approval needed
        
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # First decision - should approve the request
        client.post(f"/api/v1/approvals/{request_id}/decision", json=sample_decision_data)
        
        # Try to make another decision
        response = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=sample_decision_data
        )
        
        assert response.status_code == 400
        assert "Cannot make decision on approved request" in response.json()["detail"]
    
    def test_duplicate_role_approval_not_allowed(self, sample_approval_request_data, sample_decision_data):
        """Test that the same role cannot approve twice."""
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # First approval
        client.post(f"/api/v1/approvals/{request_id}/decision", json=sample_decision_data)
        
        # Try to approve again with same role
        response = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=sample_decision_data
        )
        
        assert response.status_code == 400
        assert "has already approved" in response.json()["detail"]
    
    def test_unauthorized_role_approval(self, sample_approval_request_data):
        """Test approval by role that's not required."""
        sample_approval_request_data["required_roles"] = ["guardian"]  # Only guardian required
        
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # Try to approve with district_admin (not required)
        admin_decision = {
            "approver_id": "admin_789",
            "approver_role": "district_admin",
            "approved": True,
            "comments": "Admin approval"
        }
        
        response = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=admin_decision
        )
        
        assert response.status_code == 400
        assert "not required for this approval" in response.json()["detail"]


class TestApprovalExpiration:
    """Test suite for approval expiration and TTL functionality."""
    
    def test_timeout_expiry(self, db_session, sample_approval_request_data):
        """Test that requests expire after timeout."""
        # Create request that expires in 1 hour
        sample_approval_request_data["expires_in_hours"] = 1
        
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # Get the request from database and manually set expiration to past
        approval_request = db_session.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        
        # Set expiration to 1 hour ago
        approval_request.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()
        
        # Try to retrieve - should be marked as expired
        response = client.get(f"/api/v1/approvals/{request_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "expired"
        assert data["is_expired"] is True
        assert data["decided_at"] is not None
        assert "expired due to timeout" in data["decision_reason"]
    
    def test_cannot_decide_on_expired_request(self, db_session, sample_approval_request_data, sample_decision_data):
        """Test that decisions cannot be made on expired requests."""
        create_response = client.post("/api/v1/approvals/", json=sample_approval_request_data)
        request_id = create_response.json()["id"]
        
        # Manually expire the request
        approval_request = db_session.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        approval_request.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        db_session.commit()
        
        # Try to make decision
        response = client.post(
            f"/api/v1/approvals/{request_id}/decision",
            json=sample_decision_data
        )
        
        assert response.status_code == 400
        assert "Cannot make decision on expired request" in response.json()["detail"]


class TestApprovalStatistics:
    """Test suite for approval statistics and metrics."""
    
    def test_get_approval_stats(self, sample_approval_request_data):
        """Test getting approval statistics."""
        tenant_id = str(uuid.uuid4())
        
        # Create various types of requests
        test_cases = [
            ("iep_change", "guardian", True),
            ("level_change", "guardian", False),
            ("consent_sensitive", "teacher", True),
            ("iep_change", "teacher", True)
        ]
        
        for approval_type, role, should_approve in test_cases:
            data = sample_approval_request_data.copy()
            data["tenant_id"] = tenant_id
            data["approval_type"] = approval_type
            data["required_roles"] = [role]
            
            create_response = client.post("/api/v1/approvals/", json=data)
            request_id = create_response.json()["id"]
            
            # Make decision
            decision = {
                "approver_id": f"{role}_123",
                "approver_role": role,
                "approved": should_approve,
                "comments": "Test decision"
            }
            
            client.post(f"/api/v1/approvals/{request_id}/decision", json=decision)
        
        # Get stats
        response = client.get(f"/api/v1/approvals/stats?tenant_id={tenant_id}")
        
        assert response.status_code == 200
        stats = response.json()
        
        assert stats["total_requests"] == 4
        assert stats["approved_requests"] == 3
        assert stats["rejected_requests"] == 1
        assert stats["pending_requests"] == 0
        assert stats["iep_change_requests"] == 2
        assert stats["level_change_requests"] == 1
        assert stats["consent_sensitive_requests"] == 1
        assert stats["approval_rate"] == 75.0  # 3/4 * 100


class TestStateManagement:
    """Test suite for approval state machine logic."""
    
    def test_state_transitions(self, db_session):
        """Test valid state transitions in the approval state machine."""
        # Create approval request directly in database
        request = ApprovalRequest(
            tenant_id=uuid.uuid4(),
            approval_type=ApprovalType.IEP_CHANGE,
            resource_id="test_resource",
            resource_type="test",
            title="Test Request",
            status=ApprovalStatus.PENDING,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            requested_by="test_user",
            context_data={"required_roles": ["guardian"]}
        )
        
        # Test valid transitions from PENDING
        assert request.can_transition_to(ApprovalStatus.APPROVED)
        assert request.can_transition_to(ApprovalStatus.REJECTED)
        assert request.can_transition_to(ApprovalStatus.EXPIRED)
        
        # Test invalid transitions
        assert not request.can_transition_to(ApprovalStatus.PENDING)
        
        # Test terminal states have no valid transitions
        request.status = ApprovalStatus.APPROVED
        assert not request.can_transition_to(ApprovalStatus.PENDING)
        assert not request.can_transition_to(ApprovalStatus.REJECTED)
        assert not request.can_transition_to(ApprovalStatus.EXPIRED)
    
    def test_computed_properties(self, db_session):
        """Test computed properties on ApprovalRequest model."""
        # Create request
        request = ApprovalRequest(
            tenant_id=uuid.uuid4(),
            approval_type=ApprovalType.IEP_CHANGE,
            resource_id="test_resource",
            resource_type="test",
            title="Test Request",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            requested_by="test_user",
            context_data={"required_roles": ["guardian", "teacher"]}
        )
        
        db_session.add(request)
        db_session.flush()
        
        # Test initial state
        assert request.required_approvals == ["guardian", "teacher"]
        assert request.pending_approvals == ["guardian", "teacher"]
        assert request.all_approvals_received is False
        assert request.is_expired is False
        
        # Add one approval
        decision = ApprovalDecision(
            request_id=request.id,
            approver_id="guardian_123",
            approver_role=ApproverRole.GUARDIAN,
            approved=True
        )
        
        db_session.add(decision)
        db_session.flush()
        
        # Test after one approval
        db_session.refresh(request)
        assert request.pending_approvals == ["teacher"]
        assert request.all_approvals_received is False
        
        # Add second approval
        decision2 = ApprovalDecision(
            request_id=request.id,
            approver_id="teacher_456",
            approver_role=ApproverRole.TEACHER,
            approved=True
        )
        
        db_session.add(decision2)
        db_session.flush()
        
        # Test after all approvals
        db_session.refresh(request)
        assert request.pending_approvals == []
        assert request.all_approvals_received is True


class TestErrorHandling:
    """Test suite for error handling and edge cases."""
    
    def test_invalid_uuid_format(self):
        """Test handling of invalid UUID formats."""
        response = client.get("/api/v1/approvals/invalid-uuid-format")
        assert response.status_code == 422
    
    def test_database_error_handling(self):
        """Test handling of database connection errors."""
        # This would require mocking database failures
        pass
    
    def test_malformed_json_request(self):
        """Test handling of malformed JSON in requests."""
        response = client.post(
            "/api/v1/approvals/",
            data="invalid json content",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422


# Test fixtures cleanup
@pytest.fixture(scope="function", autouse=True)
def cleanup_database():
    """Clean up database after each test."""
    yield
    # Clear all tables using modern SQLAlchemy syntax
    with engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
        conn.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
