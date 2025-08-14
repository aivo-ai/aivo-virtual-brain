"""
AIVO Inference Gateway - Embeddings Router
S2-01 Implementation: FastAPI router for text embeddings with batch support
"""

import time
from typing import Dict, List, Optional, Union, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field
from opentelemetry import trace

from ..providers.base import (
    BaseProvider, ProviderType, EmbeddingRequest, EmbeddingResponse,
    ProviderError, RateLimitError, SLATier
)
from ..policy import PolicyEngine, RoutingContext
from ..pii import PIIScrubber

tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/v1/embeddings", tags=["embeddings"])


class EmbeddingAPIRequest(BaseModel):
    """API request model for embeddings"""
    input: Union[str, List[str]] = Field(..., description="Text to embed")
    model: str = Field(default="text-embedding-3-large", description="Embedding model")
    encoding_format: str = Field(default="float", description="Encoding format")
    dimensions: Optional[int] = Field(default=None, description="Output dimensions")
    user: Optional[str] = Field(default=None, description="User identifier")
    subject: Optional[str] = Field(default=None, description="Subject for routing")
    locale: Optional[str] = Field(default=None, description="Locale for routing") 
    sla_tier: str = Field(default="standard", description="SLA tier")
    user_id: Optional[str] = Field(default=None, description="User ID")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")
    scrub_pii: bool = Field(default=True, description="Enable PII scrubbing")


class EmbeddingAPIResponse(BaseModel):
    """API response model for embeddings"""
    data: List[Dict[str, Any]]
    model: str
    usage: Dict[str, int]
    provider: str
    latency_ms: int
    cost_usd: float = 0.0
    pii_detected: bool = False
    pii_scrubbed: bool = False
    request_id: str


class EmbeddingData(BaseModel):
    """Single embedding data"""
    object: str = "embedding"
    embedding: List[float]
    index: int


class EmbeddingService:
    """Core embedding service with provider management"""
    
    def __init__(self, providers: Dict[ProviderType, BaseProvider],
                 policy_engine: PolicyEngine, pii_scrubber: PIIScrubber):
        self.providers = providers
        self.policy_engine = policy_engine
        self.pii_scrubber = pii_scrubber
    
    async def create_embeddings(self, request: EmbeddingAPIRequest, 
                              request_id: str) -> EmbeddingAPIResponse:
        """Create embeddings with provider routing and safety checks"""
        start_time = time.time()
        
        with tracer.start_as_current_span("create_embeddings") as span:
            span.set_attribute("model", request.model)
            span.set_attribute("request_id", request_id)
            
            # Normalize input to list
            inputs = [request.input] if isinstance(request.input, str) else request.input
            span.set_attribute("input_count", len(inputs))
            
            # Create routing context
            routing_context = RoutingContext(
                subject=request.subject,
                locale=request.locale,
                sla_tier=SLATier(request.sla_tier.lower()),
                model=request.model,
                request_type="embed",
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )
            
            # Get provider routing order
            provider_order = self.policy_engine.route_request(routing_context)
            span.set_attribute("provider_order", [p.value for p in provider_order])
            
            # PII scrubbing
            pii_detected = False
            pii_scrubbed = False
            processed_inputs = inputs
            
            if request.scrub_pii:
                scrubbed_inputs = []
                all_matches = []
                
                for input_text in inputs:
                    scrubbed_text, matches = self.pii_scrubber.scrub_text(input_text)
                    scrubbed_inputs.append(scrubbed_text)
                    all_matches.extend(matches)
                
                if all_matches:
                    pii_detected = True
                    pii_scrubbed = True
                    processed_inputs = scrubbed_inputs
                    span.set_attribute("pii_matches", len(all_matches))
            
            # Process embeddings in batches if needed
            batch_size = 100  # Most providers support up to 100-200 texts per request
            all_embeddings = []
            total_usage = {"prompt_tokens": 0, "total_tokens": 0}
            total_cost = 0.0
            
            # Try providers in order with failover
            last_error = None
            for provider_type in provider_order:
                provider = self.providers.get(provider_type)
                if not provider:
                    continue
                
                try:
                    span.set_attribute("active_provider", provider_type.value)
                    
                    # Process in batches
                    for i in range(0, len(processed_inputs), batch_size):
                        batch = processed_inputs[i:i + batch_size]
                        
                        # Create provider request
                        provider_request = EmbeddingRequest(
                            input=batch if len(batch) > 1 else batch[0],
                            model=request.model,
                            encoding_format=request.encoding_format,
                            dimensions=request.dimensions
                        )
                        
                        response = await provider.embed(provider_request)
                        
                        # Normalize response embeddings to list
                        batch_embeddings = response.embeddings
                        if not isinstance(batch_embeddings[0], list):
                            batch_embeddings = [batch_embeddings]
                        
                        all_embeddings.extend(batch_embeddings)
                        
                        # Accumulate usage and cost
                        if response.usage:
                            total_usage["prompt_tokens"] += response.usage.get("prompt_tokens", 0)
                            total_usage["total_tokens"] += response.usage.get("total_tokens", 0)
                        
                        total_cost += getattr(response, 'cost_usd', 0.0)
                    
                    # Record success
                    total_latency = int((time.time() - start_time) * 1000)
                    self.policy_engine.record_success(
                        provider_type, total_latency, total_cost
                    )
                    
                    # Format response data
                    embedding_data = []
                    for idx, embedding in enumerate(all_embeddings):
                        embedding_data.append({
                            "object": "embedding",
                            "embedding": embedding,
                            "index": idx
                        })
                    
                    span.set_attribute("total_latency_ms", total_latency)
                    span.set_attribute("success", True)
                    span.set_attribute("embeddings_generated", len(all_embeddings))
                    
                    return EmbeddingAPIResponse(
                        data=embedding_data,
                        model=getattr(response, 'model', request.model),
                        usage=total_usage,
                        provider=getattr(response, 'provider', provider_type.value),
                        latency_ms=total_latency,
                        cost_usd=total_cost,
                        pii_detected=pii_detected,
                        pii_scrubbed=pii_scrubbed,
                        request_id=request_id
                    )
                
                except RateLimitError as e:
                    self.policy_engine.record_failure(provider_type, "rate_limit")
                    last_error = e
                    continue
                
                except ProviderError as e:
                    self.policy_engine.record_failure(provider_type, "provider_error")
                    last_error = e
                    continue
                
                except Exception as e:
                    self.policy_engine.record_failure(provider_type, "unknown")
                    last_error = e
                    continue
            
            # All providers failed
            span.set_attribute("success", False)
            span.record_exception(last_error or Exception("No providers available"))
            
            raise HTTPException(
                status_code=503,
                detail=f"All providers failed. Last error: {str(last_error)}"
            )
    
    async def get_embedding_models(self) -> List[Dict[str, str]]:
        """Get list of available embedding models"""
        # Static list of supported models across providers
        models = [
            {
                "id": "text-embedding-3-large",
                "object": "model",
                "provider": "openai",
                "dimensions": 3072
            },
            {
                "id": "text-embedding-3-small", 
                "object": "model",
                "provider": "openai",
                "dimensions": 1536
            },
            {
                "id": "text-embedding-ada-002",
                "object": "model", 
                "provider": "openai",
                "dimensions": 1536
            },
            {
                "id": "textembedding-gecko@003",
                "object": "model",
                "provider": "vertex",
                "dimensions": 768
            },
            {
                "id": "amazon.titan-embed-text-v1",
                "object": "model",
                "provider": "bedrock",
                "dimensions": 1536
            },
            {
                "id": "amazon.titan-embed-text-v2:0",
                "object": "model",
                "provider": "bedrock", 
                "dimensions": 1024
            }
        ]
        
        return models


