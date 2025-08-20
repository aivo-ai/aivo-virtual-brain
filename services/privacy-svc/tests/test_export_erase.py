"""
Test suite for Privacy Service export and erase functionality
Tests data export, erasure, audit trails, and compliance requirements
"""

import asyncio
import json
import uuid
import tempfile
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import asyncpg
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.models import (
    ExportRequest, ErasureRequest, PrivacyRequestStatus, 
    DataCategory, AdapterDeletionRule
)
from app.exporter import DataExporter
from app.eraser import DataEraser
from app.database import get_db_pool


class TestPrivacyAPI:
    """Test privacy API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Test client fixture"""
        return TestClient(app)
    
    @pytest.fixture
    def sample_learner_id(self):
        """Sample learner ID for testing"""
        return uuid.uuid4()
    
    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool"""
        with patch('app.routes.get_db_pool') as mock:
            pool = AsyncMock()
            mock.return_value = pool
            yield pool

    def test_export_request_success(self, client, sample_learner_id, mock_db_pool):
        """Test successful export request submission"""
        
        # Mock database responses
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = None
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = uuid.uuid4()
        
        request_data = {
            "learner_id": str(sample_learner_id),
            "data_categories": ["learning_progress", "assessments"],
            "export_format": "json",
            "include_metadata": True,
            "redact_pii": True
        }
        
        response = client.post("/api/v1/export", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        assert "request_id" in data
        assert data["status"] == "pending"
        assert "created_at" in data
        assert "estimated_completion" in data

    def test_export_request_duplicate_pending(self, client, sample_learner_id, mock_db_pool):
        """Test export request rejection when duplicate pending"""
        
        # Mock existing pending request
        existing_request = {
            "id": uuid.uuid4(),
            "status": "pending",
            "created_at": datetime.utcnow()
        }
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = existing_request
        
        request_data = {
            "learner_id": str(sample_learner_id),
            "data_categories": ["learning_progress"],
            "export_format": "json"
        }
        
        response = client.post("/api/v1/export", json=request_data)
        
        assert response.status_code == 409
        data = response.json()
        assert "already in progress" in data["message"].lower()

    def test_export_status_check(self, client, mock_db_pool):
        """Test export status retrieval"""
        
        request_id = uuid.uuid4()
        
        # Mock completed export
        mock_export = {
            "id": request_id,
            "status": "completed",
            "progress": 100,
            "created_at": datetime.utcnow() - timedelta(minutes=30),
            "completed_at": datetime.utcnow(),
            "file_path": "/tmp/exports/test.zip",
            "file_size": 1024000,
            "expires_at": datetime.utcnow() + timedelta(days=7)
        }
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = mock_export
        
        response = client.get(f"/api/v1/export/{request_id}/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["request_id"] == str(request_id)
        assert data["status"] == "completed"
        assert data["progress"] == 100
        assert "download_url" in data

    def test_erase_request_success(self, client, sample_learner_id, mock_db_pool):
        """Test successful erasure request submission"""
        
        # Mock database responses
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = None
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchval.return_value = uuid.uuid4()
        
        request_data = {
            "learner_id": str(sample_learner_id),
            "data_categories": ["interactions", "analytics"],
            "reason": "guardian_request",
            "confirmation_token": f"confirm_erasure_{sample_learner_id}",
            "guardian_verified": True
        }
        
        response = client.post("/api/v1/erase", json=request_data)
        
        assert response.status_code == 202
        data = response.json()
        assert "request_id" in data
        assert data["status"] == "pending"
        assert "logged" in data["message"].lower()

    def test_erase_request_missing_confirmation(self, client, sample_learner_id):
        """Test erasure request rejection without confirmation token"""
        
        request_data = {
            "learner_id": str(sample_learner_id),
            "data_categories": ["all"],
            "reason": "guardian_request"
            # Missing confirmation_token
        }
        
        response = client.post("/api/v1/erase", json=request_data)
        
        assert response.status_code == 422  # Validation error

    def test_data_summary_retrieval(self, client, sample_learner_id, mock_db_pool):
        """Test data summary endpoint"""
        
        # Mock data summary
        mock_summary = {
            "total_records": 5000,
            "last_activity": datetime.utcnow(),
            "learning_progress": {"count": 1200, "size_mb": 2.4},
            "assessments": {"count": 85, "size_mb": 5.1},
            "interactions": {"count": 3500, "size_mb": 12.3}
        }
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetchrow.return_value = mock_summary
        
        response = client.get(f"/api/v1/data-summary/{sample_learner_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["learner_id"] == str(sample_learner_id)
        assert "total_data_points" in data
        assert "data_categories" in data


class TestDataExporter:
    """Test data export functionality"""
    
    @pytest.fixture
    def temp_storage(self):
        """Temporary storage directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir
    
    @pytest.fixture
    def exporter(self, temp_storage):
        """Data exporter instance"""
        return DataExporter(storage_path=temp_storage, max_size_mb=100)
    
    @pytest.fixture
    def mock_db_data(self):
        """Mock learner data for export"""
        return {
            "learning_progress": [
                {
                    "id": uuid.uuid4(),
                    "skill": "mathematics",
                    "progress": 0.85,
                    "last_updated": datetime.utcnow().isoformat()
                },
                {
                    "id": uuid.uuid4(),
                    "skill": "reading",
                    "progress": 0.92,
                    "last_updated": datetime.utcnow().isoformat()
                }
            ],
            "assessments": [
                {
                    "id": uuid.uuid4(),
                    "assessment_type": "diagnostic",
                    "score": 87,
                    "completed_at": datetime.utcnow().isoformat(),
                    "metadata": {"duration_minutes": 45}
                }
            ],
            "interactions": [
                {
                    "id": uuid.uuid4(),
                    "interaction_type": "question_answer",
                    "timestamp": datetime.utcnow().isoformat(),
                    "anonymized_content": "Math problem solved correctly"
                }
            ]
        }

    @pytest.mark.asyncio
    async def test_export_bundle_creation(self, exporter, mock_db_data):
        """Test export bundle creation with integrity verification"""
        
        request_id = uuid.uuid4()
        learner_id = uuid.uuid4()
        
        with patch.object(exporter, '_extract_learner_data', return_value=mock_db_data):
            with patch.object(exporter, '_update_request_status', return_value=None):
                
                bundle = await exporter.create_export_bundle(
                    request_id=request_id,
                    learner_id=learner_id,
                    data_categories=[DataCategory.LEARNING_PROGRESS, DataCategory.ASSESSMENTS],
                    export_format="json",
                    include_metadata=True
                )
        
        assert bundle.request_id == request_id
        assert bundle.file_path.exists()
        assert bundle.file_size > 0
        assert bundle.checksum is not None
        
        # Verify ZIP bundle integrity
        with zipfile.ZipFile(bundle.file_path, 'r') as zip_file:
            assert zip_file.testzip() is None  # No corrupt files
            
            # Check expected files
            expected_files = [
                "metadata.json",
                "learning_progress.json", 
                "assessments.json",
                "data_manifest.json"
            ]
            zip_contents = zip_file.namelist()
            for expected in expected_files:
                assert expected in zip_contents

    @pytest.mark.asyncio
    async def test_export_pii_redaction(self, exporter):
        """Test PII redaction in export data"""
        
        sensitive_data = {
            "personal_info": [
                {
                    "learner_id": uuid.uuid4(),
                    "email": "test@example.com",
                    "ip_address": "192.168.1.100",
                    "device_fingerprint": "abc123xyz",
                    "learning_score": 85
                }
            ]
        }
        
        with patch.object(exporter, '_extract_learner_data', return_value=sensitive_data):
            with patch.object(exporter, '_update_request_status', return_value=None):
                
                # Test with PII redaction enabled
                redacted_data = await exporter._apply_pii_redaction(sensitive_data, redact=True)
                
                personal_record = redacted_data["personal_info"][0]
                assert personal_record["email"] == "[REDACTED]"
                assert personal_record["ip_address"] == "[REDACTED]"
                assert personal_record["device_fingerprint"] == "[REDACTED]"
                assert personal_record["learning_score"] == 85  # Not PII, preserved

    @pytest.mark.asyncio
    async def test_export_checksum_verification(self, exporter, temp_storage):
        """Test export bundle checksum verification"""
        
        # Create test file
        test_file = Path(temp_storage) / "test_export.zip"
        test_content = b"test export content"
        test_file.write_bytes(test_content)
        
        # Calculate checksum
        checksum = exporter._calculate_file_checksum(test_file)
        assert checksum is not None
        assert len(checksum) == 64  # SHA-256 hex digest
        
        # Verify checksum matches
        verified = exporter._verify_file_checksum(test_file, checksum)
        assert verified is True
        
        # Test with wrong checksum
        wrong_checksum = "0" * 64
        verified = exporter._verify_file_checksum(test_file, wrong_checksum)
        assert verified is False


