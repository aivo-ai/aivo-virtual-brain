"""
Database Models for Authentication Service
"""

from sqlalchemy import (
    Column, String, DateTime, Boolean, Text, Integer, 
    ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()


class SSOProvider(Base):
    """SSO Provider configuration per tenant."""
    __tablename__ = "sso_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider_type = Column(String(50), nullable=False)  # 'saml' or 'oidc'
    provider_name = Column(String(100), nullable=False)  # Display name
    enabled = Column(Boolean, default=True)
    
    # SAML-specific configuration
    saml_idp_entity_id = Column(String(500), nullable=True)
    saml_idp_sso_url = Column(String(500), nullable=True)
    saml_idp_sls_url = Column(String(500), nullable=True)
    saml_idp_x509_cert = Column(Text, nullable=True)
    saml_name_id_format = Column(String(200), nullable=True)
    
    # OIDC-specific configuration
    oidc_issuer = Column(String(500), nullable=True)
    oidc_authorization_endpoint = Column(String(500), nullable=True)
    oidc_token_endpoint = Column(String(500), nullable=True)
    oidc_userinfo_endpoint = Column(String(500), nullable=True)
    oidc_jwks_uri = Column(String(500), nullable=True)
    oidc_client_id = Column(String(200), nullable=True)
    oidc_client_secret = Column(Text, nullable=True)
    
    # Group mapping configuration
    group_mapping_config = Column(JSON, nullable=True)  # Map IdP groups to roles
    attribute_mapping = Column(JSON, nullable=True)     # Map IdP attributes to user fields
    
    # JIT Provisioning settings
    jit_enabled = Column(Boolean, default=True)
    jit_default_role = Column(String(50), default="staff")
    jit_require_approval = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sso_sessions = relationship("SSOSession", back_populates="provider", cascade="all, delete-orphan")
    assertion_logs = relationship("SSOAssertionLog", back_populates="provider", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'provider_name', name='uq_tenant_provider_name'),
        Index('idx_sso_providers_tenant_enabled', 'tenant_id', 'enabled'),
    )


class SSOSession(Base):
    """SSO session tracking."""
    __tablename__ = "sso_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("sso_providers.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=True)  # null if JIT creation pending
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Session data
    session_id = Column(String(200), nullable=False, unique=True, index=True)
    nameid = Column(String(500), nullable=True)  # SAML NameID or OIDC sub
    subject = Column(String(500), nullable=False)  # User identifier from IdP
    email = Column(String(255), nullable=True)
    display_name = Column(String(200), nullable=True)
    groups = Column(JSON, nullable=True)  # Groups from IdP
    attributes = Column(JSON, nullable=True)  # Additional attributes
    
    # Session status
    session_state = Column(String(50), default="active")  # active, expired, logged_out
    jit_status = Column(String(50), nullable=True)  # pending, approved, rejected (for JIT)
    jit_approval_request_id = Column(UUID(as_uuid=True), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    last_accessed = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    provider = relationship("SSOProvider", back_populates="sso_sessions")
    
    __table_args__ = (
        Index('idx_sso_sessions_user_tenant', 'user_id', 'tenant_id'),
        Index('idx_sso_sessions_expires', 'expires_at'),
        Index('idx_sso_sessions_jit_status', 'jit_status'),
    )


class SSOAssertionLog(Base):
    """Audit log for SSO assertions (no PII beyond required fields)."""
    __tablename__ = "sso_assertion_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("sso_providers.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Assertion metadata (no PII)
    assertion_id = Column(String(200), nullable=True)  # SAML AssertionID or OIDC jti
    subject_hash = Column(String(64), nullable=False)  # SHA256 hash of subject
    session_index = Column(String(200), nullable=True)  # SAML SessionIndex
    
    # Validation results
    signature_valid = Column(Boolean, nullable=True)
    timestamp_valid = Column(Boolean, nullable=True)
    audience_valid = Column(Boolean, nullable=True)
    overall_valid = Column(Boolean, nullable=False)
    
    # Processing results
    user_created = Column(Boolean, default=False)
    user_updated = Column(Boolean, default=False)
    roles_assigned = Column(JSON, nullable=True)  # List of roles assigned
    jit_approval_required = Column(Boolean, default=False)
    
    # Timestamps
    assertion_timestamp = Column(DateTime, nullable=True)  # From assertion
    processed_at = Column(DateTime, default=datetime.utcnow)
    
    # Error information
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    provider = relationship("SSOProvider", back_populates="assertion_logs")
    
    __table_args__ = (
        Index('idx_assertion_logs_tenant_processed', 'tenant_id', 'processed_at'),
        Index('idx_assertion_logs_subject_hash', 'subject_hash'),
    )


class JITApprovalRequest(Base):
    """JIT user provisioning approval requests."""
    __tablename__ = "jit_approval_requests"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    sso_session_id = Column(UUID(as_uuid=True), ForeignKey("sso_sessions.id"), nullable=False)
    
    # User information for approval
    email = Column(String(255), nullable=False)
    display_name = Column(String(200), nullable=True)
    requested_roles = Column(JSON, nullable=True)  # Roles mapped from groups
    justification = Column(Text, nullable=True)
    
    # Approval workflow
    status = Column(String(50), default="pending")  # pending, approved, rejected
    approver_id = Column(UUID(as_uuid=True), nullable=True)
    approval_notes = Column(Text, nullable=True)
    approved_roles = Column(JSON, nullable=True)  # Final approved roles
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)  # Auto-reject after expiry
    processed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_jit_approval_tenant_status', 'tenant_id', 'status'),
        Index('idx_jit_approval_expires', 'expires_at'),
    )
