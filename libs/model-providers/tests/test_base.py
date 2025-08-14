"""
Test base provider functionality and common types.
"""

import pytest
from unittest.mock import AsyncMock

from aivo_model_providers.base import (
    Provider,
    ProviderType,
    GenerateRequest,
    GenerateResponse,
    EmbedRequest,
    EmbedResponse,
    ModerateRequest,
    ModerateResponse,
    ModerationResult,
    ModerationCategory,
    FineTuneRequest,
    FineTuneResponse,
    JobStatusRequest,
    JobStatusResponse,
    JobStatus,
    ProviderError,
    ProviderUnavailableError,
    ProviderConfigError,
    ProviderRateLimitError,
    ProviderQuotaError,
)


class MockProvider(Provider):
    """Mock provider for testing."""
    
    def __init__(self):
        super().__init__(ProviderType.OPENAI)
        self.is_available_result = True

    async def is_available(self) -> bool:
        return self.is_available_result

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return GenerateResponse(
            content="Test response",
            model=request.model,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
            provider=self.provider_type.value,
        )

    async def embed(self, request: EmbedRequest) -> EmbedResponse:
        return EmbedResponse(
            embeddings=[[0.1, 0.2, 0.3] for _ in request.texts],
            model=request.model,
            usage={"prompt_tokens": 10, "total_tokens": 10},
            provider=self.provider_type.value,
        )

    async def moderate(self, request: ModerateRequest) -> ModerateResponse:
        return ModerateResponse(
            flagged=False,
            results=[
                ModerationResult(
                    category=ModerationCategory.HATE,
                    score=0.1,
                    flagged=False
                )
            ],
            provider=self.provider_type.value,
        )

    async def fine_tune(self, request: FineTuneRequest) -> FineTuneResponse:
        return FineTuneResponse(
            job_id="test-job-123",
            status=JobStatus.PENDING,
            model=request.model,
            provider=self.provider_type.value,
        )

    async def job_status(self, request: JobStatusRequest) -> JobStatusResponse:
        return JobStatusResponse(
            job_id=request.job_id,
            status=JobStatus.SUCCEEDED,
            provider=self.provider_type.value,
        )

    async def get_available_models(self) -> dict[str, list[str]]:
        return {
            "generate": ["test-model"],
            "embed": ["test-embed"],
            "moderate": ["test-moderate"],
        }


class TestProviderTypes:
    """Test provider type enumeration."""
    
    def test_provider_types(self):
        """Test that all expected provider types exist."""
        assert ProviderType.OPENAI == "openai"
        assert ProviderType.VERTEX_GEMINI == "vertex_gemini"
        assert ProviderType.BEDROCK_ANTHROPIC == "bedrock_anthropic"
        assert ProviderType.AUTO == "auto"


class TestJobStatus:
    """Test job status enumeration."""
    
    def test_job_status_values(self):
        """Test that all expected job status values exist."""
        assert JobStatus.PENDING == "pending"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.SUCCEEDED == "succeeded"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELLED == "cancelled"


class TestModerationCategory:
    """Test moderation category enumeration."""
    
    def test_moderation_categories(self):
        """Test that all expected moderation categories exist."""
        assert ModerationCategory.HATE == "hate"
        assert ModerationCategory.HARASSMENT == "harassment"
        assert ModerationCategory.SELF_HARM == "self-harm"
        assert ModerationCategory.SEXUAL == "sexual"
        assert ModerationCategory.VIOLENCE == "violence"
        assert ModerationCategory.ILLEGAL == "illegal"


