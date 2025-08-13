from pydantic import BaseModel, Field
from typing import List, Optional, UUID
from datetime import date, datetime
from enum import Enum

class ProvisionSourceSchema(str, Enum):
    PARENT = "parent"
    DISTRICT = "district"
    SCHOOL_SPED = "school_sped"

class LearnerCreateRequest(BaseModel):
    dob: date
    provision_source: ProvisionSourceSchema
    tenant_id: Optional[UUID] = None
    guardian_user_id: Optional[UUID] = None

class LearnerResponse(BaseModel):
    id: UUID
    dob: date
    grade_default: str
    provision_source: ProvisionSourceSchema
    tenant_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TeacherAttachRequest(BaseModel):
    email: str
    subjects: List[str]

class LearnerWithRelationsResponse(LearnerResponse):
    guardians: List[dict] = []
    teachers: List[dict] = []

class EventPayload(BaseModel):
    learner_id: UUID
    provision_source: ProvisionSourceSchema
    tenant_id: Optional[UUID] = None
    created_at: datetime
