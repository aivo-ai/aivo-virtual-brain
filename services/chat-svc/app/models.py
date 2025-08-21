"""
Chat Service Database Models
Thread and Message models for per-learner message history
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import datetime
import uuid

Base = declarative_base()


class Thread(Base):
    """
    Chat Thread Model
    Represents a conversation thread scoped to a specific learner
    """
    __tablename__ = "threads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(String(255), nullable=False, index=True)
    subject = Column(String(500), nullable=True)  # Optional conversation topic
    created_by = Column(String(255), nullable=False)  # guardian, teacher, or learner
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Privacy and compliance
    tenant_isolated = Column(Boolean, default=True, nullable=False)
    data_retention_until = Column(DateTime, nullable=True)  # For automatic cleanup
    
    # Relationships
    messages = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_threads_learner_tenant', 'learner_id', 'tenant_id'),
        Index('ix_threads_created_by', 'created_by'),
        Index('ix_threads_created_at', 'created_at'),
        Index('ix_threads_updated_at', 'updated_at'),
    )


class Message(Base):
    """
    Chat Message Model
    Individual messages within a thread with role-based content
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id = Column(UUID(as_uuid=True), ForeignKey("threads.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user, assistant, system
    content = Column(JSONB, nullable=False)  # Structured message content
    tenant_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Message metadata
    message_type = Column(String(100), default="text", nullable=False)  # text, image, file, etc.
    parent_message_id = Column(UUID(as_uuid=True), ForeignKey("messages.id"), nullable=True)
    edited_at = Column(DateTime, nullable=True)
    
    # Privacy and compliance
    tenant_isolated = Column(Boolean, default=True, nullable=False)
    exported_at = Column(DateTime, nullable=True)  # For privacy export tracking
    
    # Relationships
    thread = relationship("Thread", back_populates="messages")
    parent_message = relationship("Message", remote_side=[id])
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_messages_thread_created', 'thread_id', 'created_at'),
        Index('ix_messages_role', 'role'),
        Index('ix_messages_tenant', 'tenant_id'),
        Index('ix_messages_created_at', 'created_at'),
    )


class ChatExportLog(Base):
    """
    Privacy Export Log
    Tracks when chat data was exported for privacy compliance
    """
    __tablename__ = "chat_export_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    export_type = Column(String(50), nullable=False)  # full_export, thread_export
    exported_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    requested_by = Column(String(255), nullable=False)
    export_format = Column(String(50), default="json", nullable=False)
    thread_count = Column(Integer, default=0, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index('ix_export_logs_learner_tenant', 'learner_id', 'tenant_id'),
        Index('ix_export_logs_exported_at', 'exported_at'),
    )


class ChatDeletionLog(Base):
    """
    Privacy Deletion Log
    Tracks when chat data was erased for privacy compliance
    """
    __tablename__ = "chat_deletion_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    learner_id = Column(String(255), nullable=False, index=True)
    tenant_id = Column(String(255), nullable=False, index=True)
    deletion_type = Column(String(50), nullable=False)  # full_deletion, thread_deletion
    deleted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    requested_by = Column(String(255), nullable=False)
    thread_count = Column(Integer, default=0, nullable=False)
    message_count = Column(Integer, default=0, nullable=False)
    reason = Column(String(255), nullable=True)  # privacy_request, retention_policy, etc.
    
    # Indexes
    __table_args__ = (
        Index('ix_deletion_logs_learner_tenant', 'learner_id', 'tenant_id'),
        Index('ix_deletion_logs_deleted_at', 'deleted_at'),
    )
