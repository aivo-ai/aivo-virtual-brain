# Chat Service

AIVO Chat Service provides threaded message history functionality for learner communication with comprehensive privacy compliance and role-based access control.

## Features

- **Threaded Conversations**: Organize messages into threaded conversations per learner
- **RBAC Protection**: Role-based access control with learner scope validation
- **Privacy Compliance**: GDPR-compliant data export and deletion capabilities
- **Tenant Isolation**: Multi-tenant architecture with strict data isolation
- **Event Publishing**: Kafka integration for real-time chat events
- **Performance Optimized**: Async operations, connection pooling, and caching
- **Comprehensive Logging**: Structured logging with request tracing

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Apps   │    │   API Gateway   │    │   Chat Service  │
│                 │────│     (Kong)      │────│    (FastAPI)    │
│  Web, Mobile    │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │     Kafka       │◄────────────┤
                       │  (Events)       │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │   PostgreSQL    │◄────────────┤
                       │  (Primary DB)   │             │
                       └─────────────────┘             │
                                                        │
                       ┌─────────────────┐             │
                       │     Redis       │◄────────────┘
                       │   (Cache)       │
                       └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+
- Kafka 2.8+ (optional for events)

### Installation

1. **Clone and Navigate**

   ```bash
   cd services/chat-svc
   ```

2. **Install Dependencies**

   ```bash
   pip install -e .
   ```

3. **Environment Setup**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Database Setup**

   ```bash
   # Run migrations
   alembic upgrade head
   ```

5. **Start Service**
   ```bash
   python -m app.main
   ```

The service will be available at `http://localhost:8000`

## Configuration

### Environment Variables

| Variable                  | Description                    | Default                  | Required |
| ------------------------- | ------------------------------ | ------------------------ | -------- |
| `DATABASE_URL`            | PostgreSQL connection string   | -                        | Yes      |
| `REDIS_URL`               | Redis connection string        | `redis://localhost:6379` | No       |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers                  | `localhost:9092`         | No       |
| `JWT_SECRET_KEY`          | JWT signing secret             | -                        | Yes      |
| `ENVIRONMENT`             | Environment (dev/staging/prod) | `development`            | No       |
| `LOG_LEVEL`               | Logging level                  | `INFO`                   | No       |
| `CORS_ORIGINS`            | Allowed CORS origins           | `["*"]`                  | No       |
| `PRIVACY_ENABLED`         | Enable privacy features        | `true`                   | No       |
| `ENABLE_RATE_LIMITING`    | Enable rate limiting           | `true`                   | No       |

### Example Configuration

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/chat_db

# Redis (optional)
REDIS_URL=redis://localhost:6379/0

# Kafka (optional)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256

# Service
ENVIRONMENT=development
LOG_LEVEL=INFO
PORT=8000

# Features
PRIVACY_ENABLED=true
ENABLE_RATE_LIMITING=true
MESSAGE_RETENTION_DAYS=365
MAX_MESSAGES_PER_THREAD=1000

# CORS
CORS_ORIGINS=["http://localhost:3000", "https://app.aivo.com"]
```

## API Documentation

### Authentication

All endpoints require JWT Bearer token authentication:

```bash
curl -H "Authorization: Bearer <jwt-token>" \
     -H "Content-Type: application/json" \
     https://api.aivo.com/chat/v1/threads
```

### Key Endpoints

#### Threads

- `GET /api/v1/threads` - List threads
- `POST /api/v1/threads` - Create thread
- `GET /api/v1/threads/{id}` - Get thread
- `PUT /api/v1/threads/{id}` - Update thread
- `DELETE /api/v1/threads/{id}` - Delete thread

#### Messages

- `GET /api/v1/threads/{id}/messages` - List messages
- `POST /api/v1/threads/{id}/messages` - Create message
- `GET /api/v1/threads/{id}/messages/{id}` - Get message
- `PUT /api/v1/threads/{id}/messages/{id}` - Update message
- `DELETE /api/v1/threads/{id}/messages/{id}` - Delete message

#### Privacy

- `POST /api/v1/privacy/export` - Export learner data
- `POST /api/v1/privacy/delete` - Delete learner data

### Complete API documentation is available at:

- **OpenAPI Spec**: [docs/api/rest/chat.yaml](../../docs/api/rest/chat.yaml)
- **Interactive Docs**: `http://localhost:8000/docs` (when running locally)

## Database Schema

### Tables

#### threads

