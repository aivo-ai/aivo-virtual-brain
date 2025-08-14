"""
AIVO Model Registry - Provider Binding Tests
S2-02 Implementation: Tests for provider binding operations
"""

from fastapi.testclient import TestClient


class TestProviderBindingAPI:
    """Test cases for provider binding management API"""
    
    def test_create_provider_binding(self, client: TestClient, sample_model_data, sample_version_data, sample_binding_data):
        """Test creating a new provider binding"""
        # Create model and version first
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Create provider binding
        binding_data = {**sample_binding_data, "version_id": version_id}
        response = client.post("/bindings", json=binding_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["version_id"] == version_id
        assert data["provider"] == binding_data["provider"]
        assert data["provider_model_id"] == binding_data["provider_model_id"]
        assert data["status"] == binding_data["status"]
        assert data["config"] == binding_data["config"]
    
    def test_create_binding_for_nonexistent_version(self, client: TestClient, sample_binding_data):
        """Test creating binding for non-existent version fails"""
        binding_data = {**sample_binding_data, "version_id": 99999}
        
        response = client.post("/bindings", json=binding_data)
        assert response.status_code == 404
        assert "Model version not found" in response.json()["detail"]
    
    def test_create_duplicate_binding(self, client: TestClient, sample_model_data, sample_version_data, sample_binding_data):
        """Test creating duplicate binding fails"""
        # Create model, version, and binding
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        binding_data = {**sample_binding_data, "version_id": version_id}
        client.post("/bindings", json=binding_data)
        
        # Try to create duplicate
        response = client.post("/bindings", json=binding_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_get_provider_binding(self, client: TestClient, sample_model_data, sample_version_data, sample_binding_data):
        """Test getting a provider binding by ID"""
        # Create model, version, and binding
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        binding_data = {**sample_binding_data, "version_id": version_id}
        binding_response = client.post("/bindings", json=binding_data)
        binding_id = binding_response.json()["id"]
        
        # Get binding
        response = client.get(f"/bindings/{binding_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == binding_id
        assert data["version_id"] == version_id
        assert data["provider"] == binding_data["provider"]
    
    def test_list_provider_bindings(self, client: TestClient, sample_model_data, sample_version_data):
        """Test listing provider bindings with pagination"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Create multiple bindings for different providers
        providers = ["openai", "vertex", "bedrock", "anthropic"]
        for i, provider in enumerate(providers):
            binding_data = {
                "version_id": version_id,
                "provider": provider,
                "provider_model_id": f"{provider}-model-{i}",
                "status": "active",
                "config": {"temperature": 0.7 + i * 0.1}
            }
            client.post("/bindings", json=binding_data)
        
        # List bindings with pagination
        response = client.get("/bindings?page=1&size=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 4
        assert len(data["bindings"]) == 3
        assert data["page"] == 1
        assert data["size"] == 3
    
    def test_list_bindings_with_filters(self, client: TestClient, sample_model_data, sample_version_data):
        """Test listing provider bindings with filters"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Create bindings with different properties
        bindings = [
            {"provider": "openai", "status": "active", "success_rate": 0.95},
            {"provider": "vertex", "status": "inactive", "success_rate": 0.85},
            {"provider": "bedrock", "status": "active", "success_rate": 0.90}
        ]
        
        binding_ids = []
        for i, binding_info in enumerate(bindings):
            binding_data = {
                "version_id": version_id,
                "provider": binding_info["provider"],
                "provider_model_id": f"model-{i}",
                "status": binding_info["status"]
            }
            response = client.post("/bindings", json=binding_data)
            binding_id = response.json()["id"]
            binding_ids.append(binding_id)
            
            # Update with success rate
            update_data = {"success_rate": binding_info["success_rate"]}
            client.put(f"/bindings/{binding_id}", json=update_data)
        
        # Filter by version_id
        response = client.get(f"/bindings?version_id={version_id}")
        assert response.status_code == 200
        assert response.json()["total"] == 3
        
        # Filter by provider
        response = client.get("/bindings?provider=openai")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["bindings"][0]["provider"] == "openai"
        
        # Filter by status
        response = client.get("/bindings?status=active")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        for binding in data["bindings"]:
            assert binding["status"] == "active"
        
        # Filter by min success rate
        response = client.get("/bindings?min_success_rate=0.90")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        for binding in data["bindings"]:
            if binding["success_rate"] is not None:
                assert binding["success_rate"] >= 0.90
    
    def test_update_provider_binding(self, client: TestClient, sample_model_data, sample_version_data, sample_binding_data):
        """Test updating a provider binding"""
        # Create model, version, and binding
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        binding_data = {**sample_binding_data, "version_id": version_id}
        binding_response = client.post("/bindings", json=binding_data)
        binding_id = binding_response.json()["id"]
        
        # Update binding
        update_data = {
            "status": "inactive",
            "config": {"temperature": 0.9, "max_tokens": 2000},
            "avg_latency_ms": 150.5,
            "success_rate": 0.92
        }
        response = client.put(f"/bindings/{binding_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "inactive"
        assert data["config"]["temperature"] == 0.9
        assert data["avg_latency_ms"] == 150.5
        assert data["success_rate"] == 0.92
    
    def test_delete_provider_binding(self, client: TestClient, sample_model_data, sample_version_data, sample_binding_data):
        """Test deleting a provider binding"""
        # Create model, version, and binding
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        binding_data = {**sample_binding_data, "version_id": version_id}
        binding_response = client.post("/bindings", json=binding_data)
        binding_id = binding_response.json()["id"]
        
        # Delete binding
        response = client.delete(f"/bindings/{binding_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify binding is deleted
        get_response = client.get(f"/bindings/{binding_id}")
        assert get_response.status_code == 404
    
    def test_list_bindings_for_version(self, client: TestClient, sample_model_data, sample_version_data):
        """Test listing all bindings for a specific version"""
        # Create model and version
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Create multiple bindings for the version
        providers = ["openai", "vertex", "bedrock"]
        for provider in providers:
            binding_data = {
                "version_id": version_id,
                "provider": provider,
                "provider_model_id": f"{provider}-model-1",
                "status": "active"
            }
            client.post("/bindings", json=binding_data)
        
        # List bindings for version
        response = client.get(f"/versions/{version_id}/bindings")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 3
        assert len(data["bindings"]) == 3
        
        # Verify all bindings are for the correct version
        for binding in data["bindings"]:
            assert binding["version_id"] == version_id
    
    def test_binding_validation(self, client: TestClient, sample_model_data, sample_version_data):
        """Test provider binding validation rules"""
        # Create model and version first
        model_response = client.post("/models", json=sample_model_data)
        model_id = model_response.json()["id"]
        
        version_data = {**sample_version_data, "model_id": model_id}
        version_response = client.post("/versions", json=version_data)
        version_id = version_response.json()["id"]
        
        # Test invalid provider
        response = client.post("/bindings", json={
            "version_id": version_id,
            "provider": "invalid_provider",
            "provider_model_id": "test-model"
        })
        assert response.status_code == 422
        
        # Test empty provider_model_id
        response = client.post("/bindings", json={
            "version_id": version_id,
            "provider": "openai",
            "provider_model_id": ""
        })
        assert response.status_code == 422
        
        # Test invalid success rate
        binding_data = {
            "version_id": version_id,
            "provider": "openai",
            "provider_model_id": "gpt-4"
        }
        response = client.post("/bindings", json=binding_data)
        binding_id = response.json()["id"]
        
        # Try to update with invalid success rate
        response = client.put(f"/bindings/{binding_id}", json={"success_rate": 1.5})
        assert response.status_code == 422
