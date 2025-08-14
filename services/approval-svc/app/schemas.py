# AIVO Approval Service - Pydantic Schemas
# S2-10 Implementation - Request/Response validation schemas

from pydantic import BaseModel, Field, field_validator, ConfigDict
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union
from enum import Enum
import uuid

# Re-export enums for API consistency
from .models import ApprovalStatus, ApproverRole, ApprovalType


class ApprovalRequestCreate(BaseModel):
    """Schema for creating a new approval request."""
    tenant_id: uuid.UUID = Field(..., description="Tenant ID for the request")
    approval_type: ApprovalType = Field(..., description="Type of approval needed")
    resource_id: str = Field(..., min_length=1, max_length=255, description="ID of resource being approved")
    resource_type: str = Field(..., min_length=1, max_length=100, description="Type of resource (e.g., 'iep', 'level')")
    
    title: str = Field(..., min_length=1, max_length=500, description="Human-readable title")
    description: Optional[str] = Field(None, description="Detailed description of what needs approval")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context data")
    
    # TTL configuration
    expires_in_hours: int = Field(default=72, ge=1, le=8760, description="Hours until expiration (1 hour to 1 year)")
    
    # Requester information
    requested_by: str = Field(..., min_length=1, max_length=255, description="ID of user requesting approval")
    requested_by_role: Optional[str] = Field(None, max_length=100, description="Role of requester")
    
    # Required approvals
    required_roles: List[ApproverRole] = Field(..., min_length=1, description="Roles that must approve")
    
    # Webhook configuration
    webhook_url: Optional[str] = Field(None, max_length=1000, description="URL to call when decision is made")
    webhook_headers: Optional[Dict[str, str]] = Field(None, description="Headers for webhook call")
    
    @field_validator('expires_in_hours')
    @classmethod
    def validate_expiration(cls, v):
        """Ensure reasonable expiration times."""
        if v < 1:
            raise ValueError('Expiration must be at least 1 hour')
        if v > 8760:  # 1 year
            raise ValueError('Expiration cannot exceed 1 year')
        return v
    
    @field_validator('required_roles')
    @classmethod
    def validate_required_roles(cls, v):
        """Ensure unique roles and reasonable count."""
        if len(set(v)) != len(v):
            raise ValueError('Duplicate roles not allowed in required_roles')
        if len(v) > 10:
            raise ValueError('Cannot require more than 10 approval roles')
        return v

    model_config = ConfigDict(use_enum_values=True)


class ApprovalDecisionCreate(BaseModel):
    """Schema for making an approval decision."""
    approver_id: str = Field(..., min_length=1, max_length=255, description="ID of user making decision")
    approver_role: ApproverRole = Field(..., description="Role of the approver")
    approver_name: Optional[str] = Field(None, max_length=255, description="Display name of approver")
    
    approved: bool = Field(..., description="True for approval, False for rejection")
    comments: Optional[str] = Field(None, description="Optional comments about the decision")
    decision_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional decision context")

    class Config:
        use_enum_values = True


class ApprovalDecisionResponse(BaseModel):
    """Schema for approval decision responses."""
    id: uuid.UUID
    approver_id: str
    approver_role: ApproverRole
    approver_name: Optional[str]
    approved: bool
    comments: Optional[str]
    decided_at: datetime
    decision_metadata: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
        use_enum_values = True


class ApprovalReminderResponse(BaseModel):
    """Schema for approval reminder responses."""
    id: uuid.UUID
    recipient_role: ApproverRole
    recipient_id: str
    scheduled_for: datetime
    sent_at: Optional[datetime]
    reminder_type: str
    sent: bool

    class Config:
        from_attributes = True
        use_enum_values = True


class ApprovalRequestResponse(BaseModel):
    """Schema for approval request responses."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    
    # Request details
    approval_type: ApprovalType
    resource_id: str
    resource_type: str
    title: str
    description: Optional[str]
    context_data: Optional[Dict[str, Any]]
    
    # State
    status: ApprovalStatus
    
    # Timing
    created_at: datetime
    expires_at: datetime
    updated_at: datetime
    decided_at: Optional[datetime]
    
    # Requester
    requested_by: str
    requested_by_role: Optional[str]
    
    # Decision details
    decision_reason: Optional[str]
    
    # Webhook status
    webhook_sent: bool
    webhook_sent_at: Optional[datetime]
    
    # Related data
    approvals: List[ApprovalDecisionResponse] = Field(default_factory=list)
    reminders: List[ApprovalReminderResponse] = Field(default_factory=list)
    
    # Computed properties
    required_approvals: List[str] = Field(default_factory=list)
    pending_approvals: List[str] = Field(default_factory=list)
    all_approvals_received: bool = False
    is_expired: bool = False

    class Config:
        from_attributes = True
        use_enum_values = True


class ApprovalRequestUpdate(BaseModel):
    """Schema for updating approval requests (limited fields)."""
    description: Optional[str] = Field(None, description="Updated description")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Updated context data")
    webhook_url: Optional[str] = Field(None, max_length=1000, description="Updated webhook URL")
    webhook_headers: Optional[Dict[str, str]] = Field(None, description="Updated webhook headers")

    class Config:
        use_enum_values = True


class ApprovalRequestListResponse(BaseModel):
    """Schema for paginated approval request lists."""
    items: List[ApprovalRequestResponse]
    total: int = Field(..., description="Total number of items matching query")
    page: int = Field(..., description="Current page number (1-based)")
    per_page: int = Field(..., description="Items per page")
    pages: int = Field(..., description="Total number of pages")
    has_next: bool = Field(..., description="Whether there are more pages")
    has_prev: bool = Field(..., description="Whether there are previous pages")


class ApprovalStatsResponse(BaseModel):
    """Schema for approval statistics."""
    total_requests: int = 0
    pending_requests: int = 0
    approved_requests: int = 0
    rejected_requests: int = 0
    expired_requests: int = 0
    
    # By type
    level_change_requests: int = 0
    iep_change_requests: int = 0
    consent_sensitive_requests: int = 0
    
    # Timing stats
    average_approval_time_hours: Optional[float] = None
    median_approval_time_hours: Optional[float] = None
    
    # Computed
    approval_rate: float = Field(default=0.0, description="Percentage of requests approved")
    
    class Config:
        from_attributes = True


class WebhookPayload(BaseModel):
    """Schema for webhook payloads sent on approval decisions."""
    event_type: str = Field(..., description="Type of event (approved/rejected/expired)")
    approval_request: ApprovalRequestResponse = Field(..., description="The approval request data")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Config:
        use_enum_values = True


class ErrorResponse(BaseModel):
    """Standard error response schema."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request ID for tracking")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Query parameter schemas
class ApprovalRequestFilters(BaseModel):
    """Query filters for approval requests."""
    tenant_id: Optional[uuid.UUID] = None
    approval_type: Optional[ApprovalType] = None
    resource_type: Optional[str] = None
    status: Optional[ApprovalStatus] = None
    requested_by: Optional[str] = None
    approver_role: Optional[ApproverRole] = None
    
    # Date range filters
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None
    expires_before: Optional[datetime] = None
    
    # Pagination
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    per_page: int = Field(default=50, ge=1, le=500, description="Items per page")
    
    # Sorting
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="Sort order")

    model_config = ConfigDict(use_enum_values=True)
