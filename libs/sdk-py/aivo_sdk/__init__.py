"""
AIVO Python SDK - Main Entry Point
S1-15 Contract & SDK Integration
"""

from typing import Optional, Dict, Any
import httpx
from pydantic import BaseModel

from .auth import AuthClient
from .user import UserClient
from .base import BaseClient


class SDKConfig(BaseModel):
    """SDK Configuration"""
    base_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    timeout: int = 30
    retries: int = 3
    

class AivoSDK:
    """Main AIVO SDK Client"""
    
    def __init__(self, config: Optional[SDKConfig] = None):
        self.config = config or SDKConfig()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=self.config.timeout
        )
        
        # Initialize service clients
        self.auth = AuthClient(self._client, self.config)
        self.user = UserClient(self._client, self.config)
        
        # Placeholder clients for new services
        # These will be generated from OpenAPI specs
        self._assessment_client = None
        self._learner_client = None
        self._notification_client = None
        self._search_client = None
        self._orchestrator_client = None
        
    async def __aenter__(self):
        """Async context manager entry"""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self._client.aclose()
        
    @property 
    def assessment(self):
        """Assessment service client"""
        if not self._assessment_client:
            # Will be replaced with generated client
            from .clients.assessment import AssessmentClient
            self._assessment_client = AssessmentClient(self._client, self.config)
        return self._assessment_client
        
    @property
    def learner(self):
        """Learner service client"""
        if not self._learner_client:
            # Will be replaced with generated client
            from .clients.learner import LearnerClient
            self._learner_client = LearnerClient(self._client, self.config)
        return self._learner_client
        
    @property
    def notification(self):
        """Notification service client"""
        if not self._notification_client:
            # Will be replaced with generated client
            from .clients.notification import NotificationClient
            self._notification_client = NotificationClient(self._client, self.config)
        return self._notification_client
        
    @property
    def search(self):
        """Search service client"""
        if not self._search_client:
            # Will be replaced with generated client
            from .clients.search import SearchClient
            self._search_client = SearchClient(self._client, self.config)
        return self._search_client
        
    @property
    def orchestrator(self):
        """Orchestrator service client"""
        if not self._orchestrator_client:
            # Will be replaced with generated client
            from .clients.orchestrator import OrchestratorClient
            self._orchestrator_client = OrchestratorClient(self._client, self.config)
        return self._orchestrator_client


# Export main classes
__all__ = [
    'AivoSDK',
    'SDKConfig',
    'AuthClient',
    'UserClient',
]
