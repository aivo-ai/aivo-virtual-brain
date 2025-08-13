from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional
import uuid

from ..database import get_db
from ..service import LearnerService
from ..schemas import LearnerCreateRequest, LearnerResponse, TeacherAttachRequest

router = APIRouter(prefix="/learners", tags=["learners"])

def get_current_user_id(authorization: Optional[str] = Header(None)) -> str:
    """Extract user ID from authorization header. In real implementation, validate JWT."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")

    # For MVP, simulate user ID extraction (in production, decode and validate JWT)
    # Format: "Bearer <token>" -> extract user_id from token
    return "user_123"  # Placeholder

def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> Optional[str]:
    """Extract tenant ID from header for multi-tenant support."""
    return x_tenant_id

@router.post("/", response_model=LearnerResponse, status_code=201)
def create_learner(
    learner_data: LearnerCreateRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    tenant_id: Optional[str] = Depends(get_tenant_id)
):
    """
    Create a new learner record.

    - **dob**: Date of birth (used to calculate grade_default)
    - **provision_source**: Who is creating the learner (parent/district/school_sped)
    - **tenant_id**: Optional tenant ID for multi-tenant support
    - **guardian_user_id**: Optional guardian user ID (defaults to current user if provision_source is parent)
    """
    service = LearnerService(db)
    try:
        return service.create_learner(learner_data, current_user_id, tenant_id)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{learner_id}", response_model=LearnerResponse)
def get_learner(
    learner_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    tenant_id: Optional[str] = Depends(get_tenant_id)
):
    """
    Get learner by ID with tenant scoping and access control.

    Only accessible by:
    - Guardians linked to the learner
    - Teachers assigned to the learner
    - Users within the same tenant (if tenant_id is set)
    """
    service = LearnerService(db)

    try:
        learner = service.get_learner(learner_id, current_user_id, tenant_id)
        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found")
        return learner
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid learner ID format")

@router.post("/{learner_id}/teachers", status_code=201)
def attach_teacher(
    learner_id: str,
    teacher_data: TeacherAttachRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    tenant_id: Optional[str] = Depends(get_tenant_id)
):
    """
    Attach/invite teacher to learner with specific subjects.

    - **email**: Teacher's email address
    - **subjects**: List of subjects the teacher will handle for this learner

    This endpoint supports multi-teacher access - multiple teachers can be assigned
    to the same learner with different subject responsibilities.
    """
    service = LearnerService(db)

    try:
        return service.attach_teacher(learner_id, teacher_data, current_user_id, tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid learner ID format")
