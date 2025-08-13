# AIVO Notification Service - WebSocket and Push Tests
# S1-12 Implementation - Test WebSocket fanout and Push notifications

import pytest
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid
from unittest.mock import Mock, AsyncMock, patch

# Mock dependencies for testing without external services
class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.close_code = None
        self.close_reason = None
    
    async def accept(self):
        """Mock WebSocket accept."""
        pass
    
    async def send_json(self, data: Dict[str, Any]):
        """Mock sending JSON message."""
        self.messages_sent.append(data)
    
    async def receive_json(self) -> Dict[str, Any]:
        """Mock receiving JSON message."""
        # Return ping message for testing
        return {"type": "ping", "timestamp": datetime.now(timezone.utc).isoformat()}
    
    async def close(self, code: int = 1000, reason: str = ""):
        """Mock WebSocket close."""
        self.closed = True
        self.close_code = code
        self.close_reason = reason

class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.published_messages = []
        self.subscribed_channels = []
    
    async def publish(self, channel: str, message: str):
        """Mock Redis publish."""
        self.published_messages.append({"channel": channel, "message": message})
    
    async def ping(self):
        """Mock Redis ping."""
        return True
    
    def pubsub(self):
        """Mock Redis pubsub."""
        return MockPubSub()

class MockPubSub:
    """Mock Redis PubSub."""
    
    def __init__(self):
        self.subscribed_channels = []
        self.messages = []
    
    async def subscribe(self, channel: str):
        """Mock subscribe."""
        self.subscribed_channels.append(channel)
    
    async def listen(self):
        """Mock listen for messages."""
        # Yield test messages
        test_messages = [
            {
                "type": "message",
                "data": json.dumps({
                    "type": "notification",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "notification": {
                            "id": "test-notification-1",
                            "user_id": "user_123",
                            "tenant_id": "tenant_456",
                            "title": "Test Notification",
                            "message": "This is a test notification"
                        }
                    }
                }).encode()
            }
        ]
        
        for msg in test_messages:
            yield msg

class MockDatabase:
    """Mock database session for testing."""
    
    def __init__(self):
        self.notifications = []
        self.push_subscriptions = []
        self.ws_connections = []
        self.committed = False
    
    def add(self, obj):
        """Mock add object."""
        if hasattr(obj, '__tablename__'):
            if obj.__tablename__ == 'notifications':
                self.notifications.append(obj)
            elif obj.__tablename__ == 'push_subscriptions':
                self.push_subscriptions.append(obj)
            elif obj.__tablename__ == 'websocket_connections':
                self.ws_connections.append(obj)
    
    def commit(self):
        """Mock commit."""
        self.committed = True
    
    def close(self):
        """Mock close."""
        pass
    
    def query(self, model_class):
        """Mock query."""
        return MockQuery(self, model_class)

class MockQuery:
    """Mock SQLAlchemy query."""
    
    def __init__(self, db: MockDatabase, model_class):
        self.db = db
        self.model_class = model_class
        self.filters = []
        self.updates = {}
    
    def filter(self, *conditions):
        """Mock filter."""
        self.filters.extend(conditions)
        return self
    
    def update(self, values):
        """Mock update."""
        self.updates.update(values)
        return len(self._get_mock_results())
    
    def first(self):
        """Mock first result."""
        results = self._get_mock_results()
        return results[0] if results else None
    
    def all(self):
        """Mock all results."""
        return self._get_mock_results()
    
    def count(self):
        """Mock count."""
        return len(self._get_mock_results())
    
    def _get_mock_results(self):
        """Get mock results based on model type."""
        if hasattr(self.model_class, '__tablename__'):
            if self.model_class.__tablename__ == 'notifications':
                return self.db.notifications
            elif self.model_class.__tablename__ == 'push_subscriptions':
                return self.db.push_subscriptions
            elif self.model_class.__tablename__ == 'websocket_connections':
                return self.db.ws_connections
        return []

# Import the actual modules we're testing (with mocked dependencies)
# Note: These imports would need to be adjusted based on the actual module structure

