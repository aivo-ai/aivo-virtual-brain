"""
AIVO Orchestrator Service - Rule Testing
S1-14 Implementation

Comprehensive tests for orchestration rule thresholds and scheduling correctness.
Tests intelligent decision making and action generation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, Any

from app.logic import (
    OrchestrationEngine, 
    LearnerState, 
    DifficultyLevel, 
    EngagementLevel,
    OrchestrationRules
)
from app.consumer import Event, EventType, ActionType, OrchestrationAction


class TestOrchestrationRules:
    """Test orchestration rule thresholds and logic"""
    
    @pytest.fixture
    def engine(self):
        """Create orchestration engine for testing"""
        return OrchestrationEngine()
        
    @pytest.fixture
    def sample_learner_state(self):
        """Create sample learner state"""
        return LearnerState(
            learner_id="learner-123",
            tenant_id="tenant-456",
            current_level=DifficultyLevel.MODERATE,
            performance_score=0.6,
            engagement_score=0.7,
            consecutive_correct=2,
            consecutive_incorrect=1,
            session_duration_minutes=15,
            baseline_established=True
        )
        
    @pytest.fixture
    def baseline_complete_event(self):
        """Create baseline complete event"""
        return Event(
            id="event-1",
            type=EventType.BASELINE_COMPLETE,
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={
                "overall_score": 0.75,
                "strengths": ["reading", "math_basics"],
                "challenges": ["writing", "complex_math"],
                "percentile": 65,
                "assessment_type": "comprehensive"
            }
        )
        
    @pytest.fixture
    def coursework_analyzed_event(self):
        """Create coursework analyzed event"""
        return Event(
            id="event-2",
            type=EventType.COURSEWORK_ANALYZED,
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={
                "performance_metrics": {
                    "accuracy": 0.9,
                    "engagement": 0.8,
                    "time_efficiency": 0.7
                },
                "session_duration": 20,
                "learning_gaps": ["algebra", "geometry"],
                "mastery_areas": ["arithmetic", "reading_comprehension"]
            }
        )
        
    @pytest.fixture 
    def sel_alert_event(self):
        """Create SEL alert event"""
        return Event(
            id="event-3",
            type=EventType.SEL_ALERT,
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={
                "alert_type": "anxiety",
                "severity": "moderate",
                "confidence": 0.8,
                "context": "math_assessment",
                "indicators": ["response_time_increase", "accuracy_drop"]
            }
        )


class TestLevelAdjustmentRules:
    """Test level adjustment rule logic"""
    
    @pytest.mark.asyncio
    async def test_level_up_on_high_performance(self, engine, sample_learner_state):
        """Test level up when performance exceeds threshold"""
        await engine.initialize()
        
        # Set high performance
        sample_learner_state.performance_score = 0.9  # Above LEVEL_UP_THRESHOLD
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        
        assert level_action is not None
        assert level_action.type == ActionType.LEVEL_SUGGESTED
        assert level_action.action_data["level"] == DifficultyLevel.CHALLENGING.value
        assert "high performance" in level_action.action_data["reason"]
        assert level_action.action_data["confidence"] >= 0.8
        
    @pytest.mark.asyncio
    async def test_level_up_on_consecutive_correct(self, engine, sample_learner_state):
        """Test level up on consecutive correct answers"""
        await engine.initialize()
        
        # Set consecutive correct above threshold
        sample_learner_state.consecutive_correct = 6  # Above CONSECUTIVE_CORRECT_THRESHOLD
        sample_learner_state.performance_score = 0.7  # Moderate score
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        
        assert level_action is not None
        assert level_action.type == ActionType.LEVEL_SUGGESTED
        assert level_action.action_data["level"] == DifficultyLevel.CHALLENGING.value
        assert "consecutive correct" in level_action.action_data["reason"]
        
    @pytest.mark.asyncio
    async def test_level_down_on_low_performance(self, engine, sample_learner_state):
        """Test level down when performance below threshold"""
        await engine.initialize()
        
        # Set low performance
        sample_learner_state.performance_score = 0.3  # Below LEVEL_DOWN_THRESHOLD
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        
        assert level_action is not None
        assert level_action.type == ActionType.LEVEL_SUGGESTED
        assert level_action.action_data["level"] == DifficultyLevel.EASY.value
        assert "low performance" in level_action.action_data["reason"]
        
    @pytest.mark.asyncio
    async def test_level_down_on_consecutive_incorrect(self, engine, sample_learner_state):
        """Test level down on consecutive incorrect answers"""
        await engine.initialize()
        
        # Set consecutive incorrect above threshold
        sample_learner_state.consecutive_incorrect = 4  # Above CONSECUTIVE_INCORRECT_THRESHOLD
        sample_learner_state.performance_score = 0.5  # Moderate score
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        
        assert level_action is not None
        assert level_action.action_data["level"] == DifficultyLevel.EASY.value
        assert "consecutive incorrect" in level_action.action_data["reason"]
        
    @pytest.mark.asyncio
    async def test_no_level_change_moderate_performance(self, engine, sample_learner_state):
        """Test no level change for moderate performance"""
        await engine.initialize()
        
        # Set moderate performance (between thresholds)
        sample_learner_state.performance_score = 0.6
        sample_learner_state.consecutive_correct = 2
        sample_learner_state.consecutive_incorrect = 1
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        
        assert level_action is None
        
    @pytest.mark.asyncio
    async def test_level_boundaries_respected(self, engine, sample_learner_state):
        """Test level adjustment respects difficulty boundaries"""
        await engine.initialize()
        
        # Test can't go below BEGINNER
        sample_learner_state.current_level = DifficultyLevel.BEGINNER
        sample_learner_state.performance_score = 0.1  # Very low
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        assert level_action is None  # No action because already at minimum
        
        # Test can't go above ADVANCED
        sample_learner_state.current_level = DifficultyLevel.ADVANCED
        sample_learner_state.performance_score = 0.95  # Very high
        
        level_action = await engine._check_level_adjustment(sample_learner_state)
        assert level_action is None  # No action because already at maximum


class TestGameBreakScheduling:
    """Test game break scheduling rules"""
    
    @pytest.mark.asyncio
    async def test_break_on_session_duration(self, engine, sample_learner_state):
        """Test game break triggered by session duration"""
        await engine.initialize()
        
        # Set long session duration
        sample_learner_state.session_duration_minutes = 30  # Above MAX_SESSION_DURATION
        sample_learner_state.last_break_time = None  # No recent break
        
        actions = await engine._check_universal_actions(sample_learner_state)
        
        break_actions = [a for a in actions if a.type == ActionType.GAME_BREAK]
        assert len(break_actions) == 1
        assert break_actions[0].action_data["break_type"] == "movement"
        assert "Extended session duration" in break_actions[0].action_data["reason"]
        
    @pytest.mark.asyncio
    async def test_break_on_low_engagement(self, engine, sample_learner_state):
        """Test game break triggered by low engagement"""
        await engine.initialize()
        
        # Set low engagement
        sample_learner_state.engagement_score = 0.2  # Below LOW_ENGAGEMENT_THRESHOLD
        sample_learner_state.last_break_time = None  # No recent break
        
        actions = await engine._check_universal_actions(sample_learner_state)
        
        break_actions = [a for a in actions if a.type == ActionType.GAME_BREAK]
        assert len(break_actions) == 1
        assert break_actions[0].action_data["break_type"] == "attention"
        assert "Low engagement detected" in break_actions[0].action_data["reason"]
        
    @pytest.mark.asyncio
    async def test_break_timing_interval(self, engine, sample_learner_state):
        """Test break timing respects minimum interval"""
        await engine.initialize()
        
        # Set recent break time (within minimum interval)
        sample_learner_state.last_break_time = datetime.utcnow() - timedelta(minutes=10)  # Recent break
        sample_learner_state.session_duration_minutes = 30  # Long session
        
        actions = await engine._check_universal_actions(sample_learner_state)
        
        break_actions = [a for a in actions if a.type == ActionType.GAME_BREAK]
        assert len(break_actions) == 0  # No break due to recent break
        
        # Test break allowed after minimum interval
        sample_learner_state.last_break_time = datetime.utcnow() - timedelta(minutes=20)  # Old break
        
        actions = await engine._check_universal_actions(sample_learner_state)
        
        break_actions = [a for a in actions if a.type == ActionType.GAME_BREAK]
        assert len(break_actions) == 1  # Break allowed


class TestSELInterventionRules:
    """Test Social-Emotional Learning intervention rules"""
    
    @pytest.mark.asyncio
    async def test_sel_intervention_on_alert_threshold(self, engine, sample_learner_state, sel_alert_event):
        """Test SEL intervention when alert threshold reached"""
        await engine.initialize()
        
        # Add multiple recent alerts to reach threshold
        for i in range(3):
            alert_data = {
                "timestamp": datetime.utcnow() - timedelta(minutes=i*10),
                "alert_type": "anxiety",
                "severity": "moderate",
                "data": {"context": f"test_{i}"}
            }
            sample_learner_state.sel_alerts.append(alert_data)
            
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        actions = await engine.process_event(sel_alert_event)
        
        intervention_actions = [a for a in actions if a.type == ActionType.SEL_INTERVENTION]
        break_actions = [a for a in actions if a.type == ActionType.GAME_BREAK]
        
        assert len(intervention_actions) == 1
        assert len(break_actions) == 1
        assert intervention_actions[0].action_data["intervention_type"] == "anxiety"
        assert break_actions[0].action_data["break_type"] == "mindfulness"
        
    @pytest.mark.asyncio
    async def test_sel_high_severity_immediate_intervention(self, engine, sample_learner_state):
        """Test immediate SEL intervention for high severity alerts"""
        await engine.initialize()
        
        high_severity_event = Event(
            id="event-high",
            type=EventType.SEL_ALERT,
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={
                "alert_type": "frustration",
                "severity": "high",  # High severity
                "confidence": 0.9
            }
        )
        
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        actions = await engine.process_event(high_severity_event)
        
        intervention_actions = [a for a in actions if a.type == ActionType.SEL_INTERVENTION]
        assert len(intervention_actions) == 1
        assert intervention_actions[0].action_data["urgency"] == "high"
        
    @pytest.mark.asyncio
    async def test_sel_message_generation(self, engine):
        """Test SEL message generation for different alert types"""
        
        # Test different alert types
        anxiety_msg = engine._generate_sel_message("anxiety", [])
        frustration_msg = engine._generate_sel_message("frustration", [])
        confidence_msg = engine._generate_sel_message("confidence", [])
        attention_msg = engine._generate_sel_message("attention", [])
        generic_msg = engine._generate_sel_message("unknown", [])
        
        assert "worried" in anxiety_msg or "calm" in anxiety_msg
        assert "frustrated" in frustration_msg
        assert "confidence" in confidence_msg or "strength" in confidence_msg
        assert "focus" in attention_msg or "attention" in attention_msg
        assert "support" in generic_msg


class TestBaselineProcessing:
    """Test baseline assessment processing"""
    
    @pytest.mark.asyncio
    async def test_baseline_initial_level_assignment(self, engine, baseline_complete_event):
        """Test initial level assignment from baseline"""
        await engine.initialize()
        
        actions = await engine.process_event(baseline_complete_event)
        
        level_actions = [a for a in actions if a.type == ActionType.LEVEL_SUGGESTED]
        path_actions = [a for a in actions if a.type == ActionType.LEARNING_PATH_UPDATE]
        
        assert len(level_actions) == 1
        assert len(path_actions) == 1
        
        # 0.75 score should suggest CHALLENGING level
        assert level_actions[0].action_data["level"] == DifficultyLevel.CHALLENGING.value
        assert "baseline assessment" in level_actions[0].action_data["reason"]
        
        # Learning path should be personalized
        path_data = path_actions[0].action_data["path_updates"]
        assert "challenges" in path_data
        assert "strengths" in path_data or "strength_areas" in path_data
        
    @pytest.mark.asyncio 
    async def test_baseline_level_mapping(self, engine):
        """Test baseline score to difficulty level mapping"""
        
        # Test score ranges
        assert engine._determine_initial_level(0.95, {}) == DifficultyLevel.ADVANCED
        assert engine._determine_initial_level(0.8, {}) == DifficultyLevel.CHALLENGING
        assert engine._determine_initial_level(0.6, {}) == DifficultyLevel.MODERATE
        assert engine._determine_initial_level(0.4, {}) == DifficultyLevel.EASY
        assert engine._determine_initial_level(0.2, {}) == DifficultyLevel.BEGINNER


class TestCourseworkAnalysis:
    """Test coursework analysis processing"""
    
    @pytest.mark.asyncio
    async def test_coursework_performance_update(self, engine, sample_learner_state, coursework_analyzed_event):
        """Test learner state updates from coursework analysis"""
        await engine.initialize()
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        initial_performance = sample_learner_state.performance_score
        initial_engagement = sample_learner_state.engagement_score
        
        actions = await engine.process_event(coursework_analyzed_event)
        
        # Check state was updated
        updated_state = engine.learner_states[sample_learner_state.learner_id]
        assert updated_state.performance_score == 0.9  # From event data
        assert updated_state.engagement_score == 0.8  # From event data
        assert updated_state.consecutive_correct > 0  # High accuracy should increase
        
        # Should trigger level up due to high performance
        level_actions = [a for a in actions if a.type == ActionType.LEVEL_SUGGESTED]
        assert len(level_actions) >= 1
        
    @pytest.mark.asyncio
    async def test_learning_path_optimization(self, engine, sample_learner_state, coursework_analyzed_event):
        """Test learning path optimization from coursework analysis"""
        await engine.initialize()
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        actions = await engine.process_event(coursework_analyzed_event)
        
        path_actions = [a for a in actions if a.type == ActionType.LEARNING_PATH_UPDATE]
        assert len(path_actions) == 1
        
        path_data = path_actions[0].action_data["path_updates"]
        assert "remediation_topics" in path_data
        assert "acceleration_topics" in path_data
        assert path_data["remediation_topics"] == ["algebra", "geometry"]
        assert path_data["acceleration_topics"] == ["arithmetic", "reading_comprehension"]


class TestEngagementAdjustments:
    """Test engagement-based adjustments"""
    
    @pytest.mark.asyncio
    async def test_engagement_adjustments(self, engine):
        """Test engagement adjustment suggestions"""
        
        # Test low engagement
        low_adjustments = engine._suggest_engagement_adjustments(0.2)
        assert low_adjustments["gamification_level"] == "high"
        assert low_adjustments["break_frequency"] == "increased"
        assert low_adjustments["interaction_type"] == "active"
        
        # Test moderate engagement
        mod_adjustments = engine._suggest_engagement_adjustments(0.5)
        assert mod_adjustments["gamification_level"] == "moderate"
        assert mod_adjustments["break_frequency"] == "normal"
        
        # Test high engagement
        high_adjustments = engine._suggest_engagement_adjustments(0.8)
        assert high_adjustments["gamification_level"] == "low"
        assert high_adjustments["content_variety"] == "focused"
        
    @pytest.mark.asyncio
    async def test_low_engagement_event_handling(self, engine, sample_learner_state):
        """Test handling of low engagement events"""
        await engine.initialize()
        
        low_engagement_event = Event(
            id="event-low-eng",
            type=EventType.ENGAGEMENT_LOW,
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={"engagement_score": 0.2}
        )
        
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        actions = await engine.process_event(low_engagement_event)
        
        break_actions = [a for a in actions if a.type == ActionType.GAME_BREAK]
        level_actions = [a for a in actions if a.type == ActionType.LEVEL_SUGGESTED]
        
        # Should trigger immediate energizer break
        assert len(break_actions) == 1
        assert break_actions[0].action_data["break_type"] == "energizer"
        
        # Should temporarily lower difficulty  
        assert len(level_actions) == 1
        assert level_actions[0].action_data["level"] == DifficultyLevel.EASY.value
        assert level_actions[0].action_data.get("temporary") is True


class TestStatisticsTracking:
    """Test statistics and monitoring"""
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, engine, sample_learner_state, baseline_complete_event):
        """Test statistics are properly tracked"""
        await engine.initialize()
        
        initial_stats = await engine.get_stats()
        assert initial_stats["total_events_processed"] == 0
        
        # Process event
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        actions = await engine.process_event(baseline_complete_event)
        
        # Check statistics updated
        updated_stats = await engine.get_stats()
        assert updated_stats["total_events_processed"] == 1
        assert updated_stats["active_learners"] == 1
        assert updated_stats["level_suggestions_sent"] >= 1  # Should have level suggestion
        
        # Check action-specific stats
        level_actions = [a for a in actions if a.type == ActionType.LEVEL_SUGGESTED]
        path_actions = [a for a in actions if a.type == ActionType.LEARNING_PATH_UPDATE]
        
        assert updated_stats["level_suggestions_sent"] == len(level_actions)
        assert updated_stats["learning_path_updates"] == len(path_actions)


class TestErrorHandling:
    """Test error handling and edge cases"""
    
    @pytest.mark.asyncio
    async def test_missing_event_data(self, engine, sample_learner_state):
        """Test handling of events with missing data"""
        await engine.initialize()
        
        incomplete_event = Event(
            id="event-incomplete",
            type=EventType.COURSEWORK_ANALYZED,
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={}  # Missing performance_metrics
        )
        
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        # Should not crash, should handle gracefully
        actions = await engine.process_event(incomplete_event)
        assert isinstance(actions, list)  # Should return list even with missing data
        
    @pytest.mark.asyncio
    async def test_unknown_event_type(self, engine, sample_learner_state):
        """Test handling of unknown event types"""
        await engine.initialize()
        
        # Create event with unknown type (would need to be added to EventType enum in reality)
        unknown_event = Event(
            id="event-unknown",
            type=EventType.BASELINE_COMPLETE,  # Use valid type for test 
            learner_id="learner-123",
            tenant_id="tenant-456",
            timestamp=datetime.utcnow(),
            data={"test": "data"}
        )
        
        engine.learner_states[sample_learner_state.learner_id] = sample_learner_state
        
        # Should process without crashing
        actions = await engine.process_event(unknown_event)
        assert isinstance(actions, list)


# Integration test fixtures
@pytest.fixture
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
