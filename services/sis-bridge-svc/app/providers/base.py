"""
Base SIS Provider Interface

Abstract base class defining the interface for SIS providers.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass


@dataclass
class SISUser:
    """SIS User representation."""
    id: str
    username: str
    email: str
    first_name: str
    last_name: str
    role: str  # student, teacher, admin
    active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    external_data: Optional[Dict[str, Any]] = None


@dataclass
class SISGroup:
    """SIS Group/Section representation."""
    id: str
    name: str
    description: Optional[str] = None
    subject: Optional[str] = None
    grade: Optional[str] = None
    school_id: Optional[str] = None
    teacher_ids: Optional[List[str]] = None
    student_ids: Optional[List[str]] = None
    active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    external_data: Optional[Dict[str, Any]] = None


@dataclass
class SISEnrollment:
    """SIS Enrollment representation."""
    id: str
    user_id: str
    group_id: str
    role: str  # student, teacher
    status: str  # active, inactive
    enrolled_at: Optional[datetime] = None
    external_data: Optional[Dict[str, Any]] = None


class BaseSISProvider(ABC):
    """Abstract base class for SIS providers."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        self.config = config
        self.name = config.get('name', 'Unknown Provider')
        self.base_url = config.get('base_url')
        self.api_key = config.get('api_key')
        self.client_id = config.get('client_id')
        self.client_secret = config.get('client_secret')
    
    @abstractmethod
    async def authenticate(self) -> bool:
        """
        Authenticate with the SIS provider.
        
        Returns:
            True if authentication successful
        """
        pass
    
    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to SIS provider.
        
        Returns:
            Connection test results
        """
        pass
    
    @abstractmethod
    async def get_users(
        self, 
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISUser, None]:
        """
        Get users from SIS provider.
        
        Args:
            limit: Maximum number of users to fetch
            offset: Offset for pagination
            updated_since: Only fetch users updated since this date
        
        Yields:
            SISUser objects
        """
        pass
    
    @abstractmethod
    async def get_user(self, user_id: str) -> Optional[SISUser]:
        """
        Get specific user by ID.
        
        Args:
            user_id: SIS user ID
        
        Returns:
            SISUser object or None if not found
        """
        pass
    
    @abstractmethod
    async def get_groups(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISGroup, None]:
        """
        Get groups/sections from SIS provider.
        
        Args:
            limit: Maximum number of groups to fetch
            offset: Offset for pagination
            updated_since: Only fetch groups updated since this date
        
        Yields:
            SISGroup objects
        """
        pass
    
    @abstractmethod
    async def get_group(self, group_id: str) -> Optional[SISGroup]:
        """
        Get specific group by ID.
        
        Args:
            group_id: SIS group ID
        
        Returns:
            SISGroup object or None if not found
        """
        pass
    
    @abstractmethod
    async def get_enrollments(
        self,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISEnrollment, None]:
        """
        Get enrollments from SIS provider.
        
        Args:
            user_id: Filter by specific user
            group_id: Filter by specific group
            limit: Maximum number of enrollments to fetch
            offset: Offset for pagination
            updated_since: Only fetch enrollments updated since this date
        
        Yields:
            SISEnrollment objects
        """
        pass
    
    @abstractmethod
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """
        Handle webhook event from SIS provider.
        
        Args:
            event_type: Type of webhook event
            payload: Webhook payload
        
        Returns:
            List of resource IDs that need to be synced
        """
        pass
    
    def get_rate_limit_info(self) -> Dict[str, Any]:
        """
        Get rate limit information for this provider.
        
        Returns:
            Rate limit configuration
        """
        return {
            "requests_per_second": getattr(self, 'requests_per_second', 10),
            "requests_per_minute": getattr(self, 'requests_per_minute', 600),
            "requests_per_hour": getattr(self, 'requests_per_hour', 36000)
        }
    
    def get_supported_features(self) -> Dict[str, bool]:
        """
        Get supported features for this provider.
        
        Returns:
            Feature support mapping
        """
        return {
            "users": True,
            "groups": True,
            "enrollments": True,
            "webhooks": False,
            "incremental_sync": False,
            "real_time_updates": False
        }
    
    async def cleanup(self):
        """Cleanup resources when provider is no longer needed."""
        pass
