# AIVO SLP Service - Pydantic Schemas
# S2-11 Implementation - Request/Response validation schemas

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid

# Re-export enums for API consistency
from .models import ScreeningStatus, TherapyPlanStatus, ExerciseType, SessionStatus


# Request schemas
class ScreeningRequest(BaseModel):
    """Schema for initiating a screening assessment."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    patient_id: str = Field(..., min_length=1, max_length=255, description="Patient identifier")
    patient_name: str = Field(..., min_length=1, max_length=255, description="Patient full name")
    patient_age: int = Field(..., ge=0, le=120, description="Patient age in years")
    date_of_birth: Optional[datetime] = Field(None, description="Patient date of birth")
    assessment_type: str = Field(default="comprehensive", pattern="^(comprehensive|focused)$", description="Type of assessment")
    assessment_data: Dict[str, Any] = Field(..., description="Assessment responses and data")
    
    model_config = ConfigDict(use_enum_values=True)


class TherapyPlanRequest(BaseModel):
    """Schema for creating a therapy plan from screening results."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    screening_id: uuid.UUID = Field(..., description="Associated screening assessment ID")
    plan_name: str = Field(..., min_length=1, max_length=255, description="Therapy plan name")
    priority_level: str = Field(default="medium", pattern="^(low|medium|high|urgent)$", description="Plan priority")
    sessions_per_week: int = Field(default=2, ge=1, le=7, description="Sessions per week")
    session_duration: int = Field(default=30, ge=15, le=120, description="Session duration in minutes")
    estimated_duration_weeks: Optional[int] = Field(None, ge=1, le=52, description="Estimated plan duration")
    custom_goals: Optional[List[str]] = Field(None, description="Custom therapy goals")
    
    model_config = ConfigDict(use_enum_values=True)


class ExerciseRequest(BaseModel):
    """Schema for requesting next exercise in sequence."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    therapy_plan_id: uuid.UUID = Field(..., description="Therapy plan ID")
    session_id: Optional[uuid.UUID] = Field(None, description="Current session ID")
    current_exercise_id: Optional[uuid.UUID] = Field(None, description="Current exercise ID for progression")
    difficulty_adjustment: Optional[int] = Field(None, ge=-3, le=3, description="Difficulty adjustment (-3 to +3)")
    exercise_type: Optional[ExerciseType] = Field(None, description="Specific exercise type requested")
    
    model_config = ConfigDict(use_enum_values=True)


class SessionSubmitRequest(BaseModel):
    """Schema for submitting session results."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    session_id: uuid.UUID = Field(..., description="Session ID")
    exercise_results: List[Dict[str, Any]] = Field(..., description="Results for each exercise")
    session_notes: Optional[str] = Field(None, max_length=2000, description="Session notes")
    actual_duration: Optional[int] = Field(None, ge=1, le=300, description="Actual session duration in minutes")
    audio_recordings: Optional[List[str]] = Field(None, description="Audio file references")
    voice_analysis: Optional[Dict[str, Any]] = Field(None, description="Voice analysis results")
    
    model_config = ConfigDict(use_enum_values=True)


