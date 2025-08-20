"""
Data models for Privacy Service
Pydantic models for request/response and database entities
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class PrivacyRequestType(str, Enum):
    """Types of privacy requests"""
    EXPORT = "export"
    ERASE = "erase"
    RETENTION = "retention"

class PrivacyRequestStatus(str, Enum):
    """Status of privacy requests"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DataCategory(str, Enum):
    """Categories of personal data"""
    PROFILE = "profile"
    LEARNING = "learning"
    PROGRESS = "progress"
    ASSESSMENTS = "assessments"
    INTERACTIONS = "interactions"
    ANALYTICS = "analytics"
    SYSTEM = "system"

# Database Models
class PrivacyRequest(Base):
    """Privacy request database model"""
    __tablename__ = "privacy_requests"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    learner_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    request_type = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default=PrivacyRequestStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Request details
    data_categories = Column(JSON, nullable=True)  # List of requested categories
    export_format = Column(String(20), nullable=True)  # JSON, CSV, etc.
    include_metadata = Column(Boolean, default=True)
    
    # Processing details
    file_path = Column(String(500), nullable=True)  # For export files
    file_size_bytes = Column(Integer, nullable=True)
    records_processed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    
    # Audit fields
    requested_by = Column(String(100), nullable=False)  # User ID or system
    requester_ip = Column(String(45), nullable=True)
    processed_by = Column(String(100), nullable=True)  # Worker/system ID

class AuditLog(Base):
    """Audit log for privacy operations"""
    __tablename__ = "privacy_audit_log"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    request_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    learner_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    
    event_type = Column(String(50), nullable=False)  # export_started, erase_completed, etc.
    event_data = Column(JSON, nullable=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

class DataRetentionPolicy(Base):
    """Data retention policies"""
    __tablename__ = "data_retention_policies"
    
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    data_category = Column(String(50), nullable=False, unique=True)
    retention_days = Column(Integer, nullable=False)
    checkpoint_count = Column(Integer, default=3)  # Keep N personalized checkpoints
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Policy details
    policy_description = Column(Text, nullable=True)
    legal_basis = Column(String(200), nullable=True)
    active = Column(Boolean, default=True)

# Request/Response Models
class ExportRequest(BaseModel):
    """Request model for data export"""
    learner_id: UUID = Field(..., description="Learner ID to export data for")
    data_categories: Optional[List[DataCategory]] = Field(
        default=None, 
        description="Specific data categories to export (default: all)"
    )
    export_format: str = Field(default="json", regex="^(json|csv)$")
    include_metadata: bool = Field(default=True, description="Include metadata in export")
    
    @validator('data_categories')
    def validate_categories(cls, v):
        if v is not None and len(v) == 0:
            raise ValueError("If specified, data_categories cannot be empty")
        return v

class ErasureRequest(BaseModel):
    """Request model for data erasure"""
    learner_id: UUID = Field(..., description="Learner ID to erase data for")
    data_categories: Optional[List[DataCategory]] = Field(
        default=None,
        description="Specific data categories to erase (default: all except required)"
    )
    confirm_irreversible: bool = Field(
        ..., 
        description="Confirmation that this operation is irreversible"
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Reason for erasure request"
    )
    
    @validator('confirm_irreversible')
    def validate_confirmation(cls, v):
        if not v:
            raise ValueError("Must confirm that erasure is irreversible")
        return v

class PrivacyRequestResponse(BaseModel):
    """Response model for privacy requests"""
    request_id: UUID
    learner_id: UUID
    request_type: PrivacyRequestType
    status: PrivacyRequestStatus
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    expires_at: Optional[datetime]
    
    # Export specific
    download_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    
    # Processing info
    records_processed: Optional[int] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class ExportStatusResponse(BaseModel):
    """Response for export status check"""
    request_id: UUID
    status: PrivacyRequestStatus
    progress_percentage: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    file_size_bytes: Optional[int] = None
    error_message: Optional[str] = None

class ErasureStatusResponse(BaseModel):
    """Response for erasure status check"""
    request_id: UUID
    status: PrivacyRequestStatus
    records_processed: Optional[int] = None
    completed_at: Optional[datetime] = None
    audit_trail_id: Optional[UUID] = None
    error_message: Optional[str] = None

class DataSummaryResponse(BaseModel):
    """Response showing data summary for a learner"""
    learner_id: UUID
    data_categories: Dict[DataCategory, Dict[str, Any]]
    total_records: int
    earliest_data: Optional[datetime] = None
    latest_data: Optional[datetime] = None
    retention_eligible: Dict[DataCategory, datetime] = Field(default_factory=dict)

class RetentionPolicyResponse(BaseModel):
    """Response for retention policy"""
    data_category: DataCategory
    retention_days: int
    checkpoint_count: int
    policy_description: Optional[str] = None
    legal_basis: Optional[str] = None
    
    class Config:
        from_attributes = True

# Internal Models
class ExportBundle(BaseModel):
    """Internal model for export bundle metadata"""
    learner_id: UUID
    created_at: datetime
    data_categories: List[DataCategory]
    export_format: str
    file_count: int
    total_size_bytes: int
    checksum: str
    
class AdapterDeletionRule(BaseModel):
    """Rules for adapter data deletion"""
    adapter_type: str
    delete_on_request: bool = True
    merge_upwards: bool = False  # Never merge adapter deletions upwards
    preserve_audit: bool = True
    
    @validator('merge_upwards')
    def validate_no_merge_upwards(cls, v):
        if v:
            raise ValueError("Adapter deletions must never merge upwards")
        return v
