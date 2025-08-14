"""
AIVO Inference Gateway - Generation Router
S2-01 Implementation: FastAPI router for text generation with streaming support
"""

import json
import time
from typing import Dict, List, Optional, AsyncGenerator, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from opentelemetry import trace

from ..providers.base import (
    BaseProvider, ProviderType, GenerateRequest, GenerateResponse,
    StreamChunk, ProviderError, RateLimitError, SLATier
)
from ..policy import PolicyEngine, RoutingContext
from ..pii import PIIScrubber

tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/v1/generate", tags=["generation"])


class GenerateAPIRequest(BaseModel):
    """API request model for text generation"""
    messages: List[Dict[str, str]] = Field(..., description="List of messages")
    model: str = Field(default="gpt-4o", description="Model to use")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=0.7, description="Sampling temperature")
    stream: bool = Field(default=False, description="Enable streaming response")
    subject: Optional[str] = Field(default=None, description="Subject for routing")
    locale: Optional[str] = Field(default=None, description="Locale for routing")
    sla_tier: str = Field(default="standard", description="SLA tier")
    user_id: Optional[str] = Field(default=None, description="User ID")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")
    scrub_pii: bool = Field(default=True, description="Enable PII scrubbing")
    moderate_content: bool = Field(default=True, description="Enable content moderation")


class GenerateAPIResponse(BaseModel):
    """API response model for text generation"""
    content: str
    model: str
    usage: Dict[str, int]
    provider: str
    latency_ms: int
    cost_usd: float
    pii_detected: bool = False
    pii_scrubbed: bool = False
    moderation_flagged: bool = False
    request_id: str


class StreamingChunk(BaseModel):
    """Streaming response chunk"""
    delta: str
    provider: str
    request_id: str


