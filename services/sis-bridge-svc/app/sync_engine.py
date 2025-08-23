"""
Sync Engine - Core synchronization logic

Handles the orchestration of SIS data synchronization with SCIM 2.0 provider.
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy.orm import Session

from .database import get_db, TenantSISProvider, SyncJob, SyncOperation, SISResourceMapping, SyncStatus, SyncType
from .providers import get_provider, BaseSISProvider
from .providers.base import SISUser, SISGroup, SISEnrollment
from .vault_client import VaultClient
from .config import get_settings

settings = get_settings()


class SyncEngine:
    """Core synchronization engine."""
    
    def __init__(self):
        self.vault_client = VaultClient() if settings.vault_url else None
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session for SCIM API calls."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=settings.sync_timeout),
                headers={
                    'Authorization': f'Bearer {settings.tenant_service_token}',
                    'Content-Type': 'application/scim+json',
                    'User-Agent': 'AIVO-SIS-Bridge/1.0'
                }
            )
        return self.session
    
    async def start_sync(
        self,
        provider_id: UUID,
        sync_type: str = SyncType.FULL,
        user_filter: Optional[Dict] = None,
        group_filter: Optional[Dict] = None
    ) -> UUID:
        """
        Start a synchronization job.
        
        Args:
            provider_id: SIS provider ID
            sync_type: Type of sync (full, incremental, manual)
            user_filter: Optional user filter conditions
            group_filter: Optional group filter conditions
        
        Returns:
            Sync job ID
        """
        
        db = next(get_db())
        try:
            # Get provider configuration
            provider_config = db.query(TenantSISProvider).filter(
                TenantSISProvider.id == provider_id
            ).first()
            
            if not provider_config or not provider_config.enabled:
                raise Exception("Provider not found or disabled")
            
            # Create sync job
            job = SyncJob(
                id=uuid4(),
                provider_id=provider_id,
                tenant_id=provider_config.tenant_id,
                sync_type=sync_type,
                status=SyncStatus.PENDING,
                created_at=datetime.utcnow(),
                stats={
                    'users_processed': 0,
                    'groups_processed': 0,
                    'enrollments_processed': 0,
                    'errors': 0
                }
            )
            
            db.add(job)
            db.commit()
            db.refresh(job)
            
            # Start sync in background
            asyncio.create_task(self._execute_sync(job.id, user_filter, group_filter))
            
            return job.id
        
        finally:
            db.close()
    
    async def _execute_sync(
        self,
        job_id: UUID,
        user_filter: Optional[Dict] = None,
        group_filter: Optional[Dict] = None
    ):
        """Execute synchronization job."""
        
        db = next(get_db())
        try:
            # Get job and provider config
            job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
            if not job:
                return
            
            provider_config = db.query(TenantSISProvider).filter(
                TenantSISProvider.id == job.provider_id
            ).first()
            
            # Update job status
            job.status = SyncStatus.RUNNING
            job.started_at = datetime.utcnow()
            db.commit()
            
            try:
                # Get SIS provider credentials
                credentials = await self._get_provider_credentials(provider_config)
                
                # Initialize SIS provider
                sis_provider = get_provider(provider_config.provider, credentials)
                
                # Authenticate with SIS
                if not await sis_provider.authenticate():
                    raise Exception("Failed to authenticate with SIS provider")
                
                # Determine last sync time for incremental sync
                last_sync_time = None
                if job.sync_type == SyncType.INCREMENTAL:
                    last_sync_time = provider_config.last_sync_at
                
                # Execute sync phases
                if provider_config.sync_users:
                    await self._sync_users(job, sis_provider, last_sync_time, user_filter, db)
                
                if provider_config.sync_groups:
                    await self._sync_groups(job, sis_provider, last_sync_time, group_filter, db)
                
                if provider_config.sync_enrollments:
                    await self._sync_enrollments(job, sis_provider, last_sync_time, db)
                
                # Update job completion
                job.status = SyncStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                job.progress = 100
                
                # Update provider last sync time
                provider_config.last_sync_at = datetime.utcnow()
                
                db.commit()
                
                # Cleanup
                await sis_provider.cleanup()
                
            except Exception as e:
                # Handle sync failure
                job.status = SyncStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.utcnow()
                job.stats['errors'] = job.stats.get('errors', 0) + 1
                db.commit()
                
                print(f"Sync job {job_id} failed: {e}")
        
        finally:
            db.close()
    
    async def _get_provider_credentials(self, provider_config: TenantSISProvider) -> Dict[str, Any]:
        """Get provider credentials from Vault or configuration."""
        
        if self.vault_client and provider_config.credentials_path:
            # Get credentials from Vault
            credentials = await self.vault_client.get_secret(provider_config.credentials_path)
            return {**provider_config.config, **credentials}
        else:
            # Use configuration directly (less secure)
            return provider_config.config
    
    async def _sync_users(
        self,
        job: SyncJob,
        sis_provider: BaseSISProvider,
        last_sync_time: Optional[datetime],
        user_filter: Optional[Dict],
        db: Session
    ):
        """Sync users from SIS to SCIM."""
        
        batch_size = settings.batch_size
        processed = 0
        
        try:
            async for sis_user in sis_provider.get_users(
                limit=batch_size,
                updated_since=last_sync_time
            ):
                # Apply filters
                if user_filter and not self._apply_user_filter(sis_user, user_filter):
                    continue
                
                # Process user
                await self._process_user(job, sis_user, db)
                
                processed += 1
                
                # Update progress
                if processed % 10 == 0:
                    job.stats['users_processed'] = processed
                    job.progress = min(30, (processed / 100) * 30)  # Users = 30% of total
                    db.commit()
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"Error syncing users: {e}")
            raise
    
    async def _process_user(self, job: SyncJob, sis_user: SISUser, db: Session):
        """Process individual user sync."""
        
        operation = SyncOperation(
            id=uuid4(),
            job_id=job.id,
            operation_type="sync_user",
            resource_type="user",
            resource_id=sis_user.id,
            status="pending",
            source_data=sis_user.__dict__,
            created_at=datetime.utcnow()
        )
        
        db.add(operation)
        
        try:
            # Check if user mapping exists
            mapping = db.query(SISResourceMapping).filter(
                SISResourceMapping.tenant_id == job.tenant_id,
                SISResourceMapping.provider == job.provider.provider,
                SISResourceMapping.sis_resource_id == sis_user.id,
                SISResourceMapping.sis_resource_type == "user"
            ).first()
            
            # Convert SIS user to SCIM format
            scim_user_data = self._map_sis_user_to_scim(sis_user)
            operation.mapped_data = scim_user_data
            
            if mapping:
                # Update existing user
                await self._update_scim_user(mapping.scim_resource_id, scim_user_data)
                operation.operation_type = "update_user"
            else:
                # Create new user
                scim_user_id = await self._create_scim_user(scim_user_data, str(job.tenant_id))
                
                # Create mapping
                mapping = SISResourceMapping(
                    id=uuid4(),
                    tenant_id=job.tenant_id,
                    provider=job.provider.provider,
                    sis_resource_id=sis_user.id,
                    sis_resource_type="user",
                    scim_resource_id=scim_user_id,
                    scim_resource_type="User",
                    created_at=datetime.utcnow(),
                    last_synced_at=datetime.utcnow()
                )
                db.add(mapping)
                operation.operation_type = "create_user"
                operation.scim_resource_id = scim_user_id
            
            # Update mapping sync time
            mapping.last_synced_at = datetime.utcnow()
            
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            print(f"Error processing user {sis_user.id}: {e}")
        
        db.commit()
    
    def _map_sis_user_to_scim(self, sis_user: SISUser) -> Dict[str, Any]:
        """Map SIS user to SCIM user format."""
        
        scim_user = {
            "schemas": [
                "urn:ietf:params:scim:schemas:core:2.0:User",
                "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"
            ],
            "userName": sis_user.username,
            "name": {
                "givenName": sis_user.first_name,
                "familyName": sis_user.last_name,
                "formatted": f"{sis_user.first_name} {sis_user.last_name}".strip()
            },
            "emails": [
                {
                    "value": sis_user.email,
                    "type": "work",
                    "primary": True
                }
            ],
            "active": sis_user.active,
            "userType": sis_user.role,
            "externalId": sis_user.id,
            "urn:ietf:params:scim:schemas:extension:enterprise:2.0:User": {
                "employeeNumber": sis_user.id
            }
        }
        
        # Add external data as metadata
        if sis_user.external_data:
            scim_user["urn:ietf:params:scim:schemas:extension:enterprise:2.0:User"].update({
                "department": sis_user.external_data.get("grade"),
                "organization": sis_user.external_data.get("school")
            })
        
        return scim_user
    
    async def _create_scim_user(self, scim_user_data: Dict[str, Any], tenant_id: str) -> UUID:
        """Create user via SCIM API."""
        
        session = await self._get_session()
        url = f"{settings.tenant_service_url}/scim/v2/Users"
        
        headers = {
            'X-Tenant-ID': tenant_id,
            'Content-Type': 'application/scim+json'
        }
        
        async with session.post(url, json=scim_user_data, headers=headers) as response:
            if response.status == 201:
                user_data = await response.json()
                return UUID(user_data['id'])
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create SCIM user: {response.status} - {error_text}")
    
    async def _update_scim_user(self, user_id: UUID, scim_user_data: Dict[str, Any]):
        """Update user via SCIM API."""
        
        session = await self._get_session()
        url = f"{settings.tenant_service_url}/scim/v2/Users/{user_id}"
        
        async with session.put(url, json=scim_user_data) as response:
            if response.status not in [200, 204]:
                error_text = await response.text()
                raise Exception(f"Failed to update SCIM user: {response.status} - {error_text}")
    
    async def _sync_groups(
        self,
        job: SyncJob,
        sis_provider: BaseSISProvider,
        last_sync_time: Optional[datetime],
        group_filter: Optional[Dict],
        db: Session
    ):
        """Sync groups from SIS to SCIM."""
        
        batch_size = settings.batch_size
        processed = 0
        
        try:
            async for sis_group in sis_provider.get_groups(
                limit=batch_size,
                updated_since=last_sync_time
            ):
                # Apply filters
                if group_filter and not self._apply_group_filter(sis_group, group_filter):
                    continue
                
                # Process group
                await self._process_group(job, sis_group, db)
                
                processed += 1
                
                # Update progress
                if processed % 10 == 0:
                    job.stats['groups_processed'] = processed
                    job.progress = min(60, 30 + (processed / 100) * 30)  # Groups = 30% of total
                    db.commit()
                
                # Rate limiting
                await asyncio.sleep(0.1)
        
        except Exception as e:
            print(f"Error syncing groups: {e}")
            raise
    
    async def _process_group(self, job: SyncJob, sis_group: SISGroup, db: Session):
        """Process individual group sync."""
        
        operation = SyncOperation(
            id=uuid4(),
            job_id=job.id,
            operation_type="sync_group",
            resource_type="group",
            resource_id=sis_group.id,
            status="pending",
            source_data=sis_group.__dict__,
            created_at=datetime.utcnow()
        )
        
        db.add(operation)
        
        try:
            # Check if group mapping exists
            mapping = db.query(SISResourceMapping).filter(
                SISResourceMapping.tenant_id == job.tenant_id,
                SISResourceMapping.provider == job.provider.provider,
                SISResourceMapping.sis_resource_id == sis_group.id,
                SISResourceMapping.sis_resource_type == "group"
            ).first()
            
            # Convert SIS group to SCIM format
            scim_group_data = self._map_sis_group_to_scim(sis_group, db)
            operation.mapped_data = scim_group_data
            
            if mapping:
                # Update existing group
                await self._update_scim_group(mapping.scim_resource_id, scim_group_data)
                operation.operation_type = "update_group"
            else:
                # Create new group
                scim_group_id = await self._create_scim_group(scim_group_data, str(job.tenant_id))
                
                # Create mapping
                mapping = SISResourceMapping(
                    id=uuid4(),
                    tenant_id=job.tenant_id,
                    provider=job.provider.provider,
                    sis_resource_id=sis_group.id,
                    sis_resource_type="group",
                    scim_resource_id=scim_group_id,
                    scim_resource_type="Group",
                    created_at=datetime.utcnow(),
                    last_synced_at=datetime.utcnow()
                )
                db.add(mapping)
                operation.operation_type = "create_group"
                operation.scim_resource_id = scim_group_id
            
            # Update mapping sync time
            mapping.last_synced_at = datetime.utcnow()
            
            operation.status = "completed"
            operation.completed_at = datetime.utcnow()
            
        except Exception as e:
            operation.status = "failed"
            operation.error_message = str(e)
            operation.completed_at = datetime.utcnow()
            print(f"Error processing group {sis_group.id}: {e}")
        
        db.commit()
    
    def _map_sis_group_to_scim(self, sis_group: SISGroup, db: Session) -> Dict[str, Any]:
        """Map SIS group to SCIM group format."""
        
        scim_group = {
            "schemas": ["urn:ietf:params:scim:schemas:core:2.0:Group"],
            "displayName": sis_group.name,
            "externalId": sis_group.id,
            "members": []
        }
        
        # Add members if available
        if sis_group.student_ids:
            for student_id in sis_group.student_ids:
                member_mapping = db.query(SISResourceMapping).filter(
                    SISResourceMapping.sis_resource_id == student_id,
                    SISResourceMapping.sis_resource_type == "user"
                ).first()
                
                if member_mapping:
                    scim_group["members"].append({
                        "value": str(member_mapping.scim_resource_id),
                        "type": "User"
                    })
        
        if sis_group.teacher_ids:
            for teacher_id in sis_group.teacher_ids:
                member_mapping = db.query(SISResourceMapping).filter(
                    SISResourceMapping.sis_resource_id == teacher_id,
                    SISResourceMapping.sis_resource_type == "user"
                ).first()
                
                if member_mapping:
                    scim_group["members"].append({
                        "value": str(member_mapping.scim_resource_id),
                        "type": "User"
                    })
        
        return scim_group
    
    async def _create_scim_group(self, scim_group_data: Dict[str, Any], tenant_id: str) -> UUID:
        """Create group via SCIM API."""
        
        session = await self._get_session()
        url = f"{settings.tenant_service_url}/scim/v2/Groups"
        
        headers = {
            'X-Tenant-ID': tenant_id,
            'Content-Type': 'application/scim+json'
        }
        
        async with session.post(url, json=scim_group_data, headers=headers) as response:
            if response.status == 201:
                group_data = await response.json()
                return UUID(group_data['id'])
            else:
                error_text = await response.text()
                raise Exception(f"Failed to create SCIM group: {response.status} - {error_text}")
    
    async def _update_scim_group(self, group_id: UUID, scim_group_data: Dict[str, Any]):
        """Update group via SCIM API."""
        
        session = await self._get_session()
        url = f"{settings.tenant_service_url}/scim/v2/Groups/{group_id}"
        
        async with session.put(url, json=scim_group_data) as response:
            if response.status not in [200, 204]:
                error_text = await response.text()
                raise Exception(f"Failed to update SCIM group: {response.status} - {error_text}")
    
    async def _sync_enrollments(
        self,
        job: SyncJob,
        sis_provider: BaseSISProvider,
        last_sync_time: Optional[datetime],
        db: Session
    ):
        """Sync enrollments (handled via group memberships)."""
        
        # Enrollments are handled as part of group membership sync
        # This could be extended for more complex enrollment tracking
        
        processed = 0
        
        try:
            async for enrollment in sis_provider.get_enrollments(
                updated_since=last_sync_time
            ):
                processed += 1
                
                # Update progress
                if processed % 10 == 0:
                    job.stats['enrollments_processed'] = processed
                    job.progress = min(100, 60 + (processed / 100) * 40)  # Enrollments = 40% of total
                    db.commit()
                
                # Rate limiting
                await asyncio.sleep(0.05)
        
        except Exception as e:
            print(f"Error syncing enrollments: {e}")
            raise
    
    def _apply_user_filter(self, user: SISUser, filter_config: Dict) -> bool:
        """Apply user filter conditions."""
        
        if 'roles' in filter_config:
            if user.role not in filter_config['roles']:
                return False
        
        if 'active_only' in filter_config:
            if filter_config['active_only'] and not user.active:
                return False
        
        return True
    
    def _apply_group_filter(self, group: SISGroup, filter_config: Dict) -> bool:
        """Apply group filter conditions."""
        
        if 'subjects' in filter_config:
            if group.subject not in filter_config['subjects']:
                return False
        
        if 'grades' in filter_config:
            if group.grade not in filter_config['grades']:
                return False
        
        return True
    
    async def stop_sync(self, job_id: UUID) -> bool:
        """Stop a running sync job."""
        
        db = next(get_db())
        try:
            job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
            if job and job.status == SyncStatus.RUNNING:
                job.status = SyncStatus.CANCELLED
                job.completed_at = datetime.utcnow()
                db.commit()
                return True
            return False
        finally:
            db.close()
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.session and not self.session.closed:
            await self.session.close()
