"""
Legal Hold & eDiscovery Database Models

Manages legal preservation requirements that override standard data retention
and deletion policies for litigation, compliance, and regulatory needs.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from uuid import uuid4
import enum

from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Text, JSON, 
    ForeignKey, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY

Base = declarative_base()


class HoldStatus(enum.Enum):
    """Legal hold status enumeration"""
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class HoldScope(enum.Enum):
    """Legal hold scope enumeration"""
    TENANT = "tenant"
    LEARNER = "learner"
    TEACHER = "teacher"
    CLASSROOM = "classroom"
    TIMERANGE = "timerange"
    CUSTOM = "custom"


class ExportStatus(enum.Enum):
    """eDiscovery export status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class LegalHold(Base):
    """
    Legal Hold Entity
    
    Represents a legal preservation requirement that suspends normal
    data retention and deletion policies for specific scoped data.
    """
    __tablename__ = "legal_holds"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Hold Identification
    hold_number = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Legal Context
    case_number = Column(String(100), index=True)
    court_jurisdiction = Column(String(100))
    legal_basis = Column(String(50), nullable=False)  # litigation, investigation, regulatory
    custodian_attorney = Column(String(200))
    
    # Status and Lifecycle
    status = Column(String(20), nullable=False, default=HoldStatus.ACTIVE.value)
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    approved_by = Column(UUID(as_uuid=True), index=True)
    released_by = Column(UUID(as_uuid=True), index=True)
    
    # Temporal Bounds
    effective_date = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    expiration_date = Column(DateTime(timezone=True))
    released_date = Column(DateTime(timezone=True))
    
    # Scope Definition
    scope_type = Column(String(20), nullable=False)  # tenant, learner, teacher, classroom, timerange, custom
    scope_parameters = Column(JSON, nullable=False)  # flexible scope definition
    
    # Data Range
    data_start_date = Column(DateTime(timezone=True))
    data_end_date = Column(DateTime(timezone=True))
    
    # Hold Configuration
    preserve_deleted_data = Column(Boolean, default=True)
    preserve_system_logs = Column(Boolean, default=True)
    preserve_communications = Column(Boolean, default=True)
    preserve_file_metadata = Column(Boolean, default=True)
    
    # Notification and Review
    custodian_notification_sent = Column(Boolean, default=False)
    custodian_notification_date = Column(DateTime(timezone=True))
    review_required_by = Column(DateTime(timezone=True))
    next_review_date = Column(DateTime(timezone=True))
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    hold_custodians = relationship("HoldCustodian", back_populates="hold", cascade="all, delete-orphan")
    hold_exports = relationship("eDiscoveryExport", back_populates="hold", cascade="all, delete-orphan")
    hold_audit_logs = relationship("HoldAuditLog", back_populates="hold", cascade="all, delete-orphan")
    affected_entities = relationship("HoldAffectedEntity", back_populates="hold", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('active', 'released', 'expired', 'suspended')", name="valid_hold_status"),
        CheckConstraint("scope_type IN ('tenant', 'learner', 'teacher', 'classroom', 'timerange', 'custom')", name="valid_scope_type"),
        CheckConstraint("legal_basis IN ('litigation', 'investigation', 'regulatory', 'compliance')", name="valid_legal_basis"),
        CheckConstraint("effective_date <= COALESCE(expiration_date, effective_date)", name="valid_date_range"),
        Index("idx_hold_status_effective", "status", "effective_date"),
        Index("idx_hold_scope", "scope_type", "status"),
        Index("idx_hold_case", "case_number", "status"),
    )


class HoldCustodian(Base):
    """
    Hold Custodian
    
    Individuals responsible for data preservation under a legal hold.
    """
    __tablename__ = "hold_custodians"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hold_id = Column(UUID(as_uuid=True), ForeignKey("legal_holds.id"), nullable=False)
    
    # Custodian Identity
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Custodian Information
    name = Column(String(200), nullable=False)
    email = Column(String(255), nullable=False)
    role = Column(String(100))
    department = Column(String(100))
    
    # Notification Status
    notification_sent = Column(Boolean, default=False)
    notification_date = Column(DateTime(timezone=True))
    acknowledgment_received = Column(Boolean, default=False)
    acknowledgment_date = Column(DateTime(timezone=True))
    
    # Compliance Tracking
    training_completed = Column(Boolean, default=False)
    training_date = Column(DateTime(timezone=True))
    last_reminder_sent = Column(DateTime(timezone=True))
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    hold = relationship("LegalHold", back_populates="hold_custodians")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("hold_id", "user_id", name="unique_hold_custodian"),
        Index("idx_custodian_user", "user_id", "hold_id"),
        Index("idx_custodian_tenant", "tenant_id", "hold_id"),
    )