class GenerationService:
    """Core generation service with provider management"""
    
    def __init__(self, providers: Dict[ProviderType, BaseProvider],
                 policy_engine: PolicyEngine, pii_scrubber: PIIScrubber):
        self.providers = providers
        self.policy_engine = policy_engine
        self.pii_scrubber = pii_scrubber
    
    async def generate(self, request: GenerateAPIRequest, request_id: str) -> GenerateAPIResponse:
        """Generate text completion with provider routing and safety checks"""
        start_time = time.time()
        
        with tracer.start_as_current_span("generate_completion") as span:
            span.set_attribute("model", request.model)
            span.set_attribute("stream", request.stream)
            span.set_attribute("request_id", request_id)
            
            # Create routing context
            routing_context = RoutingContext(
                subject=request.subject,
                locale=request.locale,
                sla_tier=SLATier(request.sla_tier.lower()),
                model=request.model,
                request_type="generate",
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )
            
            # Get provider routing order
            provider_order = self.policy_engine.route_request(routing_context)
            span.set_attribute("provider_order", [p.value for p in provider_order])
            
            # Convert messages to internal format
            messages = request.messages
            pii_detected = False
            pii_scrubbed = False
            
            # PII scrubbing
            if request.scrub_pii:
                scrubbed_messages = []
                all_matches = []
                
                for message in messages:
                    scrubbed_msg = {}
                    for key, value in message.items():
                        if isinstance(value, str):
                            scrubbed_value, matches = self.pii_scrubber.scrub_text(value)
                            scrubbed_msg[key] = scrubbed_value
                            all_matches.extend(matches)
                        else:
                            scrubbed_msg[key] = value
                    scrubbed_messages.append(scrubbed_msg)
                
                if all_matches:
                    pii_detected = True
                    pii_scrubbed = True
                    messages = scrubbed_messages
                    span.set_attribute("pii_matches", len(all_matches))
            
            # Content moderation check
            moderation_flagged = False
            if request.moderate_content:
                # Check all message content for safety
                content_to_moderate = " ".join([msg.get("content", "") for msg in messages])
                moderation_flagged = await self._check_content_moderation(
                    content_to_moderate, provider_order[0] if provider_order else ProviderType.OPENAI
                )
                
                if moderation_flagged:
                    span.set_attribute("moderation_flagged", True)
                    raise HTTPException(
                        status_code=400,
                        detail="Content flagged by moderation system"
                    )
            
            # Create provider request
            provider_request = GenerateRequest(
                messages=messages,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                sla_tier=routing_context.sla_tier
            )
            
            # Try providers in order with failover
            last_error = None
            for provider_type in provider_order:
                provider = self.providers.get(provider_type)
                if not provider:
                    continue
                
                try:
                    span.set_attribute("active_provider", provider_type.value)
                    
                    response = await provider.generate(provider_request)
                    
                    # Record success
                    self.policy_engine.record_success(
                        provider_type, response.latency_ms, response.cost_usd
                    )
                    
                    total_latency = int((time.time() - start_time) * 1000)
                    span.set_attribute("total_latency_ms", total_latency)
                    span.set_attribute("success", True)
                    
                    return GenerateAPIResponse(
                        content=response.content,
                        model=response.model,
                        usage=response.usage,
                        provider=response.provider,
                        latency_ms=total_latency,
                        cost_usd=response.cost_usd,
                        pii_detected=pii_detected,
                        pii_scrubbed=pii_scrubbed,
                        moderation_flagged=moderation_flagged,
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
    
    async def generate_stream(self, request: GenerateAPIRequest, 
                            request_id: str) -> AsyncGenerator[str, None]:
        """Generate streaming text completion"""
        with tracer.start_as_current_span("generate_stream") as span:
            span.set_attribute("model", request.model)
            span.set_attribute("stream", True)
            span.set_attribute("request_id", request_id)
            
            # Same routing logic as non-streaming
            routing_context = RoutingContext(
                subject=request.subject,
                locale=request.locale,
                sla_tier=SLATier(request.sla_tier.lower()),
                model=request.model,
                request_type="generate",
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )
            
            provider_order = self.policy_engine.route_request(routing_context)
            
            # PII scrubbing (same as non-streaming)
            messages = request.messages
            if request.scrub_pii:
                scrubbed_messages = []
                for message in messages:
                    scrubbed_msg = {}
                    for key, value in message.items():
                        if isinstance(value, str):
                            scrubbed_value, _ = self.pii_scrubber.scrub_text(value)
                            scrubbed_msg[key] = scrubbed_value
                        else:
                            scrubbed_msg[key] = value
                    scrubbed_messages.append(scrubbed_msg)
                messages = scrubbed_messages
            
            # Content moderation (same as non-streaming)
            if request.moderate_content:
                content_to_moderate = " ".join([msg.get("content", "") for msg in messages])
                moderation_flagged = await self._check_content_moderation(
                    content_to_moderate, provider_order[0] if provider_order else ProviderType.OPENAI
                )
                if moderation_flagged:
                    error_chunk = StreamingChunk(
                        delta="[ERROR: Content flagged by moderation]",
                        provider="moderation",
                        request_id=request_id
                    )
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
                    return
            
            provider_request = GenerateRequest(
                messages=messages,
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                sla_tier=routing_context.sla_tier
            )
            
            # Try providers for streaming
            for provider_type in provider_order:
                provider = self.providers.get(provider_type)
                if not provider:
                    continue
                
                try:
                    span.set_attribute("active_provider", provider_type.value)
                    
                    async for chunk in provider.generate_stream(provider_request):
                        streaming_chunk = StreamingChunk(
                            delta=chunk.delta,
                            provider=chunk.provider,
                            request_id=request_id
                        )
                        yield f"data: {streaming_chunk.model_dump_json()}\n\n"
                    
                    # Stream completed successfully
                    self.policy_engine.record_success(provider_type, 0, 0)  # No latency/cost for streaming
                    yield "data: [DONE]\n\n"
                    return
                
                except Exception as e:
                    self.policy_engine.record_failure(provider_type, "streaming_error")
                    error_chunk = StreamingChunk(
                        delta=f"[ERROR from {provider_type.value}: {str(e)}]",
                        provider=provider_type.value,
                        request_id=request_id
                    )
                    yield f"data: {error_chunk.model_dump_json()}\n\n"
                    continue
            
            # All providers failed
            error_chunk = StreamingChunk(
                delta="[ERROR: All providers failed]",
                provider="gateway",
                request_id=request_id
            )
            yield f"data: {error_chunk.model_dump_json()}\n\n"
    
    async def _check_content_moderation(self, content: str, provider_type: ProviderType) -> bool:
        """Check content moderation using available provider"""
        try:
            provider = self.providers.get(provider_type)
            if not provider:
                return False  # Conservative: allow if no moderation available
            
            from ..providers.base import ModerationRequest
            mod_request = ModerationRequest(input=content)
            mod_response = await provider.moderate(mod_request)
            
            # Flag if confidence > threshold
            return mod_response.flagged or mod_response.score > 0.85
        
        except Exception:
            return False  # Conservative: allow if moderation fails


# Dependency injection
generation_service: Optional[GenerationService] = None

def get_generation_service() -> GenerationService:
    """Get generation service instance"""
    if generation_service is None:
        raise HTTPException(status_code=503, detail="Generation service not initialized")
    return generation_service


@router.post("/chat/completions", response_model=GenerateAPIResponse)
async def create_chat_completion(
    request: GenerateAPIRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    service: GenerationService = Depends(get_generation_service)
):
    """Create a chat completion (OpenAI-compatible endpoint)"""
    request_id = http_request.headers.get("x-request-id", f"req_{int(time.time())}")
    
    if request.stream:
        # Return streaming response
        return StreamingResponse(
            service.generate_stream(request, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id
            }
        )
    else:
        # Return non-streaming response
        return await service.generate(request, request_id)


@router.post("/completions", response_model=GenerateAPIResponse)
async def create_completion(
    request: GenerateAPIRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    service: GenerationService = Depends(get_generation_service)
):
    """Create a text completion (legacy endpoint)"""
    request_id = http_request.headers.get("x-request-id", f"req_{int(time.time())}")
    
    # Convert to chat format if needed
    if request.messages and len(request.messages) == 1:
        # Already in messages format
        pass
    else:
        # Convert legacy prompt to messages format
        prompt = request.messages[0].get("content", "") if request.messages else ""
        request.messages = [{"role": "user", "content": prompt}]
    
    if request.stream:
        return StreamingResponse(
            service.generate_stream(request, request_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Request-ID": request_id
            }
        )
    else:
        return await service.generate(request, request_id)


@router.get("/health")
async def generation_health():
    """Health check for generation endpoints"""
    return {
        "status": "healthy",
        "service": "generation",
        "timestamp": time.time()
    }
