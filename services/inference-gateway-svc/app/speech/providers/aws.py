"""
AWS Speech Provider
Handles ASR (Automatic Speech Recognition) and TTS (Text-to-Speech) via AWS Transcribe and Polly.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
import json
import aiohttp
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from urllib.parse import quote

from ..base import SpeechProvider, SpeechResult, SpeechError
from ..config import SpeechConfig


logger = logging.getLogger(__name__)


class AWSSpeechProvider(SpeechProvider):
    """AWS Transcribe/Polly speech provider implementation."""
    
    def __init__(self, config: SpeechConfig):
        super().__init__(config)
        self.provider_name = "aws"
        self.access_key_id = config.get_provider_config("aws", "access_key_id")
        self.secret_access_key = config.get_provider_config("aws", "secret_access_key")
        self.region = config.get_provider_config("aws", "region", "us-east-1")
        
        # AWS service endpoints
        self.transcribe_url = f"https://transcribe.{self.region}.amazonaws.com"
        self.polly_url = f"https://polly.{self.region}.amazonaws.com"
        
        # AWS-specific locale mappings
        self.locale_mappings = {
            "en": "en-US",
            "es": "es-ES",
            "fr": "fr-FR",
            "zh-Hans": "zh-CN",
            "pt": "pt-BR"
        }
        
        # Voice mappings for Polly TTS
        self.voice_mappings = {
            "en": "Joanna",
            "es": "Conchita",
            "fr": "Celine",
            "zh-Hans": "Zhiyu",
            "pt": "Camila"
        }
        
        # Rate limiting
        self.rate_limiter = {
            "asr": {"requests": 10, "window": 60, "current": 0, "reset_time": None},
            "tts": {"requests": 25, "window": 60, "current": 0, "reset_time": None}
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
            logger.warning(f"AWS {operation} rate limit exceeded")
            return False
            
        limiter["current"] += 1
        return True
    
    def _sign_aws_request(self, method: str, url: str, payload: str, service: str) -> Dict[str, str]:
        """Sign AWS API request using AWS Signature Version 4."""
        
        # Parse URL components
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        host = parsed_url.hostname
        canonical_uri = parsed_url.path or '/'
        canonical_querystring = parsed_url.query or ''
        
        # Create timestamp
        t = datetime.utcnow()
        amzdate = t.strftime('%Y%m%dT%H%M%SZ')
        datestamp = t.strftime('%Y%m%d')
        
        # Create canonical headers
        canonical_headers = f'host:{host}\n'
        canonical_headers += f'x-amz-date:{amzdate}\n'
        signed_headers = 'host;x-amz-date'
        
        # Create payload hash
        payload_hash = hashlib.sha256(payload.encode('utf-8')).hexdigest()
        
        # Create canonical request
        canonical_request = f'{method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
        
        # Create string to sign
        algorithm = 'AWS4-HMAC-SHA256'
        credential_scope = f'{datestamp}/{self.region}/{service}/aws4_request'
        string_to_sign = f'{algorithm}\n{amzdate}\n{credential_scope}\n{hashlib.sha256(canonical_request.encode()).hexdigest()}'
        
        # Calculate signature
        signing_key = self._get_signature_key(self.secret_access_key, datestamp, self.region, service)
        signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()
        
        # Create authorization header
        authorization_header = f'{algorithm} Credential={self.access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'
        
        return {
            'Authorization': authorization_header,
            'X-Amz-Date': amzdate,
            'Host': host
        }
    
    def _get_signature_key(self, key: str, date_stamp: str, region_name: str, service_name: str) -> bytes:
        """Generate AWS signature key."""
        k_date = hmac.new(('AWS4' + key).encode('utf-8'), date_stamp.encode('utf-8'), hashlib.sha256).digest()
        k_region = hmac.new(k_date, region_name.encode('utf-8'), hashlib.sha256).digest()
        k_service = hmac.new(k_region, service_name.encode('utf-8'), hashlib.sha256).digest()
        k_signing = hmac.new(k_service, b'aws4_request', hashlib.sha256).digest()
        return k_signing
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        locale: str = "en",
        format: str = "wav",
        **kwargs
    ) -> SpeechResult:
        """Transcribe audio using AWS Transcribe."""
        
        if not await self._check_rate_limit("asr"):
            raise SpeechError("Rate limit exceeded for AWS ASR")
        
        # AWS Transcribe requires S3 upload for real-time transcription
        # For this implementation, we'll use the streaming API simulation
        aws_locale = self.locale_mappings.get(locale, "en-US")
        
        # Create transcription job payload
        job_name = f"aivo-transcription-{int(datetime.utcnow().timestamp())}"
        
        payload = {
            "TranscriptionJobName": job_name,
            "LanguageCode": aws_locale,
            "Media": {
                "MediaFileUri": "s3://temp-bucket/audio-file"  # Would be real S3 URI
            },
            "MediaFormat": format.upper(),
            "Settings": {
                "ShowSpeakerLabels": False,
                "MaxSpeakerLabels": 2
            }
        }
        
        # Sign the request
        url = f"{self.transcribe_url}/"
        headers = self._sign_aws_request("POST", url, json.dumps(payload), "transcribe")
        headers['Content-Type'] = 'application/x-amz-json-1.1'
        headers['X-Amz-Target'] = 'Transcribe.StartTranscriptionJob'
        
        start_time = datetime.utcnow()
        
        try:
            # For demo purposes, simulate AWS Transcribe response
            # In production, this would make actual AWS API calls
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Simulate transcription result
            transcript = "This is a simulated AWS Transcribe result for demonstration."
            confidence = 0.85
            
            return SpeechResult(
                provider=self.provider_name,
                operation="asr",
                text=transcript,
                confidence=confidence,
                locale=locale,
                processing_time=processing_time,
                metadata={
                    "aws_locale": aws_locale,
                    "job_name": job_name,
                    "format": format,
                    "simulated": True,
                    "note": "Production implementation requires S3 integration"
                }
            )
            
        except Exception as e:
            logger.error(f"AWS ASR error: {e}")
            raise SpeechError(f"AWS ASR processing error: {e}")
    
    async def synthesize_speech(
        self,
        text: str,
        locale: str = "en",
        voice: Optional[str] = None,
        **kwargs
    ) -> SpeechResult:
        """Synthesize speech using AWS Polly."""
        
        if not await self._check_rate_limit("tts"):
            raise SpeechError("Rate limit exceeded for AWS TTS")
        
        # Map locale to AWS format
        aws_locale = self.locale_mappings.get(locale, "en-US")
        voice_id = voice or self.voice_mappings.get(locale, "Joanna")
        
        # Create Polly synthesis payload
        payload = {
            "Text": text,
            "VoiceId": voice_id,
            "OutputFormat": "mp3",
            "TextType": "text",
            "LanguageCode": aws_locale
        }
        
        # Sign the request
        url = f"{self.polly_url}/v1/speech"
        headers = self._sign_aws_request("POST", url, json.dumps(payload), "polly")
        headers['Content-Type'] = 'application/x-amz-json-1.1'
        
        start_time = datetime.utcnow()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=30
                ) as response:
                    
                    processing_time = (datetime.utcnow() - start_time).total_seconds()
                    
                    if response.status == 200:
                        # For demo, create minimal audio data
                        # In production, this would be the actual Polly audio response
                        audio_data = b"AWS Polly audio data placeholder"
                        
                        return SpeechResult(
                            provider=self.provider_name,
                            operation="tts",
                            text=text,
                            audio_data=audio_data,
                            locale=locale,
                            processing_time=processing_time,
                            metadata={
                                "aws_locale": aws_locale,
                                "voice_id": voice_id,
                                "format": "mp3",
                                "simulated": True,
                                "note": "Demo implementation with placeholder audio"
                            }
                        )
                    else:
                        error_text = await response.text()
                        raise SpeechError(f"AWS TTS failed: {error_text}")
                        
        except asyncio.TimeoutError:
            raise SpeechError("AWS TTS request timed out")
        except aiohttp.ClientError as e:
            raise SpeechError(f"AWS TTS network error: {e}")
        except Exception as e:
            logger.error(f"AWS TTS error: {e}")
            raise SpeechError(f"AWS TTS processing error: {e}")
    
    async def get_supported_locales(self) -> List[str]:
        """Get list of supported locales for this provider."""
        return list(self.locale_mappings.keys())
    
    async def get_available_voices(self, locale: str) -> List[Dict[str, Any]]:
        """Get available voices for a locale."""
        
        # AWS Polly voices mapping
        voices_by_locale = {
            "en": [
                {"name": "Joanna", "gender": "Female", "language": "en-US"},
                {"name": "Matthew", "gender": "Male", "language": "en-US"},
                {"name": "Amy", "gender": "Female", "language": "en-GB"},
                {"name": "Brian", "gender": "Male", "language": "en-GB"}
            ],
            "es": [
                {"name": "Conchita", "gender": "Female", "language": "es-ES"},
                {"name": "Enrique", "gender": "Male", "language": "es-ES"},
                {"name": "Penelope", "gender": "Female", "language": "es-US"}
            ],
            "fr": [
                {"name": "Celine", "gender": "Female", "language": "fr-FR"},
                {"name": "Mathieu", "gender": "Male", "language": "fr-FR"}
            ],
            "zh-Hans": [
                {"name": "Zhiyu", "gender": "Female", "language": "zh-CN"}
            ],
            "pt": [
                {"name": "Camila", "gender": "Female", "language": "pt-BR"},
                {"name": "Ricardo", "gender": "Male", "language": "pt-BR"}
            ]
        }
        
        return voices_by_locale.get(locale, [])
    
    async def health_check(self) -> Dict[str, Any]:
        """Check AWS Speech Services health."""
        try:
            # Test credentials and basic connectivity
            credentials_valid = len(self.access_key_id) > 0 and len(self.secret_access_key) > 0
            
            # Test voice availability
            voices = await self.get_available_voices("en")
            voices_available = len(voices) > 0
            
            # Test basic TTS functionality (simulated)
            tts_working = True  # Would test actual Polly synthesis
            
            status = "healthy" if credentials_valid and voices_available and tts_working else "degraded"
            
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
                    "credentials": credentials_valid,
                    "voices_available": voices_available,
                    "tts_synthesis": tts_working,
                    "region": self.region
                },
                "notes": "Demo implementation with simulated responses",
                "last_checked": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"AWS health check failed: {e}")
            return {
                "provider": self.provider_name,
                "status": "unhealthy",
                "error": str(e),
                "last_checked": datetime.utcnow().isoformat()
            }
