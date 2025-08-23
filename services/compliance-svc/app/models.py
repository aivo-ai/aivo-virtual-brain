"""
Compliance Service Models (S5-09)

Models for compliance evidence aggregation including isolation tests,
consent history, data protection analytics, and audit logs.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class IsolationTestStatus(str, Enum):
    """Status of isolation tests."""
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"
    ERROR = "error"


class ConsentStatus(str, Enum):
    """Status of consent records."""
    ACTIVE = "active"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    PENDING = "pending"


class DataProtectionAction(str, Enum):
    """Types of data protection actions."""
    EXPORT = "export"
    ERASE = "erase"
    RECTIFY = "rectify"
    RESTRICT = "restrict"
    OBJECT = "object"


class DataProtectionStatus(str, Enum):
    """Status of data protection requests."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AuditEventType(str, Enum):
    """Types of audit events."""
    DATA_ACCESS = "data_access"
    CONSENT_CHANGE = "consent_change"
    ISOLATION_TEST = "isolation_test"
    DP_REQUEST = "dp_request"
    RETENTION_ACTION = "retention_action"
    SECURITY_EVENT = "security_event"


# Database Models
class IsolationTestResult(Base):
    """Database model for isolation test results."""
    __tablename__ = "isolation_test_results"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    test_type = Column(String(50), nullable=False)  # namespace, network, storage, etc.
    test_name = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, default=IsolationTestStatus.PENDING)
    
    # Test execution details
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Results
    pass_rate = Column(Float, nullable=True)  # 0.0 to 1.0
    test_count = Column(Integer, nullable=False, default=0)
    passed_count = Column(Integer, nullable=False, default=0)
    failed_count = Column(Integer, nullable=False, default=0)
    
    # Details
    test_config = Column(JSON, nullable=True)
    test_results = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class ConsentRecord(Base):
    """Database model for consent tracking."""
    __tablename__ = "consent_records"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    learner_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    guardian_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Consent details
    consent_version = Column(String(20), nullable=False)
    consent_type = Column(String(50), nullable=False)  # data_processing, ai_training, etc.
    status = Column(String(20), nullable=False, default=ConsentStatus.ACTIVE)
    
    # Timestamps
    granted_at = Column(DateTime(timezone=True), nullable=False)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Additional data
    consent_text = Column(Text, nullable=True)
    consent_metadata = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class DataProtectionRequest(Base):
    """Database model for data protection requests (GDPR, etc.)."""
    __tablename__ = "data_protection_requests"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    learner_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    requester_id = Column(PGUUID(as_uuid=True), nullable=False)  # Guardian or learner
    
    # Request details
    action = Column(String(20), nullable=False)  # export, erase, etc.
    status = Column(String(20), nullable=False, default=DataProtectionStatus.PENDING)
    reason = Column(Text, nullable=True)
    
    # Processing details
    requested_at = Column(DateTime(timezone=True), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Results
    result_url = Column(String(500), nullable=True)  # For export downloads
    result_metadata = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Compliance tracking
    legal_basis = Column(String(100), nullable=True)
    retention_policy = Column(String(100), nullable=True)
    
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


class AuditEvent(Base):
    """Database model for audit events."""
    __tablename__ = "audit_events"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    
    # Context
    tenant_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    learner_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    actor_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(50), nullable=False, index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(100), nullable=True)
    
    # Metadata
    event_data = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    session_id = Column(String(100), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))


# Pydantic Models for API
class IsolationTestSummary(BaseModel):
    """Summary of isolation test results."""
    test_type: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    last_test_date: datetime
    average_duration: float


class TenantEvidenceResponse(BaseModel):
    """Evidence response for tenant-level compliance."""
    tenant_id: UUID
    isolation_tests: List[IsolationTestSummary]
    chaos_checks: Dict[str, Any]
    retention_job_status: Dict[str, Any]
    last_updated: datetime
    
    # Aggregated metrics
    overall_isolation_pass_rate: float
    total_isolation_tests: int
    failed_isolation_tests: int
    retention_compliance_score: float


class ConsentSummary(BaseModel):
    """Summary of consent status."""
    consent_type: str
    current_version: str
    status: ConsentStatus
    granted_at: datetime
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None


class DataProtectionSummary(BaseModel):
    """Summary of data protection requests."""
    action: DataProtectionAction
    status: DataProtectionStatus
    requested_at: datetime
    completed_at: Optional[datetime] = None
    result_available: bool = False


class AuditEventSummary(BaseModel):
    """Summary of audit events."""
    event_type: AuditEventType
    action: str
    timestamp: datetime
    actor_id: UUID
    resource_type: Optional[str] = None
    event_data: Optional[Dict[str, Any]] = None


class LearnerEvidenceResponse(BaseModel):
    """Evidence response for learner-level compliance."""
    learner_id: UUID
    consent_history: List[ConsentSummary]
    data_protection_requests: List[DataProtectionSummary]
    audit_events: List[AuditEventSummary]
    dp_toggle_state: Dict[str, bool]
    last_updated: datetime
    
    # Aggregated metrics
    total_consent_versions: int
    active_consents: int
    pending_dp_requests: int
    total_audit_events: int
    last_activity: datetime


class EvidenceMetrics(BaseModel):
    """Overall evidence metrics."""
    total_tenants: int
    total_learners: int
    isolation_tests_24h: int
    consent_changes_24h: int
    dp_requests_24h: int
    audit_events_24h: int
    compliance_score: float
    last_calculated: datetime


# Chart data models
class SparklineData(BaseModel):
    """Data for sparkline charts."""
    timestamps: List[datetime]
    values: List[float]
    metric_name: str


class ComplianceChartData(BaseModel):
    """Chart data for compliance dashboard."""
    isolation_pass_rate: SparklineData
    consent_activity: SparklineData
    dp_request_volume: SparklineData
    audit_event_frequency: SparklineData
