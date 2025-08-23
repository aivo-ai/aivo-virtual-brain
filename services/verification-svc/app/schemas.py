"""
Pydantic schemas for Guardian Identity Verification Service
Request/response models with COPPA-compliant data handling
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum

from app.models import VerificationMethod, VerificationStatus, FailureReason


class VerificationStartRequest(BaseModel):
    """Request to start guardian identity verification"""
    guardian_user_id: str = Field(..., description="Guardian user ID")
    method: VerificationMethod = Field(..., description="Verification method to use")
    return_url: Optional[str] = Field(None, description="URL to redirect after verification")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    # Geographic context
    country_code: Optional[str] = Field(None, description="Guardian's country code (ISO 2-letter)")
    ip_address: Optional[str] = Field(None, description="Guardian's IP address for geo-policy")
    
    # Consent compliance
    consent_version: Optional[str] = Field("2025-v1", description="Consent version accepted")
    coppa_compliant: bool = Field(True, description="Ensure COPPA compliance")
    
    @validator('guardian_user_id')
    def validate_guardian_id(cls, v):
        if not v or len(v) < 3:
            raise ValueError('Guardian user ID must be at least 3 characters')
        return v
    
    @validator('country_code')
    def validate_country_code(cls, v):
        if v and len(v) != 2:
            raise ValueError('Country code must be 2 characters (ISO format)')
        return v.upper() if v else v


class MicroChargeResponse(BaseModel):
    """Response for micro-charge verification initiation"""
    client_secret: str = Field(..., description="Stripe PaymentIntent client secret")
    publishable_key: str = Field(..., description="Stripe publishable key")
    amount_cents: int = Field(..., description="Charge amount in cents")
    currency: str = Field(..., description="Currency code")
    return_url: Optional[str] = Field(None, description="Return URL after payment")


class KBAResponse(BaseModel):
    """Response for KBA verification initiation"""
    session_id: str = Field(..., description="KBA session identifier")
    session_url: str = Field(..., description="URL to complete KBA verification")
    expires_at: datetime = Field(..., description="Session expiration time")
    max_questions: int = Field(..., description="Maximum number of questions")


class VerificationStartResponse(BaseModel):
    """Response for verification start request"""
    verification_id: str = Field(..., description="Verification identifier")
    status: VerificationStatus = Field(..., description="Current verification status")
    method: VerificationMethod = Field(..., description="Verification method")
    expires_at: datetime = Field(..., description="Verification expiration time")
    
    # Method-specific data
    micro_charge: Optional[MicroChargeResponse] = Field(None, description="Micro-charge details")
    kba: Optional[KBAResponse] = Field(None, description="KBA session details")
    
    # Rate limiting info
    attempts_remaining: int = Field(..., description="Verification attempts remaining today")
    next_attempt_at: Optional[datetime] = Field(None, description="When next attempt is allowed")


class VerificationResultRequest(BaseModel):
    """Request to process verification result (webhook/callback)"""
    verification_id: str = Field(..., description="Verification identifier")
    provider: str = Field(..., description="Provider name (stripe, kba_provider)")
    event_type: str = Field(..., description="Event type")
    
    # Provider-specific data
    provider_data: Dict[str, Any] = Field(..., description="Provider event data")
    signature: Optional[str] = Field(None, description="Webhook signature")
    
    # Context
    ip_address: Optional[str] = Field(None, description="Source IP address")
    user_agent: Optional[str] = Field(None, description="User agent string")


class VerificationStatusResponse(BaseModel):
    """Response for verification status check"""
    verification_id: str = Field(..., description="Verification identifier")
    guardian_user_id: str = Field(..., description="Guardian user ID")
    status: VerificationStatus = Field(..., description="Current verification status")
    method: VerificationMethod = Field(..., description="Verification method")
    
    # Timestamps
    created_at: datetime = Field(..., description="Verification creation time")
    updated_at: datetime = Field(..., description="Last update time")
    verified_at: Optional[datetime] = Field(None, description="Verification completion time")
    expires_at: datetime = Field(..., description="Verification expiration time")
    
    # Attempt tracking
    attempt_count: int = Field(..., description="Number of attempts made")
    attempts_remaining: int = Field(..., description="Attempts remaining")
    
    # Failure details (if applicable)
    failure_reason: Optional[FailureReason] = Field(None, description="Failure reason if failed")
    can_retry: bool = Field(..., description="Whether retry is allowed")
    next_retry_at: Optional[datetime] = Field(None, description="When retry is allowed")
    
    # Compliance info
    data_retention_until: datetime = Field(..., description="Data retention end date")


class GuardianVerificationSummary(BaseModel):
    """Summary of guardian verification status for consent gating"""
    guardian_user_id: str = Field(..., description="Guardian user ID")
    is_verified: bool = Field(..., description="Overall verification status")
    verification_method: Optional[VerificationMethod] = Field(None, description="Method used for verification")
    verified_at: Optional[datetime] = Field(None, description="When verification was completed")
    expires_at: Optional[datetime] = Field(None, description="When verification expires")
    
    # Consent integration
    blocks_consent_toggles: bool = Field(..., description="Whether unverified status blocks consent toggles")
    required_for_enrollment: bool = Field(..., description="Whether required for student enrollment")


class VerificationAttemptLog(BaseModel):
    """Log entry for verification attempt"""
    event_type: str = Field(..., description="Event type")
    timestamp: datetime = Field(..., description="Event timestamp")
    success: bool = Field(..., description="Whether event was successful")
    error_code: Optional[str] = Field(None, description="Error code if failed")
    description: str = Field(..., description="Event description")


class VerificationDetailResponse(BaseModel):
    """Detailed verification response for admin/support"""
    verification: VerificationStatusResponse = Field(..., description="Verification details")
    
    # Audit trail
    attempt_logs: List[VerificationAttemptLog] = Field(..., description="Attempt history")
    
    # Provider details (scrubbed)
    charge_details: Optional[Dict[str, Any]] = Field(None, description="Charge details (tokenized)")
    kba_details: Optional[Dict[str, Any]] = Field(None, description="KBA details (minimal)")
    
    # Compliance tracking
    pii_scrubbed: bool = Field(..., description="Whether PII has been scrubbed")
    geo_compliance: Dict[str, Any] = Field(..., description="Geographic compliance status")


class RateLimitResponse(BaseModel):
    """Rate limit status response"""
    guardian_user_id: str = Field(..., description="Guardian user ID")
    rate_limited: bool = Field(..., description="Whether currently rate limited")
    attempts_used_today: int = Field(..., description="Attempts used today")
    attempts_remaining_today: int = Field(..., description="Attempts remaining today")
    lockout_until: Optional[datetime] = Field(None, description="Lockout end time")
    next_attempt_allowed_at: Optional[datetime] = Field(None, description="Next attempt allowed time")


class BulkVerificationStatusRequest(BaseModel):
    """Request for bulk verification status check"""
    guardian_user_ids: List[str] = Field(..., description="List of guardian user IDs")
    tenant_id: Optional[str] = Field(None, description="Tenant ID filter")
    
    @validator('guardian_user_ids')
    def validate_guardian_ids(cls, v):
        if len(v) > 100:  # Reasonable limit
            raise ValueError('Maximum 100 guardian IDs per request')
        return v


class BulkVerificationStatusResponse(BaseModel):
    """Response for bulk verification status check"""
    results: List[GuardianVerificationSummary] = Field(..., description="Verification summaries")
    total_count: int = Field(..., description="Total number of results")
    verified_count: int = Field(..., description="Number of verified guardians")
    unverified_count: int = Field(..., description="Number of unverified guardians")


class WebhookEventResponse(BaseModel):
    """Response for webhook event processing"""
    event_id: str = Field(..., description="Event identifier")
    processed: bool = Field(..., description="Whether event was processed")
    verification_id: Optional[str] = Field(None, description="Related verification ID")
    status_updated: bool = Field(..., description="Whether verification status was updated")
    message: str = Field(..., description="Processing result message")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    checks: Dict[str, str] = Field(..., description="Individual check results")
    verification_stats: Dict[str, Any] = Field(..., description="Verification statistics")


class ErrorResponse(BaseModel):
    """Standard error response"""
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(..., description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")


# Export all schemas
__all__ = [
    "VerificationStartRequest",
    "MicroChargeResponse", 
    "KBAResponse",
    "VerificationStartResponse",
    "VerificationResultRequest",
    "VerificationStatusResponse",
    "GuardianVerificationSummary",
    "VerificationAttemptLog",
    "VerificationDetailResponse",
    "RateLimitResponse",
    "BulkVerificationStatusRequest",
    "BulkVerificationStatusResponse",
    "WebhookEventResponse",
    "HealthCheckResponse",
    "ErrorResponse"
]
