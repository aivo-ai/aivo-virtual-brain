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
