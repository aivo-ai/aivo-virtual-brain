# AIVO IEP Service - SQLAlchemy Models
# S1-11 Implementation - IEP Data Models with CRDT and E-Signature Support

from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
from enum import Enum as PyEnum
import uuid
import json

Base = declarative_base()

class IEPStatus(PyEnum):
    """IEP document status enumeration."""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"

class SectionType(PyEnum):
    """IEP section type enumeration."""
    STUDENT_INFO = "student_info"
    PRESENT_LEVELS = "present_levels"
    ANNUAL_GOALS = "annual_goals"
    SERVICES = "services"
    PLACEMENT = "placement"
    TRANSITION = "transition"
    ASSESSMENTS = "assessments"
    ACCOMMODATIONS = "accommodations"

class SignatureRole(PyEnum):
    """E-signature role enumeration."""
    STUDENT = "student"
    PARENT_GUARDIAN = "parent_guardian"
    TEACHER = "teacher"
    CASE_MANAGER = "case_manager"
    ADMINISTRATOR = "administrator"
    SERVICE_PROVIDER = "service_provider"
    ADVOCATE = "advocate"

class CRDTOperation(PyEnum):
    """CRDT operation type for collaborative editing."""
    INSERT = "insert"
    DELETE = "delete"
    UPDATE = "update"
    RETAIN = "retain"

