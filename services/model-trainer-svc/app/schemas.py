"""
Pydantic schemas for Model Trainer Service
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator

from .models import EvaluationStatus, JobStatus, Provider


class DatasheetBase(BaseModel):
    """Datasheet information for training datasets"""
    source: str = Field(description="Dataset source")
    license: str = Field(description="Dataset license")
    redaction: str = Field(description="Redaction/privacy measures")
    description: Optional[str] = Field(None, description="Dataset description")
    size: Optional[int] = Field(None, description="Dataset size in records")
    collection_date: Optional[datetime] = Field(None, description="Data collection date")


class PolicyBase(BaseModel):
    """Training policy configuration"""
    scope: str = Field(description="Policy scope (e.g., tenant_123)")
    thresholds: Dict[str, float] = Field(default_factory=dict, description="Evaluation thresholds")
    restrictions: Dict[str, Any] = Field(default_factory=dict, description="Training restrictions")
    retention_days: Optional[int] = Field(None, description="Model retention period")


class TrainingConfigBase(BaseModel):
    """Training configuration parameters"""
    n_epochs: Optional[int] = Field(default=3, ge=1, le=10, description="Number of training epochs")
    batch_size: Optional[int] = Field(default=1, ge=1, le=32, description="Batch size")
    learning_rate_multiplier: Optional[float] = Field(default=0.1, gt=0, le=2.0, description="Learning rate multiplier")
    
    @validator('learning_rate_multiplier')
    def validate_learning_rate(cls, v):
        if v <= 0 or v > 2.0:
            raise ValueError('Learning rate multiplier must be between 0 and 2.0')
        return v


# Training Job Schemas

class TrainingJobCreate(BaseModel):
    """Create training job request"""
    name: str = Field(min_length=1, max_length=255, description="Job name")
    description: Optional[str] = Field(None, description="Job description")
    provider: Provider = Field(description="Training provider")
    base_model: str = Field(min_length=1, description="Base model identifier")
    dataset_uri: str = Field(min_length=1, description="Dataset URI")
    config: TrainingConfigBase = Field(description="Training configuration")
    policy: PolicyBase = Field(description="Policy configuration")
    datasheet: DatasheetBase = Field(description="Dataset datasheet")


class TrainingJobUpdate(BaseModel):
    """Update training job request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[JobStatus] = None


class TrainingJobResponse(BaseModel):
    """Training job response"""
    id: UUID
    name: str
    description: Optional[str]
    status: JobStatus
    provider: Provider
    base_model: str
    dataset_uri: str
    config: Dict[str, Any]
    policy: Dict[str, Any]
    datasheet: Dict[str, Any]
    provider_job_id: Optional[str]
    provider_model_id: Optional[str]
    provider_metadata: Dict[str, Any]
    training_tokens: Optional[int]
    training_cost: Optional[float]
    training_duration: Optional[int]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Evaluation Schemas

class EvaluationThresholds(BaseModel):
    """Evaluation thresholds configuration"""
    pedagogy_score: float = Field(default=0.8, ge=0.0, le=1.0)
    safety_score: float = Field(default=0.9, ge=0.0, le=1.0)
    overall_score: Optional[float] = Field(None, ge=0.0, le=1.0)


class HarnessConfig(BaseModel):
    """Evaluation harness configuration"""
    pedagogy_tests: List[str] = Field(default_factory=list, description="Pedagogy test suite names")
    safety_tests: List[str] = Field(default_factory=list, description="Safety test suite names")
    custom_tests: Dict[str, Any] = Field(default_factory=dict, description="Custom test configurations")
    timeout: Optional[int] = Field(default=600, description="Evaluation timeout in seconds")
    parallel: Optional[bool] = Field(default=True, description="Run tests in parallel")


class EvaluationCreate(BaseModel):
    """Create evaluation request"""
    name: str = Field(min_length=1, max_length=255, description="Evaluation name")
    description: Optional[str] = Field(None, description="Evaluation description")
    harness_config: HarnessConfig = Field(description="Harness configuration")
    thresholds: EvaluationThresholds = Field(description="Pass/fail thresholds")


class EvaluationResponse(BaseModel):
    """Evaluation response"""
    id: UUID
    job_id: UUID
    name: str
    description: Optional[str]
    status: EvaluationStatus
    harness_config: Dict[str, Any]
    thresholds: Dict[str, Any]
    pedagogy_score: Optional[float]
    safety_score: Optional[float]
    overall_score: Optional[float]
    passed: Optional[bool]
    results: Dict[str, Any]
    metrics: Dict[str, Any]
    error_message: Optional[str]
    retry_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Model Promotion Schemas

class PromotionRequest(BaseModel):
    """Model promotion request"""
    force: bool = Field(default=False, description="Force promotion even if evaluation failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional promotion metadata")


class PromotionResponse(BaseModel):
    """Model promotion response"""
    id: UUID
    job_id: UUID
    evaluation_id: Optional[UUID]
    registry_model_id: Optional[UUID]
    registry_version_id: Optional[UUID]
    registry_binding_id: Optional[UUID]
    promoted: bool
    promotion_reason: Optional[str]
    promotion_metadata: Dict[str, Any]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# List Schemas

class TrainingJobList(BaseModel):
    """Training job list response"""
    jobs: List[TrainingJobResponse]
    total: int
    offset: int
    limit: int


class EvaluationList(BaseModel):
    """Evaluation list response"""
    evaluations: List[EvaluationResponse]
    total: int
    offset: int
    limit: int


# Statistics Schemas

class ServiceStats(BaseModel):
    """Service statistics"""
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_evaluations: int
    passed_evaluations: int
    failed_evaluations: int
    total_promotions: int
    successful_promotions: int
    average_training_time: Optional[float]
    total_training_cost: Optional[float]


# Error Schemas

class ErrorResponse(BaseModel):
    """Error response"""
    detail: str
    error_code: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationError(BaseModel):
    """Validation error details"""
    field: str
    message: str
    value: Any = None
