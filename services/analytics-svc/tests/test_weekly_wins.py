"""
Tests for Weekly Wins Digest Generator (S5-07)
"""
import pytest
import asyncio
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4
from decimal import Decimal

from services.analytics_svc.app.digests.weekly_wins import WeeklyWinsGenerator
from services.analytics_svc.app.models import (
    SessionAggregate, MasteryAggregate, GoalProgress,
    SLPStreaks, SELProgress, AggregationLevel
)

class TestWeeklyWinsGenerator:
    """Test cases for Weekly Wins digest generation."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()
    
    @pytest.fixture
    def generator(self, mock_db_session):
        """Create WeeklyWinsGenerator instance."""
        return WeeklyWinsGenerator(mock_db_session)
    
    @pytest.fixture
    def sample_learner_id(self):
        """Sample learner UUID."""
        return uuid4()
    
    @pytest.fixture
    def sample_tenant_id(self):
        """Sample tenant UUID."""
        return uuid4()
    
    @pytest.mark.asyncio
    async def test_generate_weekly_wins_basic(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test basic weekly wins generation."""
        # Mock database queries
        mock_db_session.query.return_value.filter.return_value.first.return_value = Mock(
            total_minutes=120,
            session_count=5,
            avg_session_minutes=24
        )
        
        # Generate wins
        result = await generator.generate_weekly_wins(
            learner_id=sample_learner_id,
            tenant_id=sample_tenant_id,
            user_timezone="America/New_York",
            locale="en",
            grade_band="elementary"
        )
        
        # Assertions
        assert result is not None
        assert "learner_id" in result
        assert "minutes_learned" in result
        assert "subjects_advanced" in result
        assert "completed_goals" in result
        assert "slp_streaks" in result
        assert "sel_progress" in result
        assert "celebration_highlight" in result
        assert result["locale"] == "en"
        assert result["grade_band"] == "elementary"
    
    @pytest.mark.asyncio
    async def test_get_minutes_learned_success(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test minutes learned calculation."""
        # Mock query result
        mock_result = Mock()
        mock_result.total_minutes = 150.0
        mock_result.session_count = 6
        mock_result.avg_session_minutes = 25.0
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_result
        
        # Calculate week dates
        week_start = date.today() - timedelta(days=7)
        week_end = date.today()
        
        result = await generator._get_minutes_learned(
            "hashed_learner_id",
            sample_tenant_id,
            week_start,
            week_end
        )
        
        assert result["total_minutes"] == 150.0
        assert result["session_count"] == 6
        assert result["avg_session_minutes"] == 25.0
        assert result["hours_learned"] == 2.5
    
    @pytest.mark.asyncio
    async def test_get_minutes_learned_no_data(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test minutes learned when no data available."""
        # Mock query result with None values
        mock_result = Mock()
        mock_result.total_minutes = None
        mock_result.session_count = None
        mock_result.avg_session_minutes = None
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_result
        
        week_start = date.today() - timedelta(days=7)
        week_end = date.today()
        
        result = await generator._get_minutes_learned(
            "hashed_learner_id",
            sample_tenant_id,
            week_start,
            week_end
        )
        
        assert result["total_minutes"] == 0
        assert result["session_count"] == 0
        assert result["avg_session_minutes"] == 0
        assert result["hours_learned"] == 0
    
    @pytest.mark.asyncio
    async def test_get_subjects_advanced(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test subjects advanced calculation."""
        # Mock query results
        mock_improvements = [
            Mock(
                subject_id=uuid4(),
                max_score=Decimal('0.85'),
                min_score=Decimal('0.70')
            ),
            Mock(
                subject_id=uuid4(),
                max_score=Decimal('0.92'),
                min_score=Decimal('0.85')
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = mock_improvements
        
        week_start = date.today() - timedelta(days=7)
        week_end = date.today()
        
        result = await generator._get_subjects_advanced(
            "hashed_learner_id",
            sample_tenant_id,
            week_start,
            week_end
        )
        
        assert result["subjects_count"] == 2
        assert len(result["subjects"]) == 2
        assert result["total_improvement"] > 0
        assert result["avg_improvement"] > 0
    
    @pytest.mark.asyncio
    async def test_get_completed_goals(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test completed goals retrieval."""
        # Mock completed goals
        mock_goals = [
            Mock(
                goal_id=uuid4(),
                goal_title="Complete 5 math exercises",
                goal_type="academic",
                completed_at=datetime.now(),
                achievement_score=Decimal('0.95')
            ),
            Mock(
                goal_id=uuid4(),
                goal_title="Practice reading for 30 minutes",
                goal_type="academic",
                completed_at=datetime.now(),
                achievement_score=Decimal('1.0')
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = mock_goals
        
        week_start = date.today() - timedelta(days=7)
        week_end = date.today()
        
        result = await generator._get_completed_goals(
            "hashed_learner_id",
            sample_tenant_id,
            week_start,
            week_end
        )
        
        assert result["goals_count"] == 2
        assert len(result["goals"]) == 2
        assert result["total_achievement_score"] == 1.95
    
    @pytest.mark.asyncio
    async def test_get_slp_streaks_active(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test SLP streaks when active."""
        # Mock current streak
        mock_streak = Mock(
            streak_days=7,
            is_active=True,
            longest_streak=12
        )
        
        # Mock weekly activities
        mock_weekly = Mock(activity_count=5)
        
        mock_db_session.query.return_value.filter.return_value.first.side_effect = [
            mock_streak,  # For current streak query
            mock_weekly   # For weekly activities query
        ]
        
        week_start = date.today() - timedelta(days=7)
        week_end = date.today()
        
        result = await generator._get_slp_streaks(
            "hashed_learner_id",
            sample_tenant_id,
            week_start,
            week_end
        )
        
        assert result["current_streak_days"] == 7
        assert result["weekly_activity_count"] == 5
        assert result["streak_active"] == True
        assert result["longest_streak"] == 12
    
    @pytest.mark.asyncio
    async def test_get_sel_progress(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test SEL progress calculation."""
        # Mock SEL progress data
        mock_progress = [
            Mock(
                sel_skill="self-awareness",
                skill_score=Decimal('0.75'),
                assessment_date=date.today()
            ),
            Mock(
                sel_skill="self-awareness",
                skill_score=Decimal('0.85'),
                assessment_date=date.today() - timedelta(days=1)
            ),
            Mock(
                sel_skill="empathy",
                skill_score=Decimal('0.80'),
                assessment_date=date.today()
            ),
            Mock(
                sel_skill="empathy",
                skill_score=Decimal('0.65'),
                assessment_date=date.today() - timedelta(days=2)
            )
        ]
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_progress
        
        week_start = date.today() - timedelta(days=7)
        week_end = date.today()
        
        result = await generator._get_sel_progress(
            "hashed_learner_id",
            sample_tenant_id,
            week_start,
            week_end
        )
        
        assert result["activities_count"] == 4
        assert result["skills_count"] >= 0
        assert "skills_improved" in result
        assert result["overall_improvement"] >= 0
    
    @pytest.mark.asyncio
    async def test_celebration_highlight_selection(self, generator):
        """Test celebration highlight selection logic."""
        # Test with high time dedication
        wins_data = {
            "minutes_learned": {"total_minutes": 180, "hours_learned": 3.0, "session_count": 8},
            "subjects_advanced": {"subjects_count": 2},
            "completed_goals": {"goals_count": 1},
            "slp_streaks": {"current_streak_days": 3},
            "sel_progress": {"skills_count": 1}
        }
        
        result = await generator._get_celebration_highlight(wins_data, "en", "elementary")
        
        assert result["type"] == "time_dedication"
        assert result["value"] == 3.0
        assert "message_key" in result
    
    @pytest.mark.asyncio
    async def test_celebration_highlight_multi_subject(self, generator):
        """Test celebration highlight for multi-subject mastery."""
        wins_data = {
            "minutes_learned": {"total_minutes": 60, "hours_learned": 1.0, "session_count": 3},
            "subjects_advanced": {"subjects_count": 4},  # High subject count
            "completed_goals": {"goals_count": 1},
            "slp_streaks": {"current_streak_days": 2},
            "sel_progress": {"skills_count": 0}
        }
        
        result = await generator._get_celebration_highlight(wins_data, "en", "elementary")
        
        assert result["type"] == "multi_subject_mastery"
        assert result["value"] == 4
    
    @pytest.mark.asyncio
    async def test_week_comparison_with_data(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test week-over-week comparison when data exists."""
        # Mock last week's data
        mock_last_week = Mock(total_minutes=100.0)
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_last_week
        
        week_start = date.today() - timedelta(days=7)
        
        result = await generator._get_week_comparison(
            "hashed_learner_id",
            sample_tenant_id,
            week_start
        )
        
        assert result["last_week_minutes"] == 100.0
        assert result["has_comparison"] == True
    
    @pytest.mark.asyncio
    async def test_week_comparison_no_data(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test week-over-week comparison when no prior data."""
        # Mock no last week data
        mock_last_week = Mock(total_minutes=None)
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_last_week
        
        week_start = date.today() - timedelta(days=7)
        
        result = await generator._get_week_comparison(
            "hashed_learner_id",
            sample_tenant_id,
            week_start
        )
        
        assert result["last_week_minutes"] == 0
        assert result["has_comparison"] == False
    
    def test_generate_encouragement_message_exceptional(self, generator):
        """Test encouragement message for exceptional performance."""
        wins_data = {
            "minutes_learned": {"total_minutes": 200},
            "completed_goals": {"goals_count": 3}
        }
        
        result = generator._generate_encouragement_message(wins_data, "en", "elementary")
        
        assert result["message_key"] == "encouragement.exceptional_week"
        assert result["tone"] == "celebratory"
        assert result["locale"] == "en"
        assert result["grade_band"] == "elementary"
    
    def test_generate_encouragement_message_good_progress(self, generator):
        """Test encouragement message for good progress."""
        wins_data = {
            "minutes_learned": {"total_minutes": 90},
            "completed_goals": {"goals_count": 1}
        }
        
        result = generator._generate_encouragement_message(wins_data, "en", "middle")
        
        assert result["message_key"] == "encouragement.great_progress"
        assert result["tone"] == "encouraging"
    
    def test_generate_encouragement_message_supportive(self, generator):
        """Test encouragement message for low activity."""
        wins_data = {
            "minutes_learned": {"total_minutes": 30},
            "completed_goals": {"goals_count": 0}
        }
        
        result = generator._generate_encouragement_message(wins_data, "es", "high")
        
        assert result["message_key"] == "encouragement.keep_going"
        assert result["tone"] == "supportive"
        assert result["locale"] == "es"
        assert result["grade_band"] == "high"
    
    def test_hash_learner_id(self, generator):
        """Test learner ID hashing for privacy."""
        learner_id = str(uuid4())
        
        hashed = generator._hash_learner_id(learner_id)
        
        assert isinstance(hashed, str)
        assert len(hashed) == 32  # SHA256 truncated to 32 chars
        assert hashed != learner_id
        
        # Verify consistent hashing
        hashed2 = generator._hash_learner_id(learner_id)
        assert hashed == hashed2
    
    @pytest.mark.asyncio
    async def test_generate_weekly_wins_error_handling(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test error handling in weekly wins generation."""
        # Mock database error
        mock_db_session.query.side_effect = Exception("Database connection error")
        
        with pytest.raises(Exception) as exc_info:
            await generator.generate_weekly_wins(
                learner_id=sample_learner_id,
                tenant_id=sample_tenant_id
            )
        
        assert "Database connection error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_timezone_handling(self, generator, mock_db_session, sample_learner_id, sample_tenant_id):
        """Test timezone handling in week calculation."""
        # Mock minimal database responses
        mock_db_session.query.return_value.filter.return_value.first.return_value = Mock(
            total_minutes=0, session_count=0, avg_session_minutes=0
        )
        mock_db_session.query.return_value.filter.return_value.group_by.return_value.all.return_value = []
        mock_db_session.query.return_value.filter.return_value.all.return_value = []
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        # Test different timezones
        timezones = ["America/New_York", "America/Los_Angeles", "Europe/London", "Asia/Tokyo"]
        
        for tz in timezones:
            result = await generator.generate_weekly_wins(
                learner_id=sample_learner_id,
                tenant_id=sample_tenant_id,
                user_timezone=tz
            )
            
            assert result["timezone"] == tz
            assert "week_start" in result
            assert "week_end" in result


# Integration test fixtures
@pytest.fixture
def real_db_session():
    """Real database session for integration tests."""
    # This would be configured with a test database
    pass

@pytest.mark.integration
class TestWeeklyWinsIntegration:
    """Integration tests with real database."""
    
    @pytest.mark.asyncio
    async def test_full_weekly_wins_generation(self, real_db_session):
        """Test full weekly wins generation with real data."""
        # This would test against a real test database
        # with sample data inserted
        pass
