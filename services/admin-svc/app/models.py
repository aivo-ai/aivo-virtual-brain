"""
Pydantic models for AIVO Admin Service
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class SystemStats(BaseModel):
    """System statistics model"""
    total_learners: int
    active_sessions: int
    pending_approvals: int
    failed_jobs: int
    system_uptime: str
    avg_response_time: float
    error_rate: float
    queue_health: str
    last_updated: datetime


class ServiceHealth(BaseModel):
    """Service health status model"""
    status: str = Field(..., description="Service status: healthy, unhealthy, error")
    response_time: float = Field(..., description="Response time in milliseconds")
    last_check: datetime
    details: Dict[str, Any] = Field(default_factory=dict)


class SystemAlert(BaseModel):
    """System alert model"""
    id: str
    type: str = Field(..., description="Alert type: performance, security, queue, etc.")
    severity: str = Field(..., description="Alert severity: info, warning, critical")
    message: str
    timestamp: datetime
    source: str = Field(..., description="Source service or component")
    resolved: bool = False
    details: Dict[str, Any] = Field(default_factory=dict)


class ApprovalStatus(str, Enum):
    """Approval status enumeration"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ApprovalPriority(str, Enum):
    """Approval priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ApprovalRequest(BaseModel):
    """Approval request model"""
    id: str
    type: str = Field(..., description="Type of approval: consent, access, etc.")
    status: ApprovalStatus
    priority: ApprovalPriority
    learner_id: Optional[str] = None
    guardian_id: Optional[str] = None
    tenant_id: str
    requested_by: str
    requested_at: datetime
    expires_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ApprovalStats(BaseModel):
    """Approval queue statistics"""
    total_pending: int
    total_approved: int
    total_rejected: int
    avg_processing_time_hours: float
    urgent_count: int
    expiring_soon_count: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]


class JobStatus(str, Enum):
    """Job status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class JobPriority(str, Enum):
    """Job priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class JobQueue(BaseModel):
    """Job queue model"""
    name: str
    service: str = Field(..., description="Service that owns this queue")
    total_jobs: int
    pending_jobs: int
    running_jobs: int
    failed_jobs: int
    avg_processing_time_minutes: float
    health_status: str
    last_updated: datetime


class Job(BaseModel):
    """Job model"""
    id: str
    queue_name: str
    type: str
    status: JobStatus
    priority: JobPriority
    tenant_id: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    progress_percentage: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class JobAction(BaseModel):
    """Job action request"""
    action: str = Field(..., description="Action: requeue, cancel, retry")
    reason: str = Field(..., description="Reason for the action")
    force: bool = Field(default=False, description="Force action even if risky")


class JobActionResult(BaseModel):
    """Job action result"""
    job_id: str
    action: str
    success: bool
    message: str
    timestamp: datetime
    performed_by: str


class QueueStats(BaseModel):
    """Queue statistics"""
    total_queues: int
    healthy_queues: int
    total_jobs: int
    pending_jobs: int
    failed_jobs: int
    avg_processing_time: float
    throughput_per_minute: float
    error_rate: float


class SupportSessionRequest(BaseModel):
    """Support session request"""
    learner_id: str
    purpose: str = Field(..., description="Business purpose for data access")
    urgency: str = Field(default="normal", description="normal, urgent, emergency")
    estimated_duration_minutes: int = Field(default=30)
    requestor_notes: Optional[str] = None


class SupportSession(BaseModel):
    """Active support session"""
    id: str
    learner_id: str
    staff_user_id: str
    purpose: str
    urgency: str
    consent_token: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    accessed_data: List[str] = Field(default_factory=list)
    actions_performed: List[str] = Field(default_factory=list)
    is_active: bool = True


class ConsentRequest(BaseModel):
    """Consent request for learner data access"""
    learner_id: str
    guardian_id: Optional[str] = None
    purpose: str
    urgency: str
    data_types: List[str] = Field(..., description="Types of data to access")
    duration_minutes: int = Field(default=30)


class ConsentToken(BaseModel):
    """Just-in-time consent token"""
    token: str
    learner_id: str
    granted_by: str
    purpose: str
    data_types: List[str]
    expires_at: datetime
    usage_count: int = 0
    max_usage: int = 10


class AuditEvent(BaseModel):
    """Audit event model"""
    id: str
    event_type: str
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    action: str
    outcome: str = Field(..., description="success, failure, error")
    details: Dict[str, Any] = Field(default_factory=dict)
    tenant_id: Optional[str] = None


class AuditQuery(BaseModel):
    """Audit query parameters"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    user_id: Optional[str] = None
    event_type: Optional[str] = None
    resource_type: Optional[str] = None
    outcome: Optional[str] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


class AuditSummary(BaseModel):
    """Audit event summary"""
    total_events: int
    date_range: Dict[str, datetime]
    by_event_type: Dict[str, int]
    by_outcome: Dict[str, int]
    by_user: Dict[str, int]
    recent_events: List[AuditEvent]


class LearnerDataAccess(BaseModel):
    """Learner data access record"""
    learner_id: str
    data_type: str
    accessed_at: datetime
    accessed_by: str
    session_id: str
    purpose: str
    data_summary: Dict[str, Any] = Field(default_factory=dict)


class FeatureFlag(BaseModel):
    """Feature flag model"""
    name: str
    enabled: bool
    description: str
    last_modified: datetime
    modified_by: str
    environment: str


class AdminAction(BaseModel):
    """Admin action log"""
    action_id: str
    user_id: str
    action_type: str
    target_resource: Optional[str] = None
    timestamp: datetime
    success: bool
    details: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
