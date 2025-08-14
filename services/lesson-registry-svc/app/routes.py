"""
Lesson Registry - API Routes

FastAPI routes for lesson content management, versioning, and CDN-signed manifest delivery.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc

from .database import get_db
from .models import Lesson, Version, Asset
from .schemas import (
    LessonCreate, LessonUpdate, LessonResponse, LessonWithVersions, LessonSummary,
    VersionCreate, VersionUpdate, VersionResponse, VersionWithAssets,
    AssetCreate, AssetUpdate, AssetResponse, AssetWithSignedUrl,
    LessonManifest, ManifestAsset, LessonFilter, PaginatedLessons,
    ErrorResponse
)
from .signer import create_signer_from_config, batch_sign_assets
from .auth import get_current_user, require_role
from .config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["lesson-registry"])

# Configuration
settings = get_settings()
cdn_signer = create_signer_from_config(settings.cdn_config)


# Lesson endpoints
@router.post("/lesson", response_model=LessonResponse, status_code=201)
async def create_lesson(
    lesson_data: LessonCreate,
    current_user=Depends(require_role(["subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Create a new lesson.
    
    Only subject_brain and admin roles can create lessons.
    Creates the lesson entity with initial metadata.
    """
    try:
        # Create lesson entity
        lesson = Lesson(
            title=lesson_data.title,
            description=lesson_data.description,
            subject=lesson_data.subject,
            grade_level=lesson_data.grade_level,
            topic=lesson_data.topic,
            curriculum_standard=lesson_data.curriculum_standard,
            difficulty_level=lesson_data.difficulty_level,
            created_by=current_user.id
        )
        
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        
        logger.info(f"Created lesson {lesson.id} by user {current_user.id}")
        return lesson
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create lesson: {e}")
        raise HTTPException(status_code=500, detail="Failed to create lesson")


