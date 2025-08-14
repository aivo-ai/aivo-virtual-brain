# AIVO Game Generation Service - Manifest Validation Tests
# S2-13 Implementation - Test game manifest validation and duration adherence

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from app.models import GameManifest, GameType, GameDifficulty, GameStatus, SubjectArea, GradeBand
from app.routes import _validate_manifest_structure


class TestGameManifestValidation:
    """Test suite for game manifest validation and quality assurance."""
    
    def test_valid_complete_manifest(self):
        """Test validation of a complete, valid game manifest."""
        manifest = self._create_valid_manifest()
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is True
        assert result["score"] >= 85.0
        assert len(result["issues"]) == 0
        assert result["duration_compliance"]["within_tolerance"] is True
        assert result["duration_compliance"]["deviation_percentage"] <= 10.0
    
    def test_missing_title_validation(self):
        """Test validation fails when game title is missing."""
        manifest = self._create_valid_manifest()
        manifest.game_title = ""
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is False
        assert result["score"] < 100.0
        assert "Game title is missing or too short" in result["issues"]
    
    def test_short_title_validation(self):
        """Test validation fails when game title is too short."""
        manifest = self._create_valid_manifest()
        manifest.game_title = "Hi"
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is False
        assert "Game title is missing or too short" in result["issues"]
    
    def test_missing_scenes_validation(self):
        """Test validation fails when no game scenes are defined."""
        manifest = self._create_valid_manifest()
        manifest.game_scenes = []
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is False
        assert result["score"] < 70.0
        assert "No game scenes defined" in result["issues"]
    
    def test_scene_missing_content_validation(self):
        """Test validation detects scenes with missing content."""
        manifest = self._create_valid_manifest()
        manifest.game_scenes = [
            {
                "scene_id": "scene1",
                "scene_name": "Test Scene",
                "scene_type": "gameplay",
                "duration_minutes": 5.0
                # Missing content field
            }
        ]
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is False
        assert any("missing content" in issue for issue in result["issues"])
    
    def test_duration_compliance_within_tolerance(self):
        """Test duration compliance when within acceptable tolerance."""
        manifest = self._create_valid_manifest()
        manifest.target_duration_minutes = 10.0
        manifest.estimated_duration_minutes = 10.5  # 5% deviation
        
        result = _validate_manifest_structure(manifest)
        
        compliance = result["duration_compliance"]
        assert compliance["within_tolerance"] is True
        assert compliance["deviation_percentage"] == 5.0
        assert compliance["target_duration"] == 10.0
        assert compliance["estimated_duration"] == 10.5
    
    def test_duration_compliance_moderate_deviation(self):
        """Test duration compliance with moderate deviation (10-20%)."""
        manifest = self._create_valid_manifest()
        manifest.target_duration_minutes = 10.0
        manifest.estimated_duration_minutes = 11.5  # 15% deviation
        
        result = _validate_manifest_structure(manifest)
        
        compliance = result["duration_compliance"]
        assert compliance["within_tolerance"] is True  # Still within tolerance
        assert compliance["deviation_percentage"] == 15.0
        assert len([r for r in result["recommendations"] if "duration" in r.lower()]) > 0
    
    def test_duration_compliance_high_deviation(self):
        """Test duration compliance with high deviation (>20%)."""
        manifest = self._create_valid_manifest()
        manifest.target_duration_minutes = 10.0
        manifest.estimated_duration_minutes = 13.0  # 30% deviation
        
        result = _validate_manifest_structure(manifest)
        
        compliance = result["duration_compliance"]
        assert compliance["within_tolerance"] is False
        assert compliance["deviation_percentage"] == 30.0
        assert any("Duration deviation too high" in issue for issue in result["issues"])
        assert result["score"] < 85.0
    
    def test_duration_under_target(self):
        """Test duration compliance when game is significantly shorter than target."""
        manifest = self._create_valid_manifest()
        manifest.target_duration_minutes = 15.0
        manifest.estimated_duration_minutes = 10.0  # 33% shorter
        
        result = _validate_manifest_structure(manifest)
        
        compliance = result["duration_compliance"]
        assert compliance["within_tolerance"] is False
        assert compliance["deviation_percentage"] == 33.33  # approximately
    
    def test_no_assets_recommendation(self):
        """Test that missing assets generates a recommendation."""
        manifest = self._create_valid_manifest()
        manifest.game_assets = []
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is True  # Still valid, just not optimal
        assert any("assets" in rec.lower() for rec in result["recommendations"])
        assert result["score"] < 95.0
    
    def test_no_learning_outcomes_recommendation(self):
        """Test that missing learning outcomes generates a recommendation."""
        manifest = self._create_valid_manifest()
        manifest.expected_learning_outcomes = []
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is True
        assert any("learning outcomes" in rec.lower() for rec in result["recommendations"])
    
    def test_comprehensive_validation_scoring(self):
        """Test comprehensive validation scoring with multiple issues."""
        manifest = self._create_valid_manifest()
        
        # Introduce multiple issues
        manifest.game_title = "Hi"  # Too short (-20 points)
        manifest.game_assets = []   # Missing assets (-10 points)
        manifest.estimated_duration_minutes = 15.0  # 50% deviation (-15 points)
        manifest.target_duration_minutes = 10.0
        manifest.game_scenes = [
            {
                "scene_id": "scene1",
                "duration_minutes": 5.0,
                # Missing content (-10 points)
            }
        ]
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is False
        assert result["score"] <= 45.0  # Should lose at least 55 points
        assert len(result["issues"]) >= 3
        assert len(result["recommendations"]) >= 1
    
    def test_perfect_manifest_scoring(self):
        """Test that a perfect manifest gets high scoring."""
        manifest = self._create_valid_manifest()
        
        # Ensure perfect conditions
        manifest.game_title = "Amazing Educational Puzzle Adventure"
        manifest.target_duration_minutes = 12.0
        manifest.estimated_duration_minutes = 12.1  # 0.8% deviation
        manifest.game_scenes = [
            {
                "scene_id": "intro",
                "scene_name": "Welcome",
                "scene_type": "intro",
                "duration_minutes": 2.0,
                "content": {
                    "instructions": "Welcome to the game!",
                    "challenge": "Get ready to learn",
                    "visual_elements": "Colorful interface"
                }
            },
            {
                "scene_id": "gameplay",
                "scene_name": "Main Game",
                "scene_type": "gameplay", 
                "duration_minutes": 8.0,
                "content": {
                    "instructions": "Solve the puzzles",
                    "challenge": "Complete all challenges",
                    "visual_elements": "Interactive puzzle elements"
                }
            },
            {
                "scene_id": "conclusion",
                "scene_name": "Completion",
                "scene_type": "conclusion",
                "duration_minutes": 2.1,
                "content": {
                    "instructions": "Great job!",
                    "challenge": "Review your progress",
                    "visual_elements": "Celebration screen"
                }
            }
        ]
        manifest.game_assets = [
            {
                "asset_id": "background_music",
                "asset_type": "sound",
                "asset_data": {"content": "Upbeat learning music"}
            }
        ]
        manifest.expected_learning_outcomes = ["Problem solving", "Pattern recognition"]
        
        result = _validate_manifest_structure(manifest)
        
        assert result["is_valid"] is True
        assert result["score"] == 100.0
        assert len(result["issues"]) == 0
        assert result["duration_compliance"]["within_tolerance"] is True
    
    def test_edge_case_zero_duration(self):
        """Test validation with zero duration values."""
        manifest = self._create_valid_manifest()
        manifest.target_duration_minutes = 0.0
        manifest.estimated_duration_minutes = 0.0
        
        result = _validate_manifest_structure(manifest)
        
        # Should handle gracefully without division by zero
        assert "duration_compliance" in result
        compliance = result["duration_compliance"]
        assert compliance["target_duration"] == 0.0
        assert compliance["estimated_duration"] == 0.0
    
    def test_validation_result_structure(self):
        """Test that validation result has expected structure."""
        manifest = self._create_valid_manifest()
        
        result = _validate_manifest_structure(manifest)
        
        # Check required fields
        assert "is_valid" in result
        assert "score" in result
        assert "issues" in result
        assert "recommendations" in result
        assert "duration_compliance" in result
        
        # Check types
        assert isinstance(result["is_valid"], bool)
        assert isinstance(result["score"], (int, float))
        assert isinstance(result["issues"], list)
        assert isinstance(result["recommendations"], list)
        assert isinstance(result["duration_compliance"], dict)
        
        # Check duration compliance structure
        compliance = result["duration_compliance"]
        assert "target_duration" in compliance
        assert "estimated_duration" in compliance
        assert "within_tolerance" in compliance
        assert "deviation_percentage" in compliance
    
    def _create_valid_manifest(self) -> GameManifest:
        """Create a valid game manifest for testing."""
        return GameManifest(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            learner_id=uuid.uuid4(),
            game_title="Educational Puzzle Challenge",
            game_description="A fun puzzle game for learning",
            game_type=GameType.PUZZLE,
            subject_area=SubjectArea.MATH,
            target_duration_minutes=10.0,
            estimated_duration_minutes=10.2,
            difficulty_level=GameDifficulty.MEDIUM,
            grade_band=GradeBand.MIDDLE_SCHOOL,
            status=GameStatus.READY,
            game_scenes=[
                {
                    "scene_id": "intro",
                    "scene_name": "Introduction",
                    "scene_type": "intro",
                    "duration_minutes": 2.0,
                    "content": {
                        "instructions": "Welcome to the puzzle challenge!",
                        "challenge": "Prepare to solve fun puzzles",
                        "visual_elements": "Colorful welcome screen"
                    }
                },
                {
                    "scene_id": "gameplay",
                    "scene_name": "Puzzle Solving",
                    "scene_type": "gameplay",
                    "duration_minutes": 6.0,
                    "content": {
                        "instructions": "Solve the pattern puzzles",
                        "challenge": "Complete all puzzle levels",
                        "visual_elements": "Interactive puzzle interface"
                    }
                },
                {
                    "scene_id": "conclusion",
                    "scene_name": "Well Done",
                    "scene_type": "conclusion",
                    "duration_minutes": 2.2,
                    "content": {
                        "instructions": "Congratulations!",
                        "challenge": "Review your results",
                        "visual_elements": "Success celebration"
                    }
                }
            ],
            game_assets=[
                {
                    "asset_id": "puzzle_images",
                    "asset_type": "image",
                    "asset_data": {"content": "Colorful puzzle piece graphics"}
                }
            ],
            game_rules={
                "scoring_rules": {"points_per_correct": 10},
                "win_conditions": ["Complete all puzzles"],
                "time_limits": {"total_game": 600}
            },
            expected_learning_outcomes=["Pattern recognition", "Problem solving"],
            quality_score=85.0,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=2)
        )


