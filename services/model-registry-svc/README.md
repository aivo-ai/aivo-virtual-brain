# AIVO Model Registry Service

## S2-02 Implementation: Model→Version→ProviderBinding Lifecycle Management

The Model Registry Service provides comprehensive model lifecycle management with version tracking, provider bindings, and automated retention policies.

## Features

### Core Functionality

- **Model Management**: Create, track, and manage AI models by name, task, and subject domain
- **Version Control**: Track model versions with SHA-256 hashes, evaluation scores, and cost metrics
- **Provider Bindings**: Map model versions to provider-specific implementations (OpenAI, Vertex AI, Bedrock, etc.)
- **Retention Policies**: Automatically archive old versions (keep last N=3 by default)
- **Cost & Performance Tracking**: Monitor cost per 1K tokens, evaluation scores, and SLO compliance

### API Endpoints

#### Models

- `POST /models` - Create new model
- `GET /models/{id}` - Get model by ID
- `GET /models/name/{name}` - Get model by name
- `GET /models` - List models with filtering
- `PUT /models/{id}` - Update model
- `DELETE /models/{id}` - Delete model

#### Versions

- `POST /versions` - Create new version
- `GET /versions/{id}` - Get version by ID
- `GET /versions` - List versions with filtering
- `PUT /versions/{id}` - Update version
- `DELETE /versions/{id}` - Delete version

#### Provider Bindings

- `POST /bindings` - Create provider binding
- `GET /bindings/{id}` - Get binding by ID
- `GET /bindings` - List bindings with filtering
- `PUT /bindings/{id}` - Update binding
- `DELETE /bindings/{id}` - Delete binding

#### Statistics & Retention

- `GET /stats` - Get registry statistics
- `GET /health` - Health check
- `POST /retention/apply` - Apply retention policy
- `GET /retention/stats` - Get retention statistics

## Database Schema

### Models Table

- `id`: Primary key
- `name`: Unique model name
- `task`: Model task type (generation, embedding, moderation, etc.)
- `subject`: Subject domain/category
- `description`: Model description
- `created_at`, `updated_at`: Timestamps

### Model Versions Table

- `id`: Primary key
- `model_id`: Foreign key to models
- `hash`: SHA-256 hash (unique per model)
- `version`: Semantic version (unique per model)
- `region`: Deployment region
- `cost_per_1k`: Cost per 1K tokens/items
- `eval_score`: Evaluation score (0-1)
- `slo_ok`: SLO compliance flag
- `artifact_uri`: S3/GCS URI for model artifacts
- `archive_uri`: Glacier/Archive URI for old versions
- `size_bytes`: Model size
- `model_type`: Model type (transformer, llm, etc.)
- `framework`: Framework (pytorch, tensorflow, onnx)
- `created_at`, `archived_at`: Timestamps

### Provider Bindings Table

- `id`: Primary key
- `version_id`: Foreign key to model_versions
- `provider`: Provider name (openai, vertex, bedrock, etc.)
- `provider_model_id`: Provider's model identifier
- `status`: Binding status (active, inactive, deprecated)
- `config`: JSON config for provider settings
- `endpoint_url`: Custom endpoint URL
- `avg_latency_ms`: Average latency
- `success_rate`: Success rate (0-1)
- `last_used_at`: Last usage timestamp
- `created_at`, `updated_at`: Timestamps

## Retention Policy

The service implements automatic retention policies:

1. **Default Retention**: Keep last 3 versions per model
2. **Automatic Archiving**: Older versions moved to archive storage (Glacier)
3. **Configurable Count**: Retention count can be customized (1-10 versions)
4. **Cleanup**: Very old archived versions can be purged after 90 days

## Installation & Deployment

### Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your database settings

# Run database migrations
alembic upgrade head

# Start the service
python -m uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

### Docker Deployment

```bash
# Build image
docker build -t aivo-model-registry:latest .

# Run container
docker run -d \
  --name model-registry \
  -p 8003:8003 \
  -e POSTGRES_HOST=your-db-host \
  -e POSTGRES_PASSWORD=your-password \
  aivo-model-registry:latest
```

