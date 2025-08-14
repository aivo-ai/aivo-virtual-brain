"""
Analytics Service - Data Models (S2-15)
SQLAlchemy models for anonymized aggregates and metrics storage
"""
import enum
from datetime import datetime, date
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from decimal import Decimal

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Date, Boolean, 
    Text, JSON, Enum, Index, UniqueConstraint, CheckConstraint,
    ForeignKey, Numeric
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field, ConfigDict

Base = declarative_base()


class AggregationLevel(enum.Enum):
    """Levels of data aggregation for privacy."""
    INDIVIDUAL = "individual"      # Single learner (high privacy requirements)
    COHORT = "cohort"             # Small group (10-100 learners)
    TENANT = "tenant"             # Organization level
    GLOBAL = "global"             # Cross-tenant aggregates


class MetricType(enum.Enum):
    """Types of analytics metrics."""
    SESSION_DURATION = "session_duration"
    MASTERY_SCORE = "mastery_score"
    WEEKLY_ACTIVE = "weekly_active"
    IEP_PROGRESS = "iep_progress"
    ENGAGEMENT_RATE = "engagement_rate"
    COMPLETION_RATE = "completion_rate"


class PrivacyLevel(enum.Enum):
    """Privacy protection levels."""
    NONE = "none"                 # No privacy protection
    ANONYMIZED = "anonymized"     # PII removed, aggregated
    DP_LOW = "dp_low"            # Low differential privacy noise
    DP_MEDIUM = "dp_medium"      # Medium differential privacy noise
    DP_HIGH = "dp_high"          # High differential privacy noise


# === Database Models ===

class SessionAggregate(Base):
    """Aggregated session duration metrics."""
    __tablename__ = "session_aggregates"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    learner_id_hash = Column(String(64), nullable=True, index=True)  # Hashed for privacy
    date_bucket = Column(Date, nullable=False, index=True)
    
    # Aggregated metrics
    total_sessions = Column(Integer, nullable=False)
    avg_duration_minutes = Column(Float, nullable=False)
    median_duration_minutes = Column(Float, nullable=False)
    max_duration_minutes = Column(Float, nullable=False)
    total_duration_minutes = Column(Float, nullable=False)
    
    # Privacy and metadata
    aggregation_level = Column(Enum(AggregationLevel), nullable=False)
    privacy_level = Column(Enum(PrivacyLevel), nullable=False)
    noise_epsilon = Column(Float, nullable=True)  # DP privacy budget
    cohort_size = Column(Integer, nullable=True)  # For k-anonymity
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_session_agg_tenant_date", "tenant_id", "date_bucket"),
        Index("ix_session_agg_learner_date", "learner_id_hash", "date_bucket"),
        UniqueConstraint("tenant_id", "learner_id_hash", "date_bucket", "aggregation_level",
                        name="uq_session_agg_unique"),
        CheckConstraint("total_sessions >= 0", name="ck_session_total_positive"),
        CheckConstraint("avg_duration_minutes >= 0", name="ck_session_avg_positive"),
    )


class MasteryAggregate(Base):
    """Aggregated mastery scores per subject."""
    __tablename__ = "mastery_aggregates"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    learner_id_hash = Column(String(64), nullable=True, index=True)
    subject_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    date_bucket = Column(Date, nullable=False, index=True)
    
    # Mastery metrics
    current_mastery_score = Column(Numeric(5, 4), nullable=False)  # 0.0000 to 1.0000
    avg_mastery_score = Column(Numeric(5, 4), nullable=False)
    mastery_improvement = Column(Numeric(6, 4), nullable=True)     # Can be negative
    assessments_completed = Column(Integer, nullable=False)
    time_to_mastery_hours = Column(Float, nullable=True)
    
    # Subject details (anonymized)
    subject_category = Column(String(100), nullable=True)
    difficulty_level = Column(Integer, nullable=True)  # 1-5 scale
    
    # Privacy and metadata
    aggregation_level = Column(Enum(AggregationLevel), nullable=False)
    privacy_level = Column(Enum(PrivacyLevel), nullable=False)
    noise_epsilon = Column(Float, nullable=True)
    cohort_size = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_mastery_agg_tenant_subject", "tenant_id", "subject_id"),
        Index("ix_mastery_agg_learner_subject", "learner_id_hash", "subject_id"),
        UniqueConstraint("tenant_id", "learner_id_hash", "subject_id", "date_bucket",
                        name="uq_mastery_agg_unique"),
        CheckConstraint("current_mastery_score >= 0 AND current_mastery_score <= 1",
                       name="ck_mastery_score_range"),
        CheckConstraint("assessments_completed >= 0", name="ck_assessments_positive"),
    )


