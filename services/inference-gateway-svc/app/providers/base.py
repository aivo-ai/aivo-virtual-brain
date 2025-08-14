"""
AIVO Inference Gateway - Provider Base Interface
S2-01 Implementation: Multi-provider inference with failover
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Any, Union
from pydantic import BaseModel, Field
import time
from enum import Enum


class ProviderType(str, Enum):
    OPENAI = "openai"
    VERTEX_GEMINI = "vertex"
    BEDROCK_ANTHROPIC = "bedrock"


class SLATier(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class GenerateRequest(BaseModel):
    """Unified generation request schema"""
    messages: List[Dict[str, str]]
    model: str = "gpt-4o-mini"
    max_tokens: Optional[int] = 4000
    temperature: Optional[float] = 0.7
    stream: bool = False
    subject: Optional[str] = None  # For routing logic
    locale: str = "en-US"
    sla_tier: str = "standard"  # standard, premium, enterprise


class GenerateResponse(BaseModel):
    """Unified generation response schema"""
    content: str
    model: str
    usage: Dict[str, int]
    provider: str
    latency_ms: int
    cost_usd: Optional[float] = None


class StreamChunk(BaseModel):
    """Streaming response chunk"""
    delta: str
    provider: str
    finish_reason: Optional[str] = None


class EmbeddingRequest(BaseModel):
    """Embedding request schema"""
    input: Union[str, List[str]]
    model: str = "text-embedding-3-small"
    dimensions: Optional[int] = None


class EmbeddingResponse(BaseModel):
    """Embedding response schema"""
    embeddings: List[List[float]]
    model: str
    usage: Dict[str, int]
    provider: str
    latency_ms: int


class ModerationRequest(BaseModel):
    """Moderation request schema"""
    input: str
    model: str = "text-moderation-latest"


class ModerationResponse(BaseModel):
    """Moderation response schema"""
    flagged: bool
    score: float
    categories: Dict[str, bool]
    category_scores: Dict[str, float]
    provider: str


class ProviderError(Exception):
    """Base provider error"""
    def __init__(self, message: str, provider: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.provider = provider
        self.status_code = status_code


class RateLimitError(ProviderError):
    """Rate limit exceeded"""
    pass


class QuotaExceededError(ProviderError):
    """Quota exceeded"""
    pass


class BaseProvider(ABC):
    """Abstract base class for inference providers"""
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        self.api_key = api_key
        self.config = config
        self.provider_type = self.get_provider_type()
        self._client = None
    
    @abstractmethod
    def get_provider_type(self) -> ProviderType:
        """Return the provider type"""
        pass
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider client"""
        pass
    
    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate completion (non-streaming)"""
        pass
    
    @abstractmethod
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate completion (streaming)"""
        pass
    
    @abstractmethod
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings"""
        pass
    
    @abstractmethod
    async def moderate(self, request: ModerationRequest) -> ModerationResponse:
        """Content moderation"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check provider health"""
        pass
    
    def calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate cost based on usage (to be overridden by providers)"""
        # Default fallback cost calculation
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        # Default rates (will be overridden by specific providers)
        input_rate = 0.001  # $0.001 per 1K tokens
        output_rate = 0.002  # $0.002 per 1K tokens
        
        return (input_tokens * input_rate + output_tokens * output_rate) / 1000
    
    def supports_model(self, model: str) -> bool:
        """Check if provider supports the requested model"""
        supported_models = self.config.get("supported_models", [])
        return model in supported_models or not supported_models  # Empty list means all models
    
    def get_sla_timeout(self, sla_tier: str) -> float:
        """Get timeout based on SLA tier"""
        timeouts = {
            "enterprise": 30.0,
            "premium": 20.0, 
            "standard": 10.0
        }
        return timeouts.get(sla_tier, 10.0)
