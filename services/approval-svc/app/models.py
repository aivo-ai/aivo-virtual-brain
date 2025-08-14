# AIVO Approval Service - Data Models
# S2-10 Implementation - Approval Workflow with State Machine + TTL

from sqlalchemy import Column, String, DateTime, Text, Boolean, JSON, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime, timezone
from enum import Enum
import json

from .base import Base


class ApprovalStatus(Enum):
    """Approval status enumeration for state machine."""
    PENDING = "pending"
    APPROVED = "approved" 
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApproverRole(Enum):
    """Valid roles for approvers in the system."""
    GUARDIAN = "guardian"
    TEACHER = "teacher"
    CASE_MANAGER = "case_manager"
    DISTRICT_ADMIN = "district_admin"
    ADMINISTRATOR = "administrator"
    SERVICE_PROVIDER = "service_provider"


class ApprovalType(Enum):
    """Types of approvals that can be requested."""
    LEVEL_CHANGE = "level_change"
    IEP_CHANGE = "iep_change"
    CONSENT_SENSITIVE = "consent_sensitive"
    PLACEMENT_CHANGE = "placement_change"
    SERVICE_CHANGE = "service_change"


class ApprovalRequest(Base):
    """
    Central approval request model with state machine logic.
    Supports level changes, IEP changes, and consent-sensitive actions.
    """
    __tablename__ = "approval_requests"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Request metadata
    approval_type = Column(SQLEnum(ApprovalType, native_enum=False, length=50), nullable=False)
    resource_id = Column(String(255), nullable=False, index=True)  # ID of resource being approved
    resource_type = Column(String(100), nullable=False)  # e.g., "iep", "level", "consent"
    
    # Approval details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    context_data = Column(JSON, nullable=True)  # Additional context for the approval
    
    # State machine
    status = Column(SQLEnum(ApprovalStatus, native_enum=False), nullable=False, default=ApprovalStatus.PENDING)
    
    # Timing and TTL
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Requester information
    requested_by = Column(String(255), nullable=False)
    requested_by_role = Column(String(100), nullable=True)
    
    # Final decision metadata
    decided_at = Column(DateTime(timezone=True), nullable=True)
    decision_reason = Column(Text, nullable=True)
    
    # Webhook configuration
    webhook_url = Column(String(1000), nullable=True)
    webhook_headers = Column(JSON, nullable=True)
    webhook_sent = Column(Boolean, default=False)
    webhook_sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    approvals = relationship("ApprovalDecision", back_populates="request", cascade="all, delete-orphan")
    reminders = relationship("ApprovalReminder", back_populates="request", cascade="all, delete-orphan")
    
    @property
    def is_expired(self) -> bool:
        """Check if the approval request has expired."""
        return datetime.now(timezone.utc) > self.expires_at
    
    @property
    def required_approvals(self) -> list:
        """Get list of required approval roles from context data."""
        if not self.context_data:
            return []
        return self.context_data.get("required_roles", [])
    
    @property
    def pending_approvals(self) -> list:
        """Get list of roles that still need to approve."""
        approved_roles = {approval.approver_role for approval in self.approvals if approval.approved}
        required_roles = set(self.required_approvals)
        return list(required_roles - approved_roles)
    
    @property
    def all_approvals_received(self) -> bool:
        """Check if all required approvals have been received."""
        return len(self.pending_approvals) == 0 and len(self.required_approvals) > 0
    
    def can_transition_to(self, new_status: ApprovalStatus) -> bool:
        """Validate state machine transitions."""
        valid_transitions = {
            ApprovalStatus.PENDING: [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED],
            ApprovalStatus.APPROVED: [],  # Terminal state
            ApprovalStatus.REJECTED: [],  # Terminal state  
            ApprovalStatus.EXPIRED: []   # Terminal state
        }
        return new_status in valid_transitions.get(self.status, [])
    
    def __repr__(self):
        return f"<ApprovalRequest(id={self.id}, type={self.approval_type}, status={self.status})>"


class ApprovalDecision(Base):
    """Individual approval decisions from specific roles/users."""
    __tablename__ = "approval_decisions"
    
    # Primary identifiers  
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False, index=True)
    
    # Approver information
    approver_id = Column(String(255), nullable=False)  # User ID making the decision
    approver_role = Column(SQLEnum(ApproverRole, native_enum=False), nullable=False)
    approver_name = Column(String(255), nullable=True)  # Display name
    
    # Decision
    approved = Column(Boolean, nullable=False)
    comments = Column(Text, nullable=True)
    
    # Timing
    decided_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Metadata
    decision_metadata = Column(JSON, nullable=True)  # Additional decision context
    
    # Relationships
    request = relationship("ApprovalRequest", back_populates="approvals")
    
    def __repr__(self):
        status = "APPROVED" if self.approved else "REJECTED"
        return f"<ApprovalDecision(id={self.id}, role={self.approver_role}, status={status})>"


class ApprovalReminder(Base):
    """Reminders sent for pending approvals."""
    __tablename__ = "approval_reminders"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False, index=True)
    
    # Reminder details
    recipient_role = Column(SQLEnum(ApproverRole, native_enum=False), nullable=False)
    recipient_id = Column(String(255), nullable=False)
    
    # Timing
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    
    # Content
    reminder_type = Column(String(50), nullable=False, default="standard")  # standard, urgent, final
    message = Column(Text, nullable=True)
    
    # Status
    sent = Column(Boolean, default=False)
    notification_id = Column(String(255), nullable=True)  # ID from notification service
    
    # Relationships
    request = relationship("ApprovalRequest", back_populates="reminders")
    
    def __repr__(self):
        return f"<ApprovalReminder(id={self.id}, role={self.recipient_role}, sent={self.sent})>"


class ApprovalAuditLog(Base):
    """Audit trail for all approval-related activities."""
    __tablename__ = "approval_audit_logs"
    
    # Primary identifiers
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    request_id = Column(UUID(as_uuid=True), ForeignKey("approval_requests.id"), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)  # created, approved, rejected, expired, reminded
    actor_id = Column(String(255), nullable=False)
    actor_role = Column(String(100), nullable=True)
    
    # Event data
    event_data = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ApprovalAuditLog(id={self.id}, event={self.event_type}, actor={self.actor_id})>"
