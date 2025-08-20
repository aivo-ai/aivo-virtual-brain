"""
Comprehensive Test Suite for Audit Service
Tests for audit logging, access reviews, and JIT support sessions
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import Mock, patch, AsyncMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

from services.audit_svc.app.models import (
    AuditEvent, AuditEventType, AuditSeverity, DataAccessLog, AccessReview, 
    SupportSession, AccessReviewItem, UserRole, DataClassification,
    SupportSessionStatus, AccessReviewStatus, CreateAuditEventRequest
)
from services.audit_svc.app.audit_logger import AuditLogger
from services.audit_svc.app.access_reviewer import AccessReviewer
from services.audit_svc.app.support_manager import SupportManager
from services.audit_svc.app.main import app


class TestAuditLogger:
    """Test audit logging functionality"""
    
    @pytest.fixture
    async def audit_logger(self):
        """Create audit logger instance"""
        return AuditLogger()
    
    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool"""
        with patch('services.audit_svc.app.audit_logger.get_db_pool') as mock:
            mock_conn = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock.return_value = mock_pool
            yield mock_pool
    
    @pytest.mark.asyncio
    async def test_log_audit_event(self, audit_logger, mock_db_pool):
        """Test basic audit event logging"""
        
        with patch('services.audit_svc.app.audit_logger.log_audit_event') as mock_log:
            mock_log.return_value = uuid4()
            
            event = await audit_logger.log_event(
                event_type=AuditEventType.DATA_READ,
                action="user_data_access",
                resource="student_records",
                actor_id=uuid4(),
                actor_type=UserRole.TEACHER,
                actor_email="teacher@aivo.com",
                target_classification=DataClassification.CONFIDENTIAL,
                tenant_id=uuid4()
            )
            
            assert event.event_type == AuditEventType.DATA_READ
            assert event.action == "user_data_access"
            assert event.resource == "student_records"
            assert event.actor_type == UserRole.TEACHER
            assert event.target_classification == DataClassification.CONFIDENTIAL
            
            mock_log.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_log_sensitive_data_access(self, audit_logger, mock_db_pool):
        """Test sensitive data access logging"""
        
        user_id = uuid4()
        tenant_id = uuid4()
        session_id = "session_123"
        
        with patch('services.audit_svc.app.audit_logger.log_data_access') as mock_log_data, \
             patch.object(audit_logger, 'log_event') as mock_log_event:
            
            mock_log_data.return_value = uuid4()
            mock_log_event.return_value = Mock()
            
            log_id = await audit_logger.log_sensitive_data_access(
                user_id=user_id,
                user_role=UserRole.TEACHER,
                user_email="teacher@aivo.com",
                data_type="student_grades",
                operation="read",
                purpose="review_assignments",
                tenant_id=tenant_id,
                session_id=session_id,
                data_classification=DataClassification.CONFIDENTIAL,
                justification="Quarterly grade review",
                records_affected=25
            )
            
            assert log_id is not None
            mock_log_data.assert_called_once()
            mock_log_event.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_query_audit_events(self, audit_logger, mock_db_pool):
        """Test querying audit events with filters"""
        
        from services.audit_svc.app.models import AuditQuery
        
        # Mock database response
        mock_rows = [
            {
                'id': uuid4(),
                'timestamp': datetime.utcnow(),
                'event_type': 'data_read',
                'severity': 'medium',
                'actor_type': 'teacher',
                'target_classification': 'confidential',
                'action': 'view_grades',
                'resource': 'student_data',
                'outcome': 'success',
                'actor_id': uuid4(),
                'actor_email': 'teacher@aivo.com',
                'actor_ip': None,
                'actor_user_agent': None,
                'target_id': None,
                'target_type': None,
                'tenant_id': uuid4(),
                'session_id': None,
                'request_id': None,
                'reason': None,
                'metadata': {},
                'retention_days': 2555
            }
        ]
        
        mock_db_pool.acquire.return_value.__aenter__.return_value.fetch.return_value = mock_rows
        
        query = AuditQuery(
            event_types=[AuditEventType.DATA_READ],
            severities=[AuditSeverity.MEDIUM],
            tenant_id=uuid4(),
            page=1,
            page_size=50
        )
        
        events = await audit_logger.query_events(query)
        
        assert len(events) == 1
        assert events[0].event_type == AuditEventType.DATA_READ
        assert events[0].action == "view_grades"
    
    @pytest.mark.asyncio
    async def test_generate_summary_report(self, audit_logger, mock_db_pool):
        """Test audit summary report generation"""
        
        tenant_id = uuid4()
        start_date = datetime.utcnow() - timedelta(days=30)
        end_date = datetime.utcnow()
        
        # Mock database responses
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchval.side_effect = [100, 5, 2, 1, 0]  # Various counts
        mock_conn.fetch.side_effect = [
            [{'event_type': 'data_read', 'count': 50}, {'event_type': 'login_success', 'count': 30}],
            [{'severity': 'medium', 'count': 70}, {'severity': 'low', 'count': 30}],
            [{'actor_id': uuid4(), 'actor_email': 'user@aivo.com', 'event_count': 20}],
            [{'resource': 'student_data', 'access_count': 40}],
            [{'id': uuid4(), 'timestamp': datetime.utcnow(), 'event_type': 'permission_denied', 
              'action': 'unauthorized_access', 'resource': 'admin_panel', 'severity': 'high', 'outcome': 'failure'}]
        ]
        
        report = await audit_logger.generate_summary_report(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date
        )
        
        assert report.tenant_id == tenant_id
        assert report.total_events == 100
        assert report.unique_actors == 5
        assert report.failed_events == 2
        assert 'data_read' in report.events_by_type
        assert 'medium' in report.events_by_severity


