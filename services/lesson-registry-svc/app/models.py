"""
Lesson Registry - Database Models

Content versioning system for educational materials with asset management
and CDN signing capabilities.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class Lesson(Base):
    """
    Core lesson entity representing educational content.
    
    Contains metadata about the lesson and serves as the parent
    for versioned content and associated assets.
    """
    __tablename__ = "lesson"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    subject = Column(String(100), nullable=False, index=True)
    grade_level = Column(String(20), index=True)
    
    # Content categorization
    topic = Column(String(200), index=True)
    curriculum_standard = Column(String(100))
    difficulty_level = Column(String(20), default="intermediate")
    
    # Publishing metadata
    status = Column(String(20), default="draft", index=True)  # draft, published, archived
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Content management
    is_active = Column(Boolean, default=True, index=True)
    published_at = Column(DateTime, index=True)
    
    # Relationships
    versions = relationship("Version", back_populates="lesson", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_lesson_subject_grade', 'subject', 'grade_level'),
        Index('idx_lesson_status_active', 'status', 'is_active'),
        Index('idx_lesson_created_by_date', 'created_by', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Lesson(id={self.id}, title='{self.title}', subject='{self.subject}')>"


class Version(Base):
    """
    Versioned lesson content with semantic versioning support.
    
    Each version represents a distinct iteration of the lesson content
    with associated assets and manifest data.
    """
    __tablename__ = "version"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Version information
    version_number = Column(String(20), nullable=False)  # e.g., "1.0.0", "2.1.3"
    version_name = Column(String(100))  # Optional human-readable name
    changelog = Column(Text)
    
    # Content metadata
    content_type = Column(String(50), default="interactive")  # interactive, video, assessment, etc.
    duration_minutes = Column(Integer)
    learning_objectives = Column(Text)  # JSON array as text
    
    # Version status and publishing
    status = Column(String(20), default="draft", index=True)  # draft, published, deprecated
    is_current = Column(Boolean, default=False, index=True)  # Only one current version per lesson
    
    # Audit trail
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    published_at = Column(DateTime, index=True)
    
    # Content validation
    manifest_checksum = Column(String(64))  # SHA-256 of complete manifest
    total_assets = Column(Integer, default=0)
    total_size_bytes = Column(BigInteger, default=0)
    
    # Relationships
    lesson = relationship("Lesson", back_populates="versions")
    assets = relationship("Asset", back_populates="version", cascade="all, delete-orphan")
    
    # Indexes for performance and uniqueness
    __table_args__ = (
        Index('idx_version_lesson_number', 'lesson_id', 'version_number', unique=True),
        Index('idx_version_current', 'lesson_id', 'is_current'),
        Index('idx_version_status_published', 'status', 'published_at'),
    )
    
    def __repr__(self):
        return f"<Version(id={self.id}, lesson_id={self.lesson_id}, version='{self.version_number}')>"


class Asset(Base):
    """
    Individual assets associated with lesson versions.
    
    Tracks files stored in S3/MinIO with integrity checks and 
    metadata for CDN delivery and caching.
    """
    __tablename__ = "asset"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("version.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File identification
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False, index=True)  # Full S3 object key
    asset_path = Column(String(500), nullable=False)  # Logical path in lesson structure
    
    # File metadata
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False, index=True)  # SHA-256
    
    # Asset categorization
    asset_type = Column(String(50), nullable=False, index=True)  # html, css, js, image, video, audio, etc.
    is_entry_point = Column(Boolean, default=False)  # Main lesson file
    is_required = Column(Boolean, default=True)  # Critical for lesson functionality
    
    # Caching and delivery
    cache_duration_seconds = Column(Integer, default=3600)  # CDN cache TTL
    compression_enabled = Column(Boolean, default=True)
    
    # Upload and validation metadata
    uploaded_at = Column(DateTime, default=datetime.utcnow, index=True)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    validated_at = Column(DateTime, index=True)
    validation_status = Column(String(20), default="pending")  # pending, valid, invalid
    
    # Relationships
    version = relationship("Version", back_populates="assets")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_asset_version_path', 'version_id', 'asset_path', unique=True),
        Index('idx_asset_type_required', 'asset_type', 'is_required'),
        Index('idx_asset_checksum_size', 'checksum', 'size_bytes'),
        Index('idx_asset_uploaded', 'uploaded_at', 'uploaded_by'),
    )
    
    def __repr__(self):
        return f"<Asset(id={self.id}, filename='{self.filename}', type='{self.asset_type}')>"


# Database utility functions
def get_current_version(lesson_id: uuid.UUID) -> Optional[Version]:
    """Get the current published version of a lesson."""
    from sqlalchemy.orm import sessionmaker
    from .database import engine
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        return session.query(Version).filter(
            Version.lesson_id == lesson_id,
            Version.is_current == True,
            Version.status == "published"
        ).first()
    finally:
        session.close()


def get_lesson_versions(lesson_id: uuid.UUID, include_drafts: bool = False) -> List[Version]:
    """Get all versions of a lesson, optionally including drafts."""
    from sqlalchemy.orm import sessionmaker
    from .database import engine
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        query = session.query(Version).filter(Version.lesson_id == lesson_id)
        
        if not include_drafts:
            query = query.filter(Version.status == "published")
            
        return query.order_by(Version.created_at.desc()).all()
    finally:
        session.close()


def validate_asset_integrity(asset: Asset, file_content: bytes) -> bool:
    """Validate asset integrity using checksum and size."""
    import hashlib
    
    # Verify file size
    if len(file_content) != asset.size_bytes:
        return False
    
    # Verify checksum
    file_hash = hashlib.sha256(file_content).hexdigest()
    return file_hash == asset.checksum
