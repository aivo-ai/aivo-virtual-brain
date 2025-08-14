# AIVO Assessment Service - Pydantic Schemas
# S1-10 Implementation - Request/Response Models

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
import uuid

class AssessmentTypeSchema(str, Enum):
    """Assessment type enumeration."""
    BASELINE = "baseline"
    ADAPTIVE = "adaptive"
    DIAGNOSTIC = "diagnostic"

class AssessmentStatusSchema(str, Enum):
    """Assessment status enumeration."""
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SubjectLevelSchema(str, Enum):
    """Subject proficiency levels."""
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"

# Request Schemas
class BaselineStartRequest(BaseModel):
    """Request to start a baseline assessment."""
    learner_id: str = Field(..., min_length=1, max_length=100, description="Learner identifier")
    tenant_id: str = Field(..., min_length=1, max_length=100, description="Tenant identifier") 
    subject: str = Field(..., min_length=1, max_length=50, description="Assessment subject (math, reading, etc.)")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional session metadata")
    
    @validator('subject')
    def validate_subject(cls, v):
        """Validate subject format."""
        allowed_subjects = ["math", "reading", "science", "social_studies", "language_arts"]
        if v.lower() not in allowed_subjects:
            raise ValueError(f"Subject must be one of: {', '.join(allowed_subjects)}")
        return v.lower()

class BaselineAnswerRequest(BaseModel):
    """Request to submit an answer during baseline assessment."""
    session_id: str = Field(..., description="Assessment session ID")
    question_id: str = Field(..., description="Question identifier") 
    user_answer: str = Field(..., min_length=1, max_length=500, description="User's answer")
    response_time_ms: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional response metadata")

# Response Schemas
class QuestionResponse(BaseModel):
    """Question data for assessment."""
    id: str
    content: str
    question_type: str
    options: Optional[List[str]] = None
    estimated_time_seconds: int
    metadata: Optional[Dict[str, Any]] = {}
    
    class Config:
        from_attributes = True

class BaselineStartResponse(BaseModel):
    """Response from starting a baseline assessment."""
    session_id: str
    status: AssessmentStatusSchema
    subject: str
    first_question: QuestionResponse
    session_metadata: Dict[str, Any]
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class BaselineAnswerResponse(BaseModel):
    """Response after submitting an answer."""
    session_id: str
    question_answered: bool
    is_correct: bool
    next_question: Optional[QuestionResponse] = None
    assessment_complete: bool
    progress: Dict[str, Any]
    
    class Config:
        from_attributes = True

class AssessmentProgress(BaseModel):
    """Assessment progress information."""
    questions_answered: int
    total_questions: int
    current_theta: float
    standard_error: float
    estimated_completion: Optional[int] = None  # Estimated questions remaining
    
class BaselineResultResponse(BaseModel):
    """Final baseline assessment results."""
    session_id: str
    learner_id: str
    subject: str
    status: AssessmentStatusSchema
    
    # IRT Results
    final_theta: float = Field(..., description="Final ability estimate (IRT theta)")
    standard_error: float = Field(..., description="Standard error of measurement")
    reliability: Optional[float] = Field(None, description="Assessment reliability")
    
    # Level mapping
    proficiency_level: SubjectLevelSchema = Field(..., description="Mapped proficiency level (L0-L4)")
    level_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in level assignment")
    
    # Performance metrics
    total_questions: int
    correct_answers: int
    accuracy_percentage: float
    average_response_time_ms: Optional[int]
    
    # Detailed analysis
    strengths: List[str] = Field(default=[], description="Areas of strength")
    weaknesses: List[str] = Field(default=[], description="Areas needing improvement")  
    recommendations: List[str] = Field(default=[], description="Learning recommendations")
    
    # Timestamps
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True

