# AIVO SLP Service - Data Models
# S2-11 Implementation - Speech & Language Pathology workflow models

from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, Float, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from enum import Enum

Base = declarative_base()


class ScreeningStatus(Enum):
    """Screening assessment status."""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TherapyPlanStatus(Enum):
    """Therapy plan status."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class ExerciseType(Enum):
    """Types of SLP exercises."""
    ARTICULATION = "articulation"
    FLUENCY = "fluency"
    LANGUAGE = "language"
    VOICE = "voice"
    COMPREHENSION = "comprehension"
    PHONOLOGICAL = "phonological"


class SessionStatus(Enum):
    """Session status."""
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class ScreeningAssessment(Base):
    """
    Screening assessment for speech and language pathology.
    Evaluates various SLP domains to generate therapy recommendations.
    """
    __tablename__ = "screening_assessments"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    patient_id = Column(String(255), nullable=False, index=True)
    
    # Assessment metadata
    assessment_type = Column(String(100), nullable=False, default="comprehensive")  # comprehensive, focused
    status = Column(String(50), nullable=False, default=ScreeningStatus.IN_PROGRESS.value)
    
    # Patient information
    patient_name = Column(String(255), nullable=False)
    patient_age = Column(Integer, nullable=False)
    date_of_birth = Column(DateTime(timezone=True), nullable=True)
    
    # Assessment data
    assessment_data = Column(JSON, nullable=False, default=dict)  # Raw assessment responses
    scores = Column(JSON, nullable=True)  # Calculated scores by domain
    risk_factors = Column(JSON, nullable=True)  # Identified risk factors
    recommendations = Column(JSON, nullable=True)  # Generated recommendations
    
    # Assessment results
    overall_score = Column(Float, nullable=True)
    priority_areas = Column(JSON, nullable=True)  # Areas needing immediate attention
    therapy_recommended = Column(Boolean, nullable=True)
    
    # Workflow tracking
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    therapy_plans = relationship("TherapyPlan", back_populates="screening", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ScreeningAssessment(id={self.id}, patient={self.patient_name}, status={self.status})>"


class TherapyPlan(Base):
    """
    Individualized therapy plan based on screening assessment.
    Defines goals, objectives, and exercise sequences.
    """
    __tablename__ = "therapy_plans"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    screening_id = Column(UUID(as_uuid=True), ForeignKey("screening_assessments.id"), nullable=False)
    patient_id = Column(String(255), nullable=False, index=True)
    
    # Plan metadata
    plan_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False, default=TherapyPlanStatus.ACTIVE.value)
    priority_level = Column(String(50), nullable=False, default="medium")  # low, medium, high, urgent
    
    # Plan structure
    goals = Column(JSON, nullable=False)  # Long-term therapy goals
    objectives = Column(JSON, nullable=False)  # Short-term measurable objectives
    exercise_sequence = Column(JSON, nullable=False)  # Ordered sequence of exercises
    
    # Plan configuration
    sessions_per_week = Column(Integer, nullable=False, default=2)
    session_duration = Column(Integer, nullable=False, default=30)  # minutes
    estimated_duration_weeks = Column(Integer, nullable=True)
    
    # Progress tracking
    progress_data = Column(JSON, nullable=False, default=dict)
    current_phase = Column(String(100), nullable=False, default="initial")
    completion_percentage = Column(Float, nullable=False, default=0.0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    screening = relationship("ScreeningAssessment", back_populates="therapy_plans")
    sessions = relationship("ExerciseSession", back_populates="therapy_plan", cascade="all, delete-orphan")
    exercises = relationship("ExerciseInstance", back_populates="therapy_plan", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<TherapyPlan(id={self.id}, name={self.plan_name}, status={self.status})>"


class ExerciseInstance(Base):
    """
    Individual exercise instance within a therapy plan.
    Generated dynamically based on patient progress and needs.
    """
    __tablename__ = "exercise_instances"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    therapy_plan_id = Column(UUID(as_uuid=True), ForeignKey("therapy_plans.id"), nullable=False)
    session_id = Column(UUID(as_uuid=True), ForeignKey("exercise_sessions.id"), nullable=True)
    
    # Exercise metadata
    exercise_type = Column(String(50), nullable=False)  # From ExerciseType enum
    exercise_name = Column(String(255), nullable=False)
    difficulty_level = Column(Integer, nullable=False, default=1)  # 1-10 scale
    sequence_order = Column(Integer, nullable=False)
    
    # Exercise content
    instructions = Column(Text, nullable=False)
    content_data = Column(JSON, nullable=False)  # Exercise-specific content
    audio_prompts = Column(JSON, nullable=True)  # TTS/audio configuration
    expected_responses = Column(JSON, nullable=True)  # For assessment
    
    # Configuration
    max_attempts = Column(Integer, nullable=False, default=3)
    time_limit_seconds = Column(Integer, nullable=True)
    feedback_enabled = Column(Boolean, nullable=False, default=True)
    
    # Results tracking
    attempts = Column(JSON, nullable=False, default=list)
    best_score = Column(Float, nullable=True)
    completion_status = Column(String(50), nullable=False, default="pending")  # pending, completed, skipped
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    therapy_plan = relationship("TherapyPlan", back_populates="exercises")
    session = relationship("ExerciseSession", back_populates="exercises")
    
    def __repr__(self):
        return f"<ExerciseInstance(id={self.id}, type={self.exercise_type}, name={self.exercise_name})>"


class ExerciseSession(Base):
    """
    Therapy session containing multiple exercises.
    Tracks session-level progress and performance.
    """
    __tablename__ = "exercise_sessions"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    therapy_plan_id = Column(UUID(as_uuid=True), ForeignKey("therapy_plans.id"), nullable=False)
    patient_id = Column(String(255), nullable=False, index=True)
    
    # Session metadata
    session_number = Column(Integer, nullable=False)
    session_type = Column(String(100), nullable=False, default="regular")  # regular, assessment, review
    status = Column(String(50), nullable=False, default=SessionStatus.ACTIVE.value)
    
    # Session configuration
    planned_duration = Column(Integer, nullable=False, default=30)  # minutes
    exercise_count = Column(Integer, nullable=False, default=0)
    
    # Session results
    actual_duration = Column(Integer, nullable=True)  # minutes
    exercises_completed = Column(Integer, nullable=False, default=0)
    overall_score = Column(Float, nullable=True)
    session_notes = Column(Text, nullable=True)
    
    # Performance metrics
    engagement_score = Column(Float, nullable=True)  # 0.0-1.0
    accuracy_rate = Column(Float, nullable=True)
    completion_rate = Column(Float, nullable=True)
    
    # Voice/audio data
    audio_recordings = Column(JSON, nullable=True)  # Audio file references
    voice_analysis = Column(JSON, nullable=True)  # Voice quality metrics
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    therapy_plan = relationship("TherapyPlan", back_populates="sessions")
    exercises = relationship("ExerciseInstance", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ExerciseSession(id={self.id}, session_number={self.session_number}, status={self.status})>"


class ProgressEvent(Base):
    """
    Progress events emitted during SLP workflows.
    Tracks significant milestones and updates.
    """
    __tablename__ = "progress_events"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    patient_id = Column(String(255), nullable=False, index=True)
    
    # Event metadata
    event_type = Column(String(100), nullable=False)  # SLP_SCREENING_COMPLETE, SLP_PLAN_UPDATED, etc.
    event_source = Column(String(100), nullable=False)  # screening, therapy_plan, exercise, session
    source_id = Column(UUID(as_uuid=True), nullable=False)
    
    # Event data
    event_data = Column(JSON, nullable=False)
    previous_state = Column(JSON, nullable=True)
    new_state = Column(JSON, nullable=False)
    
    # Event context
    triggered_by = Column(String(255), nullable=True)  # User or system that triggered the event
    context_data = Column(JSON, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ProgressEvent(id={self.id}, type={self.event_type}, source={self.event_source})>"
