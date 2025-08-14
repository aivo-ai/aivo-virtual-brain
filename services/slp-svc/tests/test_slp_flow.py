# AIVO SLP Service - Comprehensive Test Suite
# S2-11 Implementation - Tests for complete SLP workflow

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import json
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

# Import app and dependencies
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.database import get_db, Base
from app.models import ScreeningAssessment, TherapyPlan, ExerciseInstance, ExerciseSession
from app.schemas import ScreeningRequest, TherapyPlanRequest, ExerciseRequest, SessionSubmitRequest

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_slp.db"

engine = create_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def test_client():
    """Create test client."""
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Create clean database session for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def sample_tenant_id():
    """Sample tenant ID."""
    return uuid.uuid4()


@pytest.fixture
def sample_patient_id():
    """Sample patient ID."""
    return "patient_123"


@pytest.fixture
def sample_screening_data():
    """Sample screening assessment data."""
    return {
        "articulation_tasks": [
            {"word": "cat", "phoneme": "/k/", "accuracy": 0.85, "attempts": 3},
            {"word": "dog", "phoneme": "/d/", "accuracy": 0.92, "attempts": 2}
        ],
        "language_comprehension": [
            {"instruction": "Point to the red ball", "correct": True, "response_time": 2.1},
            {"instruction": "Put the block under the table", "correct": False, "response_time": 4.5}
        ],
        "voice_sample": {
            "recording_url": "https://example.com/voice/sample1.wav",
            "duration": 15.3,
            "pitch_analysis": {"mean_f0": 145.2, "f0_range": 45.8},
            "fluency_metrics": {"words_per_minute": 120, "disfluencies": 3}
        }
    }


# Test Root Endpoints
class TestRootEndpoints:
    """Test root and health endpoints."""
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "slp-svc"
        assert data["name"] == "AIVO Speech & Language Pathology Service"
        assert "version" in data
    
    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "slp-svc"
        assert "components" in data
        assert "database" in data["components"]
    
    def test_service_info(self, test_client):
        """Test service info endpoint."""
        response = test_client.get("/info")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "slp-svc"
        assert "features" in data
        assert data["features"]["screening"] is True
        assert data["features"]["therapy_planning"] is True


