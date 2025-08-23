"""
Authoring API Routes

Teacher content authoring system with draft management, asset uploads,
review workflows, and publishing pipeline.
"""

import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_, or_, desc, func

from ..database import get_db
from ..models import (
    Lesson, LessonDraft, DraftAsset, ContentReview, PublishingWorkflow, 
    LocalizedContent, Version, Asset
)
from ..auth import get_current_user, require_role
from ..config import get_settings
from ..signer import create_signer_from_config

import logging
import boto3
from botocore.exceptions import ClientError
import requests

logger = logging.getLogger(__name__)

# Router setup
router = APIRouter(prefix="/api/v1/authoring", tags=["authoring"])
settings = get_settings()

# S3 client for asset uploads
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)

# Content block validation schemas
VALID_BLOCK_TYPES = {
    "text": {"required": ["content"], "optional": ["style", "alignment"]},
    "heading": {"required": ["content", "level"], "optional": ["style"]},
    "image": {"required": ["asset_id", "alt_text"], "optional": ["caption", "alignment", "size"]},
    "video": {"required": ["asset_id"], "optional": ["caption", "autoplay", "controls"]},
    "audio": {"required": ["asset_id"], "optional": ["caption", "autoplay", "controls"]},
    "quiz": {"required": ["questions"], "optional": ["title", "instructions", "time_limit"]},
    "code": {"required": ["content"], "optional": ["language", "highlight"]},
    "embed": {"required": ["url"], "optional": ["title", "width", "height"]},
    "file": {"required": ["asset_id", "filename"], "optional": ["description"]},
    "interactive": {"required": ["config"], "optional": ["title", "instructions"]}
}


# Pydantic models for request/response
from pydantic import BaseModel, Field, validator

class ContentBlock(BaseModel):
    """Content block for lesson drafts"""
    id: str = Field(..., description="Unique block ID")
    type: str = Field(..., description="Block type (text, image, video, etc.)")
    content: Dict[str, Any] = Field(..., description="Block content data")
    order: int = Field(..., description="Display order")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    
    @validator('type')
    def validate_block_type(cls, v):
        if v not in VALID_BLOCK_TYPES:
            raise ValueError(f"Invalid block type: {v}")
        return v


class LessonDraftCreate(BaseModel):
    """Create new lesson draft"""
    title: str = Field(..., max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., max_length=100)
    grade_level: Optional[str] = Field(None, max_length=20)
    topic: Optional[str] = Field(None, max_length=200)
    curriculum_standard: Optional[str] = Field(None, max_length=100)
    difficulty_level: str = Field(default="intermediate", max_length=20)
    estimated_duration: Optional[int] = Field(None, gt=0, description="Duration in minutes")
    language: str = Field(default="en", max_length=10)
    tags: Optional[List[str]] = Field(default=[])
    lesson_id: Optional[UUID] = Field(None, description="Existing lesson ID for updates")


class LessonDraftUpdate(BaseModel):
    """Update lesson draft"""
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    content_blocks: Optional[List[ContentBlock]] = None
    learning_objectives: Optional[List[str]] = None
    assessment_data: Optional[Dict[str, Any]] = None
    estimated_duration: Optional[int] = Field(None, gt=0)
    tags: Optional[List[str]] = None
    changelog: Optional[str] = None


class DraftAssetResponse(BaseModel):
    """Draft asset response"""
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


class LessonDraftResponse(BaseModel):
    """Lesson draft response"""
    id: UUID
    lesson_id: Optional[UUID]
    title: str
    description: Optional[str]
    subject: str
    grade_level: Optional[str]
    content_blocks: Optional[List[Dict[str, Any]]]
    learning_objectives: Optional[List[str]]
    status: str
    completion_percentage: int
    is_valid: bool
    validation_errors: Optional[List[str]]
    created_at: datetime
    updated_at: datetime
    assets: List[DraftAssetResponse] = []


