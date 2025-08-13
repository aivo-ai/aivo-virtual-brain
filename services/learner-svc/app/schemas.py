from pydantic import BaseModel, Field, validator
from typing import List, Optional
from uuid import UUID
from datetime import date, datetime
from enum import Enum

class ProvisionSourceSchema(str, Enum):
    PARENT = "parent"
    DISTRICT = "district"
    SCHOOL_SPED = "school_sped"

class ModelProviderSchema(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"

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

# Private Brain Persona Schemas
class PersonaCreateRequest(BaseModel):
    alias: str = Field(..., min_length=2, max_length=100, description="Safe alias for the learner")
    voice: Optional[str] = Field(None, max_length=50, description="Voice preference for TTS")
    tone: Optional[str] = Field(None, max_length=50, description="Conversation tone preference")
    speech_rate: Optional[int] = Field(None, ge=50, le=200, description="Speech rate for TTS (50-200)")

    @validator('alias')
    def validate_alias_format(cls, v):
        if not v or not v.strip():
            raise ValueError('Alias cannot be empty')
        # Additional validation will be done in the service layer
        return v.strip()

    @validator('speech_rate')
    def validate_speech_rate(cls, v):
        if v is not None and (v < 50 or v > 200):
            raise ValueError('Speech rate must be between 50 and 200')
        return v

class PersonaResponse(BaseModel):
    id: UUID
    learner_id: UUID
    alias: str
    voice: Optional[str]
    tone: Optional[str]
    speech_rate: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ModelBindingResponse(BaseModel):
    id: UUID
    learner_id: UUID
    subject: str
    provider: ModelProviderSchema
    model_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class PrivateBrainReadyEvent(BaseModel):
    learner_id: UUID
    persona_id: UUID
    model_bindings_count: int
    subjects: List[str]
    created_at: datetime
