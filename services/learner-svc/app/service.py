from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import List, Optional
import uuid
from datetime import datetime

from .models import Learner, LearnerGuardian, LearnerTeacher, ProvisionSource
from .schemas import LearnerCreateRequest, LearnerResponse, TeacherAttachRequest, EventPayload
from .utils import grade_calculator
from .events import publish_event

class LearnerService:
    """Service layer for learner management operations."""

    def __init__(self, db: Session):
        self.db = db

    def create_learner(self, learner_data: LearnerCreateRequest, current_user_id: str, tenant_id: Optional[str] = None) -> LearnerResponse:
        """Create a new learner with grade calculation and guardian linking."""

        # Calculate default grade from DOB
        grade_default = grade_calculator.calculate_grade_default(learner_data.dob)

        # Create learner record
        db_learner = Learner(
            dob=learner_data.dob,
            grade_default=grade_default,
            provision_source=ProvisionSource(learner_data.provision_source.value),
            tenant_id=learner_data.tenant_id or tenant_id
        )

        self.db.add(db_learner)
        self.db.flush()  # Get the ID without committing

        # Link guardian if provided or if provision source is parent
        guardian_user_id = learner_data.guardian_user_id
        if learner_data.provision_source == "parent":
            guardian_user_id = guardian_user_id or current_user_id

        if guardian_user_id:
            guardian_link = LearnerGuardian(
                learner_id=db_learner.id,
                user_id=uuid.UUID(guardian_user_id)
            )
            self.db.add(guardian_link)

        self.db.commit()
        self.db.refresh(db_learner)

        # Publish LEARNER_CREATED event
        event_payload = EventPayload(
            learner_id=db_learner.id,
            provision_source=db_learner.provision_source.value,
            tenant_id=db_learner.tenant_id,
            created_at=db_learner.created_at
        )
        publish_event("LEARNER_CREATED", event_payload.dict())

        # Create default model bindings for private brain
        self._create_default_model_bindings(db_learner.id)

        return LearnerResponse.from_orm(db_learner)

    def get_learner(self, learner_id: str, current_user_id: str, tenant_id: Optional[str] = None) -> Optional[LearnerResponse]:
        """Get learner by ID with tenant scoping."""
        learner = self.db.query(Learner).filter(Learner.id == uuid.UUID(learner_id)).first()

        if not learner:
            return None

        # Tenant scope enforcement
        if tenant_id and learner.tenant_id != uuid.UUID(tenant_id):
            raise HTTPException(status_code=403, detail="Access denied: tenant scope violation")

        # Check if user has access (is guardian or teacher)
        if not self._user_has_access(learner.id, current_user_id):
            raise HTTPException(status_code=403, detail="Access denied: not authorized for this learner")

        return LearnerResponse.from_orm(learner)

    def attach_teacher(self, learner_id: str, teacher_data: TeacherAttachRequest, current_user_id: str, tenant_id: Optional[str] = None) -> dict:
        """Attach teacher to learner with subjects."""
        learner = self.db.query(Learner).filter(Learner.id == uuid.UUID(learner_id)).first()

        if not learner:
            raise HTTPException(status_code=404, detail="Learner not found")

        # Tenant scope enforcement
        if tenant_id and learner.tenant_id != uuid.UUID(tenant_id):
            raise HTTPException(status_code=403, detail="Access denied: tenant scope violation")

        # For MVP, we'll use email as user lookup (in real implementation, would lookup user by email)
        # Simulating teacher user ID generation from email
        teacher_user_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, teacher_data.email))

        # Check if teacher already exists for this learner
        existing = self.db.query(LearnerTeacher).filter(
            LearnerTeacher.learner_id == learner.id,
            LearnerTeacher.user_id == uuid.UUID(teacher_user_id)
        ).first()

        if existing:
            # Update subjects
            existing.subjects = teacher_data.subjects
            existing.updated_at = datetime.utcnow()
        else:
            # Create new teacher link
            teacher_link = LearnerTeacher(
                learner_id=learner.id,
                user_id=uuid.UUID(teacher_user_id),
                subjects=teacher_data.subjects
            )
            self.db.add(teacher_link)

        self.db.commit()

        return {
            "learner_id": str(learner.id),
            "teacher_email": teacher_data.email,
            "teacher_user_id": teacher_user_id,
            "subjects": teacher_data.subjects,
            "status": "attached"
        }

    def _user_has_access(self, learner_id: uuid.UUID, user_id: str) -> bool:
        """Check if user has access to learner (is guardian or teacher)."""
        user_uuid = uuid.UUID(user_id)

        # Check if user is guardian
        guardian = self.db.query(LearnerGuardian).filter(
            LearnerGuardian.learner_id == learner_id,
            LearnerGuardian.user_id == user_uuid
        ).first()

        if guardian:
            return True

        # Check if user is teacher
        teacher = self.db.query(LearnerTeacher).filter(
            LearnerTeacher.learner_id == learner_id,
            LearnerTeacher.user_id == user_uuid
        ).first()

        return teacher is not None

    def _create_default_model_bindings(self, learner_id: uuid.UUID) -> None:
        """Create default AI model bindings for a new learner."""
        from .private_brain_service import PrivateBrainService
        
        private_brain_service = PrivateBrainService(self.db)
        event_data = {"learner_id": str(learner_id)}
        private_brain_service.handle_learner_created_event(event_data)

    def _create_default_model_bindings(self, learner_id: uuid.UUID) -> None:
        """Create default model bindings for a new learner."""
        from .private_brain_service import PrivateBrainService
        
        private_brain_service = PrivateBrainService(self.db)
        event_data = {"learner_id": str(learner_id)}
        private_brain_service.handle_learner_created_event(event_data)