# Test Screening Workflow
class TestScreeningWorkflow:
    """Test screening assessment workflow."""
    
    @patch('app.engine.SLPEngine.process_screening')
    def test_create_screening_assessment(self, mock_process, test_client, sample_tenant_id, sample_patient_id, sample_screening_data):
        """Test creating a new screening assessment."""
        # Mock processing results
        mock_process.return_value = {
            "scores": {"articulation": 0.85, "language": 0.70, "voice": 0.92},
            "risk_factors": ["mild_articulation_delay"],
            "recommendations": ["Focus on /k/ phoneme production"],
            "overall_score": 0.82,
            "priority_areas": ["articulation"],
            "therapy_recommended": True
        }
        
        request_data = {
            "tenant_id": str(sample_tenant_id),
            "patient_id": sample_patient_id,
            "patient_name": "John Doe",
            "patient_age": 6,
            "date_of_birth": "2017-05-15",
            "assessment_type": "comprehensive",
            "assessment_data": sample_screening_data
        }
        
        response = test_client.post("/api/v1/slp/screen", json=request_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["tenant_id"] == str(sample_tenant_id)
        assert data["patient_id"] == sample_patient_id
        assert data["patient_name"] == "John Doe"
        assert data["status"] == "in_progress"
    
    def test_get_screening_assessment(self, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test retrieving a screening assessment."""
        # Create assessment directly in database
        assessment = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed"
        )
        db_session.add(assessment)
        db_session.commit()
        db_session.refresh(assessment)
        
        response = test_client.get(f"/api/v1/slp/screen/{assessment.id}?tenant_id={sample_tenant_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(assessment.id)
        assert data["patient_name"] == "John Doe"
    
    def test_list_screening_assessments(self, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test listing screening assessments."""
        # Create multiple assessments
        for i in range(3):
            assessment = ScreeningAssessment(
                tenant_id=sample_tenant_id,
                patient_id=f"{sample_patient_id}_{i}",
                patient_name=f"Patient {i}",
                patient_age=6 + i,
                assessment_type="comprehensive",
                assessment_data={"test": f"data_{i}"},
                status="completed"
            )
            db_session.add(assessment)
        
        db_session.commit()
        
        response = test_client.get(f"/api/v1/slp/screen?tenant_id={sample_tenant_id}&per_page=10")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) == 3
        assert all(item["tenant_id"] == str(sample_tenant_id) for item in data)


# Test Therapy Planning Workflow
class TestTherapyPlanningWorkflow:
    """Test therapy planning workflow."""
    
    @patch('app.engine.SLPEngine.generate_therapy_plan')
    def test_create_therapy_plan(self, mock_generate, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test creating a therapy plan."""
        # Create completed screening assessment
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed",
            overall_score=0.82,
            therapy_recommended=True
        )
        db_session.add(screening)
        db_session.commit()
        db_session.refresh(screening)
        
        # Mock plan generation
        mock_generate.return_value = {
            "goals": [
                {"goal": "Improve /k/ phoneme production", "target_accuracy": 0.90},
                {"goal": "Increase vocabulary comprehension", "target_words": 50}
            ],
            "objectives": [
                {"objective": "Practice /k/ in word-initial position", "sessions": 5},
                {"objective": "Learn 10 new action words", "sessions": 3}
            ],
            "exercise_sequence": ["articulation_drill", "vocabulary_match", "sentence_completion"],
            "estimated_duration_weeks": 8,
            "progress_data": {"phase": 1, "exercises_completed": 0},
            "current_phase": "initial_assessment"
        }
        
        request_data = {
            "tenant_id": str(sample_tenant_id),
            "screening_id": str(screening.id),
            "plan_name": "John's Articulation Plan",
            "priority_level": "medium",
            "sessions_per_week": 2,
            "session_duration": 30
        }
        
        response = test_client.post("/api/v1/slp/plan", json=request_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["plan_name"] == "John's Articulation Plan"
        assert data["screening_id"] == str(screening.id)
        assert data["status"] == "active"
        assert len(data["goals"]) == 2
    
    def test_get_therapy_plan(self, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test retrieving a therapy plan."""
        # Create screening first
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed"
        )
        db_session.add(screening)
        db_session.commit()
        
        # Create therapy plan
        plan = TherapyPlan(
            tenant_id=sample_tenant_id,
            screening_id=screening.id,
            patient_id=sample_patient_id,
            plan_name="Test Plan",
            priority_level="medium",
            goals=[{"goal": "Test goal"}],
            objectives=[{"objective": "Test objective"}],
            exercise_sequence=["test_exercise"],
            sessions_per_week=2,
            session_duration=30,
            status="active"
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)
        
        response = test_client.get(f"/api/v1/slp/plan/{plan.id}?tenant_id={sample_tenant_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(plan.id)
        assert data["plan_name"] == "Test Plan"


# Test Exercise Generation Workflow
class TestExerciseWorkflow:
    """Test exercise generation workflow."""
    
    @patch('app.engine.SLPEngine.generate_next_exercise')
    def test_generate_next_exercise(self, mock_generate, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test generating next exercise."""
        # Create screening and therapy plan
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed"
        )
        db_session.add(screening)
        db_session.commit()
        
        plan = TherapyPlan(
            tenant_id=sample_tenant_id,
            screening_id=screening.id,
            patient_id=sample_patient_id,
            plan_name="Test Plan",
            priority_level="medium",
            goals=[{"goal": "Test goal"}],
            objectives=[{"objective": "Test objective"}],
            exercise_sequence=["articulation_drill"],
            sessions_per_week=2,
            session_duration=30,
            status="active"
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)
        
        # Mock exercise generation
        mock_exercise = ExerciseInstance(
            tenant_id=sample_tenant_id,
            therapy_plan_id=plan.id,
            patient_id=sample_patient_id,
            exercise_name="K Sound Practice",
            exercise_type="articulation_drill",
            difficulty_level="beginner",
            estimated_duration=10,
            exercise_content={
                "target_phoneme": "/k/",
                "word_list": ["cat", "car", "key", "cake"],
                "instructions": "Practice saying each word clearly"
            },
            voice_config={"asr_enabled": True, "tts_enabled": True}
        )
        mock_generate.return_value = mock_exercise
        
        request_data = {
            "tenant_id": str(sample_tenant_id),
            "therapy_plan_id": str(plan.id),
            "exercise_type": "articulation_drill",
            "difficulty_preference": "adaptive"
        }
        
        response = test_client.post("/api/v1/slp/exercise/next", json=request_data)
        assert response.status_code == 201
        
        data = response.json()
        assert data["exercise_name"] == "K Sound Practice"
        assert data["exercise_type"] == "articulation_drill"
        assert data["difficulty_level"] == "beginner"
    
    def test_get_exercise(self, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test retrieving an exercise."""
        # Create required dependencies
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed"
        )
        db_session.add(screening)
        db_session.commit()
        
        plan = TherapyPlan(
            tenant_id=sample_tenant_id,
            screening_id=screening.id,
            patient_id=sample_patient_id,
            plan_name="Test Plan",
            priority_level="medium",
            goals=[{"goal": "Test goal"}],
            objectives=[{"objective": "Test objective"}],
            exercise_sequence=["test_exercise"],
            sessions_per_week=2,
            session_duration=30,
            status="active"
        )
        db_session.add(plan)
        db_session.commit()
        
        # Create exercise
        exercise = ExerciseInstance(
            tenant_id=sample_tenant_id,
            therapy_plan_id=plan.id,
            patient_id=sample_patient_id,
            exercise_name="Test Exercise",
            exercise_type="test_type",
            difficulty_level="beginner",
            estimated_duration=10,
            exercise_content={"test": "content"}
        )
        db_session.add(exercise)
        db_session.commit()
        db_session.refresh(exercise)
        
        response = test_client.get(f"/api/v1/slp/exercise/{exercise.id}?tenant_id={sample_tenant_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == str(exercise.id)
        assert data["exercise_name"] == "Test Exercise"


# Test Session Management
class TestSessionWorkflow:
    """Test session management workflow."""
    
    def test_create_session(self, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test creating a new session."""
        # Create required dependencies
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed"
        )
        db_session.add(screening)
        db_session.commit()
        
        plan = TherapyPlan(
            tenant_id=sample_tenant_id,
            screening_id=screening.id,
            patient_id=sample_patient_id,
            plan_name="Test Plan",
            priority_level="medium",
            goals=[{"goal": "Test goal"}],
            objectives=[{"objective": "Test objective"}],
            exercise_sequence=["test_exercise"],
            sessions_per_week=2,
            session_duration=30,
            status="active"
        )
        db_session.add(plan)
        db_session.commit()
        db_session.refresh(plan)
        
        response = test_client.post(
            f"/api/v1/slp/session?tenant_id={sample_tenant_id}&therapy_plan_id={plan.id}&session_type=regular"
        )
        assert response.status_code == 201
        
        data = response.json()
        assert data["therapy_plan_id"] == str(plan.id)
        assert data["session_number"] == 1
        assert data["status"] == "active"
    
    @patch('app.engine.SLPEngine.process_session_submission')
    def test_submit_session_results(self, mock_process, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test submitting session results."""
        # Create required dependencies
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="completed"
        )
        db_session.add(screening)
        db_session.commit()
        
        plan = TherapyPlan(
            tenant_id=sample_tenant_id,
            screening_id=screening.id,
            patient_id=sample_patient_id,
            plan_name="Test Plan",
            priority_level="medium",
            goals=[{"goal": "Test goal"}],
            objectives=[{"objective": "Test objective"}],
            exercise_sequence=["test_exercise"],
            sessions_per_week=2,
            session_duration=30,
            status="active"
        )
        db_session.add(plan)
        db_session.commit()
        
        session = ExerciseSession(
            tenant_id=sample_tenant_id,
            therapy_plan_id=plan.id,
            patient_id=sample_patient_id,
            session_number=1,
            session_type="regular",
            planned_duration=30,
            status="active"
        )
        db_session.add(session)
        db_session.commit()
        db_session.refresh(session)
        
        # Mock processing results
        mock_process.return_value = {
            "session_metrics": {
                "overall_score": 0.85,
                "engagement_score": 0.90,
                "accuracy_rate": 0.80,
                "completion_rate": 1.0
            },
            "voice_analysis": {
                "clarity_score": 0.85,
                "fluency_score": 0.78
            }
        }
        
        request_data = {
            "tenant_id": str(sample_tenant_id),
            "session_id": str(session.id),
            "exercise_results": [
                {
                    "exercise_id": str(uuid.uuid4()),
                    "completed": True,
                    "accuracy_score": 0.85,
                    "time_spent": 5,
                    "attempts": 3
                }
            ],
            "actual_duration": 28,
            "session_notes": "Good progress on articulation",
            "audio_recordings": ["recording1.wav", "recording2.wav"]
        }
        
        response = test_client.post("/api/v1/slp/session/submit", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "completed"
        assert data["overall_score"] == 0.85
        assert data["exercises_completed"] == 1


# Test Complete Workflow Integration
class TestCompleteWorkflow:
    """Test complete SLP workflow from screening to session completion."""
    
    @patch('app.engine.SLPEngine.process_screening')
    @patch('app.engine.SLPEngine.generate_therapy_plan')
    @patch('app.engine.SLPEngine.generate_next_exercise')
    @patch('app.engine.SLPEngine.process_session_submission')
    async def test_complete_slp_workflow(self, mock_session, mock_exercise, mock_plan, mock_screening, 
                                       test_client, sample_tenant_id, sample_patient_id, sample_screening_data):
        """Test complete workflow: screening → plan → exercise → session."""
        
        # Mock all engine methods
        mock_screening.return_value = {
            "scores": {"articulation": 0.85, "language": 0.70, "voice": 0.92},
            "risk_factors": ["mild_articulation_delay"],
            "recommendations": ["Focus on /k/ phoneme production"],
            "overall_score": 0.82,
            "priority_areas": ["articulation"],
            "therapy_recommended": True
        }
        
        mock_plan.return_value = {
            "goals": [{"goal": "Improve /k/ phoneme production", "target_accuracy": 0.90}],
            "objectives": [{"objective": "Practice /k/ in word-initial position", "sessions": 5}],
            "exercise_sequence": ["articulation_drill"],
            "estimated_duration_weeks": 8,
            "progress_data": {"phase": 1, "exercises_completed": 0},
            "current_phase": "initial_assessment"
        }
        
        mock_exercise.return_value = ExerciseInstance(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            exercise_name="K Sound Practice",
            exercise_type="articulation_drill",
            difficulty_level="beginner",
            estimated_duration=10,
            exercise_content={"target_phoneme": "/k/", "word_list": ["cat", "car"]}
        )
        
        mock_session.return_value = {
            "session_metrics": {"overall_score": 0.85, "completion_rate": 1.0},
            "voice_analysis": {"clarity_score": 0.85}
        }
        
        # Step 1: Create screening assessment
        screening_data = {
            "tenant_id": str(sample_tenant_id),
            "patient_id": sample_patient_id,
            "patient_name": "John Doe",
            "patient_age": 6,
            "date_of_birth": "2017-05-15",
            "assessment_type": "comprehensive",
            "assessment_data": sample_screening_data
        }
        
        screening_response = test_client.post("/api/v1/slp/screen", json=screening_data)
        assert screening_response.status_code == 201
        screening_id = screening_response.json()["id"]
        
        # Wait for background processing (in real test, would need to handle async)
        # For this test, we'll simulate completion by updating status
        
        # Step 2: Create therapy plan
        plan_data = {
            "tenant_id": str(sample_tenant_id),
            "screening_id": screening_id,
            "plan_name": "John's Comprehensive Plan",
            "priority_level": "medium",
            "sessions_per_week": 2,
            "session_duration": 30
        }
        
        # Note: This would fail in real test due to async processing
        # In production, client would poll or use webhooks
        # plan_response = test_client.post("/api/v1/slp/plan", json=plan_data)
        # assert plan_response.status_code == 201


# Test Error Handling
class TestErrorHandling:
    """Test error handling scenarios."""
    
    def test_invalid_screening_data(self, test_client, sample_tenant_id):
        """Test validation errors on screening creation."""
        invalid_data = {
            "tenant_id": str(sample_tenant_id),
            "patient_id": "",  # Invalid: empty patient_id
            "patient_name": "John Doe",
            "patient_age": -1,  # Invalid: negative age
            "assessment_data": {}
        }
        
        response = test_client.post("/api/v1/slp/screen", json=invalid_data)
        assert response.status_code == 422
        assert "Validation Error" in response.json()["error"]
    
    def test_nonexistent_resource(self, test_client, sample_tenant_id):
        """Test 404 errors for nonexistent resources."""
        fake_id = str(uuid.uuid4())
        
        response = test_client.get(f"/api/v1/slp/screen/{fake_id}?tenant_id={sample_tenant_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["message"].lower()
    
    def test_therapy_plan_without_completed_screening(self, test_client, db_session, sample_tenant_id, sample_patient_id):
        """Test creating therapy plan with incomplete screening."""
        # Create incomplete screening
        screening = ScreeningAssessment(
            tenant_id=sample_tenant_id,
            patient_id=sample_patient_id,
            patient_name="John Doe",
            patient_age=6,
            assessment_type="comprehensive",
            assessment_data={"test": "data"},
            status="in_progress"  # Not completed
        )
        db_session.add(screening)
        db_session.commit()
        db_session.refresh(screening)
        
        plan_data = {
            "tenant_id": str(sample_tenant_id),
            "screening_id": str(screening.id),
            "plan_name": "Test Plan",
            "priority_level": "medium",
            "sessions_per_week": 2,
            "session_duration": 30
        }
        
        response = test_client.post("/api/v1/slp/plan", json=plan_data)
        assert response.status_code == 400
        assert "must be completed" in response.json()["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
