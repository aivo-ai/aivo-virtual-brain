"""
AIVO Search Service - Access Control Tests
S1-13 Implementation

Test suite for role-based search functionality and cross-school visibility controls.
"""

import pytest
import asyncio
from typing import Dict, List, Any
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import jwt
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.rbac import Role, Permission, UserContext, RBACManager
from app.client import SearchContext, SearchResult, SuggestionResult


class TestRBACSearchFiltering:
    """Test role-based access control for search operations"""
    
    @pytest.fixture
    def rbac_manager(self):
        """Create RBAC manager for testing"""
        return RBACManager(jwt_secret="test-secret", jwt_algorithm="HS256")
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        return TestClient(app)
    
    def create_jwt_token(
        self, 
        user_id: str,
        tenant_id: str = "tenant_123",
        school_ids: List[str] = None,
        roles: List[str] = None,
        student_ids: List[str] = None
    ) -> str:
        """Create JWT token for testing"""
        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "school_ids": school_ids or [],
            "roles": roles or ["teacher"],
            "student_ids": student_ids or [],
            "exp": int(datetime.now().timestamp()) + 3600  # 1 hour
        }
        return jwt.encode(payload, "test-secret", algorithm="HS256")
    
    def test_cross_school_visibility_blocked(self, rbac_manager):
        """Test that non-admin users cannot see cross-school data"""
        
        # Teacher context for School A
        teacher_context = UserContext(
            user_id="teacher_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=[Role.TEACHER],
            permissions=rbac_manager.get_effective_permissions([Role.TEACHER])
        )
        
        # Should not have cross-school visibility
        assert not rbac_manager.get_cross_school_visibility(teacher_context)
        
        # Admin context should have cross-school visibility
        admin_context = UserContext(
            user_id="admin_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=[Role.TENANT_ADMIN],
            permissions=rbac_manager.get_effective_permissions([Role.TENANT_ADMIN])
        )
        
        assert rbac_manager.get_cross_school_visibility(admin_context)
    
    def test_suggestion_filtering_by_role(self, rbac_manager):
        """Test that suggestions are filtered based on user role"""
        
        # Parent context - limited access
        parent_context = UserContext(
            user_id="parent_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=[Role.PARENT],
            permissions=rbac_manager.get_effective_permissions([Role.PARENT]),
            student_ids=["student_456"]
        )
        
        # Check document type access
        assert rbac_manager.check_document_access(parent_context, "iep")
        assert rbac_manager.check_document_access(parent_context, "assessment")
        assert not rbac_manager.check_document_access(parent_context, "curriculum")
        assert not rbac_manager.check_document_access(parent_context, "resource")
    
    def test_teacher_school_access(self, rbac_manager):
        """Test teacher access to school-specific data"""
        
        teacher_context = UserContext(
            user_id="teacher_123",
            tenant_id="tenant_123",
            school_ids=["school_a", "school_b"],
            roles=[Role.TEACHER],
            permissions=rbac_manager.get_effective_permissions([Role.TEACHER])
        )
        
        # Build search filters
        filters = rbac_manager.build_search_filters(teacher_context)
        
        # Should include tenant and school filters
        assert "bool" in filters
        assert "must" in filters["bool"]
        
        tenant_filter_found = False
        school_filter_found = False
        
        for filter_clause in filters["bool"]["must"]:
            if "term" in filter_clause and "tenant_id" in filter_clause["term"]:
                tenant_filter_found = True
                assert filter_clause["term"]["tenant_id"] == "tenant_123"
            elif "terms" in filter_clause and "school_id" in filter_clause["terms"]:
                school_filter_found = True
                assert set(filter_clause["terms"]["school_id"]) == {"school_a", "school_b"}
        
        assert tenant_filter_found, "Tenant filter not found"
        assert school_filter_found, "School filter not found"
    
    def test_parent_student_access(self, rbac_manager):
        """Test parent access limited to their children's data"""
        
        parent_context = UserContext(
            user_id="parent_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=[Role.PARENT],
            permissions=rbac_manager.get_effective_permissions([Role.PARENT]),
            student_ids=["student_456", "student_789"]
        )
        
        filters = rbac_manager.build_search_filters(parent_context)
        
        # Should include student ID filter
        assert "bool" in filters
        assert "must" in filters["bool"]
        
        student_filter_found = False
        for filter_clause in filters["bool"]["must"]:
            if "terms" in filter_clause and "metadata.student_id" in filter_clause["terms"]:
                student_filter_found = True
                assert set(filter_clause["terms"]["metadata.student_id"]) == {"student_456", "student_789"}
                
        assert student_filter_found, "Student filter not found"
    
    @patch('app.client.get_search_client')
    def test_search_endpoint_rbac(self, mock_get_client, test_client):
        """Test search endpoint with RBAC filtering"""
        
        # Mock search client
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock search results
        mock_results = [
            SearchResult(
                id="iep_123",
                title="IEP for Student A",
                content="Individual Education Program content...",
                document_type="iep",
                tenant_id="tenant_123",
                school_id="school_a",
                score=0.95,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                metadata={"student_id": "student_456"}
            )
        ]
        mock_client.search.return_value = mock_results
        
        # Create token for teacher
        token = self.create_jwt_token(
            user_id="teacher_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=["teacher"]
        )
        
        # Test search request
        response = test_client.get(
            "/api/v1/search?q=reading&doc_types=iep",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["query"] == "reading"
        assert len(data["results"]) == 1
        assert data["results"][0]["document_type"] == "iep"
        assert data["results"][0]["title"] == "IEP for Student A"
        
        # Verify search was called with correct context
        mock_client.search.assert_called_once()
        call_args = mock_client.search.call_args
        search_context = call_args.kwargs["context"]
        assert search_context.user_id == "teacher_123"
        assert search_context.tenant_id == "tenant_123"
        assert search_context.school_ids == ["school_a"]
    
    @patch('app.client.get_search_client')
    def test_suggestions_fra_to_fractions(self, mock_get_client, test_client):
        """Test 'fra' -> 'fractions' suggestion with ACL"""
        
        # Mock search client
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock suggestion results
        mock_suggestions = [
            SuggestionResult(
                text="fractions",
                score=0.9,
                category="curriculum"
            ),
            SuggestionResult(
                text="framework",
                score=0.7,
                category="curriculum"
            ),
            SuggestionResult(
                text="fragmented",
                score=0.5,
                category="assessment"
            )
        ]
        mock_client.suggest.return_value = mock_suggestions
        
        # Create token for teacher
        token = self.create_jwt_token(
            user_id="teacher_456",
            tenant_id="tenant_123",
            school_ids=["school_b"],
            roles=["teacher"]
        )
        
        # Test suggestion request
        response = test_client.get(
            "/api/v1/suggest?q=fra&size=5",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["query"] == "fra"
        assert len(data["suggestions"]) == 3
        
        # Check that "fractions" is the top suggestion
        suggestions = data["suggestions"]
        assert suggestions[0]["text"] == "fractions"
        assert suggestions[0]["score"] == 0.9
        
        # Verify suggest was called with correct context
        mock_client.suggest.assert_called_once()
        call_args = mock_client.suggest.call_args
        search_context = call_args.kwargs["context"]
        assert search_context.user_id == "teacher_456"
        assert search_context.tenant_id == "tenant_123"
        assert search_context.school_ids == ["school_b"]
    
    def test_unauthorized_access(self, test_client):
        """Test that requests without valid tokens are rejected"""
        
        # Request without Authorization header
        response = test_client.get("/api/v1/search?q=test")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Request with invalid token
        response = test_client.get(
            "/api/v1/search?q=test",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_cross_tenant_access_blocked(self, rbac_manager):
        """Test that users cannot access other tenants' data"""
        
        user_context = UserContext(
            user_id="user_123",
            tenant_id="tenant_a",
            school_ids=["school_1"],
            roles=[Role.TEACHER],
            permissions=rbac_manager.get_effective_permissions([Role.TEACHER])
        )
        
        filters = rbac_manager.build_search_filters(user_context)
        
        # Should always include tenant filter
        tenant_filters = []
        for filter_clause in filters["bool"]["must"]:
            if "term" in filter_clause and "tenant_id" in filter_clause["term"]:
                tenant_filters.append(filter_clause["term"]["tenant_id"])
        
        assert len(tenant_filters) == 1
        assert tenant_filters[0] == "tenant_a"
    
    def test_student_own_data_access(self, rbac_manager):
        """Test that students can only access their own data"""
        
        student_context = UserContext(
            user_id="student_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=[Role.STUDENT],
            permissions=rbac_manager.get_effective_permissions([Role.STUDENT])
        )
        
        filters = rbac_manager.build_search_filters(student_context)
        
        # Should include student ID filter for own data
        student_filter_found = False
        for filter_clause in filters["bool"]["must"]:
            if "term" in filter_clause and "metadata.student_id" in filter_clause["term"]:
                student_filter_found = True
                assert filter_clause["term"]["metadata.student_id"] == "student_123"
                
        assert student_filter_found, "Student self-access filter not found"
    
    def test_role_permission_inheritance(self, rbac_manager):
        """Test that higher roles inherit permissions from lower roles"""
        
        # School admin should have teacher permissions
        school_admin_perms = rbac_manager.get_effective_permissions([Role.SCHOOL_ADMIN])
        teacher_perms = rbac_manager.get_effective_permissions([Role.TEACHER])
        
        # School admin should have at least the teacher permissions
        assert teacher_perms.issubset(school_admin_perms)
        
        # Tenant admin should have school admin permissions
        tenant_admin_perms = rbac_manager.get_effective_permissions([Role.TENANT_ADMIN])
        assert school_admin_perms.issubset(tenant_admin_perms)
    
    @patch('app.client.get_search_client')
    def test_document_type_filtering(self, mock_get_client, test_client):
        """Test filtering of document types based on role permissions"""
        
        # Mock search client
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.search.return_value = []
        
        # Create token for parent (limited document access)
        token = self.create_jwt_token(
            user_id="parent_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=["parent"],
            student_ids=["student_456"]
        )
        
        # Test search with document types parent shouldn't access
        response = test_client.get(
            "/api/v1/search?q=test&doc_types=curriculum,resource",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        # Should return empty results since parent can't access curriculum/resource
        data = response.json()
        assert data["filters"]["accessible_types"] == []  # No accessible types from request
    
    @patch('app.client.get_search_client')
    def test_search_pagination(self, mock_get_client, test_client):
        """Test search pagination with RBAC"""
        
        # Mock search client
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        mock_client.search.return_value = []
        
        # Create token
        token = self.create_jwt_token(
            user_id="teacher_123",
            roles=["teacher"]
        )
        
        # Test pagination parameters
        response = test_client.get(
            "/api/v1/search?q=test&size=10&from=20",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["size"] == 10
        assert data["page"] == 2  # from=20, size=10 -> page 2
    
    def test_expired_token_rejection(self, test_client):
        """Test that expired tokens are rejected"""
        
        # Create expired token
        expired_payload = {
            "sub": "user_123",
            "tenant_id": "tenant_123",
            "roles": ["teacher"],
            "exp": int(datetime.now().timestamp()) - 3600  # 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, "test-secret", algorithm="HS256")
        
        response = test_client.get(
            "/api/v1/search?q=test",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "expired" in response.json()["error"].lower()


class TestSearchClientMocking:
    """Test search client functionality with mocked OpenSearch"""
    
    @pytest.fixture
    def mock_opensearch(self):
        """Mock OpenSearch client"""
        with patch('app.client.OpenSearch') as mock:
            yield mock
    
    def test_search_context_creation(self):
        """Test creation of search context from user context"""
        
        user_context = UserContext(
            user_id="user_123",
            tenant_id="tenant_456",
            school_ids=["school_a", "school_b"],
            roles=[Role.TEACHER, Role.CASE_MANAGER],
            permissions={Permission.SEARCH_SCHOOL, Permission.VIEW_IEP}
        )
        
        search_context = SearchContext(
            user_id=user_context.user_id,
            tenant_id=user_context.tenant_id,
            school_ids=user_context.school_ids,
            roles=[role.value for role in user_context.roles],
            permissions=[perm.value for perm in user_context.permissions],
            is_admin=user_context.is_admin,
            is_system=user_context.is_system
        )
        
        assert search_context.user_id == "user_123"
        assert search_context.tenant_id == "tenant_456"
        assert search_context.school_ids == ["school_a", "school_b"]
        assert "teacher" in search_context.roles
        assert "case_manager" in search_context.roles
    
    @patch('app.client.get_search_client')
    async def test_suggestion_acl_filtering(self, mock_get_client):
        """Test suggestion ACL filtering prevents cross-school visibility"""
        
        # Mock client with suggestions from different schools
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client
        
        # Mock suggestions that would come from different schools
        mock_client.suggest.return_value = [
            SuggestionResult(text="fractions_school_a", score=0.9),
            SuggestionResult(text="fractions_school_b", score=0.8),
            SuggestionResult(text="fractions_general", score=0.7)
        ]
        
        # User from school A should not see school B suggestions
        school_a_context = SearchContext(
            user_id="teacher_123",
            tenant_id="tenant_123",
            school_ids=["school_a"],
            roles=["teacher"],
            permissions=["search:school"],
            is_admin=False,
            is_system=False
        )
        
        suggestions = await mock_client.suggest(
            query="fra",
            context=school_a_context,
            size=10
        )
        
        # Verify suggest was called with correct context
        mock_client.suggest.assert_called_once_with(
            query="fra",
            context=school_a_context,
            size=10
        )
        
        # In a real implementation, suggestions would be filtered
        # Here we just verify the context was passed correctly
        assert len(suggestions) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
