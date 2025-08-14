# AIVO SEL Service (S2-12)

## Social-Emotional Learning Service with Check-ins, Strategies, and Consent-Aware Alerts

The AIVO SEL Service provides comprehensive social-emotional learning support through:

- **Student Check-ins**: Emotional assessment and contextual data collection
- **Strategy Generation**: Personalized SEL interventions tailored to grade bands
- **Alert System**: Consent-aware threshold-based notifications
- **Privacy Compliance**: FERPA-compliant consent management and data protection

## Features

### 🎯 Core Functionality

- **POST /checkin** - Create SEL check-ins with emotional assessment
- **GET /strategy/next** - Generate personalized strategies based on current state
- **POST /report** - Create comprehensive SEL reports with privacy controls
- **Consent Management** - FERPA-compliant consent verification for all operations

### 🔒 Privacy & Compliance

- **Consent-Aware Alerts** - Only generate alerts when explicitly consented
- **Privacy Levels** - Configurable data sharing and retention policies
- **FERPA Compliance** - Parent/guardian consent with student assent validation
- **Audit Trails** - Comprehensive logging for compliance monitoring

### 🎨 Grade Band Adaptation

- **Early Elementary** (K-2): Visual supports, interactive elements, 5-10 min activities
- **Late Elementary** (3-5): Visual supports, moderate complexity, 10-15 min activities
- **Middle School** (6-8): Text-based strategies, higher complexity, 15-20 min activities
- **High School** (9-12): Advanced strategies, self-directed learning, 20-30 min activities
- **Adult**: Professional development focused, 25-45 min activities

## API Endpoints

### Check-in Endpoints

```http
POST /api/v1/checkin
GET /api/v1/checkin?student_id={id}&tenant_id={id}
```

### Strategy Endpoints

```http
GET /api/v1/strategy/next?student_id={id}&tenant_id={id}
POST /api/v1/strategy/{id}/usage
```

### Report Endpoints

```http
POST /api/v1/report
```

### Alert Endpoints

```http
GET /api/v1/alerts?tenant_id={id}&student_id={id}
PATCH /api/v1/alerts/{id}/acknowledge
```

### Consent Management

```http
POST /api/v1/consent
GET /api/v1/consent/{student_id}
```

## Data Models

### SEL Check-in

- Emotional state assessment (primary/secondary emotions, intensity)
- SEL domain ratings (self-awareness, self-management, social awareness, relationship skills, decision-making)
- Contextual information (location, social context, triggers)
- Wellness indicators (energy, stress, confidence levels)
- Support needs and notes

### SEL Strategy

- Personalized interventions based on check-in data
- Grade-band appropriate content and complexity
- Step-by-step instructions with success indicators
- Multimedia resources (video, audio, images)
- Effectiveness tracking and optimization

### Consent Management

- Comprehensive consent types (data collection, sharing, alerts, AI processing)
- Parent/guardian consent with student assent
- Expiration dates and withdrawal options
- Custom alert thresholds and privacy preferences
- FERPA compliance validation

## Alert System

### Threshold-Based Alerts

The SEL service generates alerts when:

- SEL domain ratings fall below configured thresholds
- High emotional intensity with negative emotions persists
- Multiple risk factors are detected simultaneously
- Students frequently request support

### Alert Types

- **Domain Threshold Exceeded**: Low ratings in SEL domains
- **Risk Factors Detected**: Multiple concerning indicators
- **Support Requested**: Student explicitly asks for help
- **Pattern Alerts**: Concerning trends over time

### Consent-Aware Processing

All alerts respect consent preferences:

- Only generate alerts when notifications are consented
- Respect custom threshold settings
- Honor privacy levels and data sharing preferences
- Maintain audit trails for compliance

## Installation & Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 13+
- Docker (optional)

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd services/sel-svc

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/sel_db
export ENVIRONMENT=development

# Initialize database
python -c "from app.database import init_database; import asyncio; asyncio.run(init_database())"

# Run the service
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Docker Deployment

```bash
# Build image
docker build -t aivo-sel-svc .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/sel_db \
  -e ENVIRONMENT=production \
  aivo-sel-svc
```

