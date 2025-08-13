# AIVO Assessment Service

# S1-10 Implementation - Assessment Service with IRT Engine

## Overview

The AIVO Assessment Service provides intelligent baseline assessment capabilities using Item Response Theory (IRT) to accurately measure learner proficiency across subjects. It supports adaptive questioning, psychometric analysis, and proficiency level mapping (L0-L4).

## Features

### Core Assessment Engine

- **IRT-Ready**: 3-Parameter Logistic (3PL) model with discrimination, difficulty, and guessing parameters
- **Adaptive Questioning**: Information-based item selection for efficient assessments
- **Theta Estimation**: Expected A Posteriori (EAP) method with prior distribution
- **Termination Criteria**: Standard error thresholds and maximum information detection

### Proficiency Mapping

- **Level Classification**: L0 (Beginner) to L4 (Expert) mapping based on theta values
- **Confidence Scoring**: Statistical confidence in level assignments
- **Performance Analysis**: Strengths, weaknesses, and recommendation generation

### API Endpoints

#### Baseline Assessment

- `POST /api/v1/baseline/start` - Start new baseline assessment
- `POST /api/v1/baseline/answer` - Submit question response
- `GET /api/v1/baseline/result/{session_id}` - Retrieve assessment results

#### Session Management

- `GET /api/v1/assessment/sessions/{learner_id}` - List learner sessions
- `GET /api/v1/assessment/session/{session_id}` - Get session details
- `DELETE /api/v1/assessment/session/{session_id}` - Cancel active session
- `GET /api/v1/assessment/stats/{learner_id}` - Get performance statistics

#### Health & Monitoring

- `GET /api/v1/health` - Basic health check
- `GET /api/v1/health/detailed` - Detailed system status
- `GET /api/v1/metrics` - Service performance metrics

## Architecture

### Database Models

- **AssessmentSession**: Session state with IRT parameters
- **QuestionBank**: Question repository with psychometric properties
- **AssessmentResponse**: Individual responses with timing data
- **AssessmentResult**: Final results with level mapping

### IRT Engine Components

- **IRTEngine**: Core psychometric calculations
- **LevelMapper**: Theta to proficiency level conversion
- **BaselineAssessmentEngine**: Assessment workflow management

### Event Integration

- **Event Emission**: Publishes BASELINE_COMPLETE events
- **Background Processing**: Asynchronous event handling
- **Metadata Enrichment**: Comprehensive result data

## Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Virtual environment

### Installation

```bash
cd services/assessment-svc
pip install -r requirements.txt
```

### Database Setup

```bash
# Configure database URL in environment
export DATABASE_URL="postgresql://user:pass@localhost/assessment_db"

# Run migrations (when available)
alembic upgrade head
```

### Run Service

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8003
```

### API Documentation

- Swagger UI: `http://localhost:8003/docs`
- ReDoc: `http://localhost:8003/redoc`

## Configuration

### Environment Variables

```bash
DATABASE_URL=postgresql://user:pass@localhost/assessment_db
EVENT_ENDPOINT_URL=http://localhost:8000/events
LOG_LEVEL=INFO
ENVIRONMENT=development
```

### IRT Configuration

- **Theta Range**: -4.0 to 4.0 (standardized scale)
- **Prior Distribution**: Normal(0, 1)
- **Termination SE**: 0.3 (standard error threshold)
- **Max Questions**: 30 per assessment
- **Min Questions**: 10 for reliability

### Level Thresholds

- **L0**: θ < -1.5 (Beginner)
- **L1**: -1.5 ≤ θ < -0.5 (Elementary)
- **L2**: -0.5 ≤ θ < 0.5 (Intermediate)
- **L3**: 0.5 ≤ θ < 1.5 (Advanced)
- **L4**: θ ≥ 1.5 (Expert)

## Testing

### Unit Tests

```bash
pytest tests/ -v --cov=app
```

### Integration Tests

```bash
pytest tests/integration/ -v
```

### Load Testing

```bash
# Using pytest-benchmark
pytest tests/performance/ -v --benchmark-only
```

## Development

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Monitoring

### Health Checks

- Basic: `/api/v1/health`
- Detailed: `/api/v1/health/detailed`
- Metrics: `/api/v1/metrics`

### Logging

Structured logging with correlation IDs for request tracing.

### Performance Metrics

- Assessment completion rates
- Average response times
- Question bank utilization
- Theta estimation accuracy

## Integration

### Event Publishing

The service publishes `BASELINE_COMPLETE` events with comprehensive assessment results:

```json
{
  "event_type": "BASELINE_COMPLETE",
  "learner_id": "learner_123",
  "tenant_id": "tenant_456",
  "subject": "mathematics",
  "proficiency_level": "L2",
  "final_theta": 0.25,
  "standard_error": 0.28,
  "accuracy_percentage": 72.5,
  "total_questions": 18,
  "correct_answers": 13,
  "session_id": "session_789",
  "completed_at": "2025-08-13T10:30:00Z",
  "metadata": {
    "reliability": 0.87,
    "level_confidence": 0.92,
    "strengths": ["algebra", "geometry"],
    "weaknesses": ["statistics", "calculus"],
    "recommendations": ["Focus on probability theory"]
  }
}
```

### Service Dependencies

- **Database**: PostgreSQL for persistence
- **Event Bus**: HTTP POST to event service
- **Authentication**: JWT validation (when integrated)

## Security

### Data Protection

- No PII storage in question responses
- Secure session management
- Input validation and sanitization

### API Security

- CORS configuration
- Request rate limiting (planned)
- Authentication middleware (planned)

## Performance

### Optimization

- Database connection pooling
- Async request handling
- Background task processing
- Response caching (planned)

### Scalability

- Stateless service design
- Horizontal scaling ready
- Database read replicas (planned)

## Troubleshooting

### Common Issues

1. **Database Connection**: Verify DATABASE_URL
2. **Question Bank Empty**: Load questions before assessments
3. **Event Publishing Fails**: Check EVENT_ENDPOINT_URL

### Debugging

- Enable DEBUG logging
- Check health endpoints
- Review database logs
- Monitor event publication

## License

Copyright (c) 2025 AIVO. All rights reserved.
