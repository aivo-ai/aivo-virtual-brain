"""
AIVO Orchestrator Service - Basic Tests
S1-14 Implementation

Basic test setup and sanity checks.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

# Simple test to verify import and basic functionality
def test_imports():
    """Test that core modules import correctly"""
    try:
        from app.consumer import EventConsumer, Event, EventType, ActionType
        from app.logic import OrchestrationEngine, DifficultyLevel
        from app.main import app
        assert True, "All imports successful"
    except ImportError as e:
        pytest.fail(f"Import failed: {e}")

@pytest.mark.asyncio
async def test_engine_initialization():
    """Test orchestration engine initialization"""
    from app.logic import OrchestrationEngine
    
    engine = OrchestrationEngine()
    assert not engine.is_initialized
    
    await engine.initialize()
    assert engine.is_initialized

def test_event_types():
    """Test event type definitions"""
    from app.consumer import EventType, ActionType
    
    # Check required event types
    assert EventType.BASELINE_COMPLETE == "BASELINE_COMPLETE"
    assert EventType.SLP_UPDATED == "SLP_UPDATED" 
    assert EventType.SEL_ALERT == "SEL_ALERT"
    assert EventType.COURSEWORK_ANALYZED == "COURSEWORK_ANALYZED"
    
    # Check action types
    assert ActionType.LEVEL_SUGGESTED == "LEVEL_SUGGESTED"
    assert ActionType.GAME_BREAK == "GAME_BREAK"

def test_difficulty_levels():
    """Test difficulty level definitions"""
    from app.logic import DifficultyLevel
    
    levels = list(DifficultyLevel)
    assert len(levels) == 5
    assert DifficultyLevel.BEGINNER in levels
    assert DifficultyLevel.ADVANCED in levels

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
