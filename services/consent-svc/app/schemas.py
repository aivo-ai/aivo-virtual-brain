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
    
    class Config:
        schema_extra = {
            "example": {
                "actor_user_id": "guardian_456",
                "consents": [
                    {"key": "media", "value": True},
                    {"key": "chat", "value": False}
                ],
                "metadata": {
                    "source": "guardian_portal",
                    "reason": "parental_decision"
                }
            }
        }


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
    
    class Config:
        schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "learner_id": "learner_123",
                "actor_user_id": "guardian_456",
                "key": "media",
                "value": True,
                "ts": "2025-08-12T12:30:00Z",
                "metadata_json": "{\"source\": \"guardian_portal\"}",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0..."
            }
        }


class ConsentLogResponse(BaseModel):
    """Response containing consent log history"""
    learner_id: str = Field(..., description="Learner user ID")
    total_entries: int = Field(..., description="Total number of log entries")
    entries: List[ConsentLogEntry] = Field(..., description="Log entries")
    
    class Config:
        schema_extra = {
            "example": {
                "learner_id": "learner_123",
                "total_entries": 5,
                "entries": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "learner_id": "learner_123",
                        "actor_user_id": "guardian_456",
                        "key": "media",
                        "value": True,
                        "ts": "2025-08-12T12:30:00Z"
                    }
                ]
            }
        }


class ConsentBulkStateResponse(BaseModel):
    """Response for bulk consent state queries"""
    learners: List[ConsentStateResponse] = Field(..., description="Consent states for multiple learners")
    total_count: int = Field(..., description="Total number of learners")
    
    class Config:
        schema_extra = {
            "example": {
                "learners": [
                    {
                        "learner_id": "learner_123",
                        "media": True,
                        "chat": False,
                        "third_party": True
                    }
                ],
                "total_count": 1
            }
        }


class ConsentGateCheckRequest(BaseModel):
    """Request for gateway consent gate check"""
    learner_id: str = Field(..., description="Learner user ID")
    required_consent: ConsentKey = Field(..., description="Required consent type")
    
    class Config:
        schema_extra = {
            "example": {
                "learner_id": "learner_123",
                "required_consent": "media"
            }
        }


class ConsentGateCheckResponse(BaseModel):
    """Response for gateway consent gate check"""
    learner_id: str = Field(..., description="Learner user ID")
    required_consent: ConsentKey = Field(..., description="Required consent type")
    granted: bool = Field(..., description="Whether consent is granted")
    cached: bool = Field(default=False, description="Whether response was cached")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")
    
    class Config:
        schema_extra = {
            "example": {
                "learner_id": "learner_123",
                "required_consent": "media",
                "granted": True,
                "cached": True,
                "cache_ttl": 300
            }
        }


class ConsentSystemStatus(BaseModel):
    """System status and statistics"""
    service_status: str = Field(..., description="Service health status")
    database_connected: bool = Field(..., description="Database connectivity")
    redis_connected: bool = Field(..., description="Redis connectivity")
    total_learners: int = Field(..., description="Total learners with consent records")
    consent_stats: Dict[ConsentKey, Dict[str, int]] = Field(..., description="Consent statistics")
    
    class Config:
        schema_extra = {
            "example": {
                "service_status": "healthy",
                "database_connected": True,
                "redis_connected": True,
                "total_learners": 1500,
                "consent_stats": {
                    "media": {"granted": 1200, "revoked": 300},
                    "chat": {"granted": 800, "revoked": 700},
                    "third_party": {"granted": 600, "revoked": 900}
                }
            }
        }


class ErrorResponse(BaseModel):
    """Error response format"""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    request_id: Optional[str] = Field(None, description="Request tracking ID")
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "consent_not_found",
                "message": "Consent record not found for learner",
                "details": {"learner_id": "learner_123"},
                "request_id": "req_550e8400"
            }
        }


# Validation helpers

class ConsentValidator:
    """Validation utilities for consent operations"""
    
    @staticmethod
    def validate_learner_id(learner_id: str) -> bool:
        """Validate learner ID format"""
        if not learner_id or len(learner_id.strip()) == 0:
            return False
        return len(learner_id) <= 255
    
    @staticmethod
    def validate_actor_id(actor_id: str) -> bool:
        """Validate actor user ID format"""
        if not actor_id or len(actor_id.strip()) == 0:
            return False
        return len(actor_id) <= 255
    
    @staticmethod
    def validate_consent_keys(keys: List[ConsentKey]) -> bool:
        """Validate consent key list"""
        valid_keys = {ConsentKey.MEDIA, ConsentKey.CHAT, ConsentKey.THIRD_PARTY}
        return all(key in valid_keys for key in keys)


# Cache schemas

class CachedConsentState(BaseModel):
    """Cached consent state for Redis"""
    learner_id: str
    media: bool
    chat: bool
    third_party: bool
    cached_at: datetime
    expires_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