class PublishRequest(BaseModel):
    """Publish draft request"""
    version_number: str = Field(..., description="Target version number (e.g., 1.0.0)")
    changelog: str = Field(..., description="Description of changes")
    publish_immediately: bool = Field(default=True)
    scheduled_publish_at: Optional[datetime] = None
    requires_approval: Optional[bool] = None  # Override system default


class ReviewRequest(BaseModel):
    """Content review request"""
    review_type: str = Field(default="content")
    assigned_to: Optional[UUID] = None
    reviewer_role: Optional[str] = None
    request_notes: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: str = Field(default="normal")


class TranslationRequest(BaseModel):
    """Translation request"""
    target_languages: List[str] = Field(..., description="Target language codes")
    human_review_required: bool = Field(default=True)
    cultural_adaptation_notes: Optional[str] = None


# Draft Management Endpoints

@router.post("/drafts", response_model=LessonDraftResponse)
async def create_draft(
    draft_data: LessonDraftCreate,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Create a new lesson draft"""
    
    # Validate lesson_id if provided
    if draft_data.lesson_id:
        existing_lesson = db.query(Lesson).filter(Lesson.id == draft_data.lesson_id).first()
        if not existing_lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Check if user can edit this lesson
        if existing_lesson.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
            raise HTTPException(status_code=403, detail="Not authorized to edit this lesson")
    
    # Create draft
    draft = LessonDraft(
        lesson_id=draft_data.lesson_id,
        title=draft_data.title,
        description=draft_data.description,
        subject=draft_data.subject,
        grade_level=draft_data.grade_level,
        topic=draft_data.topic,
        curriculum_standard=draft_data.curriculum_standard,
        difficulty_level=draft_data.difficulty_level,
        estimated_duration=draft_data.estimated_duration,
        language=draft_data.language,
        tags=draft_data.tags,
        created_by=current_user.id,
        last_edited_by=current_user.id
    )
    
    db.add(draft)
    db.commit()
    db.refresh(draft)
    
    logger.info(f"Created lesson draft {draft.id} by user {current_user.id}")
    
    return LessonDraftResponse(
        id=draft.id,
        lesson_id=draft.lesson_id,
        title=draft.title,
        description=draft.description,
        subject=draft.subject,
        grade_level=draft.grade_level,
        content_blocks=draft.content_blocks or [],
        learning_objectives=draft.learning_objectives or [],
        status=draft.status,
        completion_percentage=draft.completion_percentage,
        is_valid=draft.is_valid,
        validation_errors=draft.validation_errors or [],
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        assets=[]
    )


@router.get("/drafts", response_model=List[LessonDraftResponse])
async def list_drafts(
    subject: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """List lesson drafts for current user"""
    
    query = db.query(LessonDraft).options(selectinload(LessonDraft.assets))
    
    # Filter by author unless admin/subject_brain
    if current_user.role not in ["admin", "subject_brain"]:
        query = query.filter(LessonDraft.created_by == current_user.id)
    
    if subject:
        query = query.filter(LessonDraft.subject == subject)
    
    if status:
        query = query.filter(LessonDraft.status == status)
    
    query = query.order_by(desc(LessonDraft.updated_at))
    drafts = query.offset(offset).limit(limit).all()
    
    return [
        LessonDraftResponse(
            id=draft.id,
            lesson_id=draft.lesson_id,
            title=draft.title,
            description=draft.description,
            subject=draft.subject,
            grade_level=draft.grade_level,
            content_blocks=draft.content_blocks or [],
            learning_objectives=draft.learning_objectives or [],
            status=draft.status,
            completion_percentage=draft.completion_percentage,
            is_valid=draft.is_valid,
            validation_errors=draft.validation_errors or [],
            created_at=draft.created_at,
            updated_at=draft.updated_at,
            assets=[
                DraftAssetResponse(
                    id=asset.id,
                    filename=asset.filename,
                    original_filename=asset.original_filename,
                    content_type=asset.content_type,
                    size_bytes=asset.size_bytes,
                    asset_type=asset.asset_type,
                    usage_context=asset.usage_context,
                    alt_text=asset.alt_text,
                    processing_status=asset.processing_status,
                    uploaded_at=asset.uploaded_at
                ) for asset in draft.assets
            ]
        ) for draft in drafts
    ]


@router.get("/drafts/{draft_id}", response_model=LessonDraftResponse)
async def get_draft(
    draft_id: UUID,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Get specific lesson draft"""
    
    draft = db.query(LessonDraft).options(
        selectinload(LessonDraft.assets)
    ).filter(LessonDraft.id == draft_id).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Check permissions
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this draft")
    
    # Generate temporary URLs for assets
    assets_with_urls = []
    for asset in draft.assets:
        temp_url = None
        if asset.processing_status == "ready":
            try:
                temp_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': settings.s3_bucket, 'Key': asset.temp_s3_key},
                    ExpiresIn=3600
                )
            except Exception as e:
                logger.warning(f"Failed to generate presigned URL for asset {asset.id}: {e}")
        
        assets_with_urls.append(
            DraftAssetResponse(
                id=asset.id,
                filename=asset.filename,
                original_filename=asset.original_filename,
                content_type=asset.content_type,
                size_bytes=asset.size_bytes,
                asset_type=asset.asset_type,
                usage_context=asset.usage_context,
                alt_text=asset.alt_text,
                processing_status=asset.processing_status,
                uploaded_at=asset.uploaded_at,
                temp_url=temp_url
            )
        )
    
    return LessonDraftResponse(
        id=draft.id,
        lesson_id=draft.lesson_id,
        title=draft.title,
        description=draft.description,
        subject=draft.subject,
        grade_level=draft.grade_level,
        content_blocks=draft.content_blocks or [],
        learning_objectives=draft.learning_objectives or [],
        status=draft.status,
        completion_percentage=draft.completion_percentage,
        is_valid=draft.is_valid,
        validation_errors=draft.validation_errors or [],
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        assets=assets_with_urls
    )


