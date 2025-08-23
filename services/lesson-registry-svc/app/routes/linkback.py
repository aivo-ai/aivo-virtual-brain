"""
Lesson Registry - Coursework Linkback Routes (S5-10)

API routes for linking coursework items to lessons and managing
progress hooks for the learning orchestrator.
"""
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ..database import get_db
from ..models import Lesson, CourseworkLink
from ..schemas.linkback import (
    CourseworkLinkRequest, CourseworkLinkResponse, LinkbackStatus,
    CourseworkLinksQuery, CourseworkLinksResponse, ProgressHookEvent,
    LinkbackValidation
)
from ..auth import get_current_user, require_role
from .events import emit_coursework_linked_event, emit_coursework_unlinked_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/linkback", tags=["coursework-linkback"])


@router.post("/link", response_model=CourseworkLinkResponse, status_code=201)
async def link_coursework_to_lesson(
    link_request: CourseworkLinkRequest,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_role(["teacher", "guardian"])),
    db: Session = Depends(get_db)
):
    """
    Link a coursework item to a lesson for progress tracking.
    
    RBAC: Only teacher/guardian roles can create linkbacks.
    Requires same learner scope validation.
    
    Args:
        link_request: Contains courseworkId, lessonId, and optional learner scope
        background_tasks: For async event emission
        current_user: Authenticated user with teacher/guardian role
        db: Database session
    
    Returns:
        CourseworkLinkResponse with link details and status
        
    Raises:
        HTTPException: 403 if insufficient permissions, 404 if resources not found,
                      409 if link already exists
    """
    try:
        # Validate lesson exists and user has access
        lesson = db.query(Lesson).filter(
            and_(
                Lesson.id == link_request.lesson_id,
                Lesson.is_active == True
            )
        ).first()
        
        if not lesson:
            raise HTTPException(
                status_code=404,
                detail=f"Lesson {link_request.lesson_id} not found or inactive"
            )
        
        # Check if user has permission for this learner scope
        if link_request.learner_id:
            if not await _validate_learner_scope(
                current_user, link_request.learner_id, db
            ):
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions for specified learner"
                )
        
        # Check if link already exists
        existing_link = db.query(CourseworkLink).filter(
            and_(
                CourseworkLink.coursework_id == link_request.coursework_id,
                CourseworkLink.lesson_id == link_request.lesson_id,
                CourseworkLink.learner_id == link_request.learner_id,
                CourseworkLink.is_active == True
            )
        ).first()
        
        if existing_link:
            raise HTTPException(
                status_code=409,
                detail="Coursework is already linked to this lesson"
            )
        
        # Create the linkback
        coursework_link = CourseworkLink(
            coursework_id=link_request.coursework_id,
            lesson_id=link_request.lesson_id,
            learner_id=link_request.learner_id,
            created_by=current_user.id,
            link_context=link_request.context or {},
            mastery_weight=link_request.mastery_weight or 1.0,
            difficulty_adjustment=link_request.difficulty_adjustment or 0.0
        )
        
        db.add(coursework_link)
        db.commit()
        db.refresh(coursework_link)
        
        # Emit event for orchestrator
        background_tasks.add_task(
            emit_coursework_linked_event,
            coursework_link.id,
            link_request.coursework_id,
            link_request.lesson_id,
            link_request.learner_id,
            current_user.id
        )
        
        logger.info(
            f"Coursework {link_request.coursework_id} linked to lesson "
            f"{link_request.lesson_id} by user {current_user.id}"
        )
        
        return CourseworkLinkResponse(
            id=coursework_link.id,
            coursework_id=coursework_link.coursework_id,
            lesson_id=coursework_link.lesson_id,
            learner_id=coursework_link.learner_id,
            status=LinkbackStatus.ACTIVE,
            created_by=coursework_link.created_by,
            created_at=coursework_link.created_at,
            mastery_weight=coursework_link.mastery_weight,
            difficulty_adjustment=coursework_link.difficulty_adjustment,
            link_context=coursework_link.link_context
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create coursework linkback: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create coursework linkback"
        )


