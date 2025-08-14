"""
Pydantic schemas for AIVO Game Generation Service (S2-13)
Handles request/response validation for dynamic game generation with AI integration
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.types import PositiveInt, PositiveFloat


# Enum definitions matching models
class GameType(str, Enum):
    VOCABULARY_BUILDER = "vocabulary_builder"
    MATH_PUZZLE = "math_puzzle"
    SCIENCE_EXPERIMENT = "science_experiment"
    HISTORY_TIMELINE = "history_timeline"
    READING_COMPREHENSION = "reading_comprehension"
    CREATIVE_WRITING = "creative_writing"
    LOGIC_PUZZLE = "logic_puzzle"
    MEMORY_GAME = "memory_game"
    PATTERN_RECOGNITION = "pattern_recognition"
    CRITICAL_THINKING = "critical_thinking"


class GameDifficulty(str, Enum):
    BEGINNER = "beginner"
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class GameStatus(str, Enum):
    DRAFT = "draft"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SubjectArea(str, Enum):
    ENGLISH = "english"
    MATHEMATICS = "mathematics"
    SCIENCE = "science"
    HISTORY = "history"
    GEOGRAPHY = "geography"
    ARTS = "arts"
    PHYSICAL_EDUCATION = "physical_education"
    FOREIGN_LANGUAGE = "foreign_language"


class GradeBand(str, Enum):
    K_2 = "K-2"
    GRADES_3_5 = "3-5"
    GRADES_6_8 = "6-8"
    GRADES_9_12 = "9-12"


# Base schema with common config
class BaseSchema(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


# Game Generation Schemas
class GameGenerationRequest(BaseSchema):
    """Request schema for generating new games"""
    learner_id: UUID
    duration_minutes: PositiveInt = Field(..., description="Target game duration in minutes", ge=1, le=60)
    game_type: Optional[GameType] = Field(None, description="Specific game type to generate")
    subject_area: Optional[SubjectArea] = Field(None, description="Educational subject focus")
    difficulty: Optional[GameDifficulty] = Field(GameDifficulty.MEDIUM, description="Game difficulty level")
    grade_band: Optional[GradeBand] = Field(None, description="Target grade level range")
    learning_objectives: Optional[List[str]] = Field(default_factory=list, description="Specific learning goals")
    custom_requirements: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional customization")
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v):
        if not (1 <= v <= 60):
            raise ValueError("Duration must be between 1 and 60 minutes")
        return v

    @field_validator('learning_objectives')
    @classmethod
    def validate_objectives(cls, v):
        if v and len(v) > 10:
            raise ValueError("Maximum 10 learning objectives allowed")
        return v


class GameGenerationResponse(BaseSchema):
    """Response schema for generated games"""
    game_id: UUID
    manifest: Dict[str, Any]
    estimated_duration: PositiveFloat
    actual_generation_time: PositiveFloat
    status: GameStatus
    ai_generated: bool
    fallback_used: bool
    event_emitted: bool
    created_at: datetime


# Game Manifest Schemas
class GameManifestResponse(BaseSchema):
    """Response schema for game manifests"""
    id: UUID
    title: str
    description: str
    game_type: GameType
    subject_area: SubjectArea
    grade_band: GradeBand
    difficulty: GameDifficulty
    estimated_duration: PositiveFloat
    learning_objectives: List[str]
    manifest_data: Dict[str, Any]
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# Learner Profile Schemas
class LearnerProfileRequest(BaseSchema):
    """Request schema for creating/updating learner profiles"""
    learner_id: UUID
    attention_span_minutes: Optional[PositiveInt] = Field(15, description="Average attention span in minutes")
    preferred_subjects: Optional[List[SubjectArea]] = Field(default_factory=list)
    difficulty_preferences: Optional[List[GameDifficulty]] = Field(default_factory=list)
    learning_style: Optional[str] = Field(None, description="Preferred learning approach")
    accessibility_needs: Optional[Dict[str, Any]] = Field(default_factory=dict)
    performance_history: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    @field_validator('attention_span_minutes')
    @classmethod
    def validate_attention_span(cls, v):
        if v is not None and not (1 <= v <= 120):
            raise ValueError("Attention span must be between 1 and 120 minutes")
        return v


class LearnerProfileResponse(BaseSchema):
    """Response schema for learner profiles"""
    id: UUID
    learner_id: UUID
    attention_span_minutes: int
    preferred_subjects: List[SubjectArea]
    difficulty_preferences: List[GameDifficulty]
    learning_style: Optional[str]
    accessibility_needs: Dict[str, Any]
    performance_history: Dict[str, Any]
    created_at: datetime
    updated_at: Optional[datetime] = None


# Game Session Schemas
class GameSessionCreate(BaseSchema):
    """Schema for creating new game sessions"""
    game_id: UUID
    learner_id: UUID
    expected_duration: Optional[PositiveInt] = Field(None, description="Expected session duration in minutes")
    session_context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class GameSessionUpdate(BaseSchema):
    """Schema for updating game sessions"""
    status: Optional[GameStatus] = None
    progress_data: Optional[Dict[str, Any]] = None
    performance_metrics: Optional[Dict[str, Any]] = None
    completion_percentage: Optional[float] = Field(None, ge=0.0, le=100.0)
    actual_duration: Optional[PositiveFloat] = None
    ended_at: Optional[datetime] = None


class GameSessionResponse(BaseSchema):
    """Response schema for game sessions"""
    id: UUID
    game_id: UUID
    learner_id: UUID
    status: GameStatus
    progress_data: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    completion_percentage: float
    expected_duration: Optional[int]
    actual_duration: Optional[float]
    started_at: datetime
    ended_at: Optional[datetime]
    created_at: datetime


# Game Analytics Schemas
class GameAnalyticsResponse(BaseSchema):
    """Response schema for game analytics"""
    id: UUID
    game_id: UUID
    session_id: UUID
    learner_id: UUID
    engagement_score: float
    learning_effectiveness: float
    time_on_task: float
    completion_rate: float
    error_patterns: Dict[str, Any]
    performance_trends: Dict[str, Any]
    recorded_at: datetime


# Template Schemas
class GameTemplateResponse(BaseSchema):
    """Response schema for game templates"""
    id: UUID
    name: str
    game_type: GameType
    subject_area: SubjectArea
    grade_band: GradeBand
    template_data: Dict[str, Any]
    usage_count: int
    effectiveness_rating: float
    created_at: datetime
    updated_at: Optional[datetime] = None


# List and Filter Schemas
class GameListFilter(BaseSchema):
    """Schema for filtering game lists"""
    game_type: Optional[GameType] = None
    subject_area: Optional[SubjectArea] = None
    difficulty: Optional[GameDifficulty] = None
    grade_band: Optional[GradeBand] = None
    status: Optional[GameStatus] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    limit: Optional[int] = Field(10, ge=1, le=100)
    offset: Optional[int] = Field(0, ge=0)


class GameListResponse(BaseSchema):
    """Response schema for paginated game lists"""
    games: List[GameManifestResponse]
    total_count: int
    limit: int
    offset: int
    has_next: bool
    has_previous: bool


# Event Schemas
class GameEventRequest(BaseSchema):
    """Request schema for game events"""
    event_type: str = Field(..., description="Type of event to emit")
    game_id: UUID
    session_id: Optional[UUID] = None
    event_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None


class EventEmissionResponse(BaseSchema):
    """Response schema for event emissions"""
    event_id: str
    event_type: str
    status: str
    emitted_at: datetime
    delivery_confirmed: bool
    error_message: Optional[str] = None


# Validation Schemas
class ValidationResponse(BaseSchema):
    """Response schema for validation operations"""
    is_valid: bool
    validation_errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    validated_at: datetime
    validation_context: Optional[Dict[str, Any]] = None


# Game Completion Schemas  
class GameCompletionRequest(BaseSchema):
    """Request schema for game completion events"""
    session_id: UUID
    game_id: UUID
    learner_id: UUID
    final_score: Optional[float] = Field(None, ge=0.0, le=100.0)
    completion_percentage: float = Field(..., ge=0.0, le=100.0)
    actual_duration: PositiveFloat
    performance_data: Dict[str, Any] = Field(default_factory=dict)
    learning_outcomes: Optional[List[str]] = Field(default_factory=list)
    feedback_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
