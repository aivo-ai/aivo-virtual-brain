"""
Database models for Model Trainer Service
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .database import Base


class JobStatus(enum.Enum):
    """Training job status"""
    PENDING = "pending"
    VALIDATING = "validating"
    TRAINING = "training"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationStatus(enum.Enum):
    """Evaluation status"""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class Provider(enum.Enum):
    """Supported training providers"""
    OPENAI = "openai"
    VERTEX_AI = "vertex_ai"
    BEDROCK = "bedrock"
    ANTHROPIC = "anthropic"


class TrainingJob(Base):
    """Training job model"""
    
    __tablename__ = "training_jobs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Job metadata
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(JobStatus), nullable=False, default=JobStatus.PENDING, index=True)
    
    # Training configuration
    provider = Column(Enum(Provider), nullable=False, index=True)
    base_model = Column(String(255), nullable=False)
    dataset_uri = Column(String(500), nullable=False)
    
    # Training parameters (stored as JSON)
    config = Column(JSON, nullable=False, default=dict)
    
    # Policy configuration
    policy = Column(JSON, nullable=False, default=dict)
    
    # Datasheet requirements
    datasheet = Column(JSON, nullable=False, default=dict)
    
    # Provider-specific job details
    provider_job_id = Column(String(255), nullable=True, unique=True)
    provider_model_id = Column(String(255), nullable=True)
    provider_metadata = Column(JSON, nullable=True, default=dict)
    
    # Training metrics
    training_tokens = Column(Integer, nullable=True)
    training_cost = Column(Float, nullable=True)
    training_duration = Column(Integer, nullable=True)  # seconds
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('name', name='uq_training_job_name'),
    )


class Evaluation(Base):
    """Evaluation model"""
    
    __tablename__ = "evaluations"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Associated training job
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Evaluation metadata
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Enum(EvaluationStatus), nullable=False, default=EvaluationStatus.PENDING, index=True)
    
    # Evaluation configuration
    harness_config = Column(JSON, nullable=False, default=dict)
    thresholds = Column(JSON, nullable=False, default=dict)
    
    # Results
    pedagogy_score = Column(Float, nullable=True)
    safety_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # Detailed results
    results = Column(JSON, nullable=True, default=dict)
    metrics = Column(JSON, nullable=True, default=dict)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)


class ModelPromotion(Base):
    """Model promotion tracking"""
    
    __tablename__ = "model_promotions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4, index=True)
    
    # Associated training job and evaluation
    job_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    evaluation_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    
    # Registry information
    registry_model_id = Column(UUID(as_uuid=True), nullable=True)
    registry_version_id = Column(UUID(as_uuid=True), nullable=True)
    registry_binding_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Promotion details
    promoted = Column(Boolean, nullable=False, default=False)
    promotion_reason = Column(Text, nullable=True)
    promotion_metadata = Column(JSON, nullable=True, default=dict)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
