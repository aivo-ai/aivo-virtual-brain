# AIVO Game Generation Service - Pydantic Schemas (Minimal Version)
# S2-13 Implementation - Request/response validation for game generation

from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum
import uuid

from .models import (
    GradeBand, GameType, GameDifficulty, GameStatus, SubjectArea
)


# Minimal schemas for testing

class GameGenerationRequest(BaseModel):
    """Request schema for generating a new game."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    learner_id: uuid.UUID
    minutes: int = Field(ge=1, le=60)
    subject: SubjectArea = SubjectArea.GENERAL
    game_type: Optional[GameType] = None
    difficulty: Optional[GameDifficulty] = GameDifficulty.ADAPTIVE
    grade_band: Optional[GradeBand] = None
    traits: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    require_accessibility: Optional[List[str]] = None
    preferred_interaction_style: Optional[str] = None


class GameGenerationResponse(BaseModel):
    """Response schema for game generation requests."""
    model_config = ConfigDict(from_attributes=True)
    
    success: bool
    message: str
    game_manifest_id: uuid.UUID
    estimated_completion_seconds: int
    status: GameStatus
    expected_ready_at: Optional[datetime] = None


class GameManifestResponse(BaseModel):
    """Response schema for complete game manifests."""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    learner_id: uuid.UUID
    game_title: str
    game_description: Optional[str] = None
    game_type: GameType
    subject_area: SubjectArea
    target_duration_minutes: int
    estimated_duration_minutes: float
    difficulty_level: GameDifficulty
    grade_band: GradeBand
    game_scenes: List[Dict[str, Any]]
    game_assets: List[Dict[str, Any]]
    game_rules: Dict[str, Any]
    status: GameStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    quality_score: Optional[float] = None
    expected_learning_outcomes: List[str] = []
    fallback_used: bool = False
    generation_errors: Optional[Dict[str, Any]] = None


# Additional minimal schemas for the service

class LearnerProfileRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    learner_id: uuid.UUID
    grade_band: GradeBand


class LearnerProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    learner_id: uuid.UUID
    grade_band: GradeBand


class GameSessionCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    learner_id: uuid.UUID
    game_manifest_id: uuid.UUID
    initial_progress: Optional[Dict[str, Any]] = None
    device_info: Optional[Dict[str, Any]] = None


class GameSessionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    progress_percentage: Optional[float] = None
    score: Optional[int] = None
    progress_data: Optional[Dict[str, Any]] = None
    engagement_metrics: Optional[Dict[str, Any]] = None
    performance_data: Optional[Dict[str, Any]] = None
    completion_reason: Optional[str] = None
    learner_satisfaction: Optional[int] = None
    session_notes: Optional[str] = None


class GameSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    learner_id: uuid.UUID
    game_manifest_id: uuid.UUID
    session_status: str = "active"
    session_started_at: datetime
    progress_percentage: float = 0.0
    score: Optional[int] = None


class GameCompletionRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    completion_reason: str
    satisfaction: Optional[int] = None
    final_score: Optional[int] = None
    notes: Optional[str] = None


class GameAnalyticsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    learner_id: uuid.UUID
    total_games_played: int = 0
    total_time_played_minutes: float = 0
    average_completion_rate: float = 0


class GameTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    template_name: str
    game_type: GameType
    subject_area: SubjectArea


class GameListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    games: List[GameManifestResponse]
    total_count: int
    page_size: int
    page_offset: int
    has_more: bool


class ValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    is_valid: bool
    validation_score: float
    issues: List[str]
    recommendations: List[str]
    duration_compliance: Dict[str, Any]


class EventEmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    success: bool
    event_id: Optional[str] = None
    event_type: str
    timestamp: datetime
    error_message: Optional[str] = None
