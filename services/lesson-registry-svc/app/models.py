"""
Lesson Registry - Database Models

Content versioning system for educational materials with asset management,
CDN signing capabilities, and authoring workflow support.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class LessonDraft(Base):
    """
    Draft content for lessons during authoring process.
    
    Stores work-in-progress lesson content with block-based editor data,
    assets, and metadata before publishing to versions.
    """
    __tablename__ = "lesson_draft"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lesson.id", ondelete="CASCADE"), nullable=True, index=True)  # Null for new lessons
    
    # Draft metadata
    title = Column(String(255), nullable=False)
    description = Column(Text)
    subject = Column(String(100), nullable=False)
    grade_level = Column(String(20))
    topic = Column(String(200))
    curriculum_standard = Column(String(100))
    difficulty_level = Column(String(20), default="intermediate")
    
    # Content data (block editor format)
    content_blocks = Column(JSON)  # JSON array of content blocks
    learning_objectives = Column(JSON)  # JSON array of learning objectives
    assessment_data = Column(JSON)  # Quiz/assessment configuration
    
    # Draft settings
    estimated_duration = Column(Integer)  # minutes
    language = Column(String(10), default="en")
    tags = Column(JSON)  # JSON array of tags
    
    # Authoring status
    status = Column(String(20), default="editing", index=True)  # editing, ready_for_review, under_review
    completion_percentage = Column(Integer, default=0)  # 0-100
    
    # Validation and readiness
    validation_errors = Column(JSON)  # JSON array of validation issues
    is_valid = Column(Boolean, default=False)
    last_validated_at = Column(DateTime)
    
    # Author information
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_edited_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    
    # Publishing preparation
    changelog = Column(Text)
    target_version = Column(String(20))  # Intended version number
    
    # Relationships
    lesson = relationship("Lesson", backref="drafts")
    assets = relationship("DraftAsset", back_populates="draft", cascade="all, delete-orphan")
    reviews = relationship("ContentReview", back_populates="draft", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_draft_lesson_status', 'lesson_id', 'status'),
        Index('idx_draft_author_updated', 'created_by', 'updated_at'),
        Index('idx_draft_valid_ready', 'is_valid', 'status'),
    )


class DraftAsset(Base):
    """
    Assets associated with lesson drafts during authoring.
    
    Temporary storage for uploaded assets before they're moved
    to permanent storage during publishing.
    """
    __tablename__ = "draft_asset"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("lesson_draft.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File identification
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    temp_s3_key = Column(String(500), nullable=False, index=True)  # Temporary S3 location
    
    # File metadata
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(BigInteger, nullable=False)
    checksum = Column(String(64), nullable=False)
    
    # Asset categorization
    asset_type = Column(String(50), nullable=False, index=True)  # image, video, audio, document
    usage_context = Column(String(100))  # Where the asset is used in content
    alt_text = Column(String(500))  # Accessibility description
    
    # Upload metadata
    uploaded_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Processing status
    processing_status = Column(String(20), default="uploaded")  # uploaded, processing, ready, error
    processing_error = Column(Text)
    optimized_variants = Column(JSON)  # Different sizes/formats generated
    
    # Relationships
    draft = relationship("LessonDraft", back_populates="assets")
    
    __table_args__ = (
        Index('idx_draft_asset_type_status', 'asset_type', 'processing_status'),
        Index('idx_draft_asset_uploaded', 'uploaded_at'),
    )


class ContentReview(Base):
    """
    Review and approval workflow for lesson content.
    
    Tracks review requests, feedback, and approval decisions
    for lesson drafts before publishing.
    """
    __tablename__ = "content_review"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("lesson_draft.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Review metadata
    review_type = Column(String(50), default="content")  # content, accessibility, curriculum_alignment
    status = Column(String(20), default="pending", index=True)  # pending, approved, rejected, needs_changes
    priority = Column(String(20), default="normal")  # low, normal, high, urgent
    
    # Review assignment
    requested_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    assigned_to = Column(UUID(as_uuid=True), nullable=True, index=True)
    reviewer_role = Column(String(50))  # district_admin, curriculum_specialist, accessibility_expert
    
    # Review content
    request_notes = Column(Text)
    review_feedback = Column(JSON)  # Structured feedback with line/block references
    approval_notes = Column(Text)
    
    # Review decision
    decision = Column(String(20))  # approved, rejected, conditional
    decision_reason = Column(Text)
    conditions = Column(JSON)  # Required changes for conditional approval
    
    # Timing
    requested_at = Column(DateTime, default=datetime.utcnow, index=True)
    assigned_at = Column(DateTime)
    completed_at = Column(DateTime)
    due_date = Column(DateTime)
    
    # Relationships
    draft = relationship("LessonDraft", back_populates="reviews")
    
    __table_args__ = (
        Index('idx_review_status_assigned', 'status', 'assigned_to'),
        Index('idx_review_due_date', 'due_date'),
        Index('idx_review_type_status', 'review_type', 'status'),
    )


class PublishingWorkflow(Base):
    """
    Publishing workflow tracking from draft to live lesson version.
    
    Manages the complete publishing pipeline including validation,
    approval, asset processing, and version creation.
    """
    __tablename__ = "publishing_workflow"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("lesson_draft.id"), nullable=False, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey("version.id"), nullable=True, index=True)
    
    # Workflow status
    status = Column(String(30), default="initiated", index=True)  
    # initiated, validating, pending_approval, approved, processing_assets, publishing, published, failed
    
    # Workflow configuration
    requires_approval = Column(Boolean, default=True)
    approval_required_roles = Column(JSON)  # Roles that must approve
    auto_publish_on_approval = Column(Boolean, default=True)
    
    # Publishing settings
    target_version_number = Column(String(20), nullable=False)
    publish_immediately = Column(Boolean, default=False)
    scheduled_publish_at = Column(DateTime)
    
    # Progress tracking
    validation_step_completed = Column(Boolean, default=False)
    approval_step_completed = Column(Boolean, default=False)
    asset_processing_completed = Column(Boolean, default=False)
    version_creation_completed = Column(Boolean, default=False)
    
    # Results and errors
    validation_results = Column(JSON)
    processing_errors = Column(JSON)
    success_metrics = Column(JSON)  # Assets processed, size, etc.
    
    # Audit trail
    initiated_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    initiated_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    approved_by = Column(UUID(as_uuid=True))
    approved_at = Column(DateTime)
    
    # Relationships
    draft = relationship("LessonDraft")
    version = relationship("Version")
    
    __table_args__ = (
        Index('idx_workflow_status_initiated', 'status', 'initiated_at'),
        Index('idx_workflow_scheduled', 'scheduled_publish_at'),
    )


class LocalizedContent(Base):
    """
    Localized versions of lesson content for internationalization.
    
    Stores translated content blocks and metadata for different
    languages and regions.
    """
    __tablename__ = "localized_content"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False, index=True)
    version_id = Column(UUID(as_uuid=True), ForeignKey("version.id", ondelete="CASCADE"), nullable=True, index=True)
    draft_id = Column(UUID(as_uuid=True), ForeignKey("lesson_draft.id", ondelete="CASCADE"), nullable=True, index=True)
    
    # Localization metadata
    language_code = Column(String(10), nullable=False, index=True)  # ISO 639-1
    region_code = Column(String(10))  # ISO 3166-1 alpha-2
    locale = Column(String(20), nullable=False, index=True)  # e.g., en-US, es-MX
    
    # Localized content
    localized_title = Column(String(255))
    localized_description = Column(Text)
    localized_content_blocks = Column(JSON)
    localized_learning_objectives = Column(JSON)
    localized_metadata = Column(JSON)
    
    # Translation metadata
    translation_status = Column(String(20), default="requested", index=True)  # requested, in_progress, completed, reviewed
    translation_method = Column(String(20))  # human, ai_assisted, automatic
    translator_id = Column(UUID(as_uuid=True))
    reviewer_id = Column(UUID(as_uuid=True))
    
    # Quality metrics
    translation_quality_score = Column(Integer)  # 0-100
    human_review_required = Column(Boolean, default=True)
    cultural_adaptation_notes = Column(Text)
    
    # Timing
    requested_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    reviewed_at = Column(DateTime)
    
    # Relationships
    lesson = relationship("Lesson")
    version = relationship("Version")
    draft = relationship("LessonDraft")
    
    __table_args__ = (
        Index('idx_localized_lesson_locale', 'lesson_id', 'locale', unique=True),
        Index('idx_localized_status_language', 'translation_status', 'language_code'),
    )


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
    coursework_links = relationship("CourseworkLink", back_populates="lesson", cascade="all, delete-orphan")
    
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
    draft_id = Column(UUID(as_uuid=True), ForeignKey("lesson_draft.id"), nullable=True, index=True)  # Source draft
    
    # Version information
    version_number = Column(String(20), nullable=False)  # e.g., "1.0.0", "2.1.3"
    version_name = Column(String(100))  # Optional human-readable name
    changelog = Column(Text)
    
    # Content metadata
    content_type = Column(String(50), default="interactive")  # interactive, video, assessment, etc.
    duration_minutes = Column(Integer)
    learning_objectives = Column(JSON)  # JSON array of learning objectives
    content_blocks = Column(JSON)  # Published content blocks from draft
    
    # Version status and publishing
    status = Column(String(20), default="draft", index=True)  # draft, published, deprecated
    is_current = Column(Boolean, default=False, index=True)  # Only one current version per lesson
    review_state = Column(String(20), default="none")  # none, pending, approved, rejected
    
    # Audit trail
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    published_at = Column(DateTime, index=True)
    approved_by = Column(UUID(as_uuid=True), nullable=True, index=True)
    approved_at = Column(DateTime, nullable=True)
    
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


class CourseworkLink(Base):
    """
    Links coursework items to lessons for progress tracking.
    
    Enables the orchestrator to credit mastery and recommend
    remediations based on coursework completion.
    """
    __tablename__ = "coursework_link"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    coursework_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lesson.id"), nullable=False, index=True)
    learner_id = Column(UUID(as_uuid=True), nullable=True, index=True)  # Optional learner scope
    
    # Link metadata
    created_by = Column(UUID(as_uuid=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Soft delete support
    is_active = Column(Boolean, default=True, index=True)
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    
    # Progress tracking parameters
    mastery_weight = Column(Integer, default=100)  # Weight in mastery calculation (0-100)
    difficulty_adjustment = Column(Integer, default=0)  # Difficulty modifier (-100 to +100)
    link_context = Column(Text)  # JSON context data for analytics
    
    # Relationships
    lesson = relationship("Lesson", back_populates="coursework_links")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_coursework_lesson', 'coursework_id', 'lesson_id'),
        Index('idx_learner_active', 'learner_id', 'is_active'),
        Index('idx_created_date', 'created_at'),
    )


def validate_asset_integrity(asset: Asset, file_content: bytes) -> bool:
    """Validate asset integrity using checksum and size."""
    import hashlib
    
    # Verify file size
    if len(file_content) != asset.size_bytes:
        return False
    
    # Verify checksum
    file_hash = hashlib.sha256(file_content).hexdigest()
    return file_hash == asset.checksum
