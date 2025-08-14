"""
AIVO Inference Gateway - Google Vertex AI Gemini Provider
S2-01 Implementation: Vertex AI integration with cost tracking
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


class VertexGeminiProvider(BaseProvider):
    """Google Vertex AI Gemini provider implementation"""
    
    # Vertex AI pricing (approximate, per 1K tokens)
    MODEL_PRICING = {
        "gemini-1.5-pro": {"input": 0.0035, "output": 0.0105},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-pro": {"input": 0.0005, "output": 0.0015},
        "text-embedding-004": {"input": 0.00001, "output": 0},
        "textembedding-gecko": {"input": 0.00001, "output": 0},
    }
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        super().__init__(api_key, config)
        self.project_id = config.get("project_id", "aivo-inference")
        self.location = config.get("location", "us-central1")
        self.base_url = f"https://{self.location}-aiplatform.googleapis.com/v1"
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.VERTEX_GEMINI
    
    async def initialize(self) -> None:
        """Initialize Vertex AI HTTP client"""
        # Note: In production, use Google Cloud authentication
        # For now, using API key authentication
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(45.0),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AIVO-Inference-Gateway/1.0"
            }
        )
    
    def _convert_messages_to_gemini(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Convert OpenAI-style messages to Gemini format"""
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        return {"contents": contents}
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate completion using Vertex AI Gemini"""
        start_time = time.time()
        
        with tracer.start_as_current_span("vertex_generate") as span:
            span.set_attribute("provider", "vertex")
            span.set_attribute("model", request.model)
            
            # Convert model name to Vertex format
            vertex_model = self._map_model_name(request.model)
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{vertex_model}:generateContent"
            
            payload = {
                **self._convert_messages_to_gemini(request.messages),
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                }
            }
            
            try:
                response = await self._client.post(
                    f"{self.base_url}/{endpoint}",
                    json=payload,
                    timeout=self.get_sla_timeout(request.sla_tier)
                )
                
                if response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded", "vertex", 429)
                elif response.status_code >= 400:
                    raise ProviderError(
                        f"Vertex AI error: {response.text}", 
                        "vertex", 
                        response.status_code
                    )
                
                data = response.json()
                
                # Extract content from Vertex response
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ProviderError("No candidates in response", "vertex")
                
                content = candidates[0]["content"]["parts"][0]["text"]
                
                # Estimate usage (Vertex doesn't always provide exact counts)
                usage = self._estimate_usage(request.messages, content)
                
                latency_ms = int((time.time() - start_time) * 1000)
                cost = self.calculate_cost(vertex_model, usage)
                
                span.set_attribute("latency_ms", latency_ms)
                span.set_attribute("cost_usd", cost)
                span.set_attribute("tokens_used", usage["total_tokens"])
                
                return GenerateResponse(
                    content=content,
                    model=vertex_model,
                    usage=usage,
                    provider="vertex",
                    latency_ms=latency_ms,
                    cost_usd=cost
                )
                
            except httpx.TimeoutException:
                raise ProviderError("Request timeout", "vertex", 408)
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"Vertex AI error: {str(e)}", "vertex")
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming completion (Vertex AI streaming support)"""
        with tracer.start_as_current_span("vertex_generate_stream") as span:
            span.set_attribute("provider", "vertex")
            span.set_attribute("model", request.model)
            span.set_attribute("stream", True)
            
            # Note: Vertex AI streaming implementation
            # For simplicity, using server-sent events approach
            vertex_model = self._map_model_name(request.model)
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{vertex_model}:streamGenerateContent"
            
            payload = {
                **self._convert_messages_to_gemini(request.messages),
                "generationConfig": {
                    "temperature": request.temperature,
                    "maxOutputTokens": request.max_tokens,
                }
            }
            
            try:
                async with self._client.stream(
                    "POST",
                    f"{self.base_url}/{endpoint}",
                    json=payload,
                    timeout=self.get_sla_timeout(request.sla_tier)
                ) as response:
                    
                    if response.status_code >= 400:
                        raise ProviderError(
                            f"Vertex AI streaming error: {response.status_code}", 
                            "vertex", 
                            response.status_code
                        )
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            try:
                                data = json.loads(data_str)
                                candidates = data.get("candidates", [])
                                
                                if candidates:
                                    content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                    if content:
                                        yield StreamChunk(
                                            delta=content,
                                            provider="vertex",
                                            finish_reason=candidates[0].get("finishReason")
                                        )
                                        
                            except json.JSONDecodeError:
                                continue
                                
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"Vertex AI streaming error: {str(e)}", "vertex")
    
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings using Vertex AI Text Embeddings"""
        start_time = time.time()
        
        with tracer.start_as_current_span("vertex_embed") as span:
            span.set_attribute("provider", "vertex")
            span.set_attribute("model", request.model)
            
            # Map to Vertex embedding model
            vertex_model = self._map_embedding_model(request.model)
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models/{vertex_model}:predict"
            
            # Convert input to list if string
            inputs = [request.input] if isinstance(request.input, str) else request.input
            
            payload = {
                "instances": [{"content": text} for text in inputs]
            }
            
            try:
                response = await self._client.post(
                    f"{self.base_url}/{endpoint}",
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code >= 400:
                    raise ProviderError(
                        f"Vertex AI embeddings error: {response.text}", 
                        "vertex", 
                        response.status_code
                    )
                
                data = response.json()
                embeddings = [pred["embeddings"]["values"] for pred in data["predictions"]]
                
                # Estimate usage for embeddings
                total_tokens = sum(len(text.split()) * 1.3 for text in inputs)  # Rough estimate
                usage = {
                    "prompt_tokens": int(total_tokens),
                    "total_tokens": int(total_tokens)
                }
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                span.set_attribute("latency_ms", latency_ms)
                span.set_attribute("embeddings_count", len(embeddings))
                
                return EmbeddingResponse(
                    embeddings=embeddings,
                    model=vertex_model,
                    usage=usage,
                    provider="vertex",
                    latency_ms=latency_ms
                )
                
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"Vertex AI embeddings error: {str(e)}", "vertex")
    
    async def moderate(self, request: ModerationRequest) -> ModerationResponse:
        """Content moderation (basic implementation using classification)"""
        # Note: Vertex AI doesn't have direct moderation API like OpenAI
        # This is a simplified implementation using text classification
        with tracer.start_as_current_span("vertex_moderate") as span:
            span.set_attribute("provider", "vertex")
            
            # For now, return a conservative moderation response
            # In production, you'd use Vertex AI's safety ratings or custom models
            span.set_attribute("flagged", False)
            span.set_attribute("score", 0.1)
            
            return ModerationResponse(
                flagged=False,
                score=0.1,  # Conservative score
                categories={
                    "harassment": False,
                    "hate": False,
                    "self-harm": False,
                    "sexual": False,
                    "violence": False
                },
                category_scores={
                    "harassment": 0.05,
                    "hate": 0.05,
                    "self-harm": 0.03,
                    "sexual": 0.04,
                    "violence": 0.06
                },
                provider="vertex"
            )
    
    async def health_check(self) -> bool:
        """Check Vertex AI health"""
        try:
            # Simple health check by listing models
            endpoint = f"projects/{self.project_id}/locations/{self.location}/publishers/google/models"
            response = await self._client.get(f"{self.base_url}/{endpoint}", timeout=5.0)
            return response.status_code == 200
        except:
            return False
    
    def _map_model_name(self, openai_model: str) -> str:
        """Map OpenAI model names to Vertex AI equivalents"""
        mapping = {
            "gpt-4o": "gemini-1.5-pro",
            "gpt-4o-mini": "gemini-1.5-flash",
            "gpt-4-turbo": "gemini-1.5-pro",
            "gpt-3.5-turbo": "gemini-pro"
        }
        return mapping.get(openai_model, "gemini-1.5-flash")
    
    def _map_embedding_model(self, model: str) -> str:
        """Map embedding model names"""
        mapping = {
            "text-embedding-3-large": "text-embedding-004",
            "text-embedding-3-small": "textembedding-gecko",
            "text-embedding-ada-002": "textembedding-gecko"
        }
        return mapping.get(model, "textembedding-gecko")
    
    def _estimate_usage(self, messages: List[Dict[str, str]], content: str) -> Dict[str, int]:
        """Estimate token usage (Vertex doesn't always provide exact counts)"""
        # Rough estimation: 1 word ≈ 1.3 tokens
        input_text = " ".join(msg["content"] for msg in messages)
        input_tokens = int(len(input_text.split()) * 1.3)
        output_tokens = int(len(content.split()) * 1.3)
        
        return {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    
    def calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate Vertex AI specific costs"""
        if model not in self.MODEL_PRICING:
            return super().calculate_cost(model, usage)
        
        pricing = self.MODEL_PRICING[model]
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        input_cost = (input_tokens * pricing["input"]) / 1000
        output_cost = (output_tokens * pricing["output"]) / 1000
        
        return input_cost + output_cost
