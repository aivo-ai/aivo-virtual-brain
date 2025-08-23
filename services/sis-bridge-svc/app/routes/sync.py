"""
Sync Management API Routes

Endpoints for managing SIS synchronization jobs.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db, TenantSISProvider, SyncJob
from ..scheduler import SyncScheduler

router = APIRouter()


class SyncRequest(BaseModel):
    """Sync job request model."""
    sync_type: str = "full"  # full, incremental, manual
    user_filter: Optional[Dict[str, Any]] = None
    group_filter: Optional[Dict[str, Any]] = None


class SyncResponse(BaseModel):
    """Sync job response model."""
    job_id: str
    status: str
    message: str


class SyncStatusResponse(BaseModel):
    """Sync status response model."""
    id: str
    status: str
    progress: int
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    stats: Dict[str, Any]
    error_message: Optional[str] = None


def get_scheduler() -> SyncScheduler:
    """Get sync scheduler instance from app state."""
    # This would be injected from the main app
    # For now, create a new instance
    return SyncScheduler()


@router.post("/{tenant_id}/start", response_model=SyncResponse)
async def start_sync(
    tenant_id: UUID,
    sync_request: SyncRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """Start a synchronization job for tenant."""
    
    try:
        # Get all enabled providers for tenant
        providers = db.query(TenantSISProvider).filter(
            TenantSISProvider.tenant_id == tenant_id,
            TenantSISProvider.enabled == True
        ).all()
        
        if not providers:
            raise HTTPException(
                status_code=404,
                detail="No enabled SIS providers found for tenant"
            )
        
        # For now, sync the first provider
        # In a full implementation, you might want to sync all or allow selection
        provider = providers[0]
        
        # Get scheduler from app state
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            raise HTTPException(
                status_code=500,
                detail="Sync scheduler not available"
            )
        
        # Start sync job
        job_id = await scheduler.schedule_immediate_sync(
            provider_id=provider.id,
            sync_type=sync_request.sync_type,
            user_filter=sync_request.user_filter,
            group_filter=sync_request.group_filter
        )
        
        return SyncResponse(
            job_id=str(job_id),
            status="started",
            message=f"Sync job started for provider {provider.name}"
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}/status", response_model=SyncStatusResponse)
async def get_sync_status(
    tenant_id: UUID,
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """Get sync job status."""
    
    try:
        # Verify job belongs to tenant
        job = db.query(SyncJob).filter(
            SyncJob.id == job_id,
            SyncJob.tenant_id == tenant_id
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Sync job not found"
            )
        
        # Get scheduler from app state
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            raise HTTPException(
                status_code=500,
                detail="Sync scheduler not available"
            )
        
        # Get detailed status
        status = scheduler.get_sync_status(job_id)
        if not status:
            raise HTTPException(
                status_code=404,
                detail="Sync job status not found"
            )
        
        return SyncStatusResponse(**status)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tenant_id}/stop")
async def stop_sync(
    tenant_id: UUID,
    job_id: UUID,
    request: Request,
    db: Session = Depends(get_db)
):
    """Stop a running sync job."""
    
    try:
        # Verify job belongs to tenant
        job = db.query(SyncJob).filter(
            SyncJob.id == job_id,
            SyncJob.tenant_id == tenant_id
        ).first()
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail="Sync job not found"
            )
        
        # Get scheduler from app state
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            raise HTTPException(
                status_code=500,
                detail="Sync scheduler not available"
            )
        
        # Cancel sync job
        cancelled = await scheduler.cancel_sync(job_id)
        
        if cancelled:
            return {"message": "Sync job cancelled"}
        else:
            return {"message": "Sync job was not running"}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}/history")
async def get_sync_history(
    tenant_id: UUID,
    request: Request,
    provider_id: Optional[UUID] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get sync job history for tenant."""
    
    try:
        # Get scheduler from app state
        scheduler = getattr(request.app.state, 'scheduler', None)
        if not scheduler:
            raise HTTPException(
                status_code=500,
                detail="Sync scheduler not available"
            )
        
        if provider_id:
            # Get history for specific provider
            # Verify provider belongs to tenant
            provider = db.query(TenantSISProvider).filter(
                TenantSISProvider.id == provider_id,
                TenantSISProvider.tenant_id == tenant_id
            ).first()
            
            if not provider:
                raise HTTPException(
                    status_code=404,
                    detail="SIS provider not found"
                )
            
            history = scheduler.get_provider_sync_history(provider_id, limit)
        else:
            # Get history for all providers of tenant
            providers = db.query(TenantSISProvider).filter(
                TenantSISProvider.tenant_id == tenant_id
            ).all()
            
            history = []
            for provider in providers:
                provider_history = scheduler.get_provider_sync_history(provider.id, limit)
                history.extend(provider_history)
            
            # Sort by creation time and limit
            history.sort(key=lambda x: x.get('started_at', ''), reverse=True)
            history = history[:limit]
        
        return {
            "history": history,
            "total": len(history)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}/providers")
async def list_sync_providers(
    tenant_id: UUID,
    db: Session = Depends(get_db)
):
    """List SIS providers and their sync status."""
    
    try:
        providers = db.query(TenantSISProvider).filter(
            TenantSISProvider.tenant_id == tenant_id
        ).all()
        
        provider_list = []
        for provider in providers:
            # Get latest sync job
            latest_job = db.query(SyncJob).filter(
                SyncJob.provider_id == provider.id
            ).order_by(SyncJob.created_at.desc()).first()
            
            provider_info = {
                "id": str(provider.id),
                "name": provider.name,
                "provider": provider.provider,
                "enabled": provider.enabled,
                "auto_sync": provider.auto_sync,
                "sync_interval": provider.sync_interval,
                "last_sync_at": provider.last_sync_at.isoformat() if provider.last_sync_at else None,
                "latest_job": {
                    "id": str(latest_job.id),
                    "status": latest_job.status,
                    "started_at": latest_job.started_at.isoformat() if latest_job.started_at else None,
                    "completed_at": latest_job.completed_at.isoformat() if latest_job.completed_at else None
                } if latest_job else None
            }
            provider_list.append(provider_info)
        
        return {"providers": provider_list}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
