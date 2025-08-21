"""
Job queue management endpoints
Monitor and manage orchestrator and ingest service queues
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import logging

from app.auth import AdminUser, verify_admin_token, require_tenant_admin
from app.audit import log_admin_action
from app.config import settings
from app.models import (
    JobQueue, Job, JobStatus, JobPriority, JobAction, 
    JobActionResult, QueueStats
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/queues", response_model=List[JobQueue])
async def get_job_queues(admin: AdminUser = Depends(verify_admin_token)):
    """
    Get all job queues status
    Available to all staff roles (read-only)
    """
    await log_admin_action(
        admin.user_id,
        "job_queues_accessed",
        details={"access_level": "read_only"}
    )
    
    try:
        queues = await _fetch_all_queues()
        return queues
    except Exception as e:
        logger.error(f"Error fetching job queues: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job queues")


@router.get("/queues/stats", response_model=QueueStats)
async def get_queue_stats(admin: AdminUser = Depends(verify_admin_token)):
    """
    Get comprehensive queue statistics
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "queue_stats_accessed",
        details={"timestamp": datetime.utcnow()}
    )
    
    try:
        stats = await _fetch_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"Error fetching queue stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch queue statistics")


@router.get("/queues/{queue_name}/jobs", response_model=List[Job])
async def get_queue_jobs(
    queue_name: str,
    status: Optional[JobStatus] = None,
    priority: Optional[JobPriority] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get jobs in specific queue with filtering
    Available to all staff roles (read-only)
    """
    await log_admin_action(
        admin.user_id,
        "queue_jobs_accessed",
        details={
            "queue_name": queue_name,
            "filters": {"status": status, "priority": priority},
            "pagination": {"limit": limit, "offset": offset}
        }
    )
    
    try:
        jobs = await _fetch_queue_jobs(
            queue_name=queue_name,
            status=status,
            priority=priority,
            limit=limit,
            offset=offset
        )
        return jobs
    except Exception as e:
        logger.error(f"Error fetching jobs for queue {queue_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch jobs for queue {queue_name}")


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job_details(
    job_id: str,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get detailed job information
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "job_details_accessed",
        details={"job_id": job_id},
        target_resource=f"job:{job_id}"
    )
    
    try:
        job = await _fetch_job_by_id(job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching job details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch job details")


@router.post("/jobs/{job_id}/requeue", response_model=JobActionResult)
async def requeue_job(
    job_id: str,
    action: JobAction,
    admin: AdminUser = Depends(require_tenant_admin)
):
    """
    Requeue a failed or cancelled job
    Requires tenant admin or system admin role
    """
    await log_admin_action(
        admin.user_id,
        "job_requeue_attempted",
        details={
            "job_id": job_id,
            "reason": action.reason,
            "force": action.force
        },
        target_resource=f"job:{job_id}"
    )
    
    try:
        # Fetch job to validate status
        job = await _fetch_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job can be requeued
        if job.status not in [JobStatus.FAILED, JobStatus.CANCELLED]:
            if not action.force:
                raise HTTPException(
                    status_code=400,
                    detail=f"Job status '{job.status}' cannot be requeued. Use force=true to override."
                )
        
        # Perform requeue action
        result = await _perform_job_action(job_id, "requeue", action.reason, admin.user_id)
        
        # Log the action result
        await log_admin_action(
            admin.user_id,
            "job_requeued",
            details={
                "job_id": job_id,
                "success": result.success,
                "message": result.message,
                "reason": action.reason
            },
            target_resource=f"job:{job_id}",
            success=result.success
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requeuing job {job_id}: {e}")
        await log_admin_action(
            admin.user_id,
            "job_requeue_failed",
            details={"job_id": job_id, "error": str(e)},
            target_resource=f"job:{job_id}",
            success=False
        )
        raise HTTPException(status_code=500, detail="Failed to requeue job")


@router.post("/jobs/{job_id}/cancel", response_model=JobActionResult)
async def cancel_job(
    job_id: str,
    action: JobAction,
    admin: AdminUser = Depends(require_tenant_admin)
):
    """
    Cancel a pending or running job
    Requires tenant admin or system admin role
    """
    await log_admin_action(
        admin.user_id,
        "job_cancel_attempted",
        details={
            "job_id": job_id,
            "reason": action.reason,
            "force": action.force
        },
        target_resource=f"job:{job_id}"
    )
    
    try:
        # Fetch job to validate status
        job = await _fetch_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job can be cancelled
        if job.status not in [JobStatus.PENDING, JobStatus.RUNNING]:
            if not action.force:
                raise HTTPException(
                    status_code=400,
                    detail=f"Job status '{job.status}' cannot be cancelled. Use force=true to override."
                )
        
        # Perform cancel action
        result = await _perform_job_action(job_id, "cancel", action.reason, admin.user_id)
        
        # Log the action result
        await log_admin_action(
            admin.user_id,
            "job_cancelled",
            details={
                "job_id": job_id,
                "success": result.success,
                "message": result.message,
                "reason": action.reason
            },
            target_resource=f"job:{job_id}",
            success=result.success
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job {job_id}: {e}")
        await log_admin_action(
            admin.user_id,
            "job_cancel_failed",
            details={"job_id": job_id, "error": str(e)},
            target_resource=f"job:{job_id}",
            success=False
        )
        raise HTTPException(status_code=500, detail="Failed to cancel job")


@router.post("/jobs/{job_id}/retry", response_model=JobActionResult)
async def retry_job(
    job_id: str,
    action: JobAction,
    admin: AdminUser = Depends(require_tenant_admin)
):
    """
    Retry a failed job
    Requires tenant admin or system admin role
    """
    await log_admin_action(
        admin.user_id,
        "job_retry_attempted",
        details={
            "job_id": job_id,
            "reason": action.reason,
            "force": action.force
        },
        target_resource=f"job:{job_id}"
    )
    
    try:
        # Fetch job to validate status and retry count
        job = await _fetch_job_by_id(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        # Check if job can be retried
        if job.status != JobStatus.FAILED:
            if not action.force:
                raise HTTPException(
                    status_code=400,
                    detail=f"Only failed jobs can be retried. Current status: {job.status}"
                )
        
        if job.retry_count >= job.max_retries:
            if not action.force:
                raise HTTPException(
                    status_code=400,
                    detail=f"Job has exceeded max retries ({job.max_retries}). Use force=true to override."
                )
        
        # Perform retry action
        result = await _perform_job_action(job_id, "retry", action.reason, admin.user_id)
        
        # Log the action result
        await log_admin_action(
            admin.user_id,
            "job_retried",
            details={
                "job_id": job_id,
                "success": result.success,
                "message": result.message,
                "reason": action.reason,
                "retry_count": job.retry_count + 1
            },
            target_resource=f"job:{job_id}",
            success=result.success
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job {job_id}: {e}")
        await log_admin_action(
            admin.user_id,
            "job_retry_failed",
            details={"job_id": job_id, "error": str(e)},
            target_resource=f"job:{job_id}",
            success=False
        )
        raise HTTPException(status_code=500, detail="Failed to retry job")


@router.get("/jobs/failed")
async def get_failed_jobs(
    hours: int = Query(24, ge=1, le=168),  # Last 1-168 hours
    limit: int = Query(50, le=200),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get recently failed jobs for incident management
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "failed_jobs_accessed",
        details={"hours_back": hours, "limit": limit}
    )
    
    try:
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        failed_jobs = await _fetch_failed_jobs_since(since_time, limit)
        
        return {
            "timeframe_hours": hours,
            "since_time": since_time,
            "failed_count": len(failed_jobs),
            "jobs": failed_jobs
        }
    except Exception as e:
        logger.error(f"Error fetching failed jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch failed jobs")


async def _fetch_all_queues() -> List[JobQueue]:
    """Fetch all job queues from services"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        return [
            JobQueue(
                name="orchestrator-main",
                service="orchestrator-svc",
                total_jobs=1250,
                pending_jobs=12,
                running_jobs=3,
                failed_jobs=2,
                avg_processing_time_minutes=4.2,
                health_status="healthy",
                last_updated=datetime.utcnow()
            ),
            JobQueue(
                name="ingest-coursework",
                service="ingest-svc",
                total_jobs=845,
                pending_jobs=8,
                running_jobs=2,
                failed_jobs=1,
                avg_processing_time_minutes=2.1,
                health_status="healthy",
                last_updated=datetime.utcnow()
            ),
            JobQueue(
                name="ingest-assessment",
                service="ingest-svc",
                total_jobs=342,
                pending_jobs=5,
                running_jobs=1,
                failed_jobs=0,
                avg_processing_time_minutes=1.8,
                health_status="healthy",
                last_updated=datetime.utcnow()
            )
        ]
    
    # Production: fetch from services
    queues = []
    
    # Fetch from orchestrator service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ORCHESTRATOR_SERVICE_URL}/admin/queues",
                timeout=10.0
            )
            if response.status_code == 200:
                queues.extend([JobQueue(**q) for q in response.json()])
    except Exception as e:
        logger.warning(f"Could not fetch orchestrator queues: {e}")
    
    # Fetch from ingest service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.INGEST_SERVICE_URL}/admin/queues",
                timeout=10.0
            )
            if response.status_code == 200:
                queues.extend([JobQueue(**q) for q in response.json()])
    except Exception as e:
        logger.warning(f"Could not fetch ingest queues: {e}")
    
    return queues