- Stores chat thread metadata
- Indexed by tenant_id, learner_id, timestamps
- JSONB metadata for extensibility

#### messages

- Stores individual messages within threads
- Foreign key to threads with CASCADE delete
- JSONB content and metadata
- Indexed for efficient retrieval

#### chat_export_logs

- Tracks privacy export requests
- GDPR compliance auditing

#### chat_deletion_logs

- Tracks privacy deletion requests
- Right-to-be-forgotten compliance

### Indexes

```sql
-- Performance indexes
CREATE INDEX idx_threads_tenant_learner ON threads(tenant_id, learner_id);
CREATE INDEX idx_threads_updated_at ON threads(updated_at);
CREATE INDEX idx_messages_thread_id ON messages(thread_id);
CREATE INDEX idx_messages_created_at ON messages(created_at);

-- Privacy indexes
CREATE INDEX idx_export_tenant_learner ON chat_export_logs(tenant_id, learner_id);
CREATE INDEX idx_deletion_tenant_learner ON chat_deletion_logs(tenant_id, learner_id);
```

## Security & Privacy

### Access Control

The service implements comprehensive RBAC:

1. **JWT Authentication**: All requests require valid JWT tokens
2. **Tenant Isolation**: Users can only access data within their tenant
3. **Learner Scope**: Users can only access threads for learners in their scope
4. **Role-Based Permissions**: Different roles have different capabilities

### Privacy Compliance

- **Data Export**: Full GDPR-compliant data export
- **Right to Erasure**: Complete data deletion capabilities
- **Audit Trails**: All privacy operations are logged
- **Data Retention**: Configurable message retention policies

### Rate Limiting

- Per-IP rate limiting to prevent abuse
- Configurable limits (default: 60 requests/minute)
- Graceful degradation with proper error responses

## Event Publishing

The service publishes events to Kafka for real-time integrations:

### Event Types

- `CHAT_MESSAGE_CREATED` - New message posted
- `CHAT_THREAD_CREATED` - New thread created
- `CHAT_THREAD_DELETED` - Thread deleted
- `CHAT_PRIVACY_EXPORT_REQUESTED` - Data export requested
- `CHAT_PRIVACY_DELETION_REQUESTED` - Data deletion requested

### Event Format

```json
{
  "event_type": "CHAT_MESSAGE_CREATED",
  "tenant_id": "tenant-123",
  "learner_id": "learner-456",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "message_id": "msg-789",
    "thread_id": "thread-123",
    "sender_id": "user-456",
    "content": "Hello, world!",
    "message_type": "text"
  }
}
```

## Development

### Project Structure

```
services/chat-svc/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database setup
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── routes.py            # API routes
│   ├── middleware.py        # Authentication & middleware
│   └── events.py            # Event publishing
├── migrations/              # Alembic migrations
├── tests/                   # Test suite
├── pyproject.toml          # Dependencies
├── alembic.ini             # Alembic configuration
└── README.md               # This file
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test
pytest tests/test_api.py::TestThreadsAPI::test_create_thread
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Add new feature"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
ruff format app/ tests/

# Lint code
ruff check app/ tests/

# Type checking
mypy app/
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .

CMD ["python", "-m", "app.main"]
```

### Health Checks

The service provides health check endpoints:

- `GET /health` - Basic health status
- `GET /` - Service information and features

### Monitoring

Key metrics to monitor:

- Response times
- Error rates
- Database connection pool usage
- Message throughput
- Privacy operation completion rates

## Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check `DATABASE_URL` configuration
   - Verify PostgreSQL is running and accessible
   - Check network connectivity

2. **Authentication Failures**
   - Verify `JWT_SECRET_KEY` matches auth service
   - Check token expiration
   - Validate learner scope in JWT

3. **Kafka Connection Issues**
   - Check `KAFKA_BOOTSTRAP_SERVERS` configuration
   - Verify Kafka cluster is healthy
   - Events are optional - service works without Kafka

4. **Performance Issues**
   - Check database indexes
   - Monitor connection pool utilization
   - Enable Redis caching
   - Optimize query pagination

### Logs

Service logs are structured and include:

- Request ID for tracing
- User context (tenant, user ID)
- Performance metrics
- Error details

Example log entry:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "request_id": "req-12345",
  "user_id": "user-456",
  "tenant_id": "tenant-123",
  "message": "Thread created successfully",
  "thread_id": "thread-789",
  "duration_ms": 45
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

Proprietary - AIVO Virtual Brains Platform
