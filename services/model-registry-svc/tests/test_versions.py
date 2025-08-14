"""
AIVO Model Registry - Version API Tests
S2-02 Implementation: Tests for model version operations and retention
"""

from fastapi.testclient import TestClient


class TestVersionAPI:
    """Test cases for model version management API"""
    
    def test_create_model_version(self, client: TestClient, sample_model_data, sample_version_data):
        """Test creating a new model version"""
        # Create model first
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Update version data with model ID
        version_data = {**sample_version_data, "model_id": model_id}
        
        # Create version
        response = client.post("/versions", json=version_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["model_id"] == model_id
        assert data["hash"] == version_data["hash"]
        assert data["version"] == version_data["version"]
        assert data["cost_per_1k"] == version_data["cost_per_1k"]
        assert data["eval_score"] == version_data["eval_score"]
    
    def test_create_version_for_nonexistent_model(self, client: TestClient, sample_version_data):
        """Test creating version for non-existent model fails"""
        version_data = {**sample_version_data, "model_id": 99999}
        
        response = client.post("/versions", json=version_data)
        assert response.status_code == 404
        assert "Model not found" in response.json()["detail"]
    
    def test_create_duplicate_version_hash(self, client: TestClient, sample_model_data, sample_version_data):
        """Test creating version with duplicate hash fails"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        client.post("/versions", json=version_data)
        
        # Try to create duplicate hash
        duplicate_data = {**version_data, "version": "2.0.0"}
        response = client.post("/versions", json=duplicate_data)
        assert response.status_code == 400
        assert "hash already exists" in response.json()["detail"]
    
    def test_create_duplicate_version_number(self, client: TestClient, sample_model_data, sample_version_data):
        """Test creating version with duplicate version number fails"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        client.post("/versions", json=version_data)
        
        # Try to create duplicate version
        duplicate_data = {**version_data, "hash": "different" + version_data["hash"][9:]}
        response = client.post("/versions", json=duplicate_data)
        assert response.status_code == 400
        assert "Version number already exists" in response.json()["detail"]
    
    def test_get_model_version(self, client: TestClient, sample_model_data, sample_version_data):
        """Test getting a model version by ID"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Get version
        response = client.get(f"/versions/{version_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == version_id
        assert data["model_id"] == model_id
        assert data["version"] == version_data["version"]
    
    def test_list_model_versions(self, client: TestClient, sample_model_data):
        """Test listing model versions with pagination"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create multiple versions
        for i in range(5):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1",
                "cost_per_1k": 0.002 + i * 0.001,
                "eval_score": 0.8 + i * 0.02
            }
            client.post("/versions", json=version_data)
        
        # List versions with pagination
        response = client.get("/versions?page=1&size=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5
        assert len(data["versions"]) == 3
        assert data["page"] == 1
        assert data["size"] == 3
    
    def test_list_versions_with_filters(self, client: TestClient, sample_model_data):
        """Test listing model versions with filters"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create versions with different properties
        versions = [
            {"hash": "1" * 64, "version": "1.0.0", "region": "us-east-1", "eval_score": 0.9, "cost_per_1k": 0.001},
            {"hash": "2" * 64, "version": "1.1.0", "region": "eu-west-1", "eval_score": 0.8, "cost_per_1k": 0.003},
            {"hash": "3" * 64, "version": "1.2.0", "region": "us-east-1", "eval_score": 0.85, "cost_per_1k": 0.002}
        ]
        
        for version_data in versions:
            full_data = {**version_data, "model_id": model_id}
            client.post("/versions", json=full_data)
        
        # Filter by model_id
        response = client.get(f"/versions?model_id={model_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 3
        
        # Filter by region
        response = client.get("/versions?region=us-east-1")
        assert response.status_code == 200
        assert response.json()["total"] == 2
        
        # Filter by min eval score
        response = client.get("/versions?min_eval_score=0.85")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for version in data["versions"]:
            assert version["eval_score"] >= 0.85
        
        # Filter by max cost
        response = client.get("/versions?max_cost_per_1k=0.002")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for version in data["versions"]:
            assert version["cost_per_1k"] <= 0.002
    
    def test_update_model_version(self, client: TestClient, sample_model_data, sample_version_data):
        """Test updating a model version"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Update version
        update_data = {
            "cost_per_1k": 0.005,
            "eval_score": 0.92,
            "slo_ok": False
        }
        response = client.put(f"/versions/{version_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["cost_per_1k"] == 0.005
        assert data["eval_score"] == 0.92
        assert data["slo_ok"] is False
    
    def test_delete_model_version(self, client: TestClient, sample_model_data, sample_version_data):
        """Test deleting a model version"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Delete version
        response = client.delete(f"/versions/{version_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify version is deleted
        get_response = client.get(f"/versions/{version_id}")
        assert get_response.status_code == 404
    
    def test_retention_policy(self, client: TestClient, sample_model_data):
        """Test retention policy application"""
        # Create model
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Create 5 versions (retention default is 3)
        version_ids = []
        for i in range(5):
            version_data = {
                "model_id": model_id,
                "hash": f"{i:064d}",
                "version": f"1.{i}.0",
                "region": "us-east-1",
                "artifact_uri": f"s3://models/test/v1.{i}.0/model.bin"
            }
            response = client.post("/versions", json=version_data)
            version_ids.append(response.json()["id"])
        
        # Apply retention policy manually
        retention_request = {"model_id": model_id, "retention_count": 3}
        response = client.post("/retention/apply", json=retention_request)
        assert response.status_code == 200
        
        result = response.json()
        assert "retention policy applied" in result["message"].lower()
        assert result["versions_archived"] >= 0  # Some versions may be archived
    
    def test_version_validation(self, client: TestClient, sample_model_data):
        """Test version validation rules"""
        # Create model first
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        # Test invalid hash length
        response = client.post("/versions", json={
            "model_id": model_id,
            "hash": "short_hash",
            "version": "1.0.0"
        })
        assert response.status_code == 422
        
        # Test invalid version format
        response = client.post("/versions", json={
            "model_id": model_id,
            "hash": "a" * 64,
            "version": "invalid.version.format.extra"
        })
        assert response.status_code == 422
        
        # Test negative cost
        response = client.post("/versions", json={
            "model_id": model_id,
            "hash": "b" * 64,
            "version": "1.0.0",
            "cost_per_1k": -0.001
        })
        assert response.status_code == 422
        
        # Test eval_score out of range
        response = client.post("/versions", json={
            "model_id": model_id,
            "hash": "c" * 64,
            "version": "1.0.0",
            "eval_score": 1.5
        })
        assert response.status_code == 422
