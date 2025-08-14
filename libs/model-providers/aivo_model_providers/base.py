"""
Base provider interface and common types for the AIVO Model Providers library.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class ProviderType(str, Enum):
    """Supported provider types."""
    OPENAI = "openai"
    VERTEX_GEMINI = "vertex_gemini" 
    BEDROCK_ANTHROPIC = "bedrock_anthropic"
    AUTO = "auto"  # Auto-detect best available provider


class JobStatus(str, Enum):
    """Job status for async operations like fine-tuning."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ModerationCategory(str, Enum):
    """Content moderation categories."""
    HATE = "hate"
    HARASSMENT = "harassment"
    SELF_HARM = "self-harm"
    SEXUAL = "sexual"
    VIOLENCE = "violence"
    ILLEGAL = "illegal"


# Request/Response Models
class GenerateRequest(BaseModel):
    """Request for text generation."""
    messages: List[Dict[str, str]] = Field(..., description="Chat messages")
    model: str = Field(..., description="Model identifier")
    max_tokens: Optional[int] = Field(None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: Optional[float] = Field(None, ge=-2.0, le=2.0, description="Presence penalty")
    stop: Optional[Union[str, List[str]]] = Field(None, description="Stop sequences")
    stream: bool = Field(False, description="Stream response")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class GenerateResponse(BaseModel):
    """Response from text generation."""
    content: str = Field(..., description="Generated text content")
    model: str = Field(..., description="Model used")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    finish_reason: Optional[str] = Field(None, description="Why generation stopped")
    provider: str = Field(..., description="Provider that handled request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class EmbedRequest(BaseModel):
    """Request for text embeddings."""
    texts: List[str] = Field(..., description="Texts to embed")
    model: str = Field(..., description="Embedding model identifier")
    dimensions: Optional[int] = Field(None, description="Embedding dimensions")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class EmbedResponse(BaseModel):
    """Response from text embedding."""
    embeddings: List[List[float]] = Field(..., description="Generated embeddings")
    model: str = Field(..., description="Model used")
    usage: Dict[str, int] = Field(..., description="Token usage statistics")
    provider: str = Field(..., description="Provider that handled request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class ModerationResult(BaseModel):
    """Single moderation result."""
    category: ModerationCategory = Field(..., description="Moderation category")
    score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    flagged: bool = Field(..., description="Whether content was flagged")


class ModerateRequest(BaseModel):
    """Request for content moderation."""
    content: str = Field(..., description="Content to moderate")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class ModerateResponse(BaseModel):
    """Response from content moderation."""
    flagged: bool = Field(..., description="Whether any content was flagged")
    results: List[ModerationResult] = Field(..., description="Detailed moderation results")
    provider: str = Field(..., description="Provider that handled request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class FineTuneRequest(BaseModel):
    """Request for fine-tuning a model."""
    training_file_url: str = Field(..., description="URL to training data file")
    model: str = Field(..., description="Base model to fine-tune")
    validation_file_url: Optional[str] = Field(None, description="URL to validation data file")
    hyperparameters: Optional[Dict[str, Any]] = Field(None, description="Training hyperparameters")
    suffix: Optional[str] = Field(None, description="Model name suffix")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class FineTuneResponse(BaseModel):
    """Response from fine-tuning request."""
    job_id: str = Field(..., description="Fine-tuning job ID")
    status: JobStatus = Field(..., description="Initial job status")
    model: str = Field(..., description="Base model being fine-tuned")
    estimated_completion_time: Optional[str] = Field(None, description="Estimated completion time")
    provider: str = Field(..., description="Provider that handled request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class JobStatusRequest(BaseModel):
    """Request for job status."""
    job_id: str = Field(..., description="Job identifier")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


class JobStatusResponse(BaseModel):
    """Response from job status query."""
    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: Optional[float] = Field(None, ge=0.0, le=1.0, description="Completion progress")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    result: Optional[Dict[str, Any]] = Field(None, description="Job results if completed")
    created_at: Optional[str] = Field(None, description="Job creation time")
    completed_at: Optional[str] = Field(None, description="Job completion time")
    provider: str = Field(..., description="Provider that handled request")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Provider-specific metadata")


# Exceptions
class ProviderError(Exception):
    """Base exception for provider errors."""
    def __init__(self, message: str, provider: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.error_code = error_code


class ProviderUnavailableError(ProviderError):
    """Provider is unavailable (e.g., missing credentials)."""
    pass


class ProviderConfigError(ProviderError):
    """Provider configuration error."""
    pass


class ProviderRateLimitError(ProviderError):
    """Provider rate limit exceeded."""
    def __init__(self, message: str, provider: str, retry_after: Optional[int] = None):
        super().__init__(message, provider)
        self.retry_after = retry_after


class ProviderQuotaError(ProviderError):
    """Provider quota exceeded."""
    pass


class Provider(ABC):
    """Abstract base class for all model providers."""

    def __init__(self, provider_type: ProviderType):
        self.provider_type = provider_type
        self.logger = structlog.get_logger().bind(provider=provider_type.value)

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass

    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate text using the provider's models."""
        pass

    @abstractmethod
    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        """Create embeddings using the provider's models."""
        pass

    @abstractmethod
    async def moderate(self, request: ModerateRequest) -> ModerateResponse:
        """Moderate content using the provider's safety features."""
        pass

    @abstractmethod
    async def fine_tune(self, request: FineTuneRequest) -> FineTuneResponse:
        """Start a fine-tuning job."""
        pass

    @abstractmethod
    async def job_status(self, request: JobStatusRequest) -> JobStatusResponse:
        """Get the status of a fine-tuning job."""
        pass

    @abstractmethod
    async def get_available_models(self) -> Dict[str, List[str]]:
        """Get available models by capability (generate, embed, moderate)."""
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        pass
