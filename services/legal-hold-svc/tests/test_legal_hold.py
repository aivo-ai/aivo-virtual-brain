"""
Legal Hold Service Tests

Comprehensive test suite for legal hold functionality, eDiscovery exports,
and compliance requirements.
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models import (
    Base, LegalHold, HoldCustodian, HoldAffectedEntity, 
    eDiscoveryExport, HoldAuditLog, DataRetentionOverride
)


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_legal_hold.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


def override_get_current_user():
    """Override user dependency for testing"""
    return Mock(
        id=uuid4(),
        name="Test User",
        email="test@example.com",
        role="compliance_officer",
        tenant_id=uuid4()
    )


def override_require_compliance_role():
    """Override compliance role requirement for testing"""
    return override_get_current_user()


# Apply dependency overrides
app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[require_compliance_role] = override_require_compliance_role

client = TestClient(app)


class TestLegalHolds:
    """Test legal hold management functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.db = TestingSessionLocal()
        self.user_id = uuid4()
        self.tenant_id = uuid4()
        
        # Clear test data
        self.db.query(LegalHold).delete()
        self.db.commit()

    def teardown_method(self):
        """Cleanup after each test"""
        self.db.close()

    def test_create_legal_hold_success(self):
        """Test successful legal hold creation"""
        hold_data = {
            "title": "Test Litigation Hold",
            "description": "Hold for ongoing litigation case",
            "case_number": "CASE-2025-001",
            "legal_basis": "litigation",
            "scope_type": "tenant",
            "scope_parameters": {"tenant_id": str(self.tenant_id)},
            "preserve_deleted_data": True,
            "custodian_user_ids": [str(uuid4())],
            "notify_custodians": True
        }
        
        response = client.post("/api/v1/legal-holds", json=hold_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == hold_data["title"]
        assert data["legal_basis"] == hold_data["legal_basis"]
        assert data["status"] == "active"
        assert "hold_number" in data
        assert data["hold_number"].startswith("LH-")

    def test_create_legal_hold_invalid_legal_basis(self):
        """Test legal hold creation with invalid legal basis"""
        hold_data = {
            "title": "Invalid Hold",
            "legal_basis": "invalid_basis",
            "scope_type": "tenant",
            "scope_parameters": {"tenant_id": str(self.tenant_id)},
            "custodian_user_ids": []
        }
        
        response = client.post("/api/v1/legal-holds", json=hold_data)
        
        assert response.status_code == 422
        assert "Legal basis must be one of" in response.text

    def test_create_legal_hold_invalid_scope_type(self):
        """Test legal hold creation with invalid scope type"""
        hold_data = {
            "title": "Invalid Scope Hold",
            "legal_basis": "litigation",
            "scope_type": "invalid_scope",
            "scope_parameters": {"tenant_id": str(self.tenant_id)},
            "custodian_user_ids": []
        }
        
        response = client.post("/api/v1/legal-holds", json=hold_data)
        
        assert response.status_code == 422
        assert "Scope type must be one of" in response.text

    def test_list_legal_holds(self):
        """Test listing legal holds"""
        # Create test holds
        hold1 = LegalHold(
            hold_number="LH-20250823-TEST001",
            title="Hold 1",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(self.tenant_id)},
            created_by=self.user_id,
            status="active"
        )
        hold2 = LegalHold(
            hold_number="LH-20250823-TEST002",
            title="Hold 2",
            legal_basis="investigation",
            scope_type="learner",
            scope_parameters={"learner_id": str(uuid4())},
            created_by=self.user_id,
            status="released"
        )
        
        self.db.add_all([hold1, hold2])
        self.db.commit()
        
        response = client.get("/api/v1/legal-holds")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] in ["Hold 1", "Hold 2"]
        assert data[1]["title"] in ["Hold 1", "Hold 2"]

    def test_list_legal_holds_with_status_filter(self):
        """Test listing legal holds with status filter"""
        # Create test holds with different statuses
        hold1 = LegalHold(
            hold_number="LH-20250823-TEST001",
            title="Active Hold",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(self.tenant_id)},
            created_by=self.user_id,
            status="active"
        )
        hold2 = LegalHold(
            hold_number="LH-20250823-TEST002",
            title="Released Hold",
            legal_basis="investigation",
            scope_type="learner",
            scope_parameters={"learner_id": str(uuid4())},
            created_by=self.user_id,
            status="released"
        )
        
        self.db.add_all([hold1, hold2])
        self.db.commit()
        
        # Test filtering by active status
        response = client.get("/api/v1/legal-holds?status=active")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Active Hold"
        assert data[0]["status"] == "active"

    def test_get_legal_hold_by_id(self):
        """Test getting specific legal hold by ID"""
        hold = LegalHold(
            hold_number="LH-20250823-TEST001",
            title="Test Hold",
            description="Test description",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(self.tenant_id)},
            created_by=self.user_id,
            status="active"
        )
        
        self.db.add(hold)
        self.db.commit()
        self.db.refresh(hold)
        
        response = client.get(f"/api/v1/legal-holds/{hold.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(hold.id)
        assert data["title"] == "Test Hold"
        assert data["description"] == "Test description"

    def test_get_legal_hold_not_found(self):
        """Test getting non-existent legal hold"""
        non_existent_id = uuid4()
        
        response = client.get(f"/api/v1/legal-holds/{non_existent_id}")
        
        assert response.status_code == 404
        assert "Legal hold not found" in response.text

    def test_update_legal_hold(self):
        """Test updating legal hold"""
        hold = LegalHold(
            hold_number="LH-20250823-TEST001",
            title="Original Title",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(self.tenant_id)},
            created_by=self.user_id,
            status="active"
        )
        
        self.db.add(hold)
        self.db.commit()
        self.db.refresh(hold)
        
        update_data = {
            "title": "Updated Title",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/v1/legal-holds/{hold.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated description"

    def test_release_legal_hold(self):
        """Test releasing a legal hold"""
        hold = LegalHold(
            hold_number="LH-20250823-TEST001",
            title="Hold to Release",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(self.tenant_id)},
            created_by=self.user_id,
            status="active"
        )
        
        self.db.add(hold)
        self.db.commit()
        self.db.refresh(hold)
        
        update_data = {"status": "released"}
        
        response = client.put(f"/api/v1/legal-holds/{hold.id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "released"


class TesteDiscoveryExports:
    """Test eDiscovery export functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.db = TestingSessionLocal()
        self.user_id = uuid4()
        self.hold_id = uuid4()
        
        # Create test hold
        self.test_hold = LegalHold(
            id=self.hold_id,
            hold_number="LH-20250823-TEST001",
            title="Test Hold for Export",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(uuid4())},
            created_by=self.user_id,
            status="active"
        )
        
        self.db.add(self.test_hold)
        self.db.commit()

    def teardown_method(self):
        """Cleanup after each test"""
        self.db.query(eDiscoveryExport).delete()
        self.db.query(LegalHold).delete()
        self.db.commit()
        self.db.close()

    def test_create_ediscovery_export(self):
        """Test creating eDiscovery export"""
        export_data = {
            "title": "Test Export",
            "description": "Export for litigation",
            "export_format": "structured_json",
            "include_metadata": True,
            "include_system_logs": True,
            "data_types": ["chat", "audit", "files"],
            "requesting_attorney": "John Doe, Esq."
        }
        
        with patch('app.routes.process_ediscovery_export') as mock_process:
            response = client.post(f"/api/v1/ediscovery/{self.hold_id}/exports", json=export_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == export_data["title"]
        assert data["status"] == "pending"
        assert "export_number" in data
        assert data["export_number"].startswith("ED-")
        
        # Verify background task was scheduled
        mock_process.assert_called_once()

    def test_create_export_invalid_format(self):
        """Test creating export with invalid format"""
        export_data = {
            "title": "Invalid Format Export",
            "export_format": "invalid_format",
            "data_types": ["chat"]
        }
        
        response = client.post(f"/api/v1/ediscovery/{self.hold_id}/exports", json=export_data)
        
        assert response.status_code == 422
        assert "Export format must be one of" in response.text

    def test_create_export_nonexistent_hold(self):
        """Test creating export for non-existent hold"""
        export_data = {
            "title": "Test Export",
            "export_format": "structured_json",
            "data_types": ["chat"]
        }
        
        non_existent_hold_id = uuid4()
        response = client.post(f"/api/v1/ediscovery/{non_existent_hold_id}/exports", json=export_data)
        
        assert response.status_code == 404
        assert "Legal hold not found" in response.text

    def test_list_exports_for_hold(self):
        """Test listing exports for a hold"""
        # Create test exports
        export1 = eDiscoveryExport(
            hold_id=self.hold_id,
            export_number="ED-20250823-TEST001",
            title="Export 1",
            export_format="structured_json",
            status="completed",
            requested_by=self.user_id
        )
        export2 = eDiscoveryExport(
            hold_id=self.hold_id,
            export_number="ED-20250823-TEST002",
            title="Export 2",
            export_format="pdf",
            status="pending",
            requested_by=self.user_id
        )
        
        self.db.add_all([export1, export2])
        self.db.commit()
        
        response = client.get(f"/api/v1/ediscovery/{self.hold_id}/exports")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["title"] in ["Export 1", "Export 2"]
        assert data[1]["title"] in ["Export 1", "Export 2"]


class TestComplianceIntegration:
    """Test compliance and retention override functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.db = TestingSessionLocal()
        self.tenant_id = uuid4()
        self.entity_id = str(uuid4())

    def teardown_method(self):
        """Cleanup after each test"""
        self.db.query(DataRetentionOverride).delete()
        self.db.query(HoldAffectedEntity).delete()
        self.db.query(LegalHold).delete()
        self.db.commit()
        self.db.close()

    def test_check_retention_override_exists(self):
        """Test checking for existing retention override"""
        # Create retention override
        override = DataRetentionOverride(
            entity_type="user_data",
            entity_id=self.entity_id,
            tenant_id=self.tenant_id,
            override_reason="legal_hold",
            override_reference="LH-20250823-TEST001",
            override_applied_by=uuid4(),
            is_active=True
        )
        
        self.db.add(override)
        self.db.commit()
        
        response = client.post("/api/v1/compliance/check-retention-override", json={
            "entity_type": "user_data",
            "entity_id": self.entity_id,
            "tenant_id": str(self.tenant_id)
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_override"] is True
        assert data["override_reason"] == "legal_hold"
        assert data["override_reference"] == "LH-20250823-TEST001"

    def test_check_retention_override_not_exists(self):
        """Test checking for non-existent retention override"""
        response = client.post("/api/v1/compliance/check-retention-override", json={
            "entity_type": "user_data",
            "entity_id": self.entity_id,
            "tenant_id": str(self.tenant_id)
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_override"] is False

    def test_block_deletion_attempt_with_hold(self):
        """Test blocking deletion attempt for entity under hold"""
        # Create hold and affected entity
        hold = LegalHold(
            hold_number="LH-20250823-TEST001",
            title="Test Hold",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(self.tenant_id)},
            created_by=uuid4(),
            status="active"
        )
        self.db.add(hold)
        self.db.flush()
        
        affected_entity = HoldAffectedEntity(
            hold_id=hold.id,
            entity_type="user_data",
            entity_id=self.entity_id,
            tenant_id=self.tenant_id,
            entity_name="Test User Data"
        )
        self.db.add(affected_entity)
        self.db.commit()
        
        response = client.post("/api/v1/compliance/block-deletion", json={
            "entity_type": "user_data",
            "entity_id": self.entity_id,
            "tenant_id": str(self.tenant_id),
            "attempted_by": str(uuid4())
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["deletion_blocked"] is True
        assert data["hold_id"] == str(hold.id)
        assert "legal hold" in data["message"]

    def test_block_deletion_attempt_no_hold(self):
        """Test deletion attempt for entity not under hold"""
        response = client.post("/api/v1/compliance/block-deletion", json={
            "entity_type": "user_data",
            "entity_id": self.entity_id,
            "tenant_id": str(self.tenant_id),
            "attempted_by": str(uuid4())
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["deletion_blocked"] is False


class TestAuditLogging:
    """Test audit logging functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.db = TestingSessionLocal()
        self.hold_id = uuid4()
        self.user_id = uuid4()
        
        # Create test hold
        hold = LegalHold(
            id=self.hold_id,
            hold_number="LH-20250823-TEST001",
            title="Test Hold for Audit",
            legal_basis="litigation",
            scope_type="tenant",
            scope_parameters={"tenant_id": str(uuid4())},
            created_by=self.user_id,
            status="active"
        )
        self.db.add(hold)
        self.db.commit()

    def teardown_method(self):
        """Cleanup after each test"""
        self.db.query(HoldAuditLog).delete()
        self.db.query(LegalHold).delete()
        self.db.commit()
        self.db.close()

    def test_get_hold_audit_logs(self):
        """Test retrieving audit logs for a hold"""
        # Create test audit logs
        log1 = HoldAuditLog(
            hold_id=self.hold_id,
            event_type="hold_created",
            event_description="Hold created",
            event_category="administrative",
            user_id=self.user_id,
            user_name="Test User",
            risk_level="medium"
        )
        log2 = HoldAuditLog(
            hold_id=self.hold_id,
            event_type="hold_accessed",
            event_description="Hold accessed",
            event_category="access",
            user_id=self.user_id,
            user_name="Test User",
            risk_level="low"
        )
        
        self.db.add_all([log1, log2])
        self.db.commit()
        
        response = client.get(f"/api/v1/audit/holds/{self.hold_id}/logs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        # Check that logs are returned in reverse chronological order
        assert data[0]["event_type"] in ["hold_created", "hold_accessed"]
        assert data[1]["event_type"] in ["hold_created", "hold_accessed"]
        
        # Verify log details
        for log in data:
            assert log["hold_id"] == str(self.hold_id)
            assert log["user_name"] == "Test User"
            assert log["risk_level"] in ["low", "medium"]

    def test_audit_log_creation_on_hold_access(self):
        """Test that audit log is created when accessing hold"""
        response = client.get(f"/api/v1/legal-holds/{self.hold_id}")
        
        assert response.status_code == 200
        
        # Verify audit log was created
        audit_logs = self.db.query(HoldAuditLog).filter(
            HoldAuditLog.hold_id == self.hold_id,
            HoldAuditLog.event_type == "hold_accessed"
        ).all()
        
        assert len(audit_logs) == 1
        assert audit_logs[0].event_description == f"Legal hold LH-20250823-TEST001 accessed"


class TestRetentionOverrides:
    """Test data retention override functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.db = TestingSessionLocal()

    def teardown_method(self):
        """Cleanup after each test"""
        self.db.query(DataRetentionOverride).delete()
        self.db.commit()
        self.db.close()

    def test_retention_override_prevents_deletion(self):
        """Test that retention override prevents data deletion"""
        entity_type = "chat_message"
        entity_id = str(uuid4())
        tenant_id = uuid4()
        
        # Create retention override
        override = DataRetentionOverride(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            override_reason="legal_hold",
            override_reference="LH-20250823-TEST001",
            override_applied_by=uuid4(),
            is_active=True,
            original_retention_days=30,
            original_deletion_date=datetime.now(timezone.utc) + timedelta(days=30)
        )
        
        self.db.add(override)
        self.db.commit()
        
        # Check override exists
        response = client.post("/api/v1/compliance/check-retention-override", json={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "tenant_id": str(tenant_id)
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_override"] is True
        assert data["override_reason"] == "legal_hold"

    def test_multiple_retention_overrides(self):
        """Test handling multiple retention overrides for same entity"""
        entity_type = "user_profile"
        entity_id = str(uuid4())
        tenant_id = uuid4()
        
        # Create multiple overrides (should be prevented by unique constraint)
        override1 = DataRetentionOverride(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            override_reason="legal_hold",
            override_reference="LH-20250823-TEST001",
            override_applied_by=uuid4(),
            is_active=True
        )
        
        override2 = DataRetentionOverride(
            entity_type=entity_type,
            entity_id=entity_id,
            tenant_id=tenant_id,
            override_reason="legal_hold",
            override_reference="LH-20250823-TEST002",  # Different reference
            override_applied_by=uuid4(),
            is_active=True
        )
        
        self.db.add(override1)
        self.db.commit()
        
        # Second override with different reference should be allowed
        self.db.add(override2)
        self.db.commit()
        
        # Query should return the first active override
        response = client.post("/api/v1/compliance/check-retention-override", json={
            "entity_type": entity_type,
            "entity_id": entity_id,
            "tenant_id": str(tenant_id)
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["has_override"] is True


# Integration tests

class TestServiceIntegration:
    """Test integration with other services"""

    def test_privacy_service_integration(self):
        """Test integration with privacy service for deletion blocking"""
        # This would test actual integration with privacy service
        # when it attempts to delete data that's under legal hold
        pass

    def test_audit_service_integration(self):
        """Test integration with audit service for log collection"""
        # This would test collection of audit logs from audit service
        # for eDiscovery exports
        pass

    def test_chat_service_integration(self):
        """Test integration with chat service for message preservation"""
        # This would test preservation of chat messages
        # and blocking deletion during legal holds
        pass

    def test_analytics_service_integration(self):
        """Test integration with analytics service for data masking"""
        # This would test that analytics writes are masked
        # for entities under legal hold
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
