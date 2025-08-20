"""
Audit Service Data Models
Comprehensive audit logging for AIVO platform with access reviews and JIT support
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List, Union
from uuid import UUID, uuid4

import structlog
from pydantic import BaseModel, Field, validator

logger = structlog.get_logger()


class AuditEventType(str, Enum):
    """Types of audit events in the system"""
    
    # Data Access Events
    DATA_READ = "data_read"
    DATA_WRITE = "data_write" 
    DATA_DELETE = "data_delete"
    DATA_EXPORT = "data_export"
    DATA_ANONYMIZE = "data_anonymize"
    
    # Authentication Events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_ENABLED = "mfa_enabled"
    MFA_DISABLED = "mfa_disabled"
    
    # Authorization Events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    
    # Support Events
    SUPPORT_SESSION_REQUEST = "support_session_request"
    SUPPORT_SESSION_APPROVED = "support_session_approved"
    SUPPORT_SESSION_DENIED = "support_session_denied"
    SUPPORT_SESSION_START = "support_session_start"
    SUPPORT_SESSION_END = "support_session_end"
    SUPPORT_TOKEN_ISSUED = "support_token_issued"
    SUPPORT_TOKEN_EXPIRED = "support_token_expired"
    
    # Administrative Events
    USER_CREATED = "user_created"
    USER_UPDATED = "user_updated"
    USER_DISABLED = "user_disabled"
    SYSTEM_CONFIG_CHANGED = "system_config_changed"
    
    # Access Review Events
    ACCESS_REVIEW_STARTED = "access_review_started"
    ACCESS_REVIEW_COMPLETED = "access_review_completed"
    ACCESS_CERTIFIED = "access_certified"
    ACCESS_REVOKED = "access_revoked"


class AuditSeverity(str, Enum):
    """Severity levels for audit events"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataClassification(str, Enum):
    """Data classification levels"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class UserRole(str, Enum):
    """User roles in the system"""
    STUDENT = "student"
    TEACHER = "teacher"
    GUARDIAN = "guardian"
    ADMIN = "admin"
    SUPPORT = "support"
    SYSTEM = "system"


class AccessReviewStatus(str, Enum):
    """Status of access reviews"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class SupportSessionStatus(str, Enum):
    """Status of support sessions"""
    REQUESTED = "requested"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DENIED = "denied"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"


class AuditEvent(BaseModel):
    """Core audit event model"""
    
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.MEDIUM
    
    # Actor information (who performed the action)
    actor_id: Optional[UUID] = None
    actor_type: Optional[UserRole] = None
    actor_email: Optional[str] = None
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None
    
    # Target information (what was acted upon)
    target_id: Optional[UUID] = None
    target_type: Optional[str] = None
    target_classification: Optional[DataClassification] = None
    
    # Context information
    tenant_id: UUID
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Event details
    action: str
    resource: str
    outcome: str = "success"  # success, failure, error
    reason: Optional[str] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Compliance fields
    retention_days: int = 2555  # 7 years default
    
    class Config:
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: str
        }


class DataAccessLog(BaseModel):
    """Specialized model for data access logging"""
    
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Who accessed the data
    user_id: UUID
    user_role: UserRole
    user_email: str
    
    # What data was accessed
    data_type: str
    data_id: Optional[UUID] = None
    data_classification: DataClassification
    
    # How the data was accessed
    operation: str  # read, write, delete, export
    endpoint: Optional[str] = None
    sql_query_hash: Optional[str] = None
    
    # Why the data was accessed
    purpose: str
    justification: Optional[str] = None
    
    # Context
    tenant_id: UUID
    session_id: str
    ip_address: Optional[str] = None
    
    # Result
    records_affected: int = 0
    success: bool = True
    error_message: Optional[str] = None
    
    class Config:
        use_enum_values = True


class AccessReview(BaseModel):
    """Model for periodic access reviews"""
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Review scope
    tenant_id: UUID
    review_type: str = "quarterly"  # quarterly, annual, ad_hoc
    review_period_start: datetime
    review_period_end: datetime
    
    # Status
    status: AccessReviewStatus = AccessReviewStatus.PENDING
    due_date: datetime
    completed_at: Optional[datetime] = None
    
    # Reviewer
    reviewer_id: UUID
    reviewer_email: str
    
    # Scope filters
    roles_to_review: List[UserRole] = Field(default_factory=list)
    departments: List[str] = Field(default_factory=list)
    risk_levels: List[str] = Field(default_factory=list)
    
    # Results
    total_users_reviewed: int = 0
    access_certified: int = 0
    access_revoked: int = 0
    access_modified: int = 0
    
    # Metadata
    notes: Optional[str] = None
    attachments: List[str] = Field(default_factory=list)
    
    @validator('due_date', pre=True, always=True)
    def set_due_date(cls, v, values):
        if v is None and 'review_period_end' in values:
            return values['review_period_end'] + timedelta(days=30)
        return v


