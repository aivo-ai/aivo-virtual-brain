"""
SIS Provider Implementations

Base classes and specific implementations for SIS providers.
"""

from .base import BaseSISProvider
from .clever import CleverProvider
from .classlink import ClassLinkProvider

__all__ = ["BaseSISProvider", "CleverProvider", "ClassLinkProvider", "get_provider", "AVAILABLE_PROVIDERS"]

# Available SIS providers
AVAILABLE_PROVIDERS = {
    "clever": CleverProvider,
    "classlink": ClassLinkProvider
}


def get_provider(provider_name: str, config: dict) -> BaseSISProvider:
    """Get SIS provider instance by name."""
    if provider_name not in AVAILABLE_PROVIDERS:
        raise ValueError(f"Unknown SIS provider: {provider_name}")
    
    return AVAILABLE_PROVIDERS[provider_name](config)