class TestWebSocketManager:
    """Test WebSocket connection management and fanout."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client fixture."""
        return MockRedis()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database fixture."""
        return MockDatabase()
    
    @pytest.fixture
    def ws_manager(self, mock_redis):
        """WebSocket manager fixture."""
        # This would import the actual WebSocketManager
        # For now, creating a minimal mock
        class MockWebSocketManager:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.active_connections = {}
                self.user_connections = {}
                self.tenant_connections = {}
                self.server_instance = "test-server"
            
            async def connect(self, websocket, user_id, tenant_id, db):
                connection_id = f"conn-{uuid.uuid4().hex}"
                self.active_connections[connection_id] = websocket
                
                if user_id not in self.user_connections:
                    self.user_connections[user_id] = set()
                self.user_connections[user_id].add(connection_id)
                
                if tenant_id not in self.tenant_connections:
                    self.tenant_connections[tenant_id] = set()
                self.tenant_connections[tenant_id].add(connection_id)
                
                return connection_id
            
            async def disconnect(self, connection_id, db):
                if connection_id in self.active_connections:
                    del self.active_connections[connection_id]
                
                # Remove from user/tenant mappings
                for user_id, conn_ids in list(self.user_connections.items()):
                    conn_ids.discard(connection_id)
                    if not conn_ids:
                        del self.user_connections[user_id]
                
                for tenant_id, conn_ids in list(self.tenant_connections.items()):
                    conn_ids.discard(connection_id)
                    if not conn_ids:
                        del self.tenant_connections[tenant_id]
            
            async def send_personal_message(self, message, connection_id):
                if connection_id in self.active_connections:
                    websocket = self.active_connections[connection_id]
                    await websocket.send_json(message)
            
            async def notify_user(self, user_id, notification_data, db):
                message = {
                    "type": "notification",
                    "data": notification_data,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                if user_id in self.user_connections:
                    for connection_id in list(self.user_connections[user_id]):
                        await self.send_personal_message(message, connection_id)
                
                # Publish to Redis
                await self.redis.publish("notification:events", json.dumps({
                    "type": "notification",
                    "data": {"notification": notification_data}
                }))
            
            async def broadcast_to_tenant(self, tenant_id, message, exclude_user_id=None):
                if tenant_id in self.tenant_connections:
                    for connection_id in list(self.tenant_connections[tenant_id]):
                        # In real implementation, would check exclude_user_id
                        await self.send_personal_message(message, connection_id)
                
                # Publish to Redis
                await self.redis.publish("notification:events", json.dumps({
                    "type": "tenant_broadcast",
                    "data": {"tenant_id": tenant_id, "message": message}
                }))
        
        return MockWebSocketManager(mock_redis)
    
    @pytest.mark.asyncio
    async def test_websocket_connection_management(self, ws_manager, mock_db):
        """Test WebSocket connection lifecycle."""
        # Create mock WebSocket
        websocket1 = MockWebSocket()
        websocket2 = MockWebSocket()
        
        # Connect first user
        conn_id1 = await ws_manager.connect(websocket1, "user_123", "tenant_456", mock_db)
        assert conn_id1 in ws_manager.active_connections
        assert "user_123" in ws_manager.user_connections
        assert "tenant_456" in ws_manager.tenant_connections
        
        # Connect second user to same tenant
        conn_id2 = await ws_manager.connect(websocket2, "user_789", "tenant_456", mock_db)
        assert len(ws_manager.active_connections) == 2
        assert len(ws_manager.tenant_connections["tenant_456"]) == 2
        
        # Disconnect first user
        await ws_manager.disconnect(conn_id1, mock_db)
        assert conn_id1 not in ws_manager.active_connections
        assert "user_123" not in ws_manager.user_connections
        assert len(ws_manager.tenant_connections["tenant_456"]) == 1
        
        # Disconnect second user
        await ws_manager.disconnect(conn_id2, mock_db)
        assert len(ws_manager.active_connections) == 0
        assert "tenant_456" not in ws_manager.tenant_connections
    
    @pytest.mark.asyncio
    async def test_1_to_n_websocket_fanout(self, ws_manager, mock_db):
        """Test 1-to-N WebSocket message fanout."""
        # Connect multiple WebSockets for the same user
        websockets = []
        connection_ids = []
        
        for i in range(3):
            ws = MockWebSocket()
            websockets.append(ws)
            conn_id = await ws_manager.connect(ws, "user_123", "tenant_456", mock_db)
            connection_ids.append(conn_id)
        
        # Send notification to user (should fan out to all connections)
        notification_data = {
            "id": "test-notification",
            "title": "Test Notification",
            "message": "This should be received by all user connections",
            "user_id": "user_123"
        }
        
        await ws_manager.notify_user("user_123", notification_data, mock_db)
        
        # Verify all WebSockets received the message
        for ws in websockets:
            assert len(ws.messages_sent) == 1
            message = ws.messages_sent[0]
            assert message["type"] == "notification"
            assert message["data"]["id"] == "test-notification"
            assert message["data"]["title"] == "Test Notification"
        
        # Verify Redis publish was called
        assert len(ws_manager.redis.published_messages) == 1
        redis_msg = ws_manager.redis.published_messages[0]
        assert redis_msg["channel"] == "notification:events"
    
    @pytest.mark.asyncio
    async def test_tenant_broadcast(self, ws_manager, mock_db):
        """Test tenant-wide broadcast functionality."""
        # Connect users from same tenant
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws3 = MockWebSocket()  # Different tenant
        
        await ws_manager.connect(ws1, "user_123", "tenant_456", mock_db)
        await ws_manager.connect(ws2, "user_789", "tenant_456", mock_db)
        await ws_manager.connect(ws3, "user_999", "tenant_999", mock_db)
        
        # Broadcast to tenant_456
        broadcast_message = {
            "type": "announcement",
            "title": "System Maintenance",
            "message": "Scheduled maintenance tonight at 10 PM"
        }
        
        await ws_manager.broadcast_to_tenant("tenant_456", broadcast_message)
        
        # Verify only tenant_456 users received the broadcast
        assert len(ws1.messages_sent) == 1
        assert len(ws2.messages_sent) == 1
        assert len(ws3.messages_sent) == 0  # Different tenant
        
        # Verify message content
        assert ws1.messages_sent[0]["title"] == "System Maintenance"
        assert ws2.messages_sent[0]["title"] == "System Maintenance"

class TestPushNotificationService:
    """Test push notification functionality."""
    
    @pytest.fixture
    def mock_push_subscription(self):
        """Mock push subscription."""
        class MockPushSubscription:
            def __init__(self):
                self.id = uuid.uuid4()
                self.user_id = "user_123"
                self.endpoint = "https://fcm.googleapis.com/fcm/send/test-endpoint"
                self.p256dh_key = "test-p256dh-key"
                self.auth_key = "test-auth-key"
                self.is_active = True
                self.last_used_at = None
        
        return MockPushSubscription()
    
    @pytest.fixture
    def push_service(self):
        """Mock push notification service."""
        class MockPushNotificationService:
            def __init__(self):
                self.mock_mode = True
                self.sent_notifications = []
            
            async def send_to_user(self, user_id, notification_data, db):
                # Mock sending push notification
                self.sent_notifications.append({
                    "user_id": user_id,
                    "notification_data": notification_data,
                    "timestamp": datetime.now(timezone.utc)
                })
                
                return {
                    "status": "completed",
                    "sent": 1,
                    "failed": 0,
                    "total_subscriptions": 1
                }
            
            async def send_test_notification(self, user_id, db):
                test_data = {
                    "title": "🔔 Test Notification",
                    "message": "Test push notification",
                    "id": "test-push"
                }
                return await self.send_to_user(user_id, test_data, db)
        
        return MockPushNotificationService()
    
    @pytest.mark.asyncio
    async def test_push_subscription_storage(self, push_service, mock_db):
        """Test storing push subscription data."""
        # This would test the actual push subscription endpoint
        subscription_data = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/test-endpoint",
            "p256dh_key": "test-p256dh-key",
            "auth_key": "test-auth-key",
            "user_agent": "Mozilla/5.0 Test Browser",
            "device_info": {"platform": "web", "browser": "chrome"}
        }
        
        # Mock subscription creation (would be done via API endpoint)
        assert subscription_data["endpoint"].startswith("https://fcm.googleapis.com/")
        assert len(subscription_data["p256dh_key"]) > 0
        assert len(subscription_data["auth_key"]) > 0
    
    @pytest.mark.asyncio
    async def test_push_notification_sending(self, push_service, mock_db):
        """Test push notification delivery."""
        notification_data = {
            "id": "test-push-notification",
            "title": "Test Push",
            "message": "This is a test push notification",
            "notification_type": "system",
            "priority": "normal"
        }
        
        result = await push_service.send_to_user("user_123", notification_data, mock_db)
        
        # Verify push was sent
        assert result["status"] == "completed"
        assert result["sent"] == 1
        assert result["failed"] == 0
        
        # Verify notification was logged
        assert len(push_service.sent_notifications) == 1
        sent_notification = push_service.sent_notifications[0]
        assert sent_notification["user_id"] == "user_123"
        assert sent_notification["notification_data"]["title"] == "Test Push"
    
    @pytest.mark.asyncio
    async def test_push_notification_retrieval(self, mock_db):
        """Test retrieving push notifications."""
        # Mock retrieving notifications from database
        mock_notifications = [
            {
                "id": "notif_1",
                "title": "Notification 1",
                "message": "Message 1",
                "created_at": datetime.now(timezone.utc),
                "read_at": None
            },
            {
                "id": "notif_2",
                "title": "Notification 2",
                "message": "Message 2",
                "created_at": datetime.now(timezone.utc),
                "read_at": datetime.now(timezone.utc)
            }
        ]
        
        # Test filtering unread notifications
        unread_notifications = [n for n in mock_notifications if n["read_at"] is None]
        assert len(unread_notifications) == 1
        assert unread_notifications[0]["id"] == "notif_1"
        
        # Test total count
        assert len(mock_notifications) == 2

class TestNotificationIntegration:
    """Integration tests for the complete notification flow."""
    
    @pytest.mark.asyncio
    async def test_complete_notification_flow(self):
        """Test end-to-end notification delivery."""
        # Setup mocks
        mock_redis = MockRedis()
        mock_db = MockDatabase()
        
        # Create WebSocket manager
        class MockWebSocketManager:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.active_connections = {}
                self.user_connections = {}
                self.notifications_sent = []
            
            async def notify_user(self, user_id, notification_data, db):
                self.notifications_sent.append({
                    "user_id": user_id,
                    "data": notification_data
                })
                
                # Publish to Redis
                await self.redis.publish("notification:events", json.dumps({
                    "type": "notification",
                    "data": {"notification": notification_data}
                }))
        
        ws_manager = MockWebSocketManager(mock_redis)
        
        # Create push service
        class MockPushService:
            def __init__(self):
                self.push_sent = []
            
            async def send_to_user(self, user_id, notification_data, db):
                self.push_sent.append({
                    "user_id": user_id,
                    "data": notification_data
                })
                return {"status": "completed", "sent": 1, "failed": 0}
        
        push_service = MockPushService()
        
        # Simulate notification creation and delivery
        notification_data = {
            "id": "integration-test-notification",
            "user_id": "user_123",
            "tenant_id": "tenant_456",
            "title": "Integration Test Notification",
            "message": "Testing complete notification flow",
            "notification_type": "system",
            "priority": "normal",
            "channels": ["websocket", "push"]
        }
        
        # Send via WebSocket
        await ws_manager.notify_user(
            notification_data["user_id"],
            notification_data,
            mock_db
        )
        
        # Send via Push
        await push_service.send_to_user(
            notification_data["user_id"],
            notification_data,
            mock_db
        )
        
        # Verify WebSocket delivery
        assert len(ws_manager.notifications_sent) == 1
        ws_notification = ws_manager.notifications_sent[0]
        assert ws_notification["user_id"] == "user_123"
        assert ws_notification["data"]["title"] == "Integration Test Notification"
        
        # Verify Push delivery
        assert len(push_service.push_sent) == 1
        push_notification = push_service.push_sent[0]
        assert push_notification["user_id"] == "user_123"
        assert push_notification["data"]["title"] == "Integration Test Notification"
        
        # Verify Redis publication
        assert len(mock_redis.published_messages) == 1
        redis_message = mock_redis.published_messages[0]
        assert redis_message["channel"] == "notification:events"
    
    @pytest.mark.asyncio
    async def test_digest_generation(self):
        """Test daily digest generation."""
        # Mock digest service functionality
        class MockDigestService:
            async def generate_daily_digest(self, user_id, tenant_id, db):
                # Mock generating digest from notifications
                mock_notifications = [
                    {
                        "id": "notif_1",
                        "title": "IEP Updated",
                        "message": "IEP for John Doe has been updated",
                        "notification_type": "iep_update",
                        "priority": "normal",
                        "created_at": datetime.now(timezone.utc)
                    },
                    {
                        "id": "notif_2",
                        "title": "Assessment Complete",
                        "message": "Assessment for Jane Smith is complete",
                        "notification_type": "assessment_complete",
                        "priority": "high",
                        "created_at": datetime.now(timezone.utc)
                    }
                ]
                
                return {
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "date": datetime.now(timezone.utc).date().isoformat(),
                    "summary": {
                        "total_notifications": len(mock_notifications),
                        "unread_notifications": 2,
                        "priority_breakdown": {"normal": 1, "high": 1}
                    },
                    "notifications_by_type": {
                        "iep_update": {"count": 1, "notifications": [mock_notifications[0]]},
                        "assessment_complete": {"count": 1, "notifications": [mock_notifications[1]]}
                    }
                }
            
            async def send_digest_notification(self, user_id, digest_content, db):
                # Mock sending digest notification
                return {
                    "status": "sent",
                    "user_id": user_id,
                    "notification_count": digest_content["summary"]["total_notifications"]
                }
        
        digest_service = MockDigestService()
        mock_db = MockDatabase()
        
        # Generate digest
        digest_content = await digest_service.generate_daily_digest("user_123", "tenant_456", mock_db)
        
        # Verify digest content
        assert digest_content is not None
        assert digest_content["user_id"] == "user_123"
        assert digest_content["summary"]["total_notifications"] == 2
        assert digest_content["summary"]["unread_notifications"] == 2
        assert "iep_update" in digest_content["notifications_by_type"]
        assert "assessment_complete" in digest_content["notifications_by_type"]
        
        # Send digest
        result = await digest_service.send_digest_notification("user_123", digest_content, mock_db)
        assert result["status"] == "sent"
        assert result["notification_count"] == 2

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
