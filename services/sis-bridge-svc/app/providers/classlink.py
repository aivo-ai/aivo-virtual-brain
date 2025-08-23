"""
ClassLink SIS Provider Implementation

Implements ClassLink OneRoster API integration for user, class, and enrollment sync.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator
from urllib.parse import urljoin, quote
import base64

from .base import BaseSISProvider, SISUser, SISGroup, SISEnrollment


class ClassLinkProvider(BaseSISProvider):
    """ClassLink SIS provider implementation using OneRoster API."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.classlink.com')
        self.api_version = config.get('api_version', 'v2')
        self.tenant_id = config.get('tenant_id')
        self.requests_per_second = 5
        self.requests_per_minute = 300
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers={
                    'User-Agent': 'AIVO-SIS-Bridge/1.0',
                    'Accept': 'application/json'
                }
            )
        return self.session
    
    async def authenticate(self) -> bool:
        """Authenticate with ClassLink using OAuth2."""
        try:
            session = await self._get_session()
            
            # OAuth2 client credentials flow
            auth_url = urljoin(self.base_url, '/oauth2/v2/token')
            
            # Basic authentication header
            credentials = f"{self.client_id}:{self.client_secret}"
            auth_header = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            auth_data = {
                'grant_type': 'client_credentials',
                'scope': 'oneroster'
            }
            
            async with session.post(auth_url, data=auth_data, headers=headers) as response:
                if response.status == 200:
                    token_data = await response.json()
                    self.access_token = token_data['access_token']
                    expires_in = token_data.get('expires_in', 3600)
                    self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                    return True
                else:
                    error_text = await response.text()
                    raise Exception(f"Authentication failed: {response.status} - {error_text}")
        
        except Exception as e:
            print(f"ClassLink authentication error: {e}")
            return False
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if (not self.access_token or 
            not self.token_expires_at or 
            datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5)):
            
            if not await self.authenticate():
                raise Exception("Failed to authenticate with ClassLink")
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to ClassLink OneRoster API."""
        await self._ensure_authenticated()
        
        session = await self._get_session()
        url = urljoin(self.base_url, f'/ims/oneroster/{self.api_version}/{endpoint}')
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Accept': 'application/json'
        }
        
        async with session.get(url, params=params, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 401:
                # Token expired, retry once
                await self.authenticate()
                headers['Authorization'] = f'Bearer {self.access_token}'
                async with session.get(url, params=params, headers=headers) as retry_response:
                    if retry_response.status == 200:
                        return await retry_response.json()
                    else:
                        error_text = await retry_response.text()
                        raise Exception(f"API request failed: {retry_response.status} - {error_text}")
            else:
                error_text = await response.text()
                raise Exception(f"API request failed: {response.status} - {error_text}")
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to ClassLink OneRoster API."""
        try:
            # Get orgs to test connection
            data = await self._make_request('orgs')
            return {
                "success": True,
                "message": "Connection successful",
                "org_count": len(data.get('orgs', []))
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
    
    async def get_users(
        self, 
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISUser, None]:
        """Get users from ClassLink OneRoster API."""
        
        params = {}
        if limit:
            params['limit'] = min(limit, 100)  # ClassLink recommended limit
        if offset:
            params['offset'] = offset
        if updated_since:
            params['filter'] = f"dateLastModified>='{updated_since.isoformat()}'"
        
        try:
            while True:
                data = await self._make_request('users', params)
                users = data.get('users', [])
                
                if not users:
                    break
                
                for user_data in users:
                    user = self._map_user_to_sis_user(user_data)
                    if user:
                        yield user
                
                # Check pagination
                if len(users) < params.get('limit', 100):
                    break
                
                # Update offset for next page
                params['offset'] = params.get('offset', 0) + len(users)
                
                # Rate limiting
                await asyncio.sleep(0.2)
        
        except Exception as e:
            print(f"Error fetching users: {e}")
            return
    
    def _map_user_to_sis_user(self, user_data: Dict[str, Any]) -> Optional[SISUser]:
        """Map ClassLink OneRoster user data to SISUser."""
        try:
            # Extract role (student, teacher, administrator)
            role = user_data.get('role', 'student')
            if role == 'administrator':
                role = 'admin'
            
            # Extract name components
            given_name = user_data.get('givenName', '')
            family_name = user_data.get('familyName', '')
            
            # Username and email
            username = user_data.get('username') or user_data.get('sourcedId')
            email = user_data.get('email', f"{username}@school.edu")
            
            # Status
            status = user_data.get('status', 'active')
            active = status == 'active'
            
            return SISUser(
                id=user_data.get('sourcedId'),
                username=username,
                email=email,
                first_name=given_name,
                last_name=family_name,
                role=role,
                active=active,
                created_at=self._parse_datetime(user_data.get('dateLastModified')),
                updated_at=self._parse_datetime(user_data.get('dateLastModified')),
                external_data={
                    'identifier': user_data.get('identifier'),
                    'enabledUser': user_data.get('enabledUser'),
                    'orgs': user_data.get('orgs', []),
                    'grades': user_data.get('grades', []),
                    'metadata': user_data.get('metadata', {})
                }
            )
        except Exception as e:
            print(f"Error mapping user data: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[SISUser]:
        """Get specific user by ID."""
        try:
            data = await self._make_request(f'users/{quote(user_id)}')
            user_data = data.get('user')
            if user_data:
                return self._map_user_to_sis_user(user_data)
            return None
        except Exception as e:
            print(f"Error fetching user {user_id}: {e}")
            return None
    
    async def get_groups(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISGroup, None]:
        """Get classes from ClassLink OneRoster API."""
        
        params = {}
        if limit:
            params['limit'] = min(limit, 100)
        if offset:
            params['offset'] = offset
        if updated_since:
            params['filter'] = f"dateLastModified>='{updated_since.isoformat()}'"
        
        try:
            while True:
                data = await self._make_request('classes', params)
                classes = data.get('classes', [])
                
                if not classes:
                    break
                
                for class_data in classes:
                    group = self._map_class_to_sis_group(class_data)
                    if group:
                        yield group
                
                # Check pagination
                if len(classes) < params.get('limit', 100):
                    break
                
                # Update offset for next page
                params['offset'] = params.get('offset', 0) + len(classes)
                
                # Rate limiting
                await asyncio.sleep(0.2)
        
        except Exception as e:
            print(f"Error fetching classes: {e}")
            return
    
    def _map_class_to_sis_group(self, class_data: Dict[str, Any]) -> Optional[SISGroup]:
        """Map ClassLink OneRoster class data to SISGroup."""
        try:
            # Extract course info
            course = class_data.get('course', {})
            
            # Status
            status = class_data.get('status', 'active')
            active = status == 'active'
            
            return SISGroup(
                id=class_data.get('sourcedId'),
                name=class_data.get('title', ''),
                description=course.get('title', ''),
                subject=course.get('subjectCodes', [None])[0] if course.get('subjectCodes') else None,
                grade=class_data.get('grades', [None])[0] if class_data.get('grades') else None,
                school_id=class_data.get('school', {}).get('sourcedId'),
                active=active,
                created_at=self._parse_datetime(class_data.get('dateLastModified')),
                updated_at=self._parse_datetime(class_data.get('dateLastModified')),
                external_data={
                    'classCode': class_data.get('classCode'),
                    'classType': class_data.get('classType'),
                    'location': class_data.get('location'),
                    'course': course,
                    'terms': class_data.get('terms', []),
                    'metadata': class_data.get('metadata', {})
                }
            )
        except Exception as e:
            print(f"Error mapping class data: {e}")
            return None
    
    async def get_group(self, group_id: str) -> Optional[SISGroup]:
        """Get specific class by ID."""
        try:
            data = await self._make_request(f'classes/{quote(group_id)}')
            class_data = data.get('class')
            if class_data:
                return self._map_class_to_sis_group(class_data)
            return None
        except Exception as e:
            print(f"Error fetching class {group_id}: {e}")
            return None
    
    async def get_enrollments(
        self,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISEnrollment, None]:
        """Get enrollments from ClassLink OneRoster API."""
        
        params = {}
        if limit:
            params['limit'] = min(limit, 100)
        if offset:
            params['offset'] = offset
        if updated_since:
            params['filter'] = f"dateLastModified>='{updated_since.isoformat()}'"
        
        # Add specific filters
        filters = []
        if user_id:
            filters.append(f"user.sourcedId='{user_id}'")
        if group_id:
            filters.append(f"class.sourcedId='{group_id}'")
        
        if filters:
            existing_filter = params.get('filter', '')
            if existing_filter:
                filters.append(existing_filter)
            params['filter'] = ' AND '.join(filters)
        
        try:
            while True:
                data = await self._make_request('enrollments', params)
                enrollments = data.get('enrollments', [])
                
                if not enrollments:
                    break
                
                for enrollment_data in enrollments:
                    enrollment = self._map_enrollment_to_sis_enrollment(enrollment_data)
                    if enrollment:
                        yield enrollment
                
                # Check pagination
                if len(enrollments) < params.get('limit', 100):
                    break
                
                # Update offset for next page
                params['offset'] = params.get('offset', 0) + len(enrollments)
                
                # Rate limiting
                await asyncio.sleep(0.2)
        
        except Exception as e:
            print(f"Error fetching enrollments: {e}")
            return
    
    def _map_enrollment_to_sis_enrollment(self, enrollment_data: Dict[str, Any]) -> Optional[SISEnrollment]:
        """Map ClassLink OneRoster enrollment data to SISEnrollment."""
        try:
            # Extract user and class info
            user = enrollment_data.get('user', {})
            class_info = enrollment_data.get('class', {})
            
            # Role mapping
            role = enrollment_data.get('role', 'student')
            if role in ['teacher', 'instructor']:
                role = 'teacher'
            elif role == 'administrator':
                role = 'admin'
            else:
                role = 'student'
            
            # Status
            status = enrollment_data.get('status', 'active')
            
            return SISEnrollment(
                id=enrollment_data.get('sourcedId'),
                user_id=user.get('sourcedId'),
                group_id=class_info.get('sourcedId'),
                role=role,
                status=status,
                enrolled_at=self._parse_datetime(enrollment_data.get('dateLastModified')),
                external_data={
                    'beginDate': enrollment_data.get('beginDate'),
                    'endDate': enrollment_data.get('endDate'),
                    'primary': enrollment_data.get('primary'),
                    'metadata': enrollment_data.get('metadata', {})
                }
            )
        except Exception as e:
            print(f"Error mapping enrollment data: {e}")
            return None
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """Handle ClassLink webhook events."""
        resource_ids = []
        
        try:
            # ClassLink webhook format varies, extract resource IDs
            if 'data' in payload:
                data = payload['data']
                if isinstance(data, list):
                    for item in data:
                        if 'sourcedId' in item:
                            resource_ids.append(item['sourcedId'])
                elif isinstance(data, dict) and 'sourcedId' in data:
                    resource_ids.append(data['sourcedId'])
            
        except Exception as e:
            print(f"Error handling ClassLink webhook: {e}")
        
        return resource_ids
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from ClassLink OneRoster API."""
        if not dt_str:
            return None
        
        try:
            # OneRoster uses ISO 8601 format
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None
    
    def get_supported_features(self) -> Dict[str, bool]:
        """Get supported features for ClassLink provider."""
        return {
            "users": True,
            "groups": True,
            "enrollments": True,
            "webhooks": True,
            "incremental_sync": True,
            "real_time_updates": True
        }
    
    async def cleanup(self):
        """Cleanup HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
