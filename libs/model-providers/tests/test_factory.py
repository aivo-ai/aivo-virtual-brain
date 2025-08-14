"""
Test factory functionality and provider registry.
"""

import os
import pytest
from unittest.mock import AsyncMock, patch

from aivo_model_providers.factory import (
    ProviderRegistry,
    get_provider,
    is_provider_available,
    get_available_providers,
    clear_provider_cache,
    close_all_providers,
    get_provider_config,
    get_feature_flags,
)
from aivo_model_providers.base import (
    ProviderType,
    ProviderUnavailableError,
)


class TestProviderRegistry:
    """Test the provider registry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh provider registry for testing."""
        return ProviderRegistry()

    @pytest.mark.asyncio
    async def test_get_provider_creates_instance(self, registry):
        """Test that get_provider creates provider instances."""
        with patch.object(registry, '_instances', {}), \
             patch('aivo_model_providers.factory.OpenAIProvider') as mock_openai:
            
            # Mock provider instance
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_openai.return_value = mock_provider
            
            provider = await registry.get_provider(ProviderType.OPENAI)
            
            assert provider is mock_provider
            mock_openai.assert_called_once()
            mock_provider.is_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_provider_reuses_cached_instance(self, registry):
        """Test that get_provider reuses cached instances."""
        mock_provider = AsyncMock()
        registry._instances[ProviderType.OPENAI] = mock_provider
        
        provider = await registry.get_provider(ProviderType.OPENAI)
        
        assert provider is mock_provider

    @pytest.mark.asyncio
    async def test_get_provider_unavailable_raises_error(self, registry):
        """Test that unavailable provider raises error."""
        with patch('aivo_model_providers.factory.OpenAIProvider') as mock_openai:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = False
            mock_openai.return_value = mock_provider
            
            with pytest.raises(ProviderUnavailableError):
                await registry.get_provider(ProviderType.OPENAI)

    @pytest.mark.asyncio
    async def test_get_auto_provider_selects_available(self, registry):
        """Test auto provider selection."""
        with patch.object(registry, 'get_provider') as mock_get:
            mock_provider = AsyncMock()
            
            # First provider fails, second succeeds
            mock_get.side_effect = [
                ProviderUnavailableError("OpenAI unavailable", "openai"),
                mock_provider,
            ]
            
            provider = await registry._get_auto_provider()
            
            assert provider is mock_provider
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_get_auto_provider_no_available_raises_error(self, registry):
        """Test auto provider when none available."""
        with patch.object(registry, 'get_provider') as mock_get:
            mock_get.side_effect = ProviderUnavailableError("Unavailable", "test")
            
            with pytest.raises(ProviderUnavailableError):
                await registry._get_auto_provider()

    @pytest.mark.asyncio
    async def test_is_provider_available_checks_provider(self, registry):
        """Test provider availability checking."""
        with patch('aivo_model_providers.factory.OpenAIProvider') as mock_openai:
            mock_provider = AsyncMock()
            mock_provider.is_available.return_value = True
            mock_openai.return_value = mock_provider
            
            is_available = await registry.is_provider_available(ProviderType.OPENAI)
            
            assert is_available is True
            mock_provider.is_available.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_provider_available_caches_result(self, registry):
        """Test that availability results are cached."""
        registry._availability_cache[ProviderType.OPENAI] = True
        
        is_available = await registry.is_provider_available(ProviderType.OPENAI)
        
        assert is_available is True

    @pytest.mark.asyncio
    async def test_get_available_providers(self, registry):
        """Test getting list of available providers."""
        with patch.object(registry, 'is_provider_available') as mock_is_available:
            # Mock availability results
            availability_results = {
                ProviderType.OPENAI: True,
                ProviderType.VERTEX_GEMINI: False,
                ProviderType.BEDROCK_ANTHROPIC: True,
            }
            mock_is_available.side_effect = lambda pt: availability_results[pt]
            
            available = await registry.get_available_providers()
            
            assert ProviderType.OPENAI in available
            assert ProviderType.VERTEX_GEMINI not in available
            assert ProviderType.BEDROCK_ANTHROPIC in available

    def test_clear_cache(self, registry):
        """Test clearing availability cache."""
        registry._availability_cache[ProviderType.OPENAI] = True
        registry.clear_cache()
        assert len(registry._availability_cache) == 0

    @pytest.mark.asyncio
    async def test_close_all(self, registry):
        """Test closing all provider instances."""
        mock_provider1 = AsyncMock()
        mock_provider2 = AsyncMock()
        
        registry._instances = {
            ProviderType.OPENAI: mock_provider1,
            ProviderType.VERTEX_GEMINI: mock_provider2,
        }
        
        await registry.close_all()
        
        mock_provider1.__aexit__.assert_called_once()
        mock_provider2.__aexit__.assert_called_once()
        assert len(registry._instances) == 0


