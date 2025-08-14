# AIVO Speech & Language Pathology (SLP) Service

## S2-11 Implementation

Comprehensive SLP service providing screening assessments, therapy planning, exercise generation, and session management with AI-powered content generation and voice integration capabilities.

## Features

- **🔍 Screening Assessments** - Multi-domain speech and language evaluations
- **📋 Therapy Planning** - AI-generated individualized treatment plans
- **🎯 Exercise Generation** - Adaptive therapy exercises with voice integration
- **📊 Session Management** - Progress tracking and outcome analytics
- **🧠 AI Integration** - Inference gateway for intelligent content generation
- **🎤 Voice Analysis** - ASR/TTS integration for speech processing
- **📈 Event System** - Real-time progress tracking and milestone alerts

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Screening     │    │  Therapy Plan    │    │   Exercise      │
│   Assessment    ├───►│    Generation    ├───►│   Generation    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                    ┌─────────────────────────┐
                    │   Session Management    │
                    │   & Progress Tracking   │
                    └─────────────────────────┘
```

## Workflow

1. **Screening**: Patient undergoes comprehensive assessment across multiple SLP domains
2. **Analysis**: AI processes results to identify areas of need and risk factors
3. **Planning**: Therapy plan generated with specific goals, objectives, and exercise sequences
4. **Exercise Generation**: AI creates adaptive exercises based on patient needs and progress
5. **Session Execution**: Exercises are completed with voice analysis and performance tracking
6. **Progress Tracking**: Continuous monitoring of outcomes and plan adjustments

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 12+
- Docker (optional)

### Development Setup

```bash
# Clone repository (if not already)
cd services/slp-svc

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql://aivo:aivo123@localhost:5432/aivo_slp"
export INFERENCE_GATEWAY_URL="http://localhost:8001"

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Docker Setup

```bash
# Build image
docker build -t aivo-slp-svc .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://aivo:aivo123@host.docker.internal:5432/aivo_slp" \
  -e INFERENCE_GATEWAY_URL="http://host.docker.internal:8001" \
  aivo-slp-svc
```

## API Endpoints

### Core Workflow

| Endpoint                     | Method | Description                 |
| ---------------------------- | ------ | --------------------------- |
| `/api/v1/slp/screen`         | POST   | Create screening assessment |
| `/api/v1/slp/plan`           | POST   | Generate therapy plan       |
| `/api/v1/slp/exercise/next`  | POST   | Generate next exercise      |
| `/api/v1/slp/session/submit` | POST   | Submit session results      |

### Resource Management

| Endpoint                    | Method | Description              |
| --------------------------- | ------ | ------------------------ |
| `/api/v1/slp/screen/{id}`   | GET    | Get screening details    |
| `/api/v1/slp/plan/{id}`     | GET    | Get therapy plan details |
| `/api/v1/slp/exercise/{id}` | GET    | Get exercise details     |
| `/api/v1/slp/session/{id}`  | GET    | Get session details      |

### Progress & Analytics

| Endpoint                            | Method | Description         |
| ----------------------------------- | ------ | ------------------- |
| `/api/v1/slp/progress/{patient_id}` | GET    | Get progress events |

## Usage Examples

### 1. Create Screening Assessment

```bash
curl -X POST "http://localhost:8000/api/v1/slp/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "patient_id": "patient_123",
    "patient_name": "John Doe",
    "patient_age": 6,
    "date_of_birth": "2017-05-15",
    "assessment_type": "comprehensive",
    "assessment_data": {
      "articulation_tasks": [
        {"word": "cat", "phoneme": "/k/", "accuracy": 0.85, "attempts": 3}
      ],
      "language_comprehension": [
        {"instruction": "Point to the red ball", "correct": true, "response_time": 2.1}
      ],
      "voice_sample": {
        "recording_url": "https://example.com/voice/sample1.wav",
        "duration": 15.3
      }
    }
  }'
```

### 2. Generate Therapy Plan

```bash
curl -X POST "http://localhost:8000/api/v1/slp/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "screening_id": "660e8400-e29b-41d4-a716-446655440001",
    "plan_name": "Johns Articulation Plan",
    "priority_level": "medium",
    "sessions_per_week": 2,
    "session_duration": 30
  }'
```

### 3. Generate Exercise

```bash
curl -X POST "http://localhost:8000/api/v1/slp/exercise/next" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "therapy_plan_id": "770e8400-e29b-41d4-a716-446655440002",
    "exercise_type": "articulation_drill",
    "difficulty_preference": "adaptive"
  }'
```

### 4. Submit Session Results

