"""
API integration tests for Private Foundation Model Orchestrator.
"""

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient

from tests.conftest import create_test_namespace_data, create_test_merge_request, create_test_fallback_request


class TestNamespaceAPI:
    """Test namespace-related API endpoints."""
    
    def test_create_namespace_success(self, test_client: TestClient, sample_namespace_data: dict):
        """Test successful namespace creation."""
        response = test_client.post("/api/v1/namespaces", json=sample_namespace_data)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "id" in data
        assert data["learner_id"] == sample_namespace_data["learner_id"]
        assert data["status"] == "active"
        assert data["base_fm_version"] == sample_namespace_data["base_fm_version"]
        assert data["version_count"] == 1
        assert "current_checkpoint_hash" in data
        assert "encryption_key_hash" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_namespace_invalid_data(self, test_client: TestClient):
        """Test namespace creation with invalid data."""
        invalid_data = {"learner_id": "invalid-uuid"}
        
        response = test_client.post("/api/v1/namespaces", json=invalid_data)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_create_duplicate_namespace_fails(self, test_client: TestClient):
        """Test that creating duplicate namespace fails."""
        namespace_data = create_test_namespace_data()
        
        # Create first namespace
        response1 = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert response1.status_code == status.HTTP_201_CREATED
        
        # Try to create duplicate
        response2 = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
        assert "already exists" in response2.json()["detail"]
    
    def test_get_namespace_success(self, test_client: TestClient):
        """Test successful namespace retrieval."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Get namespace
        response = test_client.get(f"/api/v1/namespaces/{learner_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["learner_id"] == learner_id
        assert data["status"] == "active"
        assert "id" in data
        assert "current_checkpoint_hash" in data
    
    def test_get_nonexistent_namespace_returns_404(self, test_client: TestClient):
        """Test getting non-existent namespace returns 404."""
        nonexistent_id = str(uuid4())
        
        response = test_client.get(f"/api/v1/namespaces/{nonexistent_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"]
    
    def test_list_namespaces(self, test_client: TestClient):
        """Test listing namespaces."""
        # Create a few namespaces
        for i in range(3):
            namespace_data = create_test_namespace_data()
            response = test_client.post("/api/v1/namespaces", json=namespace_data)
            assert response.status_code == status.HTTP_201_CREATED
        
        # List namespaces
        response = test_client.get("/api/v1/namespaces")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 3
        for namespace in data:
            assert "id" in namespace
            assert "learner_id" in namespace
            assert "status" in namespace
    
    def test_list_namespaces_with_filters(self, test_client: TestClient):
        """Test listing namespaces with status filter."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert response.status_code == status.HTTP_201_CREATED
        
        # List with filter
        response = test_client.get("/api/v1/namespaces?status_filter=active&limit=10&offset=0")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        for namespace in data:
            assert namespace["status"] == "active"
    
    def test_delete_namespace_success(self, test_client: TestClient):
        """Test successful namespace deletion."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Delete namespace
        response = test_client.delete(f"/api/v1/namespaces/{learner_id}")
        
        assert response.status_code == status.HTTP_204_NO_CONTENT
        
        # Verify it's gone
        get_response = test_client.get(f"/api/v1/namespaces/{learner_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_delete_nonexistent_namespace_returns_404(self, test_client: TestClient):
        """Test deleting non-existent namespace returns 404."""
        nonexistent_id = str(uuid4())
        
        response = test_client.delete(f"/api/v1/namespaces/{nonexistent_id}")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestHealthAPI:
    """Test health check API endpoints."""
    
    def test_basic_health_check(self, test_client: TestClient):
        """Test basic health check endpoint."""
        response = test_client.get("/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
    
    def test_detailed_health_check(self, test_client: TestClient):
        """Test detailed health check endpoint."""
        response = test_client.get("/health/detailed")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "status" in data
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
        assert "background_tasks" in data["checks"]
    
    def test_namespace_health_check(self, test_client: TestClient):
        """Test namespace health check endpoint."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Check health
        response = test_client.get(f"/api/v1/namespaces/{learner_id}/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "is_healthy" in data
        assert "integrity_score" in data
        assert "version_lag" in data
        assert "checkpoint_size_mb" in data
        assert "last_health_check" in data
        assert "issues" in data
        assert isinstance(data["issues"], list)


class TestMergeAPI:
    """Test merge operation API endpoints."""
    
    def test_trigger_merge_success(self, test_client: TestClient):
        """Test successful merge trigger."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Trigger merge
        merge_request = create_test_merge_request()
        response = test_client.post(f"/api/v1/namespaces/{learner_id}/merge", json=merge_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "id" in data
        assert "namespace_id" in data
        assert data["operation_type"] == merge_request["operation_type"]
        assert data["status"] == "pending"
        assert "source_checkpoint_hash" in data
        assert "created_at" in data
    
    def test_trigger_merge_nonexistent_namespace_fails(self, test_client: TestClient):
        """Test triggering merge on non-existent namespace fails."""
        nonexistent_id = str(uuid4())
        merge_request = create_test_merge_request()
        
        response = test_client.post(f"/api/v1/namespaces/{nonexistent_id}/merge", json=merge_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"]
    
    def test_list_merge_operations(self, test_client: TestClient):
        """Test listing merge operations for a namespace."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Trigger a merge
        merge_request = create_test_merge_request()
        merge_response = test_client.post(f"/api/v1/namespaces/{learner_id}/merge", json=merge_request)
        assert merge_response.status_code == status.HTTP_200_OK
        
        # List merge operations
        response = test_client.get(f"/api/v1/namespaces/{learner_id}/merge-operations")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["operation_type"] == merge_request["operation_type"]
    
    def test_get_merge_operation_details(self, test_client: TestClient):
        """Test getting merge operation details."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Trigger merge
        merge_request = create_test_merge_request()
        merge_response = test_client.post(f"/api/v1/namespaces/{learner_id}/merge", json=merge_request)
        assert merge_response.status_code == status.HTTP_200_OK
        
        operation_id = merge_response.json()["id"]
        
        # Get merge operation details
        response = test_client.get(f"/api/v1/merge-operations/{operation_id}")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == operation_id
        assert data["operation_type"] == merge_request["operation_type"]
        assert "status" in data
        assert "created_at" in data


class TestFallbackAPI:
    """Test fallback recovery API endpoints."""
    
    def test_initiate_fallback_recovery(self, test_client: TestClient):
        """Test initiating fallback recovery."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Initiate fallback
        fallback_request = create_test_fallback_request()
        response = test_client.post(f"/api/v1/namespaces/{learner_id}/fallback", json=fallback_request)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "operation_id" in data
        assert "message" in data
        assert data["reason"] == fallback_request["reason"]
        assert "timestamp" in data
    
    def test_initiate_fallback_nonexistent_namespace_fails(self, test_client: TestClient):
        """Test initiating fallback on non-existent namespace fails."""
        nonexistent_id = str(uuid4())
        fallback_request = create_test_fallback_request()
        
        response = test_client.post(f"/api/v1/namespaces/{nonexistent_id}/fallback", json=fallback_request)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not found" in response.json()["detail"]


class TestEventAPI:
    """Test event and audit API endpoints."""
    
    def test_get_namespace_events(self, test_client: TestClient):
        """Test getting namespace events."""
        # Create namespace (this generates events)
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Get events
        response = test_client.get(f"/api/v1/namespaces/{learner_id}/events")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        # Should have at least a creation event
        assert len(data) >= 1
        
        for event in data:
            assert "id" in event
            assert "namespace_id" in event
            assert "learner_id" in event
            assert "event_type" in event
            assert "event_data" in event
            assert "created_at" in event
    
    def test_get_namespace_events_with_filter(self, test_client: TestClient):
        """Test getting namespace events with event type filter."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Get events with filter
        response = test_client.get(f"/api/v1/namespaces/{learner_id}/events?event_type=namespace_created&limit=10")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert isinstance(data, list)
        for event in data:
            assert event["event_type"] == "namespace_created"


class TestStatsAPI:
    """Test statistics and analytics API endpoints."""
    
    def test_get_namespace_stats(self, test_client: TestClient):
        """Test getting namespace statistics."""
        # Create namespace
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        learner_id = namespace_data["learner_id"]
        
        # Get stats
        response = test_client.get(f"/api/v1/namespaces/{learner_id}/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "namespace_id" in data
        assert "learner_id" in data
        assert data["learner_id"] == learner_id
        assert "status" in data
        assert "version_count" in data
        assert "uptime_hours" in data
        assert "merge_operations" in data
        assert "events" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_get_global_stats(self, test_client: TestClient):
        """Test getting global orchestrator statistics."""
        # Create a namespace to have some data
        namespace_data = create_test_namespace_data()
        create_response = test_client.post("/api/v1/namespaces", json=namespace_data)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        # Get global stats
        response = test_client.get("/api/v1/stats/global")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "total_namespaces" in data
        assert "namespace_status_distribution" in data
        assert "total_merge_operations" in data
        assert "merge_status_distribution" in data
        assert "recent_activity_24h" in data
        assert "timestamp" in data
        
        # Should have at least one namespace now
        assert data["total_namespaces"] >= 1


class TestAdminAPI:
    """Test administrative API endpoints."""
    
    def test_trigger_nightly_merge_job(self, test_client: TestClient):
        """Test triggering nightly merge job manually."""
        response = test_client.post("/admin/jobs/nightly-merge")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "timestamp" in data
        assert "triggered" in data["message"]
    
    def test_trigger_health_check_job(self, test_client: TestClient):
        """Test triggering health check job manually."""
        response = test_client.post("/admin/jobs/health-check")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "timestamp" in data
    
    def test_trigger_cleanup_job(self, test_client: TestClient):
        """Test triggering cleanup job manually."""
        response = test_client.post("/admin/jobs/cleanup")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "timestamp" in data
    
    def test_get_admin_stats(self, test_client: TestClient):
        """Test getting administrative statistics."""
        response = test_client.get("/admin/stats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "database" in data
        assert "queues" in data
        assert "memory" in data
        assert "background_tasks" in data
        
        # Database stats
        assert "total_namespaces" in data["database"]
        assert "status_distribution" in data["database"]
        assert "total_merge_operations" in data["database"]
        assert "total_event_logs" in data["database"]
        
        # Queue stats
        assert "merge_queue_size" in data["queues"]
        assert "fallback_queue_size" in data["queues"]


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_invalid_uuid_parameters(self, test_client: TestClient):
        """Test handling of invalid UUID parameters."""
        invalid_uuid = "not-a-uuid"
        
        # Test various endpoints with invalid UUID
        endpoints = [
            f"/api/v1/namespaces/{invalid_uuid}",
            f"/api/v1/namespaces/{invalid_uuid}/health",
            f"/api/v1/namespaces/{invalid_uuid}/merge",
            f"/api/v1/merge-operations/{invalid_uuid}"
        ]
        
        for endpoint in endpoints:
            response = test_client.get(endpoint)
            assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]
    
    def test_large_request_handling(self, test_client: TestClient):
        """Test handling of unusually large requests."""
        # Create namespace data with very large configuration
        large_config = {"large_field": "x" * 10000}  # 10KB string
        namespace_data = create_test_namespace_data(configuration=large_config)
        
        response = test_client.post("/api/v1/namespaces", json=namespace_data)
        
        # Should either succeed or fail gracefully
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            status.HTTP_400_BAD_REQUEST
        ]
    
    def test_concurrent_api_requests(self, test_client: TestClient):
        """Test handling of concurrent API requests."""
        # This would be more effective with actual concurrent testing,
        # but we can at least verify that rapid sequential requests work
        
        namespace_data_list = [create_test_namespace_data() for _ in range(5)]
        
        responses = []
        for data in namespace_data_list:
            response = test_client.post("/api/v1/namespaces", json=data)
            responses.append(response)
        
        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_201_CREATED
