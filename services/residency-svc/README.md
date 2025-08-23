# Data Residency Service (S6-05)

The Data Residency Service provides comprehensive data residency pinning and regional routing capabilities to ensure compliance with international data protection regulations and regional data sovereignty requirements.

## Overview

This service implements:

- **Region-based Data Pinning**: Associates tenants and learners with specific geographic regions
- **Cross-Region Policy Enforcement**: Prevents unauthorized data movement between regions
- **Compliance Framework Integration**: Enforces GDPR, CCPA, FERPA, COPPA, PIPEDA, and other regulations
- **Emergency Override System**: Controlled break-glass procedures for critical situations
- **Comprehensive Audit Logging**: Complete audit trail for compliance and security monitoring
- **Infrastructure Routing**: Regional routing for storage, search, and inference services

## Features

### 🌍 Regional Data Residency

- Tenant and learner-specific region assignment
- Primary region with optional allowed/prohibited regions
- Automatic region inheritance (learners inherit tenant region by default)
- Support for 7 global regions: US East/West, EU West/Central, APAC South/East, Canada Central

### 🔒 Compliance Frameworks

- **GDPR**: EU data residency with cross-region restrictions
- **CCPA**: California privacy protections
- **FERPA**: Educational record protections (US/Canada)
- **COPPA**: Children's data protection with stricter retention
- **PIPEDA**: Canadian privacy legislation
- **LGPD**: Brazilian data protection (planned)

### 🚨 Emergency Procedures

- Time-limited emergency overrides
- Reason tracking and approval workflows
- Usage monitoring and automatic expiration
- Comprehensive audit trail for all overrides

### 📊 Infrastructure Integration

- Region-specific S3/MinIO bucket routing
- OpenSearch domain selection by region
- Inference provider routing (AWS Bedrock, OpenAI, Anthropic)
- Presigned URL generation with region constraints

## API Endpoints

### Policy Management

```http
POST /api/v1/policies                    # Create residency policy
GET  /api/v1/policies/{tenant_id}        # Get tenant policies
PUT  /api/v1/policies/{policy_id}        # Update policy
```

### Data Access Resolution

```http
POST /api/v1/access/resolve              # Resolve data access request
GET  /api/v1/regions                     # List supported regions
```

### Emergency Procedures

```http
POST /api/v1/emergency/override          # Request emergency override
GET  /api/v1/emergency/overrides         # List active overrides
```

### Audit and Compliance

```http
GET  /api/v1/audit/access-logs/{tenant_id}  # Get access audit logs
GET  /api/v1/audit/violations               # Get compliance violations
```

## Quick Start

### Development Setup

1. **Clone and setup**:

```bash
cd services/residency-svc
docker-compose up -d postgres redis
```

2. **Install dependencies**:

```bash
pip install -r requirements.txt
```

3. **Run the service**:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. **Initialize database**:

```bash
# Database tables are auto-created on startup
# Sample data is inserted via init-db.sql
```

### Docker Deployment

```bash
# Full stack with all dependencies
docker-compose up -d

# Service only (requires external DB)
docker build -t residency-svc .
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379/0 \
  residency-svc
```

## Configuration

### Environment Variables

| Variable                | Description                  | Default                                                           |
| ----------------------- | ---------------------------- | ----------------------------------------------------------------- |
| `DATABASE_URL`          | PostgreSQL connection string | `postgresql+asyncpg://postgres:postgres@localhost:5432/residency` |
| `REDIS_URL`             | Redis connection string      | `redis://localhost:6379/0`                                        |
| `SECRET_KEY`            | JWT secret key               | `your-secret-key-change-in-production`                            |
| `DEBUG`                 | Enable debug mode            | `false`                                                           |
| `LOG_LEVEL`             | Logging level                | `INFO`                                                            |
| `AWS_ACCESS_KEY_ID`     | AWS credentials              | -                                                                 |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials              | -                                                                 |

### Regional Configuration

The service supports the following regions:

- **us-east**: US East (Virginia) - Default region
- **us-west**: US West (Oregon)
- **eu-west**: EU West (Ireland) - GDPR compliant
- **eu-central**: EU Central (Frankfurt) - GDPR compliant
- **apac-south**: Asia Pacific South (Mumbai)
- **apac-east**: Asia Pacific East (Tokyo)
- **ca-central**: Canada Central - PIPEDA compliant

Each region has dedicated:

- S3/MinIO storage buckets
- OpenSearch domains
- Inference provider endpoints
- Compliance certifications

## Usage Examples

### Create Residency Policy

```python
import httpx

policy_data = {
    "tenant_id": "acme-edu",
    "learner_id": "student-123",  # Optional - for learner-specific policy
    "primary_region": "us-east",
    "allowed_regions": ["us-west", "ca-central"],
    "prohibited_regions": ["eu-west"],
    "compliance_frameworks": ["ferpa", "coppa"],
    "data_classification": "educational",
    "allow_cross_region_failover": True,
    "data_retention_days": 2555,  # 7 years for educational records
    "emergency_contact": "dpo@acme-edu.com"
}

response = httpx.post(
    "http://localhost:8000/api/v1/policies",
    json=policy_data,
    headers={
        "X-User-ID": "admin-user",
        "X-Request-ID": "req-123"
    }
)

print(response.json())
```

### Resolve Data Access

