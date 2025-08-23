"""
Tenant Service - Database Models

Comprehensive models for tenants, users, groups, and SCIM 2.0 support
with SIS integration capabilities.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Text, JSON,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

Base = declarative_base()


class Tenant(Base):
    """Tenant model with SCIM and SIS integration support."""
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False)
    
    # SCIM Configuration
    scim_enabled = Column(Boolean, default=False)
    scim_base_url = Column(String(512))
    scim_bearer_token = Column(String(512))  # Encrypted
    scim_version = Column(String(10), default="2.0")
    
    # SIS Integration
    sis_enabled = Column(Boolean, default=False)
    sis_provider = Column(String(50))  # clever, classlink, etc.
    sis_config = Column(JSON)  # Provider-specific configuration
    sis_sync_enabled = Column(Boolean, default=False)
    sis_last_sync = Column(DateTime)
    
    # Metadata
    status = Column(String(20), default="active")
    seat_limit = Column(Integer)
    seat_allocated = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    groups = relationship("Group", back_populates="tenant", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_tenant_domain', 'domain'),
        Index('idx_tenant_status', 'status'),
    )


class User(Base):
    """User model with SCIM 2.0 attributes and SIS mapping."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # SCIM Core Attributes
    user_name = Column(String(255), nullable=False)
    external_id = Column(String(255))  # External system identifier
    display_name = Column(String(255))
    nick_name = Column(String(255))
    profile_url = Column(String(512))
    title = Column(String(255))
    user_type = Column(String(50))  # teacher, student, admin, parent
    locale = Column(String(10))
    timezone = Column(String(50))
    
    # SCIM Name Attributes
    formatted_name = Column(String(255))
    family_name = Column(String(255))
    given_name = Column(String(255))
    middle_name = Column(String(255))
    honorific_prefix = Column(String(50))
    honorific_suffix = Column(String(50))
    
    # SCIM Email Attributes
    primary_email = Column(String(255))
    work_email = Column(String(255))
    home_email = Column(String(255))
    
    # SCIM Phone Attributes
    work_phone = Column(String(50))
    home_phone = Column(String(50))
    mobile_phone = Column(String(50))
    
    # SCIM Address Attributes
    work_address = Column(JSON)
    home_address = Column(JSON)
    
    # SCIM Enterprise Extension
    employee_number = Column(String(50))
    cost_center = Column(String(50))
    organization = Column(String(255))
    division = Column(String(255))
    department = Column(String(255))
    manager_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    
    # SIS Integration
    sis_user_id = Column(String(255))  # Original SIS user ID
    sis_source = Column(String(50))  # clever, classlink
    sis_last_sync = Column(DateTime)
    sis_metadata = Column(JSON)  # Provider-specific data
    
    # Status and Control
    active = Column(Boolean, default=True)
    password = Column(String(255))  # Hashed
    must_change_password = Column(Boolean, default=False)
    password_never_expires = Column(Boolean, default=False)
    account_disabled = Column(Boolean, default=False)
    
    # SCIM Metadata
    resource_type = Column(String(20), default="User")
    version = Column(String(50), default="1")  # ETag support
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Seat Management
    seat_allocated = Column(Boolean, default=False)
    seat_allocated_at = Column(DateTime)
    seat_type = Column(String(50))  # teacher, student, admin
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    manager = relationship("User", remote_side=[id], backref="direct_reports")
    group_memberships = relationship("GroupMembership", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'user_name', name='uq_tenant_username'),
        UniqueConstraint('tenant_id', 'external_id', name='uq_tenant_external_id'),
        UniqueConstraint('tenant_id', 'sis_user_id', name='uq_tenant_sis_user_id'),
        Index('idx_user_tenant_username', 'tenant_id', 'user_name'),
        Index('idx_user_external_id', 'external_id'),
        Index('idx_user_sis', 'sis_source', 'sis_user_id'),
        Index('idx_user_email', 'primary_email'),
        Index('idx_user_active', 'active'),
    )