class HoldAffectedEntity(Base):
    """
    Hold Affected Entity
    
    Specific data entities (users, conversations, files) under legal hold.
    """
    __tablename__ = "hold_affected_entities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hold_id = Column(UUID(as_uuid=True), ForeignKey("legal_holds.id"), nullable=False)
    
    # Entity Identification
    entity_type = Column(String(50), nullable=False)  # user, conversation, file, assessment, etc.
    entity_id = Column(String(255), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Entity Metadata
    entity_name = Column(String(500))
    entity_description = Column(Text)
    entity_metadata = Column(JSON)
    
    # Hold Application
    hold_applied_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    deletion_attempts_blocked = Column(Integer, default=0)
    last_access_attempt = Column(DateTime(timezone=True))
    
    # Data Preservation Status
    preservation_verified = Column(Boolean, default=False)
    preservation_verification_date = Column(DateTime(timezone=True))
    backup_location = Column(String(500))
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    hold = relationship("LegalHold", back_populates="affected_entities")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("hold_id", "entity_type", "entity_id", name="unique_hold_entity"),
        Index("idx_entity_type_id", "entity_type", "entity_id"),
        Index("idx_entity_tenant", "tenant_id", "entity_type"),
        Index("idx_entity_hold", "hold_id", "entity_type"),
    )


class eDiscoveryExport(Base):
    """
    eDiscovery Export
    
    Immutable data exports for legal discovery and compliance audits.
    """
    __tablename__ = "ediscovery_exports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hold_id = Column(UUID(as_uuid=True), ForeignKey("legal_holds.id"), nullable=False)
    
    # Export Identification
    export_number = Column(String(100), unique=True, nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    
    # Export Configuration
    export_format = Column(String(50), default="structured_json")  # structured_json, pst, pdf, native
    include_metadata = Column(Boolean, default=True)
    include_system_logs = Column(Boolean, default=True)
    include_deleted_data = Column(Boolean, default=False)
    
    # Export Scope
    date_range_start = Column(DateTime(timezone=True))
    date_range_end = Column(DateTime(timezone=True))
    entity_filters = Column(JSON)  # specific entities to include/exclude
    data_types = Column(ARRAY(String))  # chat, audit, files, assessments, etc.
    
    # Export Status and Progress
    status = Column(String(20), nullable=False, default=ExportStatus.PENDING.value)
    progress_percentage = Column(Integer, default=0)
    total_records = Column(Integer, default=0)
    exported_records = Column(Integer, default=0)
    
    # File Information
    file_count = Column(Integer, default=0)
    total_size_bytes = Column(Integer, default=0)
    archive_location = Column(String(500))
    archive_password_hash = Column(String(255))
    
    # Integrity and Chain of Custody
    manifest_hash = Column(String(255))  # SHA-256 of complete manifest
    archive_hash = Column(String(255))   # SHA-256 of complete archive
    digital_signature = Column(Text)      # Digital signature for authenticity
    chain_of_custody = Column(JSON)       # Full custody chain documentation
    
    # Legal and Compliance
    requesting_attorney = Column(String(200))
    production_date = Column(DateTime(timezone=True))
    privilege_log_generated = Column(Boolean, default=False)
    redaction_log_generated = Column(Boolean, default=False)
    
    # Processing Details
    requested_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    processed_by = Column(UUID(as_uuid=True), index=True)
    approved_by = Column(UUID(as_uuid=True), index=True)
    
    # Temporal Fields
    requested_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_date = Column(DateTime(timezone=True))
    completed_date = Column(DateTime(timezone=True))
    expiration_date = Column(DateTime(timezone=True))
    
    # Error Handling
    error_message = Column(Text)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    hold = relationship("LegalHold", back_populates="hold_exports")
    export_items = relationship("ExportItem", back_populates="export", cascade="all, delete-orphan")
    access_logs = relationship("ExportAccessLog", back_populates="export", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('pending', 'in_progress', 'completed', 'failed', 'expired')", name="valid_export_status"),
        CheckConstraint("progress_percentage >= 0 AND progress_percentage <= 100", name="valid_progress"),
        CheckConstraint("exported_records <= total_records", name="valid_record_counts"),
        Index("idx_export_status_date", "status", "requested_date"),
        Index("idx_export_hold", "hold_id", "status"),
    )


class ExportItem(Base):
    """
    Export Item
    
    Individual data items included in an eDiscovery export.
    """
    __tablename__ = "export_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_id = Column(UUID(as_uuid=True), ForeignKey("ediscovery_exports.id"), nullable=False)
    
    # Item Identification
    item_type = Column(String(50), nullable=False)  # message, file, log_entry, assessment, etc.
    source_id = Column(String(255), nullable=False)
    source_system = Column(String(100), nullable=False)
    
    # Item Metadata
    item_title = Column(String(500))
    item_description = Column(Text)
    original_location = Column(String(500))
    file_extension = Column(String(10))
    mime_type = Column(String(100))
    
    # Temporal Information
    item_created_date = Column(DateTime(timezone=True))
    item_modified_date = Column(DateTime(timezone=True))
    item_accessed_date = Column(DateTime(timezone=True))
    
    # Size and Content
    size_bytes = Column(Integer, default=0)
    content_hash = Column(String(255))  # SHA-256 of content
    content_preview = Column(Text)      # First 1000 chars for search
    
    # Export Processing
    exported_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    export_path = Column(String(500))
    processing_notes = Column(Text)
    
    # Legal Processing
    privileged = Column(Boolean, default=False)
    redacted = Column(Boolean, default=False)
    confidential = Column(Boolean, default=False)
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    export = relationship("eDiscoveryExport", back_populates="export_items")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("export_id", "source_id", "source_system", name="unique_export_item"),
        Index("idx_item_type_export", "item_type", "export_id"),
        Index("idx_item_source", "source_system", "source_id"),
        Index("idx_item_dates", "item_created_date", "item_modified_date"),
    )


