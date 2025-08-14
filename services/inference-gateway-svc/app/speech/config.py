"""
Speech configuration management and provider matrix setup.
"""

from typing import Dict, Any, List
import json
import os
from pathlib import Path

from .base import SpeechConfig, SpeechMatrix
from .providers.azure import AzureSpeechProvider
from .providers.google import GoogleSpeechProvider  
from .providers.aws import AWSSpeechProvider


class SpeechConfigManager:
    """Manages speech configuration and provider initialization."""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or self._get_default_config_path()
        self.config_data = self._load_config()
        self.speech_config = SpeechConfig(self.config_data)
        self.matrix = SpeechMatrix(self.speech_config)
        
    def _get_default_config_path(self) -> str:
        """Get default path to locales configuration."""
        # Look for locales.json in the libs/i18n directory
        current_dir = Path(__file__).parent
        project_root = current_dir.parent.parent.parent.parent
        locales_path = project_root / "libs" / "i18n" / "locales.json"
        return str(locales_path)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from locales.json."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            # Fallback configuration if file not found
            return self._get_fallback_config()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """Fallback configuration if locales.json is not available."""
        return {
            "default_locale": "en",
            "fallback_locale": "en",
            "speech_matrix": {
                "providers": {
                    "azure": {
                        "name": "Azure Cognitive Services",
                        "priority": 1,
                        "capabilities": ["asr", "tts"],
                        "supported_locales": ["en", "es", "fr", "ar", "zh-Hans", "hi", "pt"]
                    },
                    "google": {
                        "name": "Google Cloud Speech",
                        "priority": 2,
                        "capabilities": ["asr", "tts"],
                        "supported_locales": ["en", "es", "fr", "ar", "zh-Hans", "hi", "pt", "ig", "yo", "ha", "sw"]
                    },
                    "aws": {
                        "name": "AWS Transcribe/Polly",
                        "priority": 3,
                        "capabilities": ["asr", "tts"],
                        "supported_locales": ["en", "es", "fr", "zh-Hans", "pt"]
                    }
                },
                "fallback_chains": {
                    "asr": {
                        "default": ["google", "azure"]
                    },
                    "tts": {
                        "default": ["google", "azure"]
                    }
                }
            }
        }
    
    def initialize_providers(self, provider_configs: Dict[str, Dict[str, Any]] = None) -> SpeechMatrix:
        """Initialize speech providers."""
        
        # Default provider configurations
        default_configs = {
            "azure": {
                "subscription_key": os.getenv("AZURE_SPEECH_KEY", ""),
                "region": os.getenv("AZURE_SPEECH_REGION", "eastus")
            },
            "google": {
                "api_key": os.getenv("GOOGLE_SPEECH_API_KEY", ""),
                "project_id": os.getenv("GOOGLE_PROJECT_ID", "")
            },
            "aws": {
                "access_key_id": os.getenv("AWS_ACCESS_KEY_ID", ""),
                "secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY", ""),
                "region": os.getenv("AWS_REGION", "us-east-1")
            }
        }
        
        # Merge with provided configs
        if provider_configs:
            for provider, config in provider_configs.items():
                if provider in default_configs:
                    default_configs[provider].update(config)
                else:
                    default_configs[provider] = config
        
        # Update speech config with provider configurations
        self.config_data["providers"] = default_configs
        self.speech_config = SpeechConfig(self.config_data)
        self.matrix = SpeechMatrix(self.speech_config)
        
        # Initialize providers
        try:
            azure_provider = AzureSpeechProvider(self.speech_config)
            self.matrix.register_provider(azure_provider)
        except Exception as e:
            print(f"Failed to initialize Azure provider: {e}")
        
        try:
            google_provider = GoogleSpeechProvider(self.speech_config)
            self.matrix.register_provider(google_provider)
        except Exception as e:
            print(f"Failed to initialize Google provider: {e}")
        
        try:
            aws_provider = AWSSpeechProvider(self.speech_config)
            self.matrix.register_provider(aws_provider)
        except Exception as e:
            print(f"Failed to initialize AWS provider: {e}")
        
        return self.matrix
    
    def get_supported_locales(self) -> List[str]:
        """Get all supported locales across providers."""
        locales = set()
        
        for provider_config in self.config_data.get("speech_matrix", {}).get("providers", {}).values():
            locales.update(provider_config.get("supported_locales", []))
        
        return sorted(list(locales))
    
    def get_locale_info(self, locale: str) -> Dict[str, Any]:
        """Get detailed information about a locale."""
        supported_locales = self.config_data.get("supported_locales", {})
        return supported_locales.get(locale, {})
    
    def get_rtl_locales(self) -> List[str]:
        """Get list of right-to-left locales."""
        return self.config_data.get("rtl_locales", [])
    
    def get_provider_matrix(self) -> Dict[str, Any]:
        """Get the complete provider matrix configuration."""
        return self.config_data.get("speech_matrix", {})
    
    def get_fallback_chains(self) -> Dict[str, Dict[str, List[str]]]:
        """Get fallback chains for all operations and locales."""
        return self.config_data.get("speech_matrix", {}).get("fallback_chains", {})


# Singleton instance for global access
_config_manager = None

def get_speech_config_manager() -> SpeechConfigManager:
    """Get global speech configuration manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = SpeechConfigManager()
    return _config_manager


def initialize_speech_matrix(provider_configs: Dict[str, Dict[str, Any]] = None) -> SpeechMatrix:
    """Initialize the global speech matrix."""
    config_manager = get_speech_config_manager()
    return config_manager.initialize_providers(provider_configs)
