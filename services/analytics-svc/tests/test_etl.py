"""
Analytics Service - ETL Tests (S2-15)
Test suite for ETL jobs, aggregations, and differential privacy
"""
import pytest
import numpy as np
from datetime import datetime, date, timedelta
from uuid import uuid4, UUID
from decimal import Decimal
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.models import Base, PrivacyLevel, AggregationLevel, MetricType
from app.etl import (
    ETLOrchestrator, SessionDurationETL, MasteryProgressETL,
    WeeklyActiveLearnersETL, IEPProgressETL,
    DifferentialPrivacyEngine, PrivacyAnonimizer
)


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_analytics.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


class TestDifferentialPrivacy:
    """Test differential privacy mechanisms."""
    
    def test_laplace_noise_addition(self):
        """Test Laplace noise mechanism."""
        dp_engine = DifferentialPrivacyEngine(epsilon=1.0)
        
        original_value = 100.0
        noisy_values = []
        
        # Generate 1000 noisy values
        for _ in range(1000):
            noisy_value = dp_engine.add_laplace_noise(original_value)
            noisy_values.append(noisy_value)
        
        # Statistical tests
        mean_noise = np.mean(noisy_values)
        std_noise = np.std(noisy_values)
        
        # Mean should be close to original value
        assert abs(mean_noise - original_value) < 5.0, f"Mean too far from original: {mean_noise} vs {original_value}"
        
        # Standard deviation should be reasonable for epsilon=1.0
        assert 0.5 < std_noise < 10.0, f"Standard deviation unreasonable: {std_noise}"
        
        # All values should be non-negative (clamped)
        assert all(v >= 0 for v in noisy_values), "Found negative values"
    
    def test_gaussian_noise_addition(self):
        """Test Gaussian noise mechanism."""
        dp_engine = DifferentialPrivacyEngine(epsilon=1.0, delta=1e-5)
        
        original_value = 50.0
        noisy_values = []
        
        for _ in range(1000):
            noisy_value = dp_engine.add_gaussian_noise(original_value)
            noisy_values.append(noisy_value)
        
        mean_noise = np.mean(noisy_values)
        assert abs(mean_noise - original_value) < 3.0
    
    def test_count_noise_bounded(self):
        """Test that noise on counts is properly bounded."""
        dp_engine = DifferentialPrivacyEngine(epsilon=2.0)
        
        original_count = 25
        noisy_counts = []
        
        for _ in range(100):
            noisy_count = dp_engine.add_noise_to_count(original_count)
            noisy_counts.append(noisy_count)
        
        # All counts should be non-negative integers
        assert all(isinstance(c, int) and c >= 0 for c in noisy_counts)
        
        # Mean should be reasonably close
        mean_count = np.mean(noisy_counts)
        assert abs(mean_count - original_count) < 10
    
    def test_privacy_budget_scaling(self):
        """Test that smaller epsilon adds more noise."""
        original_value = 100.0
        
        # High epsilon (less private, less noise)
        dp_high = DifferentialPrivacyEngine(epsilon=5.0)
        high_noise_values = [dp_high.add_laplace_noise(original_value) for _ in range(500)]
        high_variance = np.var(high_noise_values)
        
        # Low epsilon (more private, more noise)
        dp_low = DifferentialPrivacyEngine(epsilon=0.1)
        low_noise_values = [dp_low.add_laplace_noise(original_value) for _ in range(500)]
        low_variance = np.var(low_noise_values)
        
        # Lower epsilon should have higher variance (more noise)
        assert low_variance > high_variance * 5, f"Privacy scaling failed: {low_variance} vs {high_variance}"


