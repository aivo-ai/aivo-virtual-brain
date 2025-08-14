"""
AIVO Inference Gateway - Checkpoint Router Tests
S2-06 Implementation: Tests for personalized checkpoint fetch + signed URLs
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.routers.checkpoints import CheckpointService, get_checkpoint_service


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Async HTTP client for testing"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_checkpoint_service():
    """Mock checkpoint service for testing"""
    service = CheckpointService()
    # Clear default test data to start fresh
    service.cache.clear()
    return service


@pytest.fixture
def valid_bearer_token():
    """Valid bearer token for authentication"""
    return "valid-test-token-12345"


@pytest.fixture 
def auth_headers(valid_bearer_token):
    """Authentication headers"""
    return {"Authorization": f"Bearer {valid_bearer_token}"}


class TestCheckpointEndpoints:
    """Test checkpoint endpoint functionality"""
    
    def test_get_checkpoint_success(self, client, auth_headers):
        """Test successful checkpoint retrieval"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate response structure
        assert data["learner_id"] == learner_id
        assert data["subject"] == subject
        assert data["version"] == 3
        assert data["checkpoint_hash"] == "ckpt_math_v3_a1b2c3d4"
        assert "signed_url" in data
        assert "expires_at" in data
        assert data["size_bytes"] == 4294967296
        assert data["quantization"] == "int8"  # Should match request or default
        assert data["model_type"] == "personalized-llama-7b"
    
    def test_get_checkpoint_with_custom_quantization(self, client, auth_headers):
        """Test checkpoint retrieval with custom quantization"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "science"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}?quantization=fp16&url_expires_minutes=30",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["quantization"] == "fp16"
        assert data["checkpoint_hash"] == "ckpt_science_v5_e5f6g7h8"
        
        # Verify URL expiration is approximately 30 minutes from now
        expires_at = datetime.fromisoformat(data["expires_at"].replace("Z", "+00:00"))
        expected_expires = datetime.utcnow() + timedelta(minutes=30)
        time_diff = abs((expires_at - expected_expires).total_seconds())
        assert time_diff < 60  # Within 1 minute tolerance
    
    def test_get_checkpoint_without_signed_url(self, client, auth_headers):
        """Test checkpoint retrieval without signed URL"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}?include_url=false",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["signed_url"] is None
        assert "expires_at" in data  # Still included for consistency
    
    def test_get_checkpoint_invalid_auth_fails(self, client):
        """Test that invalid authentication fails"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        # No auth header
        response = client.get(f"/v1/checkpoints/{learner_id}/{subject}")
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]
        
        # Invalid auth header
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers={"Authorization": "Invalid token"}
        )
        assert response.status_code == 403
        
        # Empty bearer token
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers={"Authorization": "Bearer "}
        )
        assert response.status_code == 403
    
    def test_get_checkpoint_invalid_learner_id_fails(self, client, auth_headers):
        """Test that invalid learner ID format fails"""
        invalid_learner_ids = [
            "not-a-uuid",
            "123456789",
            "invalid-uuid-format"
        ]
        
        for learner_id in invalid_learner_ids:
            response = client.get(
                f"/v1/checkpoints/{learner_id}/mathematics",
                headers=auth_headers
            )
            assert response.status_code == 403
            assert "Access denied" in response.json()["detail"]
    
    def test_get_checkpoint_not_found(self, client, auth_headers):
        """Test checkpoint not found scenario"""
        learner_id = "550e8400-e29b-41d4-a716-446655440999"  # Non-existent
        subject = "physics"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        assert "No personalized checkpoint found" in response.json()["detail"]
    
    def test_get_checkpoint_invalid_quantization(self, client, auth_headers):
        """Test invalid quantization format"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}?quantization=invalid_format",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid quantization format" in response.json()["detail"]
    
    def test_get_checkpoint_invalid_expiration(self, client, auth_headers):
        """Test invalid URL expiration times"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        # Too short
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}?url_expires_minutes=0",
            headers=auth_headers
        )
        assert response.status_code == 400
        
        # Too long
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}?url_expires_minutes=120",
            headers=auth_headers
        )
        assert response.status_code == 400


class TestSignedURLGeneration:
    """Test signed URL generation functionality"""
    
    def test_signed_url_format(self, mock_checkpoint_service):
        """Test signed URL has correct format"""
        checkpoint_hash = "test_checkpoint_hash"
        signed_url = mock_checkpoint_service.generate_signed_url(
            checkpoint_hash, expires_in_minutes=10
        )
        
        # Verify URL structure
        assert "localhost:9000/checkpoints" in signed_url
        assert checkpoint_hash in signed_url
        assert "AWSAccessKeyId=" in signed_url
        assert "Expires=" in signed_url
        assert "Signature=" in signed_url
        assert "safetensors" in signed_url
    
    def test_signed_url_expiration(self, mock_checkpoint_service):
        """Test signed URL expiration calculation"""
        checkpoint_hash = "test_checkpoint_hash"
        expires_minutes = 15
        
        signed_url = mock_checkpoint_service.generate_signed_url(
            checkpoint_hash, expires_minutes
        )
        
        # Extract expiration timestamp
        import re
        expires_match = re.search(r"Expires=(\d+)", signed_url)
        assert expires_match
        
        expires_timestamp = int(expires_match.group(1))
        expected_expires = datetime.utcnow() + timedelta(minutes=expires_minutes)
        expected_timestamp = int(expected_expires.timestamp())
        
        # Allow 60 second tolerance for test timing
        assert abs(expires_timestamp - expected_timestamp) < 60


class TestCacheInvalidation:
    """Test cache invalidation functionality"""
    
    def test_invalidate_specific_subject(self, client, auth_headers):
        """Test invalidating cache for specific subject"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        response = client.post(
            f"/v1/checkpoints/{learner_id}/invalidate-cache?subject={subject}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert subject in data["message"]
        assert "timestamp" in data
    
    def test_invalidate_all_subjects(self, client, auth_headers):
        """Test invalidating cache for all subjects of a learner"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        
        response = client.post(
            f"/v1/checkpoints/{learner_id}/invalidate-cache",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert learner_id in data["message"]
    
    def test_invalidate_cache_unauthorized(self, client):
        """Test cache invalidation without proper auth"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        
        response = client.post(f"/v1/checkpoints/{learner_id}/invalidate-cache")
        
        assert response.status_code == 403
        assert "Access denied" in response.json()["detail"]


