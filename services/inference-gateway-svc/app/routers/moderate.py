"""
AIVO Inference Gateway - Moderation Router
S2-01 Implementation: FastAPI router for content moderation
"""

import time
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from pydantic import BaseModel, Field
from opentelemetry import trace

from ..providers.base import (
    BaseProvider, ProviderType, ModerationRequest, ModerationResponse,
    ProviderError, RateLimitError, SLATier
)
from ..policy import PolicyEngine, RoutingContext

tracer = trace.get_tracer(__name__)

router = APIRouter(prefix="/v1/moderations", tags=["moderation"])


class ModerationAPIRequest(BaseModel):
    """API request model for content moderation"""
    input: str = Field(..., description="Text to moderate")
    model: str = Field(default="text-moderation-latest", description="Moderation model")
    subject: Optional[str] = Field(default=None, description="Subject for routing")
    locale: Optional[str] = Field(default=None, description="Locale for routing")
    sla_tier: str = Field(default="standard", description="SLA tier")
    user_id: Optional[str] = Field(default=None, description="User ID")
    tenant_id: Optional[str] = Field(default=None, description="Tenant ID")


class ModerationAPIResponse(BaseModel):
    """API response model for content moderation"""
    id: str
    model: str
    results: List[Dict[str, Any]]
    provider: str
    latency_ms: int
    request_id: str


class ModerationResult(BaseModel):
    """Single moderation result"""
    flagged: bool
    categories: Dict[str, bool]
    category_scores: Dict[str, float]


