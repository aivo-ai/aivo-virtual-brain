"""
Test OpenAI provider implementation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aivo_model_providers.openai_provider import OpenAIProvider
from aivo_model_providers.base import (
    GenerateRequest,
    EmbedRequest,
    ModerateRequest,
    FineTuneRequest,
    JobStatusRequest,
    ProviderUnavailableError,
    ProviderRateLimitError,
    ProviderQuotaError,
    ProviderConfigError,
    ProviderError,
)


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""

    @pytest.fixture
    def provider(self):
        """Create OpenAI provider instance."""
        return OpenAIProvider()

    @pytest.fixture
    def mock_openai_client(self):
        """Create mock OpenAI client."""
        mock_client = AsyncMock()
        return mock_client

    @pytest.mark.asyncio
    async def test_is_available_with_api_key(self, provider):
        """Test provider availability with API key."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), \
             patch.object(provider, '_ensure_client') as mock_ensure:
            
            mock_client = AsyncMock()
            mock_client.models.list.return_value = MagicMock()
            mock_ensure.return_value = mock_client
            
            is_available = await provider.is_available()
            
            assert is_available is True
            mock_client.models.list.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_available_without_api_key(self, provider):
        """Test provider availability without API key."""
        with patch.dict('os.environ', {}, clear=True):
            is_available = await provider.is_available()
            assert is_available is False

    @pytest.mark.asyncio
    async def test_is_available_with_api_error(self, provider):
        """Test provider availability with API error."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}), \
             patch.object(provider, '_ensure_client') as mock_ensure:
            
            mock_client = AsyncMock()
            mock_client.models.list.side_effect = Exception("API Error")
            mock_ensure.return_value = mock_client
            
            is_available = await provider.is_available()
            assert is_available is False

    @pytest.mark.asyncio
    async def test_ensure_client_without_api_key(self, provider):
        """Test _ensure_client raises error without API key."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(ProviderUnavailableError):
                await provider._ensure_client()

    @pytest.mark.asyncio
    async def test_generate_success(self, provider, mock_openai_client):
        """Test successful text generation."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            # Mock response
            mock_completion = MagicMock()
            mock_completion.choices = [MagicMock()]
            mock_completion.choices[0].message.content = "Test response"
            mock_completion.choices[0].finish_reason = "stop"
            mock_completion.model = "gpt-4"
            mock_completion.usage.prompt_tokens = 10
            mock_completion.usage.completion_tokens = 5
            mock_completion.usage.total_tokens = 15
            mock_completion.id = "test-123"
            mock_completion.created = 1234567890
            
            mock_openai_client.chat.completions.create.return_value = mock_completion
            
            request = GenerateRequest(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4",
                max_tokens=100,
                temperature=0.7,
            )
            
            response = await provider.generate(request)
            
            assert response.content == "Test response"
            assert response.model == "gpt-4"
            assert response.usage["total_tokens"] == 15
            assert response.finish_reason == "stop"
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_generate_with_openai_error(self, provider, mock_openai_client):
        """Test generate with OpenAI API error."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            mock_openai_client.chat.completions.create.side_effect = Exception("rate_limit exceeded")
            
            request = GenerateRequest(
                messages=[{"role": "user", "content": "Hello"}],
                model="gpt-4",
            )
            
            with pytest.raises(ProviderRateLimitError):
                await provider.generate(request)

    @pytest.mark.asyncio
    async def test_embed_success(self, provider, mock_openai_client):
        """Test successful embedding generation."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            # Mock response
            mock_response = MagicMock()
            mock_response.data = [MagicMock(), MagicMock()]
            mock_response.data[0].embedding = [0.1, 0.2, 0.3]
            mock_response.data[1].embedding = [0.4, 0.5, 0.6]
            mock_response.model = "text-embedding-3-small"
            mock_response.usage.prompt_tokens = 10
            mock_response.usage.total_tokens = 10
            mock_response.object = "list"
            
            mock_openai_client.embeddings.create.return_value = mock_response
            
            request = EmbedRequest(
                texts=["Hello", "World"],
                model="text-embedding-3-small",
                dimensions=1536,
            )
            
            response = await provider.embed(request)
            
            assert len(response.embeddings) == 2
            assert response.embeddings[0] == [0.1, 0.2, 0.3]
            assert response.embeddings[1] == [0.4, 0.5, 0.6]
            assert response.model == "text-embedding-3-small"
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_moderate_success(self, provider, mock_openai_client):
        """Test successful content moderation."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            # Mock response
            mock_moderation = MagicMock()
            mock_moderation.results = [MagicMock()]
            mock_moderation.results[0].flagged = True
            mock_moderation.results[0].categories.model_dump.return_value = {
                "hate": True,
                "harassment": False,
                "self-harm": False,
                "sexual": False,
                "violence": False,
            }
            mock_moderation.results[0].category_scores.model_dump.return_value = {
                "hate": 0.8,
                "harassment": 0.1,
                "self-harm": 0.0,
                "sexual": 0.0,
                "violence": 0.0,
            }
            mock_moderation.id = "mod-123"
            mock_moderation.model = "text-moderation-latest"
            
            mock_openai_client.moderations.create.return_value = mock_moderation
            
            request = ModerateRequest(content="This is hate speech")
            
            response = await provider.moderate(request)
            
            assert response.flagged is True
            assert len(response.results) > 0
            assert response.provider == "openai"
            
            # Check that hate category was flagged
            hate_results = [r for r in response.results if r.category.value == "hate"]
            assert len(hate_results) > 0
            assert hate_results[0].flagged is True
            assert hate_results[0].score == 0.8

    @pytest.mark.asyncio
    async def test_fine_tune_success(self, provider, mock_openai_client):
        """Test successful fine-tuning job creation."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            # Mock response
            mock_job = MagicMock()
            mock_job.id = "ftjob-123"
            mock_job.status = "queued"
            mock_job.model = "gpt-3.5-turbo"
            mock_job.estimated_finish = "2024-01-15T10:00:00Z"
            mock_job.object = "fine_tuning.job"
            mock_job.created_at = 1234567890
            mock_job.organization_id = "org-123"
            
            mock_openai_client.fine_tuning.jobs.create.return_value = mock_job
            
            request = FineTuneRequest(
                training_file_url="file-123",
                model="gpt-3.5-turbo",
                validation_file_url="file-456",
                suffix="custom",
            )
            
            response = await provider.fine_tune(request)
            
            assert response.job_id == "ftjob-123"
            assert response.status.value == "pending"  # queued maps to pending
            assert response.model == "gpt-3.5-turbo"
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_job_status_success(self, provider, mock_openai_client):
        """Test successful job status query."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            # Mock response
            mock_job = MagicMock()
            mock_job.id = "ftjob-123"
            mock_job.status = "succeeded"
            mock_job.fine_tuned_model = "ft:gpt-3.5-turbo:custom"
            mock_job.result_files = ["file-result-123"]
            mock_job.error = None
            mock_job.created_at = 1234567890
            mock_job.finished_at = 1234567900
            mock_job.object = "fine_tuning.job"
            mock_job.organization_id = "org-123"
            mock_job.training_file = "file-123"
            mock_job.validation_file = "file-456"
            
            mock_openai_client.fine_tuning.jobs.retrieve.return_value = mock_job
            
            request = JobStatusRequest(job_id="ftjob-123")
            
            response = await provider.job_status(request)
            
            assert response.job_id == "ftjob-123"
            assert response.status.value == "succeeded"
            assert response.result["fine_tuned_model"] == "ft:gpt-3.5-turbo:custom"
            assert response.provider == "openai"

    @pytest.mark.asyncio
    async def test_get_available_models(self, provider, mock_openai_client):
        """Test getting available models."""
        with patch.object(provider, '_ensure_client', return_value=mock_openai_client):
            # Mock response
            mock_models = MagicMock()
            mock_models.data = [
                MagicMock(id="gpt-4"),
                MagicMock(id="gpt-3.5-turbo"),
                MagicMock(id="text-embedding-3-small"),
                MagicMock(id="text-embedding-ada-002"),
            ]
            
            mock_openai_client.models.list.return_value = mock_models
            
            models = await provider.get_available_models()
            
            assert "generate" in models
            assert "embed" in models
            assert "moderate" in models
            assert "gpt-4" in models["generate"]
            assert "text-embedding-3-small" in models["embed"]

    def test_map_openai_error_rate_limit(self, provider):
        """Test mapping rate limit error."""
        error = Exception("rate_limit exceeded")
        mapped_error = provider._map_openai_error(error)
        
        assert isinstance(mapped_error, ProviderRateLimitError)
        assert "rate limit" in str(mapped_error).lower()

    def test_map_openai_error_quota(self, provider):
        """Test mapping quota error."""
        error = Exception("quota exceeded")
        mapped_error = provider._map_openai_error(error)
        
        assert isinstance(mapped_error, ProviderQuotaError)

    def test_map_openai_error_authentication(self, provider):
        """Test mapping authentication error."""
        error = Exception("invalid api_key")
        mapped_error = provider._map_openai_error(error)
        
        assert isinstance(mapped_error, ProviderConfigError)

    def test_map_openai_error_generic(self, provider):
        """Test mapping generic error."""
        error = Exception("something went wrong")
        mapped_error = provider._map_openai_error(error)
        
        assert isinstance(mapped_error, ProviderError)
        assert not isinstance(mapped_error, (ProviderRateLimitError, ProviderQuotaError, ProviderConfigError))

    @pytest.mark.asyncio
    async def test_context_manager_cleanup(self, provider):
        """Test provider cleanup in context manager."""
        mock_client = AsyncMock()
        provider.client = mock_client
        
        await provider.__aexit__(None, None, None)
        
        mock_client.close.assert_called_once()
