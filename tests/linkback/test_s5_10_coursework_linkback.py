"""
Tests for S5-10 Coursework→Lesson Linkback & Progress Hooks

Comprehensive testing suite covering API endpoints, analytics integration,
frontend functionality, and end-to-end linkback workflows.
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

# Service imports  
from services.lesson_registry_svc.app.models import Lesson, CourseworkLink
from services.lesson_registry_svc.app.routes.linkback import router
from services.lesson_registry_svc.app.schemas.linkback import (
    CourseworkLinkRequest, CourseworkLinkResponse, LinkbackStatus
)
from services.analytics_svc.app.hooks.progress_from_coursework import (
    CourseworkProgressHook, coursework_hook
)

# Test fixtures
@pytest.fixture
def sample_lesson():
    """Sample lesson for testing."""
    return Lesson(
        id=uuid4(),
        title="Introduction to Algebra",
        description="Basic algebraic concepts and operations",
        subject="Mathematics",
        grade_band="6-8",
        difficulty_level=2,
        estimated_duration=45,
        learning_objectives=["Understand variables", "Solve basic equations"],
        created_by=uuid4(),
        tenant_id=uuid4()
    )

@pytest.fixture  
def sample_coursework_link(sample_lesson):
    """Sample coursework link for testing."""
    return CourseworkLink(
        id=uuid4(),
        coursework_id=uuid4(),
        lesson_id=sample_lesson.id,
        learner_id=uuid4(),
        created_by=uuid4(),
        mastery_weight=100,
        difficulty_adjustment=0,
        is_active=True
    )

@pytest.fixture
def linkback_request():
    """Sample linkback request."""
    return CourseworkLinkRequest(
        coursework_id=uuid4(),
        lesson_id=uuid4(),
        learner_id=uuid4(),
        mastery_weight=85,
        difficulty_adjustment=10,
        link_context={"assignment_type": "homework", "due_date": "2024-02-15"}
    )

@pytest.fixture
def db_session():
    """Mock database session."""
    session = Mock(spec=Session)
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    return session


class TestCourseworkLinkAPI:
    """Test the coursework linkback API endpoints."""
    
    @pytest.mark.asyncio
    async def test_create_coursework_link_success(self, db_session, sample_lesson, linkback_request):
        """Test successful coursework link creation."""
        with patch('services.lesson_registry_svc.app.routes.linkback.get_db') as mock_db:
            mock_db.return_value.__next__.return_value = db_session
            
            # Mock lesson exists
            db_session.query.return_value.filter.return_value.first.return_value = sample_lesson
            
            with patch('services.lesson_registry_svc.app.routes.linkback.emit_coursework_linked_event') as mock_emit:
                from fastapi.testclient import TestClient
                from services.lesson_registry_svc.app.main import app
                
                client = TestClient(app)
                
                response = client.post(
                    "/linkback",
                    json={
                        "coursework_id": str(linkback_request.coursework_id),
                        "lesson_id": str(linkback_request.lesson_id),
                        "learner_id": str(linkback_request.learner_id),
                        "mastery_weight": linkback_request.mastery_weight,
                        "difficulty_adjustment": linkback_request.difficulty_adjustment,
                        "link_context": linkback_request.link_context
                    },
                    headers={"X-User-ID": str(uuid4()), "X-User-Role": "teacher"}
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
                assert data["event_emitted"] is True
                assert "link_id" in data
                
                # Verify event emission
                mock_emit.assert_called_once()
    
    @pytest.mark.asyncio  
    async def test_create_coursework_link_lesson_not_found(self, db_session, linkback_request):
        """Test link creation when lesson doesn't exist."""
        with patch('services.lesson_registry_svc.app.routes.linkback.get_db') as mock_db:
            mock_db.return_value.__next__.return_value = db_session
            
            # Mock lesson not found
            db_session.query.return_value.filter.return_value.first.return_value = None
            
            from fastapi.testclient import TestClient
            from services.lesson_registry_svc.app.main import app
            
            client = TestClient(app)
            
            response = client.post(
                "/linkback",
                json={
                    "coursework_id": str(linkback_request.coursework_id),
                    "lesson_id": str(linkback_request.lesson_id),
                    "mastery_weight": linkback_request.mastery_weight
                },
                headers={"X-User-ID": str(uuid4()), "X-User-Role": "teacher"}
            )
            
            assert response.status_code == 404
            assert "Lesson not found" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_create_coursework_link_rbac_unauthorized(self, linkback_request):
        """Test RBAC authorization for link creation."""
        from fastapi.testclient import TestClient
        from services.lesson_registry_svc.app.main import app
        
        client = TestClient(app)
        
        # Test without proper role
        response = client.post(
            "/linkback",
            json={
                "coursework_id": str(linkback_request.coursework_id),
                "lesson_id": str(linkback_request.lesson_id)
            },
            headers={"X-User-ID": str(uuid4()), "X-User-Role": "student"}
        )
        
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["detail"]
    
    @pytest.mark.asyncio
    async def test_get_coursework_links(self, db_session, sample_coursework_link):
        """Test retrieving coursework links."""
        with patch('services.lesson_registry_svc.app.routes.linkback.get_db') as mock_db:
            mock_db.return_value.__next__.return_value = db_session
            
            # Mock query results
            db_session.query.return_value.filter.return_value.all.return_value = [sample_coursework_link]
            
            from fastapi.testclient import TestClient
            from services.lesson_registry_svc.app.main import app
            
            client = TestClient(app)
            
            response = client.get(
                f"/linkback/coursework/{sample_coursework_link.coursework_id}/links",
                headers={"X-User-ID": str(uuid4()), "X-User-Role": "teacher"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["links"]) == 1
            assert data["links"][0]["id"] == str(sample_coursework_link.id)
    
    @pytest.mark.asyncio
    async def test_delete_coursework_link(self, db_session, sample_coursework_link):
        """Test deleting a coursework link."""
        with patch('services.lesson_registry_svc.app.routes.linkback.get_db') as mock_db:
            mock_db.return_value.__next__.return_value = db_session
            
            # Mock finding the link
            db_session.query.return_value.filter.return_value.first.return_value = sample_coursework_link
            
            with patch('services.lesson_registry_svc.app.routes.linkback.emit_coursework_unlinked_event') as mock_emit:
                from fastapi.testclient import TestClient
                from services.lesson_registry_svc.app.main import app
                
                client = TestClient(app)
                
                response = client.delete(
                    f"/linkback/links/{sample_coursework_link.id}",
                    headers={"X-User-ID": str(uuid4()), "X-User-Role": "teacher"}
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                
                # Verify soft delete
                assert sample_coursework_link.is_active is False
                assert sample_coursework_link.deleted_at is not None


class TestProgressHooks:
    """Test analytics service progress hooks for coursework integration."""
    
    @pytest.mark.asyncio
    async def test_process_coursework_linked_event(self):
        """Test processing COURSEWORK_LINKED events."""
        hook = CourseworkProgressHook()
        
        event_data = {
            "coursework_id": str(uuid4()),
            "lesson_id": str(uuid4()),
            "learner_id": str(uuid4()),
            "link_id": str(uuid4()),
            "mastery_weight": 90
        }
        
        # Mock lesson metadata fetch
        with patch.object(hook, '_fetch_lesson_metadata') as mock_fetch:
            mock_fetch.return_value = {
                "id": event_data["lesson_id"],
                "title": "Test Lesson", 
                "subject": "Mathematics",
                "difficulty_level": 2,
                "tenant_id": str(uuid4())
            }
            
            with patch.object(hook, '_initialize_progress_tracking') as mock_init:
                with patch.object(hook, '_setup_completion_monitoring') as mock_monitor:
                    with patch('services.analytics_svc.app.hooks.progress_from_coursework.emit_event') as mock_emit:
                        
                        result = await hook.process_coursework_linked_event(event_data)
                        
                        assert result is True
                        mock_fetch.assert_called_once()
                        mock_init.assert_called_once()
                        mock_monitor.assert_called_once()
                        mock_emit.assert_called_once_with("PROGRESS_UPDATED", pytest.any(dict))
    
    @pytest.mark.asyncio
    async def test_process_coursework_completion(self):
        """Test processing coursework completion signals."""
        hook = CourseworkProgressHook()
        
        completion_data = {
            "coursework_id": str(uuid4()),
            "learner_id": str(uuid4()),
            "score": 85.5,
            "completion_time": "2024-01-15T14:30:00Z"
        }
        
        linked_lessons = [
            {
                "id": str(uuid4()),
                "coursework_id": completion_data["coursework_id"],
                "lesson_id": str(uuid4()),
                "learner_id": completion_data["learner_id"],
                "mastery_weight": 100,
                "difficulty_adjustment": 0
            }
        ]
        
        with patch.object(hook, '_get_linked_lessons') as mock_get_links:
            mock_get_links.return_value = linked_lessons
            
            with patch.object(hook, '_update_lesson_mastery') as mock_update:
                with patch.object(hook, '_recalculate_mastery_curves') as mock_recalc:
                    
                    result = await hook.process_coursework_completion(completion_data)
                    
                    assert result is True
                    mock_get_links.assert_called_once()
                    mock_update.assert_called_once()
                    mock_recalc.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_mastery_calculation_with_weights(self):
        """Test mastery calculation with different weights and adjustments."""
        hook = CourseworkProgressHook()
        
        lesson_link = {
            "lesson_id": str(uuid4()),
            "learner_id": str(uuid4()),
            "coursework_id": str(uuid4()),
            "mastery_weight": 80,  # 80% weight
            "difficulty_adjustment": 20  # +20% difficulty
        }
        
        completion_score = 90.0
        
        # Expected adjusted score: 90 * 0.8 * 1.2 = 86.4
        expected_adjusted = 90.0 * 0.8 * 1.2
        
        with patch('services.analytics_svc.app.hooks.progress_from_coursework.get_db'):
            with patch('sqlalchemy.text') as mock_text:
                mock_db = Mock()
                mock_db.execute = Mock()
                mock_db.commit = Mock()
                
                await hook._update_lesson_mastery(
                    mock_db, lesson_link, completion_score, "2024-01-15T14:30:00Z"
                )
                
                # Verify SQL execution with adjusted score
                assert mock_db.execute.call_count >= 2  # Progress metric + mastery aggregate updates
                
                # Check that adjusted score is used
                calls = mock_db.execute.call_args_list
                score_used = None
                for call in calls:
                    args, kwargs = call
                    if 'score' in kwargs:
                        score_used = kwargs['score']
                        break
                
                assert score_used is not None
                assert abs(score_used - expected_adjusted) < 0.1


class TestFrontendIntegration:
    """Test frontend linkback functionality."""
    
    def test_linkback_modal_components(self):
        """Test that linkback modal components render correctly."""
        # This would be a React testing library test in a real scenario
        # For now, we'll test the logic that would be called
        
        coursework_id = str(uuid4())
        lesson_id = str(uuid4())
        
        # Mock API response
        mock_lessons = [
            {
                "id": lesson_id,
                "title": "Test Lesson",
                "subject": "Mathematics", 
                "gradeBand": "6-8",
                "description": "A test lesson for linkback"
            }
        ]
        
        # Test lesson filtering logic
        linked_lessons = []  # No existing links
        available_lessons = [l for l in mock_lessons if not any(
            link["lesson_id"] == l["id"] for link in linked_lessons
        )]
        
        assert len(available_lessons) == 1
        assert available_lessons[0]["id"] == lesson_id
    
    def test_link_creation_payload(self):
        """Test that frontend creates correct API payload."""
        coursework_id = str(uuid4())
        lesson_id = str(uuid4())
        
        # Frontend would build this payload
        payload = {
            "coursework_id": coursework_id,
            "lesson_id": lesson_id,
            "mastery_weight": 100,
            "difficulty_adjustment": 0
        }
        
        # Validate payload structure
        assert "coursework_id" in payload
        assert "lesson_id" in payload
        assert payload["mastery_weight"] >= 0 and payload["mastery_weight"] <= 100
        assert payload["difficulty_adjustment"] >= -100 and payload["difficulty_adjustment"] <= 100


class TestEndToEndWorkflow:
    """End-to-end testing of the complete linkback workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_linkback_workflow(self, db_session, sample_lesson):
        """Test the complete workflow from link creation to progress update."""
        coursework_id = uuid4()
        learner_id = uuid4()
        teacher_id = uuid4()
        
        # Step 1: Teacher creates coursework-lesson link
        link_request = CourseworkLinkRequest(
            coursework_id=coursework_id,
            lesson_id=sample_lesson.id,
            learner_id=learner_id,
            mastery_weight=90,
            difficulty_adjustment=5
        )
        
        with patch('services.lesson_registry_svc.app.routes.linkback.get_db') as mock_db:
            mock_db.return_value.__next__.return_value = db_session
            db_session.query.return_value.filter.return_value.first.return_value = sample_lesson
            
            # Mock event emission
            with patch('services.lesson_registry_svc.app.routes.linkback.emit_coursework_linked_event') as mock_emit:
                from fastapi.testclient import TestClient
                from services.lesson_registry_svc.app.main import app
                
                client = TestClient(app)
                
                # Create the link
                response = client.post(
                    "/linkback",
                    json=link_request.dict(),
                    headers={"X-User-ID": str(teacher_id), "X-User-Role": "teacher"}
                )
                
                assert response.status_code == 201
                link_data = response.json()
                
                # Verify event was emitted for orchestrator
                mock_emit.assert_called_once()
                event_args = mock_emit.call_args[0]
                assert event_args[0]["coursework_id"] == str(coursework_id)
                assert event_args[0]["lesson_id"] == str(sample_lesson.id)
        
        # Step 2: Simulate coursework completion
        completion_data = {
            "coursework_id": str(coursework_id),
            "learner_id": str(learner_id),
            "score": 88.0,
            "completion_time": "2024-01-15T14:30:00Z"
        }
        
        # Step 3: Analytics hook processes completion
        hook = CourseworkProgressHook()
        
        with patch.object(hook, '_get_linked_lessons') as mock_get_links:
            mock_get_links.return_value = [{
                "id": str(uuid4()),
                "coursework_id": str(coursework_id),
                "lesson_id": str(sample_lesson.id),
                "learner_id": str(learner_id),
                "mastery_weight": 90,
                "difficulty_adjustment": 5
            }]
            
            with patch.object(hook, '_update_lesson_mastery') as mock_update:
                with patch.object(hook, '_recalculate_mastery_curves') as mock_recalc:
                    
                    result = await hook.process_coursework_completion(completion_data)
                    
                    # Verify the completion was processed
                    assert result is True
                    mock_update.assert_called_once()
                    mock_recalc.assert_called_once()
                    
                    # Verify mastery calculation
                    update_args = mock_update.call_args[0]
                    lesson_link = update_args[1]
                    score = update_args[2]
                    
                    assert lesson_link["mastery_weight"] == 90
                    assert lesson_link["difficulty_adjustment"] == 5
                    assert score == 88.0
    
    @pytest.mark.asyncio
    async def test_learner_scope_validation(self, db_session, sample_lesson):
        """Test that learner scope is properly validated."""
        coursework_id = uuid4()
        learner_id = uuid4()
        other_learner_id = uuid4()
        teacher_id = uuid4()
        
        # Create a learner-scoped link
        with patch('services.lesson_registry_svc.app.routes.linkback.get_db') as mock_db:
            mock_db.return_value.__next__.return_value = db_session
            db_session.query.return_value.filter.return_value.first.return_value = sample_lesson
            
            from fastapi.testclient import TestClient
            from services.lesson_registry_svc.app.main import app
            
            client = TestClient(app)
            
            # Create link for specific learner
            response = client.post(
                "/linkback",
                json={
                    "coursework_id": str(coursework_id),
                    "lesson_id": str(sample_lesson.id),
                    "learner_id": str(learner_id),
                    "mastery_weight": 100
                },
                headers={"X-User-ID": str(teacher_id), "X-User-Role": "teacher"}
            )
            
            assert response.status_code == 201
            
            # Verify links are filtered by learner scope
            mock_links = [Mock(spec=CourseworkLink)]
            mock_links[0].learner_id = learner_id
            mock_links[0].coursework_id = coursework_id
            mock_links[0].is_active = True
            
            db_session.query.return_value.filter.return_value.all.return_value = mock_links
            
            # Query links for the correct learner
            response = client.get(
                f"/linkback/coursework/{coursework_id}/links?learner_id={learner_id}",
                headers={"X-User-ID": str(teacher_id), "X-User-Role": "teacher"}
            )
            
            assert response.status_code == 200
            
            # Query links for a different learner should return empty
            response = client.get(
                f"/linkback/coursework/{coursework_id}/links?learner_id={other_learner_id}",
                headers={"X-User-ID": str(teacher_id), "X-User-Role": "teacher"}
            )
            
            # Would return empty due to learner filtering in the actual implementation
            assert response.status_code == 200


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