class TestFactoryFunctions:
    """Test module-level factory functions."""

    @pytest.mark.asyncio
    async def test_get_provider_function(self):
        """Test get_provider module function."""
        with patch('aivo_model_providers.factory._registry') as mock_registry:
            mock_provider = AsyncMock()
            mock_registry.get_provider.return_value = mock_provider
            
            provider = await get_provider(ProviderType.OPENAI)
            
            assert provider is mock_provider
            mock_registry.get_provider.assert_called_once_with(ProviderType.OPENAI)

    @pytest.mark.asyncio
    async def test_get_provider_with_string_type(self):
        """Test get_provider with string provider type."""
        with patch('aivo_model_providers.factory._registry') as mock_registry:
            mock_provider = AsyncMock()
            mock_registry.get_provider.return_value = mock_provider
            
            provider = await get_provider("openai")
            
            mock_registry.get_provider.assert_called_once_with(ProviderType.OPENAI)

    @pytest.mark.asyncio
    async def test_is_provider_available_function(self):
        """Test is_provider_available module function."""
        with patch('aivo_model_providers.factory._registry') as mock_registry:
            mock_registry.is_provider_available.return_value = True
            
            is_available = await is_provider_available(ProviderType.OPENAI)
            
            assert is_available is True
            mock_registry.is_provider_available.assert_called_once_with(ProviderType.OPENAI)

    @pytest.mark.asyncio
    async def test_get_available_providers_function(self):
        """Test get_available_providers module function."""
        with patch('aivo_model_providers.factory._registry') as mock_registry:
            expected_providers = [ProviderType.OPENAI, ProviderType.VERTEX_GEMINI]
            mock_registry.get_available_providers.return_value = expected_providers
            
            providers = await get_available_providers()
            
            assert providers == expected_providers

    def test_clear_provider_cache_function(self):
        """Test clear_provider_cache module function."""
        with patch('aivo_model_providers.factory._registry') as mock_registry:
            clear_provider_cache()
            mock_registry.clear_cache.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_all_providers_function(self):
        """Test close_all_providers module function."""
        with patch('aivo_model_providers.factory._registry') as mock_registry:
            await close_all_providers()
            mock_registry.close_all.assert_called_once()


class TestProviderConfig:
    """Test provider configuration functions."""

    def test_get_provider_config(self):
        """Test getting provider configuration from environment."""
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key',
            'GOOGLE_APPLICATION_CREDENTIALS': '/path/to/creds.json',
            'GOOGLE_CLOUD_PROJECT': 'test-project',
            'AWS_ACCESS_KEY_ID': 'test-access-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret-key',
        }):
            config = get_provider_config()
            
            assert config['openai_enabled'] is True
            assert config['vertex_enabled'] is True
            assert config['bedrock_enabled'] is True

    def test_get_provider_config_missing_credentials(self):
        """Test provider config with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            config = get_provider_config()
            
            assert config['openai_enabled'] is False
            assert config['vertex_enabled'] is False
            assert config['bedrock_enabled'] is False

    def test_get_feature_flags(self):
        """Test getting feature flags."""
        with patch('aivo_model_providers.factory.get_provider_config') as mock_config:
            mock_config.return_value = {
                'openai_enabled': True,
                'vertex_enabled': False,
                'bedrock_enabled': True,
            }
            
            flags = get_feature_flags()
            
            assert flags['generate_enabled'] is True  # Any provider available
            assert flags['embed_enabled'] is True     # Any provider available
            assert flags['moderate_enabled'] is True  # OpenAI available
            assert flags['fine_tune_enabled'] is True # Any provider available
            assert flags['openai_available'] is True
            assert flags['vertex_available'] is False
            assert flags['bedrock_available'] is True

    def test_get_feature_flags_no_providers(self):
        """Test feature flags when no providers available."""
        with patch('aivo_model_providers.factory.get_provider_config') as mock_config:
            mock_config.return_value = {
                'openai_enabled': False,
                'vertex_enabled': False,
                'bedrock_enabled': False,
            }
            
            flags = get_feature_flags()
            
            assert flags['generate_enabled'] is False
            assert flags['embed_enabled'] is False
            assert flags['moderate_enabled'] is False
            assert flags['fine_tune_enabled'] is False