class SupportSession(BaseModel):
    """Model for Just-In-Time support sessions"""
    
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Request details
    learner_id: UUID
    guardian_id: UUID
    support_agent_id: Optional[UUID] = None
    
    # Session details
    status: SupportSessionStatus = SupportSessionStatus.REQUESTED
    reason: str
    description: Optional[str] = None
    urgency: str = "normal"  # low, normal, high, emergency
    
    # Approval workflow
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    approval_requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    denied_at: Optional[datetime] = None
    approval_reason: Optional[str] = None
    
    # Session timing
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None
    max_duration_minutes: int = 60  # Default 1 hour
    
    # Access control
    read_only: bool = True
    allowed_data_types: List[str] = Field(default_factory=list)
    restricted_data_types: List[str] = Field(default_factory=list)
    
    # Tracking
    access_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    actions_performed: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    tenant_id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    @validator('token_expires_at', pre=True, always=True)
    def set_token_expiry(cls, v, values):
        if v is None and 'session_start' in values and values['session_start']:
            duration = values.get('max_duration_minutes', 60)
            return values['session_start'] + timedelta(minutes=duration)
        return v


class AccessReviewItem(BaseModel):
    """Individual item within an access review"""
    
    id: UUID = Field(default_factory=uuid4)
    review_id: UUID
    
    # User being reviewed
    user_id: UUID
    user_email: str
    user_role: UserRole
    department: Optional[str] = None
    
    # Access details
    permissions: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    last_login: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    
    # Review decision
    status: str = "pending"  # pending, certified, revoked, modified
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None
    
    # Risk assessment
    risk_score: float = 0.0
    risk_factors: List[str] = Field(default_factory=list)
    
    # Changes made
    changes_made: List[Dict[str, Any]] = Field(default_factory=list)


class AuditQuery(BaseModel):
    """Model for audit log queries and filters"""
    
    # Time range
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Filters
    event_types: Optional[List[AuditEventType]] = None
    severities: Optional[List[AuditSeverity]] = None
    actor_ids: Optional[List[UUID]] = None
    target_ids: Optional[List[UUID]] = None
    tenant_id: Optional[UUID] = None
    
    # Search
    search_term: Optional[str] = None
    
    # Pagination
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)
    
    # Sorting
    sort_by: str = "timestamp"
    sort_order: str = "desc"  # asc, desc


class AuditReport(BaseModel):
    """Model for audit reports and dashboards"""
    
    id: UUID = Field(default_factory=uuid4)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Report scope
    tenant_id: UUID
    report_type: str
    period_start: datetime
    period_end: datetime
    
    # Metrics
    total_events: int = 0
    events_by_type: Dict[str, int] = Field(default_factory=dict)
    events_by_severity: Dict[str, int] = Field(default_factory=dict)
    unique_actors: int = 0
    failed_events: int = 0
    
    # Top lists
    top_actors: List[Dict[str, Any]] = Field(default_factory=list)
    top_resources: List[Dict[str, Any]] = Field(default_factory=list)
    risk_events: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Compliance metrics
    access_reviews_completed: int = 0
    support_sessions_approved: int = 0
    policy_violations: int = 0
    
    # File attachments
    report_file_path: Optional[str] = None
    charts: List[str] = Field(default_factory=list)


# Request/Response Models for API

class CreateAuditEventRequest(BaseModel):
    """Request model for creating audit events"""
    
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.MEDIUM
    action: str
    resource: str
    outcome: str = "success"
    reason: Optional[str] = None
    
    # Actor info (optional, can be inferred from JWT)
    actor_id: Optional[UUID] = None
    actor_type: Optional[UserRole] = None
    
    # Target info
    target_id: Optional[UUID] = None
    target_type: Optional[str] = None
    target_classification: Optional[DataClassification] = None
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CreateSupportSessionRequest(BaseModel):
    """Request model for creating support sessions"""
    
    learner_id: UUID
    reason: str
    description: Optional[str] = None
    urgency: str = "normal"
    max_duration_minutes: int = 60
    allowed_data_types: List[str] = Field(default_factory=list)


class ApproveSupportSessionRequest(BaseModel):
    """Request model for approving support sessions"""
    
    approved: bool
    reason: Optional[str] = None
    max_duration_minutes: Optional[int] = None
    allowed_data_types: Optional[List[str]] = None


class StartAccessReviewRequest(BaseModel):
    """Request model for starting access reviews"""
    
    review_type: str = "quarterly"
    roles_to_review: List[UserRole] = Field(default_factory=list)
    departments: List[str] = Field(default_factory=list)
    due_date: Optional[datetime] = None


class ReviewAccessItemRequest(BaseModel):
    """Request model for reviewing individual access items"""
    
    status: str  # certified, revoked, modified
    reviewer_notes: Optional[str] = None
    changes_to_make: List[Dict[str, Any]] = Field(default_factory=list)
