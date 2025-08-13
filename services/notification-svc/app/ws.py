# AIVO Notification Service - WebSocket Manager
# S1-12 Implementation - Real-time WebSocket Hub with JWT Authentication

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Set, Any, Optional, List
import uuid
import jwt
from fastapi import WebSocket, WebSocketDisconnect, HTTPException, Depends
from sqlalchemy.orm import Session
import redis.asyncio as redis
from contextlib import asynccontextmanager

from .models import (
    WebSocketConnection, Notification, NotificationQueue,
    NotificationType, NotificationStatus
)
from .database import get_db

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections with Redis pub/sub for scalability."""
    
    def __init__(self, redis_client: redis.Redis):
        # Active connections: {connection_id: WebSocketConnection}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User to connections mapping: {user_id: set of connection_ids}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Tenant to connections mapping: {tenant_id: set of connection_ids}
        self.tenant_connections: Dict[str, Set[str]] = {}
        
        self.redis = redis_client
        self.pubsub_channel = "notification:events"
        self.server_instance = f"ws-server-{uuid.uuid4().hex[:8]}"
        
        # Start Redis subscriber task
        self._subscriber_task = None
        self._start_subscriber()
    
    def _start_subscriber(self):
        """Start Redis pub/sub subscriber for cross-server communication."""
        if self._subscriber_task is None or self._subscriber_task.done():
            self._subscriber_task = asyncio.create_task(self._redis_subscriber())
    
    async def _redis_subscriber(self):
        """Subscribe to Redis pub/sub for cross-server notifications."""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(self.pubsub_channel)
            
            logger.info(f"WebSocket server {self.server_instance} subscribed to Redis pub/sub")
            
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"].decode())
                        await self._handle_redis_event(event_data)
                    except Exception as e:
                        logger.error(f"Error handling Redis event: {e}")
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}")
            # Retry after delay
            await asyncio.sleep(5)
            self._start_subscriber()
    
    async def _handle_redis_event(self, event_data: Dict[str, Any]):
        """Handle events from Redis pub/sub."""
        event_type = event_data.get("type")
        data = event_data.get("data", {})
        
        if event_type == "notification":
            notification_data = data.get("notification")
            user_id = notification_data.get("user_id")
            tenant_id = notification_data.get("tenant_id")
            
            # Send to user's connections
            if user_id:
                await self._send_to_user(user_id, {
                    "type": "notification",
                    "data": notification_data,
                    "timestamp": event_data.get("timestamp")
                })
            
            # Send to tenant connections if broadcast
            if data.get("broadcast_to_tenant") and tenant_id:
                await self._send_to_tenant(tenant_id, {
                    "type": "notification",
                    "data": notification_data,
                    "timestamp": event_data.get("timestamp")
                })
    
    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        tenant_id: str, 
        db: Session
    ) -> str:
        """Accept WebSocket connection and register it."""
        await websocket.accept()
        
        connection_id = f"conn-{uuid.uuid4().hex}"
        
        # Store connection
        self.active_connections[connection_id] = websocket
        
        # Update user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Update tenant connections
        if tenant_id not in self.tenant_connections:
            self.tenant_connections[tenant_id] = set()
        self.tenant_connections[tenant_id].add(connection_id)
        
        # Store in database
        ws_connection = WebSocketConnection(
            connection_id=connection_id,
            user_id=user_id,
            tenant_id=tenant_id,
            server_instance=self.server_instance,
            session_data={"connected_at": datetime.now(timezone.utc).isoformat()},
            is_active=True
        )
        
        db.add(ws_connection)
        db.commit()
        
        logger.info(f"WebSocket connected: {connection_id} for user {user_id}")
        
        # Send pending notifications
        await self._send_pending_notifications(websocket, user_id, tenant_id, db)
        
        return connection_id
    
    async def disconnect(self, connection_id: str, db: Session):
        """Disconnect WebSocket and clean up."""
        if connection_id not in self.active_connections:
            return
        
        websocket = self.active_connections[connection_id]
        
        # Find user and tenant for this connection
        user_id = None
        tenant_id = None
        
        for uid, conn_ids in self.user_connections.items():
            if connection_id in conn_ids:
                user_id = uid
                break
        
        for tid, conn_ids in self.tenant_connections.items():
            if connection_id in conn_ids:
                tenant_id = tid
                break
        
        # Remove from active connections
        del self.active_connections[connection_id]
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from tenant connections
        if tenant_id and tenant_id in self.tenant_connections:
            self.tenant_connections[tenant_id].discard(connection_id)
            if not self.tenant_connections[tenant_id]:
                del self.tenant_connections[tenant_id]
        
        # Update database
        db.query(WebSocketConnection).filter(
            WebSocketConnection.connection_id == connection_id
        ).update({
            "is_active": False,
            "disconnected_at": datetime.now(timezone.utc)
        })
        db.commit()
        
        logger.info(f"WebSocket disconnected: {connection_id}")
    
    async def _send_pending_notifications(
        self, 
        websocket: WebSocket, 
        user_id: str, 
        tenant_id: str, 
        db: Session
    ):
        """Send any pending notifications to newly connected user."""
        # Get unread notifications
        notifications = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.tenant_id == tenant_id,
            Notification.read_at.is_(None),
            Notification.status == NotificationStatus.PENDING
        ).order_by(Notification.created_at.desc()).limit(10).all()
        
        for notification in notifications:
            await websocket.send_json({
                "type": "notification",
                "data": notification.to_dict(),
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    
    async def send_personal_message(
        self, 
        message: Dict[str, Any], 
        connection_id: str
    ):
        """Send message to specific connection."""
        if connection_id in self.active_connections:
            websocket = self.active_connections[connection_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                # Connection might be dead, remove it
                await self._cleanup_dead_connection(connection_id)
    
    async def _send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send message to all connections for a user."""
        if user_id not in self.user_connections:
            return
        
        connection_ids = list(self.user_connections[user_id])
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    async def _send_to_tenant(self, tenant_id: str, message: Dict[str, Any]):
        """Send message to all connections in a tenant."""
        if tenant_id not in self.tenant_connections:
            return
        
        connection_ids = list(self.tenant_connections[tenant_id])
        for connection_id in connection_ids:
            await self.send_personal_message(message, connection_id)
    
    async def broadcast_to_tenant(
        self, 
        tenant_id: str, 
        message: Dict[str, Any],
        exclude_user_id: str = None
    ):
        """Broadcast message to all users in tenant, optionally excluding one user."""
        if tenant_id not in self.tenant_connections:
            # Still publish to Redis for other servers
            await self._publish_to_redis("tenant_broadcast", {
                "tenant_id": tenant_id,
                "message": message,
                "exclude_user_id": exclude_user_id
            })
            return
        
        connection_ids = list(self.tenant_connections[tenant_id])
        
        for connection_id in connection_ids:
            # Skip connections for excluded user
            if exclude_user_id:
                user_id_for_conn = None
                for uid, conn_ids in self.user_connections.items():
                    if connection_id in conn_ids:
                        user_id_for_conn = uid
                        break
                
                if user_id_for_conn == exclude_user_id:
                    continue
            
            await self.send_personal_message(message, connection_id)
        
        # Also publish to Redis for other servers
        await self._publish_to_redis("tenant_broadcast", {
            "tenant_id": tenant_id,
            "message": message,
            "exclude_user_id": exclude_user_id
        })
    
    async def notify_user(
        self, 
        user_id: str, 
        notification_data: Dict[str, Any],
        db: Session
    ):
        """Send notification to specific user via WebSocket."""
        message = {
            "type": "notification",
            "data": notification_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send to local connections
        await self._send_to_user(user_id, message)
        
        # Publish to Redis for other servers
        await self._publish_to_redis("notification", {
            "notification": notification_data,
            "user_id": user_id
        })
    
    async def _publish_to_redis(self, event_type: str, data: Dict[str, Any]):
        """Publish event to Redis pub/sub."""
        try:
            event_data = {
                "type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "server_instance": self.server_instance,
                "data": data
            }
            await self.redis.publish(self.pubsub_channel, json.dumps(event_data))
        except Exception as e:
            logger.error(f"Error publishing to Redis: {e}")
    
    async def _cleanup_dead_connection(self, connection_id: str):
        """Clean up a dead connection."""
        if connection_id in self.active_connections:
            try:
                # Try to close the websocket
                websocket = self.active_connections[connection_id]
                await websocket.close()
            except:
                pass
            
            # Remove from tracking
            del self.active_connections[connection_id]
    
    async def handle_connection_messages(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str,
        db: Session
    ):
        """Handle incoming WebSocket messages."""
        try:
            while True:
                # Wait for messages from client
                data = await websocket.receive_json()
                message_type = data.get("type")
                
                if message_type == "ping":
                    # Update last ping time
                    db.query(WebSocketConnection).filter(
                        WebSocketConnection.connection_id == connection_id
                    ).update({
                        "last_ping": datetime.now(timezone.utc)
                    })
                    db.commit()
                    
                    # Send pong response
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                
                elif message_type == "mark_read":
                    # Mark notification as read
                    notification_id = data.get("notification_id")
                    if notification_id:
                        db.query(Notification).filter(
                            Notification.id == notification_id,
                            Notification.user_id == user_id
                        ).update({
                            "read_at": datetime.now(timezone.utc),
                            "status": NotificationStatus.READ,
                            "updated_at": datetime.now(timezone.utc)
                        })
                        db.commit()
                        
                        # Send confirmation
                        await websocket.send_json({
                            "type": "read_confirmation",
                            "notification_id": notification_id,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                
                elif message_type == "subscribe_channel":
                    # Subscribe to specific notification channels
                    channel = data.get("channel")
                    if channel:
                        # Update connection session data
                        db.query(WebSocketConnection).filter(
                            WebSocketConnection.connection_id == connection_id
                        ).update({
                            "session_data": {"subscribed_channels": [channel]}
                        })
                        db.commit()
                        
                        await websocket.send_json({
                            "type": "subscription_confirmed",
                            "channel": channel,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                
        except WebSocketDisconnect:
            await self.disconnect(connection_id, db)
        except Exception as e:
            logger.error(f"WebSocket error for {connection_id}: {e}")
            await self.disconnect(connection_id, db)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        return {
            "total_connections": len(self.active_connections),
            "users_connected": len(self.user_connections),
            "tenants_connected": len(self.tenant_connections),
            "server_instance": self.server_instance
        }

# JWT Authentication for WebSocket
async def authenticate_websocket(token: str) -> Dict[str, str]:
    """Authenticate WebSocket connection via JWT token."""
    try:
        # In production, use proper JWT secret and validation
        payload = jwt.decode(token, "your-secret-key", algorithms=["HS256"])
        return {
            "user_id": payload.get("user_id"),
            "tenant_id": payload.get("tenant_id"),
            "roles": payload.get("roles", [])
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Global WebSocket manager instance
ws_manager = None

def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global ws_manager
    if ws_manager is None:
        # This would be initialized in main.py with proper Redis connection
        raise RuntimeError("WebSocket manager not initialized")
    return ws_manager
