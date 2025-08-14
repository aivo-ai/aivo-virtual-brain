# AIVO SEL Service - Pydantic Schemas
# S2-12 Implementation - Request/Response validation for SEL workflows

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, date
from enum import Enum
import uuid

# Import enums from models
from .models import (
    EmotionType, SELDomain, AlertLevel, StrategyType, GradeBand, 
    ConsentStatus, CheckInStatus, AlertStatus
)


# Base schemas for common patterns
class TenantBase(BaseModel):
    tenant_id: uuid.UUID = Field(..., description="Tenant identifier")


class StudentIdentifier(BaseModel):
    student_id: str = Field(..., min_length=1, max_length=100, description="Student identifier")
    student_name: Optional[str] = Field(None, max_length=200, description="Student display name")


# Check-in related schemas
class CheckInRequest(TenantBase, StudentIdentifier):
    """Request schema for creating a new SEL check-in."""
    
    student_name: str = Field(..., min_length=1, max_length=200)
    grade_band: GradeBand = Field(..., description="Student's grade band")
    
    # Core emotional assessment
    primary_emotion: EmotionType = Field(..., description="Primary emotion reported")
    emotion_intensity: int = Field(..., ge=1, le=10, description="Emotion intensity (1-10)")
    secondary_emotions: Optional[List[EmotionType]] = Field(None, description="Additional emotions")
    
    # Contextual information
    triggers: Optional[List[str]] = Field(None, description="Identified triggers")
    current_situation: Optional[str] = Field(None, max_length=1000, description="Current situation description")
    location_context: Optional[str] = Field(None, max_length=100, description="Physical location context")
    social_context: Optional[str] = Field(None, max_length=100, description="Social situation context")
    
    # SEL domain self-ratings
    self_awareness_rating: Optional[int] = Field(None, ge=1, le=10)
    self_management_rating: Optional[int] = Field(None, ge=1, le=10)
    social_awareness_rating: Optional[int] = Field(None, ge=1, le=10)
    relationship_skills_rating: Optional[int] = Field(None, ge=1, le=10)
    decision_making_rating: Optional[int] = Field(None, ge=1, le=10)
    
    # Wellness indicators
    energy_level: Optional[int] = Field(None, ge=1, le=10, description="Energy level (1-10)")
    stress_level: Optional[int] = Field(None, ge=1, le=10, description="Stress level (1-10)")
    confidence_level: Optional[int] = Field(None, ge=1, le=10, description="Confidence level (1-10)")
    support_needed: bool = Field(False, description="Whether student requests support")
    
    # Additional context
    checkin_notes: Optional[str] = Field(None, max_length=2000)
    previous_strategies_used: Optional[List[str]] = Field(None, description="Previously tried strategies")
    strategy_effectiveness: Optional[Dict[str, int]] = Field(None, description="Effectiveness ratings for previous strategies")
    
    @validator('emotion_intensity', 'energy_level', 'stress_level', 'confidence_level')
    def validate_rating_scale(cls, v):
        if v is not None and not (1 <= v <= 10):
            raise ValueError('Rating must be between 1 and 10')
        return v
    
    @validator('secondary_emotions')
    def validate_secondary_emotions(cls, v, values):
        if v and 'primary_emotion' in values and values['primary_emotion'] in v:
            raise ValueError('Primary emotion cannot be listed in secondary emotions')
        return v


class CheckInResponse(BaseModel):
    """Response schema for SEL check-in data."""
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: str
    student_name: str
    grade_band: GradeBand
    
    # Check-in metadata
    checkin_date: datetime
    status: CheckInStatus
    session_duration: Optional[int]
    
    # Emotional assessment
    primary_emotion: EmotionType
    emotion_intensity: int
    secondary_emotions: Optional[List[EmotionType]]
    
    # Context
    triggers: Optional[List[str]]
    current_situation: Optional[str]
    location_context: Optional[str]
    social_context: Optional[str]
    
    # SEL ratings
    self_awareness_rating: Optional[int]
    self_management_rating: Optional[int]
    social_awareness_rating: Optional[int]
    relationship_skills_rating: Optional[int]
    decision_making_rating: Optional[int]
    
    # Wellness indicators
    energy_level: Optional[int]
    stress_level: Optional[int]
    confidence_level: Optional[int]
    support_needed: bool
    
    # Metadata
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Strategy related schemas  
class StrategyRequest(TenantBase):
    """Request schema for getting next SEL strategy."""
    
    student_id: str = Field(..., min_length=1, max_length=100)
    checkin_id: Optional[uuid.UUID] = Field(None, description="Associated check-in ID")
    
    # Strategy preferences
    strategy_type: Optional[StrategyType] = Field(None, description="Preferred strategy type")
    target_emotion: Optional[EmotionType] = Field(None, description="Emotion to address")
    target_domain: Optional[SELDomain] = Field(None, description="SEL domain to focus on")
    difficulty_preference: Optional[str] = Field("adaptive", regex="^(easy|adaptive|challenging)$")
    max_duration: Optional[int] = Field(None, ge=1, le=120, description="Maximum duration in minutes")
    
    # Context for personalization
    current_location: Optional[str] = Field(None, max_length=100)
    available_time: Optional[int] = Field(None, ge=1, le=120, description="Available time in minutes")
    materials_available: Optional[List[str]] = Field(None, description="Available materials/tools")
    support_available: Optional[str] = Field(None, description="Available support (teacher, peer, none)")
    
    class Config:
        use_enum_values = True


