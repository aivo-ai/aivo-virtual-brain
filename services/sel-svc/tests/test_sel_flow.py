# AIVO SEL Service - Test Suite
# S2-12 Implementation - Comprehensive testing for SEL workflows

import pytest
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import (
    SELCheckIn, SELStrategy, SELAlert, ConsentRecord, StrategyUsage, SELReport,
    EmotionType, SELDomain, AlertLevel, StrategyType, GradeBand, ConsentStatus, AlertStatus
)
from app.engine import SELEngine


# Test database setup
TEST_DATABASE_URL = "sqlite:///./test.db"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Create test database tables
Base.metadata.create_all(bind=test_engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


class TestSELService:
    """Test suite for SEL service functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return AsyncClient(app=app, base_url="http://test")
    
    @pytest.fixture
    def db_session(self):
        """Create test database session."""
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @pytest.fixture
    def test_consent(self, db_session):
        """Create test consent record."""
        consent = ConsentRecord(
            tenant_id=uuid.UUID("12345678-1234-5678-9abc-123456789012"),
            student_id=uuid.UUID("87654321-4321-8765-cbaa-210987654321"),
            status=ConsentStatus.GRANTED,
            consent_type="comprehensive",
            data_collection_allowed=True,
            data_sharing_allowed=True,
            alert_notifications_allowed=True,
            ai_processing_allowed=True,
            research_participation_allowed=False,
            parent_guardian_consent=True,
            student_assent=True,
            consent_date=datetime.now(timezone.utc),
            expiration_date=datetime.now(timezone.utc) + timedelta(days=365),
            consent_method="digital_signature",
            consenting_party_name="Test Parent",
            consenting_party_relationship="parent"
        )
        db_session.add(consent)
        db_session.commit()
        db_session.refresh(consent)
        return consent
    
    @pytest.fixture
    def test_headers(self):
        """Create test authorization headers."""
        return {"Authorization": "Bearer test_token_12345"}
    
    # Health Check Tests
    
    @pytest.mark.asyncio
    async def test_health_check(self, client):
        """Test basic health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_detailed_health_check(self, client):
        """Test detailed health check endpoint."""
        response = await client.get("/health/detailed")
        assert response.status_code in [200, 503]  # May be unhealthy in test environment
        data = response.json()
        assert "components" in data
        assert "database" in data["components"]
    
    # SEL Check-in Tests
    
    @pytest.mark.asyncio
    async def test_create_checkin_success(self, client, test_consent, test_headers):
        """Test successful check-in creation."""
        checkin_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "grade_band": "middle_school",
            "primary_emotion": "anxious",
            "emotion_intensity": 7,
            "secondary_emotions": ["worried", "overwhelmed"],
            "triggers": ["upcoming_test", "peer_interaction"],
            "current_situation": "Preparing for math test",
            "location_context": "classroom",
            "social_context": "with_classmates",
            "self_awareness_rating": 6,
            "self_management_rating": 4,
            "social_awareness_rating": 5,
            "relationship_skills_rating": 3,
            "decision_making_rating": 5,
            "energy_level": 5,
            "stress_level": 8,
            "confidence_level": 3,
            "support_needed": True,
            "additional_notes": "Feeling nervous about the test"
        }
        
        response = await client.post("/api/v1/checkin", json=checkin_data, headers=test_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["student_id"] == checkin_data["student_id"]
        assert data["primary_emotion"] == checkin_data["primary_emotion"]
        assert data["emotion_intensity"] == checkin_data["emotion_intensity"]
        assert data["consent_verified"] is True
        assert "processing_results" in data
    
    @pytest.mark.asyncio
    async def test_create_checkin_without_consent(self, client, test_headers):
        """Test check-in creation without proper consent."""
        checkin_data = {
            "tenant_id": "12345678-1234-5678-9abc-123456789012",
            "student_id": "00000000-0000-0000-0000-000000000000",  # No consent for this student
            "grade_band": "middle_school",
            "primary_emotion": "happy",
            "emotion_intensity": 5
        }
        
        response = await client.post("/api/v1/checkin", json=checkin_data, headers=test_headers)
        assert response.status_code == 403
        assert "consent" in response.json()["error"]["message"].lower()
    
    @pytest.mark.asyncio
    async def test_get_checkins(self, client, test_consent, test_headers, db_session):
        """Test retrieving student check-ins."""
        # Create test check-in
        checkin = SELCheckIn(
            tenant_id=test_consent.tenant_id,
            student_id=test_consent.student_id,
            consent_record_id=test_consent.id,
            checkin_date=datetime.now(timezone.utc),
            grade_band=GradeBand.MIDDLE_SCHOOL,
            primary_emotion=EmotionType.HAPPY,
            emotion_intensity=6,
            self_awareness_rating=7,
            self_management_rating=6,
            social_awareness_rating=7,
            relationship_skills_rating=6,
            decision_making_rating=7
        )
        db_session.add(checkin)
        db_session.commit()
        
        response = await client.get(
            f"/api/v1/checkin?student_id={test_consent.student_id}&tenant_id={test_consent.tenant_id}",
            headers=test_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0
        assert data[0]["student_id"] == str(test_consent.student_id)
    
    # SEL Strategy Tests
    
    @pytest.mark.asyncio
    async def test_get_next_strategy(self, client, test_consent, test_headers, db_session):
        """Test personalized strategy generation."""
        # Create test check-in for context
        checkin = SELCheckIn(
            tenant_id=test_consent.tenant_id,
            student_id=test_consent.student_id,
            consent_record_id=test_consent.id,
            checkin_date=datetime.now(timezone.utc),
            grade_band=GradeBand.MIDDLE_SCHOOL,
            primary_emotion=EmotionType.ANXIOUS,
            emotion_intensity=8,
            self_awareness_rating=5,
            self_management_rating=3,  # Low rating should trigger strategy
            social_awareness_rating=6,
            relationship_skills_rating=5,
            decision_making_rating=4,
            support_needed=True
        )
        db_session.add(checkin)
        db_session.commit()
        
        response = await client.get(
            f"/api/v1/strategy/next?student_id={test_consent.student_id}&tenant_id={test_consent.tenant_id}&target_emotion=anxious",
            headers=test_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "strategy_title" in data
        assert "strategy_description" in data
        assert "instructions" in data
        assert "step_by_step" in data
        assert data["target_emotion"] == "anxious"
        assert data["grade_band"] == "middle_school"
    
    @pytest.mark.asyncio
    async def test_record_strategy_usage(self, client, test_consent, test_headers, db_session):
        """Test recording strategy usage and effectiveness."""
        # Create test strategy
        strategy = SELStrategy(
            tenant_id=test_consent.tenant_id,
            student_id=test_consent.student_id,
            strategy_type=StrategyType.BREATHING,
            strategy_title="Deep Breathing Exercise",
            strategy_description="A calming breathing technique",
            instructions="Follow the breathing pattern",
            grade_band=GradeBand.MIDDLE_SCHOOL,
            target_emotion=EmotionType.ANXIOUS,
            target_domain=SELDomain.SELF_MANAGEMENT,
            difficulty_level=2,
            estimated_duration=10,
            step_by_step=["Step 1", "Step 2", "Step 3"]
        )
        db_session.add(strategy)
        db_session.commit()
        db_session.refresh(strategy)
        
        usage_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "duration_used": 8,
            "completion_status": "completed",
            "pre_emotion_rating": 8,
            "post_emotion_rating": 4,
            "helpfulness_rating": 7,
            "difficulty_rating": 3,
            "would_use_again": True,
            "liked_aspects": ["Easy to follow", "Felt calming"]
        }
        
        response = await client.post(
            f"/api/v1/strategy/{strategy.id}/usage",
            json=usage_data,
            headers=test_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["completion_status"] == "completed"
        assert data["effectiveness_score"] == -4  # 4 - 8 = -4 (improvement)
        assert data["helpfulness_rating"] == 7
    
    # SEL Report Tests
    
    @pytest.mark.asyncio
    async def test_generate_report(self, client, test_consent, test_headers, db_session):
        """Test SEL report generation."""
        # Create test data for report
        checkin1 = SELCheckIn(
            tenant_id=test_consent.tenant_id,
            student_id=test_consent.student_id,
            consent_record_id=test_consent.id,
            checkin_date=datetime.now(timezone.utc) - timedelta(days=5),
            grade_band=GradeBand.MIDDLE_SCHOOL,
            primary_emotion=EmotionType.ANXIOUS,
            emotion_intensity=7,
            self_awareness_rating=5,
            self_management_rating=4,
            social_awareness_rating=6,
            relationship_skills_rating=5,
            decision_making_rating=5
        )
        
        checkin2 = SELCheckIn(
            tenant_id=test_consent.tenant_id,
            student_id=test_consent.student_id,
            consent_record_id=test_consent.id,
            checkin_date=datetime.now(timezone.utc) - timedelta(days=2),
            grade_band=GradeBand.MIDDLE_SCHOOL,
            primary_emotion=EmotionType.CALM,
            emotion_intensity=4,
            self_awareness_rating=6,
            self_management_rating=5,
            social_awareness_rating=6,
            relationship_skills_rating=6,
            decision_making_rating=6
        )
        
        db_session.add_all([checkin1, checkin2])
        db_session.commit()
        
        report_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "report_type": "progress_summary",
            "start_date": (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
            "end_date": datetime.now(timezone.utc).isoformat(),
            "report_audience": "educator",
            "privacy_level": "confidential",
            "include_strategies": True,
            "include_alerts": True,
            "include_trends": True,
            "include_detailed_data": False
        }
        
        response = await client.post("/api/v1/report", json=report_data, headers=test_headers)
        assert response.status_code == 201
        
        data = response.json()
        assert data["total_checkins"] == 2
        assert data["most_common_emotion"] in ["anxious", "calm"]
        assert "key_insights" in data
        assert "recommendations" in data
        assert data["consent_verified"] is True
    
    # Alert System Tests
    
    @pytest.mark.asyncio
    async def test_alert_generation_on_threshold_exceed(self, client, test_consent, test_headers, db_session):
        """Test that alerts are generated when thresholds are exceeded."""
        # Create check-in with concerning data that should trigger alerts
        concerning_checkin_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "grade_band": "middle_school",
            "primary_emotion": "overwhelmed",
            "emotion_intensity": 9,
            "secondary_emotions": ["anxious", "frustrated"],
            "self_awareness_rating": 2,  # Very low - should trigger alert
            "self_management_rating": 1,  # Very low - should trigger alert
            "social_awareness_rating": 2,  # Low
            "relationship_skills_rating": 3,
            "decision_making_rating": 2,  # Low
            "stress_level": 9,  # Very high
            "confidence_level": 2,  # Very low
            "support_needed": True
        }
        
        response = await client.post("/api/v1/checkin", json=concerning_checkin_data, headers=test_headers)
        assert response.status_code == 201
        
        # Check that processing results indicate alerts were generated
        data = response.json()
        processing_results = data.get("processing_results", {})
        alerts_generated = processing_results.get("alerts_generated", [])
        
        # Should have multiple alerts due to low ratings and high intensity
        assert len(alerts_generated) > 0
        
        # Verify alert types
        alert_types = [alert["type"] for alert in alerts_generated]
        assert "domain_threshold_exceeded" in alert_types or "risk_factors_detected" in alert_types
    
    @pytest.mark.asyncio
    async def test_get_alerts(self, client, test_consent, test_headers, db_session):
        """Test retrieving generated alerts."""
        # Create test alert
        alert = SELAlert(
            tenant_id=test_consent.tenant_id,
            student_id=test_consent.student_id,
            consent_record_id=test_consent.id,
            alert_type="domain_threshold_exceeded",
            alert_level=AlertLevel.HIGH,
            title="Low Self-Management Rating",
            description="Student rated themselves 2/10 in self-management",
            trigger_domain=SELDomain.SELF_MANAGEMENT,
            trigger_value=2.0,
            threshold_value=3.0,
            risk_score=60.0,
            risk_factors=["low_self_management_rating"],
            consent_verified=True,
            privacy_level="confidential"
        )
        db_session.add(alert)
        db_session.commit()
        
        response = await client.get(
            f"/api/v1/alerts?tenant_id={test_consent.tenant_id}&student_id={test_consent.student_id}",
            headers=test_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) > 0
        assert data[0]["alert_type"] == "domain_threshold_exceeded"
        assert data[0]["alert_level"] == "high"
        assert data[0]["consent_verified"] is True
    
    # Consent Management Tests
    
    @pytest.mark.asyncio
    async def test_create_consent_record(self, client, test_headers):
        """Test creating consent records."""
        consent_data = {
            "tenant_id": "12345678-1234-5678-9abc-123456789012",
            "student_id": "11111111-1111-1111-1111-111111111111",
            "status": "granted",
            "consent_type": "comprehensive",
            "data_collection_allowed": True,
            "data_sharing_allowed": True,
            "alert_notifications_allowed": True,
            "ai_processing_allowed": True,
            "research_participation_allowed": False,
            "parent_guardian_consent": True,
            "student_assent": True,
            "consent_method": "digital_signature",
            "consenting_party_name": "Jane Doe",
            "consenting_party_relationship": "parent"
        }
        
        response = await client.post("/api/v1/consent", json=consent_data, headers=test_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "granted"
        assert data["data_collection_allowed"] is True
        assert data["privacy_compliance"] is True
    
    @pytest.mark.asyncio
    async def test_get_consent_record(self, client, test_consent, test_headers):
        """Test retrieving consent records."""
        response = await client.get(
            f"/api/v1/consent/{test_consent.student_id}?tenant_id={test_consent.tenant_id}",
            headers=test_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["student_id"] == str(test_consent.student_id)
        assert data["status"] == "granted"
        assert data["privacy_compliance"] is True
    
    # Integration Tests
    
    @pytest.mark.asyncio
    async def test_complete_sel_workflow(self, client, test_consent, test_headers, db_session):
        """Test complete SEL workflow: check-in → strategy → usage → report."""
        # Step 1: Create check-in
        checkin_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "grade_band": "middle_school",
            "primary_emotion": "frustrated",
            "emotion_intensity": 6,
            "self_awareness_rating": 5,
            "self_management_rating": 4,
            "social_awareness_rating": 6,
            "relationship_skills_rating": 5,
            "decision_making_rating": 5,
            "support_needed": False
        }
        
        checkin_response = await client.post("/api/v1/checkin", json=checkin_data, headers=test_headers)
        assert checkin_response.status_code == 201
        
        # Step 2: Get personalized strategy
        strategy_response = await client.get(
            f"/api/v1/strategy/next?student_id={test_consent.student_id}&tenant_id={test_consent.tenant_id}",
            headers=test_headers
        )
        assert strategy_response.status_code == 200
        strategy_data = strategy_response.json()
        strategy_id = strategy_data["id"]
        
        # Step 3: Record strategy usage
        usage_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "duration_used": 12,
            "completion_status": "completed",
            "pre_emotion_rating": 6,
            "post_emotion_rating": 3,
            "helpfulness_rating": 8,
            "would_use_again": True
        }
        
        usage_response = await client.post(
            f"/api/v1/strategy/{strategy_id}/usage",
            json=usage_data,
            headers=test_headers
        )
        assert usage_response.status_code == 200
        
        # Step 4: Generate report
        report_data = {
            "tenant_id": str(test_consent.tenant_id),
            "student_id": str(test_consent.student_id),
            "report_type": "progress_summary",
            "start_date": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "end_date": datetime.now(timezone.utc).isoformat(),
            "report_audience": "educator",
            "privacy_level": "confidential",
            "include_strategies": True,
            "include_alerts": True,
            "include_trends": True
        }
        
        report_response = await client.post("/api/v1/report", json=report_data, headers=test_headers)
        assert report_response.status_code == 201
        
        # Verify complete workflow
        report_result = report_response.json()
        assert report_result["total_checkins"] >= 1
        assert report_result["consent_verified"] is True


# Test configuration and utilities
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    # Run tests
    pytest.main(["-v", __file__])
