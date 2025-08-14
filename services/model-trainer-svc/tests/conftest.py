"""
Test configuration and fixtures for Model Trainer Service
"""

import asyncio
import os
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app


# Set test environment
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = settings.test_database_url

# Create test database engine
test_engine = create_async_engine(
    settings.test_database_url.replace("postgresql://", "postgresql+asyncpg://"),
    poolclass=StaticPool,
    echo=False,
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a test database session"""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestSessionLocal() as session:
        yield session
    
    # Drop tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session):
    """Create a test HTTP client"""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_training_job_data():
    """Sample training job data for testing"""
    return {
        "name": "test-fine-tune-job",
        "description": "Test fine-tuning job",
        "provider": "openai",
        "base_model": "gpt-3.5-turbo",
        "dataset_uri": "s3://test-bucket/training-data.jsonl",
        "config": {
            "n_epochs": 3,
            "batch_size": 1,
            "learning_rate_multiplier": 0.1
        },
        "policy": {
            "scope": "tenant_test",
            "thresholds": {
                "pedagogy_score": 0.8,
                "safety_score": 0.9
            }
        },
        "datasheet": {
            "source": "test_curriculum",
            "license": "proprietary",
            "redaction": "pii_removed",
            "description": "Test dataset for fine-tuning"
        }
    }


@pytest.fixture
def sample_evaluation_data():
    """Sample evaluation data for testing"""
    return {
        "name": "test-evaluation",
        "description": "Test evaluation run",
        "harness_config": {
            "pedagogy_tests": ["curriculum_alignment", "learning_objectives"],
            "safety_tests": ["harmful_content", "bias_detection"],
            "timeout": 300,
            "parallel": True
        },
        "thresholds": {
            "pedagogy_score": 0.8,
            "safety_score": 0.9,
            "overall_score": 0.85
        }
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API responses"""
    return {
        "fine_tune_job": {
            "id": "ft-job-test-123",
            "object": "fine_tuning.job",
            "model": "gpt-3.5-turbo",
            "created_at": 1692661014,
            "fine_tuned_model": None,
            "hyperparameters": {
                "n_epochs": 3,
                "batch_size": 1,
                "learning_rate_multiplier": 0.1
            },
            "status": "running",
            "trained_tokens": None,
            "training_file": "file-test-123"
        },
        "completed_job": {
            "id": "ft-job-test-123",
            "object": "fine_tuning.job",
            "model": "gpt-3.5-turbo",
            "created_at": 1692661014,
            "fine_tuned_model": "ft:gpt-3.5-turbo-test:aivo:test:123",
            "hyperparameters": {
                "n_epochs": 3,
                "batch_size": 1,
                "learning_rate_multiplier": 0.1
            },
            "status": "succeeded",
            "trained_tokens": 15000,
            "training_file": "file-test-123"
        },
        "training_file": {
            "id": "file-test-123",
            "object": "file",
            "bytes": 120000,
            "created_at": 1692661014,
            "filename": "training_data.jsonl",
            "purpose": "fine-tune"
        }
    }


class MockOpenAIClient:
    """Mock OpenAI client for testing"""
    
    def __init__(self, responses):
        self.responses = responses
        self.fine_tuning = MockFineTuning(responses)
        self.files = MockFiles(responses)


class MockFineTuning:
    def __init__(self, responses):
        self.responses = responses
        self.jobs = MockJobs(responses)


class MockJobs:
    def __init__(self, responses):
        self.responses = responses
    
    async def create(self, **kwargs):
        return MockResponse(self.responses["fine_tune_job"])
    
    async def retrieve(self, job_id):
        if "completed" in job_id or job_id.endswith("completed"):
            return MockResponse(self.responses["completed_job"])
        return MockResponse(self.responses["fine_tune_job"])
    
    async def cancel(self, job_id):
        cancelled_job = self.responses["fine_tune_job"].copy()
        cancelled_job["status"] = "cancelled"
        return MockResponse(cancelled_job)


class MockFiles:
    def __init__(self, responses):
        self.responses = responses
    
    async def create(self, **kwargs):
        return MockResponse(self.responses["training_file"])


class MockResponse:
    def __init__(self, data):
        self._data = data
        for key, value in data.items():
            setattr(self, key, value)
    
    def dict(self):
        return self._data