### Using Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs sel-svc
```

## Environment Variables

| Variable       | Description                  | Default                                                           |
| -------------- | ---------------------------- | ----------------------------------------------------------------- |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://aivo_sel:sel_secure_pass@postgres:5432/aivo_sel_db` |
| `ENVIRONMENT`  | Deployment environment       | `development`                                                     |
| `SQL_ECHO`     | Enable SQL query logging     | `false`                                                           |

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test suite
pytest tests/test_sel_flow.py -v

# Run with coverage
pytest --cov=app tests/
```

### Test Coverage

- ✅ Check-in creation and retrieval
- ✅ Strategy generation and usage tracking
- ✅ Alert system with threshold testing
- ✅ Report generation with privacy controls
- ✅ Consent management and FERPA compliance
- ✅ Complete workflow integration testing

## Configuration

### Alert Thresholds

Default SEL domain thresholds (1-10 scale):

```python
thresholds = {
    "self_awareness": {"low": 3, "medium": 2, "high": 1},
    "self_management": {"low": 3, "medium": 2, "high": 1},
    "social_awareness": {"low": 3, "medium": 2, "high": 1},
    "relationship_skills": {"low": 3, "medium": 2, "high": 1},
    "responsible_decision_making": {"low": 3, "medium": 2, "high": 1}
}
```

### Grade Band Settings

Each grade band has tailored strategy parameters:

- **Duration**: Age-appropriate activity lengths
- **Complexity**: Cognitive demand level (1-5)
- **Visual Supports**: Images and interactive elements
- **Language**: Vocabulary and instruction complexity

## Integration

### Orchestrator Events

The SEL service publishes events to the AIVO orchestrator:

- `SEL_ALERT` - When alert thresholds are exceeded
- `SEL_CHECKIN_COMPLETED` - After successful check-in processing
- `SEL_STRATEGY_COMPLETED` - When students complete strategies

### Inference Gateway

AI-powered features integrate with the inference gateway:

- Strategy personalization using GPT-4
- Check-in analysis and insights
- Risk pattern recognition
- Recommendation generation

## Privacy & Security

### FERPA Compliance

- **Consent Management**: Explicit consent for data collection, sharing, and processing
- **Parent Authorization**: Required for students under 18
- **Student Assent**: Age-appropriate agreement for older students
- **Data Minimization**: Only collect necessary information
- **Retention Policies**: Automated cleanup of expired data

### Security Measures

- JWT-based authentication
- Role-based access control
- Audit logging for all data access
- Encrypted data transmission
- Secure database connections

### Privacy Controls

- Configurable privacy levels (public, internal, confidential, restricted)
- Custom data sharing preferences
- Granular consent management
- Right to withdraw consent
- Data export and deletion capabilities

## Monitoring & Observability

### Health Checks

- `/health` - Basic service health
- `/health/detailed` - Component health (database, engine, dependencies)

### Metrics

- Check-in completion rates
- Strategy effectiveness scores
- Alert generation frequency
- Consent compliance metrics
- API response times and error rates

### Logging

- Structured JSON logging
- Request/response auditing
- Privacy-compliant event logging
- Error tracking and alerting

## Development

### Code Structure

```
services/sel-svc/
├── app/
│   ├── __init__.py          # Package initialization
│   ├── main.py              # FastAPI application
│   ├── models.py            # SQLAlchemy data models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── routes.py            # API route handlers
│   ├── engine.py            # SEL business logic engine
│   ├── auth.py              # Authentication and consent
│   └── database.py          # Database configuration
├── tests/
│   └── test_sel_flow.py     # Comprehensive test suite
├── migrations/              # Database migrations
├── requirements.txt         # Python dependencies
├── Dockerfile              # Container configuration
└── README.md               # This documentation
```

### Contributing

1. Follow PEP 8 style guidelines
2. Add comprehensive tests for new features
3. Update documentation for API changes
4. Ensure FERPA compliance for data handling
5. Validate consent requirements for new operations

## Support

For questions or issues:

1. Check the test suite for usage examples
2. Review the API documentation at `/docs`
3. Examine logs for debugging information
4. Contact the AIVO development team

---

**S2-12 Implementation**: Complete social-emotional learning service with check-ins, strategy engine, and consent-aware alerts. Ready for integration with the AIVO orchestrator and inference gateway.
