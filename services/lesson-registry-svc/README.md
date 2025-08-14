# Lesson Registry Service

Educational content management system with versioning, asset management, and CDN-signed delivery.

## Features

- **Content Versioning**: Semantic versioning for lesson content with full history
- **Asset Management**: File upload, integrity validation, and metadata tracking
- **CDN Integration**: Signed URLs for secure, time-limited asset access
- **Role-Based Access**: Permission control for different user types
- **Manifest Generation**: Complete lesson packages ready for delivery

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Client    │    │   Lesson API     │    │  CDN Provider   │
│                 │◄──►│                  │◄──►│ (CloudFront/    │
│ - Teachers      │    │ - FastAPI        │    │  MinIO)         │
│ - Students      │    │ - PostgreSQL     │    │                 │
│ - Parents       │    │ - JWT Auth       │    │ - Signed URLs   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Storage Layer   │
                       │                  │
                       │ - S3/MinIO       │
                       │ - Asset Files    │
                       │ - Checksums      │
                       └──────────────────┘
```

## API Endpoints

### Core Endpoints

- `POST /api/v1/lesson` - Create new lesson
- `GET /api/v1/lesson` - List lessons with filtering
- `GET /api/v1/lesson/{id}` - Get lesson details
- `PATCH /api/v1/lesson/{id}` - Update lesson metadata
- `POST /api/v1/lesson/{id}/version` - Create new version
- `GET /api/v1/manifest/{lessonId}` - **Get signed manifest**
- `POST /api/v1/lesson/{id}/version/{versionId}/asset` - Register asset

### Manifest Endpoint (Core Feature)

The manifest endpoint is the primary interface for lesson delivery:

```http
GET /api/v1/manifest/{lessonId}?version=1.0.0&expires_seconds=600
```

Returns a complete lesson manifest with:

- Signed CDN URLs for all assets
- Asset integrity checksums
- Entry point identification
- Expiration timestamps
- Complete metadata

## Database Schema

### Tables

- **`lesson`**: Core lesson metadata and status
- **`version`**: Versioned lesson content with semantic versioning
- **`asset`**: Individual files with S3 keys, checksums, and metadata

### Key Relationships

```sql
lesson (1) -> (N) version (1) -> (N) asset
```

## CDN Integration

Supports multiple CDN providers:

### CloudFront

- Private key signing
- Global edge distribution
- Custom domain support
- Policy-based access control

### MinIO/S3

- Presigned URL generation
- Self-hosted option
- S3-compatible API
- Cost-effective storage

## Role-Based Permissions

| Role          | Create Lessons | Create Versions | Update Metadata | Access Content |
| ------------- | -------------- | --------------- | --------------- | -------------- |
| subject_brain | ✅             | ✅              | ✅              | ✅             |
| teacher       | ❌             | ❌              | ✅ (limited)    | ✅             |
| parent        | ❌             | ❌              | ❌              | ✅             |
| student       | ❌             | ❌              | ❌              | ✅             |
| admin         | ✅             | ✅              | ✅              | ✅             |

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/lesson_registry

# CDN Configuration
CDN_TYPE=minio  # or cloudfront
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=lesson-assets

# CloudFront (if using)
CLOUDFRONT_DOMAIN=https://d123456.cloudfront.net
CLOUDFRONT_KEY_PAIR_ID=KEYPAIRID123
CLOUDFRONT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----...

# Security
JWT_SECRET_KEY=your-secret-key
CDN_EXPIRES_SECONDS=600
```

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Testing

```bash
# Run test suite
pytest tests/ -v

# Run manifest signing tests specifically
pytest tests/test_manifest_signing.py -v

# Test with coverage
pytest --cov=app tests/
```

### Key Test Scenarios

- Upload + manifest retrieval
- Expired signature handling (403 errors)
- Version differences in manifests
- Role-based permission validation
- Batch asset URL signing

## Production Deployment

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health with database/CDN status
curl http://localhost:8000/health/detailed
```

## Security Considerations

- All asset URLs are time-limited (expires after 10 minutes by default)
- JWT token authentication required for all endpoints
- Role-based access control enforced at API level
- Asset integrity validated with SHA-256 checksums
- CDN signatures prevent unauthorized access

## Monitoring

Key metrics to monitor:

- Manifest generation latency
- CDN signing success rate
- Asset upload success rate
- Database connection health
- Token validation errors

## Troubleshooting

### Common Issues

1. **CDN signing failures**: Check credentials and configuration
2. **Database connection errors**: Verify DATABASE_URL and network access
3. **Permission denied**: Verify user role and JWT token validity
4. **Asset not found**: Check S3 key and bucket configuration

### Debug Endpoints (Development Only)

- `GET /debug/config` - View sanitized configuration
- `GET /debug/signer` - Test CDN signer functionality