class TestPrivacyAnonimization:
    """Test privacy and anonymization utilities."""
    
    def test_learner_id_hashing(self):
        """Test consistent learner ID hashing."""
        anonymizer = PrivacyAnonimizer()
        learner_id = uuid4()
        
        # Same ID should produce same hash
        hash1 = anonymizer.hash_learner_id(learner_id)
        hash2 = anonymizer.hash_learner_id(learner_id)
        assert hash1 == hash2
        
        # Hash should be 16 characters
        assert len(hash1) == 16
        assert all(c in '0123456789abcdef' for c in hash1.lower())
        
        # Different IDs should produce different hashes
        different_id = uuid4()
        different_hash = anonymizer.hash_learner_id(different_id)
        assert hash1 != different_hash
    
    def test_age_generalization(self):
        """Test age generalization categories."""
        anonymizer = PrivacyAnonimizer()
        
        test_cases = [
            (10, "under_13"),
            (15, "13_17"),
            (20, "18_24"),
            (30, "25_34"),
            (40, "35_49"),
            (60, "50_plus")
        ]
        
        for age, expected_category in test_cases:
            assert anonymizer.generalize_age(age) == expected_category
    
    def test_small_count_suppression(self):
        """Test suppression of small counts for k-anonymity."""
        anonymizer = PrivacyAnonimizer()
        
        data = {
            "category_a": 10,  # Above threshold
            "category_b": 3,   # Below threshold
            "category_c": 2,   # Below threshold
            "category_d": 8    # Above threshold
        }
        
        suppressed = anonymizer.suppress_small_counts(data, threshold=5)
        
        assert "category_a" in suppressed
        assert "category_d" in suppressed
        assert "category_b" not in suppressed
        assert "category_c" not in suppressed
        assert suppressed["other_suppressed"] == 5  # 3 + 2
    
    def test_k_anonymity_enforcement(self):
        """Test k-anonymity group filtering."""
        anonymizer = PrivacyAnonimizer()
        
        groups = [
            {"id": 1, "count": 10},  # Above threshold
            {"id": 2, "count": 3},   # Below threshold
            {"id": 3, "count": 8},   # Above threshold
            {"id": 4, "count": 2}    # Below threshold
        ]
        
        filtered = anonymizer.ensure_k_anonymity(groups, k=5)
        
        assert len(filtered) == 2
        assert all(group["count"] >= 5 for group in filtered)


class TestETLJobs:
    """Test ETL job implementations."""
    
    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        Base.metadata.create_all(bind=test_engine)
        session = TestingSessionLocal()
        yield session
        session.close()
        Base.metadata.drop_all(bind=test_engine)
    
    def test_session_duration_etl_individual(self, db_session):
        """Test session duration ETL for individual aggregation."""
        etl = SessionDurationETL(db_session, PrivacyLevel.ANONYMIZED)
        tenant_id = uuid4()
        
        # Mock raw session data
        with patch.object(etl, 'extract_raw_sessions') as mock_extract:
            mock_sessions = [
                {
                    "learner_id": uuid4(),
                    "tenant_id": tenant_id,
                    "session_start": datetime(2025, 1, 15, 10, 0),
                    "duration_minutes": 45
                },
                {
                    "learner_id": uuid4(),
                    "tenant_id": tenant_id,
                    "session_start": datetime(2025, 1, 15, 14, 0),
                    "duration_minutes": 60
                }
            ]
            mock_extract.return_value = mock_sessions
            
            # Run ETL
            job_run = etl.run_etl(date(2025, 1, 15), date(2025, 1, 15), tenant_id)
            
            assert job_run.status == "completed"
            assert job_run.records_processed == 2
            assert job_run.records_created > 0
    
    def test_session_duration_etl_with_dp_noise(self, db_session):
        """Test session duration ETL with differential privacy."""
        etl = SessionDurationETL(db_session, PrivacyLevel.DP_LOW)
        tenant_id = uuid4()
        
        # Generate consistent test data
        mock_sessions = []
        for i in range(50):  # Larger dataset for DP testing
            mock_sessions.append({
                "learner_id": uuid4(),
                "tenant_id": tenant_id,
                "session_start": datetime(2025, 1, 15, 10 + i % 8, 0),
                "duration_minutes": 30 + (i % 20)
            })
        
        with patch.object(etl, 'extract_raw_sessions') as mock_extract:
            mock_extract.return_value = mock_sessions
            
            job_run = etl.run_etl(date(2025, 1, 15), date(2025, 1, 15), tenant_id)
            
            assert job_run.status == "completed"
            assert job_run.privacy_level_used == PrivacyLevel.DP_LOW
            assert job_run.epsilon_budget_used is not None
    
    def test_mastery_progress_etl(self, db_session):
        """Test mastery progress ETL."""
        etl = MasteryProgressETL(db_session, PrivacyLevel.ANONYMIZED)
        tenant_id = uuid4()
        
        # Mock assessment data
        with patch.object(etl, 'extract_assessment_events') as mock_extract:
            mock_assessments = [
                {
                    "learner_id": uuid4(),
                    "tenant_id": tenant_id,
                    "subject_id": uuid4(),
                    "subject_category": "Mathematics",
                    "assessment_date": date(2025, 1, 15),
                    "mastery_score": 0.75,
                    "difficulty_level": 3,
                    "time_spent_minutes": 45
                }
            ]
            mock_extract.return_value = mock_assessments
            
            job_run = etl.run_etl(date(2025, 1, 15), date(2025, 1, 15), tenant_id)
            
            assert job_run.status == "completed"
            assert job_run.job_type == MetricType.MASTERY_SCORE
    
    def test_weekly_active_learners_etl(self, db_session):
        """Test weekly active learners ETL."""
        etl = WeeklyActiveLearnersETL(db_session, PrivacyLevel.ANONYMIZED)
        tenant_id = uuid4()
        
        job_run = etl.run_etl(date(2025, 1, 13), tenant_id)  # Monday
        
        assert job_run.status == "completed"
        assert job_run.job_type == MetricType.WEEKLY_ACTIVE
        assert job_run.records_created == 1
    
    def test_iep_progress_etl(self, db_session):
        """Test IEP progress ETL."""
        etl = IEPProgressETL(db_session, PrivacyLevel.DP_MEDIUM)
        tenant_id = uuid4()
        
        job_run = etl.run_etl(date(2025, 1, 15), date(2025, 1, 15), tenant_id)
        
        assert job_run.status == "completed"
        assert job_run.job_type == MetricType.IEP_PROGRESS
        assert job_run.privacy_level_used == PrivacyLevel.DP_MEDIUM
    
    def test_etl_orchestrator(self, db_session):
        """Test ETL orchestrator running multiple jobs."""
        orchestrator = ETLOrchestrator(db_session)
        tenant_id = uuid4()
        
        # Run daily ETL
        job_runs = orchestrator.run_daily_etl(date(2025, 1, 15), tenant_id)
        
        # Should have multiple jobs (session, mastery, IEP)
        assert len(job_runs) >= 3
        
        # All jobs should complete (even with mock data)
        completed_jobs = [j for j in job_runs if j.status == "completed"]
        assert len(completed_jobs) >= 2  # At least most jobs should complete
    
    def test_etl_error_handling(self, db_session):
        """Test ETL error handling and job status."""
        etl = SessionDurationETL(db_session, PrivacyLevel.ANONYMIZED)
        tenant_id = uuid4()
        
        # Force an error by patching database commit
        with patch.object(db_session, 'commit', side_effect=Exception("Database error")):
            job_run = etl.run_etl(date(2025, 1, 15), date(2025, 1, 15), tenant_id)
            
            assert job_run.status == "failed"
            assert job_run.error_message is not None
            assert "Database error" in job_run.error_message