class AssessmentSessionResponse(BaseModel):
    """Assessment session information."""
    id: str
    learner_id: str
    tenant_id: str
    assessment_type: AssessmentTypeSchema
    subject: str
    status: AssessmentStatusSchema
    
    # Progress info
    current_theta: float
    standard_error: float
    progress: AssessmentProgress
    
    # Timestamps
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Event Schemas
class BaselineCompleteEvent(BaseModel):
    """Event payload for baseline completion."""
    event_type: str = "BASELINE_COMPLETE"
    learner_id: str
    tenant_id: str
    subject: str
    proficiency_level: SubjectLevelSchema  # L0, L1, L2, L3, L4
    final_theta: float
    standard_error: float
    accuracy_percentage: float
    total_questions: int
    correct_answers: int
    session_id: str
    completed_at: datetime
    metadata: Optional[Dict[str, Any]] = {}

# Assessment Status Schemas
class AssessmentSessionSummary(BaseModel):
    """Summary view of an assessment session."""
    id: str
    subject: str
    status: str
    questions_answered: int
    current_theta: float
    standard_error: float
    proficiency_level: Optional[str] = None
    accuracy_percentage: Optional[float] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class AssessmentSessionListResponse(BaseModel):
    """Paginated list of assessment sessions."""
    sessions: List[AssessmentSessionSummary]
    total_count: int
    limit: int
    offset: int
    has_more: bool

class AssessmentSessionResponse(BaseModel):
    """Detailed assessment session information."""
    id: str
    learner_id: str
    tenant_id: str
    subject: str
    assessment_type: str
    status: str
    current_theta: float
    standard_error: float
    questions_answered: int
    correct_answers: int
    proficiency_level: Optional[str] = None
    level_confidence: Optional[float] = None
    accuracy_percentage: Optional[float] = None
    reliability: Optional[float] = None
    strengths: List[str] = []
    weaknesses: List[str] = []
    recommendations: List[str] = []
    response_statistics: Optional[Dict[str, Any]] = None
    progress_metrics: Dict[str, Any] = {}
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

# Error Schemas
class AssessmentError(BaseModel):
    """Standard error response."""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationError(AssessmentError):
    """Validation error response."""
    error: str = "validation_error"
    field_errors: Optional[List[Dict[str, str]]] = None

# Adaptive Assessment Schemas (S2-08)
class AdaptiveStartRequest(BaseModel):
    """Request to start an adaptive assessment session."""
    learner_id: str = Field(..., min_length=1, max_length=100, description="Learner identifier")
    tenant_id: str = Field(..., min_length=1, max_length=100, description="Tenant identifier")
    subject: str = Field(..., min_length=1, max_length=50, description="Assessment subject")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional session metadata")
    
    @validator('subject')
    def validate_subject(cls, v):
        allowed_subjects = ["math", "reading", "science", "social_studies", "language_arts"]
        if v.lower() not in allowed_subjects:
            raise ValueError(f"Subject must be one of: {', '.join(allowed_subjects)}")
        return v.lower()

class AdaptiveStartResponse(BaseModel):
    """Response when starting an adaptive assessment."""
    session_id: str = Field(..., description="Assessment session ID")
    status: str = Field(..., description="Session status")
    current_theta: float = Field(..., description="Initial ability estimate")
    standard_error: float = Field(..., description="Standard error of ability estimate")
    questions_answered: int = Field(..., description="Number of questions answered so far")
    first_question: Optional[Dict[str, Any]] = Field(None, description="First question to answer")
    estimated_total_questions: int = Field(..., description="Estimated total questions needed")
    message: str = Field(..., description="Status message")

class AdaptiveAnswerRequest(BaseModel):
    """Request to submit an answer in adaptive assessment."""
    session_id: str = Field(..., description="Assessment session ID")
    question_id: str = Field(..., description="Question ID being answered")
    user_answer: str = Field(..., min_length=1, description="User's answer")
    response_time_ms: Optional[int] = Field(None, ge=0, description="Response time in milliseconds")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional response metadata")

