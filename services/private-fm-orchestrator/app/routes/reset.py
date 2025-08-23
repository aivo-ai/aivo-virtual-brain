"""
Adapter Reset Routes for Private Foundation Model Orchestrator (S5-08)
Per-subject adapter reset with approval workflow and orchestrator execution
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update
import structlog
import httpx

from ..models import (
    LearnerNamespace, 
    EventLog,
    NamespaceStatus,
    AdapterResetRequest,
    AdapterResetStatus
)
from ..database import get_db_session
from ..isolator import NamespaceIsolator

logger = structlog.get_logger()
router = APIRouter(prefix="/reset", tags=["adapter-reset"])


# Request/Response Models
class AdapterResetRequestModel(BaseModel):
    """Request to reset a learner's adapter for a specific subject."""
    learner_id: UUID = Field(..., description="Unique identifier for the learner")
    subject: str = Field(..., description="Subject to reset (e.g., 'math', 'reading')")
    reason: str = Field(..., description="Reason for the reset request")
    requested_by: UUID = Field(..., description="User ID of the requester")
    requester_role: str = Field(..., description="Role of the requester (guardian, teacher)")


class AdapterResetResponse(BaseModel):
    """Response for adapter reset request."""
    request_id: UUID
    status: str
    approval_required: bool
    approval_request_id: Optional[UUID] = None
    message: str
    estimated_completion_time: Optional[str] = None


class AdapterResetStatusResponse(BaseModel):
    """Response for checking adapter reset status."""
    request_id: UUID
    status: AdapterResetStatus
    progress_percent: int
    current_stage: Optional[str] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    events_replayed: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


# Dependency for HTTP client
async def get_http_client():
    """Get HTTP client for service communication."""
    return httpx.AsyncClient(timeout=30.0)


@router.post("/", response_model=AdapterResetResponse)
async def request_adapter_reset(
    request: AdapterResetRequestModel,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    http_client: httpx.AsyncClient = Depends(get_http_client)
):
    """
    Request an adapter reset for a specific subject.
    
    This endpoint:
    1. Validates the request and learner permissions
    2. Creates an approval request if guardian approval is needed
    3. If auto-approved, queues the reset operation
    4. Returns the request status
    """
    try:
        logger.info(
            "Adapter reset requested",
            learner_id=str(request.learner_id),
            subject=request.subject,
            requested_by=str(request.requested_by),
            requester_role=request.requester_role
        )
        
        # Validate learner namespace exists
        namespace_result = await db.execute(
            select(LearnerNamespace).where(
                LearnerNamespace.learner_id == request.learner_id
            )
        )
        namespace = namespace_result.scalar_one_or_none()
        
        if not namespace:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Learner namespace not found for learner {request.learner_id}"
            )
        
        # Validate subject exists in namespace
        if request.subject not in namespace.subjects:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Subject '{request.subject}' not found in learner's subjects"
            )
        
        # Check if there's already a pending reset for this learner/subject
        existing_reset = await db.execute(
            select(AdapterResetRequest).where(
                and_(
                    AdapterResetRequest.learner_id == request.learner_id,
                    AdapterResetRequest.subject == request.subject,
                    AdapterResetRequest.status.in_([
                        AdapterResetStatus.PENDING_APPROVAL,
                        AdapterResetStatus.APPROVED,
                        AdapterResetStatus.EXECUTING
                    ])
                )
            )
        )
        if existing_reset.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A reset request is already pending or in progress for this subject"
            )
        
        # Create the reset request record
        reset_request = AdapterResetRequest(
            id=uuid4(),
            learner_id=request.learner_id,
            subject=request.subject,
            reason=request.reason,
            requested_by=request.requested_by,
            requester_role=request.requester_role,
            status=AdapterResetStatus.PENDING_APPROVAL,
            created_at=datetime.now(timezone.utc)
        )
        
        db.add(reset_request)
        await db.flush()  # Get the ID without committing
        
        # Determine if approval is required
        requires_approval = await _requires_guardian_approval(
            request.requester_role, 
            request.learner_id,
            http_client
        )
        
        approval_request_id = None
        
        if requires_approval:
            # Create approval request via approval service
            approval_request_id = await _create_approval_request(
                reset_request, 
                http_client
            )
            
            reset_request.approval_request_id = approval_request_id
            reset_request.status = AdapterResetStatus.PENDING_APPROVAL
            
        else:
            # Auto-approve for guardians and authorized teachers
            reset_request.status = AdapterResetStatus.APPROVED
            reset_request.approved_at = datetime.now(timezone.utc)
            reset_request.approved_by = request.requested_by
            
            # Queue the reset operation
            background_tasks.add_task(
                _execute_adapter_reset,
                reset_request.id,
                db
            )
        
        await db.commit()
        
        # Create audit log entry
        await _create_audit_entry(
            reset_request,
            "ADAPTER_RESET_REQUESTED",
            http_client
        )
        
        response = AdapterResetResponse(
            request_id=reset_request.id,
            status=reset_request.status.value,
            approval_required=requires_approval,
            approval_request_id=approval_request_id,
            message="Reset request created successfully" if requires_approval 
                   else "Reset approved and queued for execution",
            estimated_completion_time="5-10 minutes" if not requires_approval else None
        )
        
        logger.info(
            "Adapter reset request created",
            request_id=str(reset_request.id),
            requires_approval=requires_approval,
            status=reset_request.status.value
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating adapter reset request", error=str(e))
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create adapter reset request"
        )


