"""
Clever SIS Provider Implementation

Implements Clever API integration for user, section, and enrollment sync.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, AsyncGenerator
from urllib.parse import urljoin

from .base import BaseSISProvider, SISUser, SISGroup, SISEnrollment


class CleverProvider(BaseSISProvider):
    """Clever SIS provider implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_url = config.get('base_url', 'https://api.clever.com')
        self.api_version = config.get('api_version', 'v3.0')
        self.district_id = config.get('district_id')
        self.requests_per_second = 10
        self.requests_per_minute = 600
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
        """Authenticate with Clever using OAuth2 client credentials."""
        try:
            session = await self._get_session()
            
            # OAuth2 client credentials flow
            auth_url = urljoin(self.base_url, '/oauth/tokens')
            
            auth_data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            async with session.post(auth_url, data=auth_data) as response:
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
            print(f"Clever authentication error: {e}")
            return False
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid access token."""
        if (not self.access_token or 
            not self.token_expires_at or 
            datetime.utcnow() >= self.token_expires_at - timedelta(minutes=5)):
            
            if not await self.authenticate():
                raise Exception("Failed to authenticate with Clever")
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to Clever API."""
        await self._ensure_authenticated()
        
        session = await self._get_session()
        url = urljoin(self.base_url, f'/{self.api_version}/{endpoint}')
        
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
        """Test connection to Clever API."""
        try:
            # Get district info to test connection
            data = await self._make_request('districts')
            return {
                "success": True,
                "message": "Connection successful",
                "district_count": len(data.get('data', []))
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
        """Get users from Clever (students and teachers)."""
        
        # Get students
        async for student in self._get_students(limit, offset, updated_since):
            yield student
        
        # Get teachers
        async for teacher in self._get_teachers(limit, offset, updated_since):
            yield teacher
    
    async def _get_students(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISUser, None]:
        """Get students from Clever."""
        
        params = {}
        if limit:
            params['limit'] = min(limit, 1000)  # Clever max is 1000
        if offset:
            params['starting_after'] = offset
        if updated_since:
            params['updated_since'] = updated_since.isoformat()
        
        try:
            page = 0
            while True:
                if page > 0:
                    params['page'] = page
                
                data = await self._make_request('students', params)
                students = data.get('data', [])
                
                if not students:
                    break
                
                for student_data in students:
                    student = self._map_student_to_sis_user(student_data)
                    if student:
                        yield student
                
                # Check if there are more pages
                if not data.get('paging', {}).get('next'):
                    break
                
                page += 1
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"Error fetching students: {e}")
            return
    
    async def _get_teachers(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISUser, None]:
        """Get teachers from Clever."""
        
        params = {}
        if limit:
            params['limit'] = min(limit, 1000)
        if offset:
            params['starting_after'] = offset
        if updated_since:
            params['updated_since'] = updated_since.isoformat()
        
        try:
            page = 0
            while True:
                if page > 0:
                    params['page'] = page
                
                data = await self._make_request('teachers', params)
                teachers = data.get('data', [])
                
                if not teachers:
                    break
                
                for teacher_data in teachers:
                    teacher = self._map_teacher_to_sis_user(teacher_data)
                    if teacher:
                        yield teacher
                
                # Check if there are more pages
                if not data.get('paging', {}).get('next'):
                    break
                
                page += 1
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"Error fetching teachers: {e}")
            return
    
    def _map_student_to_sis_user(self, student_data: Dict[str, Any]) -> Optional[SISUser]:
        """Map Clever student data to SISUser."""
        try:
            data = student_data.get('data', {})
            
            # Extract name components
            name = data.get('name', {})
            first_name = name.get('first', '')
            last_name = name.get('last', '')
            
            # Generate username and email
            username = data.get('student_number') or data.get('sis_id') or student_data.get('id')
            email = data.get('email', f"{username}@student.school.edu")
            
            return SISUser(
                id=student_data.get('id'),
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='student',
                active=True,  # Clever doesn't provide explicit active status
                created_at=self._parse_datetime(data.get('created')),
                updated_at=self._parse_datetime(data.get('last_modified')),
                external_data={
                    'grade': data.get('grade'),
                    'student_number': data.get('student_number'),
                    'sis_id': data.get('sis_id'),
                    'school': data.get('school'),
                    'graduation_year': data.get('graduation_year')
                }
            )
        except Exception as e:
            print(f"Error mapping student data: {e}")
            return None
    
    def _map_teacher_to_sis_user(self, teacher_data: Dict[str, Any]) -> Optional[SISUser]:
        """Map Clever teacher data to SISUser."""
        try:
            data = teacher_data.get('data', {})
            
            # Extract name components
            name = data.get('name', {})
            first_name = name.get('first', '')
            last_name = name.get('last', '')
            
            # Generate username
            username = data.get('teacher_number') or data.get('sis_id') or teacher_data.get('id')
            email = data.get('email', f"{username}@school.edu")
            
            return SISUser(
                id=teacher_data.get('id'),
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role='teacher',
                active=True,
                created_at=self._parse_datetime(data.get('created')),
                updated_at=self._parse_datetime(data.get('last_modified')),
                external_data={
                    'teacher_number': data.get('teacher_number'),
                    'sis_id': data.get('sis_id'),
                    'school': data.get('school'),
                    'title': data.get('title')
                }
            )
        except Exception as e:
            print(f"Error mapping teacher data: {e}")
            return None
    
    async def get_user(self, user_id: str) -> Optional[SISUser]:
        """Get specific user by ID."""
        try:
            # Try as student first
            try:
                data = await self._make_request(f'students/{user_id}')
                return self._map_student_to_sis_user(data)
            except:
                pass
            
            # Try as teacher
            try:
                data = await self._make_request(f'teachers/{user_id}')
                return self._map_teacher_to_sis_user(data)
            except:
                pass
            
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
        """Get sections from Clever."""
        
        params = {}
        if limit:
            params['limit'] = min(limit, 1000)
        if offset:
            params['starting_after'] = offset
        if updated_since:
            params['updated_since'] = updated_since.isoformat()
        
        try:
            page = 0
            while True:
                if page > 0:
                    params['page'] = page
                
                data = await self._make_request('sections', params)
                sections = data.get('data', [])
                
                if not sections:
                    break
                
                for section_data in sections:
                    section = self._map_section_to_sis_group(section_data)
                    if section:
                        yield section
                
                # Check if there are more pages
                if not data.get('paging', {}).get('next'):
                    break
                
                page += 1
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"Error fetching sections: {e}")
            return
    
    def _map_section_to_sis_group(self, section_data: Dict[str, Any]) -> Optional[SISGroup]:
        """Map Clever section data to SISGroup."""
        try:
            data = section_data.get('data', {})
            
            return SISGroup(
                id=section_data.get('id'),
                name=data.get('name', ''),
                description=f"{data.get('subject')} - {data.get('course_name', '')}".strip(' -'),
                subject=data.get('subject'),
                grade=data.get('grade'),
                school_id=data.get('school'),
                teacher_ids=data.get('teachers', []),
                student_ids=data.get('students', []),
                active=True,
                created_at=self._parse_datetime(data.get('created')),
                updated_at=self._parse_datetime(data.get('last_modified')),
                external_data={
                    'course_name': data.get('course_name'),
                    'course_number': data.get('course_number'),
                    'period': data.get('period'),
                    'sis_id': data.get('sis_id')
                }
            )
        except Exception as e:
            print(f"Error mapping section data: {e}")
            return None
    
    async def get_group(self, group_id: str) -> Optional[SISGroup]:
        """Get specific section by ID."""
        try:
            data = await self._make_request(f'sections/{group_id}')
            return self._map_section_to_sis_group(data)
        except Exception as e:
            print(f"Error fetching section {group_id}: {e}")
            return None
    
    async def get_enrollments(
        self,
        user_id: Optional[str] = None,
        group_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        updated_since: Optional[datetime] = None
    ) -> AsyncGenerator[SISEnrollment, None]:
        """Get enrollments from Clever."""
        
        if group_id:
            # Get enrollments for specific section
            async for enrollment in self._get_section_enrollments(group_id, limit, offset):
                yield enrollment
        elif user_id:
            # Get enrollments for specific user
            async for enrollment in self._get_user_enrollments(user_id, limit, offset):
                yield enrollment
        else:
            # Get all enrollments (via sections)
            async for group in self.get_groups(limit, offset, updated_since):
                async for enrollment in self._get_section_enrollments(group.id):
                    yield enrollment
    
    async def _get_section_enrollments(
        self, 
        section_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> AsyncGenerator[SISEnrollment, None]:
        """Get enrollments for a specific section."""
        try:
            # Get section details to get student and teacher lists
            section_data = await self._make_request(f'sections/{section_id}')
            section = section_data.get('data', {})
            
            # Student enrollments
            for student_id in section.get('students', []):
                yield SISEnrollment(
                    id=f"{section_id}_{student_id}_student",
                    user_id=student_id,
                    group_id=section_id,
                    role='student',
                    status='active',
                    external_data={'section_name': section.get('name')}
                )
            
            # Teacher enrollments
            for teacher_id in section.get('teachers', []):
                yield SISEnrollment(
                    id=f"{section_id}_{teacher_id}_teacher",
                    user_id=teacher_id,
                    group_id=section_id,
                    role='teacher',
                    status='active',
                    external_data={'section_name': section.get('name')}
                )
        
        except Exception as e:
            print(f"Error fetching section enrollments for {section_id}: {e}")
            return
    
    async def _get_user_enrollments(
        self,
        user_id: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> AsyncGenerator[SISEnrollment, None]:
        """Get enrollments for a specific user."""
        try:
            # Try as student
            try:
                data = await self._make_request(f'students/{user_id}/sections')
                sections = data.get('data', [])
                
                for section_data in sections:
                    section_id = section_data.get('id')
                    yield SISEnrollment(
                        id=f"{section_id}_{user_id}_student",
                        user_id=user_id,
                        group_id=section_id,
                        role='student',
                        status='active',
                        external_data={'section_name': section_data.get('data', {}).get('name')}
                    )
            except:
                pass
            
            # Try as teacher
            try:
                data = await self._make_request(f'teachers/{user_id}/sections')
                sections = data.get('data', [])
                
                for section_data in sections:
                    section_id = section_data.get('id')
                    yield SISEnrollment(
                        id=f"{section_id}_{user_id}_teacher",
                        user_id=user_id,
                        group_id=section_id,
                        role='teacher',
                        status='active',
                        external_data={'section_name': section_data.get('data', {}).get('name')}
                    )
            except:
                pass
        
        except Exception as e:
            print(f"Error fetching user enrollments for {user_id}: {e}")
            return
    
    async def handle_webhook(self, event_type: str, payload: Dict[str, Any]) -> List[str]:
        """Handle Clever webhook events."""
        resource_ids = []
        
        try:
            event_data = payload.get('data', {})
            resource_type = event_data.get('type')
            resource_id = event_data.get('id')
            
            if resource_id:
                resource_ids.append(resource_id)
            
            # Handle different event types
            if event_type in ['students.created', 'students.updated', 'students.deleted']:
                # Student change event
                pass
            elif event_type in ['teachers.created', 'teachers.updated', 'teachers.deleted']:
                # Teacher change event
                pass
            elif event_type in ['sections.created', 'sections.updated', 'sections.deleted']:
                # Section change event
                pass
            
        except Exception as e:
            print(f"Error handling Clever webhook: {e}")
        
        return resource_ids
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Clever API."""
        if not dt_str:
            return None
        
        try:
            # Clever uses ISO 8601 format
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except:
            return None
    
    def get_supported_features(self) -> Dict[str, bool]:
        """Get supported features for Clever provider."""
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