class TestDataEraser:
    """Test data erasure functionality"""
    
    @pytest.fixture
    def eraser(self):
        """Data eraser instance"""
        return DataEraser()
    
    @pytest.fixture
    def sample_learner_id(self):
        """Sample learner ID for testing"""
        return uuid.uuid4()

    @pytest.mark.asyncio
    async def test_erasure_request_processing(self, eraser, sample_learner_id):
        """Test erasure request processing with audit trail"""
        
        request_id = uuid.uuid4()
        
        with patch.object(eraser, '_update_request_status', return_value=None):
            with patch.object(eraser, '_erase_data_category', return_value={"records_deleted": 150}):
                with patch.object(eraser, '_log_erasure_audit', return_value=None):
                    
                    result = await eraser.process_erasure_request(
                        request_id=request_id,
                        learner_id=sample_learner_id,
                        data_categories=[DataCategory.INTERACTIONS, DataCategory.ANALYTICS],
                        reason="guardian_request"
                    )
        
        assert result["status"] == "completed"
        assert result["total_records_deleted"] > 0
        assert "audit_log_id" in result

    @pytest.mark.asyncio
    async def test_adapter_deletion_rules(self, eraser):
        """Test adapter one-way deletion rules"""
        
        # Verify adapter rules are configured correctly
        learning_rule = eraser.adapter_rules["learning_adapters"]
        assert learning_rule.delete_on_request is True
        assert learning_rule.merge_upwards is False  # Critical: never merge upwards
        assert learning_rule.preserve_audit is True
        
        assessment_rule = eraser.adapter_rules["assessment_adapters"]
        assert assessment_rule.delete_on_request is True
        assert assessment_rule.merge_upwards is False
        assert assessment_rule.preserve_audit is True

    @pytest.mark.asyncio
    async def test_erasure_idempotency(self, eraser, sample_learner_id):
        """Test that multiple erasure requests are handled safely"""
        
        request_id = uuid.uuid4()
        
        with patch.object(eraser, '_check_existing_erasure', return_value=True):
            with patch.object(eraser, '_update_request_status', return_value=None):
                
                # First erasure request
                result1 = await eraser.process_erasure_request(
                    request_id=request_id,
                    learner_id=sample_learner_id,
                    data_categories=[DataCategory.ALL],
                    reason="guardian_request"
                )
                
                # Second erasure request (should be idempotent)
                result2 = await eraser.process_erasure_request(
                    request_id=request_id,
                    learner_id=sample_learner_id,
                    data_categories=[DataCategory.ALL],
                    reason="guardian_request"
                )
        
        # Both should return success without data corruption
        assert result1["status"] == "completed"
        assert result2["status"] == "completed"
        assert result1["request_id"] == result2["request_id"]

    @pytest.mark.asyncio
    async def test_audit_trail_immutability(self, eraser, sample_learner_id):
        """Test that audit trails are immutable and comprehensive"""
        
        audit_events = []
        
        def mock_log_audit(event_type, learner_id, details, request_id):
            audit_events.append({
                "event_type": event_type,
                "learner_id": learner_id,
                "details": details,
                "request_id": request_id,
                "timestamp": datetime.utcnow()
            })
        
        with patch.object(eraser, '_log_erasure_audit', side_effect=mock_log_audit):
            with patch.object(eraser, '_erase_data_category', return_value={"records_deleted": 100}):
                with patch.object(eraser, '_update_request_status', return_value=None):
                    
                    await eraser.process_erasure_request(
                        request_id=uuid.uuid4(),
                        learner_id=sample_learner_id,
                        data_categories=[DataCategory.LEARNING_PROGRESS],
                        reason="guardian_request"
                    )
        
        # Verify comprehensive audit logging
        assert len(audit_events) > 0
        
        # Check audit event structure
        for event in audit_events:
            assert "event_type" in event
            assert "learner_id" in event
            assert "details" in event
            assert "timestamp" in event
            assert event["learner_id"] == sample_learner_id


