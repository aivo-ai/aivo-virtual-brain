"""
Azure Cognitive Services Speech Provider
Handles ASR (Automatic Speech Recognition) and TTS (Text-to-Speech) via Azure Speech Services.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
import json
import aiohttp
from datetime import datetime, timedelta

from ..base import SpeechProvider, SpeechResult, SpeechError
from ..config import SpeechConfig


logger = logging.getLogger(__name__)


class AzureSpeechProvider(SpeechProvider):
    """Azure Cognitive Services speech provider implementation."""
    
    def __init__(self, config: SpeechConfig):
        super().__init__(config)
        self.provider_name = "azure"
        self.subscription_key = config.get_provider_config("azure", "subscription_key")
        self.region = config.get_provider_config("azure", "region", "eastus")
        self.base_url = f"https://{self.region}.api.cognitive.microsoft.com"
        
        # Azure-specific locale mappings
        self.locale_mappings = {
            "en": "en-US",
            "es": "es-ES", 
            "fr": "fr-FR",
            "ar": "ar-SA",
            "zh-Hans": "zh-CN",
            "hi": "hi-IN",
            "pt": "pt-BR"
        }
        
        # Voice mappings for TTS
        self.voice_mappings = {
            "en": "en-US-AriaNeural",
            "es": "es-ES-ElviraNeural",
            "fr": "fr-FR-DeniseNeural", 
            "ar": "ar-SA-ZariyahNeural",
            "zh-Hans": "zh-CN-XiaoxiaoNeural",
            "hi": "hi-IN-SwaraNeural",
            "pt": "pt-BR-FranciscaNeural"
        }
        
        # Rate limiting
        self.rate_limiter = {
            "asr": {"requests": 20, "window": 60, "current": 0, "reset_time": None},
            "tts": {"requests": 50, "window": 60, "current": 0, "reset_time": None}
        }
    
    async def _check_rate_limit(self, operation: str) -> bool:
        """Check if request is within rate limits."""
        limiter = self.rate_limiter.get(operation)
        if not limiter:
            return True
            
        now = datetime.utcnow()
        
        # Reset counter if window expired
        if limiter["reset_time"] is None or now > limiter["reset_time"]:
            limiter["current"] = 0
            limiter["reset_time"] = now + timedelta(seconds=limiter["window"])
        
        if limiter["current"] >= limiter["requests"]:
            logger.warning(f"Azure {operation} rate limit exceeded")
            return False
            
        limiter["current"] += 1
        return True
    
    async def _get_access_token(self) -> str:
        """Get Azure Cognitive Services access token."""
        token_url = f"https://{self.region}.api.cognitive.microsoft.com/sts/v1.0/issuetoken"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, headers=headers) as response:
                if response.status == 200:
                    token = await response.text()
                    return token.strip()
                else:
                    error_text = await response.text()
                    raise SpeechError(f"Failed to get Azure token: {error_text}")
    
    async def transcribe_audio(
        self, 
        audio_data: bytes, 
        locale: str = "en",
        format: str = "wav",
        **kwargs
    ) -> SpeechResult:
        """Transcribe audio using Azure Speech-to-Text."""
        
        if not await self._check_rate_limit("asr"):
            raise SpeechError("Rate limit exceeded for Azure ASR")
        
        # Map locale to Azure format
        azure_locale = self.locale_mappings.get(locale, "en-US")
        
        # Get access token
        try:
            access_token = await self._get_access_token()
        except Exception as e:
            logger.error(f"Azure token error: {e}")
            raise SpeechError(f"Authentication failed: {e}")
        
        # Prepare request
        stt_url = f"{self.base_url}/speechtotext/v3.0/transcriptions"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": f"audio/{format}",
            "Accept": "application/json"
        }
        
        params = {
            "language": azure_locale,
            "format": "detailed"
        }
        
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    stt_url, 
                    headers=headers, 
                    params=params,
                    data=audio_data,
                    timeout=30
                ) as response:
                    
                    response_data = await response.json()
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    if response.status == 200:
                        # Parse Azure response
                        if "NBest" in response_data and len(response_data["NBest"]) > 0:
                            best_result = response_data["NBest"][0]
                            transcript = best_result.get("Display", "")
                            confidence = best_result.get("Confidence", 0.0)
                        else:
                            transcript = response_data.get("DisplayText", "")
                            confidence = response_data.get("Confidence", 0.0)
                        
                        return SpeechResult(
                            provider=self.provider_name,
                            operation="asr",
                            text=transcript,
                            confidence=confidence,
                            locale=locale,
                            processing_time=processing_time,
                            metadata={
                                "azure_locale": azure_locale,
                                "raw_response": response_data,
                                "format": format
                            }
                        )
                    else:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        raise SpeechError(f"Azure ASR failed: {error_msg}")
                        
        except asyncio.TimeoutError:
            raise SpeechError("Azure ASR request timed out")
        except aiohttp.ClientError as e:
            raise SpeechError(f"Azure ASR network error: {e}")
        except Exception as e:
            logger.error(f"Azure ASR error: {e}")
            raise SpeechError(f"Azure ASR processing error: {e}")
    
    async def synthesize_speech(
        self,
        text: str,
        locale: str = "en", 
        voice: Optional[str] = None,
        **kwargs
    ) -> SpeechResult:
        """Synthesize speech using Azure Text-to-Speech."""
        
        if not await self._check_rate_limit("tts"):
            raise SpeechError("Rate limit exceeded for Azure TTS")
        
        # Map locale to Azure format
        azure_locale = self.locale_mappings.get(locale, "en-US")
        voice_name = voice or self.voice_mappings.get(locale, "en-US-AriaNeural")
        
        # Get access token
        try:
            access_token = await self._get_access_token()
        except Exception as e:
            logger.error(f"Azure token error: {e}")
            raise SpeechError(f"Authentication failed: {e}")
        
        # Create SSML
        ssml = f"""
        <speak version='1.0' xml:lang='{azure_locale}'>
            <voice xml:lang='{azure_locale}' name='{voice_name}'>
                {text}
            </voice>
        </speak>
        """
        
        # Prepare request
        tts_url = f"{self.base_url}/cognitiveservices/v1"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm"
        }
        
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    tts_url,
                    headers=headers,
                    data=ssml.encode('utf-8'),
                    timeout=30
                ) as response:
                    
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    if response.status == 200:
                        audio_data = await response.read()
                        
                        return SpeechResult(
                            provider=self.provider_name,
                            operation="tts",
                            text=text,
                            audio_data=audio_data,
                            locale=locale,
                            processing_time=processing_time,
                            metadata={
                                "azure_locale": azure_locale,
                                "voice_name": voice_name,
                                "format": "wav",
                                "ssml_used": True
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise SpeechError(f"Azure TTS failed: {error_text}")
                        
        except asyncio.TimeoutError:
            raise SpeechError("Azure TTS request timed out")
        except aiohttp.ClientError as e:
            raise SpeechError(f"Azure TTS network error: {e}")
        except Exception as e:
            logger.error(f"Azure TTS error: {e}")
            raise SpeechError(f"Azure TTS processing error: {e}")
    
    async def get_supported_locales(self) -> List[str]:
        """Get list of supported locales for this provider."""
        return list(self.locale_mappings.keys())
    
    async def get_available_voices(self, locale: str) -> List[Dict[str, Any]]:
        """Get available voices for a locale."""
        voices_url = f"{self.base_url}/cognitiveservices/voices/list"
        
        try:
            access_token = await self._get_access_token()
            headers = {"Authorization": f"Bearer {access_token}"}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(voices_url, headers=headers) as response:
                    if response.status == 200:
                        voices = await response.json()
                        azure_locale = self.locale_mappings.get(locale, "en-US")
                        
                        # Filter voices by locale
                        filtered_voices = [
                            {
                                "name": voice["Name"],
                                "display_name": voice["DisplayName"], 
                                "gender": voice["Gender"],
                                "locale": voice["Locale"],
                                "voice_type": voice.get("VoiceType", "Neural")
                            }
                            for voice in voices
                            if voice["Locale"].startswith(azure_locale[:2])
                        ]
                        
                        return filtered_voices
                    else:
                        logger.warning(f"Failed to get Azure voices: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting Azure voices: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Azure Speech Services health."""
        try:
            # Test token acquisition
            token = await self._get_access_token()
            token_valid = len(token) > 0
            
            # Test voices endpoint
            voices = await self.get_available_voices("en")
            voices_available = len(voices) > 0
            
            return {
                "provider": self.provider_name,
                "status": "healthy" if token_valid and voices_available else "degraded",
                "capabilities": ["asr", "tts"],
                "supported_locales": await self.get_supported_locales(),
                "rate_limits": {
                    "asr": f"{self.rate_limiter['asr']['current']}/{self.rate_limiter['asr']['requests']}",
                    "tts": f"{self.rate_limiter['tts']['current']}/{self.rate_limiter['tts']['requests']}"
                },
                "checks": {
                    "authentication": token_valid,
                    "voices_endpoint": voices_available
                },
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Azure health check failed: {e}")
            return {
                "provider": self.provider_name,
                "status": "unhealthy",
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