# Dependency injection
embedding_service: Optional[EmbeddingService] = None

def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    if embedding_service is None:
        raise HTTPException(status_code=503, detail="Embedding service not initialized")
    return embedding_service


@router.post("", response_model=EmbeddingAPIResponse)
async def create_embedding(
    request: EmbeddingAPIRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    service: EmbeddingService = Depends(get_embedding_service)
):
    """Create embeddings for input text(s)"""
    request_id = http_request.headers.get("x-request-id", f"emb_{int(time.time())}")
    
    # Validate input
    if isinstance(request.input, list) and len(request.input) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Too many inputs. Maximum 1000 texts per request."
        )
    
    return await service.create_embeddings(request, request_id)


@router.get("/models")
async def list_embedding_models(
    service: EmbeddingService = Depends(get_embedding_service)
):
    """List available embedding models"""
    models = await service.get_embedding_models()
    return {
        "object": "list",
        "data": models
    }


@router.post("/similarity")
async def compute_similarity(
    texts1: List[str] = Field(..., description="First set of texts"),
    texts2: List[str] = Field(..., description="Second set of texts"),
    model: str = Field(default="text-embedding-3-large", description="Embedding model"),
    http_request: Request = None,
    service: EmbeddingService = Depends(get_embedding_service)
):
    """Compute cosine similarity between two sets of texts"""
    import numpy as np
    
    request_id = http_request.headers.get("x-request-id", f"sim_{int(time.time())}")
    
    # Get embeddings for both sets
    request1 = EmbeddingAPIRequest(input=texts1, model=model, scrub_pii=True)
    request2 = EmbeddingAPIRequest(input=texts2, model=model, scrub_pii=True)
    
    response1 = await service.create_embeddings(request1, f"{request_id}_1")
    response2 = await service.create_embeddings(request2, f"{request_id}_2")
    
    # Compute similarities
    embeddings1 = np.array([item["embedding"] for item in response1.data])
    embeddings2 = np.array([item["embedding"] for item in response2.data])
    
    # Cosine similarity matrix
    similarities = np.dot(embeddings1, embeddings2.T) / (
        np.linalg.norm(embeddings1, axis=1, keepdims=True) * 
        np.linalg.norm(embeddings2, axis=1, keepdims=False)
    )
    
    return {
        "similarities": similarities.tolist(),
        "model": model,
        "request_id": request_id,
        "shape": list(similarities.shape)
    }


@router.get("/health")
async def embedding_health():
    """Health check for embedding endpoints"""
    return {
        "status": "healthy",
        "service": "embeddings",
        "timestamp": time.time()
    }
