# AIVO IEP Service - Strawberry GraphQL Schema
# S1-11 Implementation - GraphQL Schema with CRDT and E-Signature Support

import strawberry
from strawberry.scalars import JSON
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

# GraphQL Enums
@strawberry.enum
class IEPStatus:
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"

@strawberry.enum
class SectionType:
    STUDENT_INFO = "student_info"
    PRESENT_LEVELS = "present_levels"
    ANNUAL_GOALS = "annual_goals"
    SERVICES = "services"
    PLACEMENT = "placement"
    TRANSITION = "transition"
    ASSESSMENTS = "assessments"
    ACCOMMODATIONS = "accommodations"

@strawberry.enum
class SignatureRole:
    STUDENT = "student"
    PARENT_GUARDIAN = "parent_guardian"
    TEACHER = "teacher"
    CASE_MANAGER = "case_manager"
    ADMINISTRATOR = "administrator"
    SERVICE_PROVIDER = "service_provider"
    ADVOCATE = "advocate"

@strawberry.enum
class CRDTOperationType:
    INSERT = "insert"
    DELETE = "delete"
    UPDATE = "update"
    RETAIN = "retain"

# GraphQL Types
@strawberry.type
class CRDTOperation:
    """CRDT operation for collaborative editing."""
    operation_id: str
    operation_type: CRDTOperationType
    position: int
    length: int
    content: Optional[str] = None
    author_id: str
    timestamp: datetime
    vector_clock: JSON

@strawberry.type
class ESignature:
    """Electronic signature information."""
    id: str
    signer_id: str
    signer_name: str
    signer_email: str
    signer_role: SignatureRole
    is_signed: bool
    signed_at: Optional[datetime] = None
    signature_method: Optional[str] = None
    auth_method: Optional[str] = None
    invitation_sent_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    created_at: datetime

@strawberry.type
class EvidenceAttachment:
    """Evidence attachment metadata."""
    id: str
    filename: str
    original_filename: str
    content_type: str
    file_size: int
    evidence_type: str
    description: Optional[str] = None
    tags: List[str]
    is_confidential: bool
    access_level: str
    uploaded_by: str
    uploaded_at: datetime

@strawberry.type
class IEPSection:
    """IEP document section with CRDT support."""
    id: str
    section_type: SectionType
    title: str
    order_index: int
    content: str
    operation_counter: int
    last_editor_id: Optional[str] = None
    last_edited_at: Optional[datetime] = None
    is_required: bool
    is_locked: bool
    validation_rules: JSON
    created_at: datetime
    updated_at: datetime

@strawberry.type
class IEP:
    """Individual Education Program document."""
    id: str
    student_id: str
    tenant_id: str
    school_district: str
    school_name: str
    title: str
    academic_year: str
    grade_level: str
    status: IEPStatus
    version: int
    is_current: bool
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    next_review_date: Optional[datetime] = None
    crdt_state: JSON
    last_operation_id: Optional[str] = None
    signature_required_roles: List[str]
    signature_deadline: Optional[datetime] = None
    content_hash: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_by: str
    updated_at: datetime
    
    # Relationships
    sections: List[IEPSection]
    signatures: List[ESignature]
    evidence_attachments: List[EvidenceAttachment]

# Input Types
@strawberry.input
class IEPCreateInput:
    """Input for creating a new IEP."""
    student_id: str
    tenant_id: str
    school_district: str
    school_name: str
    title: str
    academic_year: str
    grade_level: str
    effective_date: Optional[datetime] = None
    expiration_date: Optional[datetime] = None
    signature_required_roles: List[str] = strawberry.field(default_factory=list)

@strawberry.input
class IEPSectionUpsertInput:
    """Input for upserting an IEP section."""
    iep_id: str
    section_type: SectionType
    title: str
    content: str
    order_index: Optional[int] = None
    validation_rules: Optional[JSON] = None

@strawberry.input
class CRDTOperationInput:
    """Input for CRDT operation."""
    operation_id: str
    operation_type: CRDTOperationType
    position: int
    length: int
    content: Optional[str] = None
    author_id: str
    vector_clock: JSON

@strawberry.input
class EvidenceAttachmentInput:
    """Input for attaching evidence."""
    iep_id: str
    filename: str
    content_type: str
    file_size: int
    evidence_type: str
    description: Optional[str] = None
    tags: List[str] = strawberry.field(default_factory=list)
    is_confidential: bool = False

@strawberry.input
class ESignatureInviteInput:
    """Input for inviting e-signature."""
    iep_id: str
    signer_email: str
    signer_name: str
    signer_role: SignatureRole
    expires_at: Optional[datetime] = None

# Response Types
@strawberry.type
class IEPMutationResponse:
    """Standard response for IEP mutations."""
    success: bool
    message: str
    iep: Optional[IEP] = None
    errors: List[str] = strawberry.field(default_factory=list)

@strawberry.type
class IEPSectionMutationResponse:
    """Response for IEP section mutations."""
    success: bool
    message: str
    section: Optional[IEPSection] = None
    errors: List[str] = strawberry.field(default_factory=list)

@strawberry.type
class EvidenceAttachmentResponse:
    """Response for evidence attachment operations."""
    success: bool
    message: str
    attachment: Optional[EvidenceAttachment] = None
    upload_url: Optional[str] = None  # Pre-signed upload URL
    errors: List[str] = strawberry.field(default_factory=list)

@strawberry.type
class ESignatureResponse:
    """Response for e-signature operations."""
    success: bool
    message: str
    signature: Optional[ESignature] = None
    signing_url: Optional[str] = None  # E-signature portal URL
    errors: List[str] = strawberry.field(default_factory=list)

# Subscription Types
@strawberry.type
class IEPUpdateEvent:
    """Real-time IEP update event."""
    iep_id: str
    event_type: str  # "section_updated", "signature_completed", "status_changed"
    section_id: Optional[str] = None
    operation: Optional[CRDTOperation] = None
    updated_by: str
    timestamp: datetime
    metadata: JSON

# Filter and Pagination Types
@strawberry.input
class IEPFilterInput:
    """Filter criteria for IEP queries."""
    student_id: Optional[str] = None
    tenant_id: Optional[str] = None
    status: Optional[IEPStatus] = None
    academic_year: Optional[str] = None
    is_current: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None

@strawberry.input
class PaginationInput:
    """Pagination parameters."""
    offset: int = 0
    limit: int = 50
    order_by: Optional[str] = None
    order_direction: str = "ASC"

@strawberry.type
class IEPConnection:
    """Paginated IEP results."""
    items: List[IEP]
    total_count: int
    has_next_page: bool
    has_previous_page: bool
