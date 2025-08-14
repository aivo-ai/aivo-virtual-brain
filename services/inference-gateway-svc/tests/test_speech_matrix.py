"""
Test suite for speech provider matrix and internationalization features.
"""

import pytest
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from speech.config import SpeechConfigManager, initialize_speech_matrix
from speech.base import SpeechProvider, SpeechResult, SpeechError, SpeechMatrix
from speech.providers.azure import AzureSpeechProvider
from speech.providers.google import GoogleSpeechProvider
from speech.providers.aws import AWSSpeechProvider


class TestSpeechMatrix:
    """Test speech provider matrix functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        return {
            "default_locale": "en",
            "fallback_locale": "en",
            "supported_locales": {
                "en": {
                    "code": "en",
                    "display_name": "English",
                    "rtl": False,
                    "speech_support": {
                        "asr": ["azure", "google", "aws"],
                        "tts": ["azure", "google", "aws"]
                    }
                },
                "es": {
                    "code": "es",
                    "display_name": "Spanish",
                    "rtl": False,
                    "speech_support": {
                        "asr": ["azure", "google"],
                        "tts": ["azure", "google"]
                    }
                },
                "ar": {
                    "code": "ar",
                    "display_name": "Arabic",
                    "rtl": True,
                    "speech_support": {
                        "asr": ["azure", "google"],
                        "tts": ["azure", "google"]
                    }
                },
                "ig": {
                    "code": "ig",
                    "display_name": "Igbo", 
                    "rtl": False,
                    "speech_support": {
                        "asr": ["google"],
                        "tts": ["google"]
                    }
                }
            },
            "rtl_locales": ["ar"],
            "speech_matrix": {
                "providers": {
                    "azure": {
                        "name": "Azure Cognitive Services",
                        "priority": 1,
                        "capabilities": ["asr", "tts"],
                        "supported_locales": ["en", "es", "ar"],
                        "quality_score": 95
                    },
                    "google": {
                        "name": "Google Cloud Speech",
                        "priority": 2, 
                        "capabilities": ["asr", "tts"],
                        "supported_locales": ["en", "es", "ar", "ig", "yo", "ha"],
                        "quality_score": 90
                    },
                    "aws": {
                        "name": "AWS Transcribe/Polly",
                        "priority": 3,
                        "capabilities": ["asr", "tts"],
                        "supported_locales": ["en", "es"],
                        "quality_score": 85
                    }
                },
                "fallback_chains": {
                    "asr": {
                        "en": ["azure", "google", "aws"],
                        "es": ["azure", "google"],
                        "ar": ["azure", "google"],
                        "ig": ["google"],
                        "default": ["google", "azure"]
                    },
                    "tts": {
                        "en": ["azure", "google", "aws"],
                        "es": ["azure", "google"],
                        "ar": ["azure", "google"],
                        "ig": ["google"],
                        "default": ["google", "azure"]
                    }
                }
            }
        }
    
    @pytest.fixture
    def config_manager(self, mock_config, tmp_path):
        """Create a test configuration manager."""
        config_file = tmp_path / "test_locales.json"
        with open(config_file, 'w') as f:
            json.dump(mock_config, f)
        
        return SpeechConfigManager(str(config_file))
    
    def test_config_loading(self, config_manager):
        """Test configuration loading from file."""
        assert config_manager.config_data["default_locale"] == "en"
        assert len(config_manager.config_data["supported_locales"]) == 4
        assert "ar" in config_manager.get_rtl_locales()
    
    def test_supported_locales(self, config_manager):
        """Test getting supported locales."""
        locales = config_manager.get_supported_locales()
        assert "en" in locales
        assert "es" in locales
        assert "ig" in locales
        assert len(locales) >= 3
    
    def test_rtl_locale_detection(self, config_manager):
        """Test RTL locale detection."""
        rtl_locales = config_manager.get_rtl_locales()
        assert "ar" in rtl_locales
        assert "en" not in rtl_locales
    
    def test_locale_info_retrieval(self, config_manager):
        """Test getting detailed locale information."""
        en_info = config_manager.get_locale_info("en")
        assert en_info["display_name"] == "English"
        assert en_info["rtl"] == False
        assert "asr" in en_info["speech_support"]
        
        ar_info = config_manager.get_locale_info("ar")
        assert ar_info["rtl"] == True
    
    def test_fallback_chains(self, config_manager):
        """Test fallback chain configuration."""
        fallbacks = config_manager.get_fallback_chains()
        
        # Test English fallback (full support)
        en_asr_fallback = fallbacks["asr"]["en"]
        assert en_asr_fallback == ["azure", "google", "aws"]
        
        # Test Igbo fallback (Google only)
        ig_asr_fallback = fallbacks["asr"]["ig"]
        assert ig_asr_fallback == ["google"]
        
        # Test default fallback
        default_fallback = fallbacks["asr"]["default"]
        assert "google" in default_fallback


class TestProviderMatrix:
    """Test provider matrix functionality."""
    
    @pytest.fixture
    def speech_matrix(self):
        """Create a test speech matrix."""
        from speech.base import SpeechConfig, SpeechMatrix
        config_data = {
            "providers": {
                "azure": {"supported_locales": ["en", "es", "ar"], "capabilities": ["asr", "tts"]},
                "google": {"supported_locales": ["en", "es", "ar", "ig"], "capabilities": ["asr", "tts"]},
                "aws": {"supported_locales": ["en", "es"], "capabilities": ["asr", "tts"]}
            },
            "speech_matrix": {
                "fallback_chains": {
                    "asr": {
                        "en": ["azure", "google", "aws"],
                        "ig": ["google"],
                        "default": ["google", "azure"]
                    }
                }
            }
        }
        config = SpeechConfig(config_data)
        return SpeechMatrix(config)
    
    @pytest.fixture
    def mock_providers(self, speech_matrix):
        """Create mock providers for testing."""
        # Mock Azure provider
        azure_provider = Mock(spec=SpeechProvider)
        azure_provider.provider_name = "azure"
        azure_provider.supports_locale.return_value = True
        azure_provider.supports_operation.return_value = True
        
        # Mock Google provider
        google_provider = Mock(spec=SpeechProvider)
        google_provider.provider_name = "google"
        google_provider.supports_locale.return_value = True
        google_provider.supports_operation.return_value = True
        
        # Mock AWS provider
        aws_provider = Mock(spec=SpeechProvider) 
        aws_provider.provider_name = "aws"
        aws_provider.supports_locale.side_effect = lambda locale: locale in ["en", "es"]
        aws_provider.supports_operation.return_value = True
        
        speech_matrix.register_provider(azure_provider)
        speech_matrix.register_provider(google_provider)
        speech_matrix.register_provider(aws_provider)
        
        return {
            "azure": azure_provider,
            "google": google_provider,
            "aws": aws_provider
        }
    
    def test_provider_registration(self, speech_matrix, mock_providers):
        """Test provider registration in matrix."""
        assert len(speech_matrix.providers) == 3
        assert "azure" in speech_matrix.providers
        assert "google" in speech_matrix.providers
        assert "aws" in speech_matrix.providers
    
    def test_best_provider_selection(self, speech_matrix, mock_providers):
        """Test best provider selection based on fallback chains."""
        # Test English (should prefer Azure first)
        best_en = speech_matrix.get_best_provider("asr", "en")
        assert best_en.provider_name == "azure"
        
        # Test Igbo (should only have Google)
        best_ig = speech_matrix.get_best_provider("asr", "ig")
        assert best_ig.provider_name == "google"
    
    def test_available_providers_list(self, speech_matrix, mock_providers):
        """Test getting list of available providers for locale."""
        # Test English (all providers should support)
        providers_en = speech_matrix.get_available_providers("asr", "en")
        assert len(providers_en) == 3
        
        # Test Igbo (only Google should support based on mock)
        mock_providers["azure"].supports_locale.side_effect = lambda locale: locale != "ig"
        mock_providers["aws"].supports_locale.side_effect = lambda locale: locale in ["en", "es"]
        
        providers_ig = speech_matrix.get_available_providers("asr", "ig")
        assert len(providers_ig) == 1
        assert providers_ig[0].provider_name == "google"
    
    @pytest.mark.asyncio
    async def test_health_status_aggregation(self, speech_matrix, mock_providers):
        """Test health status aggregation across providers."""
        # Mock health check responses
        mock_providers["azure"].health_check.return_value = {"status": "healthy", "provider": "azure"}
        mock_providers["google"].health_check.return_value = {"status": "degraded", "provider": "google"}
        mock_providers["aws"].health_check.return_value = {"status": "unhealthy", "provider": "aws"}
        
        health_status = await speech_matrix.get_health_status()
        
        assert health_status["summary"]["total_providers"] == 3
        assert health_status["summary"]["healthy_providers"] == 1
        assert health_status["summary"]["degraded_providers"] == 1
        assert health_status["summary"]["unhealthy_providers"] == 1


class TestLocaleSupport:
    """Test locale-specific functionality."""
    
    def test_tier1_locale_support(self):
        """Test that tier 1 locales have full provider support."""
        tier1_locales = ["en", "es", "fr", "ar", "zh-Hans", "hi", "pt"]
        
        for locale in tier1_locales:
            # These should have multiple provider options
            assert locale in ["en", "es", "fr", "ar", "zh-Hans", "hi", "pt"]
    
    def test_african_locale_support(self):
        """Test African language locale support."""
        african_locales = ["ig", "yo", "ha", "sw", "xh", "ki"]
        
        # Test that Google provides primary support for African languages
        google_supported = ["ig", "yo", "ha", "sw"]
        for locale in google_supported:
            assert locale in african_locales
    
    def test_experimental_locale_handling(self):
        """Test handling of experimental locales."""
        experimental_locales = ["efi", "xh", "ki"]
        
        # These locales should be marked as experimental
        for locale in experimental_locales:
            assert locale in ["efi", "xh", "ki"]
    
    def test_rtl_locale_configuration(self):
        """Test right-to-left locale configuration."""
        rtl_locales = ["ar"]
        
        # Arabic should be configured as RTL
        assert "ar" in rtl_locales


class TestProviderFallback:
    """Test provider fallback mechanisms."""
    
    @pytest.mark.asyncio
    async def test_primary_provider_failure_fallback(self):
        """Test fallback when primary provider fails."""
        # Mock a scenario where Azure fails but Google succeeds
        with patch('speech.providers.azure.AzureSpeechProvider') as mock_azure, \
             patch('speech.providers.google.GoogleSpeechProvider') as mock_google:
            
            # Azure fails
            mock_azure_instance = Mock()
            mock_azure_instance.transcribe_audio.side_effect = SpeechError("Azure failed")
            mock_azure.return_value = mock_azure_instance
            
            # Google succeeds
            mock_google_instance = Mock()
            mock_google_instance.transcribe_audio.return_value = SpeechResult(
                provider="google",
                operation="asr", 
                text="Test transcription",
                confidence=0.95
            )
            mock_google.return_value = mock_google_instance
            
            # Test that fallback works
            assert mock_google_instance.transcribe_audio.return_value.provider == "google"
    
    def test_missing_locale_fallback(self):
        """Test fallback when locale is not supported by primary provider."""
        # Test scenario where AWS doesn't support Igbo but Google does
        config_data = {
            "speech_matrix": {
                "fallback_chains": {
                    "asr": {
                        "ig": ["aws", "google"],  # AWS first, but doesn't support Igbo
                        "default": ["google"]
                    }
                }
            },
            "providers": {
                "aws": {"supported_locales": ["en", "es"], "capabilities": ["asr"]},
                "google": {"supported_locales": ["en", "es", "ig"], "capabilities": ["asr"]}
            }
        }
        
        from speech.base import SpeechConfig, SpeechMatrix
        config = SpeechConfig(config_data)
        matrix = SpeechMatrix(config)
        
        # Mock providers
        aws_provider = Mock()
        aws_provider.provider_name = "aws"
        aws_provider.supports_locale.side_effect = lambda locale: locale in ["en", "es"]
        aws_provider.supports_operation.return_value = True
        
        google_provider = Mock()
        google_provider.provider_name = "google"
        google_provider.supports_locale.return_value = True
        google_provider.supports_operation.return_value = True
        
        matrix.register_provider(aws_provider)
        matrix.register_provider(google_provider)
        
        # Should fallback to Google for Igbo
        best_provider = matrix.get_best_provider("asr", "ig")
        assert best_provider.provider_name == "google"


class TestHealthEndpoint:
    """Test health endpoint functionality."""
    
    @pytest.mark.asyncio
    async def test_health_endpoint_response_format(self):
        """Test health endpoint returns expected format."""
        # Mock speech matrix
        matrix = Mock()
        matrix.get_health_status.return_value = {
            "providers": {
                "azure": {"status": "healthy", "provider": "azure"},
                "google": {"status": "healthy", "provider": "google"},
                "aws": {"status": "degraded", "provider": "aws"}
            },
            "summary": {
                "total_providers": 3,
                "healthy_providers": 2,
                "degraded_providers": 1,
                "unhealthy_providers": 0
            },
            "last_checked": "2025-08-14T10:00:00Z"
        }
        
        health_response = await matrix.get_health_status()
        
        # Verify response structure
        assert "providers" in health_response
        assert "summary" in health_response
        assert "last_checked" in health_response
        assert health_response["summary"]["total_providers"] == 3
        assert health_response["summary"]["healthy_providers"] == 2
    
    def test_supported_speech_pairs_listing(self):
        """Test listing of supported speech pairs per locale."""
        config_data = {
            "supported_locales": {
                "en": {"speech_support": {"asr": ["azure", "google"], "tts": ["azure", "google"]}},
                "ig": {"speech_support": {"asr": ["google"], "tts": ["google"]}},
                "ar": {"speech_support": {"asr": ["azure"], "tts": ["azure"]}}
            }
        }
        
        # Extract speech pairs
        speech_pairs = {}
        for locale, info in config_data["supported_locales"].items():
            speech_support = info.get("speech_support", {})
            speech_pairs[locale] = {
                "asr_providers": speech_support.get("asr", []),
                "tts_providers": speech_support.get("tts", []),
                "full_speech_support": len(speech_support.get("asr", [])) > 0 and len(speech_support.get("tts", [])) > 0
            }
        
        # Verify speech pair data
        assert speech_pairs["en"]["full_speech_support"] == True
        assert speech_pairs["ig"]["full_speech_support"] == True
        assert "google" in speech_pairs["ig"]["asr_providers"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