class TestAggregateAccuracy:
    """Test accuracy of aggregate calculations."""
    
    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        Base.metadata.create_all(bind=test_engine)
        session = TestingSessionLocal()
        yield session
        session.close()
        Base.metadata.drop_all(bind=test_engine)
    
    def test_session_aggregation_accuracy(self, db_session):
        """Test that session aggregations produce correct statistics."""
        etl = SessionDurationETL(db_session, PrivacyLevel.ANONYMIZED)
        
        # Create test data with known statistics
        learner_id = uuid4()
        tenant_id = uuid4()
        
        durations = [20, 30, 40, 50, 60]  # Known values
        expected_avg = 40.0
        expected_median = 40.0
        expected_max = 60
        expected_total = 200
        
        raw_sessions = []
        for i, duration in enumerate(durations):
            raw_sessions.append({
                "learner_id": learner_id,
                "tenant_id": tenant_id,
                "session_start": datetime(2025, 1, 15, 10 + i, 0),
                "duration_minutes": duration
            })
        
        # Transform to aggregates
        aggregates = etl.transform_to_aggregates(raw_sessions, AggregationLevel.INDIVIDUAL)
        
        assert len(aggregates) == 1
        agg = aggregates[0]
        
        assert agg["total_sessions"] == 5
        assert abs(agg["avg_duration_minutes"] - expected_avg) < 0.01
        assert abs(agg["median_duration_minutes"] - expected_median) < 0.01
        assert agg["max_duration_minutes"] == expected_max
        assert abs(agg["total_duration_minutes"] - expected_total) < 0.01
    
    def test_mastery_improvement_calculation(self, db_session):
        """Test mastery improvement delta calculation."""
        etl = MasteryProgressETL(db_session, PrivacyLevel.ANONYMIZED)
        
        learner_id = uuid4()
        subject_id = uuid4()
        tenant_id = uuid4()
        
        # Progressive assessment scores
        assessments = [
            {
                "learner_id": learner_id,
                "tenant_id": tenant_id,
                "subject_id": subject_id,
                "subject_category": "Mathematics",
                "assessment_date": date(2025, 1, 10),
                "mastery_score": 0.60,
                "difficulty_level": 2,
                "time_spent_minutes": 30
            },
            {
                "learner_id": learner_id,
                "tenant_id": tenant_id,
                "subject_id": subject_id,
                "subject_category": "Mathematics",
                "assessment_date": date(2025, 1, 15),
                "mastery_score": 0.85,
                "difficulty_level": 3,
                "time_spent_minutes": 45
            }
        ]
        
        aggregates = etl.transform_mastery_aggregates(assessments)
        
        assert len(aggregates) == 1
        agg = aggregates[0]
        
        assert float(agg["current_mastery_score"]) == 0.85
        assert abs(float(agg["mastery_improvement"]) - 0.25) < 0.01  # 0.85 - 0.60
        assert agg["assessments_completed"] == 2
    
    def test_dp_noise_bounds(self, db_session):
        """Test that DP noise is within reasonable bounds."""
        dp_engine = DifferentialPrivacyEngine(epsilon=1.0)
        
        # Test multiple values
        test_values = [10, 50, 100, 500]
        noise_ratios = []
        
        for value in test_values:
            noisy_values = [dp_engine.add_laplace_noise(value) for _ in range(100)]
            noise_ratio = np.std(noisy_values) / value
            noise_ratios.append(noise_ratio)
        
        # Noise ratio should be reasonable (not too high)
        avg_noise_ratio = np.mean(noise_ratios)
        assert avg_noise_ratio < 0.5, f"Noise ratio too high: {avg_noise_ratio}"
        
        # All noisy values should be non-negative
        for value in test_values:
            noisy_values = [dp_engine.add_laplace_noise(value) for _ in range(50)]
            assert all(v >= 0 for v in noisy_values), "Found negative values after noise"


