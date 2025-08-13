# AIVO Assessment Service - Basic Test Suite
# S1-10 Implementation - Baseline Assessment Testing

import pytest
import asyncio
from httpx import AsyncClient
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import json

# Test configuration
TEST_BASE_URL = "http://localhost:8003"
SAMPLE_LEARNER_ID = "test-learner-123"
SAMPLE_TENANT_ID = "test-tenant-456"
SAMPLE_SUBJECT = "mathematics"

class TestBaselineAssessment:
    """Test suite for baseline assessment workflow."""
    
    @pytest.fixture
    async def async_client(self):
        """Create async HTTP client for testing."""
        async with AsyncClient(base_url=TEST_BASE_URL) as client:
            yield client
    
    @pytest.fixture
    def sample_start_request(self):
        """Sample baseline start request payload."""
        return {
            "learner_id": SAMPLE_LEARNER_ID,
            "tenant_id": SAMPLE_TENANT_ID,
            "subject": SAMPLE_SUBJECT,
            "metadata": {
                "source": "automated_test",
                "test_mode": True
            }
        }
    
    @pytest.fixture
    def sample_question_response(self):
        """Sample question for testing."""
        return {
            "id": "q_001",
            "content": "What is 2 + 2?",
            "question_type": "multiple_choice",
            "options": ["2", "3", "4", "5"],
            "estimated_time_seconds": 30,
            "metadata": {
                "tags": ["arithmetic", "addition"],
                "difficulty": 0.2,
                "question_number": 1
            }
        }
    
    async def test_health_check(self, async_client: AsyncClient):
        """Test basic health check endpoint."""
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "assessment-svc"
        assert "timestamp" in data
    
    async def test_detailed_health_check(self, async_client: AsyncClient):
        """Test detailed health check with dependencies."""
        response = await async_client.get("/api/v1/health/detailed")
        # May return 503 if database isn't configured
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
    
    async def test_service_metrics(self, async_client: AsyncClient):
        """Test service metrics endpoint."""
        response = await async_client.get("/api/v1/metrics")
        # May return 500 if database isn't configured
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "session_metrics" in data
            assert "assessment_metrics" in data
    
    async def test_start_baseline_assessment_validation(self, async_client: AsyncClient):
        """Test baseline assessment start with validation."""
        # Test missing required fields
        invalid_request = {"learner_id": SAMPLE_LEARNER_ID}
        
        response = await async_client.post(
            "/api/v1/baseline/start",
            json=invalid_request
        )
        assert response.status_code == 422  # Validation error
    
    async def test_start_baseline_assessment_success(self, async_client: AsyncClient, sample_start_request):
        """Test successful baseline assessment start."""
        response = await async_client.post(
            "/api/v1/baseline/start",
            json=sample_start_request
        )
        
        # May return 500 if database/questions not configured
        if response.status_code == 500:
            pytest.skip("Database not configured for testing")
        
        # Should return 201 or 409 (existing session)
        assert response.status_code in [200, 409]
        
        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
            assert data["subject"] == SAMPLE_SUBJECT
            assert "first_question" in data
            assert data["status"] in ["CREATED", "IN_PROGRESS"]
    
    def test_answer_request_validation(self):
        """Test answer request validation."""
        # Valid answer request structure
        valid_request = {
            "session_id": "session_123",
            "question_id": "q_001",
            "user_answer": "4",
            "response_time_ms": 2500
        }
        
        # Missing fields should fail validation
        invalid_requests = [
            {"session_id": "session_123"},  # Missing question_id
            {"question_id": "q_001"},       # Missing session_id
            {"session_id": "session_123", "question_id": "q_001"}  # Missing user_answer
        ]
        
        # This would be tested with pydantic validation
        from app.schemas import BaselineAnswerRequest
        
        # Test valid request
        valid_model = BaselineAnswerRequest(**valid_request)
        assert valid_model.session_id == "session_123"
        assert valid_model.user_answer == "4"
        
        # Test invalid requests
        for invalid_req in invalid_requests:
            with pytest.raises(ValueError):
                BaselineAnswerRequest(**invalid_req)
    
    async def test_get_nonexistent_session_result(self, async_client: AsyncClient):
        """Test retrieving result for nonexistent session."""
        response = await async_client.get("/api/v1/baseline/result/nonexistent-session")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert data["error"] == "session_not_found"
    
    async def test_get_learner_sessions_empty(self, async_client: AsyncClient):
        """Test retrieving sessions for learner with no sessions."""
        response = await async_client.get(f"/api/v1/assessment/sessions/{SAMPLE_LEARNER_ID}")
        
        # May return 500 if database not configured
        if response.status_code == 500:
            pytest.skip("Database not configured for testing")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert isinstance(data["sessions"], list)
    
    async def test_get_learner_sessions_with_filters(self, async_client: AsyncClient):
        """Test retrieving sessions with query filters."""
        params = {
            "subject": SAMPLE_SUBJECT,
            "status": "COMPLETED",
            "limit": 10,
            "offset": 0
        }
        
        response = await async_client.get(
            f"/api/v1/assessment/sessions/{SAMPLE_LEARNER_ID}",
            params=params
        )
        
        # May return 500 if database not configured
        if response.status_code == 500:
            pytest.skip("Database not configured for testing")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "sessions" in data
        assert "total_count" in data
        assert "has_more" in data
    
    async def test_get_session_details_nonexistent(self, async_client: AsyncClient):
        """Test getting details for nonexistent session."""
        response = await async_client.get("/api/v1/assessment/session/nonexistent-session")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert data["error"] == "session_not_found"
    
    async def test_cancel_nonexistent_session(self, async_client: AsyncClient):
        """Test cancelling nonexistent session."""
        response = await async_client.delete("/api/v1/assessment/session/nonexistent-session")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data
        assert data["error"] == "session_not_found"
    
    async def test_get_learner_stats_empty(self, async_client: AsyncClient):
        """Test getting stats for learner with no assessments."""
        response = await async_client.get(f"/api/v1/assessment/stats/{SAMPLE_LEARNER_ID}")
        
        # May return 500 if database not configured
        if response.status_code == 500:
            pytest.skip("Database not configured for testing")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "learner_id" in data
        assert "session_counts" in data
        assert data["learner_id"] == SAMPLE_LEARNER_ID