class AdaptiveAnswerResponse(BaseModel):
    """Response after submitting an answer."""
    session_id: str = Field(..., description="Assessment session ID")
    is_correct: bool = Field(..., description="Whether the answer was correct")
    updated_theta: float = Field(..., description="Updated ability estimate")
    standard_error: float = Field(..., description="Current standard error")
    questions_answered: int = Field(..., description="Total questions answered")
    assessment_complete: bool = Field(..., description="Whether assessment is complete")
    next_question: Optional[Dict[str, Any]] = Field(None, description="Next question if continuing")
    stopping_reason: Optional[str] = Field(None, description="Reason for stopping if complete")
    message: str = Field(..., description="Status message")

class NextQuestionResponse(BaseModel):
    """Response when requesting next question."""
    session_id: str = Field(..., description="Assessment session ID")
    question: Optional[Dict[str, Any]] = Field(None, description="Next question data")
    current_theta: float = Field(..., description="Current ability estimate")
    standard_error: float = Field(..., description="Current standard error")
    questions_answered: int = Field(..., description="Questions answered so far")
    has_next_question: bool = Field(..., description="Whether next question is available")
    message: str = Field(..., description="Status message")

class AssessmentReportResponse(BaseModel):
    """Comprehensive assessment report response."""
    session_id: str = Field(..., description="Assessment session ID")
    learner_id: str = Field(..., description="Learner identifier")
    subject: str = Field(..., description="Assessment subject")
    assessment_type: str = Field(..., description="Type of assessment")
    status: str = Field(..., description="Assessment status")
    
    # IRT Results
    final_theta: float = Field(..., description="Final ability estimate")
    standard_error: float = Field(..., description="Final standard error")
    reliability: Optional[float] = Field(None, description="Assessment reliability")
    
    # Level Mapping
    proficiency_level: str = Field(..., description="Proficiency level (L0-L4)")
    level_confidence: float = Field(..., description="Confidence in level assignment")
    
    # Performance Metrics
    total_questions: int = Field(..., description="Total questions answered")
    correct_answers: int = Field(..., description="Number of correct answers")
    accuracy_percentage: float = Field(..., description="Accuracy as percentage")
    average_response_time_ms: Optional[int] = Field(None, description="Average response time")
    
    # Detailed Results
    strengths: List[str] = Field(default=[], description="Identified strengths")
    weaknesses: List[str] = Field(default=[], description="Areas for improvement")
    recommendations: List[str] = Field(default=[], description="Learning recommendations")
    
    # Session Timeline
    theta_history: List[float] = Field(default=[], description="History of theta estimates")
    response_history: List[Dict[str, Any]] = Field(default=[], description="Detailed response history")
    
    # Timestamps
    started_at: Optional[datetime] = Field(None, description="Assessment start time")
    completed_at: Optional[datetime] = Field(None, description="Assessment completion time")
    total_time_minutes: Optional[float] = Field(None, description="Total assessment time in minutes")

# Item Calibration Schemas (Admin)
class ItemResponseData(BaseModel):
    """Individual response data for item calibration."""
    theta: float = Field(..., description="Ability level of respondent")
    is_correct: bool = Field(..., description="Whether response was correct")
    response_time_ms: Optional[int] = Field(None, description="Response time")

class ItemCalibrationData(BaseModel):
    """Calibration data for a single item."""
    item_id: str = Field(..., description="Item/question identifier")
    responses: List[ItemResponseData] = Field(..., min_items=10, description="Response data for calibration")

class ItemCalibrationRequest(BaseModel):
    """Request to calibrate item parameters."""
    items: List[ItemCalibrationData] = Field(..., min_items=1, description="Items to calibrate")
    calibration_method: str = Field("mle", description="Calibration method (mle, bayes)")
    
class ItemCalibrationResponse(BaseModel):
    """Response from item calibration."""
    calibrated_items: int = Field(..., description="Number of successfully calibrated items")
    failed_items: List[Dict[str, str]] = Field(default=[], description="Items that failed calibration")
    message: str = Field(..., description="Status message")

# Error Response
class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
