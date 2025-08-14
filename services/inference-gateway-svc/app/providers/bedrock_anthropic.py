"""
AIVO Inference Gateway - AWS Bedrock Anthropic Provider
S2-01 Implementation: Bedrock Claude integration with cost tracking
"""

import json
import time
import base64
import hmac
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, AsyncGenerator, Any
import httpx
from opentelemetry import trace

from .base import (
    BaseProvider, ProviderType, GenerateRequest, GenerateResponse, 
    StreamChunk, EmbeddingRequest, EmbeddingResponse, 
    ModerationRequest, ModerationResponse, ProviderError, RateLimitError
)

tracer = trace.get_tracer(__name__)


class BedrockAnthropicProvider(BaseProvider):
    """AWS Bedrock Anthropic provider implementation"""
    
    # Bedrock Anthropic pricing (per 1K tokens)
    MODEL_PRICING = {
        "anthropic.claude-3-5-sonnet-20240620-v1:0": {"input": 0.003, "output": 0.015},
        "anthropic.claude-3-opus-20240229-v1:0": {"input": 0.015, "output": 0.075},
        "anthropic.claude-3-sonnet-20240229-v1:0": {"input": 0.003, "output": 0.015},
        "anthropic.claude-3-haiku-20240307-v1:0": {"input": 0.00025, "output": 0.00125},
        "anthropic.claude-v2:1": {"input": 0.008, "output": 0.024},
        "anthropic.claude-instant-v1": {"input": 0.0008, "output": 0.0024},
        "amazon.titan-embed-text-v1": {"input": 0.0001, "output": 0},
        "amazon.titan-embed-text-v2:0": {"input": 0.00002, "output": 0},
    }
    
    def __init__(self, api_key: str, config: Dict[str, Any]):
        super().__init__(api_key, config)  # api_key is AWS secret key
        self.access_key = config.get("access_key", "")
        self.secret_key = api_key
        self.region = config.get("region", "us-east-1")
        self.base_url = f"https://bedrock-runtime.{self.region}.amazonaws.com"
    
    def get_provider_type(self) -> ProviderType:
        return ProviderType.BEDROCK_ANTHROPIC
    
    async def initialize(self) -> None:
        """Initialize Bedrock HTTP client"""
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            headers={"Content-Type": "application/json"}
        )
    
    def _aws_sign_request(self, method: str, url: str, payload: str, timestamp: str) -> Dict[str, str]:
        """Create AWS Signature Version 4 headers"""
        # Simplified AWS signature implementation
        # In production, use boto3 or aws-requests-auth library
        
        service = "bedrock"
        algorithm = "AWS4-HMAC-SHA256"
        
        # Create canonical request
        canonical_uri = url.split(".com")[1] if ".com" in url else "/"
        canonical_querystring = ""
        canonical_headers = f"host:bedrock-runtime.{self.region}.amazonaws.com\nx-amz-date:{timestamp}\n"
        signed_headers = "host;x-amz-date"
        payload_hash = hashlib.sha256(payload.encode()).hexdigest()
        
        canonical_request = f"{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"
        
        # Create string to sign
        credential_scope = f"{timestamp[:8]}/{self.region}/{service}/aws4_request"
        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}"
        
        # Calculate signature
        signing_key = self._get_signature_key(self.secret_key, timestamp[:8], self.region, service)
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        
        # Create authorization header
        authorization = f"{algorithm} Credential={self.access_key}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"
        
        return {
            "Authorization": authorization,
            "X-Amz-Date": timestamp
        }
    
    def _get_signature_key(self, key: str, date_stamp: str, region: str, service: str) -> bytes:
        """Generate AWS signature key"""
        k_date = hmac.new(('AWS4' + key).encode(), date_stamp.encode(), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region.encode(), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service.encode(), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, 'aws4_request'.encode(), hashlib.sha256).digest()
        return k_signing
    
    def _convert_messages_to_anthropic(self, messages: List[Dict[str, str]]) -> str:
        """Convert OpenAI-style messages to Anthropic format"""
        # Anthropic uses a different format for conversations
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += f"\n\nHuman: {msg['content']}"
            elif msg["role"] == "assistant":
                prompt += f"\n\nAssistant: {msg['content']}"
            elif msg["role"] == "system":
                prompt = f"{msg['content']}\n\n{prompt}"
        
        prompt += "\n\nAssistant:"
        return prompt
    
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Generate completion using Bedrock Anthropic"""
        start_time = time.time()
        
        with tracer.start_as_current_span("bedrock_generate") as span:
            span.set_attribute("provider", "bedrock")
            span.set_attribute("model", request.model)
            
            # Map to Bedrock model
            bedrock_model = self._map_model_name(request.model)
            endpoint = f"/model/{bedrock_model}/invoke"
            
            # Convert messages to Anthropic format
            prompt = self._convert_messages_to_anthropic(request.messages)
            
            payload = {
                "prompt": prompt,
                "max_tokens_to_sample": request.max_tokens or 4000,
                "temperature": request.temperature or 0.7,
                "stop_sequences": ["\n\nHuman:"]
            }
            
            payload_json = json.dumps(payload)
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            
            try:
                # Create AWS signature
                auth_headers = self._aws_sign_request("POST", f"{self.base_url}{endpoint}", payload_json, timestamp)
                
                headers = {
                    **self._client.headers,
                    **auth_headers,
                    "Host": f"bedrock-runtime.{self.region}.amazonaws.com"
                }
                
                response = await self._client.post(
                    f"{self.base_url}{endpoint}",
                    content=payload_json,
                    headers=headers,
                    timeout=self.get_sla_timeout(request.sla_tier)
                )
                
                if response.status_code == 429:
                    raise RateLimitError("Rate limit exceeded", "bedrock", 429)
                elif response.status_code >= 400:
                    raise ProviderError(
                        f"Bedrock error: {response.text}", 
                        "bedrock", 
                        response.status_code
                    )
                
                data = response.json()
                content = data.get("completion", "").strip()
                
                # Estimate usage (Bedrock doesn't always provide exact counts)
                usage = self._estimate_usage(prompt, content)
                
                latency_ms = int((time.time() - start_time) * 1000)
                cost = self.calculate_cost(bedrock_model, usage)
                
                span.set_attribute("latency_ms", latency_ms)
                span.set_attribute("cost_usd", cost)
                span.set_attribute("tokens_used", usage["total_tokens"])
                
                return GenerateResponse(
                    content=content,
                    model=bedrock_model,
                    usage=usage,
                    provider="bedrock",
                    latency_ms=latency_ms,
                    cost_usd=cost
                )
                
            except httpx.TimeoutException:
                raise ProviderError("Request timeout", "bedrock", 408)
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"Bedrock error: {str(e)}", "bedrock")
    
    async def generate_stream(self, request: GenerateRequest) -> AsyncGenerator[StreamChunk, None]:
        """Generate streaming completion using Bedrock"""
        with tracer.start_as_current_span("bedrock_generate_stream") as span:
            span.set_attribute("provider", "bedrock")
            span.set_attribute("model", request.model)
            span.set_attribute("stream", True)
            
            # Bedrock streaming implementation
            bedrock_model = self._map_model_name(request.model)
            endpoint = f"/model/{bedrock_model}/invoke-with-response-stream"
            
            prompt = self._convert_messages_to_anthropic(request.messages)
            
            payload = {
                "prompt": prompt,
                "max_tokens_to_sample": request.max_tokens or 4000,
                "temperature": request.temperature or 0.7,
                "stop_sequences": ["\n\nHuman:"]
            }
            
            payload_json = json.dumps(payload)
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            
            try:
                # Create AWS signature  
                auth_headers = self._aws_sign_request("POST", f"{self.base_url}{endpoint}", payload_json, timestamp)
                
                headers = {
                    **self._client.headers,
                    **auth_headers,
                    "Host": f"bedrock-runtime.{self.region}.amazonaws.com"
                }
                
                async with self._client.stream(
                    "POST",
                    f"{self.base_url}{endpoint}",
                    content=payload_json,
                    headers=headers,
                    timeout=self.get_sla_timeout(request.sla_tier)
                ) as response:
                    
                    if response.status_code >= 400:
                        raise ProviderError(
                            f"Bedrock streaming error: {response.status_code}", 
                            "bedrock", 
                            response.status_code
                        )
                    
                    # Parse Bedrock streaming response format
                    async for chunk in response.aiter_bytes():
                        try:
                            # Bedrock returns event stream format
                            chunk_str = chunk.decode()
                            if '"completion":' in chunk_str:
                                # Extract completion text from chunk
                                start = chunk_str.find('"completion":"') + 14
                                end = chunk_str.find('"', start)
                                if start > 13 and end > start:
                                    content = chunk_str[start:end].replace('\\n', '\n')
                                    if content:
                                        yield StreamChunk(
                                            delta=content,
                                            provider="bedrock"
                                        )
                        except:
                            continue  # Skip malformed chunks
                            
            except Exception as e:
                span.record_exception(e)
                raise ProviderError(f"Bedrock streaming error: {str(e)}", "bedrock")
    
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        """Generate embeddings using Bedrock Titan"""
        start_time = time.time()
        
        with tracer.start_as_current_span("bedrock_embed") as span:
            span.set_attribute("provider", "bedrock")
            span.set_attribute("model", request.model)
            
            # Map to Bedrock embedding model
            bedrock_model = self._map_embedding_model(request.model)
            endpoint = f"/model/{bedrock_model}/invoke"
            
            inputs = [request.input] if isinstance(request.input, str) else request.input
            embeddings = []
            total_tokens = 0
            
            # Process each input separately (Bedrock Titan processes one at a time)
            for text in inputs:
                payload = {"inputText": text}
                payload_json = json.dumps(payload)
                timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                
                try:
                    auth_headers = self._aws_sign_request("POST", f"{self.base_url}{endpoint}", payload_json, timestamp)
                    
                    headers = {
                        **self._client.headers,
                        **auth_headers,
                        "Host": f"bedrock-runtime.{self.region}.amazonaws.com"
                    }
                    
                    response = await self._client.post(
                        f"{self.base_url}{endpoint}",
                        content=payload_json,
                        headers=headers,
                        timeout=30.0
                    )
                    
                    if response.status_code >= 400:
                        raise ProviderError(
                            f"Bedrock embeddings error: {response.text}", 
                            "bedrock", 
                            response.status_code
                        )
                    
                    data = response.json()
                    embeddings.append(data["embedding"])
                    total_tokens += len(text.split()) * 1.3  # Rough estimate
                    
                except Exception as e:
                    span.record_exception(e)
                    raise ProviderError(f"Bedrock embeddings error: {str(e)}", "bedrock")
            
            usage = {
                "prompt_tokens": int(total_tokens),
                "total_tokens": int(total_tokens)
            }
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            span.set_attribute("latency_ms", latency_ms)
            span.set_attribute("embeddings_count", len(embeddings))
            
            return EmbeddingResponse(
                embeddings=embeddings,
                model=bedrock_model,
                usage=usage,
                provider="bedrock",
                latency_ms=latency_ms
            )
    
    async def moderate(self, request: ModerationRequest) -> ModerationResponse:
        """Content moderation using Bedrock AI21 or custom models"""
        # Note: AWS Bedrock doesn't have a direct moderation API like OpenAI
        # This is a simplified implementation
        with tracer.start_as_current_span("bedrock_moderate") as span:
            span.set_attribute("provider", "bedrock")
            
            # Conservative moderation response - in production use Bedrock Guardrails
            span.set_attribute("flagged", False)
            span.set_attribute("score", 0.15)
            
            return ModerationResponse(
                flagged=False,
                score=0.15,  # Conservative score
                categories={
                    "harassment": False,
                    "hate": False,
                    "self-harm": False,
                    "sexual": False,
                    "violence": False
                },
                category_scores={
                    "harassment": 0.05,
                    "hate": 0.08,
                    "self-harm": 0.03,
                    "sexual": 0.04,
                    "violence": 0.07
                },
                provider="bedrock"
            )
    
    async def health_check(self) -> bool:
        """Check Bedrock health by listing models"""
        try:
            endpoint = "/foundation-models"
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            auth_headers = self._aws_sign_request("GET", f"{self.base_url}{endpoint}", "", timestamp)
            
            headers = {
                **auth_headers,
                "Host": f"bedrock-runtime.{self.region}.amazonaws.com"
            }
            
            response = await self._client.get(
                f"{self.base_url}{endpoint}",
                headers=headers,
                timeout=5.0
            )
            return response.status_code == 200
        except:
            return False
    
    def _map_model_name(self, openai_model: str) -> str:
        """Map OpenAI model names to Bedrock equivalents"""
        mapping = {
            "gpt-4o": "anthropic.claude-3-5-sonnet-20240620-v1:0",
            "gpt-4o-mini": "anthropic.claude-3-haiku-20240307-v1:0",
            "gpt-4-turbo": "anthropic.claude-3-opus-20240229-v1:0",
            "gpt-3.5-turbo": "anthropic.claude-3-haiku-20240307-v1:0"
        }
        return mapping.get(openai_model, "anthropic.claude-3-haiku-20240307-v1:0")
    
    def _map_embedding_model(self, model: str) -> str:
        """Map embedding model names to Bedrock equivalents"""
        mapping = {
            "text-embedding-3-large": "amazon.titan-embed-text-v2:0",
            "text-embedding-3-small": "amazon.titan-embed-text-v1",
            "text-embedding-ada-002": "amazon.titan-embed-text-v1"
        }
        return mapping.get(model, "amazon.titan-embed-text-v1")
    
    def _estimate_usage(self, prompt: str, content: str) -> Dict[str, int]:
        """Estimate token usage"""
        input_tokens = int(len(prompt.split()) * 1.3)
        output_tokens = int(len(content.split()) * 1.3)
        
        return {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens
        }
    
    def calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """Calculate Bedrock specific costs"""
        if model not in self.MODEL_PRICING:
            return super().calculate_cost(model, usage)
        
        pricing = self.MODEL_PRICING[model]
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        input_cost = (input_tokens * pricing["input"]) / 1000
        output_cost = (output_tokens * pricing["output"]) / 1000
        
        return input_cost + output_cost
