"""
AIVO Model Registry - Test Configuration
S2-02 Implementation: Pytest configuration and fixtures
"""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["POSTGRES_DB"] = "test_model_registry"

from app.database import get_db_session, Base
from app.main import app
from app.service import get_model_registry_service

# Test database URL
TEST_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/test_model_registry"

# Create test engine
test_engine = create_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Override the dependency
app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(scope="session")
def setup_test_database():
    """Create test database tables before all tests"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session(setup_test_database):
    """Create a fresh database session for each test"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(setup_test_database):
    """Create a test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_model_data():
    """Sample model data for testing"""
    return {
        "name": "test-llm-model",
        "task": "generation",
        "subject": "general",
        "description": "Test LLM model for generation tasks"
    }


@pytest.fixture
def sample_version_data():
    """Sample version data for testing"""
    return {
        "model_id": 1,
        "hash": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd",
        "version": "1.0.0",
        "region": "us-east-1",
        "cost_per_1k": 0.002,
        "eval_score": 0.85,
        "slo_ok": True,
        "artifact_uri": "s3://models/test-llm/v1.0.0/model.bin",
        "size_bytes": 1024000000,
        "model_type": "transformer",
        "framework": "pytorch"
    }


@pytest.fixture
def sample_binding_data():
    """Sample provider binding data for testing"""
    return {
        "version_id": 1,
        "provider": "openai",
        "provider_model_id": "gpt-4-turbo-preview",
        "status": "active",
        "config": {"temperature": 0.7, "max_tokens": 1000},
        "endpoint_url": "https://api.openai.com/v1/chat/completions"
    }