```python
access_request = {
    "tenant_id": "acme-edu",
    "learner_id": "student-123",
    "operation_type": "read",
    "resource_type": "document",
    "resource_id": "assignment-456",
    "requested_region": "us-west"  # Optional - cross-region request
}

response = httpx.post(
    "http://localhost:8000/api/v1/access/resolve",
    json=access_request,
    headers={
        "X-User-ID": "teacher-789",
        "X-Request-ID": "req-456",
        "X-Region": "us-east"  # Current user region
    }
)

result = response.json()
print(f"Access allowed: {result['allowed']}")
print(f"Target region: {result['target_region']}")
print(f"Infrastructure: {result['infrastructure']}")
```

### Emergency Override

```python
override_request = {
    "tenant_id": "acme-edu",
    "reason": "Critical system failure requires emergency data access",
    "affected_learners": ["student-123", "student-456"],
    "source_region": "us-east",
    "target_region": "eu-west",
    "duration_hours": 24
}

response = httpx.post(
    "http://localhost:8000/api/v1/emergency/override",
    json=override_request,
    headers={
        "X-User-ID": "emergency-admin",
        "X-Request-ID": "emergency-req-789"
    }
)

override = response.json()
print(f"Override ID: {override['override_id']}")
print(f"Status: {override['status']}")
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest test_routing_policies.py -v

# Run specific test categories
pytest test_routing_policies.py::TestResidencyPolicies -v
pytest test_routing_policies.py::TestComplianceFrameworks -v
pytest test_routing_policies.py::TestEmergencyOverrides -v

# Run with coverage
pytest test_routing_policies.py --cov=app --cov-report=html
```

### Integration Testing

```bash
# Test with real database
docker-compose up -d postgres redis
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/residency
pytest test_routing_policies.py -v

# Test emergency scenarios
pytest test_routing_policies.py::test_emergency_override_excessive_duration -v
pytest test_routing_policies.py::test_access_with_emergency_override -v
```

### Load Testing

```bash
# Install load testing tools
pip install locust

# Run load tests (create locustfile.py first)
locust -f locustfile.py --host=http://localhost:8000
```

## Monitoring

### Health Checks

```bash
# Service health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/health/db

# Regional infrastructure health
curl http://localhost:8000/health/regions
```

### Metrics

The service exposes Prometheus metrics on port 8001:

- `residency_policies_total`: Total residency policies
- `data_access_requests_total`: Total data access requests by region
- `cross_region_access_total`: Cross-region access attempts
- `compliance_violations_total`: Compliance violations by framework
- `emergency_overrides_total`: Emergency overrides by status

### Logging

Structured logging with the following fields:

- `timestamp`: ISO 8601 timestamp
- `level`: Log level (DEBUG, INFO, WARNING, ERROR)
- `tenant_id`: Tenant identifier
- `learner_id`: Learner identifier (when applicable)
- `user_id`: User performing the action
- `region`: Target region
- `compliance_frameworks`: Applicable compliance frameworks
- `operation_type`: Type of operation (read, write, inference)
- `emergency_override`: Whether emergency override was used

Example log entry:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "message": "Data access resolved",
  "tenant_id": "acme-edu",
  "learner_id": "student-123",
  "user_id": "teacher-789",
  "region": "us-east",
  "compliance_frameworks": ["ferpa"],
  "operation_type": "read",
  "emergency_override": false,
  "request_id": "req-abc123"
}
```

## Security Considerations

### Data Protection

- All database connections use TLS encryption
- Sensitive data is encrypted at rest using AES-256
- API communications require TLS 1.2+
- Presigned URLs have short expiration times (1 hour default)

### Access Control

- All API endpoints require authentication headers
- Role-based access control for admin functions
- Emergency overrides require elevated permissions
- Audit logs are immutable and tamper-evident

### Compliance

- GDPR: Right to erasure, data portability, consent management
- COPPA: Parental consent verification, strict data retention
- FERPA: Educational purpose restrictions, directory information handling
- CCPA: Opt-out rights, data sale restrictions

## Troubleshooting

### Common Issues

**Database Connection Errors**:

```bash
# Check database status
docker-compose logs postgres

# Test connection
psql postgresql://postgres:postgres@localhost:5432/residency
```

**Region Configuration Issues**:

```bash
# Validate region configuration
curl http://localhost:8000/api/v1/regions

# Check infrastructure health
curl http://localhost:8000/health/regions
```

**Compliance Violations**:

```bash
# Get violation details
curl http://localhost:8000/api/v1/audit/violations

# Check policy configuration
curl http://localhost:8000/api/v1/policies/{tenant_id}
```

### Debug Mode

Enable debug logging:

```bash
export DEBUG=true
export LOG_LEVEL=DEBUG
uvicorn app.main:app --reload
```

## Development

### Project Structure

```
services/residency-svc/
├── app/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── routes.py            # API routes
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   └── utils.py             # Utility functions
├── test_routing_policies.py # Comprehensive tests
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container definition
├── docker-compose.yml      # Development stack
├── init-db.sql            # Database initialization
└── README.md              # This file
```

### Contributing

1. Create feature branch: `git checkout -b feature/new-capability`
2. Make changes and add tests
3. Run test suite: `pytest test_routing_policies.py -v`
4. Update documentation
5. Submit pull request

### Code Style

- Use Black for code formatting: `black app/`
- Use isort for import sorting: `isort app/`
- Use mypy for type checking: `mypy app/`
- Follow PEP 8 guidelines

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

- Create GitHub issue for bugs/feature requests
- Review audit logs for troubleshooting: `/api/v1/audit/access-logs`
- Check health endpoints for system status
- Review compliance documentation for regulatory questions

---

**S6-05 Data Residency Pinning & Regional Routing** - Ensuring global compliance through intelligent data governance.
