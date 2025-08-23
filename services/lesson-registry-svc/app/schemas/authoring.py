"""
Pydantic schemas for teacher content authoring system
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from pydantic import BaseModel, Field, validator


# Content Block Schemas

class ContentBlock(BaseModel):
    """Base content block schema"""
    id: str
    type: str = Field(..., description="Block type: text, heading, image, video, audio, quiz, code, embed, file, interactive")
    content: Dict[str, Any] = Field(..., description="Block-specific content data")
    order: int = Field(..., description="Display order in lesson")
    metadata: Optional[Dict[str, Any]] = None

    @validator('type')
    def validate_block_type(cls, v):
        allowed_types = [
            'text', 'heading', 'image', 'video', 'audio', 
            'quiz', 'code', 'embed', 'file', 'interactive'
        ]
        if v not in allowed_types:
            raise ValueError(f'Block type must be one of: {", ".join(allowed_types)}')
        return v


class LearningObjective(BaseModel):
    """Learning objective schema"""
    text: str = Field(..., description="Objective description")
    level: Optional[str] = Field(None, description="Bloom's taxonomy level")
    assessment_criteria: Optional[List[str]] = None


# Draft Management Schemas

class LessonDraftCreate(BaseModel):
    """Schema for creating a new lesson draft"""
    lesson_id: Optional[UUID] = Field(None, description="ID of existing lesson to create draft from")
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    subject: str = Field(..., description="Subject area")
    grade_level: str = Field(..., description="Target grade level")
    topic: Optional[str] = None
    curriculum_standard: Optional[str] = None
    difficulty_level: Optional[str] = Field(None, description="beginner, intermediate, advanced")
    estimated_duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    content_blocks: List[ContentBlock] = []
    learning_objectives: List[LearningObjective] = []
    tags: List[str] = []
    
    @validator('difficulty_level')
    def validate_difficulty(cls, v):
        if v and v not in ['beginner', 'intermediate', 'advanced']:
            raise ValueError('Difficulty level must be beginner, intermediate, or advanced')
        return v


class LessonDraftUpdate(BaseModel):
    """Schema for updating an existing lesson draft"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    subject: Optional[str] = None
    grade_level: Optional[str] = None
    topic: Optional[str] = None
    curriculum_standard: Optional[str] = None
    difficulty_level: Optional[str] = None
    estimated_duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    content_blocks: Optional[List[ContentBlock]] = None
    learning_objectives: Optional[List[LearningObjective]] = None
    tags: Optional[List[str]] = None


class LessonDraftResponse(BaseModel):
    """Schema for lesson draft responses"""
    id: UUID
    lesson_id: Optional[UUID]
    title: str
    description: Optional[str]
    subject: str
    grade_level: str
    topic: Optional[str]
    curriculum_standard: Optional[str]
    difficulty_level: Optional[str]
    estimated_duration_minutes: Optional[int]
    content_blocks: List[ContentBlock]
    learning_objectives: List[LearningObjective]
    tags: List[str]
    status: str
    completion_percentage: int
    is_valid: bool
    validation_errors: List[str]
    created_at: datetime
    updated_at: datetime
    assets: List['DraftAssetResponse'] = []

    class Config:
        from_attributes = True


# Asset Management Schemas

class DraftAssetResponse(BaseModel):
    """Schema for draft asset responses"""
    id: UUID
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    asset_type: str
    usage_context: Optional[str]
    alt_text: Optional[str]
    processing_status: str
    uploaded_at: datetime
    temp_url: Optional[str] = None

    class Config:
        from_attributes = True


# Publishing Workflow Schemas

class PublishRequest(BaseModel):
    """Schema for publishing a draft"""
    version_number: str = Field(..., description="Semantic version number (e.g., 1.0.0)")
    changelog: Optional[str] = Field(None, description="Description of changes")
    publish_immediately: bool = Field(False, description="Publish without approval")
    requires_approval: Optional[bool] = Field(None, description="Override system default for approval requirement")
    scheduled_publish_at: Optional[datetime] = Field(None, description="Schedule publication for future date")
    notify_reviewers: bool = Field(True, description="Send notifications to reviewers")

    @validator('version_number')
    def validate_version_format(cls, v):
        import re
        pattern = r'^\d+\.\d+\.\d+(?:-[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?(?:\+[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)*)?$'
        if not re.match(pattern, v):
            raise ValueError('Version number must follow semantic versioning format (e.g., 1.0.0)')
        return v