# Response schemas
class ScreeningResponse(BaseModel):
    """Schema for screening assessment response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: str
    patient_name: str
    patient_age: int
    assessment_type: str
    status: str
    scores: Optional[Dict[str, Any]]
    risk_factors: Optional[List[str]]
    recommendations: Optional[List[str]]
    overall_score: Optional[float]
    priority_areas: Optional[List[str]]
    therapy_recommended: Optional[bool]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class TherapyPlanResponse(BaseModel):
    """Schema for therapy plan response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    screening_id: uuid.UUID
    patient_id: str
    plan_name: str
    status: str
    priority_level: str
    goals: List[Dict[str, Any]]
    objectives: List[Dict[str, Any]]
    sessions_per_week: int
    session_duration: int
    estimated_duration_weeks: Optional[int]
    progress_data: Dict[str, Any]
    current_phase: str
    completion_percentage: float
    created_at: datetime
    started_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ExerciseResponse(BaseModel):
    """Schema for exercise instance response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    therapy_plan_id: uuid.UUID
    session_id: Optional[uuid.UUID]
    exercise_type: str
    exercise_name: str
    difficulty_level: int
    sequence_order: int
    instructions: str
    content_data: Dict[str, Any]
    audio_prompts: Optional[Dict[str, Any]]
    expected_responses: Optional[List[str]]
    max_attempts: int
    time_limit_seconds: Optional[int]
    feedback_enabled: bool
    completion_status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class SessionResponse(BaseModel):
    """Schema for exercise session response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    therapy_plan_id: uuid.UUID
    patient_id: str
    session_number: int
    session_type: str
    status: str
    planned_duration: int
    exercise_count: int
    actual_duration: Optional[int]
    exercises_completed: int
    overall_score: Optional[float]
    engagement_score: Optional[float]
    accuracy_rate: Optional[float]
    completion_rate: Optional[float]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class ProgressEventResponse(BaseModel):
    """Schema for progress event response."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    patient_id: str
    event_type: str
    event_source: str
    source_id: uuid.UUID
    event_data: Dict[str, Any]
    new_state: Dict[str, Any]
    triggered_by: Optional[str]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# Assessment domain schemas
class AssessmentDomain(BaseModel):
    """Schema for assessment domain results."""
    domain_name: str = Field(..., description="Domain name (e.g., 'articulation', 'fluency')")
    raw_score: float = Field(..., description="Raw domain score")
    percentile: Optional[float] = Field(None, description="Percentile ranking")
    severity_level: str = Field(..., description="Severity level (normal, mild, moderate, severe)")
    recommendations: List[str] = Field(default_factory=list, description="Domain-specific recommendations")
    
    model_config = ConfigDict(use_enum_values=True)


class TherapyGoal(BaseModel):
    """Schema for therapy goals."""
    goal_id: str = Field(..., description="Unique goal identifier")
    goal_text: str = Field(..., description="Goal description")
    target_domain: str = Field(..., description="Target SLP domain")
    priority: str = Field(..., pattern="^(high|medium|low)$", description="Goal priority")
    measurable_criteria: List[str] = Field(..., description="Measurable success criteria")
    estimated_sessions: int = Field(..., ge=1, description="Estimated sessions to achieve goal")
    
    model_config = ConfigDict(use_enum_values=True)


class ExerciseContent(BaseModel):
    """Schema for exercise content generation."""
    content_type: str = Field(..., description="Type of content (text, audio, visual)")
    content_data: Dict[str, Any] = Field(..., description="Content-specific data")
    difficulty_indicators: Dict[str, float] = Field(..., description="Difficulty metrics")
    adaptation_hints: List[str] = Field(default_factory=list, description="Adaptation suggestions")
    
    model_config = ConfigDict(use_enum_values=True)


# Voice/Audio configuration schemas
class VoiceConfig(BaseModel):
    """Schema for voice and audio configuration."""
    tts_provider: str = Field(default="default", description="Text-to-speech provider")
    tts_voice: str = Field(default="neutral", description="TTS voice selection")
    tts_speed: float = Field(default=1.0, ge=0.5, le=2.0, description="TTS speed multiplier")
    asr_provider: str = Field(default="default", description="Automatic speech recognition provider")
    asr_model: str = Field(default="general", description="ASR model selection")
    recording_quality: str = Field(default="standard", pattern="^(low|standard|high)$", description="Recording quality")
    
    model_config = ConfigDict(use_enum_values=True)


# Filter and query schemas
class ScreeningFilters(BaseModel):
    """Schema for screening assessment filtering."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    status: Optional[ScreeningStatus] = Field(None, description="Filter by status")
    assessment_type: Optional[str] = Field(None, description="Filter by assessment type")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    model_config = ConfigDict(use_enum_values=True)


class TherapyPlanFilters(BaseModel):
    """Schema for therapy plan filtering."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID")
    patient_id: Optional[str] = Field(None, description="Filter by patient ID")
    status: Optional[TherapyPlanStatus] = Field(None, description="Filter by status")
    priority_level: Optional[str] = Field(None, description="Filter by priority")
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number")
    per_page: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    model_config = ConfigDict(use_enum_values=True)


# Error response schema
class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(use_enum_values=True)