@router.get("/{request_id}/status", response_model=AdapterResetStatusResponse)
async def get_reset_status(
    request_id: UUID,
    db: AsyncSession = Depends(get_db_session)
):
    """Get the status of an adapter reset request."""
    try:
        result = await db.execute(
            select(AdapterResetRequest).where(
                AdapterResetRequest.id == request_id
            )
        )
        reset_request = result.scalar_one_or_none()
        
        if not reset_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reset request not found"
            )
        
        return AdapterResetStatusResponse(
            request_id=reset_request.id,
            status=reset_request.status,
            progress_percent=reset_request.progress_percent or 0,
            current_stage=reset_request.current_stage,
            error_message=reset_request.error_message,
            started_at=reset_request.started_at,
            completed_at=reset_request.completed_at,
            events_replayed=reset_request.events_replayed,
            metadata=reset_request.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting reset status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get reset status"
        )


@router.post("/webhook/approval-decision")
async def handle_approval_decision(
    approval_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session),
    http_client: httpx.AsyncClient = Depends(get_http_client)
):
    """
    Webhook endpoint to handle approval decisions from the approval service.
    
    Expected payload:
    {
        "approval_request_id": "uuid",
        "status": "approved|rejected",
        "approved_by": "uuid",
        "decision_reason": "string"
    }
    """
    try:
        approval_request_id = approval_data.get("approval_request_id")
        decision_status = approval_data.get("status")
        approved_by = approval_data.get("approved_by")
        
        if not all([approval_request_id, decision_status]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required fields in approval webhook"
            )
        
        # Find the reset request
        result = await db.execute(
            select(AdapterResetRequest).where(
                AdapterResetRequest.approval_request_id == UUID(approval_request_id)
            )
        )
        reset_request = result.scalar_one_or_none()
        
        if not reset_request:
            logger.warning("Reset request not found for approval", approval_id=approval_request_id)
            return {"status": "ignored", "reason": "reset_request_not_found"}
        
        if decision_status == "approved":
            # Approve the reset request
            reset_request.status = AdapterResetStatus.APPROVED
            reset_request.approved_at = datetime.now(timezone.utc)
            reset_request.approved_by = UUID(approved_by) if approved_by else None
            
            await db.commit()
            
            # Queue the reset operation
            background_tasks.add_task(
                _execute_adapter_reset,
                reset_request.id,
                db
            )
            
            # Create audit entry
            await _create_audit_entry(
                reset_request,
                "ADAPTER_RESET_APPROVED",
                http_client
            )
            
            logger.info(
                "Adapter reset approved and queued",
                request_id=str(reset_request.id),
                approved_by=approved_by
            )
            
        elif decision_status == "rejected":
            # Reject the reset request
            reset_request.status = AdapterResetStatus.REJECTED
            reset_request.rejected_at = datetime.now(timezone.utc)
            reset_request.rejected_by = UUID(approved_by) if approved_by else None
            reset_request.rejection_reason = approval_data.get("decision_reason")
            
            await db.commit()
            
            # Create audit entry
            await _create_audit_entry(
                reset_request,
                "ADAPTER_RESET_REJECTED",
                http_client
            )
            
            logger.info(
                "Adapter reset rejected",
                request_id=str(reset_request.id),
                rejected_by=approved_by,
                reason=reset_request.rejection_reason
            )
        
        return {"status": "processed"}
        
    except Exception as e:
        logger.error("Error handling approval decision", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process approval decision"
        )


