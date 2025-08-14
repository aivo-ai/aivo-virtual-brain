# AIVO Model Trainer Service

## S2-03 Implementation: OpenAI Fine-Tuning with Evaluation & Promotion

The Model Trainer Service orchestrates fine-tuning workflows, tracks training jobs, runs evaluations, and promotes successful models to the registry.

## Features

### Core Functionality

- **Fine-Tuning Jobs**: Launch OpenAI fine-tuning jobs with configurable parameters
- **Status Tracking**: Monitor training progress and completion
- **Evaluation Harness**: Run pedagogy and safety evaluations on trained models
- **Model Promotion**: Automatically register successful models with bindings
- **Datasheet Compliance**: Enforce dataset documentation requirements

### API Endpoints

#### Training Jobs

- `POST /trainer/jobs` - Create fine-tuning job
- `GET /trainer/jobs/{id}` - Get job status and details
- `GET /trainer/jobs` - List training jobs with filtering
- `DELETE /trainer/jobs/{id}` - Cancel training job

#### Evaluation

- `POST /trainer/jobs/{id}/evaluate` - Run evaluation harness
- `GET /trainer/jobs/{id}/evaluation` - Get evaluation results
- `POST /trainer/jobs/{id}/promote` - Promote model to registry

#### Health & Status

- `GET /health` - Service health check
- `GET /stats` - Training service statistics

## Quick Start

### Development

```bash
# Clone and navigate to service
cd services/model-trainer-svc

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
make dev

# Run tests
make test
```

### Docker

```bash
# Build and run with Docker Compose
docker-compose up --build

# Run tests in container
docker-compose exec trainer python -m pytest
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY` - OpenAI API key for fine-tuning
- `MODEL_REGISTRY_URL` - Model Registry service URL
- `DATABASE_URL` - PostgreSQL database connection
- `REDIS_URL` - Redis for job queue (optional)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, etc.)

### Training Configuration

```json
{
  "provider": "openai",
  "baseModel": "gpt-3.5-turbo",
  "datasetUri": "s3://bucket/training-data.jsonl",
  "config": {
    "n_epochs": 3,
    "batch_size": 1,
    "learning_rate_multiplier": 0.1
  },
  "policy": {
    "scope": "tenant_123",
    "thresholds": {
      "pedagogy_score": 0.8,
      "safety_score": 0.9
    }
  },
  "datasheet": {
    "source": "internal_curriculum",
    "license": "proprietary",
    "redaction": "pii_removed"
  }
}
```

## Architecture

### Components

- **Training Orchestrator**: Manages job lifecycle
- **OpenAI Trainer**: Handles OpenAI fine-tuning API
- **Evaluation Harness**: Runs pedagogy and safety tests
- **Registry Client**: Promotes models to registry
- **Job Queue**: Manages async training tasks

### Data Flow

1. **Job Creation**: Receive training request with datasheet
2. **Validation**: Validate dataset and configuration
3. **Training**: Launch OpenAI fine-tuning job
4. **Monitoring**: Poll status until completion
5. **Evaluation**: Run evaluation harness on trained model
6. **Promotion**: Register model if thresholds met

## Testing

### Unit Tests

- Training job creation and validation
- OpenAI API integration (mocked)
- Evaluation harness functionality
- Registry promotion workflow

### Integration Tests

- End-to-end training workflow
- Model registry integration
- Dataset validation and processing

## Production Considerations

### Security

- API key rotation and secure storage
- Dataset access controls
- Model artifact encryption

### Scalability

- Async job processing with Redis/Celery
- Distributed evaluation for large models
- Cost optimization for training resources

### Monitoring

- Training job metrics and alerts
- Evaluation result tracking
- Cost and usage monitoring

## API Reference

See `docs/api/rest/model-trainer.yaml` for detailed API documentation.
