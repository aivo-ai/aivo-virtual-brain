"""
Database Models for Guardian Identity Verification Service
COPPA-compliant data models with privacy-first design
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, DateTime, Boolean, Integer, Text, 
    Enum, JSON, Index, UniqueConstraint, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import structlog

logger = structlog.get_logger(__name__)

Base = declarative_base()


class VerificationMethod(PyEnum):
    """Verification method types"""
    MICRO_CHARGE = "micro_charge"
    KBA = "kba"
    HYBRID = "hybrid"  # Both methods required


class VerificationStatus(PyEnum):
    """Verification status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"
    RATE_LIMITED = "rate_limited"


class FailureReason(PyEnum):
    """Failure reason codes"""
    INSUFFICIENT_FUNDS = "insufficient_funds"
    CARD_DECLINED = "card_declined"
    KBA_FAILED = "kba_failed"
    EXPIRED = "expired"
    TOO_MANY_ATTEMPTS = "too_many_attempts"
    GEO_RESTRICTED = "geo_restricted"
    PROVIDER_ERROR = "provider_error"
    FRAUD_DETECTED = "fraud_detected"


class GuardianVerification(Base):
    """Main verification record for guardians with privacy-first design"""
    __tablename__ = "guardian_verifications"
    
    # Primary identification
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    guardian_user_id = Column(String(100), nullable=False, index=True)
    tenant_id = Column(String(100), nullable=False, index=True)
    
    # Verification metadata
    verification_method = Column(Enum(VerificationMethod), nullable=False)
    status = Column(Enum(VerificationStatus), nullable=False, default=VerificationStatus.PENDING)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)  # Verification expiry
    
    # Attempt tracking for rate limiting
    attempt_count = Column(Integer, nullable=False, default=0)
    last_attempt_at = Column(DateTime, nullable=True)
    lockout_until = Column(DateTime, nullable=True)
    
    # Failure tracking
    failure_reason = Column(Enum(FailureReason), nullable=True)
    failure_details = Column(Text, nullable=True)  # Minimal, scrubbed details
    
    # Geographic and compliance
    verification_country = Column(String(2), nullable=True)  # ISO country code
    ip_country = Column(String(2), nullable=True)  # For geo-policy enforcement
    
    # Privacy and audit
    data_retention_until = Column(DateTime, nullable=False)  # Auto-deletion date
    consent_version = Column(String(20), nullable=False, default="2025-v1")
    
    # Relationships
    charge_verifications = relationship("ChargeVerification", back_populates="verification", cascade="all, delete-orphan")
    kba_sessions = relationship("KBASession", back_populates="verification", cascade="all, delete-orphan")
    audit_logs = relationship("VerificationAuditLog", back_populates="verification", cascade="all, delete-orphan")
    
    # Indexes for performance and compliance
    __table_args__ = (
        Index('idx_guardian_status', 'guardian_user_id', 'status'),
        Index('idx_tenant_verification', 'tenant_id', 'created_at'),
        Index('idx_expiry_cleanup', 'data_retention_until'),
        Index('idx_lockout_check', 'guardian_user_id', 'lockout_until'),
        UniqueConstraint('guardian_user_id', 'tenant_id', 'created_at', 
                        name='uq_guardian_tenant_verification'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Set default expiry times
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
        if not self.data_retention_until:
            self.data_retention_until = datetime.utcnow() + timedelta(days=90)
    
    @property
    def is_expired(self) -> bool:
        """Check if verification has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_locked_out(self) -> bool:
        """Check if guardian is in lockout period"""
        return self.lockout_until and datetime.utcnow() < self.lockout_until
    
    @property
    def can_retry(self) -> bool:
        """Check if guardian can attempt verification again"""
        return not self.is_locked_out and self.attempt_count < 5


class ChargeVerification(Base):
    """Micro-charge verification details with tokenized storage"""
    __tablename__ = "charge_verifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_id = Column(UUID(as_uuid=True), ForeignKey('guardian_verifications.id'), nullable=False)
    
    # Stripe integration (tokenized)
    stripe_payment_intent_id = Column(String(100), nullable=False, unique=True)
    stripe_customer_id = Column(String(100), nullable=True)  # If customer created
    
    # Charge details (minimal storage)
    charge_amount_cents = Column(Integer, nullable=False, default=10)  # $0.10
    currency = Column(String(3), nullable=False, default="USD")
    
    # Payment method (tokenized)
    payment_method_token = Column(String(100), nullable=True)  # Stripe PM token
    card_fingerprint = Column(String(50), nullable=True)  # For duplicate detection
    card_last_four = Column(String(4), nullable=True)  # Display purposes only
    
    # Processing status
    charge_status = Column(String(50), nullable=False, default="pending")  # Stripe status
    refund_status = Column(String(50), nullable=True)  # Refund status
    refund_id = Column(String(100), nullable=True)  # Stripe refund ID
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    charged_at = Column(DateTime, nullable=True)
    refunded_at = Column(DateTime, nullable=True)
    
    # Privacy compliance
    pii_scrubbed_at = Column(DateTime, nullable=True)  # When PII was removed
    
    # Relationships
    verification = relationship("GuardianVerification", back_populates="charge_verifications")
    
    __table_args__ = (
        Index('idx_stripe_payment_intent', 'stripe_payment_intent_id'),
        Index('idx_verification_charge', 'verification_id', 'created_at'),
        Index('idx_card_fingerprint', 'card_fingerprint'),
    )


class KBASession(Base):
    """Knowledge-Based Authentication session with minimal data storage"""
    __tablename__ = "kba_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_id = Column(UUID(as_uuid=True), ForeignKey('guardian_verifications.id'), nullable=False)
    
    # KBA provider details
    provider_name = Column(String(50), nullable=False)  # e.g., "lexisnexis", "experian"
    provider_session_id = Column(String(100), nullable=False)
    
    # Session tracking
    questions_presented = Column(Integer, nullable=False, default=0)
    questions_answered = Column(Integer, nullable=False, default=0)
    correct_answers = Column(Integer, nullable=False, default=0)
    
    # Scoring (minimal details)
    kba_score = Column(Integer, nullable=True)  # Provider's confidence score
    pass_threshold = Column(Integer, nullable=False, default=80)
    passed = Column(Boolean, nullable=True)
    
    # Geographic compliance
    verification_eligible = Column(Boolean, nullable=False, default=True)  # EU/GDPR compliance
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    
    # Privacy compliance
    provider_data_deleted_at = Column(DateTime, nullable=True)
    
    # Relationships
    verification = relationship("GuardianVerification", back_populates="kba_sessions")
    
    __table_args__ = (
        Index('idx_provider_session', 'provider_name', 'provider_session_id'),
        Index('idx_verification_kba', 'verification_id', 'created_at'),
        Index('idx_kba_expiry', 'expires_at'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(minutes=30)  # KBA session timeout


class VerificationAuditLog(Base):
    """Audit log for verification activities with privacy compliance"""
    __tablename__ = "verification_audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_id = Column(UUID(as_uuid=True), ForeignKey('guardian_verifications.id'), nullable=False)
    
    # Event details
    event_type = Column(String(50), nullable=False)  # "attempt", "success", "failure", etc.
    event_description = Column(String(200), nullable=False)
    
    # Context (minimal)
    ip_address_hash = Column(String(64), nullable=True)  # Hashed IP for compliance
    user_agent_hash = Column(String(64), nullable=True)  # Hashed user agent
    session_id = Column(String(100), nullable=True)  # Session identifier
    
    # Result details
    success = Column(Boolean, nullable=False)
    error_code = Column(String(50), nullable=True)
    
    # Metadata (scrubbed)
    metadata = Column(JSON, nullable=True)  # Additional context, privacy-compliant
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Privacy compliance
    auto_delete_at = Column(DateTime, nullable=False)  # Auto-deletion for compliance
    
    # Relationships
    verification = relationship("GuardianVerification", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_verification_audit', 'verification_id', 'created_at'),
        Index('idx_event_type', 'event_type', 'created_at'),
        Index('idx_audit_deletion', 'auto_delete_at'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.auto_delete_at:
            # Audit logs retained for 1 year for compliance
            self.auto_delete_at = datetime.utcnow() + timedelta(days=365)


class VerificationRateLimit(Base):
    """Rate limiting table for verification attempts"""
    __tablename__ = "verification_rate_limits"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Rate limit scope
    guardian_user_id = Column(String(100), nullable=False, index=True)
    ip_address_hash = Column(String(64), nullable=True, index=True)  # Hashed IP
    rate_limit_type = Column(String(50), nullable=False)  # "daily", "hourly", "per_session"
    
    # Rate limit tracking
    attempt_count = Column(Integer, nullable=False, default=1)
    window_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    window_end = Column(DateTime, nullable=False)
    
    # Lockout details
    locked_out = Column(Boolean, nullable=False, default=False)
    lockout_until = Column(DateTime, nullable=True)
    lockout_reason = Column(String(100), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_guardian_rate_limit', 'guardian_user_id', 'rate_limit_type'),
        Index('idx_ip_rate_limit', 'ip_address_hash', 'rate_limit_type'),
        Index('idx_rate_limit_window', 'window_end'),
        UniqueConstraint('guardian_user_id', 'rate_limit_type', 'window_start',
                        name='uq_guardian_rate_limit_window'),
    )
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.window_end:
            # Default to 24-hour window
            self.window_end = datetime.utcnow() + timedelta(hours=24)


class GeoPolicyRule(Base):
    """Geographic policy rules for verification methods"""
    __tablename__ = "geo_policy_rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Geographic scope
    country_code = Column(String(2), nullable=False, index=True)  # ISO country code
    region_code = Column(String(10), nullable=True)  # State/province if applicable
    
    # Policy details
    micro_charge_allowed = Column(Boolean, nullable=False, default=True)
    kba_allowed = Column(Boolean, nullable=False, default=True)
    minimum_age = Column(Integer, nullable=False, default=18)
    
    # Compliance requirements
    gdpr_applicable = Column(Boolean, nullable=False, default=False)
    coppa_applicable = Column(Boolean, nullable=False, default=False)
    additional_consent_required = Column(Boolean, nullable=False, default=False)
    
    # Policy metadata
    policy_version = Column(String(20), nullable=False, default="2025-v1")
    effective_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_country_policy', 'country_code', 'effective_date'),
        UniqueConstraint('country_code', 'region_code', 'effective_date',
                        name='uq_geo_policy_effective'),
    )