class HoldAuditLog(Base):
    """
    Hold Audit Log
    
    Comprehensive audit trail for all legal hold activities and access.
    """
    __tablename__ = "hold_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    hold_id = Column(UUID(as_uuid=True), ForeignKey("legal_holds.id"), nullable=False)
    
    # Event Information
    event_type = Column(String(50), nullable=False)  # creation, modification, access, export, deletion_blocked
    event_description = Column(Text, nullable=False)
    event_category = Column(String(50), nullable=False)  # administrative, access, compliance, system
    
    # Actor Information
    user_id = Column(UUID(as_uuid=True), index=True)
    user_name = Column(String(200))
    user_role = Column(String(100))
    system_component = Column(String(100))  # For automated system events
    
    # Context Information
    source_ip = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(String(500))
    session_id = Column(String(255))
    tenant_id = Column(UUID(as_uuid=True), index=True)
    
    # Event Details
    affected_entity_type = Column(String(50))
    affected_entity_id = Column(String(255))
    before_values = Column(JSON)
    after_values = Column(JSON)
    event_metadata = Column(JSON)
    
    # Risk and Compliance
    risk_level = Column(String(20), default="low")  # low, medium, high, critical
    compliance_relevant = Column(Boolean, default=True)
    retention_required = Column(Boolean, default=True)
    
    # Temporal Information
    event_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    hold = relationship("LegalHold", back_populates="hold_audit_logs")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("risk_level IN ('low', 'medium', 'high', 'critical')", name="valid_risk_level"),
        Index("idx_audit_event_type", "event_type", "event_timestamp"),
        Index("idx_audit_user", "user_id", "event_timestamp"),
        Index("idx_audit_hold", "hold_id", "event_timestamp"),
        Index("idx_audit_entity", "affected_entity_type", "affected_entity_id"),
    )


class ExportAccessLog(Base):
    """
    Export Access Log
    
    Audit trail for eDiscovery export access and downloads.
    """
    __tablename__ = "export_access_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    export_id = Column(UUID(as_uuid=True), ForeignKey("ediscovery_exports.id"), nullable=False)
    
    # Access Information
    access_type = Column(String(50), nullable=False)  # view, download, preview, verify
    access_granted = Column(Boolean, nullable=False)
    access_reason = Column(String(100))
    
    # Actor Information
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    user_name = Column(String(200))
    user_role = Column(String(100))
    attorney_bar_number = Column(String(50))
    
    # Context Information
    source_ip = Column(String(45))
    user_agent = Column(String(500))
    session_id = Column(String(255))
    
    # Access Details
    files_accessed = Column(ARRAY(String))
    download_size_bytes = Column(Integer, default=0)
    access_duration_seconds = Column(Integer)
    
    # Legal Context
    case_reference = Column(String(100))
    privilege_assertion = Column(Boolean, default=False)
    confidentiality_agreement = Column(Boolean, default=False)
    
    # Temporal Information
    access_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationships
    export = relationship("eDiscoveryExport", back_populates="access_logs")
    
    # Constraints
    __table_args__ = (
        Index("idx_access_export", "export_id", "access_timestamp"),
        Index("idx_access_user", "user_id", "access_timestamp"),
        Index("idx_access_type", "access_type", "access_granted"),
    )


class DataRetentionOverride(Base):
    """
    Data Retention Override
    
    Records overrides to standard data retention policies due to legal holds.
    """
    __tablename__ = "data_retention_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Override Information
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(255), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Original Retention Policy
    original_retention_days = Column(Integer)
    original_deletion_date = Column(DateTime(timezone=True))
    retention_policy_name = Column(String(100))
    
    # Override Details
    override_reason = Column(String(50), nullable=False)  # legal_hold, investigation, regulatory
    override_reference = Column(String(255))  # Hold ID or case number
    override_applied_by = Column(UUID(as_uuid=True), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    suspension_count = Column(Integer, default=0)
    
    # Temporal Information
    override_start_date = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    override_end_date = Column(DateTime(timezone=True))
    
    # Audit Fields
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Constraints
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", "override_reference", name="unique_retention_override"),
        CheckConstraint("override_reason IN ('legal_hold', 'investigation', 'regulatory', 'compliance')", name="valid_override_reason"),
        Index("idx_override_entity", "entity_type", "entity_id"),
        Index("idx_override_tenant", "tenant_id", "is_active"),
        Index("idx_override_reference", "override_reference", "is_active"),
    )