class WeeklyActiveAggregate(Base):
    """Weekly active learners aggregates."""
    __tablename__ = "weekly_active_aggregates"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    week_start_date = Column(Date, nullable=False, index=True)
    
    # Activity metrics
    total_active_learners = Column(Integer, nullable=False)
    new_learners = Column(Integer, nullable=False)
    returning_learners = Column(Integer, nullable=False)
    churned_learners = Column(Integer, nullable=False)
    
    # Engagement metrics
    avg_sessions_per_learner = Column(Float, nullable=False)
    avg_time_per_learner_minutes = Column(Float, nullable=False)
    engagement_rate = Column(Numeric(5, 4), nullable=False)  # % of enrolled learners active
    
    # Demographics (aggregated, no PII)
    age_distribution = Column(JSON, nullable=True)  # {"18-25": 45, "26-35": 32, ...}
    grade_distribution = Column(JSON, nullable=True)
    special_needs_percentage = Column(Float, nullable=True)
    
    # Privacy and metadata
    aggregation_level = Column(Enum(AggregationLevel), nullable=False)
    privacy_level = Column(Enum(PrivacyLevel), nullable=False)
    noise_epsilon = Column(Float, nullable=True)
    total_population = Column(Integer, nullable=False)  # Base population for percentages
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_weekly_active_tenant_week", "tenant_id", "week_start_date"),
        UniqueConstraint("tenant_id", "week_start_date", name="uq_weekly_active_unique"),
        CheckConstraint("total_active_learners >= 0", name="ck_weekly_active_positive"),
        CheckConstraint("engagement_rate >= 0 AND engagement_rate <= 1",
                       name="ck_engagement_rate_range"),
    )


class IEPProgressAggregate(Base):
    """IEP (Individualized Education Program) progress tracking aggregates."""
    __tablename__ = "iep_progress_aggregates"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    learner_id_hash = Column(String(64), nullable=True, index=True)
    iep_goal_category = Column(String(100), nullable=False, index=True)  # Anonymized category
    date_bucket = Column(Date, nullable=False, index=True)
    
    # IEP Progress metrics
    baseline_score = Column(Numeric(5, 2), nullable=False)
    current_score = Column(Numeric(5, 2), nullable=False)
    target_score = Column(Numeric(5, 2), nullable=False)
    progress_delta = Column(Numeric(5, 2), nullable=False)
    progress_percentage = Column(Numeric(5, 4), nullable=False)  # % toward goal
    
    # Timeline metrics
    days_since_baseline = Column(Integer, nullable=False)
    projected_days_to_goal = Column(Integer, nullable=True)
    is_on_track = Column(Boolean, nullable=False)
    
    # Intervention tracking
    accommodations_used = Column(JSON, nullable=True)  # ["audio", "extended_time", ...]
    intervention_count = Column(Integer, nullable=False, default=0)
    support_level = Column(String(20), nullable=True)  # "minimal", "moderate", "intensive"
    
    # Privacy and metadata
    aggregation_level = Column(Enum(AggregationLevel), nullable=False)
    privacy_level = Column(Enum(PrivacyLevel), nullable=False)
    noise_epsilon = Column(Float, nullable=True)
    cohort_size = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_iep_agg_tenant_category", "tenant_id", "iep_goal_category"),
        Index("ix_iep_agg_learner_category", "learner_id_hash", "iep_goal_category"),
        UniqueConstraint("tenant_id", "learner_id_hash", "iep_goal_category", "date_bucket",
                        name="uq_iep_agg_unique"),
        CheckConstraint("progress_percentage >= 0", name="ck_iep_progress_positive"),
        CheckConstraint("days_since_baseline >= 0", name="ck_iep_days_positive"),
    )


class ETLJobRun(Base):
    """ETL job execution tracking."""
    __tablename__ = "etl_job_runs"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_name = Column(String(100), nullable=False, index=True)
    job_type = Column(Enum(MetricType), nullable=False)
    
    # Execution details
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # "running", "completed", "failed"
    error_message = Column(Text, nullable=True)
    
    # Processing statistics
    records_processed = Column(Integer, nullable=False, default=0)
    records_created = Column(Integer, nullable=False, default=0)
    records_updated = Column(Integer, nullable=False, default=0)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Privacy configuration
    privacy_level_used = Column(Enum(PrivacyLevel), nullable=False)
    epsilon_budget_used = Column(Float, nullable=True)
    
    # Data range
    data_start_date = Column(Date, nullable=True)
    data_end_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index("ix_etl_job_name_status", "job_name", "status"),
        Index("ix_etl_job_started", "started_at"),
    )


# === Pydantic Response Models ===

class SessionMetrics(BaseModel):
    """Session duration metrics response."""
    model_config = ConfigDict(from_attributes=True)
    
    total_sessions: int = Field(..., description="Total number of sessions")
    avg_duration_minutes: float = Field(..., description="Average session duration")
    median_duration_minutes: float = Field(..., description="Median session duration")
    total_hours: float = Field(..., description="Total learning hours")
    trend_direction: str = Field(..., description="Trend: up, down, stable")
    
    # Privacy metadata
    privacy_level: str = Field(..., description="Privacy protection level applied")
    data_points: int = Field(..., description="Number of sessions aggregated")


