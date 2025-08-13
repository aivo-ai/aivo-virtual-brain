from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List
import uuid
import logging

from ..database import get_db
from ..private_brain_service import PrivateBrainService
from ..service import LearnerService
from ..schemas import PersonaCreateRequest, PersonaResponse, ModelBindingResponse

router = APIRouter(tags=["persona"])
logger = logging.getLogger(__name__)

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

@router.post("/learners/{learner_id}/persona", response_model=PersonaResponse, status_code=201)
def create_persona(
    learner_id: str,
    persona_data: PersonaCreateRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    tenant_id: Optional[str] = Depends(get_tenant_id)
):
    """
    Create a private brain persona for a learner.
    
    - **alias**: Safe nickname for the learner (cannot be legal name, contains profanity/PII guard)
    - **voice**: Optional voice preference for text-to-speech
    - **tone**: Optional conversation tone preference
    - **speech_rate**: Optional speech rate for TTS (50-200)
    
    Security features:
    - Alias undergoes profanity and PII detection
    - Alias cannot appear to be a real name
    - All logging redacts the alias to prevent exposure
    """
    
    # Verify user has access to this learner
    learner_service = LearnerService(db)
    try:
        learner = learner_service.get_learner(learner_id, current_user_id, tenant_id)
        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found")
    except HTTPException:
        # Re-raise HTTP exceptions (403, 404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error verifying learner access: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Create persona
    private_brain_service = PrivateBrainService(db)
    persona = private_brain_service.create_persona(learner_id, persona_data, current_user_id)
    
    # Check if we can emit PRIVATE_BRAIN_READY (if model bindings already exist)
    private_brain_service.trigger_private_brain_ready_if_complete(learner_id)
    
    return persona

@router.get("/learners/{learner_id}/persona", response_model=PersonaResponse)
def get_persona(
    learner_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    tenant_id: Optional[str] = Depends(get_tenant_id)
):
    """
    Get the private brain persona for a learner.
    
    Returns the learner's persona profile if it exists.
    """
    
    # Verify user has access to this learner
    learner_service = LearnerService(db)
    try:
        learner = learner_service.get_learner(learner_id, current_user_id, tenant_id)
        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying learner access: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Get persona
    try:
        learner_uuid = uuid.UUID(learner_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid learner ID format")

    from ..models import PrivateBrainProfile
    persona = db.query(PrivateBrainProfile).filter(
        PrivateBrainProfile.learner_id == learner_uuid
    ).first()

    if not persona:
        raise HTTPException(status_code=404, detail="Persona not found")

    return PersonaResponse.from_orm(persona)

@router.get("/learners/{learner_id}/model-bindings", response_model=List[ModelBindingResponse])
def get_model_bindings(
    learner_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
    tenant_id: Optional[str] = Depends(get_tenant_id)
):
    """
    Get all active model bindings for a learner.
    
    Returns the list of AI model bindings configured for different subjects.
    """
    
    # Verify user has access to this learner
    learner_service = LearnerService(db)
    try:
        learner = learner_service.get_learner(learner_id, current_user_id, tenant_id)
        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verifying learner access: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    # Get model bindings
    private_brain_service = PrivateBrainService(db)
    return private_brain_service.get_model_bindings(learner_id)
