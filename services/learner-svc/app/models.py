from sqlalchemy import Column, String, UUID, DateTime, Boolean, JSON, Text, ForeignKey, Enum as SQLEnum, Integer
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from datetime import datetime

from .database import Base

class ProvisionSource(enum.Enum):
    PARENT = "parent"
    DISTRICT = "district"
    SCHOOL_SPED = "school_sped"

class ModelProvider(enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"

class Learner(Base):
    __tablename__ = "learners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    dob = Column(DateTime, nullable=False)
    grade_default = Column(String, nullable=False)
    provision_source = Column(SQLEnum(ProvisionSource), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    guardians = relationship("LearnerGuardian", back_populates="learner")
    teachers = relationship("LearnerTeacher", back_populates="learner")
    private_brain_profile = relationship("PrivateBrainProfile", back_populates="learner", uselist=False)
    model_bindings = relationship("ModelBinding", back_populates="learner")

class LearnerGuardian(Base):
    __tablename__ = "learner_guardians"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    learner = relationship("Learner", back_populates="guardians")

class LearnerTeacher(Base):
    __tablename__ = "learner_teachers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    subjects = Column(JSON, nullable=False)  # List of subjects as JSON array
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    learner = relationship("Learner", back_populates="teachers")

class PrivateBrainProfile(Base):
    __tablename__ = "private_brain_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id"), nullable=False, unique=True)
    alias = Column(String(100), nullable=False)  # Safe alias, never legal name
    voice = Column(String(50), nullable=True)  # Voice preference
    tone = Column(String(50), nullable=True)  # Conversation tone
    speech_rate = Column(Integer, nullable=True)  # Speech rate for TTS
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    learner = relationship("Learner", back_populates="private_brain_profile")

class ModelBinding(Base):
    __tablename__ = "model_bindings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(UUID(as_uuid=True), ForeignKey("learners.id"), nullable=False)
    subject = Column(String(100), nullable=False)  # e.g., "math", "reading", "science"
    provider = Column(SQLEnum(ModelProvider), nullable=False, default=ModelProvider.OPENAI)
    model_name = Column(String(100), nullable=False)  # e.g., "gpt-4", "gpt-3.5-turbo"
    adapter_policy_id = Column(UUID(as_uuid=True), ForeignKey("adapter_policies.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    learner = relationship("Learner", back_populates="model_bindings")
    adapter_policy = relationship("AdapterPolicy", back_populates="model_bindings")

class AdapterPolicy(Base):
    __tablename__ = "adapter_policies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    policy_config = Column(JSON, nullable=False)  # Configuration as JSON
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    model_bindings = relationship("ModelBinding", back_populates="adapter_policy")
