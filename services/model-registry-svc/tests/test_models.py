"""
AIVO Model Registry - Model API Tests
S2-02 Implementation: Tests for model CRUD operations
"""

import pytest
from fastapi.testclient import TestClient
from app.models import ModelTaskType


class TestModelAPI:
    """Test cases for model management API"""
    
    def test_create_model(self, client: TestClient, sample_model_data):
        """Test creating a new model"""
        response = client.post("/models", json=sample_model_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_model_data["name"]
        assert data["task"] == sample_model_data["task"]
        assert data["subject"] == sample_model_data["subject"]
        assert data["description"] == sample_model_data["description"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
    
    def test_create_model_duplicate_name(self, client: TestClient, sample_model_data):
        """Test creating a model with duplicate name fails"""
        # Create first model
        client.post("/models", json=sample_model_data)
        
        # Try to create duplicate
        response = client.post("/models", json=sample_model_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    def test_get_model(self, client: TestClient, sample_model_data):
        """Test getting a model by ID"""
        # Create model
        create_response = client.post("/models", json=sample_model_data)
        model_id = create_response.json()["id"]
        
        # Get model
        response = client.get(f"/models/{model_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == model_id
        assert data["name"] == sample_model_data["name"]
    
    def test_get_model_by_name(self, client: TestClient, sample_model_data):
        """Test getting a model by name"""
        # Create model
        client.post("/models", json=sample_model_data)
        
        # Get model by name
        response = client.get(f"/models/name/{sample_model_data['name']}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == sample_model_data["name"]
    
    def test_get_nonexistent_model(self, client: TestClient):
        """Test getting a non-existent model returns 404"""
        response = client.get("/models/99999")
        assert response.status_code == 404
    
    def test_list_models(self, client: TestClient):
        """Test listing models with pagination"""
        # Create multiple models
        for i in range(5):
            model_data = {
                "name": f"test-model-{i}",
                "task": "generation",
                "subject": f"subject-{i}",
                "description": f"Test model {i}"
            }
            client.post("/models", json=model_data)
        
        # List models
        response = client.get("/models?page=1&size=3")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total"] == 5
        assert len(data["models"]) == 3
        assert data["page"] == 1
        assert data["size"] == 3
        assert data["pages"] == 2
    
    def test_list_models_with_filters(self, client: TestClient):
        """Test listing models with filters"""
        # Create models with different tasks
        models = [
            {"name": "gen-model", "task": "generation", "subject": "general"},
            {"name": "emb-model", "task": "embedding", "subject": "general"},
            {"name": "mod-model", "task": "moderation", "subject": "safety"}
        ]
        
        for model_data in models:
            client.post("/models", json=model_data)
        
        # Filter by task
        response = client.get("/models?task=generation")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["models"][0]["task"] == "generation"
        
        # Filter by subject
        response = client.get("/models?subject=general")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        
        # Filter by name substring
        response = client.get("/models?name_contains=gen")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert "gen" in data["models"][0]["name"]
    
    def test_update_model(self, client: TestClient, sample_model_data):
        """Test updating a model"""
        # Create model
        create_response = client.post("/models", json=sample_model_data)
        model_id = create_response.json()["id"]
        
        # Update model
        update_data = {
            "subject": "updated-subject",
            "description": "Updated description"
        }
        response = client.put(f"/models/{model_id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["subject"] == "updated-subject"
        assert data["description"] == "Updated description"
    
    def test_delete_model(self, client: TestClient, sample_model_data):
        """Test deleting a model"""
        # Create model
        create_response = client.post("/models", json=sample_model_data)
        model_id = create_response.json()["id"]
        
        # Delete model
        response = client.delete(f"/models/{model_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]
        
        # Verify model is deleted
        get_response = client.get(f"/models/{model_id}")
        assert get_response.status_code == 404
    
    def test_model_validation(self, client: TestClient):
        """Test model validation rules"""
        # Test empty name
        response = client.post("/models", json={
            "name": "",
            "task": "generation"
        })
        assert response.status_code == 422
        
        # Test invalid task
        response = client.post("/models", json={
            "name": "test-model",
            "task": "invalid_task"
        })
        assert response.status_code == 422
        
        # Test name too long
        response = client.post("/models", json={
            "name": "x" * 300,
            "task": "generation"
        })
        assert response.status_code == 422
