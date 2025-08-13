# AIVO Assessment Service - Data Models  
# S1-10 Implementation - IRT-Ready Baseline Assessment

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid
import enum

class AssessmentType(enum.Enum):
    """Types of assessments supported."""
    BASELINE = "baseline"
    ADAPTIVE = "adaptive" 
    DIAGNOSTIC = "diagnostic"

class AssessmentStatus(enum.Enum):
    """Assessment session status."""
    CREATED = "created"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class SubjectLevel(enum.Enum):
    """Subject proficiency levels (L0-L4 mapping)."""
    L0_BEGINNER = "L0"
    L1_ELEMENTARY = "L1"  
    L2_INTERMEDIATE = "L2"
    L3_ADVANCED = "L3"
    L4_EXPERT = "L4"

class AssessmentSession(Base):
    """Assessment session tracking."""
    __tablename__ = "assessment_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    learner_id = Column(String, nullable=False, index=True)
    tenant_id = Column(String, nullable=False, index=True)
    assessment_type = Column(String, nullable=False, default=AssessmentType.BASELINE.value)
    subject = Column(String, nullable=False, index=True)  # math, reading, science, etc.
    status = Column(String, nullable=False, default=AssessmentStatus.CREATED.value)
    
    # IRT Parameters  
    current_theta = Column(Float, default=0.0)  # Current ability estimate
    theta_history = Column(JSON, default=list)  # History of theta estimates
    standard_error = Column(Float, default=1.0)  # Standard error of measurement
    
    # Session metadata
    total_questions = Column(Integer, default=0)
    questions_answered = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    session_data = Column(JSON, default=dict)  # Flexible session data
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    responses = relationship("AssessmentResponse", back_populates="session", cascade="all, delete-orphan")
    result = relationship("AssessmentResult", back_populates="session", uselist=False)

class QuestionBank(Base):
    """Question bank with IRT parameters."""
    __tablename__ = "question_bank"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    subject = Column(String, nullable=False, index=True)
    question_type = Column(String, nullable=False)  # multiple_choice, fill_blank, etc.
    content = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # For multiple choice questions
    correct_answer = Column(String, nullable=False)
    
    # IRT Parameters (Item Response Theory)
    difficulty = Column(Float, nullable=False, default=0.0)  # b parameter
    discrimination = Column(Float, nullable=False, default=1.0)  # a parameter  
    guessing = Column(Float, nullable=False, default=0.0)  # c parameter
    
    # Metadata
    tags = Column(JSON, default=list)  # Question tags/categories
    estimated_time_seconds = Column(Integer, default=60)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class AssessmentResponse(Base):
    """Individual question responses."""
    __tablename__ = "assessment_responses"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("assessment_sessions.id"), nullable=False)
    question_id = Column(String, ForeignKey("question_bank.id"), nullable=False)
    
    # Response data
    user_answer = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    
    # IRT calculations
    theta_before = Column(Float, nullable=True)  # Ability estimate before this question
    theta_after = Column(Float, nullable=True)   # Ability estimate after this question
    information_value = Column(Float, nullable=True)  # Information contribution
    
    # Metadata
    question_order = Column(Integer, nullable=False)
    response_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    session = relationship("AssessmentSession", back_populates="responses")
    question = relationship("QuestionBank")

class AssessmentResult(Base):
    """Final assessment results and level mapping."""
    __tablename__ = "assessment_results"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, ForeignKey("assessment_sessions.id"), nullable=False, unique=True)
    learner_id = Column(String, nullable=False, index=True)
    subject = Column(String, nullable=False, index=True)
    
    # Final IRT results
    final_theta = Column(Float, nullable=False)  # Final ability estimate
    standard_error = Column(Float, nullable=False)  # Final standard error
    reliability = Column(Float, nullable=True)  # Assessment reliability
    
    # Level mapping (L0-L4)
    proficiency_level = Column(String, nullable=False)  # L0, L1, L2, L3, L4
    level_confidence = Column(Float, nullable=False, default=0.0)  # Confidence in level assignment
    
    # Performance metrics
    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    accuracy_percentage = Column(Float, nullable=False)
    average_response_time_ms = Column(Integer, nullable=True)
    
    # Detailed results
    strengths = Column(JSON, default=list)  # Areas of strength
    weaknesses = Column(JSON, default=list)  # Areas needing improvement
    recommendations = Column(JSON, default=list)  # Learning recommendations
    
    # Event tracking
    event_published = Column(Boolean, default=False)
    event_published_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    session = relationship("AssessmentSession", back_populates="result")
