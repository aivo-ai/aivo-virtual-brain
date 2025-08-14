"""
AIVO Model Providers Library

Unified interface for multi-cloud AI model providers.
"""

from .base import (
    Provider,
    ProviderType,
    GenerateRequest,
    GenerateResponse,
    EmbedRequest,
    EmbedResponse,
    ModerateRequest,
    ModerateResponse,
    FineTuneRequest,
    FineTuneResponse,
    JobStatusRequest,
    JobStatusResponse,
    ProviderError,
    ProviderUnavailableError,
    ProviderConfigError,
    ProviderRateLimitError,
    ProviderQuotaError,
)
from .factory import get_provider, get_available_providers, is_provider_available, get_feature_flags
from .config import get_config, reload_config, update_config

__version__ = "0.1.0"
__all__ = [
    # Base classes and types
    "Provider",
    "ProviderType",
    # Request/Response models
    "GenerateRequest",
    "GenerateResponse", 
    "EmbedRequest",
    "EmbedResponse",
    "ModerateRequest",
    "ModerateResponse",
    "FineTuneRequest",
    "FineTuneResponse",
    "JobStatusRequest",
    "JobStatusResponse",
    # Exceptions
    "ProviderError",
    "ProviderUnavailableError",
    "ProviderConfigError", 
    "ProviderRateLimitError",
    "ProviderQuotaError",
    # Factory functions
    "get_provider",
    "get_available_providers",
    "is_provider_available",
    "get_feature_flags",
    # Configuration
    "get_config",
    "reload_config", 
    "update_config",
]
