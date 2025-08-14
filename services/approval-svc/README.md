# AIVO Approval Service

**S2-10 Implementation** - Approval workflow service for level changes, IEP changes, and consent-sensitive actions with state machine logic, TTL, and role-based approvals.

## Overview

The AIVO Approval Service manages approval workflows for critical educational decisions that require stakeholder sign-off. It implements a robust state machine with automatic expiration, role-based access control, and webhook integration for orchestrating downstream actions.

## Features

### 🔄 **State Machine Workflow**

- **PENDING** → **APPROVED**/**REJECTED**/**EXPIRED**
- Any rejection immediately rejects the entire request
- All required approvals must be received for final approval
- Automatic expiration handling with configurable TTL

### 👥 **Role-Based Approvals**

- **Guardian**: Parent/legal guardian approval
- **Teacher**: Classroom teacher approval
- **Case Manager**: Special education case manager
- **District Admin**: Administrative approval
- **Administrator**: School administrator
- **Service Provider**: Related service provider

### 📋 **Approval Types**

- **Level Changes**: Academic level progression
- **IEP Changes**: Individual Education Program modifications
- **Consent-Sensitive**: Actions requiring explicit consent
- **Placement Changes**: Educational placement modifications
- **Service Changes**: Related service adjustments

### ⏰ **TTL & Expiration**

- Configurable expiration times (1 hour - 1 year)
- Automatic cleanup of expired requests
- Background task monitoring
- Reminder notifications (integration ready)

### 🔗 **Integration Features**

- Webhook notifications to orchestrator
- Comprehensive audit logging
- REST API with OpenAPI documentation
- Database migrations with Alembic

## API Endpoints

### Core Endpoints

```
POST   /api/v1/approvals              Create approval request
GET    /api/v1/approvals              List approval requests
GET    /api/v1/approvals/{id}         Get approval request
POST   /api/v1/approvals/{id}/decision Make approval decision
GET    /api/v1/approvals/stats        Get statistics
```

### Health & Monitoring

```
GET    /health                        Basic health check
GET    /health/detailed               Detailed health with DB check
```

## State Machine

```
PENDING ──┬── All Required Approvals ──► APPROVED
          ├── Any Rejection ───────────► REJECTED
          └── TTL Expired ─────────────► EXPIRED
```

### State Transitions

- **PENDING**: Awaiting approver decisions
- **APPROVED**: All required roles have approved
- **REJECTED**: At least one role has rejected
- **EXPIRED**: TTL exceeded without completion

## Usage Examples

### Create IEP Change Request

```json
POST /api/v1/approvals
{
  "tenant_id": "123e4567-e89b-12d3-a456-426614174000",
  "approval_type": "iep_change",
  "resource_id": "iep_12345",
  "resource_type": "iep",
  "title": "IEP Goals Update for Student John Doe",
  "description": "Updating annual goals based on Q2 assessment",
  "expires_in_hours": 72,
  "requested_by": "teacher_789",
  "required_roles": ["guardian", "teacher"],
  "webhook_url": "https://orchestrator.example.com/webhooks"
}
```

### Make Approval Decision

```json
POST /api/v1/approvals/{id}/decision
{
  "approver_id": "guardian_123",
  "approver_role": "guardian",
  "approved": true,
  "comments": "I approve these changes based on our meeting"
}
```

### Dual Approval Workflow

1. Create request with `required_roles: ["guardian", "teacher"]`
2. Guardian approves → Status remains **PENDING**
3. Teacher approves → Status becomes **APPROVED**
4. Webhook notification sent to orchestrator

## Database Schema

### Tables

- **approval_requests**: Core approval request data
- **approval_decisions**: Individual role decisions
- **approval_reminders**: Scheduled reminder notifications
- **approval_audit_logs**: Complete audit trail

### Indexes

- Tenant/type composite indexes for fast filtering
- Status/expiration indexes for cleanup tasks
- Timestamp indexes for reporting queries

## Testing

### Comprehensive Test Suite

```bash
# Run all tests
pytest tests/test_approvals.py -v

# Run specific test categories
pytest tests/test_approvals.py::TestApprovalRequests -v
pytest tests/test_approvals.py::TestApprovalDecisions -v
pytest tests/test_approvals.py::TestApprovalExpiration -v
```

### Test Coverage

- ✅ **Dual approval required path**: Both guardian & teacher must approve
- ✅ **Timeout expiry**: Automatic expiration handling
- ✅ **State machine transitions**: Valid/invalid state changes
- ✅ **Role authorization**: Only required roles can approve
- ✅ **Duplicate prevention**: Same role cannot approve twice
- ✅ **Immediate rejection**: Any rejection ends workflow
- ✅ **Statistics & metrics**: Comprehensive reporting

## Development

### Setup

```bash
# Install dependencies
poetry install

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/approval_db
CORS_ORIGINS=http://localhost:3000,https://app.aivo.ai
ENVIRONMENT=development
```

### Database Migration

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## Architecture

### Dependencies

- **FastAPI**: Modern async web framework
- **SQLAlchemy**: ORM with PostgreSQL support
- **Pydantic**: Data validation and serialization
- **Alembic**: Database migration management
- **HTTPx**: Async HTTP client for webhooks

### Integration Points

- **Orchestrator Service**: Webhook notifications on decisions
- **Notification Service**: Reminder scheduling (ready for integration)
- **Auth Service**: User authentication and authorization
- **Audit Service**: Comprehensive logging and compliance

## Monitoring & Operations

### Health Checks

- Basic health endpoint for load balancer
- Detailed health with database connectivity
- Background task monitoring

### Metrics

- Request count and timing statistics
- Approval rates by type and tenant
- Average and median approval times
- Expiration and rejection rates

### Logging

- Structured logging with request IDs
- Audit trail for all approval actions
- Error tracking and debugging context
- Performance monitoring hooks

## Security

### Role-Based Access

- Strict role validation on approval decisions
- Tenant isolation for multi-tenant security
- Audit logging for compliance requirements

### Data Protection

- Encrypted webhook payloads
- Secure database connections
- Input validation and sanitization
- SQL injection prevention

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install poetry && poetry install --no-dev
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Kubernetes

- Health check endpoints for readiness/liveness probes
- Horizontal pod autoscaling support
- Config map and secret integration
- Service mesh compatibility

---

## License

MIT License - see [LICENSE](../../LICENSE) file for details.

## Contributing

Please see [CONTRIBUTING.md](../../CONTRIBUTING.md) for development guidelines and contribution process.
