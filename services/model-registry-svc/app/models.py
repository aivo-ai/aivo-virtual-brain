"""
AIVO Model Registry - Database Models
S2-02 Implementation: Model→Version→ProviderBinding tracking with retention
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Float, Boolean, Text,
    ForeignKey, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

Base = declarative_base()


class ModelTaskType(str, Enum):
    """Model task types"""
    GENERATION = "generation"
    EMBEDDING = "embedding"
    MODERATION = "moderation"
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    TRANSLATION = "translation"


class ProviderBindingStatus(str, Enum):
    """Provider binding status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class Model(Base):
    """Model registry table - tracks AI models by name, task, and subject domain"""
    
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True, index=True)
    task = Column(String(50), nullable=False, index=True)  # ModelTaskType enum
    subject = Column(String(255), nullable=True, index=True)  # Subject domain/category
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    versions = relationship("ModelVersion", back_populates="model", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_model_task_subject', 'task', 'subject'),
        Index('idx_model_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Model(id={self.id}, name='{self.name}', task='{self.task}')>"


class ModelVersion(Base):
    """Model version table - tracks specific versions with eval scores and costs"""
    
    __tablename__ = "model_versions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False, index=True)
    hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of model artifacts
    version = Column(String(50), nullable=False)  # Semantic version (e.g., "1.0.0")
    region = Column(String(50), nullable=False, default="us-east-1")
    cost_per_1k = Column(Float, nullable=True)  # Cost per 1K tokens/items
    eval_score = Column(Float, nullable=True)  # Evaluation metric score (0-1)
    slo_ok = Column(Boolean, nullable=False, default=True)  # SLO compliance
    
    # Artifact storage
    artifact_uri = Column(String(500), nullable=True)  # S3/GCS URI for model artifacts
    archive_uri = Column(String(500), nullable=True)  # Glacier/Archive URI for old versions
    
    # Metadata
    size_bytes = Column(Integer, nullable=True)
    model_type = Column(String(100), nullable=True)  # e.g., "transformer", "llm", "embedding"
    framework = Column(String(50), nullable=True)  # e.g., "pytorch", "tensorflow", "onnx"
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    archived_at = Column(DateTime, nullable=True)  # When moved to archive storage
    
    # Relationships
    model = relationship("Model", back_populates="versions")
    provider_bindings = relationship("ProviderBinding", back_populates="version", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('model_id', 'hash', name='uq_model_version_hash'),
        UniqueConstraint('model_id', 'version', name='uq_model_version'),
        Index('idx_version_model_created', 'model_id', 'created_at'),
        Index('idx_version_eval_score', 'eval_score'),
        Index('idx_version_cost', 'cost_per_1k'),
        Index('idx_version_region', 'region'),
    )
    
    def __repr__(self):
        return f"<ModelVersion(id={self.id}, model_id={self.model_id}, version='{self.version}')>"


class ProviderBinding(Base):
    """Provider binding table - maps model versions to provider-specific model IDs"""
    
    __tablename__ = "provider_bindings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    version_id = Column(Integer, ForeignKey("model_versions.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)  # "openai", "vertex", "bedrock"
    provider_model_id = Column(String(255), nullable=False)  # Provider's model identifier
    status = Column(String(20), nullable=False, default="active", index=True)  # ProviderBindingStatus
    
    # Provider-specific configuration
    config = Column(Text, nullable=True)  # JSON config for provider-specific settings
    endpoint_url = Column(String(500), nullable=True)  # Custom endpoint if applicable
    
    # Performance tracking
    avg_latency_ms = Column(Float, nullable=True)
    success_rate = Column(Float, nullable=True, default=1.0)  # 0-1 success rate
    last_used_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    version = relationship("ModelVersion", back_populates="provider_bindings")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('version_id', 'provider', name='uq_version_provider'),
        Index('idx_binding_provider_status', 'provider', 'status'),
        Index('idx_binding_success_rate', 'success_rate'),
        Index('idx_binding_last_used', 'last_used_at'),
    )
    
    def __repr__(self):
        return f"<ProviderBinding(id={self.id}, version_id={self.version_id}, provider='{self.provider}')>"


