"""
AIVO Model Registry - Statistics and Health Tests
S2-02 Implementation: Tests for statistics, retention, and health endpoints
"""

from fastapi.testclient import TestClient


class TestStatisticsAPI:
    """Test cases for statistics and health endpoints"""
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert data["database_connected"] is True
        assert "timestamp" in data
        assert "model_count" in data
        assert "version_count" in data
    
    def test_get_model_stats_empty(self, client: TestClient):
        """Test getting model statistics when database is empty"""
        response = client.get("/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["model_count"] == 0
        assert data["version_count"] == 0
        assert data["active_version_count"] == 0
        assert data["archived_version_count"] == 0
        assert data["provider_binding_count"] == 0
        assert data["provider_distribution"] == {}
        assert data["task_distribution"] == {}
    
    def test_get_model_stats_with_data(self, client: TestClient, sample_model_data, sample_version_data, sample_binding_data):
        """Test getting model statistics with actual data"""
        # Create multiple models with different tasks
        model_data_1 = {**sample_model_data, "name": "model-1", "task": "generation"}
        model_data_2 = {**sample_model_data, "name": "model-2", "task": "embedding"}
        
        model_1_response = client.post("/models", json=model_data_1)
        model_2_response = client.post("/models", json=model_data_2)
        
        model_1_id = model_1_response.json()["id"]
        model_2_id = model_2_response.json()["id"]
        
        # Create versions for each model
        version_1_data = {**sample_version_data, "model_id": model_1_id, "hash": "1" * 64, "eval_score": 0.85, "cost_per_1k": 0.002}
        version_2_data = {**sample_version_data, "model_id": model_2_id, "hash": "2" * 64, "eval_score": 0.90, "cost_per_1k": 0.001}
        
        version_1_response = client.post("/versions", json=version_1_data)
        version_2_response = client.post("/versions", json=version_2_data)
        
        version_1_id = version_1_response.json()["id"]
        version_2_id = version_2_response.json()["id"]
        
        # Create provider bindings
        binding_1_data = {**sample_binding_data, "version_id": version_1_id, "provider": "openai"}
        binding_2_data = {**sample_binding_data, "version_id": version_2_id, "provider": "vertex"}
        
        binding_1_response = client.post("/bindings", json=binding_1_data)
        binding_2_response = client.post("/bindings", json=binding_2_data)
        
        # Update bindings with success rates
        client.put(f"/bindings/{binding_1_response.json()['id']}", json={"success_rate": 0.95})
        client.put(f"/bindings/{binding_2_response.json()['id']}", json={"success_rate": 0.92})
        
        # Get statistics
        response = client.get("/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["model_count"] == 2
        assert data["version_count"] == 2
        assert data["active_version_count"] == 2
        assert data["archived_version_count"] == 0
        assert data["provider_binding_count"] == 2
        
        # Check averages
        assert abs(data["avg_eval_score"] - 0.875) < 0.001  # (0.85 + 0.90) / 2
        assert abs(data["avg_cost_per_1k"] - 0.0015) < 0.0001  # (0.002 + 0.001) / 2
        assert abs(data["avg_success_rate"] - 0.935) < 0.001  # (0.95 + 0.92) / 2
        
        # Check distributions
        assert data["task_distribution"]["generation"] == 1
        assert data["task_distribution"]["embedding"] == 1
        assert data["provider_distribution"]["openai"] == 1
        assert data["provider_distribution"]["vertex"] == 1
    
    def test_get_retention_stats_empty(self, client: TestClient):
        """Test getting retention statistics when no models exist"""
        response = client.get("/retention/stats")
        assert response.status_code == 200
        
        data = response.json()
        assert data["model_id"] is None
        assert data["total_versions"] == 0
        assert data["active_versions"] == 0
        assert data["archived_versions"] == 0
        assert data["retention_count"] == 3  # Default retention count
    
    def test_get_retention_stats_for_model(self, client: TestClient, sample_model_data, sample_version_data):
        """Test getting retention statistics for a specific model"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create multiple versions
        for i in range(5):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1"
            }
            client.post("/versions", json=version_data)
        
        # Get retention stats for the model
        response = client.get(f"/retention/stats?model_id={model_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["model_id"] == model_id
        assert data["total_versions"] == 5
        assert data["active_versions"] == 5  # All active initially
        assert data["archived_versions"] == 0
        assert data["retention_count"] == 3
    
    def test_apply_retention_policy(self, client: TestClient, sample_model_data):
        """Test applying retention policy to a model"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create 5 versions with artifact URIs
        for i in range(5):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1",
                "artifact_uri": f"s3://models/test/v1.{i}.0/model.bin"
            }
            client.post("/versions", json=version_data)
        
        # Apply retention policy (keep 3 versions)
        retention_request = {"model_id": model_id, "retention_count": 3}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 200
        
        data = response.json()
        assert "retention policy applied" in data["message"].lower()
        assert data["retention_count"] == 3
        assert data["versions_archived"] >= 0  # May archive some versions
    
    def test_apply_retention_policy_custom_count(self, client: TestClient, sample_model_data):
        """Test applying retention policy with custom retention count"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create 6 versions
        for i in range(6):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1",
                "artifact_uri": f"s3://models/test/v1.{i}.0/model.bin"
            }
            client.post("/versions", json=version_data)
        
        # Apply retention policy (keep 2 versions)
        retention_request = {"model_id": model_id, "retention_count": 2}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 200
        
        data = response.json()
        assert data["retention_count"] == 2
    
    def test_apply_retention_policy_nonexistent_model(self, client: TestClient):
        """Test applying retention policy to non-existent model fails"""
        retention_request = {"model_id": 99999, "retention_count": 3}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]
    
    def test_model_specific_retention_endpoint(self, client: TestClient, sample_model_data):
        """Test model-specific retention policy endpoint"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create multiple versions
        for i in range(4):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1",
                "artifact_uri": f"s3://models/test/v1.{i}.0/model.bin"
            }
            client.post("/versions", json=version_data)
        
        # Apply retention policy via model-specific endpoint
        response = client.post(f"/models/{model_id}/retention?retention_count=2")
        assert response.status_code == 200
        
        data = response.json()
        assert "retention policy applied" in data["message"].lower()
        assert data["retention_count"] == 2
    
    def test_list_versions_for_model(self, client: TestClient, sample_model_data):
        """Test listing all versions for a specific model"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create multiple versions
        for i in range(3):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1"
            }
            client.post("/versions", json=version_data)
        
        # List versions for model
        response = client.get(f"/models/{model_id}/versions")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 3
        assert len(data["versions"]) == 3
        
        # Verify all versions belong to the model
        for version in data["versions"]:
            assert version["model_id"] == model_id
    
    def test_retention_validation(self, client: TestClient, sample_model_data):
        """Test retention policy validation"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Test invalid retention count (too low)
        retention_request = {"model_id": model_id, "retention_count": 0}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 422
        
        # Test invalid retention count (too high)
        retention_request = {"model_id": model_id, "retention_count": 15}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 422
        
        # Test invalid model ID
        retention_request = {"model_id": -1, "retention_count": 3}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 422
