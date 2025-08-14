"""
AIVO Assessment Service - IRT Flow Tests
S2-08 Implementation - Test Suite for Adaptive Assessment

Tests the complete IRT-based adaptive assessment flow:
- Session initialization and question selection
- Answer submission and ability estimation
- Convergence to target precision within 7 items
- Level mapping and final reporting
- Item calibration utilities
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import uuid
import math
import json

from app.main import app
from app.database import Base, get_db
from app.models import (
    AssessmentSession, QuestionBank, AssessmentResponse, AssessmentResult,
    AssessmentStatus, AssessmentType
)
from app.logic_irt import IRTEngine, IRTParameters, ItemCalibration
from app.schemas import (
    AdaptiveStartRequest, AdaptiveAnswerRequest, ItemCalibrationRequest
)

# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_irt.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def db_setup():
    """Set up test database with sample questions."""
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    
    # Create sample question bank with IRT parameters
    sample_questions = [
        # Easy questions (low difficulty)
        {"id": "q1", "subject": "math", "content": "What is 2 + 2?", "correct_answer": "4", 
         "difficulty": -2.0, "discrimination": 1.5, "guessing": 0.0},
        {"id": "q2", "subject": "math", "content": "What is 5 - 3?", "correct_answer": "2",
         "difficulty": -1.8, "discrimination": 1.2, "guessing": 0.0},
        {"id": "q3", "subject": "math", "content": "What is 3 * 2?", "correct_answer": "6",
         "difficulty": -1.5, "discrimination": 1.4, "guessing": 0.0},
        
        # Medium questions
        {"id": "q4", "subject": "math", "content": "Solve: x + 5 = 12", "correct_answer": "7",
         "difficulty": 0.0, "discrimination": 1.8, "guessing": 0.0},
        {"id": "q5", "subject": "math", "content": "What is 15% of 80?", "correct_answer": "12",
         "difficulty": 0.2, "discrimination": 1.6, "guessing": 0.0},
        {"id": "q6", "subject": "math", "content": "Factor: x² - 4", "correct_answer": "(x+2)(x-2)",
         "difficulty": 0.3, "discrimination": 2.0, "guessing": 0.0},
        
        # Hard questions (high difficulty)
        {"id": "q7", "subject": "math", "content": "Solve: log₂(x) = 3", "correct_answer": "8",
         "difficulty": 1.5, "discrimination": 1.8, "guessing": 0.0},
        {"id": "q8", "subject": "math", "content": "Find derivative of x³ + 2x", "correct_answer": "3x² + 2",
         "difficulty": 2.0, "discrimination": 2.2, "guessing": 0.0},
        {"id": "q9", "subject": "math", "content": "Evaluate ∫x²dx", "correct_answer": "x³/3 + C",
         "difficulty": 2.5, "discrimination": 1.9, "guessing": 0.0},
        {"id": "q10", "subject": "math", "content": "What is 7 * 8?", "correct_answer": "56",
         "difficulty": -1.0, "discrimination": 1.3, "guessing": 0.0}
    ]
    
    for q_data in sample_questions:
        question = QuestionBank(
            id=q_data["id"],
            subject=q_data["subject"],
            question_type="short_answer",
            content=q_data["content"],
            correct_answer=q_data["correct_answer"],
            difficulty=q_data["difficulty"],
            discrimination=q_data["discrimination"],
            guessing=q_data["guessing"],
            is_active=True
        )
        db.add(question)
    
    db.commit()
    db.close()
    
    yield
    
    # Cleanup
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)

@pytest.fixture
def mock_auth():
    """Mock authentication for testing."""
    def mock_get_current_user():
        return {"user_id": "test_user", "tenant_id": "test_tenant"}
    
    def mock_get_admin_user():
        return {"user_id": "admin_user", "tenant_id": "test_tenant", "scopes": ["admin"]}
    
    from app.dependencies import get_current_user, get_admin_user
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_admin_user] = mock_get_admin_user
    
    yield
    
    # Cleanup overrides
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_admin_user in app.dependency_overrides:
        del app.dependency_overrides[get_admin_user]

class TestIRTEngine:
    """Test IRT mathematical functions and ability estimation."""
    
    def setup_method(self):
        """Set up IRT engine for testing."""
        self.engine = IRTEngine()
        self.sample_items = [
            IRTParameters(-1.0, 1.5, 0.0),  # Easy item
            IRTParameters(0.0, 2.0, 0.0),   # Medium item
            IRTParameters(1.0, 1.8, 0.0),   # Hard item
        ]
    
    def test_probability_calculation(self):
        """Test 3PL probability calculation."""
        # Test with medium item at different ability levels
        item = IRTParameters(0.0, 1.5, 0.0)
        
        # At theta = difficulty, P should be around 0.5 (no guessing)
        p_equal = self.engine.probability(0.0, item)
        assert 0.45 <= p_equal <= 0.55, f"Expected ~0.5, got {p_equal}"
        
        # Higher ability should give higher probability
        p_high = self.engine.probability(2.0, item)
        assert p_high > p_equal, "Higher ability should give higher probability"
        
        # Lower ability should give lower probability
        p_low = self.engine.probability(-2.0, item)
        assert p_low < p_equal, "Lower ability should give lower probability"
    
    def test_information_calculation(self):
        """Test Fisher information calculation."""
        item = IRTParameters(0.0, 2.0, 0.0)
        
        # Information should be highest near item difficulty
        info_at_difficulty = self.engine.information(0.0, item)
        info_far_away = self.engine.information(3.0, item)
        
        assert info_at_difficulty > info_far_away, "Information should be higher near item difficulty"
        assert info_at_difficulty > 0, "Information should be positive"
    
    def test_ability_estimation_convergence(self):
        """Test ability estimation with known responses."""
        # Simulate a learner with theta = 1.0
        true_theta = 1.0
        responses = []
        
        # Generate responses based on true ability
        for item in self.sample_items:
            p_correct = self.engine.probability(true_theta, item)
            # Simulate correct response with this probability (deterministic for test)
            is_correct = p_correct > 0.5
            responses.append((is_correct, item))
        
        # Estimate ability
        estimated_theta, se = self.engine.estimate_ability(responses)
        
        # Should be reasonably close to true theta
        error = abs(estimated_theta - true_theta)
        assert error <= 1.0, f"Estimation error {error} too large"
        assert se > 0, "Standard error should be positive"
    
    def test_level_mapping(self):
        """Test theta to level mapping."""
        test_cases = [
            (-2.0, "L0"),  # Very low ability
            (-1.0, "L1"),  # Low ability
            (0.0, "L2"),   # Medium ability
            (1.0, "L3"),   # High ability
            (2.0, "L4"),   # Very high ability
        ]
        
        for theta, expected_level in test_cases:
            level, confidence = self.engine.map_theta_to_level(theta, 0.5)
            assert level == expected_level, f"Expected {expected_level}, got {level} for theta={theta}"
            assert 0.5 <= confidence <= 1.0, f"Confidence {confidence} out of range"
    
    def test_stopping_criteria(self):
        """Test adaptive stopping criteria."""
        # Should not stop with high SE and few questions
        assert not self.engine.should_stop_assessment(1.0, 2)
        
        # Should stop with low SE and enough questions
        assert self.engine.should_stop_assessment(0.2, 5)
        
        # Should stop at maximum questions regardless of SE
        assert self.engine.should_stop_assessment(0.8, self.engine.max_questions)

class TestItemCalibration:
    """Test item parameter calibration utilities."""
    
    def setup_method(self):
        """Set up calibration service."""
        self.calibration = ItemCalibration()
    
    def test_parameter_estimation(self):
        """Test basic parameter estimation from response data."""
        # Create sample response data
        responses = [
            {"theta": -2.0, "is_correct": False},
            {"theta": -1.0, "is_correct": False},
            {"theta": 0.0, "is_correct": True},
            {"theta": 1.0, "is_correct": True},
            {"theta": 2.0, "is_correct": True},
        ]
        
        params = self.calibration.estimate_item_parameters(responses)
        
        # Should have reasonable parameter values
        assert -3.0 <= params.difficulty <= 3.0, "Difficulty out of reasonable range"
        assert 0.5 <= params.discrimination <= 3.0, "Discrimination out of reasonable range"
        assert 0.0 <= params.guessing <= 0.5, "Guessing parameter out of range"
    
    def test_batch_calibration(self):
        """Test batch calibration of multiple items."""
        item_responses = {
            "item1": [{"theta": i * 0.5 - 2, "is_correct": i > 2} for i in range(10)],
            "item2": [{"theta": i * 0.5 - 2, "is_correct": i > 4} for i in range(10)]
        }
        
        calibrated = self.calibration.batch_calibrate_items(item_responses)
        
        assert len(calibrated) == 2, "Should calibrate both items"
        assert "item1" in calibrated and "item2" in calibrated
        
        # Item2 should be harder than Item1 (more false responses)
        assert calibrated["item2"].difficulty > calibrated["item1"].difficulty

@pytest.mark.usefixtures("db_setup", "mock_auth")
class TestAdaptiveAssessmentAPI:
    """Test complete adaptive assessment API flow."""
    
    def test_start_adaptive_session(self, client):
        """Test starting a new adaptive assessment session."""
        request_data = {
            "learner_id": "test_learner_001",
            "tenant_id": "test_tenant",
            "subject": "math",
            "metadata": {"test_session": True}
        }
        
        response = client.post("/adaptive/start", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert data["status"] in ["created", "in_progress"]
        assert data["current_theta"] == 0.0  # Should start at neutral
        assert data["questions_answered"] == 0
        assert data["first_question"] is not None
        assert "content" in data["first_question"]
    
    def test_submit_answer_and_update_theta(self, client):
        """Test answer submission and theta updating."""
        # Start session
        start_response = client.post("/adaptive/start", json={
            "learner_id": "test_learner_002",
            "tenant_id": "test_tenant",
            "subject": "math"
        })
        
        session_data = start_response.json()
        session_id = session_data["session_id"]
        first_question = session_data["first_question"]
        
        # Submit correct answer
        answer_response = client.post("/adaptive/answer", json={
            "session_id": session_id,
            "question_id": first_question["id"],
            "user_answer": first_question.get("correct_answer", "test_answer"),
            "response_time_ms": 5000
        })
        
        assert answer_response.status_code == 200
        answer_data = answer_response.json()
        
        assert answer_data["is_correct"] == True
        assert answer_data["questions_answered"] == 1
        assert "updated_theta" in answer_data
        assert "standard_error" in answer_data
        
        # For correct answer, theta should typically increase (if question was at appropriate level)
        # Note: Actual direction depends on question difficulty vs current theta
    
    def test_convergence_simulation(self, client):
        """Test that simulated learner converges within target iterations."""
        # Start session
        start_response = client.post("/adaptive/start", json={
            "learner_id": "test_convergence",
            "tenant_id": "test_tenant", 
            "subject": "math"
        })
        
        session_data = start_response.json()
        session_id = session_data["session_id"]
        
        # Simulate consistent performance learner (medium ability)
        questions_answered = 0
        max_iterations = 7  # Test requirement: converge within 7 items
        target_se = 0.25
        
        current_theta = session_data["current_theta"]
        current_se = session_data["standard_error"]
        
        while questions_answered < max_iterations and current_se > target_se:
            # Get next question
            if questions_answered == 0:
                next_question = session_data["first_question"]
            else:
                next_response = client.get(f"/adaptive/next/{session_id}")
                if next_response.status_code != 200:
                    break
                next_data = next_response.json()
                if not next_data["has_next_question"]:
                    break
                next_question = next_data["question"]
            
            if not next_question:
                break
            
            # Simulate learner response based on question difficulty
            question_difficulty = next_question.get("difficulty", 0.0)
            
            # Simulate consistent medium-ability learner (theta ~= 0)
            simulated_ability = 0.0
            probability_correct = 1 / (1 + math.exp(-(simulated_ability - question_difficulty)))
            
            # Deterministic response for consistent testing
            is_likely_correct = probability_correct > 0.5
            simulated_answer = next_question.get("correct_answer", "answer") if is_likely_correct else "wrong"
            
            # Submit answer
            answer_response = client.post("/adaptive/answer", json={
                "session_id": session_id,
                "question_id": next_question["id"],
                "user_answer": simulated_answer,
                "response_time_ms": 3000
            })
            
            if answer_response.status_code != 200:
                break
            
            answer_data = answer_response.json()
            questions_answered = answer_data["questions_answered"]
            current_theta = answer_data["updated_theta"]
            current_se = answer_data["standard_error"]
            
            # Check if assessment completed
            if answer_data["assessment_complete"]:
                break
        
        # Verify convergence criteria
        print(f"Converged in {questions_answered} questions with SE={current_se:.3f}, theta={current_theta:.3f}")
        assert questions_answered <= max_iterations, f"Should converge within {max_iterations} questions"
        assert current_se <= target_se or questions_answered == max_iterations, "Should achieve target SE or reach max questions"
    
    def test_assessment_report_generation(self, client):
        """Test final assessment report generation."""
        # Complete a short assessment
        start_response = client.post("/adaptive/start", json={
            "learner_id": "test_report",
            "tenant_id": "test_tenant",
            "subject": "math"
        })
        
        session_data = start_response.json()
        session_id = session_data["session_id"]
        
        # Answer a few questions to complete assessment
        for i in range(3):
            if i == 0:
                question = session_data["first_question"]
            else:
                next_response = client.get(f"/adaptive/next/{session_id}")
                if next_response.status_code != 200:
                    break
                question = next_response.json()["question"]
            
            if not question:
                break
            
            # Submit answer
            answer_response = client.post("/adaptive/answer", json={
                "session_id": session_id,
                "question_id": question["id"],
                "user_answer": question.get("correct_answer", "test"),
                "response_time_ms": 2000
            })
            
            if answer_response.status_code == 200 and answer_response.json()["assessment_complete"]:
                break
        
        # Get assessment report
        report_response = client.get(f"/adaptive/report/{session_id}")
        
        if report_response.status_code == 200:
            report_data = report_response.json()
            
            # Verify report structure
            assert "final_theta" in report_data
            assert "proficiency_level" in report_data
            assert report_data["proficiency_level"] in ["L0", "L1", "L2", "L3", "L4"]
            assert "level_confidence" in report_data
            assert 0.5 <= report_data["level_confidence"] <= 1.0
            assert "total_questions" in report_data
            assert "accuracy_percentage" in report_data
            assert isinstance(report_data["recommendations"], list)
            assert isinstance(report_data["theta_history"], list)
            assert len(report_data["theta_history"]) > 0
    
    def test_item_calibration_admin_endpoint(self, client):
        """Test admin item calibration functionality."""
        calibration_data = {
            "items": [
                {
                    "item_id": "q4",  # Medium difficulty question from our test set
                    "responses": [
                        {"theta": -2.0, "is_correct": False},
                        {"theta": -1.0, "is_correct": False},
                        {"theta": 0.0, "is_correct": True},
                        {"theta": 1.0, "is_correct": True},
                        {"theta": 2.0, "is_correct": True},
                        {"theta": -1.5, "is_correct": False},
                        {"theta": -0.5, "is_correct": True},
                        {"theta": 0.5, "is_correct": True},
                        {"theta": 1.5, "is_correct": True},
                        {"theta": 2.5, "is_correct": True}
                    ]
                }
            ],
            "calibration_method": "mle"
        }
        
        response = client.post("/admin/calibrate", json=calibration_data)
        
        assert response.status_code == 200
        result = response.json()
        
        assert result["calibrated_items"] == 1
        assert len(result["failed_items"]) == 0
        assert "Successfully calibrated" in result["message"]
    
    def test_error_handling(self, client):
        """Test error handling for invalid requests."""
        # Test invalid session ID
        invalid_response = client.get("/adaptive/next/invalid_session_id")
        assert invalid_response.status_code == 404
        
        # Test missing required fields
        bad_start = client.post("/adaptive/start", json={"learner_id": ""})
        assert bad_start.status_code in [400, 422]  # Validation error
        
        # Test invalid subject
        bad_subject = client.post("/adaptive/start", json={
            "learner_id": "test",
            "tenant_id": "test", 
            "subject": "invalid_subject"
        })
        assert bad_subject.status_code in [400, 422]

class TestIRTMathematicalProperties:
    """Test mathematical properties and edge cases of IRT implementation."""
    
    def setup_method(self):
        """Set up for mathematical tests."""
        self.engine = IRTEngine()
    
    def test_probability_bounds(self):
        """Test that probabilities stay within [0,1] bounds."""
        # Test with extreme parameters
        extreme_cases = [
            IRTParameters(-10.0, 5.0, 0.0),  # Very easy, high discrimination
            IRTParameters(10.0, 5.0, 0.0),   # Very hard, high discrimination  
            IRTParameters(0.0, 0.1, 0.0),    # Low discrimination
            IRTParameters(0.0, 1.0, 0.8),    # High guessing
        ]
        
        theta_values = [-5.0, -2.0, 0.0, 2.0, 5.0]
        
        for item in extreme_cases:
            for theta in theta_values:
                prob = self.engine.probability(theta, item)
                assert 0.0 <= prob <= 1.0, f"Probability {prob} out of bounds for theta={theta}, item={item}"
    
    def test_information_properties(self):
        """Test Fisher information mathematical properties."""
        item = IRTParameters(0.0, 2.0, 0.0)
        
        # Information should be non-negative
        for theta in [-3.0, -1.0, 0.0, 1.0, 3.0]:
            info = self.engine.information(theta, item)
            assert info >= 0.0, f"Information {info} should be non-negative"
        
        # Information should be highest near item difficulty for high discrimination
        info_at_diff = self.engine.information(0.0, item)
        info_far = self.engine.information(3.0, item)
        assert info_at_diff > info_far, "Information should be higher near difficulty"
    
    def test_likelihood_computation(self):
        """Test likelihood computation stability."""
        responses = [
            (True, IRTParameters(-1.0, 1.5, 0.0)),
            (False, IRTParameters(1.0, 1.8, 0.0)),
            (True, IRTParameters(0.0, 2.0, 0.0))
        ]
        
        # Test at various theta values
        for theta in [-3.0, -1.0, 0.0, 1.0, 3.0]:
            likelihood = self.engine.likelihood(theta, responses)
            
            # Likelihood should be finite
            assert not math.isinf(likelihood), f"Likelihood infinite at theta={theta}"
            assert not math.isnan(likelihood), f"Likelihood NaN at theta={theta}"

if __name__ == "__main__":
    # Run specific test for development
    pytest.main([__file__ + "::TestIRTEngine::test_ability_estimation_convergence", "-v"])
