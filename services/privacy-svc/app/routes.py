"""
API routes for Privacy Service
Handles data export, erasure, and privacy request management
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Request
from fastapi.responses import FileResponse
import asyncpg
import structlog

from .models import (
    ExportRequest, ErasureRequest, PrivacyRequestResponse,
    ExportStatusResponse, ErasureStatusResponse, DataSummaryResponse,
    RetentionPolicyResponse, DataCategory, PrivacyRequestType, PrivacyRequestStatus
)
from .database import get_db_pool, log_audit_event
from .exporter import DataExporter
from .eraser import DataEraser

logger = structlog.get_logger()
router = APIRouter()

# Initialize components
data_exporter = DataExporter(storage_path="/tmp/privacy-exports")
data_eraser = DataEraser()

@router.post("/export", response_model=PrivacyRequestResponse)
async def request_data_export(
    request: ExportRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
) -> PrivacyRequestResponse:
    """
    Request data export for a learner
    Creates a ZIP bundle with PII redaction where needed
    """
    
    logger.info("Data export requested", learner_id=str(request.learner_id))
    
    try:
        pool = await get_db_pool()
        
        # Check for existing pending/processing export requests
        async with pool.acquire() as conn:
            existing_request = await conn.fetchrow(
                """
                SELECT id, status FROM privacy_requests 
                WHERE learner_id = $1 AND request_type = 'export' 
                AND status IN ('pending', 'processing')
                ORDER BY created_at DESC LIMIT 1
                """,
                request.learner_id
            )
            
            if existing_request:
                raise HTTPException(
                    status_code=409,
                    detail=f"Export request already in progress: {existing_request['id']}"
                )
            
            # Verify learner exists
            learner_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM users WHERE id = $1)",
                request.learner_id
            )
            if not learner_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Learner not found"
                )
            
            # Create privacy request record
            request_id = await conn.fetchval(
                """
                INSERT INTO privacy_requests 
                (learner_id, request_type, data_categories, export_format, 
                 include_metadata, requested_by, requester_ip, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
                """,
                request.learner_id,
                PrivacyRequestType.EXPORT.value,
                [cat.value for cat in request.data_categories] if request.data_categories else None,
                request.export_format,
                request.include_metadata,
                "api_user",  # TODO: Extract from JWT token
                http_request.client.host if http_request.client else None,
                datetime.utcnow() + timedelta(days=30)  # Export expires in 30 days
            )
            
            # Log audit event
            await log_audit_event(
                "export_requested",
                learner_id=str(request.learner_id),
                request_id=str(request_id),
                event_data={
                    "categories": [cat.value for cat in request.data_categories] if request.data_categories else "all",
                    "format": request.export_format,
                    "include_metadata": request.include_metadata
                },
                user_id="api_user",
                ip_address=http_request.client.host if http_request.client else None
            )
            
            # Schedule background export task
            categories = request.data_categories or list(DataCategory)
            background_tasks.add_task(
                create_export_bundle_task,
                request_id,
                request.learner_id,
                categories,
                request.export_format,
                request.include_metadata
            )
            
            # Return immediate response
            return PrivacyRequestResponse(
                request_id=request_id,
                learner_id=request.learner_id,
                request_type=PrivacyRequestType.EXPORT,
                status=PrivacyRequestStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=None,
                completed_at=None,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            
    except Exception as e:
        logger.error("Failed to create export request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create export request")

@router.post("/erase", response_model=PrivacyRequestResponse)
async def request_data_erasure(
    request: ErasureRequest,
    background_tasks: BackgroundTasks,
    http_request: Request
) -> PrivacyRequestResponse:
    """
    Request irreversible data erasure for a learner
    Queues erasure job and logs receipt
    """
    
    logger.info("Data erasure requested", 
               learner_id=str(request.learner_id),
               reason=request.reason)
    
    try:
        pool = await get_db_pool()
        
        # Check for existing erasure requests
        async with pool.acquire() as conn:
            existing_request = await conn.fetchrow(
                """
                SELECT id, status FROM privacy_requests 
                WHERE learner_id = $1 AND request_type = 'erase'
                AND status IN ('pending', 'processing', 'completed')
                ORDER BY created_at DESC LIMIT 1
                """,
                request.learner_id
            )
            
            if existing_request and existing_request['status'] == 'completed':
                raise HTTPException(
                    status_code=409,
                    detail=f"Learner data already erased: {existing_request['id']}"
                )
            elif existing_request:
                raise HTTPException(
                    status_code=409,
                    detail=f"Erasure request already in progress: {existing_request['id']}"
                )
            
            # Verify learner exists
            learner_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM users WHERE id = $1 AND erased_at IS NULL)",
                request.learner_id
            )
            if not learner_exists:
                raise HTTPException(
                    status_code=404,
                    detail="Learner not found or already erased"
                )
            
            # Create privacy request record
            request_id = await conn.fetchval(
                """
                INSERT INTO privacy_requests 
                (learner_id, request_type, data_categories, requested_by, requester_ip)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
                """,
                request.learner_id,
                PrivacyRequestType.ERASE.value,
                [cat.value for cat in request.data_categories] if request.data_categories else None,
                "api_user",  # TODO: Extract from JWT token
                http_request.client.host if http_request.client else None
            )
            
            # Log audit event for receipt
            await log_audit_event(
                "erasure_requested",
                learner_id=str(request.learner_id),
                request_id=str(request_id),
                event_data={
                    "categories": [cat.value for cat in request.data_categories] if request.data_categories else "all",
                    "reason": request.reason,
                    "confirm_irreversible": request.confirm_irreversible,
                    "request_received": datetime.utcnow().isoformat()
                },
                user_id="api_user",
                ip_address=http_request.client.host if http_request.client else None
            )
            
            # Schedule background erasure task
            categories = request.data_categories or [
                cat for cat in DataCategory if cat not in [DataCategory.SYSTEM]
            ]  # Exclude system logs by default
            
            background_tasks.add_task(
                process_erasure_task,
                request_id,
                request.learner_id,
                categories,
                request.reason
            )
            
            # Return immediate response
            return PrivacyRequestResponse(
                request_id=request_id,
                learner_id=request.learner_id,
                request_type=PrivacyRequestType.ERASE,
                status=PrivacyRequestStatus.PENDING,
                created_at=datetime.utcnow(),
                updated_at=None,
                completed_at=None,
                expires_at=None
            )
            
    except Exception as e:
        logger.error("Failed to create erasure request", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create erasure request")

@router.get("/export/{request_id}/status", response_model=ExportStatusResponse)
async def get_export_status(request_id: UUID) -> ExportStatusResponse:
    """Get status of data export request"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            request_data = await conn.fetchrow(
                """
                SELECT id, status, created_at, completed_at, expires_at, 
                       file_path, file_size_bytes, records_processed, error_message
                FROM privacy_requests 
                WHERE id = $1 AND request_type = 'export'
                """,
                request_id
            )
            
            if not request_data:
                raise HTTPException(status_code=404, detail="Export request not found")
            
            # Calculate progress for processing requests
            progress_percentage = None
            if request_data['status'] == 'processing':
                # Estimate progress based on time elapsed (rough estimate)
                elapsed = (datetime.utcnow() - request_data['created_at']).total_seconds()
                estimated_total = 300  # 5 minutes average
                progress_percentage = min(95.0, (elapsed / estimated_total) * 100)
            elif request_data['status'] == 'completed':
                progress_percentage = 100.0
            
            # Generate download URL for completed exports
            download_url = None
            if request_data['status'] == 'completed' and request_data['file_path']:
                download_url = f"/api/v1/export/{request_id}/download"
            
            return ExportStatusResponse(
                request_id=request_id,
                status=PrivacyRequestStatus(request_data['status']),
                progress_percentage=progress_percentage,
                estimated_completion=request_data['completed_at'],
                download_url=download_url,
                expires_at=request_data['expires_at'],
                file_size_bytes=request_data['file_size_bytes'],
                error_message=request_data['error_message']
            )
            
    except Exception as e:
        logger.error("Failed to get export status", request_id=str(request_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get export status")

@router.get("/export/{request_id}/download")
async def download_export(request_id: UUID):
    """Download export file"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            request_data = await conn.fetchrow(
                """
                SELECT file_path, status, expires_at, learner_id
                FROM privacy_requests 
                WHERE id = $1 AND request_type = 'export'
                """,
                request_id
            )
            
            if not request_data:
                raise HTTPException(status_code=404, detail="Export request not found")
            
            if request_data['status'] != 'completed':
                raise HTTPException(status_code=409, detail="Export not yet completed")
            
            if request_data['expires_at'] and datetime.utcnow() > request_data['expires_at']:
                raise HTTPException(status_code=410, detail="Export file has expired")
            
            file_path = request_data['file_path']
            if not file_path or not Path(file_path).exists():
                raise HTTPException(status_code=404, detail="Export file not found")
            
            # Log download event
            await log_audit_event(
                "export_downloaded",
                learner_id=str(request_data['learner_id']),
                request_id=str(request_id),
                event_data={"download_timestamp": datetime.utcnow().isoformat()}
            )
            
            return FileResponse(
                path=file_path,
                filename=f"learner_data_{request_data['learner_id']}.zip",
                media_type="application/zip"
            )
            
    except Exception as e:
        logger.error("Failed to download export", request_id=str(request_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to download export")

@router.get("/erase/{request_id}/status", response_model=ErasureStatusResponse)
async def get_erasure_status(request_id: UUID) -> ErasureStatusResponse:
    """Get status of data erasure request"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            request_data = await conn.fetchrow(
                """
                SELECT id, status, completed_at, records_processed, error_message
                FROM privacy_requests 
                WHERE id = $1 AND request_type = 'erase'
                """,
                request_id
            )
            
            if not request_data:
                raise HTTPException(status_code=404, detail="Erasure request not found")
            
            # Get audit trail ID for completed erasures
            audit_trail_id = None
            if request_data['status'] == 'completed':
                audit_record = await conn.fetchrow(
                    """
                    SELECT id FROM privacy_audit_log 
                    WHERE request_id = $1 AND event_type = 'erasure_completed'
                    ORDER BY timestamp DESC LIMIT 1
                    """,
                    request_id
                )
                if audit_record:
                    audit_trail_id = audit_record['id']
            
            return ErasureStatusResponse(
                request_id=request_id,
                status=PrivacyRequestStatus(request_data['status']),
                records_processed=request_data['records_processed'],
                completed_at=request_data['completed_at'],
                audit_trail_id=audit_trail_id,
                error_message=request_data['error_message']
            )
            
    except Exception as e:
        logger.error("Failed to get erasure status", request_id=str(request_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get erasure status")

@router.get("/learner/{learner_id}/summary", response_model=DataSummaryResponse)
async def get_learner_data_summary(learner_id: UUID) -> DataSummaryResponse:
    """Get summary of data held for a learner"""
    
    try:
        pool = await get_db_pool()
        data_categories = {}
        total_records = 0
        earliest_data = None
        latest_data = None
        
        # Query data by category
        category_queries = {
            DataCategory.PROFILE: "SELECT COUNT(*) as count, MIN(created_at) as earliest, MAX(updated_at) as latest FROM users WHERE id = $1",
            DataCategory.LEARNING: "SELECT COUNT(*) as count, MIN(started_at) as earliest, MAX(completed_at) as latest FROM learning_sessions WHERE user_id = $1",
            DataCategory.PROGRESS: "SELECT COUNT(*) as count, MIN(created_at) as earliest, MAX(last_accessed) as latest FROM progress_tracking WHERE user_id = $1",
            DataCategory.ASSESSMENTS: "SELECT COUNT(*) as count, MIN(created_at) as earliest, MAX(completed_at) as latest FROM assessment_results WHERE user_id = $1",
            DataCategory.INTERACTIONS: "SELECT COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM user_interactions WHERE user_id = $1",
            DataCategory.ANALYTICS: "SELECT COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM analytics_events WHERE user_id = $1",
            DataCategory.SYSTEM: "SELECT COUNT(*) as count, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM audit_logs WHERE user_id = $1"
        }
        
        async with pool.acquire() as conn:
            for category, query in category_queries.items():
                try:
                    result = await conn.fetchrow(query, learner_id)
                    if result:
                        count = result['count'] or 0
                        data_categories[category] = {
                            "record_count": count,
                            "earliest_record": result['earliest'],
                            "latest_record": result['latest']
                        }
                        total_records += count
                        
                        # Track overall earliest/latest
                        if result['earliest']:
                            if not earliest_data or result['earliest'] < earliest_data:
                                earliest_data = result['earliest']
                        if result['latest']:
                            if not latest_data or result['latest'] > latest_data:
                                latest_data = result['latest']
                                
                except Exception as e:
                    logger.warning("Failed to query category", category=category.value, error=str(e))
                    data_categories[category] = {"record_count": 0, "error": str(e)}
        
        return DataSummaryResponse(
            learner_id=learner_id,
            data_categories=data_categories,
            total_records=total_records,
            earliest_data=earliest_data,
            latest_data=latest_data
        )
        
    except Exception as e:
        logger.error("Failed to get learner data summary", learner_id=str(learner_id), error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get data summary")

@router.get("/retention-policies", response_model=List[RetentionPolicyResponse])
async def get_retention_policies() -> List[RetentionPolicyResponse]:
    """Get current data retention policies"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            policies = await conn.fetch(
                """
                SELECT data_category, retention_days, checkpoint_count, 
                       policy_description, legal_basis
                FROM data_retention_policies 
                WHERE active = true
                ORDER BY data_category
                """
            )
            
            return [
                RetentionPolicyResponse(
                    data_category=DataCategory(policy['data_category']),
                    retention_days=policy['retention_days'],
                    checkpoint_count=policy['checkpoint_count'],
                    policy_description=policy['policy_description'],
                    legal_basis=policy['legal_basis']
                )
                for policy in policies
            ]
            
    except Exception as e:
        logger.error("Failed to get retention policies", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get retention policies")

# Background task functions
async def create_export_bundle_task(
    request_id: UUID,
    learner_id: UUID,
    data_categories: List[DataCategory],
    export_format: str,
    include_metadata: bool
):
    """Background task to create export bundle"""
    try:
        await data_exporter.create_export_bundle(
            request_id=request_id,
            learner_id=learner_id,
            data_categories=data_categories,
            export_format=export_format,
            include_metadata=include_metadata
        )
    except Exception as e:
        logger.error("Export bundle task failed", 
                    request_id=str(request_id), 
                    error=str(e))

async def process_erasure_task(
    request_id: UUID,
    learner_id: UUID,
    data_categories: List[DataCategory],
    reason: Optional[str]
):
    """Background task to process data erasure"""
    try:
        await data_eraser.process_erasure_request(
            request_id=request_id,
            learner_id=learner_id,
            data_categories=data_categories,
            reason=reason
        )
    except Exception as e:
        logger.error("Erasure task failed", 
                    request_id=str(request_id), 
                    error=str(e))