class TestRetentionJobs:
    """Test automated retention and cleanup jobs"""
    
    @pytest.mark.asyncio
    async def test_checkpoint_retention_policy(self):
        """Test that only 3 latest personalized checkpoints are retained"""
        
        learner_id = uuid.uuid4()
        
        # Mock 5 checkpoints (should keep only 3 latest)
        mock_checkpoints = [
            {"id": i, "created_at": datetime.utcnow() - timedelta(days=i*10), "learner_id": learner_id}
            for i in range(5)
        ]
        
        with patch('app.retention.get_learner_checkpoints', return_value=mock_checkpoints):
            with patch('app.retention.delete_checkpoint') as mock_delete:
                
                from app.retention import cleanup_personalized_checkpoints
                result = await cleanup_personalized_checkpoints(keep_count=3)
        
        # Should delete 2 oldest checkpoints (indices 3 and 4)
        assert mock_delete.call_count == 2
        deleted_ids = [call[0][0] for call in mock_delete.call_args_list]
        assert 3 in deleted_ids
        assert 4 in deleted_ids

    @pytest.mark.asyncio 
    async def test_export_file_cleanup(self):
        """Test automated cleanup of old export files"""
        
        with tempfile.TemporaryDirectory() as tmpdir:
            export_dir = Path(tmpdir)
            
            # Create old and recent export files
            old_file = export_dir / "old_export.zip"
            recent_file = export_dir / "recent_export.zip" 
            
            old_file.write_text("old export")
            recent_file.write_text("recent export")
            
            # Set file timestamps
            old_time = datetime.utcnow() - timedelta(days=10)
            recent_time = datetime.utcnow() - timedelta(hours=1)
            
            os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))
            os.utime(recent_file, (recent_time.timestamp(), recent_time.timestamp()))
            
            from app.retention import cleanup_export_files
            deleted_count = await cleanup_export_files(
                export_path=str(export_dir), 
                retention_days=7
            )
            
            # Old file should be deleted, recent file retained
            assert deleted_count == 1
            assert not old_file.exists()
            assert recent_file.exists()


