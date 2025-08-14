"""
Pydantic models for Private Foundation Model Orchestrator.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class NamespaceStatus(str, Enum):
    """Status of a learner namespace."""
    INITIALIZING = "initializing"
    ACTIVE = "active" 
    MERGING = "merging"
    FALLBACK = "fallback"
    CORRUPTED = "corrupted"
    DELETED = "deleted"


class MergeStatus(str, Enum):
    """Status of a merge operation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class FallbackReason(str, Enum):
    """Reasons for initiating fallback recovery."""
    CORRUPTION_DETECTED = "corruption_detected"
    VERSION_LAG = "version_lag"
    MANUAL_REQUEST = "manual_request"
    INTEGRITY_FAILURE = "integrity_failure"


# Database Models
class LearnerNamespace(Base):
    """Database model for learner namespaces."""
    __tablename__ = "learner_namespaces"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    learner_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True, index=True)
    ns_uid = Column(String(64), nullable=False, unique=True, index=True)
    status = Column(String(20), nullable=False, default=NamespaceStatus.INITIALIZING)
    subjects = Column(JSON, nullable=False, default=list)
    
    # Foundation model tracking
    base_fm_version = Column(String(64), nullable=False)
    current_checkpoint_hash = Column(String(64), nullable=True)
    version_count = Column(Integer, nullable=False, default=0)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_merge_at = Column(DateTime(timezone=True), nullable=True)
    last_fallback_at = Column(DateTime(timezone=True), nullable=True)
    
    # Configuration
    merge_config = Column(JSON, nullable=False, default=dict)
    isolation_config = Column(JSON, nullable=False, default=dict)


class MergeOperation(Base):
    """Database model for merge operations."""
    __tablename__ = "merge_operations"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    namespace_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    learner_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    status = Column(String(20), nullable=False, default=MergeStatus.PENDING)
    operation_type = Column(String(20), nullable=False)  # "nightly", "manual", "fallback"
    
    # Versioning
    source_checkpoint_hash = Column(String(64), nullable=True)
    target_checkpoint_hash = Column(String(64), nullable=True)
    fm_version = Column(String(64), nullable=False)
    
    # Progress tracking
    progress_percent = Column(Integer, nullable=False, default=0)
    stage = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Timing
    scheduled_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    merge_stats = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class EventLog(Base):
    """Database model for namespace event logging."""
    __tablename__ = "event_logs"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    namespace_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    learner_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    event_type = Column(String(50), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    checkpoint_hash = Column(String(64), nullable=True)
    
    # Sequence tracking for replay
    sequence_number = Column(Integer, nullable=False, index=True)
    correlation_id = Column(String(64), nullable=True, index=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String(100), nullable=False)  # system, guardian, api


# Pydantic Models
class NamespaceBase(BaseModel):
    """Base namespace model."""
    learner_id: UUID
    subjects: List[str] = Field(default_factory=list)
    merge_config: Dict[str, Any] = Field(default_factory=dict)
    isolation_config: Dict[str, Any] = Field(default_factory=dict)


class NamespaceCreate(NamespaceBase):
    """Model for creating a new namespace."""
    base_fm_version: str = Field(..., description="Foundation model version to base namespace on")
    
    @validator('subjects')
    def validate_subjects(cls, v):
        """Validate subject list."""
        if not isinstance(v, list):
            raise ValueError("Subjects must be a list")
        if len(v) > 50:  # Reasonable limit
            raise ValueError("Too many subjects (max 50)")
        return v


class NamespaceResponse(NamespaceBase):
    """Model for namespace response."""
    id: UUID
    ns_uid: str
    status: NamespaceStatus
    base_fm_version: str
    current_checkpoint_hash: Optional[str] = None
    version_count: int
    created_at: datetime
    updated_at: datetime
    last_merge_at: Optional[datetime] = None
    last_fallback_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class NamespaceUpdate(BaseModel):
    """Model for updating namespace."""
    subjects: Optional[List[str]] = None
    merge_config: Optional[Dict[str, Any]] = None
    isolation_config: Optional[Dict[str, Any]] = None
    status: Optional[NamespaceStatus] = None


class MergeRequest(BaseModel):
    """Model for requesting a merge operation."""
    operation_type: str = Field("manual", description="Type of merge operation")
    force: bool = Field(False, description="Force merge even if recent merge exists")
    target_fm_version: Optional[str] = Field(None, description="Specific FM version to merge with")
    merge_config: Optional[Dict[str, Any]] = Field(None, description="Override merge configuration")


class MergeResponse(BaseModel):
    """Model for merge operation response."""
    id: UUID
    namespace_id: UUID
    learner_id: UUID
    status: MergeStatus
    operation_type: str
    source_checkpoint_hash: Optional[str] = None
    target_checkpoint_hash: Optional[str] = None
    fm_version: str
    progress_percent: int = 0
    stage: Optional[str] = None
    error_message: Optional[str] = None
    scheduled_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    merge_stats: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class FallbackRequest(BaseModel):
    """Model for requesting fallback recovery."""
    reason: FallbackReason
    target_fm_version: Optional[str] = Field(None, description="FM version to fall back to")
    preserve_events_after: Optional[datetime] = Field(None, description="Preserve events after this timestamp")
    force: bool = Field(False, description="Force fallback even if namespace is healthy")


class FallbackResponse(BaseModel):
    """Model for fallback operation response."""
    operation_id: UUID
    namespace_id: UUID
    learner_id: UUID
    reason: FallbackReason
    estimated_duration_minutes: int
    events_to_replay: int
    target_fm_version: str
    started_at: datetime


class CheckpointInfo(BaseModel):
    """Model for checkpoint information."""
    hash: str
    version: int
    size_bytes: int
    created_at: datetime
    merge_operation_id: Optional[UUID] = None
    is_active: bool
    integrity_verified: bool
    metadata: Dict[str, Any] = Field(default_factory=dict)


class NamespaceHealth(BaseModel):
    """Model for namespace health status."""
    namespace_id: UUID
    learner_id: UUID
    status: NamespaceStatus
    is_healthy: bool
    last_merge_ago_hours: Optional[int] = None
    version_lag: int
    integrity_score: float = Field(..., ge=0.0, le=1.0)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class EventLogEntry(BaseModel):
    """Model for event log entries."""
    id: UUID
    namespace_id: UUID
    learner_id: UUID
    event_type: str
    event_data: Dict[str, Any]
    checkpoint_hash: Optional[str] = None
    sequence_number: int
    correlation_id: Optional[str] = None
    created_at: datetime
    created_by: str
    
    class Config:
        from_attributes = True


class PrivateBrainReadyEvent(BaseModel):
    """Model for PRIVATE_BRAIN_READY event."""
    learner_id: UUID
    brain_type: str
    subjects: List[str]
    foundation_model_version: str
    configuration: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    correlation_id: str


class NamespaceMetrics(BaseModel):
    """Model for namespace metrics."""
    total_namespaces: int
    active_namespaces: int
    namespaces_by_status: Dict[NamespaceStatus, int]
    total_merge_operations: int
    successful_merges_24h: int
    failed_merges_24h: int
    average_merge_duration_minutes: float
    total_fallback_operations: int
    fallbacks_24h: int
    average_checkpoint_size_mb: float
    oldest_namespace_days: int
