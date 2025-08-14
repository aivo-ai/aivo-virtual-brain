# Private Foundation Model Orchestrator

Manages per-learner namespaces and adapter lifecycle for the AIVO Virtual Brains platform.

## Overview

The Private-FM Orchestrator is responsible for:

- **Namespace Management**: Creating isolated namespaces for each learner's private foundation model
- **Adapter Lifecycle**: Managing nightly merge operations of learner-specific adapters
- **Fallback Mechanisms**: Handling corruption recovery and version lag scenarios
- **Security Enforcement**: Preventing upward promotion while allowing guardian-managed deletion

## Features

### 🏢 Namespace Isolation

- Creates unique namespace records for each learner: `{learnerId, subjects[], ns_uid}`
- Subscribes to `PRIVATE_BRAIN_READY` events for automatic namespace provisioning
- Maintains isolation boundaries to prevent cross-learner data leakage

### 🔄 Nightly Merge Operations

- Automated nightly jobs that merge adapters with frozen foundation models
- Produces versioned checkpoints with cryptographic hashes
- Simulates distributed foundation model operations for development

### 🛡️ Fallback & Recovery

- Detects corrupted namespaces and version lag (>3 versions behind)
- Automatic re-cloning from foundation model with event log replay
- Ensures data consistency and availability

### 🔒 Security Guarantees

- Enforces **no upward promotion** policy - learner changes never affect global models
- Guardian-controlled deletion capabilities
- Audit logging for all namespace operations

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Event Bus     │    │   Private-FM     │    │  Foundation     │
│                 │───▶│   Orchestrator   │───▶│  Model Store    │
│ PRIVATE_BRAIN_  │    │                  │    │                 │
│ READY events    │    └──────────────────┘    └─────────────────┘
└─────────────────┘             │
                                 ▼
                    ┌──────────────────┐
                    │   Namespace      │
                    │   Database       │
                    │                  │
                    └──────────────────┘
```

## API Endpoints

### Namespace Management

- `POST /api/v1/namespaces` - Create learner namespace
- `GET /api/v1/namespaces/{learner_id}` - Get namespace details
- `DELETE /api/v1/namespaces/{learner_id}` - Delete namespace (guardian only)

### Adapter Operations

- `POST /api/v1/namespaces/{learner_id}/merge` - Trigger adapter merge
- `GET /api/v1/namespaces/{learner_id}/checkpoints` - List checkpoints
- `POST /api/v1/namespaces/{learner_id}/fallback` - Initiate fallback recovery

### Monitoring

- `GET /api/v1/health` - Health check
- `GET /api/v1/metrics` - Prometheus metrics

## Event Handling

### Subscribed Events

- `PRIVATE_BRAIN_READY`: Learner brain initialization completed
  - Creates new namespace record
  - Initializes adapter tracking
  - Sets up merge scheduling

### Published Events

- `NAMESPACE_CREATED`: New learner namespace established
- `MERGE_COMPLETED`: Nightly merge operation finished
- `FALLBACK_INITIATED`: Recovery process started

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/private_fm_orchestrator
REDIS_URL=redis://localhost:6379/0

# Foundation Model Store
FM_STORE_URL=http://model-registry-svc:8000
FM_STORE_API_KEY=your_api_key

# Event Bus
EVENT_BUS_URL=redis://localhost:6379/1
EVENT_BUS_PREFIX=aivo.events

# Security
ENCRYPTION_KEY=your_32_byte_encryption_key
GUARDIAN_API_KEY=your_guardian_api_key

# Scheduling
NIGHTLY_MERGE_CRON="0 2 * * *"  # 2 AM daily
CLEANUP_CRON="0 4 * * 0"        # 4 AM Sunday

# Fallback Settings
MAX_VERSION_LAG=3
FALLBACK_RETRY_LIMIT=3
```

## Development

### Setup

```bash
# Install dependencies
pip install -e ".[dev,test]"

# Setup database
alembic upgrade head

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_isolation_merge.py
pytest -k "namespace"
pytest -k "fallback"

# With coverage
pytest --cov=app --cov-report=html
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Monitoring & Observability

### Metrics

- `namespace_count_total` - Total number of active namespaces
- `merge_operations_total` - Total merge operations performed
- `merge_duration_seconds` - Time taken for merge operations
- `fallback_operations_total` - Total fallback recoveries
- `checkpoint_size_bytes` - Size of generated checkpoints

### Health Checks

- Database connectivity
- Redis connectivity
- Foundation model store availability
- Event bus connectivity

### Logging

- Structured logging with correlation IDs
- Audit trail for all namespace operations
- Performance metrics for merge operations
- Security events for unauthorized access attempts

## Security

### Data Protection

- All namespace data encrypted at rest
- Cryptographic checksums for checkpoint integrity
- Secure communication with foundation model store

### Access Control

- API key authentication for service endpoints
- Guardian role verification for deletion operations
- Rate limiting on expensive operations

### Compliance

- Audit logging for regulatory compliance
- Data retention policies
- Privacy controls for learner data

## Deployment

### Docker

```bash
# Build image
docker build -t private-fm-orchestrator:latest .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://... \
  -e REDIS_URL=redis://... \
  private-fm-orchestrator:latest
```

### Kubernetes

See `k8s/` directory for deployment manifests.

### Health Monitoring

- Readiness probe: `GET /api/v1/health/ready`
- Liveness probe: `GET /api/v1/health/live`

## Contributing

1. Follow the established patterns in existing services
2. Add comprehensive tests for new features
3. Update API documentation in `docs/api/rest/private-fm.yaml`
4. Ensure security reviews for namespace operations