class StrategyResponse(BaseModel):
    """Response schema for SEL strategy data."""
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: str
    checkin_id: Optional[uuid.UUID]
    
    # Strategy content
    strategy_type: StrategyType
    strategy_title: str
    strategy_description: str
    instructions: str
    
    # Personalization
    grade_band: GradeBand
    target_emotion: EmotionType
    target_domain: SELDomain
    difficulty_level: int
    
    # Implementation
    estimated_duration: int
    materials_needed: Optional[List[str]]
    step_by_step: List[str]
    success_indicators: Optional[List[str]]
    
    # Multimedia
    video_url: Optional[str]
    audio_url: Optional[str]
    image_urls: Optional[List[str]]
    interactive_elements: Optional[Dict[str, Any]]
    
    # Effectiveness data
    average_rating: Optional[float]
    success_rate: Optional[float]
    times_used: int
    
    # Metadata
    generated_at: datetime
    
    class Config:
        from_attributes = True


class StrategyUsageRequest(BaseModel):
    """Request schema for recording strategy usage."""
    
    strategy_id: uuid.UUID = Field(..., description="Strategy that was used")
    duration_used: Optional[int] = Field(None, ge=1, description="Minutes actually spent using strategy")
    completion_status: str = Field(..., regex="^(completed|partial|abandoned)$")
    
    # Effectiveness measures
    pre_emotion_rating: int = Field(..., ge=1, le=10, description="Emotion rating before strategy")
    post_emotion_rating: int = Field(..., ge=1, le=10, description="Emotion rating after strategy")
    helpfulness_rating: int = Field(..., ge=1, le=10, description="How helpful was the strategy")
    difficulty_rating: Optional[int] = Field(None, ge=1, le=10, description="How difficult was the strategy")
    
    # Feedback
    liked_aspects: Optional[List[str]] = Field(None, description="What the student liked")
    disliked_aspects: Optional[List[str]] = Field(None, description="What the student didn't like")
    suggestions: Optional[str] = Field(None, max_length=1000, description="Student suggestions for improvement")
    would_use_again: Optional[bool] = Field(None, description="Would use this strategy again")
    
    # Context
    usage_context: Optional[str] = Field(None, max_length=100, description="Where/when strategy was used")
    support_received: Optional[str] = Field(None, max_length=100, description="Type of support received")


# Alert related schemas
class AlertResponse(BaseModel):
    """Response schema for SEL alert data."""
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: str
    checkin_id: uuid.UUID
    
    # Alert details
    alert_type: str
    alert_level: AlertLevel
    title: str
    description: str
    
    # Triggering data
    trigger_domain: SELDomain
    trigger_value: float
    threshold_value: float
    risk_score: float
    risk_factors: List[str]
    protective_factors: Optional[List[str]]
    
    # Status
    status: AlertStatus
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[datetime]
    
    # Consent compliance
    consent_verified: bool
    privacy_level: str
    
    # Metadata
    created_at: datetime
    
    class Config:
        from_attributes = True


# Report related schemas
class ReportRequest(TenantBase):
    """Request schema for generating SEL reports."""
    
    student_id: str = Field(..., min_length=1, max_length=100)
    report_type: str = Field(..., regex="^(weekly|monthly|semester|annual|custom)$")
    
    # Time period
    start_date: date = Field(..., description="Report start date")
    end_date: date = Field(..., description="Report end date")
    
    # Report configuration
    report_audience: str = Field("student", regex="^(student|teacher|parent|counselor|administrator)$")
    include_alerts: bool = Field(True, description="Include alert data in report")
    include_strategies: bool = Field(True, description="Include strategy data in report")
    privacy_level: str = Field("standard", regex="^(minimal|standard|detailed)$")
    
    # Content preferences
    include_visualizations: bool = Field(True, description="Include charts and graphs")
    include_narrative: bool = Field(True, description="Include narrative summary")
    highlight_achievements: bool = Field(True, description="Highlight positive achievements")
    
    @validator('end_date')
    def validate_date_range(cls, v, values):
        if 'start_date' in values and v <= values['start_date']:
            raise ValueError('End date must be after start date')
        return v
    
    @validator('start_date', 'end_date')
    def validate_future_dates(cls, v):
        if v > date.today():
            raise ValueError('Report dates cannot be in the future')
        return v