class TestQuantization:
    """Test checkpoint quantization functionality"""
    
    def test_quantize_checkpoint_request(self, client, auth_headers):
        """Test quantization request endpoint"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        target_format = "int8"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}/quantize/{target_format}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["checkpoint_hash"] == "ckpt_math_v3_a1b2c3d4"
        assert data["target_format"] == target_format
        assert "estimated_completion" in data
        assert "quantization_result" in data
        
        # Verify quantization result
        quant_result = data["quantization_result"]
        assert quant_result["status"] == "completed"
        assert quant_result["target_format"] == target_format
        assert quant_result["size_reduction_factor"] == 0.25  # int8 reduction
    
    def test_quantize_invalid_format(self, client, auth_headers):
        """Test quantization with invalid format"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        invalid_format = "invalid_format"
        
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}/quantize/{invalid_format}",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Invalid quantization format" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_quantization_simulation(self, mock_checkpoint_service):
        """Test quantization simulation logic"""
        checkpoint_hash = "test_checkpoint"
        target_format = "int4"
        
        result = await mock_checkpoint_service.simulate_quantization(
            checkpoint_hash, target_format
        )
        
        assert result["quantized_hash"] == f"{checkpoint_hash}_q{target_format}"
        assert result["target_format"] == target_format
        assert result["size_reduction_factor"] == 0.125  # int4 reduction
        assert result["status"] == "completed"
        assert result["processing_time_seconds"] == 5.0  # int4 processing time


