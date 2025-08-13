from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Dict, Optional
import uuid
from datetime import datetime
import logging

from .models import Learner, PrivateBrainProfile, ModelBinding, ModelProvider, AdapterPolicy
from .schemas import PersonaCreateRequest, PersonaResponse, ModelBindingResponse, PrivateBrainReadyEvent
from .alias_utils import validate_alias, redact_alias_from_logs, generate_safe_log_context, AliasValidationError
from .events import publish_event

logger = logging.getLogger(__name__)

# Default model bindings for new learners (MVP configuration)
DEFAULT_MODEL_BINDINGS = [
    {"subject": "math", "provider": ModelProvider.OPENAI, "model_name": "gpt-4"},
    {"subject": "reading", "provider": ModelProvider.OPENAI, "model_name": "gpt-4"},
    {"subject": "science", "provider": ModelProvider.OPENAI, "model_name": "gpt-4"},
    {"subject": "writing", "provider": ModelProvider.OPENAI, "model_name": "gpt-4"},
    {"subject": "general", "provider": ModelProvider.OPENAI, "model_name": "gpt-3.5-turbo"},
]

class PrivateBrainService:
    """Service layer for private brain persona and model binding management."""

    def __init__(self, db: Session):
        self.db = db

    def create_persona(self, learner_id: str, persona_data: PersonaCreateRequest, current_user_id: str) -> PersonaResponse:
        """Create a private brain persona for a learner with alias validation."""
        
        try:
            learner_uuid = uuid.UUID(learner_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid learner ID format")

        # Get learner
        learner = self.db.query(Learner).filter(Learner.id == learner_uuid).first()
        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found")

        # Check if persona already exists
        existing_persona = self.db.query(PrivateBrainProfile).filter(
            PrivateBrainProfile.learner_id == learner_uuid
        ).first()
        
        if existing_persona:
            raise HTTPException(status_code=409, detail="Persona already exists for this learner")

        # Validate alias (includes profanity/PII checks)
        try:
            validate_alias(persona_data.alias)
        except AliasValidationError as e:
            # Log without exposing the alias
            safe_context = generate_safe_log_context(learner_id, persona_data.alias)
            logger.warning(f"Alias validation failed: {safe_context}, reason: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))

        # Create persona
        db_persona = PrivateBrainProfile(
            learner_id=learner_uuid,
            alias=persona_data.alias,
            voice=persona_data.voice,
            tone=persona_data.tone,
            speech_rate=persona_data.speech_rate
        )

        self.db.add(db_persona)
        self.db.commit()
        self.db.refresh(db_persona)

        # Log creation (with alias redacted)
        safe_context = generate_safe_log_context(learner_id, persona_data.alias)
        logger.info(f"Private brain persona created: {safe_context}")

        return PersonaResponse.from_orm(db_persona)

    def handle_learner_created_event(self, event_data: Dict) -> None:
        """Handle LEARNER_CREATED event to seed model bindings."""
        learner_id = event_data.get('learner_id')
        
        if not learner_id:
            logger.error("No learner_id in LEARNER_CREATED event")
            return

        try:
            learner_uuid = uuid.UUID(learner_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid learner_id format in event: {learner_id}")
            return

        # Create default model bindings
        model_bindings = []
        for binding_config in DEFAULT_MODEL_BINDINGS:
            model_binding = ModelBinding(
                learner_id=learner_uuid,
                subject=binding_config["subject"],
                provider=binding_config["provider"],
                model_name=binding_config["model_name"],
                is_active=True
            )
            model_bindings.append(model_binding)
            self.db.add(model_binding)

        try:
            self.db.commit()
            
            # Log successful creation
            subjects = [mb.subject for mb in model_bindings]
            logger.info(f"Model bindings created for learner {learner_id}: {subjects}")
            
            # Check if persona exists, and if so, emit PRIVATE_BRAIN_READY
            persona = self.db.query(PrivateBrainProfile).filter(
                PrivateBrainProfile.learner_id == learner_uuid
            ).first()
            
            if persona:
                self._emit_private_brain_ready(learner_uuid, persona.id, subjects)
                
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to create model bindings for learner {learner_id}: {str(e)}")

    def get_model_bindings(self, learner_id: str) -> List[ModelBindingResponse]:
        """Get all model bindings for a learner."""
        try:
            learner_uuid = uuid.UUID(learner_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid learner ID format")

        bindings = self.db.query(ModelBinding).filter(
            ModelBinding.learner_id == learner_uuid,
            ModelBinding.is_active == True
        ).all()

        return [ModelBindingResponse.from_orm(binding) for binding in bindings]

    def trigger_private_brain_ready_if_complete(self, learner_id: str) -> None:
        """Check if both persona and model bindings exist, then emit PRIVATE_BRAIN_READY."""
        try:
            learner_uuid = uuid.UUID(learner_id)
        except ValueError:
            return

        # Check if persona exists
        persona = self.db.query(PrivateBrainProfile).filter(
            PrivateBrainProfile.learner_id == learner_uuid
        ).first()

        if not persona:
            return

        # Check if model bindings exist
        bindings = self.db.query(ModelBinding).filter(
            ModelBinding.learner_id == learner_uuid,
            ModelBinding.is_active == True
        ).all()

        if bindings:
            subjects = [binding.subject for binding in bindings]
            self._emit_private_brain_ready(learner_uuid, persona.id, subjects)

    def _emit_private_brain_ready(self, learner_id: uuid.UUID, persona_id: uuid.UUID, subjects: List[str]) -> None:
        """Emit PRIVATE_BRAIN_READY event."""
        event_payload = PrivateBrainReadyEvent(
            learner_id=learner_id,
            persona_id=persona_id,
            model_bindings_count=len(subjects),
            subjects=subjects,
            created_at=datetime.utcnow()
        )
        
        safe_context = generate_safe_log_context(str(learner_id))
        logger.info(f"Emitting PRIVATE_BRAIN_READY event: {safe_context}")
        
        publish_event("PRIVATE_BRAIN_READY", event_payload.dict())