class IEP(Base):
    """
    Individual Education Program (IEP) document.
    
    Supports collaborative editing with CRDT operations and comprehensive e-signature workflow.
    """
    __tablename__ = "ieps"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    
    # Student and organizational context
    student_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, index=True)
    school_district = Column(String(200), nullable=False)
    school_name = Column(String(200), nullable=False)
    
    # Document metadata
    title = Column(String(300), nullable=False)
    academic_year = Column(String(20), nullable=False)  # e.g., "2024-2025"
    grade_level = Column(String(20), nullable=False)
    
    # Status and lifecycle
    status = Column(Enum(IEPStatus), nullable=False, default=IEPStatus.DRAFT, index=True)
    version = Column(Integer, nullable=False, default=1)
    is_current = Column(Boolean, nullable=False, default=True, index=True)
    
    # Key dates
    effective_date = Column(DateTime(timezone=True), nullable=True)
    expiration_date = Column(DateTime(timezone=True), nullable=True)
    next_review_date = Column(DateTime(timezone=True), nullable=True)
    
    # CRDT fields for collaborative editing
    crdt_state = Column(JSON, nullable=False, default=dict)  # Current CRDT state
    operation_log = Column(JSON, nullable=False, default=list)  # Operation history
    last_operation_id = Column(String(50), nullable=True)  # Last applied operation
    
    # E-signature metadata
    signature_required_roles = Column(JSON, nullable=False, default=list)  # Required signature roles
    signature_deadline = Column(DateTime(timezone=True), nullable=True)
    
    # Content hash for integrity verification
    content_hash = Column(String(64), nullable=True)  # SHA-256 hash
    
    # Audit fields
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_by = Column(String(50), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    sections = relationship("IEPSection", back_populates="iep", cascade="all, delete-orphan")
    signatures = relationship("ESignature", back_populates="iep", cascade="all, delete-orphan")
    evidence_attachments = relationship("EvidenceAttachment", back_populates="iep", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<IEP(id={self.id}, student_id={self.student_id}, status={self.status}, version={self.version})>"

class IEPSection(Base):
    """
    IEP document section with CRDT-enabled content.
    
    Each section supports collaborative editing and tracks detailed operation history.
    """
    __tablename__ = "iep_sections"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    iep_id = Column(UUID(as_uuid=True), ForeignKey("ieps.id"), nullable=False, index=True)
    
    # Section metadata
    section_type = Column(Enum(SectionType), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    order_index = Column(Integer, nullable=False, default=0)
    
    # CRDT content fields
    content = Column(Text, nullable=False, default="")  # Current resolved content
    crdt_operations = Column(JSON, nullable=False, default=list)  # CRDT operation log
    operation_counter = Column(Integer, nullable=False, default=0)  # Operation sequence counter
    
    # Collaboration metadata
    last_editor_id = Column(String(50), nullable=True)
    last_edited_at = Column(DateTime(timezone=True), nullable=True)
    edit_session_id = Column(String(50), nullable=True)  # Active editing session
    
    # Section-specific configuration
    is_required = Column(Boolean, nullable=False, default=True)
    is_locked = Column(Boolean, nullable=False, default=False)  # Locked for editing
    validation_rules = Column(JSON, nullable=False, default=dict)
    
    # Audit fields
    created_by = Column(String(50), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_by = Column(String(50), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    iep = relationship("IEP", back_populates="sections")
    
    def __repr__(self):
        return f"<IEPSection(id={self.id}, type={self.section_type}, title='{self.title}')>"

class ESignature(Base):
    """
    Electronic signature record for IEP documents.
    
    Tracks signature status, authentication, and legal compliance metadata.
    """
    __tablename__ = "e_signatures"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    iep_id = Column(UUID(as_uuid=True), ForeignKey("ieps.id"), nullable=False, index=True)
    
    # Signer information
    signer_id = Column(String(50), nullable=False, index=True)
    signer_name = Column(String(200), nullable=False)
    signer_email = Column(String(200), nullable=False)
    signer_role = Column(Enum(SignatureRole), nullable=False, index=True)
    
    # Signature status and metadata
    is_signed = Column(Boolean, nullable=False, default=False, index=True)
    signed_at = Column(DateTime(timezone=True), nullable=True)
    signature_method = Column(String(50), nullable=True)  # e.g., "digital_signature", "electronic_consent"
    
    # Authentication and verification
    auth_method = Column(String(100), nullable=True)  # Authentication method used
    ip_address = Column(String(45), nullable=True)  # IPv4/IPv6 address
    user_agent = Column(String(500), nullable=True)  # Browser/client information
    
    # Digital signature data
    signature_hash = Column(String(128), nullable=True)  # Cryptographic signature
    certificate_fingerprint = Column(String(128), nullable=True)  # Certificate identification
    
    # Legal compliance
    consent_text = Column(Text, nullable=True)  # Consent agreement text
    legal_notices = Column(JSON, nullable=False, default=dict)  # Legal notices and disclosures
    
    # Workflow metadata
    invitation_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_count = Column(Integer, nullable=False, default=0)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    iep = relationship("IEP", back_populates="signatures")
    
    def __repr__(self):
        return f"<ESignature(id={self.id}, signer={self.signer_name}, role={self.signer_role}, signed={self.is_signed})>"

class EvidenceAttachment(Base):
    """
    Evidence and supporting document attachments for IEP sections.
    
    Supports file metadata, categorization, and access control.
    """
    __tablename__ = "evidence_attachments"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    iep_id = Column(UUID(as_uuid=True), ForeignKey("ieps.id"), nullable=False, index=True)
    
    # File metadata
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    content_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    
    # Storage information
    storage_path = Column(String(1000), nullable=False)  # File storage location
    storage_provider = Column(String(50), nullable=False, default="local")  # Storage backend
    
    # Categorization and metadata
    evidence_type = Column(String(100), nullable=False)  # e.g., "assessment_report", "progress_data"
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=False, default=list)
    
    # Content verification
    checksum = Column(String(64), nullable=False)  # File integrity checksum
    virus_scan_status = Column(String(20), nullable=False, default="pending")
    virus_scan_at = Column(DateTime(timezone=True), nullable=True)
    
    # Access control
    is_confidential = Column(Boolean, nullable=False, default=False)
    access_level = Column(String(50), nullable=False, default="team")  # team, admin, public
    
    # Audit fields
    uploaded_by = Column(String(50), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    iep = relationship("IEP", back_populates="evidence_attachments")
    
    def __repr__(self):
        return f"<EvidenceAttachment(id={self.id}, filename='{self.filename}', type={self.evidence_type})>"

class CRDTOperationLog(Base):
    """
    Detailed CRDT operation log for audit and conflict resolution.
    
    Stores granular edit operations for collaborative editing support.
    """
    __tablename__ = "crdt_operation_log"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    iep_id = Column(UUID(as_uuid=True), ForeignKey("ieps.id"), nullable=False, index=True)
    section_id = Column(UUID(as_uuid=True), ForeignKey("iep_sections.id"), nullable=True, index=True)
    
    # Operation metadata
    operation_id = Column(String(50), nullable=False, unique=True, index=True)
    operation_type = Column(Enum(CRDTOperation), nullable=False, index=True)
    operation_data = Column(JSON, nullable=False)  # Operation payload
    
    # Operation context
    position = Column(Integer, nullable=False)  # Character position in document
    length = Column(Integer, nullable=False, default=0)  # Operation length
    content = Column(Text, nullable=True)  # Inserted/updated content
    
    # Attribution and timing
    author_id = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    client_timestamp = Column(DateTime(timezone=True), nullable=True)
    
    # Conflict resolution
    parent_operation_id = Column(String(50), nullable=True)  # Parent operation for conflict resolution
    vector_clock = Column(JSON, nullable=False, default=dict)  # Distributed timestamp
    
    def __repr__(self):
        return f"<CRDTOperationLog(id={self.operation_id}, type={self.operation_type}, author={self.author_id})>"
