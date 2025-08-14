"""
Base classes and configuration for speech providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


@dataclass
class SpeechResult:
    """Result from speech processing operations."""
    
    provider: str
    operation: str  # "asr" or "tts"
    text: str
    confidence: float = 0.0
    audio_data: Optional[bytes] = None
    locale: str = "en"
    processing_time: float = 0.0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SpeechError(Exception):
    """Exception raised during speech processing."""
    
    def __init__(self, message: str, provider: str = None, operation: str = None):
        super().__init__(message)
        self.provider = provider
        self.operation = operation
        self.timestamp = datetime.utcnow()


class SpeechConfig:
    """Configuration manager for speech providers."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._providers_config = config.get("providers", {})
        
    def get_provider_config(self, provider: str, key: str, default: Any = None) -> Any:
        """Get configuration value for a specific provider."""
        provider_config = self._providers_config.get(provider, {})
        return provider_config.get(key, default)
    
    def get_fallback_chain(self, operation: str, locale: str) -> List[str]:
        """Get fallback chain for operation and locale."""
        fallbacks = self.config.get("fallback_chains", {})
        operation_fallbacks = fallbacks.get(operation, {})
        return operation_fallbacks.get(locale, operation_fallbacks.get("default", []))
    
    def is_locale_supported(self, provider: str, locale: str) -> bool:
        """Check if locale is supported by provider."""
        supported = self._providers_config.get(provider, {}).get("supported_locales", [])
        return locale in supported


class SpeechProvider(ABC):
    """Abstract base class for speech providers."""
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.provider_name = "unknown"
        self.logger = logging.getLogger(f"speech.{self.provider_name}")
    
    @abstractmethod
    async def transcribe_audio(
        self,
        audio_data: bytes,
        locale: str = "en",
        format: str = "wav",
        **kwargs
    ) -> SpeechResult:
        """Transcribe audio to text (ASR)."""
        pass
    
    @abstractmethod
    async def synthesize_speech(
        self,
        text: str,
        locale: str = "en",
        voice: Optional[str] = None,
        **kwargs
    ) -> SpeechResult:
        """Synthesize text to speech (TTS)."""
        pass
    
    @abstractmethod
    async def get_supported_locales(self) -> List[str]:
        """Get list of supported locales."""
        pass
    
    @abstractmethod
    async def get_available_voices(self, locale: str) -> List[Dict[str, Any]]:
        """Get available voices for a locale."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health status."""
        pass
    
    def supports_locale(self, locale: str) -> bool:
        """Check if provider supports a locale."""
        return self.config.is_locale_supported(self.provider_name, locale)
    
    def supports_operation(self, operation: str) -> bool:
        """Check if provider supports an operation."""
        capabilities = self.config.get_provider_config(self.provider_name, "capabilities", [])
        return operation in capabilities


class SpeechMatrix:
    """Speech provider matrix manager."""
    
    def __init__(self, config: SpeechConfig):
        self.config = config
        self.providers = {}
        self.logger = logging.getLogger("speech.matrix")
    
    def register_provider(self, provider: SpeechProvider):
        """Register a speech provider."""
        self.providers[provider.provider_name] = provider
        self.logger.info(f"Registered speech provider: {provider.provider_name}")
    
    def get_provider(self, provider_name: str) -> Optional[SpeechProvider]:
        """Get a specific provider."""
        return self.providers.get(provider_name)
    
    def get_best_provider(self, operation: str, locale: str) -> Optional[SpeechProvider]:
        """Get the best provider for operation and locale."""
        fallback_chain = self.config.get_fallback_chain(operation, locale)
        
        for provider_name in fallback_chain:
            provider = self.providers.get(provider_name)
            if provider and provider.supports_locale(locale) and provider.supports_operation(operation):
                return provider
        
        return None
    
    def get_available_providers(self, operation: str, locale: str) -> List[SpeechProvider]:
        """Get all available providers for operation and locale."""
        available = []
        
        for provider in self.providers.values():
            if provider.supports_locale(locale) and provider.supports_operation(operation):
                available.append(provider)
        
        return available
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all providers."""
        health_results = {}
        
        for name, provider in self.providers.items():
            try:
                health_results[name] = await provider.health_check()
            except Exception as e:
                health_results[name] = {
                    "provider": name,
                    "status": "error",
                    "error": str(e),
                    "last_checked": datetime.utcnow().isoformat()
                }
        
        return {
            "providers": health_results,
            "summary": {
                "total_providers": len(self.providers),
                "healthy_providers": sum(1 for h in health_results.values() if h.get("status") == "healthy"),
                "degraded_providers": sum(1 for h in health_results.values() if h.get("status") == "degraded"),
                "unhealthy_providers": sum(1 for h in health_results.values() if h.get("status") in ["unhealthy", "error"])
            },
            "last_checked": datetime.utcnow().isoformat()
        }
