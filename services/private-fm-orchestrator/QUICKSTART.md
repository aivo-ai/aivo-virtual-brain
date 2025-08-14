# Private Foundation Model Orchestrator

## Quick Start

### Development Setup

1. **Install Python dependencies**:

   ```bash
   pip install -e .
   ```

2. **Set up environment variables**:

   ```bash
   export DATABASE_URL="postgresql+asyncpg://user:password@localhost/private_fm"
   export REDIS_URL="redis://localhost:6379/0"
   ```

3. **Run database migrations**:

   ```bash
   alembic upgrade head
   ```

4. **Start the development server**:
   ```bash
   python -m uvicorn app.main:app --reload
   ```

### Docker Development

```bash
docker-compose up --build
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_isolation_merge.py -v
```

## API Documentation

Once running, visit:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics

## Key Features

✅ **Per-learner namespace isolation** - Each learner gets an isolated AI model namespace
✅ **Nightly merge operations** - Automated foundation model synchronization  
✅ **Fallback recovery** - Automatic corruption detection and recovery
✅ **Event-driven architecture** - Comprehensive audit logging and event streaming
✅ **Guardian deletion policies** - Time-delayed deletion protection
✅ **Health monitoring** - Continuous namespace integrity checks
✅ **Prometheus metrics** - Production-ready observability
✅ **Async/await architecture** - High-performance async processing

## Service Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Namespace      │    │   Background    │
│   (REST API)    │◄──►│  Isolator       │◄──►│   Jobs          │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Redis       │    │   Event Bus     │
│   (Database)    │    │   (Cache/Queue) │    │  (Publishing)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Project Structure

```
services/private-fm-orchestrator/
├── app/
│   ├── main.py           # FastAPI application
│   ├── models.py         # SQLAlchemy models
│   ├── isolator.py       # Core namespace isolation logic
│   ├── routes.py         # API endpoints
│   └── cron.py           # Scheduled jobs
├── tests/
│   ├── conftest.py       # Test configuration
│   ├── test_api.py       # API integration tests
│   └── test_isolation_merge.py  # Core functionality tests
├── migrations/           # Database migrations
├── pyproject.toml        # Package configuration
└── README.md
```
