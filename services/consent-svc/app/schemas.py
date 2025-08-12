"""
Consent Service Schemas
Pydantic models for API requests, responses, and validation
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from enum import Enum


class ConsentKey(str, Enum):
    """Available consent categories"""
    MEDIA = "media"
    CHAT = "chat"
    THIRD_PARTY = "third_party"


class ConsentValue(BaseModel):
    """Individual consent setting"""
    key: ConsentKey = Field(..., description="Consent category")
    value: bool = Field(..., description="Consent granted (true) or revoked (false)")
    
    class Config:
        schema_extra = {
            "example": {
                "key": "media",
                "value": True
            }
        }


class ConsentStateResponse(BaseModel):
    """Current consent state for a learner"""
    learner_id: str = Field(..., description="Learner user ID")
    media: bool = Field(..., description="Media access consent")
    chat: bool = Field(..., description="AI chat interaction consent")
    third_party: bool = Field(..., description="Third-party tools consent")
    created_at: Optional[datetime] = Field(None, description="Initial creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    guardian_id: Optional[str] = Field(None, description="Guardian managing consent")
    tenant_id: Optional[str] = Field(None, description="Tenant/district ID")
    
    class Config:
        schema_extra = {
            "example": {
                "learner_id": "learner_123",
                "media": True,
                "chat": False,
                "third_party": True,
                "created_at": "2025-08-12T10:00:00Z",
                "updated_at": "2025-08-12T12:30:00Z",
                "guardian_id": "guardian_456",
                "tenant_id": "district_001"
            }
        }

class ConsentUpdateRequest(BaseModel):
    """Request to update consent preferences"""
    actor_user_id: str = Field(..., description="User making the consent change")
    consents: List[ConsentValue] = Field(..., description="Consent changes to apply")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional context")
    
    @validator('consents')
    def validate_consents(cls, v):
        """Validate consent updates"""
        if not v:
            raise ValueError("At least one consent change is required")
        
        # Check for duplicate keys
        keys = [consent.key for consent in v]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate consent keys are not allowed")
        
        return v


class ConsentLogEntry(BaseModel):
    """Individual consent log entry"""
    id: str = Field(..., description="Unique log entry ID")
    learner_id: str = Field(..., description="Learner user ID")
    actor_user_id: str = Field(..., description="User who made the change")
    key: ConsentKey = Field(..., description="Consent category")
    value: bool = Field(..., description="Consent value")
    ts: datetime = Field(..., description="Timestamp of change")
    metadata_json: Optional[str] = Field(None, description="Additional metadata")
    ip_address: Optional[str] = Field(None, description="IP address of request")
    user_agent: Optional[str] = Field(None, description="User agent of request")


class ConsentGateCheckRequest(BaseModel):
    """Request for gateway consent gate check"""
    learner_id: str = Field(..., description="Learner user ID")
    required_consent: ConsentKey = Field(..., description="Required consent type")


class ConsentGateCheckResponse(BaseModel):
    """Response for gateway consent gate check"""
    learner_id: str = Field(..., description="Learner user ID")
    required_consent: ConsentKey = Field(..., description="Required consent type")
    granted: bool = Field(..., description="Whether consent is granted")
    cached: bool = Field(default=False, description="Whether response was cached")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")


class ConsentBulkRequest(BaseModel):
    """Request for bulk consent operations"""
    learner_ids: List[str] = Field(..., description="List of learner IDs")
    use_cache: bool = Field(True, description="Use cached values if available")


class ConsentBulkResponse(BaseModel):
    """Response for bulk consent operations"""
    learner_states: List[ConsentStateResponse] = Field(..., description="Consent states")
    total_count: int = Field(..., description="Total learners processed")
    cache_hits: int = Field(0, description="Number of cache hits")


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health details")

class ErrorResponse(BaseModel):
    """Error response format"""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request tracking ID")


class ConsentLogResponse(BaseModel):
    """Response containing consent log history"""
    learner_id: str = Field(..., description="Learner user ID")
    total_entries: int = Field(..., description="Total number of log entries")
    entries: List[ConsentLogEntry] = Field(..., description="Log entries")