class MasteryMetrics(BaseModel):
    """Subject mastery metrics response."""
    model_config = ConfigDict(from_attributes=True)
    
    subject_id: UUID = Field(..., description="Subject identifier")
    subject_category: str = Field(..., description="Subject category")
    current_mastery: float = Field(..., description="Current mastery score (0-1)")
    mastery_improvement: float = Field(..., description="Improvement delta")
    assessments_completed: int = Field(..., description="Number of assessments")
    time_to_mastery_hours: Optional[float] = Field(None, description="Hours to achieve mastery")
    
    # Privacy metadata
    privacy_level: str = Field(..., description="Privacy protection level")
    aggregation_level: str = Field(..., description="Individual, cohort, or tenant")


class WeeklyActivityMetrics(BaseModel):
    """Weekly activity metrics response."""
    model_config = ConfigDict(from_attributes=True)
    
    week_start: date = Field(..., description="Week starting date")
    active_learners: int = Field(..., description="Total active learners")
    new_learners: int = Field(..., description="New learners this week")
    engagement_rate: float = Field(..., description="Engagement rate (0-1)")
    avg_sessions_per_learner: float = Field(..., description="Average sessions per learner")
    avg_time_per_learner: float = Field(..., description="Average minutes per learner")
    
    # Demographics (aggregated)
    demographics: Dict[str, Any] = Field(..., description="Aggregated demographic data")
    privacy_level: str = Field(..., description="Privacy protection level")


class IEPProgressMetrics(BaseModel):
    """IEP progress metrics response."""
    model_config = ConfigDict(from_attributes=True)
    
    goal_category: str = Field(..., description="IEP goal category")
    baseline_score: float = Field(..., description="Starting baseline score")
    current_score: float = Field(..., description="Current achievement score")
    target_score: float = Field(..., description="Target goal score")
    progress_percentage: float = Field(..., description="Progress toward goal (0-1)")
    is_on_track: bool = Field(..., description="Whether learner is on track")
    
    days_since_baseline: int = Field(..., description="Days since baseline measurement")
    projected_completion: Optional[int] = Field(None, description="Projected days to completion")
    
    # Support information (anonymized)
    support_level: Optional[str] = Field(None, description="Level of support needed")
    interventions_used: int = Field(..., description="Number of interventions")
    
    privacy_level: str = Field(..., description="Privacy protection level")


class TenantAnalyticsSummary(BaseModel):
    """Comprehensive tenant analytics summary."""
    model_config = ConfigDict(from_attributes=True)
    
    tenant_id: UUID = Field(..., description="Tenant identifier")
    reporting_period_start: date = Field(..., description="Report start date")
    reporting_period_end: date = Field(..., description="Report end date")
    
    # High-level metrics
    total_active_learners: int = Field(..., description="Total active learners")
    total_learning_hours: float = Field(..., description="Total learning hours")
    average_engagement_rate: float = Field(..., description="Average engagement rate")
    
    # Breakdown by metrics
    session_metrics: SessionMetrics = Field(..., description="Session duration metrics")
    weekly_activity: List[WeeklyActivityMetrics] = Field(..., description="Weekly activity trends")
    top_subjects: List[MasteryMetrics] = Field(..., description="Top performing subjects")
    
    # IEP summary (if applicable)
    iep_progress_summary: Optional[Dict[str, Any]] = Field(None, description="IEP progress overview")
    
    # Privacy and metadata
    privacy_level: str = Field(..., description="Privacy protection applied")
    last_updated: datetime = Field(..., description="Data last updated")


class LearnerAnalyticsSummary(BaseModel):
    """Privacy-aware learner analytics summary."""
    model_config = ConfigDict(from_attributes=True)
    
    learner_id_hash: str = Field(..., description="Hashed learner identifier")
    reporting_period_start: date = Field(..., description="Report start date")
    reporting_period_end: date = Field(..., description="Report end date")
    
    # Learning activity
    session_metrics: SessionMetrics = Field(..., description="Session activity")
    subject_progress: List[MasteryMetrics] = Field(..., description="Subject mastery progress")
    
    # IEP progress (if applicable)
    iep_progress: Optional[List[IEPProgressMetrics]] = Field(None, description="IEP goal progress")
    
    # Privacy guarantees
    privacy_level: str = Field(..., description="Privacy protection level")
    minimum_cohort_size: int = Field(..., description="Minimum k-anonymity group size")
    differential_privacy_epsilon: Optional[float] = Field(None, description="DP epsilon used")
    
    # Data freshness
    last_updated: datetime = Field(..., description="Data last updated")
    data_completeness: float = Field(..., description="Data completeness score (0-1)")


class ETLJobStatus(BaseModel):
    """ETL job execution status."""
    model_config = ConfigDict(from_attributes=True)
    
    job_id: UUID = Field(..., description="Job execution ID")
    job_name: str = Field(..., description="Job name")
    status: str = Field(..., description="Job status")
    started_at: datetime = Field(..., description="Job start time")
    completed_at: Optional[datetime] = Field(None, description="Job completion time")
    
    records_processed: int = Field(..., description="Records processed")
    records_created: int = Field(..., description="Records created")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time")
    
    privacy_level: str = Field(..., description="Privacy level applied")
    epsilon_used: Optional[float] = Field(None, description="DP epsilon budget used")
    
    error_message: Optional[str] = Field(None, description="Error message if failed")