class Group(Base):
    """Group model with SCIM 2.0 attributes."""
    __tablename__ = "groups"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # SCIM Core Attributes
    display_name = Column(String(255), nullable=False)
    external_id = Column(String(255))
    
    # Group Type and Metadata
    group_type = Column(String(50))  # class, department, role
    description = Column(Text)
    
    # SIS Integration
    sis_group_id = Column(String(255))
    sis_source = Column(String(50))
    sis_last_sync = Column(DateTime)
    sis_metadata = Column(JSON)
    
    # SCIM Metadata
    resource_type = Column(String(20), default="Group")
    version = Column(String(50), default="1")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="groups")
    memberships = relationship("GroupMembership", back_populates="group", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('tenant_id', 'display_name', name='uq_tenant_group_name'),
        UniqueConstraint('tenant_id', 'external_id', name='uq_tenant_group_external_id'),
        UniqueConstraint('tenant_id', 'sis_group_id', name='uq_tenant_sis_group_id'),
        Index('idx_group_tenant_name', 'tenant_id', 'display_name'),
        Index('idx_group_external_id', 'external_id'),
        Index('idx_group_sis', 'sis_source', 'sis_group_id'),
    )


class GroupMembership(Base):
    """Group membership relationship with SCIM 2.0 support."""
    __tablename__ = "group_memberships"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    # Membership metadata
    member_type = Column(String(20), default="User")  # User, Group (nested)
    role = Column(String(50))  # student, teacher, admin in class context
    
    # SIS Integration
    sis_membership_id = Column(String(255))
    sis_source = Column(String(50))
    sis_last_sync = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    group = relationship("Group", back_populates="memberships")
    user = relationship("User", back_populates="group_memberships")
    
    __table_args__ = (
        UniqueConstraint('group_id', 'user_id', name='uq_group_user_membership'),
        Index('idx_membership_group', 'group_id'),
        Index('idx_membership_user', 'user_id'),
        Index('idx_membership_sis', 'sis_source', 'sis_membership_id'),
    )


class SCIMOperation(Base):
    """Audit log for SCIM operations."""
    __tablename__ = "scim_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Operation details
    operation_type = Column(String(20), nullable=False)  # CREATE, UPDATE, DELETE, PATCH
    resource_type = Column(String(20), nullable=False)  # User, Group
    resource_id = Column(UUID(as_uuid=True))
    external_id = Column(String(255))
    
    # Request details
    http_method = Column(String(10))
    endpoint = Column(String(255))
    request_body = Column(JSON)
    response_status = Column(Integer)
    response_body = Column(JSON)
    
    # Client information
    client_ip = Column(String(45))
    user_agent = Column(String(512))
    scim_client_id = Column(String(255))
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_scim_op_tenant', 'tenant_id'),
        Index('idx_scim_op_type', 'operation_type'),
        Index('idx_scim_op_resource', 'resource_type', 'resource_id'),
        Index('idx_scim_op_timestamp', 'created_at'),
    )


class SISSync(Base):
    """SIS synchronization job tracking."""
    __tablename__ = "sis_syncs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    
    # Sync details
    sync_type = Column(String(20), nullable=False)  # full, incremental, manual
    sis_provider = Column(String(50), nullable=False)
    status = Column(String(20), default="running")  # running, completed, failed
    
    # Progress tracking
    total_users = Column(Integer, default=0)
    processed_users = Column(Integer, default=0)
    total_groups = Column(Integer, default=0)
    processed_groups = Column(Integer, default=0)
    
    # Results
    users_created = Column(Integer, default=0)
    users_updated = Column(Integer, default=0)
    users_deactivated = Column(Integer, default=0)
    groups_created = Column(Integer, default=0)
    groups_updated = Column(Integer, default=0)
    memberships_created = Column(Integer, default=0)
    memberships_removed = Column(Integer, default=0)
    
    # Error tracking
    error_count = Column(Integer, default=0)
    error_details = Column(JSON)
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    next_sync_at = Column(DateTime)
    
    __table_args__ = (
        Index('idx_sis_sync_tenant', 'tenant_id'),
        Index('idx_sis_sync_status', 'status'),
        Index('idx_sis_sync_timestamp', 'started_at'),
    )


# Database utilities
def create_tables(engine):
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_version_etag(resource) -> str:
    """Generate ETag for SCIM resource versioning."""
    import hashlib
    data = f"{resource.id}-{resource.version}-{resource.updated_at}"
    return hashlib.md5(data.encode()).hexdigest()


def increment_version(resource):
    """Increment resource version for optimistic locking."""
    try:
        current = int(resource.version)
        resource.version = str(current + 1)
    except (ValueError, TypeError):
        resource.version = "2"
    resource.updated_at = datetime.utcnow()
