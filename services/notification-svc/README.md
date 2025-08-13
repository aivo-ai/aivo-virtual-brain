# AIVO Notification Service Documentation

# S1-12 Implementation - WebSocket Hub + Push Subscribe + Daily Digest

## Overview

The AIVO Notification Service provides real-time notification delivery with WebSocket hub functionality, browser push subscriptions, and automated daily digest capabilities. This service enables 1-to-N fanout messaging for collaborative features and multi-channel notification delivery.

## Features

### Core Functionality

- **WebSocket Hub**: Real-time bidirectional communication with JWT authentication
- **Push Subscriptions**: Browser push notifications using Web Push API standards
- **Daily Digest**: Automated daily summary notifications at user-specified times
- **Multi-channel Delivery**: WebSocket, push, email, SMS, and in-app notifications
- **1-to-N Fanout**: Efficient message broadcasting to multiple recipients
- **Cross-server Scalability**: Redis pub/sub for load balancer support

### Technical Architecture

- **FastAPI**: High-performance async web framework
- **WebSocket Manager**: Connection pooling with Redis pub/sub
- **PostgreSQL**: Persistent storage for notifications and subscriptions
- **Redis**: Pub/sub messaging and session management
- **Push Service**: Web Push API integration with VAPID authentication
- **Cron Jobs**: Scheduled digest generation and cleanup tasks

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 7+

### Installation

1. **Setup the service:**

```bash
cd services/notification-svc
pip install -r requirements.txt
```

2. **Configure environment variables:**

```bash
# Database
DATABASE_URL=postgresql://notification_user:notification_pass@localhost:5432/notification_db

# Redis
REDIS_URL=redis://localhost:6379

# JWT Configuration
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256

# VAPID Keys for Push Notifications
VAPID_PUBLIC_KEY=your-vapid-public-key
VAPID_PRIVATE_KEY=your-vapid-private-key
VAPID_EMAIL=admin@aivo.ai

# Email Configuration (optional)
SENDGRID_API_KEY=your-sendgrid-key
```

3. **Run database migrations:**

```bash
alembic upgrade head
```

4. **Start the service:**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

5. **Access the API:**
   - REST API: http://localhost:8003/api/v1
   - WebSocket: ws://localhost:8003/ws/notify?token=<jwt_token>
   - API Docs: http://localhost:8003/docs
   - Health Check: http://localhost:8003/health

## API Documentation

### WebSocket Connection

Connect to real-time notifications:

```javascript
const token = "your-jwt-token";
const ws = new WebSocket(`ws://localhost:8003/ws/notify?token=${token}`);

ws.onopen = () => {
  console.log("Connected to notification service");

  // Send ping to keep connection alive
  ws.send(
    JSON.stringify({
      type: "ping",
      timestamp: new Date().toISOString(),
    }),
  );
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "notification") {
    // Handle new notification
    displayNotification(data.data);
  } else if (data.type === "pong") {
    // Handle ping response
    console.log("Ping response received");
  }
};
```

### Push Subscription

Register for browser push notifications:

```javascript
// Request notification permission
const permission = await Notification.requestPermission();

if (permission === "granted") {
  // Get service worker registration
  const registration = await navigator.serviceWorker.ready;

  // Subscribe to push notifications
  const subscription = await registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(vapidPublicKey),
  });

  // Send subscription to server
  await fetch("/api/v1/push/subscribe", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      endpoint: subscription.endpoint,
      p256dh_key: btoa(
        String.fromCharCode(...new Uint8Array(subscription.getKey("p256dh"))),
      ),
      auth_key: btoa(
        String.fromCharCode(...new Uint8Array(subscription.getKey("auth"))),
      ),
      user_agent: navigator.userAgent,
      device_info: {
        platform: "web",
        browser: getBrowserName(),
      },
    }),
  });
}
```

### Notification Creation

Create notifications via REST API:

```bash
curl -X POST "http://localhost:8003/api/v1/notifications" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "IEP Document Updated",
    "message": "The IEP document for John Doe requires your review.",
    "notification_type": "iep_update",
    "priority": "high",
    "channels": ["websocket", "push", "in_app"],
    "action_url": "/iep/12345/review",
    "metadata": {
      "iep_id": "12345",
      "student_name": "John Doe"
    }
  }'
