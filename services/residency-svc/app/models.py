"""
Data Residency Models
Database models for region mapping and compliance tracking
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from sqlalchemy import Column, String, Boolean, DateTime, Text, JSON, Index, ForeignKey, Integer, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()

Base = declarative_base()


class RegionCode(str, Enum):
    """Supported region codes"""
    US_EAST = "us-east"
    US_WEST = "us-west"
    EU_WEST = "eu-west"
    EU_CENTRAL = "eu-central"
    APAC_SOUTH = "apac-south"
    APAC_EAST = "apac-east"
    CA_CENTRAL = "ca-central"


class ComplianceFramework(str, Enum):
    """Data compliance frameworks"""
    GDPR = "gdpr"
    CCPA = "ccpa"
    COPPA = "coppa"
    FERPA = "ferpa"
    PIPEDA = "pipeda"
    LGPD = "lgpd"


class ResidencyPolicy(Base):
    """
    Regional data residency policies for tenants and learners
    """
    __tablename__ = "residency_policies"
    
    policy_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    learner_id = Column(String(255), nullable=True, index=True)
    
    # Region assignment
    primary_region = Column(String(50), nullable=False, index=True)
    allowed_regions = Column(JSON, nullable=False, default=list)
    prohibited_regions = Column(JSON, nullable=False, default=list)
    
    # Compliance requirements
    compliance_frameworks = Column(JSON, nullable=False, default=list)
    data_classification = Column(String(50), nullable=False, default="standard")
    
    # Policy settings
    allow_cross_region_failover = Column(Boolean, default=False)
    require_encryption_at_rest = Column(Boolean, default=True)
    require_encryption_in_transit = Column(Boolean, default=True)
    data_retention_days = Column(Integer, nullable=True)
    
    # Emergency overrides
    emergency_override_enabled = Column(Boolean, default=False)
    emergency_contact = Column(String(255), nullable=True)
    
    # Metadata
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    access_logs = relationship("DataAccessLog", back_populates="policy")
    
    __table_args__ = (
        Index('idx_residency_tenant_learner', 'tenant_id', 'learner_id'),
        Index('idx_residency_region', 'primary_region'),
        Index('idx_residency_active', 'is_active'),
    )


class RegionInfrastructure(Base):
    """
    Regional infrastructure mapping for storage and compute resources
    """
    __tablename__ = "region_infrastructure"
    
    region_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    region_code = Column(String(50), nullable=False, unique=True)
    region_name = Column(String(255), nullable=False)
    
    # Storage infrastructure
    s3_bucket_name = Column(String(255), nullable=False)
    s3_region = Column(String(50), nullable=False)
    backup_bucket_name = Column(String(255), nullable=False)
    
    # Search infrastructure
    opensearch_domain = Column(String(255), nullable=False)
    opensearch_endpoint = Column(String(255), nullable=False)
    
    # Inference infrastructure
    inference_providers = Column(JSON, nullable=False, default=list)
    model_endpoints = Column(JSON, nullable=False, default=dict)
    
    # Network configuration
    vpc_id = Column(String(255), nullable=True)
    subnet_ids = Column(JSON, nullable=False, default=list)
    security_group_ids = Column(JSON, nullable=False, default=list)
    
    # Compliance certifications
    compliance_certifications = Column(JSON, nullable=False, default=list)
    data_center_location = Column(String(255), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True)
    health_check_url = Column(String(255), nullable=True)
    last_health_check = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DataAccessLog(Base):
    """
    Audit log for data access and cross-region operations
    """
    __tablename__ = "data_access_logs"
    
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    policy_id = Column(UUID(as_uuid=True), ForeignKey('residency_policies.policy_id'), nullable=False)
    
    # Request details
    tenant_id = Column(String(255), nullable=False, index=True)
    learner_id = Column(String(255), nullable=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    
    # Access details
    operation_type = Column(String(50), nullable=False)  # read, write, delete, inference
    resource_type = Column(String(50), nullable=False)   # file, model, data
    resource_id = Column(String(255), nullable=False)
    
    # Region information
    requested_region = Column(String(50), nullable=False)
    actual_region = Column(String(50), nullable=False)
    is_cross_region = Column(Boolean, default=False)
    
    # Compliance tracking
    compliance_check_result = Column(String(50), nullable=False)  # allowed, denied, override
    denial_reason = Column(Text, nullable=True)
    emergency_override = Column(Boolean, default=False)
    override_reason = Column(Text, nullable=True)
    override_authorized_by = Column(String(255), nullable=True)
    
    # Request metadata
    request_id = Column(String(255), nullable=False, index=True)
    request_headers = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Response details
    response_status = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=True)
    bytes_transferred = Column(BigInteger, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    policy = relationship("ResidencyPolicy", back_populates="access_logs")
    
    __table_args__ = (
        Index('idx_access_log_tenant_time', 'tenant_id', 'timestamp'),
        Index('idx_access_log_cross_region', 'is_cross_region', 'timestamp'),
        Index('idx_access_log_compliance', 'compliance_check_result'),
        Index('idx_access_log_emergency', 'emergency_override'),
    )


class EmergencyOverride(Base):
    """
    Emergency override requests for cross-region data access
    """
    __tablename__ = "emergency_overrides"
    
    override_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(String(255), nullable=False, index=True)
    
    # Override details
    reason = Column(Text, nullable=False)
    requested_by = Column(String(255), nullable=False)
    approved_by = Column(String(255), nullable=True)
    
    # Scope
    affected_learners = Column(JSON, nullable=False, default=list)
    source_region = Column(String(50), nullable=False)
    target_region = Column(String(50), nullable=False)
    
    # Timing
    valid_from = Column(DateTime, nullable=False)
    valid_until = Column(DateTime, nullable=False)
    
    # Status
    status = Column(String(50), default="pending")  # pending, approved, denied, expired
    approval_notes = Column(Text, nullable=True)
    
    # Audit trail
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    used_count = Column(Integer, default=0)
    last_used_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('idx_emergency_tenant_status', 'tenant_id', 'status'),
        Index('idx_emergency_validity', 'valid_from', 'valid_until'),
    )


# Pydantic Models for API

class ResidencyPolicyRequest(BaseModel):
    """Request model for creating/updating residency policies"""
    tenant_id: str = Field(..., description="Tenant ID")
    learner_id: Optional[str] = Field(None, description="Specific learner ID (optional)")
    primary_region: RegionCode = Field(..., description="Primary data region")
    allowed_regions: List[RegionCode] = Field(default=[], description="Additional allowed regions")
    prohibited_regions: List[RegionCode] = Field(default=[], description="Explicitly prohibited regions")
    compliance_frameworks: List[ComplianceFramework] = Field(default=[], description="Required compliance frameworks")
    data_classification: str = Field(default="standard", description="Data classification level")
    allow_cross_region_failover: bool = Field(default=False, description="Allow emergency failover")
    require_encryption_at_rest: bool = Field(default=True, description="Require encryption at rest")
    require_encryption_in_transit: bool = Field(default=True, description="Require encryption in transit")
    data_retention_days: Optional[int] = Field(None, description="Data retention period in days")
    emergency_contact: Optional[str] = Field(None, description="Emergency contact for overrides")


class ResidencyPolicyResponse(BaseModel):
    """Response model for residency policies"""
    policy_id: str = Field(..., description="Policy ID")
    tenant_id: str = Field(..., description="Tenant ID")
    learner_id: Optional[str] = Field(None, description="Learner ID")
    primary_region: str = Field(..., description="Primary region")
    allowed_regions: List[str] = Field(..., description="Allowed regions")
    prohibited_regions: List[str] = Field(..., description="Prohibited regions")
    compliance_frameworks: List[str] = Field(..., description="Compliance frameworks")
    allow_cross_region_failover: bool = Field(..., description="Cross-region failover allowed")
    is_active: bool = Field(..., description="Policy active status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class DataAccessRequest(BaseModel):
    """Request for data access with region routing"""
    tenant_id: str = Field(..., description="Tenant ID")
    learner_id: Optional[str] = Field(None, description="Learner ID")
    operation_type: str = Field(..., description="Operation type (read/write/inference)")
    resource_type: str = Field(..., description="Resource type")
    resource_id: str = Field(..., description="Resource identifier")
    requested_region: Optional[str] = Field(None, description="Requested region")
    emergency_override: bool = Field(default=False, description="Emergency override flag")
    override_reason: Optional[str] = Field(None, description="Reason for override")


class DataAccessResponse(BaseModel):
    """Response for data access request"""
    allowed: bool = Field(..., description="Access allowed")
    target_region: str = Field(..., description="Target region for operation")
    infrastructure: Dict[str, Any] = Field(..., description="Regional infrastructure details")
    compliance_notes: List[str] = Field(default=[], description="Compliance requirements")
    emergency_override_used: bool = Field(default=False, description="Emergency override was used")
    expires_at: Optional[datetime] = Field(None, description="Access expiration time")


class EmergencyOverrideRequest(BaseModel):
    """Request for emergency data residency override"""
    tenant_id: str = Field(..., description="Tenant ID")
    reason: str = Field(..., description="Reason for override")
    affected_learners: List[str] = Field(default=[], description="Affected learner IDs")
    source_region: str = Field(..., description="Source region")
    target_region: str = Field(..., description="Target region")
    duration_hours: int = Field(..., description="Override duration in hours")


# Database initialization
async def init_db():
    """Initialize database tables"""
    from app.config import settings
    from sqlalchemy.ext.asyncio import create_async_engine
    
    engine = create_async_engine(settings.database_url)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Database initialized successfully")
