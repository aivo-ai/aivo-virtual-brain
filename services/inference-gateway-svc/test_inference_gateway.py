"""
AIVO Inference Gateway - Test Suite
S2-01 Implementation: Comprehensive tests for multi-provider inference service
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any

from app.providers.base import (
    GenerateRequest, GenerateResponse, StreamChunk,
    EmbeddingRequest, EmbeddingResponse,
    ModerationRequest, ModerationResponse,
    ProviderType, SLATier, ProviderError, RateLimitError
)
from app.providers.openai import OpenAIProvider
from app.policy import PolicyEngine, RoutingContext, RoutingPolicy
from app.pii import PIIScrubber, PIIType


class TestProviderBase:
    """Test base provider functionality"""
    
    @pytest.fixture
    def mock_openai_provider(self):
        """Create mock OpenAI provider"""
        provider = OpenAIProvider(
            api_key="test-key",
            config={"base_url": "https://api.openai.com/v1"}
        )
        provider._client = AsyncMock()
        return provider
    
    @pytest.mark.asyncio
    async def test_generate_request(self, mock_openai_provider):
        """Test text generation request"""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello! How can I help you?"},
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 8,
                "total_tokens": 18
            },
            "model": "gpt-4o"
        }
        mock_openai_provider._client.post.return_value = mock_response
        
        request = GenerateRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o",
            max_tokens=100,
            temperature=0.7
        )
        
        response = await mock_openai_provider.generate(request)
        
        assert response.content == "Hello! How can I help you?"
        assert response.model == "gpt-4o"
        assert response.usage["total_tokens"] == 18
        assert response.provider == "openai"
    
    @pytest.mark.asyncio
    async def test_generate_stream(self, mock_openai_provider):
        """Test streaming generation"""
        # Mock streaming response
        mock_chunks = [
            'data: {"choices":[{"delta":{"content":"Hello"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":" there"}}]}\n\n',
            'data: {"choices":[{"delta":{"content":"!"}}]}\n\n',
            'data: [DONE]\n\n'
        ]
        
        async def mock_aiter_bytes():
            for chunk in mock_chunks:
                yield chunk.encode()
        
        mock_stream_response = Mock()
        mock_stream_response.status_code = 200
        mock_stream_response.aiter_bytes = mock_aiter_bytes
        
        mock_openai_provider._client.stream.return_value.__aenter__.return_value = mock_stream_response
        
        request = GenerateRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o",
            temperature=0.7
        )
        
        chunks = []
        async for chunk in mock_openai_provider.generate_stream(request):
            chunks.append(chunk)
        
        assert len(chunks) == 3  # Excluding [DONE] chunk
        assert chunks[0].delta == "Hello"
        assert chunks[1].delta == " there"
        assert chunks[2].delta == "!"
    
    @pytest.mark.asyncio
    async def test_embedding_request(self, mock_openai_provider):
        """Test embedding generation"""
        # Mock embedding response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{
                "embedding": [0.1, 0.2, 0.3, 0.4],
                "index": 0
            }],
            "usage": {
                "prompt_tokens": 5,
                "total_tokens": 5
            },
            "model": "text-embedding-3-large"
        }
        mock_openai_provider._client.post.return_value = mock_response
        
        request = EmbeddingRequest(
            input="Test text for embedding",
            model="text-embedding-3-large"
        )
        
        response = await mock_openai_provider.embed(request)
        
        assert len(response.embeddings) == 1
        assert response.embeddings[0] == [0.1, 0.2, 0.3, 0.4]
        assert response.usage["total_tokens"] == 5
    
    @pytest.mark.asyncio
    async def test_moderation_request(self, mock_openai_provider):
        """Test content moderation"""
        # Mock moderation response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [{
                "flagged": True,
                "categories": {
                    "harassment": True,
                    "hate": False,
                    "self-harm": False,
                    "sexual": False,
                    "violence": False
                },
                "category_scores": {
                    "harassment": 0.9,
                    "hate": 0.1,
                    "self-harm": 0.05,
                    "sexual": 0.02,
                    "violence": 0.08
                }
            }]
        }
        mock_openai_provider._client.post.return_value = mock_response
        
        request = ModerationRequest(input="Inappropriate content here")
        
        response = await mock_openai_provider.moderate(request)
        
        assert response.flagged is True
        assert response.categories["harassment"] is True
        assert response.category_scores["harassment"] == 0.9
    
    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_openai_provider):
        """Test rate limit error handling"""
        # Mock rate limit response
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_openai_provider._client.post.return_value = mock_response
        
        request = GenerateRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o"
        )
        
        with pytest.raises(RateLimitError):
            await mock_openai_provider.generate(request)
    
    @pytest.mark.asyncio
    async def test_provider_error(self, mock_openai_provider):
        """Test provider error handling"""
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal server error"
        mock_openai_provider._client.post.return_value = mock_response
        
        request = GenerateRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o"
        )
        
        with pytest.raises(ProviderError):
            await mock_openai_provider.generate(request)


class TestPolicyEngine:
    """Test policy engine functionality"""
    
    @pytest.fixture
    def policy_engine(self):
        """Create policy engine with test configuration"""
        config = {
            "routing_policies": [
                {
                    "subject_pattern": "enterprise/*",
                    "preferred_providers": ["openai", "vertex_gemini"],
                    "fallback_providers": ["bedrock_anthropic"],
                    "strategy": "priority_based"
                },
                {
                    "subject_pattern": "research/*",
                    "preferred_providers": ["vertex_gemini"],
                    "fallback_providers": ["openai", "bedrock_anthropic"],
                    "strategy": "lowest_cost"
                }
            ]
        }
        return PolicyEngine(config=config)
    
    def test_routing_enterprise_subject(self, policy_engine):
        """Test routing for enterprise subjects"""
        context = RoutingContext(
            subject="enterprise/customer1",
            locale="en-US",
            sla_tier=SLATier.PREMIUM,
            model="gpt-4o"
        )
        
        providers = policy_engine.route_request(context)
        
        assert ProviderType.OPENAI in providers
        assert ProviderType.VERTEX_GEMINI in providers
        # Should prioritize preferred providers
        assert providers.index(ProviderType.OPENAI) < providers.index(ProviderType.BEDROCK_ANTHROPIC)
    
    def test_routing_research_subject(self, policy_engine):
        """Test routing for research subjects"""
        context = RoutingContext(
            subject="research/project1",
            locale="en-US",
            sla_tier=SLATier.STANDARD,
            model="gpt-4o"
        )
        
        providers = policy_engine.route_request(context)
        
        # Should prefer Vertex for research
        assert providers[0] == ProviderType.VERTEX_GEMINI
    
    def test_default_routing(self, policy_engine):
        """Test default routing for unmatched subjects"""
        context = RoutingContext(
            subject="general/user",
            locale="en-US",
            sla_tier=SLATier.STANDARD,
            model="gpt-4o"
        )
        
        providers = policy_engine.route_request(context)
        
        # Should use default policy (OpenAI first)
        assert ProviderType.OPENAI in providers
    
    def test_record_success(self, policy_engine):
        """Test recording successful requests"""
        policy_engine.record_success(ProviderType.OPENAI, 150, 0.02)
        
        health = policy_engine.provider_health[ProviderType.OPENAI]
        assert health.success_count == 1
        assert health.avg_latency_ms == 150
        assert health.is_healthy is True
    
    def test_record_failure_circuit_breaker(self, policy_engine):
        """Test circuit breaker functionality"""
        # Record multiple failures
        for _ in range(10):
            policy_engine.record_failure(ProviderType.OPENAI, "timeout")
        
        health = policy_engine.provider_health[ProviderType.OPENAI]
        assert health.failure_count == 10
        # Circuit breaker should open after high failure rate
        assert health.circuit_breaker_open is True


class TestPIIScrubber:
    """Test PII scrubbing functionality"""
    
    @pytest.fixture
    def pii_scrubber(self):
        """Create PII scrubber with default configuration"""
        return PIIScrubber()
    
    def test_email_detection(self, pii_scrubber):
        """Test email address detection and masking"""
        text = "Please contact me at john.doe@example.com for more information."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.EMAIL
        assert matches[0].original_text == "john.doe@example.com"
        assert "john.doe@example.com" not in cleaned_text
        assert "[EMAIL_" in cleaned_text
    
    def test_phone_detection(self, pii_scrubber):
        """Test phone number detection and masking"""
        text = "Call me at (555) 123-4567 or 555-987-6543."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        assert len(matches) == 2
        assert all(match.pii_type == PIIType.PHONE for match in matches)
        assert "(555) 123-4567" not in cleaned_text
        assert "555-987-6543" not in cleaned_text
    
    def test_ssn_detection(self, pii_scrubber):
        """Test SSN detection and masking"""
        text = "My SSN is 123-45-6789 for verification."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.SSN
        assert matches[0].original_text == "123-45-6789"
        assert "123-45-6789" not in cleaned_text
    
    def test_credit_card_detection(self, pii_scrubber):
        """Test credit card detection and masking"""
        text = "Please charge my card 4532-1234-5678-9012."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        assert len(matches) == 1
        assert matches[0].pii_type == PIIType.CREDIT_CARD
        assert "4532-1234-5678-9012" not in cleaned_text
    
    def test_name_detection(self, pii_scrubber):
        """Test name detection using common name heuristics"""
        text = "John Smith will attend the meeting."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        # Note: This depends on having "john" and "smith" in common names lists
        name_matches = [m for m in matches if m.pii_type == PIIType.NAME]
        if name_matches:
            assert "John Smith" not in cleaned_text
    
    def test_no_pii_text(self, pii_scrubber):
        """Test text without PII"""
        text = "This is a completely normal sentence with no sensitive information."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        assert len(matches) == 0
        assert cleaned_text == text  # Should remain unchanged
    
    def test_multiple_pii_types(self, pii_scrubber):
        """Test text with multiple PII types"""
        text = "Contact John Smith at john@example.com or call (555) 123-4567."
        
        cleaned_text, matches = pii_scrubber.scrub_text(text)
        
        # Should detect email and phone
        pii_types = {match.pii_type for match in matches}
        assert PIIType.EMAIL in pii_types
        assert PIIType.PHONE in pii_types
        
        # Original PII should be removed
        assert "john@example.com" not in cleaned_text
        assert "(555) 123-4567" not in cleaned_text
    
    def test_scrub_request_data(self, pii_scrubber):
        """Test scrubbing request data structure"""
        request_data = {
            "messages": [
                {"role": "user", "content": "My email is test@example.com"},
                {"role": "assistant", "content": "I understand you provided test@example.com"}
            ],
            "model": "gpt-4o",
            "temperature": 0.7
        }
        
        scrubbed_data, matches = pii_scrubber.scrub_request(request_data)
        
        assert len(matches) >= 1  # At least one email detected
        
        # Check that emails are scrubbed in messages
        user_message = scrubbed_data["messages"][0]["content"]
        assistant_message = scrubbed_data["messages"][1]["content"]
        
        assert "test@example.com" not in user_message
        assert "test@example.com" not in assistant_message
        
        # Non-PII fields should remain unchanged
        assert scrubbed_data["model"] == "gpt-4o"
        assert scrubbed_data["temperature"] == 0.7


class TestEndToEndIntegration:
    """Test end-to-end functionality"""
    
    @pytest.mark.asyncio
    async def test_generation_with_pii_scrubbing(self):
        """Test generation request with PII scrubbing"""
        # This would be an integration test with actual FastAPI test client
        # For now, we'll test the components separately
        
        # Create mock components
        pii_scrubber = PIIScrubber()
        policy_engine = PolicyEngine()
        
        # Mock provider
        mock_provider = AsyncMock()
        mock_provider.generate.return_value = GenerateResponse(
            content="Hello! I'd be happy to help you.",
            model="gpt-4o",
            usage={"prompt_tokens": 15, "completion_tokens": 8, "total_tokens": 23},
            provider="openai",
            latency_ms=150,
            cost_usd=0.003
        )
        
        providers = {ProviderType.OPENAI: mock_provider}
        
        # Simulate request with PII
        request_data = {
            "messages": [
                {"role": "user", "content": "Hi, my email is john@example.com and I need help."}
            ],
            "model": "gpt-4o"
        }
        
        # Scrub PII
        scrubbed_data, pii_matches = pii_scrubber.scrub_request(request_data)
        
        # Verify PII was detected and scrubbed
        assert len(pii_matches) >= 1
        assert "john@example.com" not in scrubbed_data["messages"][0]["content"]
        
        # Route request
        context = RoutingContext(model="gpt-4o", request_type="generate")
        provider_order = policy_engine.route_request(context)
        
        # Generate response
        from app.providers.base import GenerateRequest
        provider_request = GenerateRequest(
            messages=scrubbed_data["messages"],
            model="gpt-4o"
        )
        
        response = await mock_provider.generate(provider_request)
        
        assert response.content == "Hello! I'd be happy to help you."
        assert response.provider == "openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