# Retention policy implementation
class RetentionManager:
    """Manages model version retention policies"""
    
    DEFAULT_RETENTION_COUNT = 3
    
    def __init__(self, session: Session):
        self.session = session
    
    def apply_retention_policy(self, model_id: int, retention_count: int = DEFAULT_RETENTION_COUNT) -> int:
        """
        Apply retention policy to a model - keep last N versions, archive older ones
        Returns number of versions archived
        """
        # Get all versions for the model ordered by creation date (newest first)
        versions = (
            self.session.query(ModelVersion)
            .filter(ModelVersion.model_id == model_id)
            .filter(ModelVersion.archived_at.is_(None))  # Only active versions
            .order_by(ModelVersion.created_at.desc())
            .all()
        )
        
        if len(versions) <= retention_count:
            return 0
        
        # Archive versions beyond retention count
        versions_to_archive = versions[retention_count:]
        archived_count = 0
        
        for version in versions_to_archive:
            if version.artifact_uri and not version.archive_uri:
                # Simulate moving to archive storage (Glacier)
                version.archive_uri = self._generate_archive_uri(version)
                version.archived_at = func.now()
                archived_count += 1
        
        self.session.commit()
        return archived_count
    
    def _generate_archive_uri(self, version: ModelVersion) -> str:
        """Generate archive URI for a model version"""
        # In production, this would be actual Glacier/Archive storage
        # For dev, simulate with archive prefix
        if version.artifact_uri:
            return version.artifact_uri.replace("s3://", "glacier://")
        else:
            model_name = version.model.name if version.model else f"model_{version.model_id}"
            return f"glacier://aivo-model-archive/{model_name}/v{version.version}/{version.hash}"
    
    def cleanup_archived_versions(self, days_old: int = 90) -> int:
        """
        Clean up very old archived versions
        Returns number of versions deleted
        """
        cutoff_date = func.date_sub(func.now(), func.interval(days_old, 'day'))
        
        # Delete versions archived more than X days ago
        deleted = (
            self.session.query(ModelVersion)
            .filter(ModelVersion.archived_at < cutoff_date)
            .delete()
        )
        
        self.session.commit()
        return deleted
    
    def get_retention_stats(self, model_id: int = None) -> dict:
        """Get retention statistics for models"""
        query = self.session.query(ModelVersion)
        if model_id:
            query = query.filter(ModelVersion.model_id == model_id)
        
        total_versions = query.count()
        active_versions = query.filter(ModelVersion.archived_at.is_(None)).count()
        archived_versions = query.filter(ModelVersion.archived_at.is_not(None)).count()
        
        return {
            "total_versions": total_versions,
            "active_versions": active_versions,
            "archived_versions": archived_versions,
            "retention_count": self.DEFAULT_RETENTION_COUNT
        }


# Database utility functions
def get_active_versions_for_model(session: Session, model_id: int) -> list[ModelVersion]:
    """Get active (non-archived) versions for a model"""
    return (
        session.query(ModelVersion)
        .filter(ModelVersion.model_id == model_id)
        .filter(ModelVersion.archived_at.is_(None))
        .order_by(ModelVersion.created_at.desc())
        .all()
    )


def get_best_version_for_model(session: Session, model_id: int) -> Optional[ModelVersion]:
    """Get the best performing active version for a model based on eval_score"""
    return (
        session.query(ModelVersion)
        .filter(ModelVersion.model_id == model_id)
        .filter(ModelVersion.archived_at.is_(None))
        .filter(ModelVersion.eval_score.is_not(None))
        .order_by(ModelVersion.eval_score.desc(), ModelVersion.created_at.desc())
        .first()
    )


def get_provider_bindings_for_version(session: Session, version_id: int) -> list[ProviderBinding]:
    """Get all provider bindings for a model version"""
    return (
        session.query(ProviderBinding)
        .filter(ProviderBinding.version_id == version_id)
        .filter(ProviderBinding.status == ProviderBindingStatus.ACTIVE)
        .order_by(ProviderBinding.success_rate.desc())
        .all()
    )
