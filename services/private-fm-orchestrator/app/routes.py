"""
API routes for Private Foundation Model Orchestrator.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import structlog

from .models import (
    LearnerNamespace,
    MergeOperation,
    EventLog,
    NamespaceStatus,
    MergeStatus,
    FallbackReason
)
from .isolator import NamespaceIsolator

logger = structlog.get_logger()


# Request/Response models
class CreateNamespaceRequest(BaseModel):
    learner_id: UUID = Field(..., description="Unique identifier for the learner")
    base_fm_version: str = Field("1.0", description="Base foundation model version")
    initial_prompt: Optional[str] = Field(None, description="Initial system prompt for the namespace")
    configuration: Optional[Dict[str, Any]] = Field(None, description="Additional configuration parameters")


class NamespaceResponse(BaseModel):
    id: UUID
    learner_id: UUID
    status: NamespaceStatus
    base_fm_version: str
    version_count: int
    current_checkpoint_hash: str
    encryption_key_hash: str
    created_at: datetime
    updated_at: datetime
    last_merge_at: Optional[datetime]
    guardian_deletable_at: Optional[datetime]
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class MergeOperationResponse(BaseModel):
    id: UUID
    namespace_id: UUID
    operation_type: str
    status: MergeStatus
    source_checkpoint_hash: str
    target_checkpoint_hash: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    metadata: Optional[Dict[str, Any]]
    
    class Config:
        from_attributes = True


class TriggerMergeRequest(BaseModel):
    operation_type: str = Field("manual", description="Type of merge operation")
    force: bool = Field(False, description="Force merge even if conditions not met")


class InitiateFallbackRequest(BaseModel):
    reason: FallbackReason = Field(..., description="Reason for fallback recovery")
    target_fm_version: Optional[str] = Field(None, description="Target FM version for recovery")


class NamespaceHealthResponse(BaseModel):
    is_healthy: bool
    integrity_score: float
    version_lag: int
    checkpoint_size_mb: float
    last_health_check: datetime
    issues: List[str]


class EventLogResponse(BaseModel):
    id: UUID
    namespace_id: UUID
    learner_id: UUID
    event_type: str
    event_data: Dict[str, Any]
    checkpoint_hash: str
    created_at: datetime
    
    class Config:
        from_attributes = True


def create_router() -> APIRouter:
    """Create and configure the API router."""
    router = APIRouter()
    
    # Namespace endpoints
    
    @router.post("/namespaces", response_model=NamespaceResponse, status_code=status.HTTP_201_CREATED)
    async def create_namespace(
        request: CreateNamespaceRequest,
        isolator: NamespaceIsolator = Depends()
    ) -> NamespaceResponse:
        """Create a new learner namespace."""
        try:
            namespace = await isolator.create_namespace(
                request.learner_id,
                request.base_fm_version,
                request.initial_prompt,
                request.configuration or {}
            )
            return NamespaceResponse.from_orm(namespace)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Failed to create namespace", error=str(e), learner_id=str(request.learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create namespace"
            )
    
    @router.get("/namespaces/{learner_id}", response_model=NamespaceResponse)
    async def get_namespace(
        learner_id: UUID,
        db: AsyncSession = Depends()
    ) -> NamespaceResponse:
        """Get namespace for a learner."""
        try:
            result = await db.execute(
                select(LearnerNamespace)
                .where(LearnerNamespace.learner_id == learner_id)
            )
            namespace = result.scalar_one_or_none()
            
            if not namespace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Namespace not found"
                )
            
            return NamespaceResponse.from_orm(namespace)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get namespace", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve namespace"
            )
    
    @router.get("/namespaces", response_model=List[NamespaceResponse])
    async def list_namespaces(
        status_filter: Optional[NamespaceStatus] = Query(None, description="Filter by namespace status"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of namespaces to return"),
        offset: int = Query(0, ge=0, description="Number of namespaces to skip"),
        db: AsyncSession = Depends()
    ) -> List[NamespaceResponse]:
        """List namespaces with optional filtering."""
        try:
            query = select(LearnerNamespace).offset(offset).limit(limit)
            
            if status_filter:
                query = query.where(LearnerNamespace.status == status_filter)
            
            result = await db.execute(query)
            namespaces = result.scalars().all()
            
            return [NamespaceResponse.from_orm(ns) for ns in namespaces]
        except Exception as e:
            logger.error("Failed to list namespaces", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list namespaces"
            )
    
    @router.delete("/namespaces/{learner_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_namespace(
        learner_id: UUID,
        force: bool = Query(False, description="Force deletion even if guardian protection active"),
        isolator: NamespaceIsolator = Depends()
    ) -> None:
        """Delete a learner namespace."""
        try:
            success = await isolator.delete_namespace(learner_id, force)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Namespace not found or cannot be deleted"
                )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Failed to delete namespace", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete namespace"
            )
    
    # Health and monitoring endpoints
    
    @router.get("/namespaces/{learner_id}/health", response_model=NamespaceHealthResponse)
    async def check_namespace_health(
        learner_id: UUID,
        isolator: NamespaceIsolator = Depends()
    ) -> NamespaceHealthResponse:
        """Check health status of a namespace."""
        try:
            health = await isolator.check_namespace_health(learner_id)
            return NamespaceHealthResponse(
                is_healthy=health.is_healthy,
                integrity_score=health.integrity_score,
                version_lag=health.version_lag,
                checkpoint_size_mb=health.checkpoint_size_mb,
                last_health_check=health.last_health_check,
                issues=health.issues
            )
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Failed to check namespace health", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to check namespace health"
            )
    
    # Merge operation endpoints
    
    @router.post("/namespaces/{learner_id}/merge", response_model=MergeOperationResponse)
    async def trigger_merge(
        learner_id: UUID,
        request: TriggerMergeRequest,
        isolator: NamespaceIsolator = Depends()
    ) -> MergeOperationResponse:
        """Trigger a merge operation for a namespace."""
        try:
            merge_op = await isolator.trigger_merge(
                learner_id,
                request.operation_type,
                request.force
            )
            return MergeOperationResponse.from_orm(merge_op)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Failed to trigger merge", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to trigger merge operation"
            )
    
    @router.get("/namespaces/{learner_id}/merge-operations", response_model=List[MergeOperationResponse])
    async def list_merge_operations(
        learner_id: UUID,
        status_filter: Optional[MergeStatus] = Query(None, description="Filter by merge status"),
        limit: int = Query(50, ge=1, le=500, description="Maximum number of operations to return"),
        offset: int = Query(0, ge=0, description="Number of operations to skip"),
        db: AsyncSession = Depends()
    ) -> List[MergeOperationResponse]:
        """List merge operations for a namespace."""
        try:
            # First get the namespace
            ns_result = await db.execute(
                select(LearnerNamespace.id)
                .where(LearnerNamespace.learner_id == learner_id)
            )
            namespace_id = ns_result.scalar_one_or_none()
            
            if not namespace_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Namespace not found"
                )
            
            query = select(MergeOperation).where(
                MergeOperation.namespace_id == namespace_id
            ).order_by(MergeOperation.created_at.desc()).offset(offset).limit(limit)
            
            if status_filter:
                query = query.where(MergeOperation.status == status_filter)
            
            result = await db.execute(query)
            merge_ops = result.scalars().all()
            
            return [MergeOperationResponse.from_orm(op) for op in merge_ops]
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to list merge operations", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to list merge operations"
            )
    
    @router.get("/merge-operations/{operation_id}", response_model=MergeOperationResponse)
    async def get_merge_operation(
        operation_id: UUID,
        db: AsyncSession = Depends()
    ) -> MergeOperationResponse:
        """Get details of a specific merge operation."""
        try:
            result = await db.execute(
                select(MergeOperation)
                .where(MergeOperation.id == operation_id)
            )
            merge_op = result.scalar_one_or_none()
            
            if not merge_op:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Merge operation not found"
                )
            
            return MergeOperationResponse.from_orm(merge_op)
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get merge operation", error=str(e), operation_id=str(operation_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve merge operation"
            )
    
    # Fallback and recovery endpoints
    
    @router.post("/namespaces/{learner_id}/fallback", response_model=Dict[str, Any])
    async def initiate_fallback_recovery(
        learner_id: UUID,
        request: InitiateFallbackRequest,
        isolator: NamespaceIsolator = Depends()
    ) -> Dict[str, Any]:
        """Initiate fallback recovery for a namespace."""
        try:
            operation_id = await isolator.initiate_fallback_recovery(
                learner_id,
                request.reason,
                request.target_fm_version
            )
            return {
                "operation_id": str(operation_id),
                "message": "Fallback recovery initiated",
                "reason": request.reason.value,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except Exception as e:
            logger.error("Failed to initiate fallback recovery", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to initiate fallback recovery"
            )
    
    # Event and audit endpoints
    
    @router.get("/namespaces/{learner_id}/events", response_model=List[EventLogResponse])
    async def get_namespace_events(
        learner_id: UUID,
        event_type: Optional[str] = Query(None, description="Filter by event type"),
        limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
        offset: int = Query(0, ge=0, description="Number of events to skip"),
        db: AsyncSession = Depends()
    ) -> List[EventLogResponse]:
        """Get event logs for a namespace."""
        try:
            query = select(EventLog).where(
                EventLog.learner_id == learner_id
            ).order_by(EventLog.created_at.desc()).offset(offset).limit(limit)
            
            if event_type:
                query = query.where(EventLog.event_type == event_type)
            
            result = await db.execute(query)
            events = result.scalars().all()
            
            return [EventLogResponse.from_orm(event) for event in events]
        except Exception as e:
            logger.error("Failed to get namespace events", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve namespace events"
            )
    
    # Statistics and analytics endpoints
    
    @router.get("/namespaces/{learner_id}/stats", response_model=Dict[str, Any])
    async def get_namespace_stats(
        learner_id: UUID,
        db: AsyncSession = Depends()
    ) -> Dict[str, Any]:
        """Get statistics for a namespace."""
        try:
            # Get namespace
            ns_result = await db.execute(
                select(LearnerNamespace)
                .where(LearnerNamespace.learner_id == learner_id)
            )
            namespace = ns_result.scalar_one_or_none()
            
            if not namespace:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Namespace not found"
                )
            
            # Get merge operation counts
            merge_counts = await db.execute(
                select(MergeOperation.status, func.count(MergeOperation.id))
                .where(MergeOperation.namespace_id == namespace.id)
                .group_by(MergeOperation.status)
            )
            merge_stats = {status.value: count for status, count in merge_counts.all()}
            
            # Get event counts
            event_counts = await db.execute(
                select(EventLog.event_type, func.count(EventLog.id))
                .where(EventLog.learner_id == learner_id)
                .group_by(EventLog.event_type)
            )
            event_stats = {event_type: count for event_type, count in event_counts.all()}
            
            # Calculate uptime
            now = datetime.now(timezone.utc)
            uptime_hours = (now - namespace.created_at).total_seconds() / 3600
            
            return {
                "namespace_id": str(namespace.id),
                "learner_id": str(learner_id),
                "status": namespace.status.value,
                "version_count": namespace.version_count,
                "uptime_hours": round(uptime_hours, 2),
                "merge_operations": merge_stats,
                "events": event_stats,
                "last_merge_at": namespace.last_merge_at.isoformat() if namespace.last_merge_at else None,
                "created_at": namespace.created_at.isoformat(),
                "updated_at": namespace.updated_at.isoformat()
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Failed to get namespace stats", error=str(e), learner_id=str(learner_id))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve namespace statistics"
            )
    
    @router.get("/stats/global", response_model=Dict[str, Any])
    async def get_global_stats(
        db: AsyncSession = Depends()
    ) -> Dict[str, Any]:
        """Get global orchestrator statistics."""
        try:
            # Namespace counts by status
            ns_counts = await db.execute(
                select(LearnerNamespace.status, func.count(LearnerNamespace.id))
                .group_by(LearnerNamespace.status)
            )
            namespace_stats = {status.value: count for status, count in ns_counts.all()}
            
            # Total merge operations by status
            merge_counts = await db.execute(
                select(MergeOperation.status, func.count(MergeOperation.id))
                .group_by(MergeOperation.status)
            )
            merge_stats = {status.value: count for status, count in merge_counts.all()}
            
            # Recent activity (last 24 hours)
            recent_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            recent_namespaces = await db.execute(
                select(func.count(LearnerNamespace.id))
                .where(LearnerNamespace.created_at >= recent_cutoff)
            )
            recent_merges = await db.execute(
                select(func.count(MergeOperation.id))
                .where(MergeOperation.created_at >= recent_cutoff)
            )
            
            return {
                "total_namespaces": sum(namespace_stats.values()),
                "namespace_status_distribution": namespace_stats,
                "total_merge_operations": sum(merge_stats.values()),
                "merge_status_distribution": merge_stats,
                "recent_activity_24h": {
                    "new_namespaces": recent_namespaces.scalar(),
                    "merge_operations": recent_merges.scalar()
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error("Failed to get global stats", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve global statistics"
            )
    
    return router
