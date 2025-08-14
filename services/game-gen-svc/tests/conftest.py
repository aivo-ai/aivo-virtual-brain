# AIVO Game Generation Service - Test Configuration
# S2-13 Implementation - pytest configuration and test runner

import pytest
import asyncio
import os
import sys
from typing import Generator
from unittest.mock import Mock

# Add app directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_database():
    """Mock database session for testing."""
    db = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    db.query = Mock()
    db.execute = Mock(return_value=Mock(scalar=Mock(return_value="PostgreSQL 15.0")))
    return db

# Test configuration
pytest_plugins = ["pytest_asyncio"]

# Configure asyncio mode
asyncio_mode = "auto"

# Test markers
markers = [
    "asyncio: mark test as async",
    "slow: mark test as slow running",
    "integration: mark test as integration test",
    "unit: mark test as unit test"
]
