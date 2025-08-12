"""
Consent Service Database Models
SQLAlchemy models for consent state and immutable consent log
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class ConsentLog(Base):
    """
    Immutable consent log table
    Records all consent changes with full audit trail
    """
    __tablename__ = "consent_log"
    
    id = Column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4,
        comment="Unique log entry ID"
    )
    
    learner_id = Column(
        String(255), 
        nullable=False, 
        index=True,
        comment="Learner user ID"
    )
    
    actor_user_id = Column(
        String(255), 
        nullable=False,
        comment="User ID who made the consent change (guardian, admin, etc.)"
    )
    
    key = Column(
        String(100), 
        nullable=False,
        comment="Consent category: media, chat, third_party"
    )
    
    value = Column(
        Boolean, 
        nullable=False,
        comment="Consent value: true (granted) or false (revoked)"
    )
    
    ts = Column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        comment="Timestamp of consent change"
    )
    
    metadata_json = Column(
        Text,
        nullable=True,
        comment="Optional metadata about the consent change context"
    )
    
    ip_address = Column(
        String(45),
        nullable=True,
        comment="IP address of the consent change request"
    )
    
    user_agent = Column(
        Text,
        nullable=True,
        comment="User agent of the consent change request"
    )
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_consent_log_learner_ts', 'learner_id', 'ts'),
        Index('idx_consent_log_learner_key', 'learner_id', 'key'),
        Index('idx_consent_log_ts', 'ts'),
        Index('idx_consent_log_actor', 'actor_user_id'),
        {
            'comment': 'Immutable audit log of all consent changes'
        }
    )


class ConsentState(Base):
    """
    Current consent state table
    Maintains the latest consent preferences for each learner
    """
    __tablename__ = "consent_state"
    
    learner_id = Column(
        String(255), 
        primary_key=True,
        comment="Learner user ID (primary key)"
    )
    
    media = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Media access consent (videos, images, audio)"
    )
    
    chat = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Learner-AI chat interaction consent"
    )
    
    third_party = Column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="Third-party tools and services consent"
    )
    
    created_at = Column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        comment="Initial consent record creation timestamp"
    )
    
    updated_at = Column(
        DateTime, 
        nullable=False, 
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Last consent update timestamp"
    )
    
    guardian_id = Column(
        String(255),
        nullable=True,
        comment="Guardian user ID who manages consent"
    )
    
    tenant_id = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Tenant/district ID for institutional consent management"
    )
    
    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_consent_state_tenant', 'tenant_id'),
        Index('idx_consent_state_guardian', 'guardian_id'),
        Index('idx_consent_state_updated', 'updated_at'),
        {
            'comment': 'Current consent state for each learner'
        }
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'learner_id': self.learner_id,
            'media': self.media,
            'chat': self.chat,
            'third_party': self.third_party,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'guardian_id': self.guardian_id,
            'tenant_id': self.tenant_id
        }