async def _fetch_queue_stats() -> QueueStats:
    """Fetch comprehensive queue statistics"""
    
    # Mock stats for development
    if settings.ENVIRONMENT == "development":
        return QueueStats(
            total_queues=3,
            healthy_queues=3,
            total_jobs=2437,
            pending_jobs=25,
            failed_jobs=3,
            avg_processing_time=2.7,
            throughput_per_minute=15.3,
            error_rate=0.001
        )
    
    # Production: aggregate from all services
    return QueueStats(
        total_queues=0,
        healthy_queues=0,
        total_jobs=0,
        pending_jobs=0,
        failed_jobs=0,
        avg_processing_time=0,
        throughput_per_minute=0,
        error_rate=0
    )


async def _fetch_queue_jobs(
    queue_name: str,
    status: Optional[JobStatus] = None,
    priority: Optional[JobPriority] = None,
    limit: int = 50,
    offset: int = 0
) -> List[Job]:
    """Fetch jobs from specific queue"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        mock_jobs = [
            Job(
                id="job_001",
                queue_name=queue_name,
                type="process_coursework",
                status=JobStatus.RUNNING,
                priority=JobPriority.MEDIUM,
                tenant_id="tenant_001",
                created_at=datetime.utcnow() - timedelta(minutes=5),
                started_at=datetime.utcnow() - timedelta(minutes=2),
                retry_count=0,
                max_retries=3,
                progress_percentage=65.0,
                metadata={
                    "coursework_id": "cw_123",
                    "learner_count": 25
                }
            ),
            Job(
                id="job_002",
                queue_name=queue_name,
                type="generate_assessment",
                status=JobStatus.FAILED,
                priority=JobPriority.HIGH,
                tenant_id="tenant_001",
                created_at=datetime.utcnow() - timedelta(hours=1),
                started_at=datetime.utcnow() - timedelta(minutes=45),
                completed_at=datetime.utcnow() - timedelta(minutes=30),
                retry_count=2,
                max_retries=3,
                error_message="Timeout connecting to AI service",
                metadata={
                    "assessment_type": "adaptive",
                    "subject": "mathematics"
                }
            ),
            Job(
                id="job_003",
                queue_name=queue_name,
                type="ingest_data",
                status=JobStatus.PENDING,
                priority=JobPriority.LOW,
                tenant_id="tenant_002",
                created_at=datetime.utcnow() - timedelta(minutes=10),
                retry_count=0,
                max_retries=3,
                metadata={
                    "data_source": "csv_upload",
                    "record_count": 1500
                }
            )
        ]
        
        # Apply filters
        filtered = mock_jobs
        if status:
            filtered = [j for j in filtered if j.status == status]
        if priority:
            filtered = [j for j in filtered if j.priority == priority]
        
        return filtered[offset:offset + limit]
    
    # Production: call appropriate service
    return []


async def _fetch_job_by_id(job_id: str) -> Optional[Job]:
    """Fetch specific job by ID"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        return Job(
            id=job_id,
            queue_name="orchestrator-main",
            type="process_coursework",
            status=JobStatus.FAILED,
            priority=JobPriority.HIGH,
            tenant_id="tenant_001",
            created_at=datetime.utcnow() - timedelta(hours=1),
            started_at=datetime.utcnow() - timedelta(minutes=45),
            completed_at=datetime.utcnow() - timedelta(minutes=30),
            retry_count=2,
            max_retries=3,
            error_message="Connection timeout to external AI service",
            metadata={
                "coursework_id": "cw_456",
                "learner_count": 50,
                "processing_stage": "content_analysis"
            }
        )
    
    # Production: search across services
    return None


