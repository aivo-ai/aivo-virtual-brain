"""
Provider factory for creating and managing model providers.
"""

import os
from typing import Dict, List, Optional, Union
import structlog

from .base import Provider, ProviderType
from .openai_provider import OpenAIProvider
from .vertex_gemini_provider import VertexGeminiProvider
from .bedrock_anthropic_provider import BedrockAnthropicProvider

logger = structlog.get_logger()


# Provider registry
_PROVIDERS: Dict[ProviderType, type[Provider]] = {
    ProviderType.OPENAI: OpenAIProvider,
    ProviderType.VERTEX_GEMINI: VertexGeminiProvider,
    ProviderType.BEDROCK_ANTHROPIC: BedrockAnthropicProvider,
}


class ProviderRegistry:
    """Registry for managing provider instances and availability."""
    
    def __init__(self):
        self._instances: Dict[ProviderType, Optional[Provider]] = {}
        self._availability_cache: Dict[ProviderType, Optional[bool]] = {}

    async def get_provider(self, provider_type: ProviderType) -> Provider:
        """Get a provider instance, creating it if necessary."""
        if provider_type == ProviderType.AUTO:
            return await self._get_auto_provider()
        
        if provider_type not in _PROVIDERS:
            raise ValueError(f"Unsupported provider type: {provider_type}")
        
        # Return cached instance if available
        if provider_type in self._instances and self._instances[provider_type]:
            return self._instances[provider_type]
        
        # Create new instance
        provider_class = _PROVIDERS[provider_type]
        provider = provider_class()
        
        # Check availability
        if not await provider.is_available():
            from .base import ProviderUnavailableError
            raise ProviderUnavailableError(
                f"Provider {provider_type.value} is not available",
                provider_type.value
            )
        
        self._instances[provider_type] = provider
        self._availability_cache[provider_type] = True
        
        return provider

    async def _get_auto_provider(self) -> Provider:
        """Auto-detect and return the best available provider."""
        # Priority order for auto-selection
        priority_order = [
            ProviderType.OPENAI,
            ProviderType.VERTEX_GEMINI,
            ProviderType.BEDROCK_ANTHROPIC,
        ]
        
        for provider_type in priority_order:
            try:
                provider = await self.get_provider(provider_type)
                logger.info("Auto-selected provider", provider=provider_type.value)
                return provider
            except Exception as e:
                logger.debug("Provider unavailable for auto-selection", 
                           provider=provider_type.value, error=str(e))
                continue
        
        from .base import ProviderUnavailableError
        raise ProviderUnavailableError(
            "No providers are available. Please check your credentials.",
            "auto"
        )

    async def is_provider_available(self, provider_type: ProviderType) -> bool:
        """Check if a specific provider is available."""
        if provider_type == ProviderType.AUTO:
            return await self._is_any_provider_available()
        
        if provider_type not in _PROVIDERS:
            return False
        
        # Check cache first
        if provider_type in self._availability_cache:
            cached_result = self._availability_cache[provider_type]
            if cached_result is not None:
                return cached_result
        
        try:
            provider_class = _PROVIDERS[provider_type]
            provider = provider_class()
            is_available = await provider.is_available()
            self._availability_cache[provider_type] = is_available
            return is_available
        except Exception as e:
            logger.warning("Error checking provider availability", 
                         provider=provider_type.value, error=str(e))
            self._availability_cache[provider_type] = False
            return False

    async def _is_any_provider_available(self) -> bool:
        """Check if any provider is available."""
        for provider_type in _PROVIDERS:
            if await self.is_provider_available(provider_type):
                return True
        return False

    async def get_available_providers(self) -> List[ProviderType]:
        """Get list of available providers."""
        available = []
        for provider_type in _PROVIDERS:
            if await self.is_provider_available(provider_type):
                available.append(provider_type)
        return available

    def clear_cache(self):
        """Clear availability cache."""
        self._availability_cache.clear()

    async def close_all(self):
        """Close all provider instances."""
        for provider in self._instances.values():
            if provider:
                try:
                    await provider.__aexit__(None, None, None)
                except Exception as e:
                    logger.warning("Error closing provider", error=str(e))
        self._instances.clear()


# Global registry instance
_registry = ProviderRegistry()


async def get_provider(
    provider_type: Union[ProviderType, str] = ProviderType.AUTO
) -> Provider:
    """
    Get a provider instance.
    
    Args:
        provider_type: Type of provider to create. Defaults to AUTO for best available.
    
    Returns:
        Provider instance
    
    Raises:
        ProviderUnavailableError: If the requested provider is not available
        ValueError: If the provider type is not supported
    """
    if isinstance(provider_type, str):
        provider_type = ProviderType(provider_type)
    
    return await _registry.get_provider(provider_type)


async def is_provider_available(
    provider_type: Union[ProviderType, str]
) -> bool:
    """
    Check if a provider is available.
    
    Args:
        provider_type: Type of provider to check
    
    Returns:
        True if provider is available, False otherwise
    """
    if isinstance(provider_type, str):
        provider_type = ProviderType(provider_type)
    
    return await _registry.is_provider_available(provider_type)


async def get_available_providers() -> List[ProviderType]:
    """
    Get list of available providers.
    
    Returns:
        List of available provider types
    """
    return await _registry.get_available_providers()


def clear_provider_cache():
    """Clear provider availability cache."""
    _registry.clear_cache()


async def close_all_providers():
    """Close all provider instances."""
    await _registry.close_all()


# Environment-based provider configuration
def get_provider_config() -> Dict[str, bool]:
    """
    Get provider configuration from environment variables.
    
    Returns:
        Dictionary with provider availability flags
    """
    return {
        "openai_enabled": bool(os.getenv("OPENAI_API_KEY")),
        "vertex_enabled": bool(
            os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and 
            os.getenv("GOOGLE_CLOUD_PROJECT")
        ),
        "bedrock_enabled": bool(
            os.getenv("AWS_ACCESS_KEY_ID") and 
            os.getenv("AWS_SECRET_ACCESS_KEY")
        ),
    }


def get_feature_flags() -> Dict[str, bool]:
    """
    Get feature flags for provider capabilities.
    
    Returns:
        Dictionary with feature availability flags
    """
    config = get_provider_config()
    
    return {
        "generate_enabled": any(config.values()),
        "embed_enabled": any(config.values()),
        "moderate_enabled": config["openai_enabled"] or config["vertex_enabled"],
        "fine_tune_enabled": any(config.values()),
        "openai_available": config["openai_enabled"],
        "vertex_available": config["vertex_enabled"],
        "bedrock_available": config["bedrock_enabled"],
    }