@router.delete("/link/{link_id}", response_model=dict)
async def unlink_coursework_from_lesson(
    link_id: UUID,
    background_tasks: BackgroundTasks,
    current_user=Depends(require_role(["teacher", "guardian"])),
    db: Session = Depends(get_db)
):
    """
    Remove a coursework-to-lesson linkback.
    
    Args:
        link_id: UUID of the linkback to remove
        background_tasks: For async event emission
        current_user: Authenticated user with teacher/guardian role
        db: Database session
        
    Returns:
        Success confirmation
        
    Raises:
        HTTPException: 403 if insufficient permissions, 404 if link not found
    """
    try:
        # Find the link
        coursework_link = db.query(CourseworkLink).filter(
            and_(
                CourseworkLink.id == link_id,
                CourseworkLink.is_active == True
            )
        ).first()
        
        if not coursework_link:
            raise HTTPException(
                status_code=404,
                detail=f"Coursework link {link_id} not found"
            )
        
        # Check permissions - user must be creator or have admin access
        if (coursework_link.created_by != current_user.id and 
            current_user.role not in ["admin", "subject_brain"]):
            # Additional check for learner scope
            if coursework_link.learner_id:
                if not await _validate_learner_scope(
                    current_user, coursework_link.learner_id, db
                ):
                    raise HTTPException(
                        status_code=403,
                        detail="Insufficient permissions to remove this link"
                    )
        
        # Soft delete the link
        coursework_link.is_active = False
        coursework_link.deleted_at = datetime.utcnow()
        coursework_link.deleted_by = current_user.id
        
        db.commit()
        
        # Emit event for orchestrator
        background_tasks.add_task(
            emit_coursework_unlinked_event,
            coursework_link.id,
            coursework_link.coursework_id,
            coursework_link.lesson_id,
            coursework_link.learner_id,
            current_user.id
        )
        
        logger.info(
            f"Coursework link {link_id} removed by user {current_user.id}"
        )
        
        return {"message": "Coursework linkback removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove coursework linkback: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to remove coursework linkback"
        )


@router.get("/links/coursework/{coursework_id}", response_model=list[CourseworkLinkResponse])
async def get_coursework_links(
    coursework_id: UUID,
    learner_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all lesson links for a specific coursework item.
    
    Args:
        coursework_id: UUID of the coursework item
        learner_id: Optional learner filter
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of active coursework links
    """
    try:
        query = db.query(CourseworkLink).filter(
            and_(
                CourseworkLink.coursework_id == coursework_id,
                CourseworkLink.is_active == True
            )
        )
        
        if learner_id:
            query = query.filter(CourseworkLink.learner_id == learner_id)
        
        links = query.all()
        
        return [
            CourseworkLinkResponse(
                id=link.id,
                coursework_id=link.coursework_id,
                lesson_id=link.lesson_id,
                learner_id=link.learner_id,
                status=LinkbackStatus.ACTIVE,
                created_by=link.created_by,
                created_at=link.created_at,
                mastery_weight=link.mastery_weight,
                difficulty_adjustment=link.difficulty_adjustment,
                link_context=link.link_context
            )
            for link in links
        ]
        
    except Exception as e:
        logger.error(f"Failed to retrieve coursework links: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve coursework links"
        )


@router.get("/links/lesson/{lesson_id}", response_model=list[CourseworkLinkResponse])
async def get_lesson_links(
    lesson_id: UUID,
    learner_id: Optional[UUID] = None,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all coursework links for a specific lesson.
    
    Args:
        lesson_id: UUID of the lesson
        learner_id: Optional learner filter
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of active lesson links
    """
    try:
        query = db.query(CourseworkLink).filter(
            and_(
                CourseworkLink.lesson_id == lesson_id,
                CourseworkLink.is_active == True
            )
        )
        
        if learner_id:
            query = query.filter(CourseworkLink.learner_id == learner_id)
        
        links = query.all()
        
        return [
            CourseworkLinkResponse(
                id=link.id,
                coursework_id=link.coursework_id,
                lesson_id=link.lesson_id,
                learner_id=link.learner_id,
                status=LinkbackStatus.ACTIVE,
                created_by=link.created_by,
                created_at=link.created_at,
                mastery_weight=link.mastery_weight,
                difficulty_adjustment=link.difficulty_adjustment,
                link_context=link.link_context
            )
            for link in links
        ]
        
    except Exception as e:
        logger.error(f"Failed to retrieve lesson links: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve lesson links"
        )


async def _validate_learner_scope(current_user, learner_id: UUID, db: Session) -> bool:
    """
    Validate that the current user has access to the specified learner.
    
    Args:
        current_user: Authenticated user
        learner_id: UUID of the learner to check
        db: Database session
        
    Returns:
        bool: True if user has access, False otherwise
    """
    # Implementation depends on your user/learner relationship model
    # This is a placeholder that should be implemented based on your
    # specific authorization model
    
    if current_user.role in ["admin", "subject_brain"]:
        return True
    
    # For teachers/guardians, check if they have access to this learner
    # This would typically query a relationship table or check tenant scope
    # For now, return True - implement based on your authorization model
    return True
