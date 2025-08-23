"""
Database configuration and models for SIS Bridge Service.
"""

from sqlalchemy import create_engine, Column, String, DateTime, Boolean, Integer, Text, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import UUID
from typing import Generator, Optional, Dict, Any
from uuid import uuid4
from datetime import datetime
from enum import Enum

from .config import get_settings

settings = get_settings()

# Create SQLAlchemy engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.environment == "development"
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Database dependency for FastAPI."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SISProvider(str, Enum):
    """Supported SIS providers."""
    CLEVER = "clever"
    CLASSLINK = "classlink"


class SyncStatus(str, Enum):
    """Sync job status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SyncType(str, Enum):
    """Types of sync operations."""
    FULL = "full"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class TenantSISProvider(Base):
    """SIS provider configuration for a tenant."""
    __tablename__ = "tenant_sis_providers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # clever, classlink
    name = Column(String(255), nullable=False)  # Display name
    
    # Configuration
    config = Column(JSON, nullable=False)  # Provider-specific config
    credentials_path = Column(String(500))  # Vault path for credentials
    
    # Sync settings
    enabled = Column(Boolean, default=True)
    sync_interval = Column(Integer, default=3600)  # seconds
    auto_sync = Column(Boolean, default=True)
    
    # Filters
    sync_users = Column(Boolean, default=True)
    sync_groups = Column(Boolean, default=True)
    sync_enrollments = Column(Boolean, default=True)
    user_filter = Column(JSON)  # Filter conditions
    group_filter = Column(JSON)
    
    # Webhooks
    webhook_enabled = Column(Boolean, default=False)
    webhook_secret = Column(String(255))
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_sync_at = Column(DateTime)
    
    # Relationships
    sync_jobs = relationship("SyncJob", back_populates="provider")


class SyncJob(Base):
    """Sync job tracking."""
    __tablename__ = "sync_jobs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("tenant_sis_providers.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Job details
    sync_type = Column(String(20), nullable=False)  # full, incremental, manual, webhook
    status = Column(String(20), default=SyncStatus.PENDING)
    
    # Progress tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    progress = Column(Integer, default=0)  # Percentage
    
    # Statistics
    stats = Column(JSON)  # Sync statistics
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    provider = relationship("TenantSISProvider", back_populates="sync_jobs")
    operations = relationship("SyncOperation", back_populates="job")


class SyncOperation(Base):
    """Individual sync operations within a job."""
    __tablename__ = "sync_operations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("sync_jobs.id"), nullable=False)
    
    # Operation details
    operation_type = Column(String(50), nullable=False)  # create_user, update_user, etc.
    resource_type = Column(String(50), nullable=False)  # user, group, enrollment
    resource_id = Column(String(255))  # External resource ID
    scim_resource_id = Column(UUID(as_uuid=True))  # SCIM resource ID
    
    # Status
    status = Column(String(20), default="pending")
    error_message = Column(Text)
    
    # Data
    source_data = Column(JSON)  # Original SIS data
    mapped_data = Column(JSON)  # Mapped SCIM data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    job = relationship("SyncJob", back_populates="operations")


class SISResourceMapping(Base):
    """Mapping between SIS resources and SCIM resources."""
    __tablename__ = "sis_resource_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    provider = Column(String(50), nullable=False)
    
    # Resource identifiers
    sis_resource_id = Column(String(255), nullable=False)
    sis_resource_type = Column(String(50), nullable=False)
    scim_resource_id = Column(UUID(as_uuid=True), nullable=False)
    scim_resource_type = Column(String(50), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime)
    
    # Additional mapping data
    mapping_data = Column(JSON)


class WebhookEvent(Base):
    """Webhook event tracking."""
    __tablename__ = "webhook_events"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    provider_id = Column(UUID(as_uuid=True), ForeignKey("tenant_sis_providers.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Event details
    event_type = Column(String(100), nullable=False)
    event_data = Column(JSON, nullable=False)
    headers = Column(JSON)
    
    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime)
    sync_job_id = Column(UUID(as_uuid=True), ForeignKey("sync_jobs.id"))
    
    # Error handling
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