```

### Daily Digest Configuration

Configure daily digest preferences:

```bash
curl -X PUT "http://localhost:8003/api/v1/digest/subscription" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "is_enabled": true,
    "delivery_time": "07:00",
    "timezone": "America/New_York",
    "frequency": "daily",
    "include_types": ["iep_update", "assessment_complete", "signature_request"],
    "exclude_weekends": false,
    "min_priority": "normal"
  }'
```

## WebSocket Hub Architecture

### Connection Management

- **JWT Authentication**: Secure WebSocket connections with JWT tokens
- **Connection Pooling**: Efficient management of active connections
- **User Mapping**: Track connections per user and tenant
- **Heartbeat**: Ping/pong mechanism for connection health

### Message Fanout

- **1-to-N Broadcasting**: Send messages to all user connections
- **Tenant Broadcasting**: Broadcast to all users in a tenant
- **Selective Delivery**: Filter messages based on user preferences
- **Cross-server Support**: Redis pub/sub for load balancer compatibility

### Message Types

#### Client to Server:

```json
{
  "type": "ping",
  "timestamp": "2025-01-15T14:30:00Z"
}

{
  "type": "mark_read",
  "notification_id": "notification-uuid"
}

{
  "type": "subscribe_channel",
  "channel": "iep_updates"
}
```

#### Server to Client:

```json
{
  "type": "notification",
  "data": {
    "id": "notification-uuid",
    "title": "New Notification",
    "message": "Notification content",
    "notification_type": "system",
    "action_url": "/path/to/action"
  },
  "timestamp": "2025-01-15T14:30:00Z"
}

{
  "type": "pong",
  "timestamp": "2025-01-15T14:30:00Z"
}
```

## Push Notification System

### Web Push Implementation

- **VAPID Authentication**: Voluntary Application Server Identification
- **Encryption**: RFC 8291 message encryption for security
- **Multi-browser Support**: Chrome, Firefox, Safari, Edge compatibility
- **Payload Delivery**: Rich notifications with actions and images

### Push Service Integration

```python
# Send push notification
push_service = PushNotificationService()

notification_data = {
    "title": "New IEP Update",
    "message": "IEP document requires your attention",
    "action_url": "/iep/12345"
}