class ModerationService:
    """Core moderation service with provider management"""
    
    def __init__(self, providers: Dict[ProviderType, BaseProvider],
                 policy_engine: PolicyEngine):
        self.providers = providers
        self.policy_engine = policy_engine
        
        # Moderation thresholds by category
        self.thresholds = {
            "harassment": 0.8,
            "hate": 0.8,
            "self-harm": 0.7,
            "sexual": 0.85,
            "violence": 0.75,
            "harassment/threatening": 0.8,
            "hate/threatening": 0.8,
            "self-harm/intent": 0.6,
            "self-harm/instructions": 0.7,
            "sexual/minors": 0.3,  # Very strict
            "violence/graphic": 0.8
        }
    
    async def moderate_content(self, request: ModerationAPIRequest,
                             request_id: str) -> ModerationAPIResponse:
        """Moderate content with provider routing"""
        start_time = time.time()
        
        with tracer.start_as_current_span("moderate_content") as span:
            span.set_attribute("model", request.model)
            span.set_attribute("request_id", request_id)
            span.set_attribute("input_length", len(request.input))
            
            # Create routing context
            routing_context = RoutingContext(
                subject=request.subject,
                locale=request.locale,
                sla_tier=SLATier(request.sla_tier.lower()),
                model=request.model,
                request_type="moderate",
                user_id=request.user_id,
                tenant_id=request.tenant_id
            )
            
            # Get provider routing order (prioritize providers with moderation APIs)
            provider_order = self.policy_engine.route_request(routing_context)
            
            # Reorder to prioritize providers with good moderation capabilities
            moderation_priority = [ProviderType.OPENAI, ProviderType.VERTEX_GEMINI, ProviderType.BEDROCK_ANTHROPIC]
            ordered_providers = []
            
            # Add providers with moderation support first
            for ptype in moderation_priority:
                if ptype in provider_order:
                    ordered_providers.append(ptype)
            
            # Add remaining providers
            for ptype in provider_order:
                if ptype not in ordered_providers:
                    ordered_providers.append(ptype)
            
            span.set_attribute("provider_order", [p.value for p in ordered_providers])
            
            # Create provider request
            provider_request = ModerationRequest(input=request.input)
            
            # Try providers in order with failover
            last_error = None
            for provider_type in ordered_providers:
                provider = self.providers.get(provider_type)
                if not provider:
                    continue
                
                try:
                    span.set_attribute("active_provider", provider_type.value)
                    
                    response = await provider.moderate(provider_request)
                    
                    # Apply custom thresholds
                    flagged, adjusted_categories, adjusted_scores = self._apply_thresholds(
                        response.flagged,
                        response.categories,
                        response.category_scores
                    )
                    
                    # Record success
                    total_latency = int((time.time() - start_time) * 1000)
                    self.policy_engine.record_success(provider_type, total_latency, 0.0)
                    
                    # Format response
                    result = {
                        "flagged": flagged,
                        "categories": adjusted_categories,
                        "category_scores": adjusted_scores
                    }
                    
                    span.set_attribute("total_latency_ms", total_latency)
                    span.set_attribute("success", True)
                    span.set_attribute("flagged", flagged)
                    span.set_attribute("max_score", max(adjusted_scores.values()) if adjusted_scores else 0.0)
                    
                    return ModerationAPIResponse(
                        id=f"modr-{request_id}",
                        model=request.model,
                        results=[result],
                        provider=response.provider,
                        latency_ms=total_latency,
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
            
            # All providers failed - return conservative result
            span.set_attribute("success", False)
            span.record_exception(last_error or Exception("No providers available"))
            
            # Conservative fallback: perform basic keyword-based moderation
            conservative_result = self._conservative_moderation(request.input)
            
            return ModerationAPIResponse(
                id=f"modr-{request_id}",
                model="conservative-fallback",
                results=[conservative_result],
                provider="gateway-fallback",
                latency_ms=int((time.time() - start_time) * 1000),
                request_id=request_id
            )
    
    def _apply_thresholds(self, original_flagged: bool, categories: Dict[str, bool],
                         scores: Dict[str, float]) -> tuple[bool, Dict[str, bool], Dict[str, float]]:
        """Apply custom thresholds to moderation results"""
        adjusted_categories = {}
        adjusted_scores = scores.copy()
        
        overall_flagged = original_flagged
        
        # Apply custom thresholds
        for category, score in scores.items():
            threshold = self.thresholds.get(category, 0.8)  # Default threshold
            
            adjusted_categories[category] = score >= threshold
            
            # Update overall flag if any category exceeds threshold
            if score >= threshold:
                overall_flagged = True
        
        return overall_flagged, adjusted_categories, adjusted_scores
    
    def _conservative_moderation(self, text: str) -> Dict[str, Any]:
        """Conservative keyword-based moderation fallback"""
        # Basic keyword lists for different categories
        harassment_keywords = [
            "idiot", "stupid", "moron", "loser", "pathetic", "worthless"
        ]
        hate_keywords = [
            # Note: In production, use more comprehensive and context-aware detection
        ]
        violence_keywords = [
            "kill", "murder", "hurt", "harm", "attack", "destroy", "violence"
        ]
        sexual_keywords = [
            # Note: In production, use more sophisticated detection
        ]
        
        text_lower = text.lower()
        
        # Calculate scores based on keyword presence
        harassment_score = min(0.9, sum(0.2 for word in harassment_keywords if word in text_lower))
        hate_score = min(0.9, sum(0.3 for word in hate_keywords if word in text_lower))
        violence_score = min(0.9, sum(0.25 for word in violence_keywords if word in text_lower))
        sexual_score = min(0.9, sum(0.3 for word in sexual_keywords if word in text_lower))
        
        categories = {
            "harassment": harassment_score >= 0.7,
            "hate": hate_score >= 0.7,
            "self-harm": False,  # Hard to detect with keywords
            "sexual": sexual_score >= 0.7,
            "violence": violence_score >= 0.7
        }
        
        category_scores = {
            "harassment": harassment_score,
            "hate": hate_score,
            "self-harm": 0.1,
            "sexual": sexual_score,
            "violence": violence_score
        }
        
        flagged = any(categories.values())
        
        return {
            "flagged": flagged,
            "categories": categories,
            "category_scores": category_scores
        }
    
    async def batch_moderate(self, texts: List[str], model: str = "text-moderation-latest",
                           request_id: str = None) -> List[Dict[str, Any]]:
        """Moderate multiple texts in batch"""
        with tracer.start_as_current_span("batch_moderate") as span:
            span.set_attribute("batch_size", len(texts))
            span.set_attribute("request_id", request_id or "batch")
            
            results = []
            
            # Process each text individually (most providers don't support batch moderation)
            for i, text in enumerate(texts):
                request = ModerationAPIRequest(
                    input=text,
                    model=model
                )
                
                try:
                    response = await self.moderate_content(request, f"{request_id}_batch_{i}")
                    results.append(response.results[0])  # Get first result
                
                except Exception:
                    # Use conservative fallback for failed items
                    results.append(self._conservative_moderation(text))
            
            span.set_attribute("results_count", len(results))
            return results


# Dependency injection
moderation_service: Optional[ModerationService] = None

def get_moderation_service() -> ModerationService:
    """Get moderation service instance"""
    if moderation_service is None:
        raise HTTPException(status_code=503, detail="Moderation service not initialized")
    return moderation_service


@router.post("", response_model=ModerationAPIResponse)
async def create_moderation(
    request: ModerationAPIRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    service: ModerationService = Depends(get_moderation_service)
):
    """Moderate text content for safety"""
    request_id = http_request.headers.get("x-request-id", f"mod_{int(time.time())}")
    
    # Validate input length
    if len(request.input) > 32000:  # ~32K characters limit
        raise HTTPException(
            status_code=400,
            detail="Input too long. Maximum 32,000 characters."
        )
    
    return await service.moderate_content(request, request_id)


@router.post("/batch")
async def create_batch_moderation(
    inputs: List[str] = Field(..., description="List of texts to moderate"),
    model: str = Field(default="text-moderation-latest", description="Moderation model"),
    http_request: Request = None,
    service: ModerationService = Depends(get_moderation_service)
):
    """Moderate multiple texts in batch"""
    request_id = http_request.headers.get("x-request-id", f"batch_mod_{int(time.time())}")
    
    # Validate batch size
    if len(inputs) > 100:
        raise HTTPException(
            status_code=400,
            detail="Too many inputs. Maximum 100 texts per batch."
        )
    
    # Validate individual input lengths
    for i, text in enumerate(inputs):
        if len(text) > 32000:
            raise HTTPException(
                status_code=400,
                detail=f"Input {i} too long. Maximum 32,000 characters per text."
            )
    
    results = await service.batch_moderate(inputs, model, request_id)
    
    return {
        "id": f"batch-modr-{request_id}",
        "model": model,
        "results": results,
        "request_id": request_id
    }


@router.get("/categories")
async def get_moderation_categories():
    """Get list of moderation categories and their thresholds"""
    service = get_moderation_service()
    
    return {
        "categories": list(service.thresholds.keys()),
        "thresholds": service.thresholds,
        "description": {
            "harassment": "Content that expresses, incites, or promotes harassing language",
            "hate": "Content that expresses, incites, or promotes hate based on race, gender, etc.",
            "self-harm": "Content that promotes, encourages, or depicts acts of self-harm",
            "sexual": "Content meant to arouse sexual excitement or sexual activities",
            "violence": "Content that depicts death, violence, or physical injury"
        }
    }


@router.get("/health")
async def moderation_health():
    """Health check for moderation endpoints"""
    return {
        "status": "healthy",
        "service": "moderation",
        "timestamp": time.time()
    }