class TestAccessReviewer:
    """Test access review functionality"""
    
    @pytest.fixture
    async def access_reviewer(self):
        """Create access reviewer instance"""
        return AccessReviewer()
    
    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool"""
        with patch('services.audit_svc.app.access_reviewer.get_db_pool') as mock:
            mock_conn = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock.return_value = mock_pool
            yield mock_pool
    
    @pytest.mark.asyncio
    async def test_start_quarterly_review(self, access_reviewer, mock_db_pool):
        """Test starting quarterly access review"""
        
        tenant_id = uuid4()
        reviewer_id = uuid4()
        reviewer_email = "security@aivo.com"
        
        review = await access_reviewer.start_review(
            tenant_id=tenant_id,
            reviewer_id=reviewer_id,
            reviewer_email=reviewer_email,
            review_type="quarterly",
            roles_to_review=[UserRole.TEACHER, UserRole.ADMIN]
        )
        
        assert review.tenant_id == tenant_id
        assert review.reviewer_id == reviewer_id
        assert review.review_type == "quarterly"
        assert UserRole.TEACHER in review.roles_to_review
        assert review.status == AccessReviewStatus.IN_PROGRESS
        
        # Verify database calls
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        assert mock_conn.execute.call_count >= 2  # Insert review + update status
    
    @pytest.mark.asyncio
    async def test_review_access_item_certification(self, access_reviewer, mock_db_pool):
        """Test certifying user access during review"""
        
        review_id = uuid4()
        item_id = uuid4()
        tenant_id = uuid4()
        reviewer_id = uuid4()
        
        # Mock item exists
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = {
            'id': item_id,
            'user_id': uuid4(),
            'user_email': 'user@aivo.com',
            'tenant_id': tenant_id
        }
        
        await access_reviewer.review_item(
            review_id=review_id,
            item_id=item_id,
            status="certified",
            reviewer_notes="Access appropriate for role",
            changes_to_make=[],
            reviewer_id=reviewer_id,
            tenant_id=tenant_id
        )
        
        # Verify update call
        mock_conn.execute.assert_called()
        update_call = mock_conn.execute.call_args_list[-2]  # Second to last call
        assert "UPDATE access_review_items" in update_call[0][0]
        assert "certified" in str(update_call[0])
    
    @pytest.mark.asyncio
    async def test_review_access_item_revocation(self, access_reviewer, mock_db_pool):
        """Test revoking user access during review"""
        
        review_id = uuid4()
        item_id = uuid4()
        user_id = uuid4()
        tenant_id = uuid4()
        reviewer_id = uuid4()
        
        # Mock item exists
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = {
            'id': item_id,
            'user_id': user_id,
            'user_email': 'user@aivo.com',
            'tenant_id': tenant_id
        }
        
        changes_to_make = [
            {"action": "revoke_permission", "target": "admin_access", "value": None},
            {"action": "remove_role", "target": "department_lead", "value": None}
        ]
        
        await access_reviewer.review_item(
            review_id=review_id,
            item_id=item_id,
            status="revoked",
            reviewer_notes="Excessive permissions for current role",
            changes_to_make=changes_to_make,
            reviewer_id=reviewer_id,
            tenant_id=tenant_id
        )
        
        # Verify access changes applied
        mock_conn.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_get_overdue_reviews(self, access_reviewer, mock_db_pool):
        """Test getting overdue access reviews"""
        
        tenant_id = uuid4()
        
        # Mock overdue review
        overdue_review_data = {
            'id': uuid4(),
            'created_at': datetime.utcnow() - timedelta(days=60),
            'updated_at': datetime.utcnow() - timedelta(days=30),
            'tenant_id': tenant_id,
            'review_type': 'quarterly',
            'review_period_start': datetime.utcnow() - timedelta(days=90),
            'review_period_end': datetime.utcnow() - timedelta(days=30),
            'status': 'in_progress',
            'due_date': datetime.utcnow() - timedelta(days=5),  # Overdue
            'completed_at': None,
            'reviewer_id': uuid4(),
            'reviewer_email': 'security@aivo.com',
            'roles_to_review': ['teacher'],
            'departments': [],
            'risk_levels': [],
            'total_users_reviewed': 5,
            'access_certified': 3,
            'access_revoked': 1,
            'access_modified': 1,
            'notes': None,
            'attachments': []
        }
        
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetch.return_value = [overdue_review_data]
        
        overdue_reviews = await access_reviewer.get_overdue_reviews(tenant_id)
        
        assert len(overdue_reviews) == 1
        assert overdue_reviews[0].tenant_id == tenant_id
        assert overdue_reviews[0].due_date < datetime.utcnow()


class TestSupportManager:
    """Test JIT support session functionality"""
    
    @pytest.fixture
    async def support_manager(self):
        """Create support manager instance"""
        return SupportManager()
    
    @pytest.fixture
    def mock_db_pool(self):
        """Mock database pool"""
        with patch('services.audit_svc.app.support_manager.get_db_pool') as mock:
            mock_conn = AsyncMock()
            mock_pool = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
            mock.return_value = mock_pool
            yield mock_pool
    
    @pytest.mark.asyncio
    async def test_create_support_session(self, support_manager, mock_db_pool):
        """Test creating support session request"""
        
        learner_id = uuid4()
        guardian_id = uuid4()
        tenant_id = uuid4()
        
        session = await support_manager.create_session(
            learner_id=learner_id,
            guardian_id=guardian_id,
            reason="Student unable to access assignments",
            description="Login issues preventing homework submission",
            urgency="high",
            max_duration_minutes=30,
            allowed_data_types=["learning_progress", "assignments"],
            tenant_id=tenant_id
        )
        
        assert session.learner_id == learner_id
        assert session.guardian_id == guardian_id
        assert session.reason == "Student unable to access assignments"
        assert session.urgency == "high"
        assert session.max_duration_minutes == 30
        assert "learning_progress" in session.allowed_data_types
        assert session.status == SupportSessionStatus.REQUESTED
        
        # Verify database insert
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        assert mock_conn.execute.call_count >= 2  # Insert + update for approval request
    
    @pytest.mark.asyncio
    async def test_approve_support_session(self, support_manager, mock_db_pool):
        """Test guardian approving support session"""
        
        session_id = uuid4()
        guardian_id = uuid4()
        tenant_id = uuid4()
        
        # Mock existing session
        session_data = {
            'id': session_id,
            'learner_id': uuid4(),
            'guardian_id': guardian_id,
            'status': 'pending_approval',
            'reason': 'Technical issue',
            'description': None,
            'urgency': 'normal',
            'requested_at': datetime.utcnow(),
            'approval_requested_at': datetime.utcnow(),
            'approved_at': None,
            'denied_at': None,
            'approval_reason': None,
            'session_start': None,
            'session_end': None,
            'max_duration_minutes': 60,
            'read_only': True,
            'allowed_data_types': [],
            'restricted_data_types': [],
            'access_token': None,
            'token_expires_at': None,
            'actions_performed': [],
            'tenant_id': tenant_id,
            'ip_address': None,
            'user_agent': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'support_agent_id': None
        }
        
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = [session_data, {**session_data, 'status': 'approved'}]
        
        approved_session = await support_manager.approve_session(
            session_id=session_id,
            approved=True,
            reason="Approved for technical assistance",
            approver_id=guardian_id,
            tenant_id=tenant_id
        )
        
        assert approved_session.guardian_id == guardian_id
        # Status would be updated in database
        mock_conn.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_start_support_session_with_token(self, support_manager, mock_db_pool):
        """Test starting support session and issuing access token"""
        
        session_id = uuid4()
        support_agent_id = uuid4()
        tenant_id = uuid4()
        
        # Mock approved session
        session_data = {
            'id': session_id,
            'learner_id': uuid4(),
            'guardian_id': uuid4(),
            'status': 'approved',
            'reason': 'Technical issue',
            'description': None,
            'urgency': 'normal',
            'requested_at': datetime.utcnow(),
            'approval_requested_at': datetime.utcnow(),
            'approved_at': datetime.utcnow(),
            'denied_at': None,
            'approval_reason': 'Approved for assistance',
            'session_start': None,
            'session_end': None,
            'max_duration_minutes': 60,
            'read_only': True,
            'allowed_data_types': ['learning_progress'],
            'restricted_data_types': [],
            'access_token': None,
            'token_expires_at': None,
            'actions_performed': [],
            'tenant_id': tenant_id,
            'ip_address': None,
            'user_agent': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'support_agent_id': None
        }
        
        active_session_data = {
            **session_data,
            'status': 'active',
            'support_agent_id': support_agent_id,
            'session_start': datetime.utcnow(),
            'access_token': 'support_token123',
            'token_expires_at': datetime.utcnow() + timedelta(hours=1)
        }
        
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = [session_data, active_session_data]
        
        session, token = await support_manager.start_session(
            session_id=session_id,
            support_agent_id=support_agent_id,
            tenant_id=tenant_id
        )
        
        assert session.support_agent_id == support_agent_id
        assert token.startswith('support_')
        assert len(token) > 20  # Ensure it's a substantial token
        
        # Verify session started in database
        mock_conn.execute.assert_called()
    
    @pytest.mark.asyncio
    async def test_validate_access_token(self, support_manager, mock_db_pool):
        """Test validating support access token"""
        
        access_token = "support_valid_token_123"
        tenant_id = uuid4()
        
        # Mock active session with valid token
        session_data = {
            'id': uuid4(),
            'learner_id': uuid4(),
            'guardian_id': uuid4(),
            'status': 'active',
            'reason': 'Technical assistance',
            'description': None,
            'urgency': 'normal',
            'requested_at': datetime.utcnow() - timedelta(minutes=30),
            'approval_requested_at': datetime.utcnow() - timedelta(minutes=25),
            'approved_at': datetime.utcnow() - timedelta(minutes=20),
            'denied_at': None,
            'approval_reason': 'Approved',
            'session_start': datetime.utcnow() - timedelta(minutes=10),
            'session_end': None,
            'max_duration_minutes': 60,
            'read_only': True,
            'allowed_data_types': ['learning_progress'],
            'restricted_data_types': [],
            'access_token': access_token,
            'token_expires_at': datetime.utcnow() + timedelta(minutes=50),
            'actions_performed': [],
            'tenant_id': tenant_id,
            'ip_address': None,
            'user_agent': None,
            'created_at': datetime.utcnow() - timedelta(minutes=30),
            'updated_at': datetime.utcnow() - timedelta(minutes=10),
            'support_agent_id': uuid4()
        }
        
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = session_data
        
        session = await support_manager.validate_access_token(access_token, tenant_id)
        
        assert session is not None
        assert session.access_token == access_token
        assert session.status == SupportSessionStatus.ACTIVE
    
    @pytest.mark.asyncio
    async def test_validate_expired_token(self, support_manager, mock_db_pool):
        """Test validating expired support token"""
        
        access_token = "support_expired_token_123"
        tenant_id = uuid4()
        
        # Mock session with expired token
        session_data = {
            'id': uuid4(),
            'learner_id': uuid4(),
            'guardian_id': uuid4(),
            'status': 'active',
            'reason': 'Technical assistance',
            'description': None,
            'urgency': 'normal',
            'requested_at': datetime.utcnow() - timedelta(hours=2),
            'approval_requested_at': datetime.utcnow() - timedelta(hours=2),
            'approved_at': datetime.utcnow() - timedelta(hours=2),
            'denied_at': None,
            'approval_reason': 'Approved',
            'session_start': datetime.utcnow() - timedelta(hours=2),
            'session_end': None,
            'max_duration_minutes': 60,
            'read_only': True,
            'allowed_data_types': ['learning_progress'],
            'restricted_data_types': [],
            'access_token': access_token,
            'token_expires_at': datetime.utcnow() - timedelta(minutes=30),  # Expired
            'actions_performed': [],
            'tenant_id': tenant_id,
            'ip_address': None,
            'user_agent': None,
            'created_at': datetime.utcnow() - timedelta(hours=2),
            'updated_at': datetime.utcnow() - timedelta(hours=2),
            'support_agent_id': uuid4()
        }
        
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.return_value = session_data
        
        session = await support_manager.validate_access_token(access_token, tenant_id)
        
        assert session is None  # Should return None for expired token
        
        # Verify session marked as expired
        mock_conn.execute.assert_called()
        expire_call = mock_conn.execute.call_args
        assert "UPDATE support_sessions" in expire_call[0][0]
        assert "expired" in str(expire_call[0])
    
    @pytest.mark.asyncio
    async def test_end_support_session(self, support_manager, mock_db_pool):
        """Test ending active support session"""
        
        session_id = uuid4()
        ended_by = uuid4()
        tenant_id = uuid4()
        
        # Mock active session
        session_data = {
            'id': session_id,
            'learner_id': uuid4(),
            'guardian_id': uuid4(),
            'status': 'active',
            'reason': 'Technical assistance',
            'description': None,
            'urgency': 'normal',
            'requested_at': datetime.utcnow() - timedelta(minutes=30),
            'approval_requested_at': datetime.utcnow() - timedelta(minutes=25),
            'approved_at': datetime.utcnow() - timedelta(minutes=20),
            'denied_at': None,
            'approval_reason': 'Approved',
            'session_start': datetime.utcnow() - timedelta(minutes=15),
            'session_end': None,
            'max_duration_minutes': 60,
            'read_only': True,
            'allowed_data_types': ['learning_progress'],
            'restricted_data_types': [],
            'access_token': 'support_token123',
            'token_expires_at': datetime.utcnow() + timedelta(minutes=45),
            'actions_performed': [],
            'tenant_id': tenant_id,
            'ip_address': None,
            'user_agent': None,
            'created_at': datetime.utcnow() - timedelta(minutes=30),
            'updated_at': datetime.utcnow() - timedelta(minutes=15),
            'support_agent_id': uuid4()
        }
        
        completed_session_data = {
            **session_data,
            'status': 'completed',
            'session_end': datetime.utcnow(),
            'access_token': None
        }
        
        mock_conn = mock_db_pool.acquire.return_value.__aenter__.return_value
        mock_conn.fetchrow.side_effect = [session_data, completed_session_data]
        
        ended_session = await support_manager.end_session(
            session_id=session_id,
            ended_by=ended_by,
            tenant_id=tenant_id,
            reason="Issue resolved"
        )
        
        # Verify session ended
        mock_conn.execute.assert_called()
        end_call = mock_conn.execute.call_args
        assert "UPDATE support_sessions" in end_call[0][0]
        assert "completed" in str(end_call[0])


class TestAuditAPI:
    """Test Audit Service API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_current_user(self):
        """Mock current user authentication"""
        with patch('services.audit_svc.app.routes.get_current_user') as mock:
            mock.return_value = {
                "user_id": str(uuid4()),
                "email": "admin@aivo.com",
                "role": "admin",
                "tenant_id": str(uuid4())
            }
            yield mock.return_value
    
    def test_health_check(self, client):
        """Test health check endpoint"""
        
        with patch('services.audit_svc.app.main.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetchval.return_value = 1
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "audit-svc"
    
    def test_create_audit_event_api(self, client, mock_current_user):
        """Test creating audit event via API"""
        
        request_data = {
            "event_type": "data_read",
            "severity": "medium",
            "action": "view_student_data",
            "resource": "student_records",
            "outcome": "success",
            "target_type": "student_profile",
            "target_classification": "confidential",
            "metadata": {
                "endpoint": "/api/students/123",
                "records_count": 1
            }
        }
        
        with patch('services.audit_svc.app.routes.AuditLogger') as mock_logger_class:
            mock_logger = AsyncMock()
            mock_logger.log_event.return_value = AuditEvent(
                id=uuid4(),
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.DATA_READ,
                action="view_student_data",
                resource="student_records",
                tenant_id=uuid4()
            )
            mock_logger_class.return_value = mock_logger
            
            response = client.post("/api/v1/audit/events", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["event_type"] == "data_read"
            assert data["action"] == "view_student_data"
    
    def test_query_audit_events_api(self, client, mock_current_user):
        """Test querying audit events via API"""
        
        with patch('services.audit_svc.app.routes.AuditLogger') as mock_logger_class:
            mock_logger = AsyncMock()
            mock_event = AuditEvent(
                id=uuid4(),
                timestamp=datetime.utcnow(),
                event_type=AuditEventType.LOGIN_SUCCESS,
                action="user_login",
                resource="auth_system",
                tenant_id=uuid4()
            )
            mock_logger.query_events.return_value = [mock_event]
            mock_logger_class.return_value = mock_logger
            
            response = client.get(
                "/api/v1/audit/events",
                params={
                    "event_types": ["login_success"],
                    "page": 1,
                    "page_size": 10
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["event_type"] == "login_success"


# Performance and Load Tests
class TestAuditPerformance:
    """Test audit service performance under load"""
    
    @pytest.mark.asyncio
    async def test_concurrent_audit_logging(self):
        """Test concurrent audit event logging"""
        
        audit_logger = AuditLogger()
        
        async def log_event():
            with patch('services.audit_svc.app.audit_logger.log_audit_event') as mock_log:
                mock_log.return_value = uuid4()
                return await audit_logger.log_event(
                    event_type=AuditEventType.DATA_READ,
                    action="concurrent_test",
                    resource="test_resource",
                    tenant_id=uuid4()
                )
        
        # Run 100 concurrent audit logs
        tasks = [log_event() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 100
        assert all(result.action == "concurrent_test" for result in results)
    
    @pytest.mark.asyncio
    async def test_large_audit_query(self):
        """Test querying large number of audit events"""
        
        from services.audit_svc.app.models import AuditQuery
        
        audit_logger = AuditLogger()
        
        # Mock large result set
        mock_events = [
            {
                'id': uuid4(),
                'timestamp': datetime.utcnow(),
                'event_type': 'data_read',
                'severity': 'low',
                'actor_type': 'student',
                'target_classification': None,
                'action': f'action_{i}',
                'resource': f'resource_{i}',
                'outcome': 'success',
                'actor_id': uuid4(),
                'actor_email': f'user{i}@aivo.com',
                'actor_ip': None,
                'actor_user_agent': None,
                'target_id': None,
                'target_type': None,
                'tenant_id': uuid4(),
                'session_id': None,
                'request_id': None,
                'reason': None,
                'metadata': {},
                'retention_days': 2555
            }
            for i in range(1000)
        ]
        
        with patch('services.audit_svc.app.audit_logger.get_db_pool') as mock_pool:
            mock_conn = AsyncMock()
            mock_conn.fetch.return_value = mock_events
            mock_pool.return_value.acquire.return_value.__aenter__.return_value = mock_conn
            
            query = AuditQuery(
                tenant_id=uuid4(),
                page=1,
                page_size=1000
            )
            
            start_time = datetime.utcnow()
            events = await audit_logger.query_events(query)
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            assert len(events) == 1000
            assert duration < 5.0  # Should complete within 5 seconds


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