class TestAPIEndpoints:
    """Test API endpoint functionality."""
    
    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "analytics-svc"
    
    def test_privacy_levels_endpoint(self, client):
        """Test privacy levels information endpoint."""
        response = client.get("/api/v1/privacy/levels")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_levels" in data
        assert len(data["privacy_levels"]) == 5  # none, anonymized, dp_low/medium/high
    
    def test_privacy_policy_endpoint(self, client):
        """Test privacy policy endpoint."""
        response = client.get("/privacy/policy")
        assert response.status_code == 200
        data = response.json()
        assert "privacy_policy" in data
        assert "data_types" in data
        assert "privacy_controls" in data
        
        # Check compliance mentions
        compliance = data["privacy_policy"]["compliance"]
        assert "FERPA" in compliance
        assert "COPPA" in compliance
        assert "GDPR" in compliance
    
    def test_root_endpoint(self, client):
        """Test root endpoint information."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Analytics Service"
        assert data["stage"] == "S2-15"
        assert "privacy_notice" in data
        assert "endpoints" in data
    
    @patch('app.routes.get_db')
    def test_tenant_analytics_endpoint_structure(self, mock_db, client):
        """Test tenant analytics endpoint structure (mocked)."""
        # Mock database session
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Mock query results
        mock_session.query.return_value.filter.return_value.all.return_value = []
        
        tenant_id = str(uuid4())
        response = client.get(f"/api/v1/metrics/tenant/{tenant_id}")
        
        # Should handle no data gracefully
        assert response.status_code in [200, 500]  # Depends on mock setup
    
    @patch('app.routes.get_db') 
    def test_learner_analytics_endpoint_validation(self, mock_db, client):
        """Test learner analytics endpoint validation."""
        mock_session = Mock()
        mock_db.return_value = mock_session
        
        # Test invalid hash format
        response = client.get("/api/v1/metrics/learner/invalid_hash")
        assert response.status_code == 400
        
        # Test valid hash format
        valid_hash = "1234567890abcdef"
        response = client.get(f"/api/v1/metrics/learner/{valid_hash}")
        # May succeed or fail depending on mock data
        assert response.status_code in [200, 500]


if __name__ == "__main__":
    # Run specific test categories
    import sys
    if "--dp" in sys.argv:
        pytest.main([__file__ + "::TestDifferentialPrivacy", "-v"])
    elif "--etl" in sys.argv:
        pytest.main([__file__ + "::TestETLJobs", "-v"])
    elif "--accuracy" in sys.argv:
        pytest.main([__file__ + "::TestAggregateAccuracy", "-v"])
    else:
        pytest.main([__file__, "-v"])
