# SIS Bridge Service

A service for synchronizing Student Information System (SIS) data with the SCIM 2.0 provider.

## Overview

The SIS Bridge Service provides:

- **Clever Integration**: Sync users, sections, and enrollments from Clever
- **ClassLink Integration**: Sync users, groups, and enrollments from ClassLink
- **Scheduled Sync**: Automated synchronization with configurable intervals
- **Real-time Webhooks**: Support for real-time updates from SIS providers
- **Seat Management**: Automatic seat allocation/deallocation based on enrollments
- **Audit Logging**: Complete audit trail of sync operations
- **Error Handling**: Robust error handling and retry mechanisms

## Features

### Supported SIS Providers

1. **Clever**
   - Student and teacher user sync
   - Section (class) sync
   - Enrollment sync
   - Real-time webhooks

2. **ClassLink**
   - User sync (students, teachers, admins)
   - Group sync (classes, schools)
   - Enrollment sync
   - OneRoster API support

### Sync Operations

- **Full Sync**: Complete data synchronization
- **Incremental Sync**: Only changed data since last sync
- **Selective Sync**: Sync specific data types or filters
- **Manual Sync**: On-demand synchronization

### Security

- **Vault Integration**: Secure storage of SIS API credentials
- **IP Allowlists**: Restrict webhook endpoints
- **Token Authentication**: Secure API access
- **Audit Logging**: Complete operation tracking

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://localhost:5432/sis_bridge_db

# Vault (for SIS credentials)
VAULT_URL=http://localhost:8200
VAULT_TOKEN=your-vault-token

# Tenant Service
TENANT_SERVICE_URL=http://localhost:8000
TENANT_SERVICE_TOKEN=your-service-token

# Redis (for job queue)
REDIS_URL=redis://localhost:6379

# Sync Settings
DEFAULT_SYNC_INTERVAL=3600  # 1 hour
MAX_RETRY_ATTEMPTS=3
BATCH_SIZE=100
```

### SIS Provider Configuration

Each tenant can configure multiple SIS providers with their own credentials and sync settings.

## API Endpoints

### Sync Management

- `POST /sync/{tenant_id}/start` - Start sync job
- `GET /sync/{tenant_id}/status` - Get sync status
- `POST /sync/{tenant_id}/stop` - Stop running sync
- `GET /sync/{tenant_id}/history` - Get sync history

### Webhook Endpoints

- `POST /webhooks/clever/{tenant_id}` - Clever webhook endpoint
- `POST /webhooks/classlink/{tenant_id}` - ClassLink webhook endpoint

### Configuration

- `GET /tenants/{tenant_id}/providers` - List SIS providers
- `POST /tenants/{tenant_id}/providers` - Add SIS provider
- `PUT /tenants/{tenant_id}/providers/{provider_id}` - Update provider
- `DELETE /tenants/{tenant_id}/providers/{provider_id}` - Remove provider

## Development

### Local Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start the service
uvicorn main:app --reload --port 8001
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=app tests/
```

## Deployment

The service is containerized and deployed via Docker Compose:

```yaml
sis-bridge-svc:
  build: ./services/sis-bridge-svc
  environment:
    - DATABASE_URL=postgresql://postgres:password@postgres:5432/sis_bridge_db
    - VAULT_URL=http://vault:8200
    - REDIS_URL=redis://redis:6379
  depends_on:
    - postgres
    - vault
    - redis
```