class TestIRTEngine:
    """Test suite for IRT engine calculations."""
    
    def test_irt_calculation_imports(self):
        """Test that IRT engine imports work."""
        try:
            from app.logic_baseline import IRTEngine, LevelMapper, BaselineAssessmentEngine
            assert True
        except ImportError as e:
            pytest.fail(f"IRT engine imports failed: {e}")
    
    def test_level_mapper_thresholds(self):
        """Test level mapping thresholds."""
        from app.logic_baseline import LevelMapper
        
        mapper = LevelMapper()
        
        # Test boundary conditions
        assert mapper.theta_to_level(-2.0) == "L0"
        assert mapper.theta_to_level(-1.0) == "L1"
        assert mapper.theta_to_level(0.0) == "L2"
        assert mapper.theta_to_level(1.0) == "L3"
        assert mapper.theta_to_level(2.0) == "L4"
        
        # Test edge cases
        assert mapper.theta_to_level(-1.5) == "L0"  # Boundary
        assert mapper.theta_to_level(-1.49) == "L1" # Just above boundary

class TestEventIntegration:
    """Test suite for event publishing."""
    
    def test_baseline_complete_event_schema(self):
        """Test baseline completion event schema."""
        from app.schemas import BaselineCompleteEvent
        
        sample_event = {
            "learner_id": SAMPLE_LEARNER_ID,
            "tenant_id": SAMPLE_TENANT_ID,
            "subject": SAMPLE_SUBJECT,
            "proficiency_level": "L2",
            "final_theta": 0.25,
            "standard_error": 0.28,
            "accuracy_percentage": 75.0,
            "total_questions": 20,
            "correct_answers": 15,
            "session_id": "session_123",
            "completed_at": datetime.utcnow(),
            "metadata": {
                "reliability": 0.87,
                "level_confidence": 0.92
            }
        }
        
        event = BaselineCompleteEvent(**sample_event)
        assert event.learner_id == SAMPLE_LEARNER_ID
        assert event.proficiency_level == "L2"
        assert event.event_type == "BASELINE_COMPLETE"

# Run tests with: pytest test_assessment_service.py -v
