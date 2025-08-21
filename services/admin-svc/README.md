# AIVO Admin Service

**S4-17 Implementation** - Internal admin backoffice service with strict RBAC and audit logging.

## Overview

The Admin Service provides secure internal tools for support staff to monitor system health, manage job queues, inspect approval workflows, and access learner data with proper consent mechanisms.

## Features

### 🔐 Security & Access Control

- **Strict RBAC**: Only `staff`, `tenant_admin`, and `system_admin` roles
- **JWT Authentication**: All endpoints require valid JWT tokens
- **Audit Logging**: Every admin action is logged and tracked
- **Session Management**: Admin sessions with timeout and tracking

### 📊 System Monitoring

- **Health Dashboard**: Real-time system status and metrics
- **Service Health**: Individual service monitoring and alerts
- **Performance Metrics**: Response times, uptime, and error rates
- **System Alerts**: Automated alerting for issues

### 📋 Approval Queue Management

- **Read-only Monitoring**: View approval requests and workflows
- **Status Tracking**: Monitor approval progress and bottlenecks
- **Filter & Search**: Find specific approvals by type, status, priority
- **Audit Trail**: Complete history of approval decisions

### 🔄 Job Queue Operations

- **Queue Monitoring**: View job status across all services
- **Incident Tools**: Requeue, cancel, or retry failed jobs
- **Performance Tracking**: Job duration, success rates, error analysis
- **Priority Management**: Handle urgent job processing

### 👥 Learner Data Inspection

- **Consent-based Access**: Requires guardian consent for data access
- **Support Sessions**: Time-limited access with specific purpose
- **JIT Tokens**: Just-in-time consent tokens for emergency access
- **Data Minimization**: Only access necessary data for support

## API Endpoints

### System Health & Stats

```
GET  /admin/stats                 # System statistics
GET  /admin/health                # Service health status
GET  /admin/alerts                # Active system alerts
GET  /admin/audit/summary         # Audit event summary
```

### Approval Queue

```
GET  /admin/approvals             # List approval requests
GET  /admin/approvals/stats       # Approval statistics
GET  /admin/approvals/{id}        # Get approval details
```

### Job Queue Management

```
GET  /admin/queues                # List job queues
GET  /admin/queues/stats          # Queue statistics
GET  /admin/queues/{name}/jobs    # Jobs in specific queue
POST /admin/jobs/{id}/requeue     # Requeue failed job
POST /admin/jobs/{id}/cancel      # Cancel pending job
POST /admin/jobs/{id}/retry       # Retry failed job
```

### Learner Data Access

```
POST /admin/support-session/request    # Request consent for data access
POST /admin/support-session           # Create support session
GET  /admin/learners/{id}/state       # Get learner state (requires consent)
```

### System Flags & Configuration

```
GET  /admin/flags                 # System feature flags
PUT  /admin/flags/{name}          # Toggle feature flag
```

### Audit & Security

```
GET  /admin/audit/events          # Query audit events
POST /admin/audit/export          # Export audit log
GET  /admin/security/sessions     # Active admin sessions
```

## Authentication & Authorization

### Required Roles

- **Staff**: Basic read-only access to dashboards and monitoring
- **Tenant Admin**: Full access within tenant scope + job management
- **System Admin**: Full system access + feature flag management

### JWT Token Requirements

```json
{
  "sub": "user_id",
  "email": "admin@example.com",
  "roles": ["staff", "tenant_admin"],
  "tenant_id": "tenant_123",
  "iat": 1234567890,
  "exp": 1234567890
}
```

### Audit Logging

Every admin action is logged with:

- Timestamp and session ID
- Actor (staff member) and role
- Action performed and resource accessed
- IP address and user agent
- Business justification (for data access)

## Data Access & Consent

### Support Session Flow

1. **Request Access**: Staff requests access to learner data with business purpose
2. **Consent Check**: System verifies active guardian consent
3. **JIT Token**: Generate just-in-time consent token if approved
4. **Time-limited Session**: Create session with specific expiration
5. **Audit Trail**: Log all data access during session
6. **Session Cleanup**: Automatic session termination

### Consent Requirements

- Guardian consent must be active and unexpired
- Support purpose must be documented
- Access is time-limited (default: 30 minutes)
- All accessed data is logged
- Emergency access requires additional approval

## Development

### Local Setup

```bash
cd services/admin-svc
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8020
```

### Environment Variables

```env
DATABASE_URL=postgresql://user:pass@localhost/aivo_admin
JWT_SECRET=your-jwt-secret
AUDIT_SERVICE_URL=http://localhost:8015
APPROVAL_SERVICE_URL=http://localhost:8010
REDIS_URL=redis://localhost:6379
LOG_LEVEL=INFO
```

### Testing

```bash
# Run all tests
pytest tests/ -v

# Test RBAC
pytest tests/test_auth.py -v

# Test audit logging
pytest tests/test_audit.py -v

# Test consent mechanisms
pytest tests/test_consent.py -v
```

## Security Considerations

### Access Control

- All endpoints require staff-level authentication
- Role-based permissions are strictly enforced
- No data modification capabilities (read-only + incident tools)
- Session timeout and automatic cleanup

### Data Protection

- Learner data access requires explicit consent
- Minimal data exposure (only what's needed for support)
- All access is logged and auditable
- Support sessions are time-limited

### Audit & Compliance

- Complete audit trail of all admin actions
- Regular security reviews and access audits
- Compliance with data protection regulations
- Incident response procedures

## Deployment

### Docker

```bash
docker build -t aivo-admin-svc .
docker run -p 8020:8000 aivo-admin-svc
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: admin-svc
spec:
  replicas: 2
  selector:
    matchLabels:
      app: admin-svc
  template:
    metadata:
      labels:
        app: admin-svc
    spec:
      containers:
        - name: admin-svc
          image: aivo-admin-svc:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: admin-secrets
                  key: database-url
```

## Monitoring & Operations

### Health Checks

- `/health` - Service health endpoint
- `/ready` - Readiness probe
- `/metrics` - Prometheus metrics

### Metrics

- Admin session duration and frequency
- API response times and error rates
- Consent request success rates
- Job management action counts

### Alerts

- Failed authentication attempts
- Unauthorized access attempts
- Long-running support sessions
- High error rates or service degradation

## License

MIT License - See LICENSE file for details.

## Contributing

1. Follow security guidelines for admin tools
2. All changes require security review
3. Test audit logging for new features
4. Document RBAC requirements