### Docker Compose

```yaml
version: "3.8"
services:
  model-registry:
    build: .
    ports:
      - "8003:8003"
    environment:
      - POSTGRES_HOST=postgres
      - POSTGRES_PASSWORD=postgres
    depends_on:
      - postgres

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=model_registry
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## Configuration

### Environment Variables

| Variable                  | Default              | Description                     |
| ------------------------- | -------------------- | ------------------------------- |
| `HOST`                    | `0.0.0.0`            | Server host                     |
| `PORT`                    | `8003`               | Server port                     |
| `POSTGRES_HOST`           | `localhost`          | Database host                   |
| `POSTGRES_PORT`           | `5432`               | Database port                   |
| `POSTGRES_DB`             | `model_registry`     | Database name                   |
| `POSTGRES_USER`           | `postgres`           | Database user                   |
| `POSTGRES_PASSWORD`       | `postgres`           | Database password               |
| `DB_POOL_SIZE`            | `10`                 | Connection pool size            |
| `OTEL_SERVICE_NAME`       | `model-registry-svc` | OpenTelemetry service name      |
| `DEFAULT_RETENTION_COUNT` | `3`                  | Default version retention count |

## Usage Examples

### Create a Model

```bash
curl -X POST http://localhost:8003/models \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gpt-4-turbo",
    "task": "generation",
    "subject": "general",
    "description": "GPT-4 Turbo model for general text generation"
  }'
```

### Create a Version

```bash
curl -X POST http://localhost:8003/versions \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "hash": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
    "version": "1.0.0",
    "region": "us-east-1",
    "cost_per_1k": 0.01,
    "eval_score": 0.92,
    "artifact_uri": "s3://models/gpt-4-turbo/v1.0.0/model.bin"
  }'
```

### Create a Provider Binding

```bash
curl -X POST http://localhost:8003/bindings \
  -H "Content-Type: application/json" \
  -d '{
    "version_id": 1,
    "provider": "openai",
    "provider_model_id": "gpt-4-0125-preview",
    "status": "active",
    "config": {
      "temperature": 0.7,
      "max_tokens": 2000
    }
  }'
```

### Apply Retention Policy

```bash
curl -X POST http://localhost:8003/retention/apply \
  -H "Content-Type: application/json" \
  -d '{
    "model_id": 1,
    "retention_count": 3
  }'
```

## Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html
```

## Monitoring

The service includes:

- **Health checks**: `/health` endpoint
- **OpenTelemetry**: Distributed tracing and metrics
- **Prometheus metrics**: Performance and usage statistics
- **Database connection monitoring**: Connection pool health

## Security

- **Input validation**: Pydantic schemas with comprehensive validation
- **SQL injection protection**: SQLAlchemy ORM with parameterized queries
- **CORS configuration**: Configurable origin restrictions
- **Error handling**: Sanitized error responses

## Performance

- **Database optimization**: Indexed queries and connection pooling
- **Pagination**: All list endpoints support pagination
- **Caching**: Database connection pooling and prepared statements
- **Async operations**: FastAPI async/await pattern throughout

## Integration

The Model Registry integrates with:

- **Inference Gateway**: Model version and provider routing
- **Observability Stack**: OpenTelemetry metrics and tracing
- **Storage Systems**: S3/GCS for model artifacts, Glacier for archives
- **CI/CD Pipelines**: Model deployment and version management

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  Service Layer   │────│  Database ORM   │
│   (API Routes)  │    │  (Business Logic)│    │  (SQLAlchemy)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   OpenAPI Docs  │    │ Retention Manager│    │   PostgreSQL    │
│   (Swagger UI)  │    │  (Policy Engine) │    │   (Database)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## License

MIT License - See LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Support

For support and questions:

- Create an issue in the repository
- Check the API documentation at `/docs`
- Review the test suite for usage examples