class TestRequestResponseModels:
    """Test request and response model validation."""

    def test_generate_request_validation(self):
        """Test GenerateRequest validation."""
        # Valid request
        request = GenerateRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4",
            max_tokens=100,
            temperature=0.7,
        )
        assert request.messages == [{"role": "user", "content": "Hello"}]
        assert request.model == "gpt-4"
        assert request.max_tokens == 100
        assert request.temperature == 0.7

        # Invalid temperature
        with pytest.raises(ValueError):
            GenerateRequest(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4",
                temperature=3.0,  # > 2.0
            )

    def test_generate_response_model(self):
        """Test GenerateResponse model."""
        response = GenerateResponse(
            content="Hello, world!",
            model="gpt-4",
            usage={"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
            finish_reason="stop",
            provider="openai",
        )
        assert response.content == "Hello, world!"
        assert response.model == "gpt-4"
        assert response.provider == "openai"

    def test_embed_request_validation(self):
        """Test EmbedRequest validation."""
        request = EmbedRequest(
            texts=["Hello", "World"],
            model="text-embedding-3-small",
            dimensions=1536,
        )
        assert len(request.texts) == 2
        assert request.model == "text-embedding-3-small"
        assert request.dimensions == 1536

    def test_moderation_result_validation(self):
        """Test ModerationResult validation."""
        result = ModerationResult(
            category=ModerationCategory.HATE,
            score=0.8,
            flagged=True,
        )
        assert result.category == ModerationCategory.HATE
        assert result.score == 0.8
        assert result.flagged is True

        # Invalid score
        with pytest.raises(ValueError):
            ModerationResult(
                category=ModerationCategory.HATE,
                score=1.5,  # > 1.0
                flagged=True,
            )


class TestProviderExceptions:
    """Test provider exception hierarchy."""

    def test_provider_error_base(self):
        """Test base ProviderError."""
        error = ProviderError("Test error", "openai", "test_code")
        assert str(error) == "Test error"
        assert error.provider == "openai"
        assert error.error_code == "test_code"

    def test_provider_unavailable_error(self):
        """Test ProviderUnavailableError."""
        error = ProviderUnavailableError("Provider unavailable", "openai")
        assert isinstance(error, ProviderError)
        assert error.provider == "openai"

    def test_provider_rate_limit_error(self):
        """Test ProviderRateLimitError."""
        error = ProviderRateLimitError("Rate limited", "openai", retry_after=60)
        assert isinstance(error, ProviderError)
        assert error.retry_after == 60


@pytest.mark.asyncio
class TestMockProvider:
    """Test mock provider implementation."""

    async def test_provider_is_available(self):
        """Test provider availability check."""
        provider = MockProvider()
        assert await provider.is_available() is True

        provider.is_available_result = False
        assert await provider.is_available() is False

    async def test_provider_generate(self):
        """Test text generation."""
        provider = MockProvider()
        request = GenerateRequest(
            messages=[{"role": "user", "content": "Hello"}],
            model="test-model",
        )
        
        response = await provider.generate(request)
        
        assert response.content == "Test response"
        assert response.model == "test-model"
        assert response.provider == "openai"
        assert response.usage["total_tokens"] == 15

    async def test_provider_embed(self):
        """Test embedding generation."""
        provider = MockProvider()
        request = EmbedRequest(
            texts=["Hello", "World"],
            model="test-embed",
        )
        
        response = await provider.embed(request)
        
        assert len(response.embeddings) == 2
        assert response.model == "test-embed"
        assert response.provider == "openai"

    async def test_provider_moderate(self):
        """Test content moderation."""
        provider = MockProvider()
        request = ModerateRequest(content="Test content")
        
        response = await provider.moderate(request)
        
        assert response.flagged is False
        assert len(response.results) == 1
        assert response.results[0].category == ModerationCategory.HATE

    async def test_provider_fine_tune(self):
        """Test fine-tuning."""
        provider = MockProvider()
        request = FineTuneRequest(
            training_file_url="https://example.com/data.jsonl",
            model="test-model",
        )
        
        response = await provider.fine_tune(request)
        
        assert response.job_id == "test-job-123"
        assert response.status == JobStatus.PENDING
        assert response.model == "test-model"

    async def test_provider_job_status(self):
        """Test job status query."""
        provider = MockProvider()
        request = JobStatusRequest(job_id="test-job-123")
        
        response = await provider.job_status(request)
        
        assert response.job_id == "test-job-123"
        assert response.status == JobStatus.SUCCEEDED

    async def test_provider_get_available_models(self):
        """Test getting available models."""
        provider = MockProvider()
        
        models = await provider.get_available_models()
        
        assert "generate" in models
        assert "embed" in models
        assert "moderate" in models
        assert "test-model" in models["generate"]

    async def test_provider_context_manager(self):
        """Test provider as async context manager."""
        provider = MockProvider()
        
        async with provider as p:
            assert p is provider
            # Context manager should work without error