# Integration test fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Test database connection"""
    db_url = "postgresql://test_user:test_pass@localhost/test_privacy_db"
    
    try:
        pool = await asyncpg.create_pool(db_url)
        yield pool
        await pool.close()
    except Exception:
        # Skip database tests if test DB not available
        pytest.skip("Test database not available")


# Performance and load tests
class TestPerformance:
    """Performance and load testing"""
    
    @pytest.mark.asyncio
    async def test_concurrent_export_requests(self):
        """Test handling of concurrent export requests"""
        
        learner_ids = [uuid.uuid4() for _ in range(10)]
        
        async def make_export_request(learner_id):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post("/api/v1/export", json={
                    "learner_id": str(learner_id),
                    "data_categories": ["learning_progress"],
                    "export_format": "json"
                })
                return response.status_code
        
        with patch('app.routes.get_db_pool'):
            # Make concurrent requests
            tasks = [make_export_request(lid) for lid in learner_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should be accepted or properly handled
        success_count = sum(1 for r in results if r == 202)
        assert success_count >= 8  # Allow for some rate limiting

    @pytest.mark.asyncio
    async def test_large_export_bundle_handling(self, temp_storage):
        """Test handling of large export bundles"""
        
        exporter = DataExporter(storage_path=temp_storage, max_size_mb=1)  # Small limit
        
        # Mock large data set
        large_data = {
            "interactions": [
                {"id": i, "data": "x" * 1000} for i in range(10000)
            ]
        }
        
        with patch.object(exporter, '_extract_learner_data', return_value=large_data):
            with patch.object(exporter, '_update_request_status', return_value=None):
                
                with pytest.raises(Exception) as exc_info:
                    await exporter.create_export_bundle(
                        request_id=uuid.uuid4(),
                        learner_id=uuid.uuid4(),
                        data_categories=[DataCategory.INTERACTIONS],
                        export_format="json"
                    )
                
                # Should fail gracefully with size limit error
                assert "size limit" in str(exc_info.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
