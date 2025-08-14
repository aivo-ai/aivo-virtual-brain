# AIVO Game Generation Service - Duration Adherence Tests
# S2-13 Implementation - Test that generated games respect duration constraints

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.engine import GameGenerationEngine
from app.models import (
    GameManifest, LearnerProfile, GameDifficulty, GameStatus,
    GameType as ModelGameType, SubjectArea as ModelSubjectArea, GradeBand as ModelGradeBand
)
from app.schemas import GameGenerationRequest, GameType, SubjectArea, GradeBand


class TestDurationAdherence:
    """Test suite for ensuring games adhere to requested durations."""
    
    @pytest.fixture
    def game_engine(self):
        """Create a game generation engine for testing."""
        engine = GameGenerationEngine()
        return engine
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = Mock()
        db.add = Mock()
        db.commit = Mock()
        db.refresh = Mock()
        db.query = Mock()
        return db
    
    @pytest.fixture
    def sample_request(self):
        """Sample game generation request."""
        return GameGenerationRequest(
            learner_id=uuid.uuid4(),
            duration_minutes=15,
            subject_area=SubjectArea.MATHEMATICS,  # Use schema enum
            game_type=GameType.MATH_PUZZLE,       # Use schema enum  
            difficulty=GameDifficulty.MEDIUM,
            grade_band=GradeBand.GRADES_6_8       # Use schema enum
        )
    
    @pytest.mark.asyncio
    async def test_short_duration_adherence(self, game_engine, mock_db, sample_request):
        """Test that short duration games (5 minutes) are properly generated."""
        # Set short duration
        sample_request.minutes = 5
        tenant_id = uuid.uuid4()
        
        # Mock AI response for short game
        mock_ai_response = {
            "title": "Quick Math Challenge",
            "description": "A fast-paced math game",
            "scenes": [
                {
                    "scene_id": "intro",
                    "scene_name": "Welcome", 
                    "scene_type": "intro",
                    "duration_minutes": 0.5,
                    "content": {"instructions": "Quick start!", "challenge": "Get ready"}
                },
                {
                    "scene_id": "gameplay",
                    "scene_name": "Math Problems",
                    "scene_type": "gameplay", 
                    "duration_minutes": 4.0,
                    "content": {"instructions": "Solve problems", "challenge": "Complete calculations"}
                },
                {
                    "scene_id": "conclusion",
                    "scene_name": "Done",
                    "scene_type": "conclusion",
                    "duration_minutes": 0.5,
                    "content": {"instructions": "Great job!", "challenge": "See results"}
                }
            ],
            "assets": [{"asset_id": "math_problems", "asset_type": "text", "asset_data": {"content": "Quick problems"}}],
            "rules": {"scoring_rules": {"points_per_correct": 10}, "win_conditions": ["Complete problems"]},
            "learning_outcomes": ["Quick math skills"],
            "quality_score": 80.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(sample_request, tenant_id, mock_db)
            
            # Check duration adherence
            assert manifest.target_duration_minutes == 5
            assert manifest.estimated_duration_minutes <= 5.5  # Within 10% tolerance
            assert manifest.estimated_duration_minutes >= 4.5  # Not too short
            
            # Check scenes total to appropriate duration
            total_scene_duration = sum(scene["duration_minutes"] for scene in manifest.game_scenes)
            assert total_scene_duration == manifest.estimated_duration_minutes
            assert abs(total_scene_duration - 5.0) <= 0.5  # Within 30 seconds
    
    @pytest.mark.asyncio
    async def test_medium_duration_adherence(self, game_engine, mock_db, sample_request):
        """Test that medium duration games (15 minutes) are properly generated."""
        # Set medium duration (default)
        assert sample_request.minutes == 15
        tenant_id = uuid.uuid4()
        
        mock_ai_response = {
            "title": "Math Puzzle Adventure",
            "description": "An engaging math puzzle game",
            "scenes": [
                {
                    "scene_id": "intro",
                    "scene_name": "Welcome",
                    "scene_type": "intro", 
                    "duration_minutes": 1.5,
                    "content": {"instructions": "Welcome to puzzles!", "challenge": "Prepare to learn"}
                },
                {
                    "scene_id": "level1",
                    "scene_name": "Easy Puzzles",
                    "scene_type": "gameplay",
                    "duration_minutes": 4.0,
                    "content": {"instructions": "Solve easy puzzles", "challenge": "Build confidence"}
                },
                {
                    "scene_id": "level2", 
                    "scene_name": "Medium Puzzles",
                    "scene_type": "gameplay",
                    "duration_minutes": 5.0,
                    "content": {"instructions": "Try harder puzzles", "challenge": "Apply skills"}
                },
                {
                    "scene_id": "level3",
                    "scene_name": "Hard Puzzles", 
                    "scene_type": "gameplay",
                    "duration_minutes": 3.5,
                    "content": {"instructions": "Challenge yourself", "challenge": "Master concepts"}
                },
                {
                    "scene_id": "conclusion",
                    "scene_name": "Success!",
                    "scene_type": "conclusion",
                    "duration_minutes": 1.0,
                    "content": {"instructions": "Excellent work!", "challenge": "Review learning"}
                }
            ],
            "assets": [{"asset_id": "puzzle_graphics", "asset_type": "image", "asset_data": {"content": "Math visuals"}}],
            "rules": {"scoring_rules": {"points_per_correct": 15}, "win_conditions": ["Complete all levels"]},
            "learning_outcomes": ["Problem solving", "Mathematical reasoning"],
            "quality_score": 85.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(sample_request, tenant_id, mock_db)
            
            # Check duration adherence
            assert manifest.target_duration_minutes == 15
            assert manifest.estimated_duration_minutes <= 16.5  # Within 10% tolerance
            assert manifest.estimated_duration_minutes >= 13.5  # Not too short
            
            # Verify total scene duration
            total_scene_duration = sum(scene["duration_minutes"] for scene in manifest.game_scenes)
            assert total_scene_duration == manifest.estimated_duration_minutes
            assert abs(total_scene_duration - 15.0) <= 1.5  # Within 1.5 minutes
    
    @pytest.mark.asyncio
    async def test_long_duration_adherence(self, game_engine, mock_db, sample_request):
        """Test that long duration games (45 minutes) are properly generated."""
        # Set long duration
        sample_request.minutes = 45
        tenant_id = uuid.uuid4()
        
        mock_ai_response = {
            "title": "Extended Math Journey",
            "description": "A comprehensive math learning experience",
            "scenes": [
                {"scene_id": "intro", "scene_name": "Introduction", "scene_type": "intro", 
                 "duration_minutes": 3.0, "content": {"instructions": "Welcome!", "challenge": "Begin journey"}},
                {"scene_id": "warmup", "scene_name": "Warmup", "scene_type": "gameplay",
                 "duration_minutes": 5.0, "content": {"instructions": "Practice basics", "challenge": "Refresh skills"}},
                {"scene_id": "section1", "scene_name": "Addition", "scene_type": "gameplay",
                 "duration_minutes": 8.0, "content": {"instructions": "Addition problems", "challenge": "Master addition"}},
                {"scene_id": "section2", "scene_name": "Subtraction", "scene_type": "gameplay", 
                 "duration_minutes": 8.0, "content": {"instructions": "Subtraction problems", "challenge": "Master subtraction"}},
                {"scene_id": "section3", "scene_name": "Multiplication", "scene_type": "gameplay",
                 "duration_minutes": 10.0, "content": {"instructions": "Multiplication problems", "challenge": "Master multiplication"}},
                {"scene_id": "section4", "scene_name": "Division", "scene_type": "gameplay",
                 "duration_minutes": 8.0, "content": {"instructions": "Division problems", "challenge": "Master division"}},
                {"scene_id": "final", "scene_name": "Final Challenge", "scene_type": "gameplay",
                 "duration_minutes": 2.5, "content": {"instructions": "Mixed problems", "challenge": "Show mastery"}},
                {"scene_id": "conclusion", "scene_name": "Completion", "scene_type": "conclusion",
                 "duration_minutes": 0.5, "content": {"instructions": "Congratulations!", "challenge": "Celebrate success"}}
            ],
            "assets": [{"asset_id": "comprehensive_math", "asset_type": "data", "asset_data": {"content": "Full curriculum"}}],
            "rules": {"scoring_rules": {"points_per_correct": 20}, "win_conditions": ["Complete all sections"]},
            "learning_outcomes": ["Comprehensive math skills", "Problem solving", "Persistence"],
            "quality_score": 90.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(sample_request, tenant_id, mock_db)
            
            # Check duration adherence for long game
            assert manifest.target_duration_minutes == 45
            assert manifest.estimated_duration_minutes <= 49.5  # Within 10% tolerance
            assert manifest.estimated_duration_minutes >= 40.5  # Not too short
            
            # Verify scenes are structured for long engagement
            total_scene_duration = sum(scene["duration_minutes"] for scene in manifest.game_scenes)
            assert total_scene_duration == manifest.estimated_duration_minutes
            assert len(manifest.game_scenes) >= 6  # Sufficient variety for long duration
    
    @pytest.mark.asyncio
    async def test_attention_span_adaptation(self, game_engine, mock_db):
        """Test that games adapt to learner attention span."""
        tenant_id = uuid.uuid4()
        learner_id = uuid.uuid4()
        
        # Create learner profile with short attention span
        mock_profile = LearnerProfile(
            tenant_id=tenant_id,
            learner_id=learner_id,
            grade_band=ModelGradeBand.EARLY_ELEMENTARY,  # Use model enum
            attention_span_minutes=8,  # Short attention span
            preferred_game_types=[ModelGameType.MEMORY],  # Use model enum
            preferred_difficulty=GameDifficulty.EASY
        )
        
        # Mock database to return this profile
        mock_db.query().filter().first.return_value = mock_profile
        
        request = GameGenerationRequest(
            learner_id=learner_id,
            duration_minutes=20,  # Request longer than attention span
            subject_area=SubjectArea.ENGLISH,  # Use schema enum
            grade_band=GradeBand.K_2  # Use schema enum
        )
        
        mock_ai_response = {
            "title": "Short Memory Game",
            "description": "A quick memory challenge",
            "scenes": [
                {"scene_id": "intro", "scene_name": "Hello", "scene_type": "intro",
                 "duration_minutes": 1.0, "content": {"instructions": "Let's play!", "challenge": "Get ready"}},
                {"scene_id": "gameplay", "scene_name": "Memory Match", "scene_type": "gameplay",
                 "duration_minutes": 6.0, "content": {"instructions": "Match cards", "challenge": "Remember positions"}},
                {"scene_id": "conclusion", "scene_name": "Great Job", "scene_type": "conclusion",
                 "duration_minutes": 1.0, "content": {"instructions": "Well done!", "challenge": "You did great"}}
            ],
            "assets": [{"asset_id": "memory_cards", "asset_type": "image", "asset_data": {"content": "Simple cards"}}],
            "rules": {"scoring_rules": {"points_per_correct": 5}, "win_conditions": ["Match all pairs"]},
            "learning_outcomes": ["Memory improvement"],
            "quality_score": 75.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(request, tenant_id, mock_db)
            
            # Should adapt to attention span, not full requested duration
            assert manifest.target_duration_minutes == 20  # Original request
            assert manifest.estimated_duration_minutes <= 8.5  # Adapted to attention span
            assert manifest.estimated_duration_minutes >= 7.0   # But not too short
    
    @pytest.mark.asyncio
    async def test_fallback_duration_compliance(self, game_engine, mock_db, sample_request):
        """Test that fallback games also comply with duration requirements."""
        tenant_id = uuid.uuid4()
        
        # Force fallback by making AI generation fail
        with patch.object(game_engine, '_generate_ai_content', side_effect=Exception("AI service unavailable")):
            manifest = await game_engine.generate_game(sample_request, tenant_id, mock_db)
            
            # Even fallback should respect duration
            assert manifest.target_duration_minutes == 15
            assert manifest.estimated_duration_minutes is not None
            assert manifest.estimated_duration_minutes > 0
            
            # Fallback should be within reasonable bounds
            assert manifest.estimated_duration_minutes <= 18.0  # Within 20% tolerance
            assert manifest.estimated_duration_minutes >= 12.0  # Not too short
            
            # Should be marked as fallback
            assert manifest.fallback_used is True
            assert "fallback_applied" in manifest.generation_errors
    
    @pytest.mark.parametrize("requested_duration,expected_min,expected_max", [
        (3, 2.5, 3.5),      # Very short game
        (8, 7.0, 9.0),      # Short game  
        (12, 10.5, 13.5),   # Medium game
        (25, 22.0, 28.0),   # Long game
        (60, 54.0, 66.0),   # Maximum duration
    ])
    @pytest.mark.asyncio
    async def test_duration_bounds_parametrized(self, game_engine, mock_db, requested_duration, expected_min, expected_max):
        """Test duration adherence across various requested durations."""
        tenant_id = uuid.uuid4()
        request = GameGenerationRequest(
            learner_id=uuid.uuid4(),
            duration_minutes=requested_duration,
            subject_area=SubjectArea.MATHEMATICS,
            game_type=GameType.MATH_PUZZLE
        )
        
        # Create appropriate mock response based on duration
        num_scenes = max(3, min(8, requested_duration // 3))  # Scale scenes with duration
        scene_duration = requested_duration / num_scenes
        
        mock_scenes = []
        for i in range(num_scenes):
            scene_type = "intro" if i == 0 else "conclusion" if i == num_scenes - 1 else "gameplay"
            mock_scenes.append({
                "scene_id": f"scene_{i}",
                "scene_name": f"Scene {i+1}",
                "scene_type": scene_type,
                "duration_minutes": scene_duration,
                "content": {"instructions": f"Scene {i+1} instructions", "challenge": f"Scene {i+1} challenge"}
            })
        
        mock_ai_response = {
            "title": f"{requested_duration} Minute Game",
            "description": f"A {requested_duration} minute educational game",
            "scenes": mock_scenes,
            "assets": [{"asset_id": "game_assets", "asset_type": "mixed", "asset_data": {"content": "Game content"}}],
            "rules": {"scoring_rules": {"points_per_correct": 10}, "win_conditions": ["Complete game"]},
            "learning_outcomes": ["Learning outcome"],
            "quality_score": 80.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(request, tenant_id, mock_db)
            
            # Check duration bounds
            assert manifest.target_duration_minutes == requested_duration
            assert expected_min <= manifest.estimated_duration_minutes <= expected_max
            
            # Verify scene structure makes sense
            total_scene_duration = sum(scene["duration_minutes"] for scene in manifest.game_scenes)
            assert total_scene_duration == manifest.estimated_duration_minutes
    
    @pytest.mark.asyncio
    async def test_minimum_duration_validation(self, game_engine, mock_db):
        """Test that games cannot be shorter than 1 minute."""
        tenant_id = uuid.uuid4()
        request = GameGenerationRequest(
            learner_id=uuid.uuid4(),
            duration_minutes=1,  # Minimum duration
            subject_area=SubjectArea.ENGLISH
        )
        
        mock_ai_response = {
            "title": "Quick Game",
            "description": "A very quick game",
            "scenes": [
                {"scene_id": "quick", "scene_name": "Quick Scene", "scene_type": "gameplay",
                 "duration_minutes": 1.0, "content": {"instructions": "Quick task", "challenge": "Fast completion"}}
            ],
            "assets": [],
            "rules": {"scoring_rules": {"points_per_correct": 1}, "win_conditions": ["Complete quickly"]},
            "learning_outcomes": ["Quick thinking"],
            "quality_score": 60.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(request, tenant_id, mock_db)
            
            assert manifest.target_duration_minutes == 1
            assert manifest.estimated_duration_minutes >= 1.0
            assert manifest.estimated_duration_minutes <= 1.2  # Allow slight buffer
    
    @pytest.mark.asyncio
    async def test_maximum_duration_validation(self, game_engine, mock_db):
        """Test that games respect maximum duration of 60 minutes."""
        tenant_id = uuid.uuid4()
        request = GameGenerationRequest(
            learner_id=uuid.uuid4(),
            duration_minutes=60,  # Maximum duration
            subject_area=SubjectArea.SCIENCE
        )
        
        # Create comprehensive mock response for maximum duration
        mock_scenes = []
        for i in range(12):  # 12 scenes for full hour
            scene_type = "intro" if i == 0 else "conclusion" if i == 11 else "gameplay"
            mock_scenes.append({
                "scene_id": f"section_{i}",
                "scene_name": f"Section {i+1}",
                "scene_type": scene_type,
                "duration_minutes": 5.0,
                "content": {"instructions": f"Section {i+1} content", "challenge": f"Section {i+1} challenge"}
            })
        
        mock_ai_response = {
            "title": "Comprehensive Learning Experience",
            "description": "A full hour of educational content",
            "scenes": mock_scenes,
            "assets": [{"asset_id": "comprehensive_content", "asset_type": "data", "asset_data": {"content": "Full curriculum"}}],
            "rules": {"scoring_rules": {"points_per_correct": 25}, "win_conditions": ["Complete all sections"]},
            "learning_outcomes": ["Comprehensive understanding", "Sustained attention", "Deep learning"],
            "quality_score": 95.0
        }
        
        with patch.object(game_engine, '_generate_ai_content', return_value=mock_ai_response):
            manifest = await game_engine.generate_game(request, tenant_id, mock_db)
            
            assert manifest.target_duration_minutes == 60
            assert manifest.estimated_duration_minutes <= 66.0  # Within 10% tolerance
            assert manifest.estimated_duration_minutes >= 54.0  # Not too short
            
            # Should have substantial content for long duration
            assert len(manifest.game_scenes) >= 8  # Sufficient variety
            total_scene_duration = sum(scene["duration_minutes"] for scene in manifest.game_scenes)
            assert total_scene_duration == manifest.estimated_duration_minutes


if __name__ == "__main__":
    pytest.main([__file__])