result = await push_service.send_to_user("user_123", notification_data, db)
```

### Service Worker Integration

```javascript
// sw.js - Service Worker for handling push notifications
self.addEventListener("push", (event) => {
  const data = event.data.json();

  const options = {
    body: data.body,
    icon: data.icon,
    badge: data.badge,
    tag: data.tag,
    data: data.data,
    actions: data.actions,
    requireInteraction: data.priority === "urgent",
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  if (event.action === "view") {
    // Open the specified URL
    clients.openWindow(event.notification.data.action_url);
  }
});
```

## Daily Digest System

### Digest Generation

- **Scheduled Processing**: Cron jobs run hourly to check for digest delivery
- **Content Aggregation**: Summarize notifications by type and priority
- **User Preferences**: Respect delivery time, timezone, and content filters
- **Weekend Handling**: Optional weekend exclusion

### Digest Content Structure

```json
{
  "date": "2025-01-15",
  "summary": {
    "total_notifications": 15,
    "unread_notifications": 8,
    "priority_breakdown": {
      "urgent": 2,
      "high": 5,
      "normal": 6,
      "low": 2
    }
  },
  "notifications_by_type": {
    "iep_update": {
      "count": 7,
      "notifications": [...]
    },
    "assessment_complete": {
      "count": 3,
      "notifications": [...]
    }
  },
  "top_notifications": [...]
}
```

### Cron Job Schedule

```python
# Daily digest processor - runs every hour
@scheduler.scheduled_job('cron', minute=0)
async def process_daily_digests():
    # Check for users scheduled to receive digest at current hour
    # Generate digest content
    # Send digest notification
    pass

# Cleanup job - runs daily at 2:00 AM
@scheduler.scheduled_job('cron', hour=2, minute=0)
async def cleanup_old_notifications():
    # Remove notifications older than 90 days
    # Archive digest history
    pass
```

## Database Schema

### Core Tables

- **notifications**: Main notification records
- **notification_deliveries**: Delivery attempts per channel
- **push_subscriptions**: Browser push subscription data
- **websocket_connections**: Active WebSocket connections
- **digest_subscriptions**: User digest preferences

### Performance Indexes

```sql
-- Optimized indexes for common queries
CREATE INDEX idx_notifications_user_status ON notifications(user_id, status);
CREATE INDEX idx_notifications_tenant_type ON notifications(tenant_id, notification_type);
CREATE INDEX idx_notifications_created_at ON notifications(created_at);
CREATE INDEX idx_push_subscriptions_active ON push_subscriptions(is_active, user_id);
```

## Testing

### Run Test Suite

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run WebSocket and Push tests
pytest tests/test_ws_push.py -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

### Test Coverage

- **WebSocket Connection Management**: Connection lifecycle, fanout messaging
- **Push Notification Delivery**: Subscription management, message encryption
- **Daily Digest Generation**: Content aggregation, scheduling
- **Integration Tests**: End-to-end notification delivery workflows

## Deployment

### Docker Configuration

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY migrations/ ./migrations/

EXPOSE 8003
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
```

### Environment Configuration

```bash
# Production environment variables
DATABASE_URL=postgresql://user:pass@db:5432/notification_db
REDIS_URL=redis://redis:6379
JWT_SECRET_KEY=production-secret-key
VAPID_PUBLIC_KEY=production-vapid-public-key
VAPID_PRIVATE_KEY=production-vapid-private-key
```

## Monitoring & Observability

### Health Checks

- **Service Health**: `/health` endpoint with dependency checks
- **WebSocket Status**: `/ws/status` for connection statistics
- **Redis Connectivity**: Real-time Redis connection monitoring

### Metrics & Logging

- **Connection Metrics**: WebSocket connection counts and duration
- **Delivery Metrics**: Notification delivery success/failure rates
- **Performance Metrics**: Message processing latency
- **Error Tracking**: Comprehensive error logging and alerting

### Prometheus Metrics

```python
# Example metrics collection
notification_delivery_total = Counter('notifications_delivered_total', 'Total notifications delivered', ['channel', 'status'])
websocket_connections_active = Gauge('websocket_connections_active', 'Active WebSocket connections')
push_notifications_sent = Counter('push_notifications_sent_total', 'Push notifications sent', ['status'])
```

## Integration Examples

### IEP Service Integration

```python
# Send IEP update notification
async def notify_iep_update(iep_id: str, student_name: str, user_id: str):
    notification_data = {
        "title": f"IEP Updated: {student_name}",
        "message": f"The IEP document for {student_name} has been updated and requires your review.",
        "notification_type": "iep_update",
        "priority": "high",
        "channels": ["websocket", "push", "in_app"],
        "action_url": f"/iep/{iep_id}/review",
        "metadata": {
            "iep_id": iep_id,
            "student_name": student_name
        }
    }

    # Send via notification service API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://notification-svc:8003/internal/broadcast",
            json=notification_data
        )
```

### Assessment Service Integration

```python
# Broadcast assessment completion
async def notify_assessment_complete(assessment_id: str, tenant_id: str):
    broadcast_data = {
        "title": "Assessment Complete",
        "message": "A new assessment has been completed and is ready for review.",
        "notification_type": "assessment_complete",
        "tenant_id": tenant_id,
        "broadcast_to_tenant": True,
        "metadata": {
            "assessment_id": assessment_id
        }
    }

    # Broadcast to entire tenant
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://notification-svc:8003/internal/broadcast",
            json=broadcast_data
        )
```

## Security Considerations

### Authentication & Authorization

- **JWT Token Validation**: Secure WebSocket and API authentication
- **Role-based Access**: User and tenant-based access controls
- **Token Expiration**: Automatic token refresh mechanisms

### Data Protection

- **Message Encryption**: Push notification payload encryption
- **Data Minimization**: Store only necessary notification metadata
- **Audit Logging**: Complete audit trail for compliance

### Rate Limiting

- **Connection Limits**: Maximum WebSocket connections per user
- **Message Throttling**: Prevent notification spam
- **Resource Protection**: CPU and memory usage monitoring

This notification service provides a robust, scalable foundation for real-time communication in the AIVO Virtual Brains ecosystem, enabling efficient collaboration and timely information delivery across all connected services and users.