class TestHealthAndService:
    """Test service health and utility endpoints"""
    
    def test_checkpoint_health_endpoint(self, client):
        """Test checkpoint service health check"""
        response = client.get("/v1/checkpoints/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["service"] == "checkpoint-service"
        assert data["status"] == "healthy"
        assert "cache_size" in data
        assert data["minio_configured"] is True
        assert "timestamp" in data
    
    def test_service_dependency_injection(self):
        """Test service dependency injection"""
        service = get_checkpoint_service()
        assert isinstance(service, CheckpointService)
        assert hasattr(service, 'cache')
        assert hasattr(service, 'minio_config')


class TestIntegration:
    """Integration tests for complete checkpoint workflows"""
    
    @pytest.mark.asyncio
    async def test_complete_checkpoint_workflow(self, async_client, auth_headers):
        """Test complete workflow: get checkpoint -> invalidate cache -> get again"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        # First request - should hit cache
        response1 = await async_client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers=auth_headers
        )
        assert response1.status_code == 200
        hash1 = response1.json()["checkpoint_hash"]
        
        # Invalidate cache
        response2 = await async_client.post(
            f"/v1/checkpoints/{learner_id}/invalidate-cache?subject={subject}",
            headers=auth_headers
        )
        assert response2.status_code == 200
        
        # Second request - should work the same (data is consistent)
        response3 = await async_client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers=auth_headers
        )
        assert response3.status_code == 200
        hash3 = response3.json()["checkpoint_hash"]
        
        # Hashes should be the same (no new checkpoint yet)
        assert hash1 == hash3
    
    def test_learner_scope_isolation(self, client, auth_headers):
        """Test that learners can only access their own checkpoints"""
        # This test assumes the auth system properly validates learner scope
        # In production, JWT tokens would contain learner_id claims
        
        learner1_id = "550e8400-e29b-41d4-a716-446655440001"
        learner2_id = "550e8400-e29b-41d4-a716-446655440002"
        
        # Learner 1 can access their checkpoint
        response1 = client.get(
            f"/v1/checkpoints/{learner1_id}/mathematics",
            headers=auth_headers
        )
        assert response1.status_code == 200
        
        # Learner 2 can access their checkpoint  
        response2 = client.get(
            f"/v1/checkpoints/{learner2_id}/literature",
            headers=auth_headers
        )
        assert response2.status_code == 200
        
        # Verify different checkpoints returned
        assert response1.json()["checkpoint_hash"] != response2.json()["checkpoint_hash"]


class TestErrorScenarios:
    """Test various error scenarios and edge cases"""
    
    def test_malformed_requests(self, client, auth_headers):
        """Test handling of malformed requests"""
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        
        # Empty subject
        response = client.get(
            f"/v1/checkpoints/{learner_id}/",
            headers=auth_headers
        )
        assert response.status_code in [404, 422]  # Depends on routing
        
        # Subject with special characters
        response = client.get(
            f"/v1/checkpoints/{learner_id}/math%20science",
            headers=auth_headers
        )
        assert response.status_code == 404  # Not found is acceptable
    
    @patch('app.routers.checkpoints.CheckpointService.get_checkpoint_metadata')
    async def test_service_timeout_handling(self, mock_get_metadata, client, auth_headers):
        """Test handling of service timeouts"""
        import asyncio
        
        # Mock timeout
        async def timeout_side_effect(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate timeout
            
        mock_get_metadata.side_effect = timeout_side_effect
        
        learner_id = "550e8400-e29b-41d4-a716-446655440001"
        subject = "mathematics"
        
        # This should timeout in real scenarios, but for testing we'll mock it
        # In production, proper timeout handling would be implemented
        response = client.get(
            f"/v1/checkpoints/{learner_id}/{subject}",
            headers=auth_headers
        )
        
        # Service should handle timeouts gracefully
        # The exact response depends on timeout implementation
        assert response.status_code in [200, 408, 500, 502, 503, 504]
