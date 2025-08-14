"""
AIVO Inference Gateway - OpenAI Provider
S2-01 Implementation: OpenAI GPT integration with cost tracking
"""

import json
import time
from typing import Dict, List, Optional, AsyncGenerator, Any
import httpx
from opentelemetry import trace

from .base import (
    BaseProvider, ProviderType, GenerateRequest, GenerateResponse, 
    StreamChunk, EmbeddingRequest, EmbeddingResponse, 
    ModerationRequest, ModerationResponse, ProviderError, RateLimitError
)

tracer = trace.get_tracer(__name__)


class OpenAIProvider(BaseProvider):
    """OpenAI provider implementation"""
    
    BASE_URL = "https://api.openai.com/v1"
    
    # OpenAI pricing (per 1K tokens as of 2025)
    MODEL_PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
        "text-embedding-3-large": {"input": 0.00013, "output": 0},
        "text-embedding-3-small": {"input": 0.00002, "output": 0},
        "text-embedding-ada-002": {"input": 0.0001, "output": 0},
    }
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    async def initialize(self) -> None:
        """Initialize OpenAI HTTP client"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AIVO-Inference-Gateway/1.0"
            }
        )
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate completion using OpenAI ChatCompletion API"""
        start_time = time.time()
        
        with tracer.start_as_current_span("openai_generate") as span:
            span.set_attribute("provider", "openai")
            span.set_attribute("model", request.model)
            span.set_attribute("stream", request.stream)
            
            payload = {
                "model": request.model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": False
            }
            
            try:
                response = await self._client.post(
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    timeout=self.get_sla_timeout(request.sla_tier)
                )
                
                if response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded", "openai", 429)
                elif response.status_code >= 400:
                    raise ProviderError(
                        f"OpenAI API error: {response.text}", 
                        "openai", 
                        response.status_code
                    )
                
                data = response.json()
                choice = data["choices"][0]
                usage = data["usage"]
                
                latency_ms = int((time.time() - start_time) * 1000)
                cost = self.calculate_cost(request.model, usage)
                
                span.set_attribute("latency_ms", latency_ms)
                span.set_attribute("cost_usd", cost)
                span.set_attribute("tokens_used", usage["total_tokens"])
                
                return GenerateResponse(
                    content=choice["message"]["content"],
                    model=request.model,
                    usage=usage,
                    provider="openai",
                    latency_ms=latency_ms,
                    cost_usd=cost
                )
                
            except httpx.TimeoutException:
                raise ProviderError("Request timeout", "openai", 408)
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"OpenAI error: {str(e)}", "openai")
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming completion"""
        with tracer.start_as_current_span("openai_generate_stream") as span:
            span.set_attribute("provider", "openai")
            span.set_attribute("model", request.model)
            span.set_attribute("stream", True)
            
            payload = {
                "model": request.model,
                "messages": request.messages,
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": True
            }
            
            try:
                async with self._client.stream(
                    "POST",
                    f"{self.BASE_URL}/chat/completions",
                    json=payload,
                    timeout=self.get_sla_timeout(request.sla_tier)
                ) as response:
                    
                    if response.status_code == 429:
                        raise RateLimitError("Rate limit exceeded", "openai", 429)
                    elif response.status_code >= 400:
                        raise ProviderError(
                            f"OpenAI API error: {response.status_code}", 
                            "openai", 
                            response.status_code
                        )
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            
                            if data_str.strip() == "[DONE]":
                                break
                            
                            try:
                                data = json.loads(data_str)
                                choice = data["choices"][0]
                                
                                if "delta" in choice and "content" in choice["delta"]:
                                    content = choice["delta"]["content"]
                                    if content:  # Skip empty content
                                        yield StreamChunk(
                                            delta=content,
                                            provider="openai",
                                            finish_reason=choice.get("finish_reason")
                                        )
                                        
                            except json.JSONDecodeError:
                                continue  # Skip malformed chunks
                                
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"OpenAI streaming error: {str(e)}", "openai")
    
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings using OpenAI Embeddings API"""
        start_time = time.time()
        
        with tracer.start_as_current_span("openai_embed") as span:
            span.set_attribute("provider", "openai")
            span.set_attribute("model", request.model)
            
            payload = {
                "model": request.model,
                "input": request.input
            }
            
            if request.dimensions:
                payload["dimensions"] = request.dimensions
            
            try:
                response = await self._client.post(
                    f"{self.BASE_URL}/embeddings",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code >= 400:
                    raise ProviderError(
                        f"OpenAI embeddings error: {response.text}", 
                        "openai", 
                        response.status_code
                    )
                
                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]
                usage = data["usage"]
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                span.set_attribute("latency_ms", latency_ms)
                span.set_attribute("embeddings_count", len(embeddings))
                
                return EmbeddingResponse(
                    embeddings=embeddings,
                    model=request.model,
                    usage=usage,
                    provider="openai",
                    latency_ms=latency_ms
                )
                
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"OpenAI embeddings error: {str(e)}", "openai")
    
    async def moderate(self, request: ModerationRequest) -> ModerationResponse:
        """Content moderation using OpenAI Moderation API"""
        with tracer.start_as_current_span("openai_moderate") as span:
            span.set_attribute("provider", "openai")
            span.set_attribute("model", request.model)
            
            payload = {
                "input": request.input,
                "model": request.model
            }
            
            try:
                response = await self._client.post(
                    f"{self.BASE_URL}/moderations",
                    json=payload,
                    timeout=10.0
                )
                
                if response.status_code >= 400:
                    raise ProviderError(
                        f"OpenAI moderation error: {response.text}", 
                        "openai", 
                        response.status_code
                    )
                
                data = response.json()
                result = data["results"][0]
                
                # Calculate overall score (max of category scores)
                scores = result["category_scores"]
                overall_score = max(scores.values()) if scores else 0.0
                
                span.set_attribute("flagged", result["flagged"])
                span.set_attribute("score", overall_score)
                
                return ModerationResponse(
                    flagged=result["flagged"],
                    score=overall_score,
                    categories=result["categories"],
                    category_scores=scores,
                    provider="openai"
                )
                
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"OpenAI moderation error: {str(e)}", "openai")
    
    async def health_check(self) -> bool:
        """Check OpenAI API health"""
        try:
            response = await self._client.get(
                f"{self.BASE_URL}/models",
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False
    
    def calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate OpenAI specific costs"""
        if model not in self.MODEL_PRICING:
            return super().calculate_cost(model, usage)
        
        pricing = self.MODEL_PRICING[model]
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        input_cost = (input_tokens * pricing["input"]) / 1000
        output_cost = (output_tokens * pricing["output"]) / 1000
        
        return input_cost + output_cost