@router.get("/lesson", response_model=PaginatedLessons)
async def list_lessons(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    grade_level: Optional[str] = Query(None, description="Filter by grade level"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List lessons with filtering and pagination.
    
    Supports filtering by subject, grade level, status and text search.
    Returns paginated lesson summaries.
    """
    try:
        # Build query with filters
        query = db.query(Lesson).filter(Lesson.is_active == True)
        
        if subject:
            query = query.filter(Lesson.subject.ilike(f"%{subject}%"))
        if grade_level:
            query = query.filter(Lesson.grade_level == grade_level)
        if status:
            query = query.filter(Lesson.status == status)
        if search:
            search_filter = or_(
                Lesson.title.ilike(f"%{search}%"),
                Lesson.description.ilike(f"%{search}%"),
                Lesson.topic.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
        
        # Get total count
        total = query.count()
        
        # Apply pagination and ordering
        offset = (page - 1) * per_page
        lessons = query.order_by(desc(Lesson.updated_at)).offset(offset).limit(per_page).all()
        
        # Convert to summary format
        lesson_summaries = []
        for lesson in lessons:
            current_version = db.query(Version).filter(
                and_(
                    Version.lesson_id == lesson.id,
                    Version.is_current == True,
                    Version.status == "published"
                )
            ).first()
            
            lesson_summaries.append(LessonSummary(
                id=lesson.id,
                title=lesson.title,
                subject=lesson.subject,
                grade_level=lesson.grade_level,
                difficulty_level=lesson.difficulty_level,
                status=lesson.status,
                current_version=current_version.version_number if current_version else None,
                created_at=lesson.created_at,
                updated_at=lesson.updated_at
            ))
        
        return PaginatedLessons(
            items=lesson_summaries,
            total=total,
            page=page,
            per_page=per_page,
            pages=(total + per_page - 1) // per_page
        )
        
    except Exception as e:
        logger.error(f"Failed to list lessons: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve lessons")


@router.get("/lesson/{lesson_id}", response_model=LessonWithVersions)
async def get_lesson(
    lesson_id: UUID,
    include_drafts: bool = Query(False, description="Include draft versions"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lesson details with version history.
    
    Returns lesson metadata and associated versions.
    Draft versions only visible to creators and admins.
    """
    try:
        # Get lesson
        lesson = db.query(Lesson).filter(
            and_(Lesson.id == lesson_id, Lesson.is_active == True)
        ).first()
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Get versions based on permissions
        version_query = db.query(Version).filter(Version.lesson_id == lesson_id)
        
        if not include_drafts or current_user.role not in ["subject_brain", "admin"]:
            version_query = version_query.filter(Version.status == "published")
        
        versions = version_query.order_by(desc(Version.created_at)).all()
        
        return LessonWithVersions(
            **lesson.__dict__,
            versions=[VersionResponse(**v.__dict__) for v in versions]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve lesson")


@router.patch("/lesson/{lesson_id}", response_model=LessonResponse)
async def update_lesson(
    lesson_id: UUID,
    lesson_update: LessonUpdate,
    current_user=Depends(require_role(["subject_brain", "teacher", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Update lesson metadata.
    
    Teachers can update metadata, subject_brain and admins can change status.
    """
    try:
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Role-based permission checks
        if current_user.role == "teacher" and lesson_update.status is not None:
            raise HTTPException(status_code=403, detail="Teachers cannot change lesson status")
        
        # Apply updates
        for field, value in lesson_update.dict(exclude_unset=True).items():
            setattr(lesson, field, value)
        
        lesson.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(lesson)
        
        logger.info(f"Updated lesson {lesson_id} by user {current_user.id}")
        return lesson
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update lesson")


# Version endpoints
@router.post("/lesson/{lesson_id}/version", response_model=VersionResponse, status_code=201)
async def create_version(
    lesson_id: UUID,
    version_data: VersionCreate,
    current_user=Depends(require_role(["subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Create a new lesson version.
    
    Only subject_brain and admin can create versions.
    Version numbers must be unique within a lesson.
    """
    try:
        # Verify lesson exists
        lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Check version uniqueness
        existing = db.query(Version).filter(
            and_(
                Version.lesson_id == lesson_id,
                Version.version_number == version_data.version_number
            )
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=409, 
                detail=f"Version {version_data.version_number} already exists"
            )
        
        # Create version
        version = Version(
            lesson_id=lesson_id,
            version_number=version_data.version_number,
            version_name=version_data.version_name,
            changelog=version_data.changelog,
            content_type=version_data.content_type,
            duration_minutes=version_data.duration_minutes,
            learning_objectives=str(version_data.learning_objectives) if version_data.learning_objectives else None,
            created_by=current_user.id
        )
        
        db.add(version)
        db.commit()
        db.refresh(version)
        
        logger.info(f"Created version {version.id} for lesson {lesson_id}")
        return version
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create version for lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to create version")


# Manifest endpoint - Core functionality
@router.get("/manifest/{lesson_id}", response_model=LessonManifest)
async def get_lesson_manifest(
    lesson_id: UUID,
    version: Optional[str] = Query(None, description="Specific version number"),
    expires_seconds: Optional[int] = Query(600, ge=60, le=3600, description="URL expiration time"),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get lesson manifest with signed CDN URLs.
    
    Returns complete lesson manifest including all assets with signed URLs
    for secure, time-limited access. This is the core endpoint for lesson delivery.
    """
    try:
        # Get lesson
        lesson = db.query(Lesson).filter(
            and_(Lesson.id == lesson_id, Lesson.is_active == True)
        ).first()
        
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        
        # Get specific version or current published version
        if version:
            lesson_version = db.query(Version).filter(
                and_(
                    Version.lesson_id == lesson_id,
                    Version.version_number == version
                )
            ).first()
        else:
            lesson_version = db.query(Version).filter(
                and_(
                    Version.lesson_id == lesson_id,
                    Version.is_current == True,
                    Version.status == "published"
                )
            ).first()
        
        if not lesson_version:
            if version:
                raise HTTPException(status_code=404, detail=f"Version {version} not found")
            else:
                raise HTTPException(status_code=404, detail="No published version available")
        
        # Get all assets for this version
        assets = db.query(Asset).filter(Asset.version_id == lesson_version.id).all()
        
        # Sign asset URLs in batch
        asset_paths = [asset.s3_key for asset in assets]
        signed_data = batch_sign_assets(
            cdn_signer,
            asset_paths,
            current_user.role,
            expires_seconds
        )
        
        # Build manifest assets with signed URLs
        manifest_assets = []
        entry_point = None
        
        for asset in assets:
            signing_result = signed_data.get(asset.s3_key)
            if not signing_result or "error" in signing_result:
                logger.error(f"Failed to sign URL for asset {asset.s3_key}")
                continue
            
            manifest_asset = ManifestAsset(
                path=asset.asset_path,
                url=signing_result["signed_url"],
                size=asset.size_bytes,
                checksum=asset.checksum,
                type=asset.asset_type,
                required=asset.is_required,
                expires_at=signing_result["expires_at"]
            )
            
            manifest_assets.append(manifest_asset)
            
            # Track entry point
            if asset.is_entry_point:
                entry_point = asset.asset_path
        
        # Generate manifest checksum
        import hashlib
        import json
        
        manifest_data = {
            "lesson_id": str(lesson_id),
            "version_id": str(lesson_version.id),
            "version_number": lesson_version.version_number,
            "assets": [
                {"path": a.path, "checksum": a.checksum, "size": a.size}
                for a in manifest_assets
            ]
        }
        manifest_json = json.dumps(manifest_data, sort_keys=True)
        manifest_checksum = hashlib.sha256(manifest_json.encode()).hexdigest()
        
        # Build complete manifest
        expires_at = datetime.utcnow().replace(microsecond=0)
        expires_at = expires_at.replace(second=0, microsecond=0)
        
        manifest = LessonManifest(
            lesson_id=lesson_id,
            version_id=lesson_version.id,
            version_number=lesson_version.version_number,
            title=lesson.title,
            description=lesson.description,
            subject=lesson.subject,
            grade_level=lesson.grade_level,
            content_type=lesson_version.content_type,
            duration_minutes=lesson_version.duration_minutes,
            learning_objectives=eval(lesson_version.learning_objectives) if lesson_version.learning_objectives else [],
            generated_at=datetime.utcnow(),
            expires_at=expires_at,
            total_assets=len(manifest_assets),
            total_size=sum(a.size for a in manifest_assets),
            checksum=manifest_checksum,
            entry_point=entry_point,
            assets=manifest_assets
        )
        
        logger.info(f"Generated manifest for lesson {lesson_id} version {lesson_version.version_number}")
        return manifest
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate manifest for lesson {lesson_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate lesson manifest")


# Asset upload endpoint (simplified for demo)
@router.post("/lesson/{lesson_id}/version/{version_id}/asset", response_model=AssetResponse, status_code=201)
async def upload_asset(
    lesson_id: UUID,
    version_id: UUID,
    asset_data: AssetCreate,
    current_user=Depends(require_role(["subject_brain", "admin"])),
    db: Session = Depends(get_db)
):
    """
    Register a new asset for a lesson version.
    
    This endpoint registers asset metadata. Actual file upload
    should happen separately to S3/MinIO storage.
    """
    try:
        # Verify version exists
        version = db.query(Version).filter(
            and_(Version.id == version_id, Version.lesson_id == lesson_id)
        ).first()
        
        if not version:
            raise HTTPException(status_code=404, detail="Version not found")
        
        # Generate S3 key
        s3_key = f"lessons/{lesson_id}/versions/{version_id}/{asset_data.filename}"
        
        # Create asset record
        asset = Asset(
            version_id=version_id,
            filename=asset_data.filename,
            s3_key=s3_key,
            asset_path=asset_data.asset_path,
            content_type=asset_data.content_type,
            size_bytes=asset_data.size_bytes,
            checksum=asset_data.checksum,
            asset_type=asset_data.asset_type,
            is_entry_point=asset_data.is_entry_point,
            is_required=asset_data.is_required,
            cache_duration_seconds=asset_data.cache_duration_seconds,
            compression_enabled=asset_data.compression_enabled,
            uploaded_by=current_user.id
        )
        
        db.add(asset)
        
        # Update version statistics
        version.total_assets = db.query(Asset).filter(Asset.version_id == version_id).count() + 1
        version.total_size_bytes = (version.total_size_bytes or 0) + asset_data.size_bytes
        
        db.commit()
        db.refresh(asset)
        
        logger.info(f"Registered asset {asset.id} for version {version_id}")
        return asset
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upload asset: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload asset")
