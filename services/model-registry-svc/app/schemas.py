"""
AIVO Model Registry - Pydantic Schemas
S2-02 Implementation: Request/Response models for API endpoints
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from enum import Enum

from .models import ModelTaskType, ProviderBindingStatus


# Base schemas
class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# Model schemas
class ModelCreate(BaseModel):
    """Schema for creating a new model"""
    name: str = Field(..., min_length=1, max_length=255, description="Unique model name")
    task: ModelTaskType = Field(..., description="Model task type")
    subject: Optional[str] = Field(None, max_length=255, description="Subject domain/category")
    description: Optional[str] = Field(None, description="Model description")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError('Model name cannot be empty')
        return v.strip().lower()


class ModelUpdate(BaseModel):
    """Schema for updating a model"""
    subject: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None


class ModelResponse(BaseSchema):
    """Schema for model response"""
    id: int
    name: str
    task: str
    subject: Optional[str]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    version_count: Optional[int] = Field(None, description="Total number of versions")
    active_version_count: Optional[int] = Field(None, description="Number of active versions")


# Model version schemas
class ModelVersionCreate(BaseModel):
    """Schema for creating a new model version"""
    model_id: int = Field(..., gt=0, description="Model ID")
    hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hash")
    version: str = Field(..., min_length=1, max_length=50, description="Semantic version")
    region: str = Field("us-east-1", max_length=50, description="Region")
    cost_per_1k: Optional[float] = Field(None, ge=0, description="Cost per 1K tokens/items")
    eval_score: Optional[float] = Field(None, ge=0, le=1, description="Evaluation score (0-1)")
    slo_ok: bool = Field(True, description="SLO compliance")
    
    # Artifact storage
    artifact_uri: Optional[str] = Field(None, max_length=500, description="Artifact storage URI")
    
    # Metadata
    size_bytes: Optional[int] = Field(None, ge=0, description="Model size in bytes")
    model_type: Optional[str] = Field(None, max_length=100, description="Model type")
    framework: Optional[str] = Field(None, max_length=50, description="Framework")
    
    @validator('hash')
    def validate_hash(cls, v):
        if len(v) != 64 or not all(c in '0123456789abcdef' for c in v.lower()):
            raise ValueError('Hash must be a 64-character hexadecimal string')
        return v.lower()
    
    @validator('version')
    def validate_version(cls, v):
        # Basic semantic versioning validation
        parts = v.split('.')
        if len(parts) < 2 or len(parts) > 3:
            raise ValueError('Version must be in format X.Y or X.Y.Z')
        
        for part in parts:
            if not part.isdigit():
                raise ValueError('Version parts must be numeric')
        
        return v


class ModelVersionUpdate(BaseModel):
    """Schema for updating a model version"""
    cost_per_1k: Optional[float] = Field(None, ge=0)
    eval_score: Optional[float] = Field(None, ge=0, le=1)
    slo_ok: Optional[bool] = None


class ModelVersionResponse(BaseSchema):
    """Schema for model version response"""
    id: int
    model_id: int
    hash: str
    version: str
    region: str
    cost_per_1k: Optional[float]
    eval_score: Optional[float]
    slo_ok: bool
    
    artifact_uri: Optional[str]
    archive_uri: Optional[str]
    size_bytes: Optional[int]
    model_type: Optional[str]
    framework: Optional[str]
    
    created_at: datetime
    archived_at: Optional[datetime]
    
    # Related data
    model_name: Optional[str] = Field(None, description="Model name")
    provider_binding_count: Optional[int] = Field(None, description="Number of provider bindings")


# Provider binding schemas
class ProviderBindingCreate(BaseModel):
    """Schema for creating a provider binding"""
    version_id: int = Field(..., gt=0, description="Model version ID")
    provider: str = Field(..., min_length=1, max_length=50, description="Provider name")
    provider_model_id: str = Field(..., min_length=1, max_length=255, description="Provider model ID")
    status: ProviderBindingStatus = Field(ProviderBindingStatus.ACTIVE, description="Binding status")
    config: Optional[Dict[str, Any]] = Field(None, description="Provider-specific config")
    endpoint_url: Optional[str] = Field(None, max_length=500, description="Custom endpoint URL")
    
    @validator('provider')
    def validate_provider(cls, v):
        allowed_providers = {"openai", "vertex", "bedrock", "anthropic", "azure"}
        if v.lower() not in allowed_providers:
            raise ValueError(f'Provider must be one of: {", ".join(allowed_providers)}')
        return v.lower()


class ProviderBindingUpdate(BaseModel):
    """Schema for updating a provider binding"""
    status: Optional[ProviderBindingStatus] = None
    config: Optional[Dict[str, Any]] = None
    endpoint_url: Optional[str] = Field(None, max_length=500)
    avg_latency_ms: Optional[float] = Field(None, ge=0)
    success_rate: Optional[float] = Field(None, ge=0, le=1)


class ProviderBindingResponse(BaseSchema):
    """Schema for provider binding response"""
    id: int
    version_id: int
    provider: str
    provider_model_id: str
    status: str
    config: Optional[Dict[str, Any]]
    endpoint_url: Optional[str]
    
    avg_latency_ms: Optional[float]
    success_rate: Optional[float]
    last_used_at: Optional[datetime]
    
    created_at: datetime
    updated_at: datetime
    
    # Related data
    model_name: Optional[str] = Field(None, description="Model name")
    version: Optional[str] = Field(None, description="Model version")


# List responses
class ModelListResponse(BaseModel):
    """Schema for paginated model list"""
    models: List[ModelResponse]
    total: int
    page: int
    size: int
    pages: int


class ModelVersionListResponse(BaseModel):
    """Schema for paginated model version list"""
    versions: List[ModelVersionResponse]
    total: int
    page: int
    size: int
    pages: int


class ProviderBindingListResponse(BaseModel):
    """Schema for paginated provider binding list"""
    bindings: List[ProviderBindingResponse]
    total: int
    page: int
    size: int
    pages: int


# Query parameter schemas
class ModelFilterParams(BaseModel):
    """Query parameters for model filtering"""
    task: Optional[ModelTaskType] = None
    subject: Optional[str] = None
    name_contains: Optional[str] = Field(None, description="Filter by name substring")


class ModelVersionFilterParams(BaseModel):
    """Query parameters for model version filtering"""
    model_id: Optional[int] = Field(None, gt=0)
    region: Optional[str] = None
    min_eval_score: Optional[float] = Field(None, ge=0, le=1)
    max_cost_per_1k: Optional[float] = Field(None, ge=0)
    slo_ok: Optional[bool] = None
    include_archived: bool = Field(False, description="Include archived versions")


class ProviderBindingFilterParams(BaseModel):
    """Query parameters for provider binding filtering"""
    version_id: Optional[int] = Field(None, gt=0)
    provider: Optional[str] = None
    status: Optional[ProviderBindingStatus] = None
    min_success_rate: Optional[float] = Field(None, ge=0, le=1)


# Retention and statistics schemas
class RetentionPolicyRequest(BaseModel):
    """Schema for applying retention policy"""
    model_id: int = Field(..., gt=0, description="Model ID")
    retention_count: int = Field(3, gt=0, le=10, description="Number of versions to keep")


class RetentionStatsResponse(BaseModel):
    """Schema for retention statistics"""
    model_id: Optional[int]
    total_versions: int
    active_versions: int
    archived_versions: int
    retention_count: int


class ModelStatsResponse(BaseModel):
    """Schema for model statistics"""
    model_count: int
    version_count: int
    active_version_count: int
    archived_version_count: int
    provider_binding_count: int
    
    # Performance stats
    avg_eval_score: Optional[float]
    avg_cost_per_1k: Optional[float]
    avg_success_rate: Optional[float]
    
    # By provider
    provider_distribution: Dict[str, int]
    
    # By task type
    task_distribution: Dict[str, int]


# Health check schema
class HealthCheckResponse(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str = Field(..., description="Service version")
    database_connected: bool = Field(..., description="Database connection status")
    model_count: int = Field(..., description="Total number of models")
    version_count: int = Field(..., description="Total number of versions")
