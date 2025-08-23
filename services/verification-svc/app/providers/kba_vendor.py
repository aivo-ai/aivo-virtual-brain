"""
Knowledge-Based Authentication (KBA) Provider for Guardian Identity Verification
COPPA-compliant fallback verification using third-party KBA services
"""

import aiohttp
import structlog
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple, List
from enum import Enum
import asyncio

from app.config import settings
from app.models import KBASession, VerificationStatus
from app.schemas import KBAResponse

logger = structlog.get_logger(__name__)


class KBAProvider(Enum):
    """Supported KBA providers"""
    LEXISNEXIS = "lexisnexis"
    EXPERIAN = "experian"
    ID_ANALYTICS = "idanalytics"
    MOCK = "mock"  # For testing


class KBAQuestionType(Enum):
    """Types of KBA questions"""
    RESIDENCE_HISTORY = "residence_history"
    EMPLOYMENT_HISTORY = "employment_history"
    FINANCIAL_HISTORY = "financial_history"
    EDUCATION_HISTORY = "education_history"
    FAMILY_ASSOCIATES = "family_associates"
    PROPERTY_OWNERSHIP = "property_ownership"


class KBAVendorProvider:
    """Generic KBA provider with vendor-specific implementations"""
    
    def __init__(self):
        self.config = settings.kba_config
        if not self.config:
            logger.warning("KBA provider not configured - fallback verification unavailable")
        else:
            logger.info("KBA provider initialized", 
                       provider=self.config.provider_name,
                       min_score=self.config.min_score_threshold)
    
    @property
    def is_available(self) -> bool:
        """Check if KBA provider is properly configured"""
        return self.config is not None
    
    async def start_kba_session(
        self,
        verification_id: str,
        guardian_user_id: str,
        guardian_info: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[KBAResponse, KBASession]:
        """
        Start KBA verification session with provider
        
        Args:
            verification_id: Verification record ID
            guardian_user_id: Guardian user ID
            guardian_info: Guardian information for KBA (minimal PII)
            metadata: Additional metadata
            
        Returns:
            Tuple of KBAResponse and KBASession record
        """
        if not self.is_available:
            raise ValueError("KBA provider not configured")
        
        # Check geographic eligibility (GDPR compliance)
        country_code = guardian_info.get('country_code', 'US')
        if not self._is_kba_eligible_country(country_code):
            raise ValueError(f"KBA verification not available in {country_code}")
        
        try:
            # Create provider session based on configured provider
            if self.config.provider_name == KBAProvider.MOCK.value:
                return await self._start_mock_session(verification_id, guardian_user_id, guardian_info)
            elif self.config.provider_name == KBAProvider.LEXISNEXIS.value:
                return await self._start_lexisnexis_session(verification_id, guardian_user_id, guardian_info)
            elif self.config.provider_name == KBAProvider.EXPERIAN.value:
                return await self._start_experian_session(verification_id, guardian_user_id, guardian_info)
            else:
                raise ValueError(f"Unsupported KBA provider: {self.config.provider_name}")
        
        except Exception as e:
            logger.error("Failed to start KBA session",
                        error=str(e),
                        verification_id=verification_id,
                        provider=self.config.provider_name)
            raise
    
    async def process_kba_callback(
        self,
        session_id: str,
        callback_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """
        Process KBA completion callback from provider
        
        Args:
            session_id: KBA session ID
            callback_data: Provider callback data
            
        Returns:
            Tuple of (success, verification_id, processed_data)
        """
        try:
            if self.config.provider_name == KBAProvider.MOCK.value:
                return await self._process_mock_callback(session_id, callback_data)
            elif self.config.provider_name == KBAProvider.LEXISNEXIS.value:
                return await self._process_lexisnexis_callback(session_id, callback_data)
            elif self.config.provider_name == KBAProvider.EXPERIAN.value:
                return await self._process_experian_callback(session_id, callback_data)
            else:
                raise ValueError(f"Unsupported KBA provider: {self.config.provider_name}")
        
        except Exception as e:
            logger.error("Failed to process KBA callback",
                        error=str(e),
                        session_id=session_id,
                        provider=self.config.provider_name)
            return False, None, {"error": str(e)}
    
    async def _start_mock_session(
        self,
        verification_id: str,
        guardian_user_id: str,
        guardian_info: Dict[str, Any]
    ) -> Tuple[KBAResponse, KBASession]:
        """Start mock KBA session for testing"""
        
        session_id = f"mock_kba_{verification_id}_{int(datetime.utcnow().timestamp())}"
        
        # Create mock session URL
        session_url = f"https://mock-kba.aivo.local/session/{session_id}"
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        # Create KBA session record
        kba_session = KBASession(
            verification_id=verification_id,
            provider_name="mock",
            provider_session_id=session_id,
            expires_at=expires_at,
            pass_threshold=self.config.min_score_threshold,
            verification_eligible=True
        )
        
        response = KBAResponse(
            session_id=session_id,
            session_url=session_url,
            expires_at=expires_at,
            max_questions=self.config.max_questions
        )
        
        logger.info("Mock KBA session created",
                   verification_id=verification_id,
                   session_id=session_id)
        
        return response, kba_session
    
    async def _start_lexisnexis_session(
        self,
        verification_id: str,
        guardian_user_id: str,
        guardian_info: Dict[str, Any]
    ) -> Tuple[KBAResponse, KBASession]:
        """Start LexisNexis KBA session"""
        
        # Prepare request payload (minimal PII)
        request_payload = {
            "sessionId": f"aivo_{verification_id}",
            "person": {
                "firstName": guardian_info.get('first_name', ''),
                "lastName": guardian_info.get('last_name', ''),
                "address": {
                    "zipCode": guardian_info.get('zip_code', ''),
                    "state": guardian_info.get('state', ''),
                    "city": guardian_info.get('city', '')
                }
            },
            "config": {
                "maxQuestions": self.config.max_questions,
                "scoreThreshold": self.config.min_score_threshold,
                "timeoutMinutes": 30
            }
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "AIVO-Verification-Service/1.0"
            }
            
            async with session.post(
                f"{self.config.api_endpoint}/kba/sessions",
                json=request_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"LexisNexis API error: {response.status} - {error_text}")
                
                result = await response.json()
        
        # Extract session details
        provider_session_id = result.get('sessionId')
        session_url = result.get('sessionUrl')
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        # Create KBA session record
        kba_session = KBASession(
            verification_id=verification_id,
            provider_name="lexisnexis",
            provider_session_id=provider_session_id,
            expires_at=expires_at,
            pass_threshold=self.config.min_score_threshold,
            verification_eligible=True
        )
        
        response = KBAResponse(
            session_id=provider_session_id,
            session_url=session_url,
            expires_at=expires_at,
            max_questions=self.config.max_questions
        )
        
        logger.info("LexisNexis KBA session created",
                   verification_id=verification_id,
                   provider_session_id=provider_session_id)
        
        return response, kba_session
    
    async def _start_experian_session(
        self,
        verification_id: str,
        guardian_user_id: str,
        guardian_info: Dict[str, Any]
    ) -> Tuple[KBAResponse, KBASession]:
        """Start Experian KBA session"""
        
        # Prepare request for Experian API
        request_payload = {
            "requestId": f"aivo_{verification_id}",
            "consumerIdentity": {
                "primaryApplicant": {
                    "name": {
                        "firstName": guardian_info.get('first_name', ''),
                        "lastName": guardian_info.get('last_name', '')
                    },
                    "currentAddress": {
                        "postalCode": guardian_info.get('zip_code', ''),
                        "state": guardian_info.get('state', ''),
                        "city": guardian_info.get('city', '')
                    }
                }
            },
            "preferences": {
                "maxQuestions": self.config.max_questions,
                "scoreThreshold": self.config.min_score_threshold
            }
        }
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Basic {self._encode_experian_auth()}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
            
            async with session.post(
                f"{self.config.api_endpoint}/kba/v1/sessions",
                json=request_payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            ) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise Exception(f"Experian API error: {response.status} - {error_text}")
                
                result = await response.json()
        
        # Extract session details
        provider_session_id = result.get('sessionId')
        session_url = result.get('sessionUrl')
        expires_at = datetime.utcnow() + timedelta(minutes=30)
        
        # Create KBA session record
        kba_session = KBASession(
            verification_id=verification_id,
            provider_name="experian",
            provider_session_id=provider_session_id,
            expires_at=expires_at,
            pass_threshold=self.config.min_score_threshold,
            verification_eligible=True
        )
        
        response = KBAResponse(
            session_id=provider_session_id,
            session_url=session_url,
            expires_at=expires_at,
            max_questions=self.config.max_questions
        )
        
        logger.info("Experian KBA session created",
                   verification_id=verification_id,
                   provider_session_id=provider_session_id)
        
        return response, kba_session
    
    async def _process_mock_callback(
        self,
        session_id: str,
        callback_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Process mock KBA callback"""
        
        # Mock successful verification for testing
        processed_data = {
            "status": "verified",
            "kba_score": 85,
            "questions_answered": 4,
            "correct_answers": 4,
            "passed": True,
            "verification_method": "kba_mock"
        }
        
        # Extract verification_id from session_id (mock format)
        verification_id = session_id.split('_')[2] if '_' in session_id else None
        
        logger.info("Mock KBA verification completed",
                   session_id=session_id,
                   verification_id=verification_id,
                   passed=True)
        
        return True, verification_id, processed_data
    
    async def _process_lexisnexis_callback(
        self,
        session_id: str,
        callback_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Process LexisNexis KBA callback"""
        
        # Extract verification results
        score = callback_data.get('score', 0)
        questions_answered = callback_data.get('questionsAnswered', 0)
        correct_answers = callback_data.get('correctAnswers', 0)
        passed = score >= self.config.min_score_threshold
        
        processed_data = {
            "status": "verified" if passed else "failed",
            "kba_score": score,
            "questions_answered": questions_answered,
            "correct_answers": correct_answers,
            "passed": passed,
            "verification_method": "kba_lexisnexis",
            "failure_reason": "kba_failed" if not passed else None
        }
        
        # Get verification_id from session metadata
        verification_id = callback_data.get('metadata', {}).get('verification_id')
        
        logger.info("LexisNexis KBA verification completed",
                   session_id=session_id,
                   verification_id=verification_id,
                   score=score,
                   passed=passed)
        
        return True, verification_id, processed_data
    
    async def _process_experian_callback(
        self,
        session_id: str,
        callback_data: Dict[str, Any]
    ) -> Tuple[bool, Optional[str], Dict[str, Any]]:
        """Process Experian KBA callback"""
        
        # Extract verification results
        result = callback_data.get('result', {})
        score = result.get('score', 0)
        questions_answered = result.get('questionsAnswered', 0)
        correct_answers = result.get('correctAnswers', 0)
        passed = score >= self.config.min_score_threshold
        
        processed_data = {
            "status": "verified" if passed else "failed",
            "kba_score": score,
            "questions_answered": questions_answered,
            "correct_answers": correct_answers,
            "passed": passed,
            "verification_method": "kba_experian",
            "failure_reason": "kba_failed" if not passed else None
        }
        
        # Get verification_id from session metadata
        verification_id = callback_data.get('requestId', '').replace('aivo_', '')
        
        logger.info("Experian KBA verification completed",
                   session_id=session_id,
                   verification_id=verification_id,
                   score=score,
                   passed=passed)
        
        return True, verification_id, processed_data
    
    def _is_kba_eligible_country(self, country_code: str) -> bool:
        """Check if KBA is available for the given country"""
        # KBA typically available in US, CA, UK, AU
        eligible_countries = ["US", "CA", "UK", "AU", "NZ"]
        
        # EU countries may have restrictions under GDPR
        if settings.is_eu_country(country_code):
            logger.warning("KBA verification may have GDPR restrictions", country=country_code)
            return False
        
        return country_code.upper() in eligible_countries
    
    def _encode_experian_auth(self) -> str:
        """Encode Experian basic auth credentials"""
        import base64
        credentials = f"{self.config.username}:{self.config.password}"
        return base64.b64encode(credentials.encode()).decode()
    
    async def get_session_status(
        self,
        provider_session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get KBA session status from provider"""
        try:
            if self.config.provider_name == KBAProvider.MOCK.value:
                return {"status": "completed", "score": 85, "passed": True}
            
            # For real providers, query their status endpoint
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.config.api_key}"}
                
                async with session.get(
                    f"{self.config.api_endpoint}/kba/sessions/{provider_session_id}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning("Failed to get KBA session status",
                                     session_id=provider_session_id,
                                     status=response.status)
                        return None
        
        except Exception as e:
            logger.error("Error getting KBA session status",
                        session_id=provider_session_id,
                        error=str(e))
            return None


# Global provider instance
kba_vendor_provider = KBAVendorProvider()