async def _perform_job_action(
    job_id: str,
    action: str,
    reason: str,
    performed_by: str
) -> JobActionResult:
    """Perform job management action"""
    
    # Mock action for development
    if settings.ENVIRONMENT == "development":
        success = True  # Simulate success most of the time
        message = f"Job {action} completed successfully"
        
        return JobActionResult(
            job_id=job_id,
            action=action,
            success=success,
            message=message,
            timestamp=datetime.utcnow(),
            performed_by=performed_by
        )
    
    # Production: call appropriate service
    return JobActionResult(
        job_id=job_id,
        action=action,
        success=False,
        message="Service integration not configured",
        timestamp=datetime.utcnow(),
        performed_by=performed_by
    )


async def _fetch_failed_jobs_since(since_time: datetime, limit: int) -> List[Job]:
    """Fetch jobs that failed since specified time"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        return [
            Job(
                id="job_failed_001",
                queue_name="orchestrator-main",
                type="process_coursework",
                status=JobStatus.FAILED,
                priority=JobPriority.HIGH,
                tenant_id="tenant_001",
                created_at=since_time + timedelta(hours=2),
                started_at=since_time + timedelta(hours=2, minutes=5),
                completed_at=since_time + timedelta(hours=2, minutes=15),
                retry_count=3,
                max_retries=3,
                error_message="AI service unavailable",
                metadata={"failure_category": "external_dependency"}
            )
        ]
    
    # Production: search across services
    return []