class PublishWorkflowResponse(BaseModel):
    """Schema for publish workflow responses"""
    workflow_id: UUID
    status: str
    requires_approval: bool
    message: str


# Review and Approval Schemas

class ReviewRequest(BaseModel):
    """Schema for requesting content review"""
    review_type: str = Field(..., description="content, accessibility, curriculum_alignment, etc.")
    priority: str = Field("normal", description="low, normal, high, urgent")
    assigned_to: Optional[UUID] = Field(None, description="Specific reviewer user ID")
    reviewer_role: Optional[str] = Field(None, description="Required reviewer role")
    request_notes: Optional[str] = Field(None, description="Special instructions for reviewer")
    due_date: Optional[datetime] = Field(None, description="Review deadline")

    @validator('review_type')
    def validate_review_type(cls, v):
        allowed_types = [
            'content', 'accessibility', 'curriculum_alignment', 
            'accuracy', 'age_appropriateness', 'technical'
        ]
        if v not in allowed_types:
            raise ValueError(f'Review type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v not in ['low', 'normal', 'high', 'urgent']:
            raise ValueError('Priority must be low, normal, high, or urgent')
        return v


class ReviewResponse(BaseModel):
    """Schema for review responses"""
    review_id: UUID
    status: str
    message: str


# Translation and Localization Schemas

class TranslationRequest(BaseModel):
    """Schema for requesting content translation"""
    target_languages: List[str] = Field(..., description="ISO 639-1 language codes")
    human_review_required: bool = Field(True, description="Require human review of AI translation")
    cultural_adaptation_notes: Optional[str] = Field(None, description="Special cultural considerations")
    priority: str = Field("normal", description="Translation priority level")

    @validator('target_languages')
    def validate_languages(cls, v):
        # Common language codes - in a real system, this would be more comprehensive
        supported_languages = [
            'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh', 'ja', 'ko', 'ar', 'hi'
        ]
        for lang in v:
            if lang not in supported_languages:
                raise ValueError(f'Language {lang} not supported. Supported: {", ".join(supported_languages)}')
        return v


class TranslationResponse(BaseModel):
    """Schema for translation responses"""
    message: str
    translation_ids: List[str]


# Validation Schemas

class ContentValidationResult(BaseModel):
    """Schema for content validation results"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    completion_percentage: int
    validation_timestamp: datetime


class AssetValidationResult(BaseModel):
    """Schema for asset validation results"""
    asset_id: UUID
    is_valid: bool
    errors: List[str]
    processing_status: str


# Workflow Status Schemas

class WorkflowStatus(BaseModel):
    """Schema for workflow status responses"""
    id: UUID
    status: str
    target_version: str
    requires_approval: bool
    validation_completed: bool
    approval_completed: bool
    asset_processing_completed: bool
    version_creation_completed: bool
    initiated_at: datetime
    completed_at: Optional[datetime]
    errors: Optional[List[str]]
    version_id: Optional[UUID]


# Batch Operations Schemas

class BatchDraftOperation(BaseModel):
    """Schema for batch operations on drafts"""
    draft_ids: List[UUID] = Field(..., description="List of draft IDs to operate on")
    operation: str = Field(..., description="Operation to perform: delete, duplicate, export")
    parameters: Optional[Dict[str, Any]] = None

    @validator('operation')
    def validate_operation(cls, v):
        allowed_ops = ['delete', 'duplicate', 'export', 'archive', 'bulk_review']
        if v not in allowed_ops:
            raise ValueError(f'Operation must be one of: {", ".join(allowed_ops)}')
        return v


class BatchOperationResult(BaseModel):
    """Schema for batch operation results"""
    operation: str
    total_processed: int
    successful: int
    failed: int
    errors: List[Dict[str, str]]
    results: List[Dict[str, Any]]


# Update the forward reference
LessonDraftResponse.model_rebuild()
