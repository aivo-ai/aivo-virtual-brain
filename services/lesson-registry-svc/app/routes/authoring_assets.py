"""
Asset Management and Publishing Endpoints for Teacher Content Authoring
"""

import hashlib
import os
from uuid import uuid4
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, BackgroundTasks
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import and_
from botocore.exceptions import ClientError

from app.core.auth import require_role
from app.core.database import get_db
from app.core.logger import logger
from app.core.config import settings
from app.core.s3 import s3_client
from app.models import (
    LessonDraft, DraftAsset, Lesson, Version, PublishingWorkflow,
    ContentReview, LocalizedContent
)
from app.schemas.authoring import (
    DraftAssetResponse, PublishRequest, ReviewRequest, TranslationRequest
)

router = APIRouter()


# Asset Management Endpoints

@router.post("/drafts/{draft_id}/assets", response_model=DraftAssetResponse)
async def upload_asset(
    draft_id: str,
    file: UploadFile = File(...),
    asset_type: str = Form(...),
    usage_context: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Upload asset for lesson draft"""
    
    # Validate draft exists and user has access
    draft = db.query(LessonDraft).filter(LessonDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized to upload assets to this draft")
    
    # Validate file
    if file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")
    
    allowed_types = {
        "image": ["image/jpeg", "image/png", "image/gif", "image/webp"],
        "video": ["video/mp4", "video/webm", "video/ogg"],
        "audio": ["audio/mp3", "audio/wav", "audio/ogg"],
        "document": ["application/pdf", "text/plain", "application/msword"]
    }
    
    if asset_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid asset type: {asset_type}")
    
    if file.content_type not in allowed_types[asset_type]:
        raise HTTPException(status_code=400, detail=f"Invalid file type for {asset_type}")
    
    # Read file content and calculate checksum
    file_content = await file.read()
    checksum = hashlib.sha256(file_content).hexdigest()
    
    # Generate unique filename and S3 key
    file_extension = os.path.splitext(file.filename)[1]
    unique_filename = f"{uuid4()}{file_extension}"
    s3_key = f"drafts/{draft_id}/assets/{unique_filename}"
    
    # Upload to S3
    try:
        s3_client.put_object(
            Bucket=settings.s3_bucket,
            Key=s3_key,
            Body=file_content,
            ContentType=file.content_type,
            Metadata={
                'draft_id': str(draft_id),
                'uploaded_by': str(current_user.id),
                'original_filename': file.filename
            }
        )
    except ClientError as e:
        logger.error(f"Failed to upload asset to S3: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload asset")
    
    # Create asset record
    asset = DraftAsset(
        draft_id=draft_id,
        filename=unique_filename,
        original_filename=file.filename,
        temp_s3_key=s3_key,
        content_type=file.content_type,
        size_bytes=len(file_content),
        checksum=checksum,
        asset_type=asset_type,
        usage_context=usage_context,
        alt_text=alt_text,
        uploaded_by=current_user.id,
        processing_status="ready"
    )
    
    db.add(asset)
    db.commit()
    db.refresh(asset)
    
    logger.info(f"Uploaded asset {asset.id} for draft {draft_id}")
    
    # Generate temporary URL
    temp_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': settings.s3_bucket, 'Key': s3_key},
        ExpiresIn=3600
    )
    
    return DraftAssetResponse(
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


@router.delete("/drafts/{draft_id}/assets/{asset_id}")
async def delete_asset(
    draft_id: str,
    asset_id: str,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Delete asset from draft"""
    
    # Validate draft access
    draft = db.query(LessonDraft).filter(LessonDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Find asset
    asset = db.query(DraftAsset).filter(
        and_(DraftAsset.id == asset_id, DraftAsset.draft_id == draft_id)
    ).first()
    
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Delete from S3
    try:
        s3_client.delete_object(Bucket=settings.s3_bucket, Key=asset.temp_s3_key)
    except ClientError as e:
        logger.warning(f"Failed to delete asset from S3: {e}")
    
    # Delete from database
    db.delete(asset)
    db.commit()
    
    logger.info(f"Deleted asset {asset_id} from draft {draft_id}")
    
    return {"message": "Asset deleted successfully"}


@router.get("/drafts/{draft_id}/assets", response_model=List[DraftAssetResponse])
async def list_draft_assets(
    draft_id: str,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """List all assets for a draft"""
    
    # Validate draft access
    draft = db.query(LessonDraft).filter(LessonDraft.id == draft_id).first()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    assets = db.query(DraftAsset).filter(DraftAsset.draft_id == draft_id).all()
    
    # Generate temporary URLs for each asset
    response_assets = []
    for asset in assets:
        temp_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.s3_bucket, 'Key': asset.temp_s3_key},
            ExpiresIn=3600
        )
        
        response_assets.append(DraftAssetResponse(
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
        ))
    
    return response_assets


# Publishing Workflow

@router.post("/drafts/{draft_id}/publish")
async def publish_draft(
    draft_id: str,
    publish_request: PublishRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Publish draft as new lesson version"""
    
    # Validate draft
    draft = db.query(LessonDraft).options(
        selectinload(LessonDraft.assets)
    ).filter(LessonDraft.id == draft_id).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized to publish this draft")
    
    if not draft.is_valid:
        raise HTTPException(status_code=400, detail="Draft is not valid for publishing")
    
    # Validate version number format
    if not _validate_version_number(publish_request.version_number):
        raise HTTPException(status_code=400, detail="Invalid version number format")
    
    # Check if lesson exists or needs to be created
    lesson = None
    if draft.lesson_id:
        lesson = db.query(Lesson).filter(Lesson.id == draft.lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Associated lesson not found")
        
        # Check for version conflicts
        existing_version = db.query(Version).filter(
            and_(Version.lesson_id == lesson.id, Version.version_number == publish_request.version_number)
        ).first()
        if existing_version:
            raise HTTPException(status_code=409, detail="Version number already exists")
    else:
        # Create new lesson
        lesson = Lesson(
            title=draft.title,
            description=draft.description,
            subject=draft.subject,
            grade_level=draft.grade_level,
            topic=draft.topic,
            curriculum_standard=draft.curriculum_standard,
            difficulty_level=draft.difficulty_level,
            status="draft",
            created_by=current_user.id
        )
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        
        # Update draft with lesson_id
        draft.lesson_id = lesson.id
    
    # Determine if approval is required
    requires_approval = publish_request.requires_approval
    if requires_approval is None:
        requires_approval = getattr(settings, 'require_content_approval', True)
    
    # Create publishing workflow
    workflow = PublishingWorkflow(
        draft_id=draft_id,
        status="initiated",
        requires_approval=requires_approval,
        approval_required_roles=["district_admin"] if requires_approval else [],
        auto_publish_on_approval=publish_request.publish_immediately,
        target_version_number=publish_request.version_number,
        publish_immediately=publish_request.publish_immediately and not requires_approval,
        scheduled_publish_at=publish_request.scheduled_publish_at,
        initiated_by=current_user.id
    )
    
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    
    # Start publishing process in background
    background_tasks.add_task(
        process_publishing_workflow, 
        workflow.id, 
        draft.id, 
        lesson.id, 
        publish_request.changelog
    )
    
    logger.info(f"Initiated publishing workflow {workflow.id} for draft {draft_id}")
    
    return {
        "workflow_id": workflow.id,
        "status": workflow.status,
        "requires_approval": requires_approval,
        "message": "Publishing workflow initiated"
    }


@router.get("/workflows/{workflow_id}")
async def get_workflow_status(
    workflow_id: str,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Get publishing workflow status"""
    
    workflow = db.query(PublishingWorkflow).filter(PublishingWorkflow.id == workflow_id).first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    # Check permissions
    if workflow.initiated_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized to view this workflow")
    
    return {
        "id": workflow.id,
        "status": workflow.status,
        "target_version": workflow.target_version_number,
        "requires_approval": workflow.requires_approval,
        "validation_completed": workflow.validation_step_completed,
        "approval_completed": workflow.approval_step_completed,
        "asset_processing_completed": workflow.asset_processing_completed,
        "version_creation_completed": workflow.version_creation_completed,
        "initiated_at": workflow.initiated_at,
        "completed_at": workflow.completed_at,
        "errors": workflow.processing_errors,
        "version_id": workflow.version_id
    }


# Review and Approval

@router.post("/drafts/{draft_id}/request-review")
async def request_review(
    draft_id: str,
    review_request: ReviewRequest,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Request content review for draft"""
    
    draft = db.query(LessonDraft).filter(LessonDraft.id == draft_id).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create review request
    review = ContentReview(
        draft_id=draft_id,
        review_type=review_request.review_type,
        status="pending",
        priority=review_request.priority,
        requested_by=current_user.id,
        assigned_to=review_request.assigned_to,
        reviewer_role=review_request.reviewer_role,
        request_notes=review_request.request_notes,
        due_date=review_request.due_date
    )
    
    db.add(review)
    
    # Update draft status
    draft.status = "under_review"
    
    db.commit()
    db.refresh(review)
    
    logger.info(f"Requested review {review.id} for draft {draft_id}")
    
    return {
        "review_id": review.id,
        "status": review.status,
        "message": "Review requested successfully"
    }


# Translation and Localization

@router.post("/drafts/{draft_id}/request-translation")
async def request_translation(
    draft_id: str,
    translation_request: TranslationRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(require_role(["teacher", "subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """Request AI-assisted translation for draft content"""
    
    draft = db.query(LessonDraft).filter(LessonDraft.id == draft_id).first()
    
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    
    if draft.created_by != current_user.id and current_user.role not in ["admin", "subject_brain"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Create localized content entries
    translation_requests = []
    for language_code in translation_request.target_languages:
        locale = f"{language_code}-{language_code.upper()}"  # Simple mapping
        
        localized = LocalizedContent(
            draft_id=draft_id,
            language_code=language_code,
            locale=locale,
            translation_status="requested",
            translation_method="ai_assisted",
            human_review_required=translation_request.human_review_required,
            cultural_adaptation_notes=translation_request.cultural_adaptation_notes
        )
        
        db.add(localized)
        translation_requests.append(localized)
    
    db.commit()
    
    # Start translation process in background
    for localized in translation_requests:
        background_tasks.add_task(process_ai_translation, localized.id, draft)
    
    logger.info(f"Requested translations for draft {draft_id} in languages: {translation_request.target_languages}")
    
    return {
        "message": f"Translation requested for {len(translation_request.target_languages)} languages",
        "translation_ids": [str(loc.id) for loc in translation_requests]
    }


# Utility Functions

def _validate_version_number(version: str) -> bool:
    """Validate semantic version number format"""
    import re
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$'
    return bool(re.match(pattern, version))


async def process_publishing_workflow(workflow_id: str, draft_id: str, lesson_id: str, changelog: str):
    """Process complete publishing workflow"""
    # Background task implementation would handle:
    # 1. Content validation
    # 2. Asset migration from temp to permanent storage
    # 3. Version creation
    # 4. Publishing approval workflow
    pass


async def process_ai_translation(localized_id: str, draft: LessonDraft):
    """Process AI translation request"""
    # This would call inference gateway for translation
    # Implementation would translate content blocks and update localized content
    pass