class ReportResponse(BaseModel):
    """Response schema for SEL report data."""
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: str
    
    # Report metadata
    report_type: str
    report_period_start: datetime
    report_period_end: datetime
    generated_for: str
    
    # Summary statistics
    total_checkins: int
    average_emotion_intensity: Optional[float]
    most_common_emotion: Optional[EmotionType]
    trend_direction: Optional[str]
    
    # SEL progress
    domain_scores: Dict[str, float]
    domain_trends: Optional[Dict[str, str]]
    growth_indicators: Optional[List[str]]
    areas_for_support: Optional[List[str]]
    
    # Strategy data
    strategies_used: int
    strategy_success_rate: Optional[float]
    preferred_strategies: Optional[List[str]]
    
    # Alert summary
    total_alerts: int
    alert_trends: Optional[Dict[str, Any]]
    
    # Insights
    key_insights: Optional[List[str]]
    recommendations: Optional[List[str]]
    celebration_points: Optional[List[str]]
    
    # Content
    narrative_summary: Optional[str]
    visualizations: Optional[Dict[str, Any]]
    
    # Privacy
    privacy_level: str
    consent_verified: bool
    
    # Metadata
    generated_at: datetime
    
    class Config:
        from_attributes = True


# Consent related schemas
class ConsentRequest(TenantBase):
    """Request schema for managing consent preferences."""
    
    student_id: str = Field(..., min_length=1, max_length=100)
    consent_type: str = Field(..., description="Type of consent being granted/updated")
    
    # Consent details
    granted_by: str = Field(..., min_length=1, max_length=200, description="Who is granting consent")
    granted_by_role: str = Field(..., regex="^(student|parent|guardian|administrator)$")
    
    # Permissions
    data_sharing_allowed: bool = Field(False, description="Allow data sharing with educators")
    alert_notifications_allowed: bool = Field(False, description="Allow alert notifications")
    counselor_sharing_allowed: bool = Field(False, description="Allow sharing with counselors")
    parent_notification_allowed: bool = Field(False, description="Allow parent notifications")
    research_participation_allowed: bool = Field(False, description="Allow anonymized research participation")
    
    # Alert preferences
    alert_thresholds: Optional[Dict[str, float]] = Field(None, description="Custom alert thresholds")
    notification_methods: Optional[List[str]] = Field(None, description="Preferred notification methods")
    emergency_contacts: Optional[List[Dict[str, str]]] = Field(None, description="Emergency contact information")
    
    # Expiration
    expires_at: Optional[datetime] = Field(None, description="When consent expires")
    
    @validator('expires_at')
    def validate_expiration(cls, v):
        if v and v <= datetime.now():
            raise ValueError('Expiration date must be in the future')
        return v


class ConsentResponse(BaseModel):
    """Response schema for consent record data."""
    
    id: uuid.UUID
    tenant_id: uuid.UUID
    student_id: str
    
    # Consent details
    consent_type: str
    status: ConsentStatus
    granted_by: str
    granted_by_role: str
    
    # Permissions
    data_sharing_allowed: bool
    alert_notifications_allowed: bool
    counselor_sharing_allowed: bool
    parent_notification_allowed: bool
    research_participation_allowed: bool
    
    # Preferences
    alert_thresholds: Optional[Dict[str, float]]
    notification_methods: Optional[List[str]]
    
    # Timeline
    granted_at: datetime
    expires_at: Optional[datetime]
    revoked_at: Optional[datetime]
    
    # Metadata
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Filter and query schemas
class CheckInFilters(BaseModel):
    """Query filters for check-in listing."""
    
    tenant_id: uuid.UUID
    student_id: Optional[str] = None
    grade_band: Optional[GradeBand] = None
    emotion_type: Optional[EmotionType] = None
    min_intensity: Optional[int] = Field(None, ge=1, le=10)
    max_intensity: Optional[int] = Field(None, ge=1, le=10)
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    support_needed: Optional[bool] = None
    status: Optional[CheckInStatus] = None
    
    # Pagination
    page: int = Field(1, ge=1, description="Page number")
    per_page: int = Field(20, ge=1, le=100, description="Items per page")
    
    @validator('max_intensity')
    def validate_intensity_range(cls, v, values):
        if v is not None and 'min_intensity' in values and values['min_intensity'] is not None:
            if v < values['min_intensity']:
                raise ValueError('max_intensity must be greater than or equal to min_intensity')
        return v


class AlertFilters(BaseModel):
    """Query filters for alert listing."""
    
    tenant_id: uuid.UUID
    student_id: Optional[str] = None
    alert_level: Optional[AlertLevel] = None
    status: Optional[AlertStatus] = None
    domain: Optional[SELDomain] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    acknowledged: Optional[bool] = None
    
    # Pagination
    page: int = Field(1, ge=1)
    per_page: int = Field(20, ge=1, le=100)


# Error response schema
class ErrorResponse(BaseModel):
    """Standard error response schema."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


# Success response schema
class SuccessResponse(BaseModel):
    """Standard success response schema."""
    
    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
