# AIVO Approval Service - API Routes
# S2-10 Implementation - REST API with state machine + TTL

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
from typing import Optional, List
from datetime import datetime, timezone, timedelta
import uuid
import logging
import httpx

from .database import get_db
from .models import ApprovalRequest, ApprovalDecision, ApprovalReminder, ApprovalAuditLog
from .models import ApprovalStatus, ApproverRole, ApprovalType
from .schemas import (
    ApprovalRequestCreate, ApprovalRequestResponse, ApprovalRequestListResponse,
    ApprovalDecisionCreate, ApprovalDecisionResponse,
    ApprovalRequestUpdate, ApprovalStatsResponse, WebhookPayload, ErrorResponse,
    ApprovalRequestFilters
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


# ============================================================================
# APPROVAL REQUEST ENDPOINTS
# ============================================================================

@router.post("/", response_model=ApprovalRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_approval_request(
    request_data: ApprovalRequestCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Create a new approval request with TTL and required roles.
    
    Supports level changes, IEP changes, and consent-sensitive actions.
    Automatically schedules reminders and expiration handling.
    """
    try:
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(hours=request_data.expires_in_hours)
        
        # Prepare context data with required roles
        context_data = request_data.context_data or {}
        # Handle both enum and string values for required_roles
        roles_list = []
        for role in request_data.required_roles:
            if hasattr(role, 'value'):
                roles_list.append(role.value)
            else:
                roles_list.append(str(role))
        context_data["required_roles"] = roles_list
        
        # Create approval request
        approval_request = ApprovalRequest(
            tenant_id=request_data.tenant_id,
            approval_type=request_data.approval_type,
            resource_id=request_data.resource_id,
            resource_type=request_data.resource_type,
            title=request_data.title,
            description=request_data.description,
            context_data=context_data,
            expires_at=expires_at,
            requested_by=request_data.requested_by,
            requested_by_role=request_data.requested_by_role,
            webhook_url=request_data.webhook_url,
            webhook_headers=request_data.webhook_headers
        )
        
        db.add(approval_request)
        db.flush()  # Get the ID
        
        # Create audit log entry
        audit_log = ApprovalAuditLog(
            request_id=approval_request.id,
            event_type="created",
            actor_id=request_data.requested_by,
            actor_role=request_data.requested_by_role,
            description=f"Approval request created: {request_data.title}",
            event_data={
                "approval_type": request_data.approval_type.value if hasattr(request_data.approval_type, 'value') else str(request_data.approval_type),
                "required_roles": roles_list,
                "expires_in_hours": request_data.expires_in_hours
            }
        )
        db.add(audit_log)
        
        # Schedule initial reminders
        background_tasks.add_task(
            schedule_reminders,
            approval_request.id,
            roles_list
        )
        
        db.commit()
        db.refresh(approval_request)
        
        logger.info(f"Created approval request {approval_request.id} for {request_data.approval_type}")
        
        return _build_response(approval_request)
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating approval request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create approval request: {str(e)}"
        )


@router.get("/{request_id}", response_model=ApprovalRequestResponse)
async def get_approval_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get a specific approval request by ID."""
    approval_request = db.query(ApprovalRequest).filter(
        ApprovalRequest.id == request_id
    ).first()
    
    if not approval_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found"
        )
    
    # Check for expiration and update status if needed
    if approval_request.is_expired and approval_request.status == ApprovalStatus.PENDING:
        await _expire_request(approval_request, db)
    
    return _build_response(approval_request)


@router.get("/", response_model=ApprovalRequestListResponse)
async def list_approval_requests(
    tenant_id: Optional[uuid.UUID] = Query(None, description="Filter by tenant ID"),
    approval_type: Optional[ApprovalType] = Query(None, description="Filter by approval type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    status: Optional[ApprovalStatus] = Query(None, description="Filter by status"),
    requested_by: Optional[str] = Query(None, description="Filter by requester"),
    approver_role: Optional[ApproverRole] = Query(None, description="Filter by pending approver role"),
    created_after: Optional[datetime] = Query(None, description="Filter by creation date (after)"),
    created_before: Optional[datetime] = Query(None, description="Filter by creation date (before)"),
    page: int = Query(default=1, ge=1, description="Page number"),
    per_page: int = Query(default=50, ge=1, le=500, description="Items per page"),
    sort_by: str = Query(default="created_at", description="Sort field"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db)
):
    """List approval requests with filtering and pagination."""
    try:
        query = db.query(ApprovalRequest)
        
        # Apply filters
        if tenant_id:
            query = query.filter(ApprovalRequest.tenant_id == tenant_id)
        if approval_type:
            query = query.filter(ApprovalRequest.approval_type == approval_type)
        if resource_type:
            query = query.filter(ApprovalRequest.resource_type == resource_type)
        if status:
            query = query.filter(ApprovalRequest.status == status)
        if requested_by:
            query = query.filter(ApprovalRequest.requested_by == requested_by)
        if created_after:
            query = query.filter(ApprovalRequest.created_at >= created_after)
        if created_before:
            query = query.filter(ApprovalRequest.created_at <= created_before)
        
        # Filter by pending approver role
        if approver_role:
            # Complex query to find requests where this role hasn't approved yet
            approved_by_role = db.query(ApprovalDecision.request_id).filter(
                and_(
                    ApprovalDecision.approver_role == approver_role,
                    ApprovalDecision.approved == True
                )
            ).subquery()
            
            query = query.filter(
                and_(
                    ApprovalRequest.status == ApprovalStatus.PENDING,
                    ~ApprovalRequest.id.in_(approved_by_role),
                    ApprovalRequest.context_data.op("->>")(
                        'required_roles'
                    ).contains(f'"{approver_role.value}"')
                )
            )
        
        # Get total count
        total = query.count()
        
        # Apply sorting
        if hasattr(ApprovalRequest, sort_by):
            sort_attr = getattr(ApprovalRequest, sort_by)
            if sort_order == "desc":
                query = query.order_by(desc(sort_attr))
            else:
                query = query.order_by(asc(sort_attr))
        
        # Apply pagination
        offset = (page - 1) * per_page
        items = query.offset(offset).limit(per_page).all()
        
        # Build response
        pages = (total + per_page - 1) // per_page
        
        return ApprovalRequestListResponse(
            items=[_build_response(item) for item in items],
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error listing approval requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list approval requests: {str(e)}"
        )


@router.post("/{request_id}/decision", response_model=ApprovalRequestResponse)
async def make_approval_decision(
    request_id: uuid.UUID,
    decision_data: ApprovalDecisionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Make an approval decision on a pending request.
    
    Handles state transitions and webhook notifications.
    Checks for completion of all required approvals.
    """
    try:
        # Get the approval request
        approval_request = db.query(ApprovalRequest).filter(
            ApprovalRequest.id == request_id
        ).first()
        
        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found"
            )
        
        # Check if request is still pending
        if approval_request.status != ApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot make decision on {approval_request.status.value} request"
            )
        
        # Check if expired
        if approval_request.is_expired:
            await _expire_request(approval_request, db)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot make decision on expired request"
            )
        
        # Validate approver role is required
        required_roles = approval_request.required_approvals
        if decision_data.approver_role.value not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role {decision_data.approver_role.value} is not required for this approval"
            )
        
        # Check if this role has already approved
        existing_approval = db.query(ApprovalDecision).filter(
            and_(
                ApprovalDecision.request_id == request_id,
                ApprovalDecision.approver_role == decision_data.approver_role,
                ApprovalDecision.approved == True
            )
        ).first()
        
        if existing_approval:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role {decision_data.approver_role.value} has already approved this request"
            )
        
        # Create the approval decision
        approval_decision = ApprovalDecision(
            request_id=request_id,
            approver_id=decision_data.approver_id,
            approver_role=decision_data.approver_role,
            approver_name=decision_data.approver_name,
            approved=decision_data.approved,
            comments=decision_data.comments,
            decision_metadata=decision_data.decision_metadata
        )
        
        db.add(approval_decision)
        
        # Create audit log
        audit_log = ApprovalAuditLog(
            request_id=request_id,
            event_type="approved" if decision_data.approved else "rejected",
            actor_id=decision_data.approver_id,
            actor_role=decision_data.approver_role.value,
            description=f"Decision made by {decision_data.approver_role.value}: {'APPROVED' if decision_data.approved else 'REJECTED'}",
            event_data={
                "approved": decision_data.approved,
                "comments": decision_data.comments,
                "approver_name": decision_data.approver_name
            }
        )
        db.add(audit_log)
        
        # Update request timestamps
        approval_request.updated_at = datetime.now(timezone.utc)
        
        # Check if this completes the approval process
        if decision_data.approved:
            # Refresh to get the new decision
            db.flush()
            db.refresh(approval_request)
            
            if approval_request.all_approvals_received:
                # All approvals received - mark as approved
                approval_request.status = ApprovalStatus.APPROVED
                approval_request.decided_at = datetime.now(timezone.utc)
                approval_request.decision_reason = "All required approvals received"
                
                # Schedule webhook notification
                background_tasks.add_task(
                    send_webhook_notification,
                    approval_request.id,
                    "approved"
                )
                
                logger.info(f"Approval request {request_id} fully approved")
        else:
            # Any rejection immediately rejects the entire request
            approval_request.status = ApprovalStatus.REJECTED
            approval_request.decided_at = datetime.now(timezone.utc)
            approval_request.decision_reason = f"Rejected by {decision_data.approver_role.value}: {decision_data.comments or 'No reason provided'}"
            
            # Schedule webhook notification
            background_tasks.add_task(
                send_webhook_notification,
                approval_request.id,
                "rejected"
            )
            
            logger.info(f"Approval request {request_id} rejected by {decision_data.approver_role.value}")
        
        db.commit()
        db.refresh(approval_request)
        
        return _build_response(approval_request)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error making approval decision: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to make approval decision: {str(e)}"
        )


# ============================================================================
# STATS AND UTILITY ENDPOINTS  
# ============================================================================

@router.get("/stats", response_model=ApprovalStatsResponse)
async def get_approval_stats(
    tenant_id: Optional[uuid.UUID] = Query(None, description="Filter stats by tenant"),
    db: Session = Depends(get_db)
):
    """Get approval statistics and metrics."""
    try:
        base_query = db.query(ApprovalRequest)
        if tenant_id:
            base_query = base_query.filter(ApprovalRequest.tenant_id == tenant_id)
        
        # Basic counts
        total_requests = base_query.count()
        pending_requests = base_query.filter(ApprovalRequest.status == ApprovalStatus.PENDING).count()
        approved_requests = base_query.filter(ApprovalRequest.status == ApprovalStatus.APPROVED).count()
        rejected_requests = base_query.filter(ApprovalRequest.status == ApprovalStatus.REJECTED).count()
        expired_requests = base_query.filter(ApprovalRequest.status == ApprovalStatus.EXPIRED).count()
        
        # By type
        level_change_requests = base_query.filter(ApprovalRequest.approval_type == ApprovalType.LEVEL_CHANGE).count()
        iep_change_requests = base_query.filter(ApprovalRequest.approval_type == ApprovalType.IEP_CHANGE).count()
        consent_sensitive_requests = base_query.filter(ApprovalRequest.approval_type == ApprovalType.CONSENT_SENSITIVE).count()
        
        # Approval rate
        total_decided = approved_requests + rejected_requests
        approval_rate = (approved_requests / total_decided * 100) if total_decided > 0 else 0.0
        
        # Timing statistics (for completed requests)
        completed_requests = base_query.filter(
            ApprovalRequest.status.in_([ApprovalStatus.APPROVED, ApprovalStatus.REJECTED])
        ).filter(
            ApprovalRequest.decided_at.isnot(None)
        ).all()
        
        approval_times = []
        for req in completed_requests:
            if req.decided_at and req.created_at:
                time_diff = req.decided_at - req.created_at
                approval_times.append(time_diff.total_seconds() / 3600)  # Convert to hours
        
        avg_approval_time = sum(approval_times) / len(approval_times) if approval_times else None
        median_approval_time = sorted(approval_times)[len(approval_times) // 2] if approval_times else None
        
        return ApprovalStatsResponse(
            total_requests=total_requests,
            pending_requests=pending_requests,
            approved_requests=approved_requests,
            rejected_requests=rejected_requests,
            expired_requests=expired_requests,
            level_change_requests=level_change_requests,
            iep_change_requests=iep_change_requests,
            consent_sensitive_requests=consent_sensitive_requests,
            approval_rate=approval_rate,
            average_approval_time_hours=avg_approval_time,
            median_approval_time_hours=median_approval_time
        )
        
    except Exception as e:
        logger.error(f"Error getting approval stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get approval stats: {str(e)}"
        )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_response(approval_request: ApprovalRequest) -> ApprovalRequestResponse:
    """Build a complete approval request response with computed properties."""
    return ApprovalRequestResponse(
        id=approval_request.id,
        tenant_id=approval_request.tenant_id,
        approval_type=approval_request.approval_type,
        resource_id=approval_request.resource_id,
        resource_type=approval_request.resource_type,
        title=approval_request.title,
        description=approval_request.description,
        context_data=approval_request.context_data,
        status=approval_request.status,
        created_at=approval_request.created_at,
        expires_at=approval_request.expires_at,
        updated_at=approval_request.updated_at,
        decided_at=approval_request.decided_at,
        requested_by=approval_request.requested_by,
        requested_by_role=approval_request.requested_by_role,
        decision_reason=approval_request.decision_reason,
        webhook_sent=approval_request.webhook_sent,
        webhook_sent_at=approval_request.webhook_sent_at,
        approvals=[
            ApprovalDecisionResponse.from_orm(approval) 
            for approval in approval_request.approvals
        ],
        reminders=[
            # Reminder responses would be built here if needed
        ],
        required_approvals=approval_request.required_approvals,
        pending_approvals=approval_request.pending_approvals,
        all_approvals_received=approval_request.all_approvals_received,
        is_expired=approval_request.is_expired
    )


async def _expire_request(approval_request: ApprovalRequest, db: Session):
    """Mark a request as expired and handle cleanup."""
    if approval_request.status == ApprovalStatus.PENDING:
        approval_request.status = ApprovalStatus.EXPIRED
        approval_request.decided_at = datetime.now(timezone.utc)
        approval_request.decision_reason = "Request expired due to timeout"
        approval_request.updated_at = datetime.now(timezone.utc)
        
        # Create audit log
        audit_log = ApprovalAuditLog(
            request_id=approval_request.id,
            event_type="expired",
            actor_id="system",
            description="Request expired due to timeout",
            event_data={"expires_at": approval_request.expires_at.isoformat()}
        )
        db.add(audit_log)
        
        # Send webhook if configured
        if approval_request.webhook_url:
            await send_webhook_notification(approval_request.id, "expired")
        
        db.commit()
        logger.info(f"Expired approval request {approval_request.id}")


# Background task functions
async def schedule_reminders(request_id: uuid.UUID, required_roles: List[str]):
    """Schedule reminder notifications for pending approvers."""
    # Implementation would integrate with notification-svc
    logger.info(f"Scheduling reminders for request {request_id} to roles: {required_roles}")


async def send_webhook_notification(request_id: uuid.UUID, event_type: str):
    """Send webhook notification to orchestrator on approval decision."""
    # Implementation would make HTTP call to configured webhook URL
    logger.info(f"Sending webhook notification for request {request_id}: {event_type}")