# Helper Functions

async def _requires_guardian_approval(
    requester_role: str, 
    learner_id: UUID,
    http_client: httpx.AsyncClient
) -> bool:
    """Determine if guardian approval is required for the reset request."""
    # Guardian requests are auto-approved
    if requester_role == "guardian":
        return False
    
    # Teachers need guardian approval unless specifically granted permission
    if requester_role == "teacher":
        # Check if teacher has been granted reset permissions for this learner
        # This would typically call the user service or permissions service
        try:
            response = await http_client.get(
                f"/api/permissions/check",
                params={
                    "resource": f"learner:{learner_id}:adapter_reset",
                    "role": requester_role
                }
            )
            if response.status_code == 200:
                data = response.json()
                return not data.get("allowed", False)
        except Exception:
            # Default to requiring approval if permission check fails
            pass
        
        return True
    
    # All other roles require guardian approval
    return True


async def _create_approval_request(
    reset_request: AdapterResetRequest,
    http_client: httpx.AsyncClient
) -> UUID:
    """Create an approval request via the approval service."""
    try:
        approval_payload = {
            "type": "ADAPTER_RESET",
            "resource_id": str(reset_request.learner_id),
            "subject": reset_request.subject,
            "requested_by": str(reset_request.requested_by),
            "requester_role": reset_request.requester_role,
            "reason": reset_request.reason,
            "metadata": {
                "subject": reset_request.subject,
                "reset_request_id": str(reset_request.id)
            },
            "callback_url": "/api/private-fm-orchestrator/reset/webhook/approval-decision"
        }
        
        response = await http_client.post(
            "/api/approval-svc/requests",
            json=approval_payload
        )
        
        if response.status_code != 201:
            raise Exception(f"Approval service returned {response.status_code}")
        
        approval_data = response.json()
        return UUID(approval_data["id"])
        
    except Exception as e:
        logger.error("Failed to create approval request", error=str(e))
        raise Exception("Failed to create approval request")


