"""
Test configuration and fixtures for Private Foundation Model Orchestrator.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis

from app.main import app
from app.models import Base
from app.isolator import NamespaceIsolator


# Test configuration
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_REDIS_URL = "redis://localhost:6379/1"  # Use different DB for tests


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    await engine.dispose()


@pytest_asyncio.fixture
async def test_db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(test_engine, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest_asyncio.fixture
async def test_redis() -> AsyncGenerator[redis.Redis, None]:
    """Create test Redis client."""
    redis_client = redis.from_url(TEST_REDIS_URL)
    
    # Clear test database
    await redis_client.flushdb()
    
    yield redis_client
    
    # Cleanup
    await redis_client.flushdb()
    await redis_client.close()


@pytest_asyncio.fixture
async def test_isolator(test_db_session, test_redis) -> NamespaceIsolator:
    """Create test namespace isolator."""
    return NamespaceIsolator(test_db_session, test_redis)


@pytest.fixture
def test_client() -> TestClient:
    """Create test FastAPI client."""
    return TestClient(app)


@pytest.fixture
def sample_learner_id() -> UUID:
    """Generate a sample learner ID for testing."""
    return uuid4()


@pytest.fixture
def sample_namespace_data() -> dict:
    """Sample namespace creation data."""
    return {
        "learner_id": str(uuid4()),
        "base_fm_version": "1.0",
        "initial_prompt": "You are a helpful assistant.",
        "configuration": {
            "max_tokens": 1000,
            "temperature": 0.7
        }
    }


# Mock fixtures for external dependencies

@pytest.fixture
def mock_provider_client():
    """Mock AI provider client."""
    mock = AsyncMock()
    mock.generate.return_value = {
        "text": "Generated response",
        "token_count": 10,
        "model": "test-model"
    }
    mock.health_check.return_value = {"status": "healthy"}
    return mock


@pytest.fixture
def mock_event_bus():
    """Mock event bus for testing."""
    mock = AsyncMock()
    mock.publish.return_value = True
    mock.subscribe.return_value = AsyncMock()
    return mock


# Helper functions for tests

def create_test_namespace_data(learner_id: UUID = None, **kwargs) -> dict:
    """Create test namespace data with optional overrides."""
    data = {
        "learner_id": str(learner_id or uuid4()),
        "base_fm_version": "1.0",
        "initial_prompt": "Test prompt",
        "configuration": {"test": True}
    }
    data.update(kwargs)
    return data


def create_test_merge_request(**kwargs) -> dict:
    """Create test merge request with optional overrides."""
    data = {
        "operation_type": "manual",
        "force": False
    }
    data.update(kwargs)
    return data


def create_test_fallback_request(**kwargs) -> dict:
    """Create test fallback request with optional overrides."""
    data = {
        "reason": "corruption_detected",
        "target_fm_version": "1.0"
    }
    data.update(kwargs)
    return data


# Test environment setup
def setup_test_environment():
    """Setup test environment variables."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["REDIS_URL"] = TEST_REDIS_URL
    os.environ["NIGHTLY_MERGE_ENABLED"] = "false"
    os.environ["CLEANUP_ENABLED"] = "false"
    os.environ["HEALTH_CHECK_ENABLED"] = "false"
    os.environ["ENABLE_MERGE_PROCESSOR"] = "false"
    os.environ["ENABLE_FALLBACK_PROCESSOR"] = "false"
    os.environ["ENABLE_METRICS"] = "false"


# Call setup when module is imported
setup_test_environment()
