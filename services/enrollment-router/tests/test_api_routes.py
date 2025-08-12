import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "service" in response.json()

def test_district_enrollment():
    """Test district enrollment routing"""
    data = {
        "learner_profile": {
            "learner_temp_id": "temp_123",
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com"
        },
        "context": {
            "tenant_id": "district_001"
        }
    }
    
    response = client.post("/enroll", json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["provision_source"] == "district"
    assert result["tenant_id"] == "district_001"
    assert "seat_allocation_id" in result

def test_parent_enrollment():
    """Test parent enrollment routing"""
    data = {
        "learner_profile": {
            "learner_temp_id": "temp_456",
            "first_name": "Jane",
            "last_name": "Smith",
            "email": "jane.smith@example.com"
        },
        "context": {}
    }
    
    response = client.post("/enroll", json=data)
    assert response.status_code == 200
    result = response.json()
    assert result["provision_source"] == "parent"
    assert "checkout_url" in result
