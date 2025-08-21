"""
Test Chat Service API endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock
import uuid
from datetime import datetime

from app.models import Thread, Message


class TestThreadsAPI:
    """Test thread-related API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_thread(self, client: AsyncClient, auth_headers, mock_user_context):
        """Test creating a new thread"""
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    thread_data = {
                        "learner_id": "learner-123",
                        "title": "Test Thread",
                        "description": "A test thread for chat",
                        "metadata": {"test": True}
                    }
                    
                    response = await client.post(
                        "/api/v1/threads",
                        json=thread_data,
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["title"] == "Test Thread"
                    assert data["learner_id"] == "learner-123"
                    assert data["metadata"]["test"] is True
    
    @pytest.mark.asyncio
    async def test_list_threads(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test listing threads"""
        # Create test thread
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Test Thread",
            description="Test description",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                response = await client.get(
                    "/api/v1/threads",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["total"] >= 1
                assert len(data["threads"]) >= 1
                assert data["threads"][0]["title"] == "Test Thread"
    
    @pytest.mark.asyncio
    async def test_get_thread(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test getting a specific thread"""
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Test Thread",
            description="Test description",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    response = await client.get(
                        f"/api/v1/threads/{thread.id}",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["id"] == thread.id
                    assert data["title"] == "Test Thread"
    
    @pytest.mark.asyncio
    async def test_update_thread(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test updating a thread"""
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Original Title",
            description="Original description",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    update_data = {
                        "title": "Updated Title",
                        "description": "Updated description"
                    }
                    
                    response = await client.put(
                        f"/api/v1/threads/{thread.id}",
                        json=update_data,
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["title"] == "Updated Title"
                    assert data["description"] == "Updated description"
    
    @pytest.mark.asyncio
    async def test_delete_thread(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test deleting a thread"""
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Thread to Delete",
            description="Will be deleted",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    with patch('app.events.EventPublisher.publish_thread_deleted', new_callable=AsyncMock):
                        response = await client.delete(
                            f"/api/v1/threads/{thread.id}",
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "deleted successfully" in data["message"]


class TestMessagesAPI:
    """Test message-related API endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_message(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test creating a new message"""
        # Create test thread first
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Test Thread",
            description="Test description",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    with patch('app.events.EventPublisher.publish_message_created', new_callable=AsyncMock):
                        message_data = {
                            "content": "Hello, this is a test message!",
                            "sender_type": "teacher",
                            "message_type": "text",
                            "metadata": {"test": True}
                        }
                        
                        response = await client.post(
                            f"/api/v1/threads/{thread.id}/messages",
                            json=message_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert data["content"] == "Hello, this is a test message!"
                        assert data["sender_type"] == "teacher"
                        assert data["thread_id"] == thread.id
    
    @pytest.mark.asyncio
    async def test_list_messages(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test listing messages in a thread"""
        # Create test thread
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Test Thread",
            description="Test description",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        
        # Create test message
        message = Message(
            id=str(uuid.uuid4()),
            thread_id=thread.id,
            content="Test message content",
            sender_id="test-user-123",
            sender_type="teacher",
            message_type="text",
            metadata={},
            created_at=datetime.utcnow()
        )
        db_session.add(message)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    response = await client.get(
                        f"/api/v1/threads/{thread.id}/messages",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["total"] >= 1
                    assert len(data["messages"]) >= 1
                    assert data["messages"][0]["content"] == "Test message content"
    
    @pytest.mark.asyncio
    async def test_get_message(self, client: AsyncClient, auth_headers, mock_user_context, db_session):
        """Test getting a specific message"""
        # Create test thread
        thread = Thread(
            id=str(uuid.uuid4()),
            tenant_id="test-tenant-123",
            learner_id="learner-123",
            title="Test Thread",
            description="Test description",
            metadata={},
            created_by="test-user-123",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db_session.add(thread)
        
        # Create test message
        message = Message(
            id=str(uuid.uuid4()),
            thread_id=thread.id,
            content="Specific test message",
            sender_id="test-user-123",
            sender_type="teacher",
            message_type="text",
            metadata={},
            created_at=datetime.utcnow()
        )
        db_session.add(message)
        await db_session.commit()
        
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    response = await client.get(
                        f"/api/v1/threads/{thread.id}/messages/{message.id}",
                        headers=auth_headers
                    )
                    
                    assert response.status_code == 200
                    data = response.json()
                    assert data["id"] == message.id
                    assert data["content"] == "Specific test message"


class TestPrivacyAPI:
    """Test privacy and compliance endpoints"""
    
    @pytest.mark.asyncio
    async def test_export_chat_data(self, client: AsyncClient, auth_headers, mock_user_context):
        """Test exporting chat data for privacy compliance"""
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    with patch('app.events.EventPublisher.publish_privacy_export_requested', new_callable=AsyncMock):
                        export_data = {
                            "learner_id": "learner-123",
                            "export_type": "full"
                        }
                        
                        response = await client.post(
                            "/api/v1/privacy/export",
                            json=export_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "export_id" in data
                        assert data["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_delete_chat_data(self, client: AsyncClient, auth_headers, mock_user_context):
        """Test deleting chat data for privacy compliance"""
        with patch('app.middleware.get_current_user', return_value=mock_user_context):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                with patch('app.middleware.validate_learner_access', return_value=None):
                    with patch('app.events.EventPublisher.publish_privacy_deletion_requested', new_callable=AsyncMock):
                        deletion_data = {
                            "learner_id": "learner-123",
                            "deletion_type": "full"
                        }
                        
                        response = await client.post(
                            "/api/v1/privacy/delete",
                            json=deletion_data,
                            headers=auth_headers
                        )
                        
                        assert response.status_code == 200
                        data = response.json()
                        assert "deletion_id" in data
                        assert data["status"] == "pending"


class TestAuthentication:
    """Test authentication and authorization"""
    
    @pytest.mark.asyncio
    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that endpoints require authentication"""
        response = await client.get("/api/v1/threads")
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_learner_scope_validation(self, client: AsyncClient, auth_headers):
        """Test that learner scope is properly validated"""
        restricted_user = {
            "user_id": "test-user-123",
            "tenant_id": "test-tenant-123",
            "learner_scope": ["learner-999"],  # Different learner
            "role": "teacher",
            "permissions": ["chat:read", "chat:write"]
        }
        
        with patch('app.middleware.get_current_user', return_value=restricted_user):
            with patch('app.middleware.get_tenant_id', return_value="test-tenant-123"):
                thread_data = {
                    "learner_id": "learner-123",  # Not in scope
                    "title": "Unauthorized Thread",
                    "description": "Should fail"
                }
                
                response = await client.post(
                    "/api/v1/threads",
                    json=thread_data,
                    headers=auth_headers
                )
                
                assert response.status_code == 403
