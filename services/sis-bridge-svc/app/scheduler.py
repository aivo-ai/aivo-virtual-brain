"""
Background job scheduler for SIS synchronization.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID
from sqlalchemy.orm import Session

from .database import get_db, TenantSISProvider, SyncJob, SyncOperation, SyncStatus
from .sync_engine import SyncEngine
from .config import get_settings

settings = get_settings()


class SyncScheduler:
    """Background scheduler for SIS sync jobs."""
    
    def __init__(self):
        self.sync_engine = SyncEngine()
        self.running = False
        self.scheduler_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the scheduler."""
        if not self.running:
            self.running = True
            self.scheduler_task = asyncio.create_task(self._scheduler_loop())
            print("SIS Sync Scheduler started")
    
    async def stop(self):
        """Stop the scheduler."""
        self.running = False
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        await self.sync_engine.cleanup()
        print("SIS Sync Scheduler stopped")
    
    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self.running
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        while self.running:
            try:
                await self._check_scheduled_syncs()
                await self._cleanup_old_jobs()
                
                # Sleep for 1 minute before next check
                await asyncio.sleep(60)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(60)
    
    async def _check_scheduled_syncs(self):
        """Check for providers that need scheduled sync."""
        
        db = next(get_db())
        try:
            # Get all enabled providers with auto sync
            providers = db.query(TenantSISProvider).filter(
                TenantSISProvider.enabled == True,
                TenantSISProvider.auto_sync == True
            ).all()
            
            for provider in providers:
                if await self._should_sync_provider(provider, db):
                    try:
                        # Start sync job
                        job_id = await self.sync_engine.start_sync(
                            provider_id=provider.id,
                            sync_type="incremental"
                        )
                        print(f"Started scheduled sync for provider {provider.id}: {job_id}")
                    except Exception as e:
                        print(f"Failed to start sync for provider {provider.id}: {e}")
        
        finally:
            db.close()
    
    async def _should_sync_provider(self, provider: TenantSISProvider, db: Session) -> bool:
        """Check if provider should be synced now."""
        
        # Check if there's already a running sync
        running_job = db.query(SyncJob).filter(
            SyncJob.provider_id == provider.id,
            SyncJob.status == SyncStatus.RUNNING
        ).first()
        
        if running_job:
            return False
        
        # Check sync interval
        if provider.last_sync_at is None:
            # Never synced, sync now
            return True
        
        sync_interval = provider.sync_interval or settings.default_sync_interval
        next_sync_time = provider.last_sync_at + timedelta(seconds=sync_interval)
        
        return datetime.utcnow() >= next_sync_time
    
    async def _cleanup_old_jobs(self):
        """Cleanup old sync jobs and operations."""
        
        db = next(get_db())
        try:
            # Keep jobs for 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)
            
            # Delete old completed/failed jobs
            old_jobs = db.query(SyncJob).filter(
                SyncJob.completed_at < cutoff_date,
                SyncJob.status.in_([SyncStatus.COMPLETED, SyncStatus.FAILED, SyncStatus.CANCELLED])
            ).all()
            
            for job in old_jobs:
                # Delete associated operations first
                db.query(SyncOperation).filter(SyncOperation.job_id == job.id).delete()
                db.delete(job)
            
            if old_jobs:
                db.commit()
                print(f"Cleaned up {len(old_jobs)} old sync jobs")
        
        except Exception as e:
            print(f"Error cleaning up old jobs: {e}")
            db.rollback()
        
        finally:
            db.close()
    
    async def schedule_immediate_sync(
        self,
        provider_id: UUID,
        sync_type: str = "manual",
        user_filter: Optional[Dict] = None,
        group_filter: Optional[Dict] = None
    ) -> UUID:
        """Schedule an immediate sync job."""
        
        return await self.sync_engine.start_sync(
            provider_id=provider_id,
            sync_type=sync_type,
            user_filter=user_filter,
            group_filter=group_filter
        )
    
    async def cancel_sync(self, job_id: UUID) -> bool:
        """Cancel a running sync job."""
        
        return await self.sync_engine.stop_sync(job_id)
    
    def get_sync_status(self, job_id: UUID) -> Optional[Dict]:
        """Get sync job status."""
        
        db = next(get_db())
        try:
            job = db.query(SyncJob).filter(SyncJob.id == job_id).first()
            if job:
                return {
                    "id": str(job.id),
                    "status": job.status,
                    "progress": job.progress,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "stats": job.stats,
                    "error_message": job.error_message
                }
            return None
        finally:
            db.close()
    
    def get_provider_sync_history(self, provider_id: UUID, limit: int = 10) -> List[Dict]:
        """Get sync history for a provider."""
        
        db = next(get_db())
        try:
            jobs = db.query(SyncJob).filter(
                SyncJob.provider_id == provider_id
            ).order_by(SyncJob.created_at.desc()).limit(limit).all()
            
            return [
                {
                    "id": str(job.id),
                    "sync_type": job.sync_type,
                    "status": job.status,
                    "progress": job.progress,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                    "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    "stats": job.stats,
                    "error_message": job.error_message
                }
                for job in jobs
            ]
        finally:
            db.close()