# Additional test class for duration-specific validation
class TestDurationCompliance:
    """Focused tests for duration compliance checking."""
    
    @pytest.mark.parametrize("target,estimated,expected_valid,expected_deviation", [
        (10.0, 10.0, True, 0.0),      # Perfect match
        (10.0, 10.5, True, 5.0),      # 5% deviation - good
        (10.0, 11.0, True, 10.0),     # 10% deviation - acceptable
        (10.0, 11.5, True, 15.0),     # 15% deviation - moderate
        (10.0, 12.5, False, 25.0),    # 25% deviation - too high
        (10.0, 8.0, False, 20.0),     # 20% under - too high
        (15.0, 18.5, False, 23.33),   # 23% over - too high
    ])
    def test_duration_compliance_parametrized(self, target, estimated, expected_valid, expected_deviation):
        """Test duration compliance with various scenarios."""
        manifest = GameManifest(
            id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            learner_id=uuid.uuid4(),
            game_title="Test Game",
            target_duration_minutes=target,
            estimated_duration_minutes=estimated,
            game_scenes=[{
                "scene_id": "test",
                "content": {"instructions": "test"}
            }]
        )
        
        result = _validate_manifest_structure(manifest)
        
        compliance = result["duration_compliance"]
        assert compliance["within_tolerance"] == expected_valid
        assert abs(compliance["deviation_percentage"] - expected_deviation) < 0.1


if __name__ == "__main__":
    pytest.main([__file__])