async def _create_audit_entry(
    reset_request: AdapterResetRequest,
    action: str,
    http_client: httpx.AsyncClient
):
    """Create an audit log entry for compliance tracking."""
    try:
        audit_payload = {
            "action": action,
            "resource_type": "adapter_reset",
            "resource_id": str(reset_request.id),
            "learner_id": str(reset_request.learner_id),
            "actor_id": str(reset_request.requested_by),
            "actor_role": reset_request.requester_role,
            "details": {
                "subject": reset_request.subject,
                "reason": reset_request.reason,
                "status": reset_request.status.value
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await http_client.post(
            "/api/audit/entries",
            json=audit_payload
        )
        
    except Exception as e:
        logger.warning("Failed to create audit entry", error=str(e))
        # Don't fail the main operation if audit logging fails


async def _execute_adapter_reset(
    request_id: UUID,
    db: AsyncSession
):
    """
    Execute the adapter reset operation.
    
    This function:
    1. Deletes the subject-specific adapter
    2. Re-clones the base foundation model
    3. Replays the learner's event log for the subject
    4. Emits completion event
    """
    try:
        # Get the reset request
        result = await db.execute(
            select(AdapterResetRequest).where(
                AdapterResetRequest.id == request_id
            )
        )
        reset_request = result.scalar_one_or_none()
        
        if not reset_request:
            logger.error("Reset request not found during execution", request_id=str(request_id))
            return
        
        # Update status to executing
        reset_request.status = AdapterResetStatus.EXECUTING
        reset_request.started_at = datetime.now(timezone.utc)
        reset_request.progress_percent = 0
        reset_request.current_stage = "Initializing"
        
        await db.commit()
        
        logger.info(
            "Starting adapter reset execution",
            request_id=str(request_id),
            learner_id=str(reset_request.learner_id),
            subject=reset_request.subject
        )
        
        # Get the namespace isolator
        isolator = NamespaceIsolator()
        
        # Stage 1: Delete existing adapter
        reset_request.current_stage = "Deleting existing adapter"
        reset_request.progress_percent = 20
        await db.commit()
        
        await isolator.delete_subject_adapter(
            reset_request.learner_id, 
            reset_request.subject
        )
        
        # Stage 2: Re-clone base foundation model
        reset_request.current_stage = "Re-cloning base foundation model"
        reset_request.progress_percent = 40
        await db.commit()
        
        await isolator.clone_base_model_for_subject(
            reset_request.learner_id,
            reset_request.subject
        )
        
        # Stage 3: Get event log for replay
        reset_request.current_stage = "Retrieving event log"
        reset_request.progress_percent = 60
        await db.commit()
        
        events_result = await db.execute(
            select(EventLog).where(
                and_(
                    EventLog.learner_id == reset_request.learner_id,
                    EventLog.subject == reset_request.subject
                )
            ).order_by(EventLog.timestamp)
        )
        events = events_result.scalars().all()
        
        # Stage 4: Replay events
        reset_request.current_stage = "Replaying learner events"
        reset_request.progress_percent = 80
        await db.commit()
        
        events_replayed = 0
        for event in events:
            await isolator.replay_event(
                reset_request.learner_id,
                reset_request.subject,
                event
            )
            events_replayed += 1
        
        # Stage 5: Finalization
        reset_request.current_stage = "Finalizing"
        reset_request.progress_percent = 95
        await db.commit()
        
        # Update namespace status if needed
        namespace_result = await db.execute(
            select(LearnerNamespace).where(
                LearnerNamespace.learner_id == reset_request.learner_id
            )
        )
        namespace = namespace_result.scalar_one()
        
        if namespace.status == NamespaceStatus.CORRUPTED:
            namespace.status = NamespaceStatus.ACTIVE
        
        # Complete the reset
        reset_request.status = AdapterResetStatus.COMPLETED
        reset_request.completed_at = datetime.now(timezone.utc)
        reset_request.progress_percent = 100
        reset_request.current_stage = "Completed"
        reset_request.events_replayed = events_replayed
        reset_request.metadata = {
            "events_replayed": events_replayed,
            "completion_time": datetime.now(timezone.utc).isoformat()
        }
        
        await db.commit()
        
        # Emit completion event (would integrate with event bus)
        await _emit_reset_completion_event(reset_request)
        
        logger.info(
            "Adapter reset completed successfully",
            request_id=str(request_id),
            events_replayed=events_replayed,
            duration_seconds=(
                reset_request.completed_at - reset_request.started_at
            ).total_seconds()
        )
        
    except Exception as e:
        logger.error(
            "Adapter reset execution failed",
            request_id=str(request_id),
            error=str(e)
        )
        
        # Update request with error status
        try:
            reset_request.status = AdapterResetStatus.FAILED
            reset_request.error_message = str(e)
            reset_request.completed_at = datetime.now(timezone.utc)
            await db.commit()
        except Exception:
            pass


async def _emit_reset_completion_event(reset_request: AdapterResetRequest):
    """Emit an event indicating the adapter reset has completed."""
    try:
        # This would integrate with your event bus/messaging system
        event_data = {
            "event_type": "ADAPTER_RESET_DONE",
            "learner_id": str(reset_request.learner_id),
            "subject": reset_request.subject,
            "request_id": str(reset_request.id),
            "events_replayed": reset_request.events_replayed,
            "completed_at": reset_request.completed_at.isoformat()
        }
        
        # Placeholder for event emission
        logger.info("Adapter reset completion event emitted", **event_data)
        
    except Exception as e:
        logger.warning("Failed to emit reset completion event", error=str(e))
