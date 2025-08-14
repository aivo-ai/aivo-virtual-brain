"""
Lesson Registry - Pydantic Schemas

Request/response models for lesson content versioning and asset management.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID
from enum import Enum


class LessonStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class VersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class AssetType(str, Enum):
    HTML = "html"
    CSS = "css"
    JAVASCRIPT = "js"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    DATA = "data"
    FONT = "font"


class DifficultyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


# Base schemas
class LessonBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Lesson title")
    description: Optional[str] = Field(None, description="Detailed lesson description")
    subject: str = Field(..., min_length=1, max_length=100, description="Academic subject")
    grade_level: Optional[str] = Field(None, max_length=20, description="Target grade level")
    topic: Optional[str] = Field(None, max_length=200, description="Specific topic within subject")
    curriculum_standard: Optional[str] = Field(None, max_length=100, description="Curriculum alignment")
    difficulty_level: DifficultyLevel = Field(DifficultyLevel.INTERMEDIATE, description="Content difficulty")


class VersionBase(BaseModel):
    version_number: str = Field(..., min_length=1, max_length=20, description="Semantic version number")
    version_name: Optional[str] = Field(None, max_length=100, description="Human-readable version name")
    changelog: Optional[str] = Field(None, description="Changes in this version")
    content_type: str = Field("interactive", max_length=50, description="Type of educational content")
    duration_minutes: Optional[int] = Field(None, gt=0, description="Expected duration in minutes")
    learning_objectives: Optional[List[str]] = Field(None, description="Learning objectives for this content")

    @validator('version_number')
    def validate_version_format(cls, v):
        """Validate semantic versioning format (major.minor.patch)."""
        import re
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must follow semantic versioning format (e.g., 1.0.0)')
        return v


class AssetBase(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255, description="Original filename")
    asset_path: str = Field(..., min_length=1, max_length=500, description="Logical path in lesson structure")
    content_type: str = Field(..., max_length=100, description="MIME type")
    asset_type: AssetType = Field(..., description="Asset category")
    is_entry_point: bool = Field(False, description="Main lesson entry file")
    is_required: bool = Field(True, description="Required for lesson functionality")
    cache_duration_seconds: int = Field(3600, gt=0, description="CDN cache duration")
    compression_enabled: bool = Field(True, description="Enable compression for delivery")


# Request schemas
class LessonCreate(LessonBase):
    """Schema for creating a new lesson."""
    pass


class LessonUpdate(BaseModel):
    """Schema for updating lesson metadata."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=100)
    grade_level: Optional[str] = Field(None, max_length=20)
    topic: Optional[str] = Field(None, max_length=200)
    curriculum_standard: Optional[str] = Field(None, max_length=100)
    difficulty_level: Optional[DifficultyLevel] = None
    status: Optional[LessonStatus] = None


class VersionCreate(VersionBase):
    """Schema for creating a new lesson version."""
    pass


class VersionUpdate(BaseModel):
    """Schema for updating version metadata."""
    version_name: Optional[str] = Field(None, max_length=100)
    changelog: Optional[str] = None
    content_type: Optional[str] = Field(None, max_length=50)
    duration_minutes: Optional[int] = Field(None, gt=0)
    learning_objectives: Optional[List[str]] = None
    status: Optional[VersionStatus] = None
    is_current: Optional[bool] = None


class AssetCreate(AssetBase):
    """Schema for creating/uploading a new asset."""
    size_bytes: int = Field(..., gt=0, description="File size in bytes")
    checksum: str = Field(..., min_length=64, max_length=64, description="SHA-256 checksum")


class AssetUpdate(BaseModel):
    """Schema for updating asset metadata."""
    filename: Optional[str] = Field(None, min_length=1, max_length=255)
    asset_path: Optional[str] = Field(None, min_length=1, max_length=500)
    asset_type: Optional[AssetType] = None
    is_entry_point: Optional[bool] = None
    is_required: Optional[bool] = None
    cache_duration_seconds: Optional[int] = Field(None, gt=0)
    compression_enabled: Optional[bool] = None


# Response schemas
class AssetResponse(AssetBase):
    """Asset information in API responses."""
    id: UUID
    version_id: UUID
    s3_key: str
    size_bytes: int
    checksum: str
    uploaded_at: datetime
    uploaded_by: UUID
    validated_at: Optional[datetime] = None
    validation_status: str

    class Config:
        from_attributes = True


class AssetWithSignedUrl(AssetResponse):
    """Asset response with signed CDN URL."""
    signed_url: str
    url_expires_at: datetime


class VersionResponse(VersionBase):
    """Version information in API responses."""
    id: UUID
    lesson_id: UUID
    status: VersionStatus
    is_current: bool
    created_by: UUID
    created_at: datetime
    published_at: Optional[datetime] = None
    manifest_checksum: Optional[str] = None
    total_assets: int = 0
    total_size_bytes: int = 0

    class Config:
        from_attributes = True


class VersionWithAssets(VersionResponse):
    """Version response with included assets."""
    assets: List[AssetResponse] = []


class LessonResponse(LessonBase):
    """Lesson information in API responses."""
    id: UUID
    status: LessonStatus
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    is_active: bool
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class LessonWithVersions(LessonResponse):
    """Lesson response with version history."""
    versions: List[VersionResponse] = []


class LessonSummary(BaseModel):
    """Condensed lesson information for listings."""
    id: UUID
    title: str
    subject: str
    grade_level: Optional[str] = None
    difficulty_level: DifficultyLevel
    status: LessonStatus
    current_version: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# Manifest schemas
class ManifestAsset(BaseModel):
    """Asset information in lesson manifest."""
    path: str
    url: str
    size: int
    checksum: str
    type: str
    required: bool
    expires_at: datetime


class LessonManifest(BaseModel):
    """Complete lesson manifest with signed asset URLs."""
    lesson_id: UUID
    version_id: UUID
    version_number: str
    title: str
    description: Optional[str] = None
    subject: str
    grade_level: Optional[str] = None
    content_type: str
    duration_minutes: Optional[int] = None
    learning_objectives: List[str] = []
    
    # Manifest metadata
    generated_at: datetime
    expires_at: datetime
    total_assets: int
    total_size: int
    checksum: str
    
    # Entry point and assets
    entry_point: Optional[str] = None
    assets: List[ManifestAsset] = []


# Pagination and filtering
class LessonFilter(BaseModel):
    """Filtering options for lesson queries."""
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    topic: Optional[str] = None
    difficulty_level: Optional[DifficultyLevel] = None
    status: Optional[LessonStatus] = None
    created_by: Optional[UUID] = None


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any]
    total: int
    page: int = Field(..., ge=1)
    per_page: int = Field(..., ge=1, le=100)
    pages: int

    @validator('pages')
    def calculate_pages(cls, v, values):
        """Calculate total pages from total items and per_page."""
        if 'total' in values and 'per_page' in values:
            import math
            return math.ceil(values['total'] / values['per_page'])
        return v


class PaginatedLessons(PaginatedResponse):
    """Paginated lesson summary response."""
    items: List[LessonSummary]


# Error schemas
class ErrorDetail(BaseModel):
    """Error detail structure."""
    field: Optional[str] = None
    code: str
    message: str


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    request_id: Optional[str] = None