```bash
curl -X POST "http://localhost:8000/api/v1/slp/session/submit" \
  -H "Content-Type: application/json" \
  -d '{
    "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
    "session_id": "880e8400-e29b-41d4-a716-446655440003",
    "exercise_results": [
      {
        "exercise_id": "990e8400-e29b-41d4-a716-446655440004",
        "completed": true,
        "accuracy_score": 0.85,
        "time_spent": 5,
        "attempts": 3
      }
    ],
    "actual_duration": 28,
    "session_notes": "Good progress on articulation",
    "audio_recordings": ["recording1.wav"]
  }'
```

## Data Models

### Core Entities

- **ScreeningAssessment**: Multi-domain speech/language evaluation results
- **TherapyPlan**: Individualized treatment plan with goals and objectives
- **ExerciseInstance**: AI-generated therapy exercise with voice integration
- **ExerciseSession**: Session tracking with performance analytics
- **ProgressEvent**: Milestone and progress tracking events

### Assessment Domains

- **Articulation**: Speech sound production accuracy
- **Language**: Comprehension and expression capabilities
- **Voice**: Vocal quality, pitch, and resonance analysis
- **Fluency**: Speech flow and rhythm assessment
- **Pragmatics**: Social communication skills evaluation

## AI Integration

### Inference Gateway

The service integrates with the inference gateway for:

- Content generation based on assessment results
- Exercise creation tailored to patient needs
- Progress analysis and recommendations
- Voice sample processing and analysis

### AI-Powered Features

- **Smart Assessment**: Automated analysis of screening results
- **Adaptive Content**: Exercises that adjust to patient performance
- **Predictive Analytics**: Progress forecasting and outcome prediction
- **Voice Analysis**: Real-time speech quality assessment

## Voice Integration

### ASR (Automatic Speech Recognition)

- Real-time speech-to-text conversion
- Pronunciation accuracy analysis
- Phoneme-level feedback
- Fluency metrics calculation

### TTS (Text-to-Speech)

- Exercise instruction delivery
- Model pronunciation examples
- Interactive feedback systems
- Multi-voice support

## Testing

```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/test_slp_flow.py -v

# Run with coverage
pytest --cov=app tests/

# Run integration tests
pytest tests/ -m integration
```

## Database Schema

The service uses PostgreSQL with the following key tables:

- `screening_assessments` - Patient evaluation data
- `therapy_plans` - Treatment planning and goals
- `exercise_instances` - Generated therapy exercises
- `exercise_sessions` - Session tracking and results
- `progress_events` - Milestone and progress events

## Configuration

### Environment Variables

| Variable                | Description                  | Default                                             |
| ----------------------- | ---------------------------- | --------------------------------------------------- |
| `DATABASE_URL`          | PostgreSQL connection string | `postgresql://aivo:aivo123@localhost:5432/aivo_slp` |
| `INFERENCE_GATEWAY_URL` | AI inference service URL     | `http://localhost:8001`                             |
| `ASR_PROVIDER_URL`      | Speech recognition service   | `http://localhost:8002`                             |
| `TTS_PROVIDER_URL`      | Text-to-speech service       | `http://localhost:8003`                             |
| `LOG_LEVEL`             | Logging level                | `INFO`                                              |
| `SQL_ECHO`              | Enable SQL query logging     | `false`                                             |

## Performance

### Optimization Features

- Connection pooling for database efficiency
- Background processing for long-running operations
- Caching for frequently accessed data
- Async operations for better concurrency

### Monitoring

- Health check endpoints
- Metrics collection
- Request/response logging
- Performance tracking

## Security

- Input validation with Pydantic schemas
- SQL injection prevention via SQLAlchemy
- Request ID tracking for audit trails
- Error handling without information leakage

## Development

### Project Structure

```
services/slp-svc/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application
│   ├── routes.py        # API endpoints
│   ├── models.py        # SQLAlchemy models
│   ├── schemas.py       # Pydantic schemas
│   ├── engine.py        # SLP business logic
│   └── database.py      # Database configuration
├── tests/
│   └── test_slp_flow.py # Comprehensive tests
├── migrations/          # Alembic migrations
├── requirements.txt     # Dependencies
├── Dockerfile          # Container configuration
└── README.md           # This file
```

### Code Quality

- Type hints throughout codebase
- Comprehensive test coverage
- Consistent error handling
- Structured logging
- API documentation

## Deployment

### Production Checklist

- [ ] Configure production database
- [ ] Set environment variables
- [ ] Run database migrations
- [ ] Configure load balancer
- [ ] Set up monitoring
- [ ] Configure logging
- [ ] Test health endpoints

### Scaling Considerations

- Horizontal scaling via load balancer
- Database connection pooling
- Background task queues
- Caching layer implementation
- Content delivery network for audio files

## Support

For technical support or questions:

- Development Team: dev@aivo.com
- Documentation: `/docs` endpoint
- API Reference: `/redoc` endpoint
- Health Status: `/health` endpoint

## License

Proprietary - AIVO Technologies
