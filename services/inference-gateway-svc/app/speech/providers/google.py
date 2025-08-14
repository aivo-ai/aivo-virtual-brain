"""
Google Cloud Speech Provider
Handles ASR (Automatic Speech Recognition) and TTS (Text-to-Speech) via Google Cloud Speech Services.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
import json
import aiohttp
import base64
from datetime import datetime, timedelta

from ..base import SpeechProvider, SpeechResult, SpeechError
from ..config import SpeechConfig


logger = logging.getLogger(__name__)


class GoogleSpeechProvider(SpeechProvider):
    """Google Cloud Speech provider implementation."""
    
    def __init__(self, config: SpeechConfig):
        super().__init__(config)
        self.provider_name = "google"
        self.api_key = config.get_provider_config("google", "api_key")
        self.project_id = config.get_provider_config("google", "project_id")
        
        # Google Cloud endpoints
        self.stt_url = "https://speech.googleapis.com/v1/speech:recognize"
        self.tts_url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        
        # Google-specific locale mappings
        self.locale_mappings = {
            "en": "en-US",
            "es": "es-ES",
            "fr": "fr-FR", 
            "ar": "ar-SA",
            "zh-Hans": "zh-CN",
            "hi": "hi-IN",
            "pt": "pt-BR",
            "ig": "ig-NG",
            "yo": "yo-NG", 
            "ha": "ha-NG",
            "sw": "sw-KE"
        }
        
        # Voice mappings for TTS
        self.voice_mappings = {
            "en": {"name": "en-US-Wavenet-D", "gender": "MALE"},
            "es": {"name": "es-ES-Wavenet-B", "gender": "MALE"},
            "fr": {"name": "fr-FR-Wavenet-B", "gender": "MALE"},
            "ar": {"name": "ar-XA-Wavenet-A", "gender": "FEMALE"},
            "zh-Hans": {"name": "zh-CN-Wavenet-A", "gender": "FEMALE"},
            "hi": {"name": "hi-IN-Wavenet-A", "gender": "FEMALE"},
            "pt": {"name": "pt-BR-Wavenet-A", "gender": "FEMALE"},
            "ig": {"name": "ig-NG-Standard-A", "gender": "FEMALE"},
            "yo": {"name": "yo-NG-Standard-A", "gender": "FEMALE"},
            "ha": {"name": "ha-NG-Standard-A", "gender": "FEMALE"},
            "sw": {"name": "sw-KE-Standard-A", "gender": "FEMALE"}
        }
        
        # Rate limiting
        self.rate_limiter = {
            "asr": {"requests": 15, "window": 60, "current": 0, "reset_time": None},
            "tts": {"requests": 30, "window": 60, "current": 0, "reset_time": None}
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
            logger.warning(f"Google {operation} rate limit exceeded")
            return False
            
        limiter["current"] += 1
        return True
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        locale: str = "en",
        format: str = "wav",
        **kwargs
    ) -> SpeechResult:
        """Transcribe audio using Google Cloud Speech-to-Text."""
        
        if not await self._check_rate_limit("asr"):
            raise SpeechError("Rate limit exceeded for Google ASR")
        
        # Map locale to Google format
        google_locale = self.locale_mappings.get(locale, "en-US")
        
        # Encode audio to base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Prepare request payload
        payload = {
            "config": {
                "encoding": "WEBM_OPUS" if format == "webm" else "LINEAR16",
                "sampleRateHertz": kwargs.get("sample_rate", 16000),
                "languageCode": google_locale,
                "enableAutomaticPunctuation": True,
                "enableWordTimeOffsets": True,
                "model": "latest_long"
            },
            "audio": {
                "content": audio_base64
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.stt_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    
                    response_data = await response.json()
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    if response.status == 200:
                        # Parse Google response
                        results = response_data.get("results", [])
                        if results and "alternatives" in results[0]:
                            best_alternative = results[0]["alternatives"][0]
                            transcript = best_alternative.get("transcript", "")
                            confidence = best_alternative.get("confidence", 0.0)
                            
                            # Extract word timings if available
                            words = best_alternative.get("words", [])
                            word_timings = [
                                {
                                    "word": word.get("word"),
                                    "start_time": word.get("startTime", "0s"),
                                    "end_time": word.get("endTime", "0s")
                                }
                                for word in words
                            ]
                        else:
                            transcript = ""
                            confidence = 0.0
                            word_timings = []
                        
                        return SpeechResult(
                            provider=self.provider_name,
                            operation="asr",
                            text=transcript,
                            confidence=confidence,
                            locale=locale,
                            processing_time=processing_time,
                            metadata={
                                "google_locale": google_locale,
                                "word_timings": word_timings,
                                "raw_response": response_data,
                                "format": format
                            }
                        )
                    else:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        raise SpeechError(f"Google ASR failed: {error_msg}")
                        
        except asyncio.TimeoutError:
            raise SpeechError("Google ASR request timed out")
        except aiohttp.ClientError as e:
            raise SpeechError(f"Google ASR network error: {e}")
        except Exception as e:
            logger.error(f"Google ASR error: {e}")
            raise SpeechError(f"Google ASR processing error: {e}")
    
    async def synthesize_speech(
        self,
        text: str,
        locale: str = "en",
        voice: Optional[str] = None,
        **kwargs
    ) -> SpeechResult:
        """Synthesize speech using Google Cloud Text-to-Speech."""
        
        if not await self._check_rate_limit("tts"):
            raise SpeechError("Rate limit exceeded for Google TTS")
        
        # Map locale to Google format
        google_locale = self.locale_mappings.get(locale, "en-US")
        
        # Get voice configuration
        voice_config = self.voice_mappings.get(locale, self.voice_mappings["en"])
        voice_name = voice or voice_config["name"]
        
        # Prepare request payload
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": google_locale,
                "name": voice_name,
                "ssmlGender": voice_config["gender"]
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": kwargs.get("speaking_rate", 1.0),
                "pitch": kwargs.get("pitch", 0.0),
                "volumeGainDb": kwargs.get("volume_gain", 0.0)
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.api_key
        }
        
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.tts_url,
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    
                    response_data = await response.json()
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    if response.status == 200:
                        # Decode base64 audio content
                        audio_base64 = response_data.get("audioContent", "")
                        audio_data = base64.b64decode(audio_base64)
                        
                        return SpeechResult(
                            provider=self.provider_name,
                            operation="tts",
                            text=text,
                            audio_data=audio_data,
                            locale=locale,
                            processing_time=processing_time,
                            metadata={
                                "google_locale": google_locale,
                                "voice_name": voice_name,
                                "voice_gender": voice_config["gender"],
                                "format": "mp3",
                                "audio_config": payload["audioConfig"]
                            }
                        )
                    else:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        raise SpeechError(f"Google TTS failed: {error_msg}")
                        
        except asyncio.TimeoutError:
            raise SpeechError("Google TTS request timed out")
        except aiohttp.ClientError as e:
            raise SpeechError(f"Google TTS network error: {e}")
        except Exception as e:
            logger.error(f"Google TTS error: {e}")
            raise SpeechError(f"Google TTS processing error: {e}")
    
    async def get_supported_locales(self) -> List[str]:
        """Get list of supported locales for this provider."""
        return list(self.locale_mappings.keys())
    
    async def get_available_voices(self, locale: str) -> List[Dict[str, Any]]:
        """Get available voices for a locale."""
        voices_url = "https://texttospeech.googleapis.com/v1/voices"
        headers = {"X-goog-api-key": self.api_key}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(voices_url, headers=headers) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        voices = response_data.get("voices", [])
                        google_locale = self.locale_mappings.get(locale, "en-US")
                        
                        # Filter voices by locale
                        filtered_voices = []
                        for voice in voices:
                            if google_locale in voice.get("languageCodes", []):
                                filtered_voices.append({
                                    "name": voice["name"],
                                    "gender": voice["ssmlGender"],
                                    "language_codes": voice["languageCodes"],
                                    "natural_sample_rate": voice["naturalSampleRateHertz"]
                                })
                        
                        return filtered_voices
                    else:
                        logger.warning(f"Failed to get Google voices: {response.status}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error getting Google voices: {e}")
            return []
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Google Cloud Speech Services health."""
        try:
            # Test voices endpoint (lightweight health check)
            voices = await self.get_available_voices("en")
            voices_available = len(voices) > 0
            
            # Test small TTS request
            test_result = None
            try:
                test_result = await self.synthesize_speech("Test", "en")
                tts_working = test_result is not None and test_result.audio_data is not None
            except:
                tts_working = False
            
            status = "healthy" if voices_available and tts_working else "degraded"
            
            return {
                "provider": self.provider_name,
                "status": status,
                "capabilities": ["asr", "tts"],
                "supported_locales": await self.get_supported_locales(),
                "rate_limits": {
                    "asr": f"{self.rate_limiter['asr']['current']}/{self.rate_limiter['asr']['requests']}",
                    "tts": f"{self.rate_limiter['tts']['current']}/{self.rate_limiter['tts']['requests']}"
                },
                "checks": {
                    "voices_endpoint": voices_available,
                    "tts_synthesis": tts_working,
                    "api_key_valid": len(self.api_key) > 0
                },
                "extended_locale_support": ["ig", "yo", "ha", "sw"],
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Google health check failed: {e}")
            return {
                "provider": self.provider_name,
                "status": "unhealthy",
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