@router.put("/drafts/{draft_id}", response_model=LessonDraftResponse)
async def update_draft(
    draft_id: UUID,
    update_data: LessonDraftUpdate,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Update lesson draft content"""
    
    draft = db.query(LessonDraft).filter(LessonDraft.id == draft_id).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    # Check permissions
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this draft")
    
    # Update fields
    if update_data.title is not None:
        draft.title = update_data.title
    if update_data.description is not None:
        draft.description = update_data.description
    if update_data.content_blocks is not None:
        # Validate content blocks
        validated_blocks = []
        for block in update_data.content_blocks:
            if block.type not in VALID_BLOCK_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid block type: {block.type}")
            validated_blocks.append(block.dict())
        draft.content_blocks = validated_blocks
    if update_data.learning_objectives is not None:
        draft.learning_objectives = update_data.learning_objectives
    if update_data.assessment_data is not None:
        draft.assessment_data = update_data.assessment_data
    if update_data.estimated_duration is not None:
        draft.estimated_duration = update_data.estimated_duration
    if update_data.tags is not None:
        draft.tags = update_data.tags
    if update_data.changelog is not None:
        draft.changelog = update_data.changelog
    
    draft.last_edited_by = current_user.id
    draft.updated_at = datetime.utcnow()
    
    # Trigger validation in background
    background_tasks.add_task(validate_draft_content, draft.id, db)
    
    db.commit()
    db.refresh(draft)
    
    logger.info(f"Updated lesson draft {draft.id} by user {current_user.id}")
    
    return LessonDraftResponse(
        id=draft.id,
        lesson_id=draft.lesson_id,
        title=draft.title,
        description=draft.description,
        subject=draft.subject,
        grade_level=draft.grade_level,
        content_blocks=draft.content_blocks or [],
        learning_objectives=draft.learning_objectives or [],
        status=draft.status,
        completion_percentage=draft.completion_percentage,
        is_valid=draft.is_valid,
        validation_errors=draft.validation_errors or [],
        created_at=draft.created_at,
        updated_at=draft.updated_at,
        assets=[]
    )
