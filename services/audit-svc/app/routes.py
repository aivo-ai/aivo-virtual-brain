"""
Audit Service API Routes
Comprehensive endpoints for audit logging, access reviews, and JIT support
"""

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.security import HTTPAuthorizationCredentials

from .models import (
    AuditEvent, AuditEventType, AuditSeverity, DataAccessLog, AccessReview, 
    SupportSession, AccessReviewItem, AuditQuery, AuditReport,
    CreateAuditEventRequest, CreateSupportSessionRequest, ApproveSupportSessionRequest,
    StartAccessReviewRequest, ReviewAccessItemRequest,
    UserRole, SupportSessionStatus, AccessReviewStatus
)
from .database import get_db_pool, log_audit_event
from .audit_logger import AuditLogger
from .access_reviewer import AccessReviewer
from .support_manager import SupportManager

logger = structlog.get_logger()
router = APIRouter()

# Dependency for authentication (to be implemented)
async def get_current_user(credentials: HTTPAuthorizationCredentials = None):
    """Get current authenticated user from JWT token"""
    # This would implement JWT validation
    # For now, return mock user data
    return {
        "user_id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "user@aivo.com",
        "role": "admin",
        "tenant_id": "tenant-123"
    }


# === Audit Event Endpoints ===

@router.post("/audit/events", response_model=AuditEvent)
async def create_audit_event(
    request: CreateAuditEventRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new audit event"""
    
    try:
        audit_logger = AuditLogger()
        
        # Create audit event
        event = await audit_logger.log_event(
            event_type=request.event_type,
            action=request.action,
            resource=request.resource,
            outcome=request.outcome,
            severity=request.severity,
            reason=request.reason,
            actor_id=request.actor_id or current_user["user_id"],
            actor_type=request.actor_type or UserRole(current_user["role"]),
            target_id=request.target_id,
            target_type=request.target_type,
            target_classification=request.target_classification,
            tenant_id=current_user["tenant_id"],
            metadata=request.metadata
        )
        
        return event
        
    except Exception as e:
        logger.error("Failed to create audit event", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create audit event")


@router.get("/audit/events", response_model=List[AuditEvent])
async def query_audit_events(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    event_types: Optional[List[AuditEventType]] = Query(None),
    severities: Optional[List[AuditSeverity]] = Query(None),
    actor_id: Optional[UUID] = Query(None),
    target_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    """Query audit events with filters"""
    
    try:
        audit_logger = AuditLogger()
        
        query = AuditQuery(
            start_date=start_date,
            end_date=end_date,
            event_types=event_types,
            severities=severities,
            actor_ids=[actor_id] if actor_id else None,
            target_ids=[target_id] if target_id else None,
            tenant_id=current_user["tenant_id"],
            search_term=search,
            page=page,
            page_size=page_size
        )
        
        events = await audit_logger.query_events(query)
        
        # Log the audit query itself
        await audit_logger.log_event(
            event_type=AuditEventType.DATA_READ,
            action="audit_query",
            resource="audit_events",
            actor_id=current_user["user_id"],
            actor_type=UserRole(current_user["role"]),
            tenant_id=current_user["tenant_id"],
            metadata={
                "query_params": query.dict(exclude_none=True),
                "results_count": len(events)
            }
        )
        
        return events
        
    except Exception as e:
        logger.error("Failed to query audit events", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to query audit events")


@router.get("/audit/events/{event_id}", response_model=AuditEvent)
async def get_audit_event(
    event_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get specific audit event by ID"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM audit_events 
                WHERE id = $1 AND tenant_id = $2
                """,
                event_id, current_user["tenant_id"]
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Audit event not found")
            
            # Log access to specific audit event
            audit_logger = AuditLogger()
            await audit_logger.log_event(
                event_type=AuditEventType.DATA_READ,
                action="audit_event_view",
                resource="audit_event",
                target_id=event_id,
                actor_id=current_user["user_id"],
                actor_type=UserRole(current_user["role"]),
                tenant_id=current_user["tenant_id"]
            )
            
            return AuditEvent(**dict(row))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get audit event", error=str(e), event_id=str(event_id))
        raise HTTPException(status_code=500, detail="Failed to retrieve audit event")


@router.get("/audit/reports/summary", response_model=AuditReport)
async def get_audit_summary(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    current_user: dict = Depends(get_current_user)
):
    """Generate audit summary report"""
    
    try:
        audit_logger = AuditLogger()
        report = await audit_logger.generate_summary_report(
            tenant_id=current_user["tenant_id"],
            start_date=start_date,
            end_date=end_date
        )
        
        # Log report generation
        await audit_logger.log_event(
            event_type=AuditEventType.DATA_READ,
            action="audit_report_generated",
            resource="audit_summary",
            actor_id=current_user["user_id"],
            actor_type=UserRole(current_user["role"]),
            tenant_id=current_user["tenant_id"],
            metadata={
                "report_period": f"{start_date} to {end_date}",
                "total_events": report.total_events
            }
        )
        
        return report
        
    except Exception as e:
        logger.error("Failed to generate audit report", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate audit report")


# === Access Review Endpoints ===

@router.post("/access-reviews", response_model=AccessReview)
async def start_access_review(
    request: StartAccessReviewRequest,
    current_user: dict = Depends(get_current_user)
):
    """Start a new access review"""
    
    try:
        # Verify user has permission to start access reviews
        if current_user["role"] not in ["admin", "security"]:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        
        reviewer = AccessReviewer()
        review = await reviewer.start_review(
            tenant_id=current_user["tenant_id"],
            reviewer_id=current_user["user_id"],
            reviewer_email=current_user["email"],
            review_type=request.review_type,
            roles_to_review=request.roles_to_review,
            departments=request.departments,
            due_date=request.due_date
        )
        
        # Log access review start
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.ACCESS_REVIEW_STARTED,
            action="access_review_start",
            resource="access_review",
            target_id=review.id,
            actor_id=current_user["user_id"],
            actor_type=UserRole(current_user["role"]),
            tenant_id=current_user["tenant_id"],
            metadata={
                "review_type": request.review_type,
                "roles_to_review": [role.value for role in request.roles_to_review],
                "due_date": review.due_date.isoformat() if review.due_date else None
            }
        )
        
        return review
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start access review", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start access review")


@router.get("/access-reviews", response_model=List[AccessReview])
async def list_access_reviews(
    status: Optional[AccessReviewStatus] = Query(None),
    reviewer_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List access reviews"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Build query
            where_conditions = ["tenant_id = $1"]
            params = [current_user["tenant_id"]]
            param_count = 1
            
            if status:
                param_count += 1
                where_conditions.append(f"status = ${param_count}")
                params.append(status.value)
            
            if reviewer_id:
                param_count += 1
                where_conditions.append(f"reviewer_id = ${param_count}")
                params.append(reviewer_id)
            
            query = f"""
                SELECT * FROM access_reviews 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY created_at DESC
            """
            
            rows = await conn.fetch(query, *params)
            reviews = [AccessReview(**dict(row)) for row in rows]
            
            return reviews
            
    except Exception as e:
        logger.error("Failed to list access reviews", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list access reviews")


@router.get("/access-reviews/{review_id}", response_model=AccessReview)
async def get_access_review(
    review_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get specific access review"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM access_reviews 
                WHERE id = $1 AND tenant_id = $2
                """,
                review_id, current_user["tenant_id"]
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Access review not found")
            
            return AccessReview(**dict(row))
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get access review", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get access review")


@router.get("/access-reviews/{review_id}/items", response_model=List[AccessReviewItem])
async def get_access_review_items(
    review_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get access review items"""
    
    try:
        reviewer = AccessReviewer()
        items = await reviewer.get_review_items(
            review_id=review_id,
            tenant_id=current_user["tenant_id"]
        )
        
        return items
        
    except Exception as e:
        logger.error("Failed to get access review items", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get access review items")


@router.put("/access-reviews/{review_id}/items/{item_id}")
async def review_access_item(
    review_id: UUID,
    item_id: UUID,
    request: ReviewAccessItemRequest,
    current_user: dict = Depends(get_current_user)
):
    """Review individual access item"""
    
    try:
        reviewer = AccessReviewer()
        await reviewer.review_item(
            review_id=review_id,
            item_id=item_id,
            status=request.status,
            reviewer_notes=request.reviewer_notes,
            changes_to_make=request.changes_to_make,
            reviewer_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"]
        )
        
        # Log access certification/revocation
        audit_logger = AuditLogger()
        event_type = AuditEventType.ACCESS_CERTIFIED if request.status == "certified" else AuditEventType.ACCESS_REVOKED
        
        await audit_logger.log_event(
            event_type=event_type,
            action=f"access_{request.status}",
            resource="user_access",
            target_id=item_id,
            actor_id=current_user["user_id"],
            actor_type=UserRole(current_user["role"]),
            tenant_id=current_user["tenant_id"],
            metadata={
                "review_id": str(review_id),
                "status": request.status,
                "notes": request.reviewer_notes,
                "changes": request.changes_to_make
            }
        )
        
        return {"message": "Access item reviewed successfully"}
        
    except Exception as e:
        logger.error("Failed to review access item", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to review access item")


# === Support Session Endpoints ===

@router.post("/support-sessions", response_model=SupportSession)
async def request_support_session(
    request: CreateSupportSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Request a new support session"""
    
    try:
        # Verify requester is guardian for the learner
        # This would check the guardian-learner relationship
        
        support_manager = SupportManager()
        session = await support_manager.create_session(
            learner_id=request.learner_id,
            guardian_id=current_user["user_id"],
            reason=request.reason,
            description=request.description,
            urgency=request.urgency,
            max_duration_minutes=request.max_duration_minutes,
            allowed_data_types=request.allowed_data_types,
            tenant_id=current_user["tenant_id"]
        )
        
        # Log support session request
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.SUPPORT_SESSION_REQUEST,
            action="support_session_request",
            resource="support_session",
            target_id=session.id,
            actor_id=current_user["user_id"],
            actor_type=UserRole.GUARDIAN,
            tenant_id=current_user["tenant_id"],
            metadata={
                "learner_id": str(request.learner_id),
                "reason": request.reason,
                "urgency": request.urgency
            }
        )
        
        return session
        
    except Exception as e:
        logger.error("Failed to request support session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to request support session")


@router.get("/support-sessions", response_model=List[SupportSession])
async def list_support_sessions(
    status: Optional[SupportSessionStatus] = Query(None),
    learner_id: Optional[UUID] = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """List support sessions"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Build query based on user role
            where_conditions = ["tenant_id = $1"]
            params = [current_user["tenant_id"]]
            param_count = 1
            
            # Filter based on user role
            if current_user["role"] == "guardian":
                param_count += 1
                where_conditions.append(f"guardian_id = ${param_count}")
                params.append(current_user["user_id"])
            elif current_user["role"] == "support":
                param_count += 1
                where_conditions.append(f"support_agent_id = ${param_count}")
                params.append(current_user["user_id"])
            elif current_user["role"] not in ["admin", "security"]:
                raise HTTPException(status_code=403, detail="Insufficient permissions")
            
            if status:
                param_count += 1
                where_conditions.append(f"status = ${param_count}")
                params.append(status.value)
            
            if learner_id:
                param_count += 1
                where_conditions.append(f"learner_id = ${param_count}")
                params.append(learner_id)
            
            query = f"""
                SELECT * FROM support_sessions 
                WHERE {' AND '.join(where_conditions)}
                ORDER BY created_at DESC
            """
            
            rows = await conn.fetch(query, *params)
            sessions = [SupportSession(**dict(row)) for row in rows]
            
            return sessions
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to list support sessions", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list support sessions")


@router.get("/support-sessions/{session_id}", response_model=SupportSession)
async def get_support_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Get specific support session"""
    
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM support_sessions 
                WHERE id = $1 AND tenant_id = $2
                """,
                session_id, current_user["tenant_id"]
            )
            
            if not row:
                raise HTTPException(status_code=404, detail="Support session not found")
            
            session = SupportSession(**dict(row))
            
            # Verify access permissions
            if current_user["role"] not in ["admin", "security"]:
                if (current_user["role"] == "guardian" and session.guardian_id != current_user["user_id"]) or \
                   (current_user["role"] == "support" and session.support_agent_id != current_user["user_id"]):
                    raise HTTPException(status_code=403, detail="Access denied")
            
            return session
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get support session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get support session")


@router.put("/support-sessions/{session_id}/approve")
async def approve_support_session(
    session_id: UUID,
    request: ApproveSupportSessionRequest,
    current_user: dict = Depends(get_current_user)
):
    """Approve or deny support session (guardian only)"""
    
    try:
        support_manager = SupportManager()
        session = await support_manager.approve_session(
            session_id=session_id,
            approved=request.approved,
            reason=request.reason,
            approver_id=current_user["user_id"],
            max_duration_minutes=request.max_duration_minutes,
            allowed_data_types=request.allowed_data_types,
            tenant_id=current_user["tenant_id"]
        )
        
        # Log approval/denial
        audit_logger = AuditLogger()
        event_type = AuditEventType.SUPPORT_SESSION_APPROVED if request.approved else AuditEventType.SUPPORT_SESSION_DENIED
        
        await audit_logger.log_event(
            event_type=event_type,
            action="support_session_approval",
            resource="support_session",
            target_id=session_id,
            actor_id=current_user["user_id"],
            actor_type=UserRole.GUARDIAN,
            tenant_id=current_user["tenant_id"],
            metadata={
                "approved": request.approved,
                "reason": request.reason
            }
        )
        
        return session
        
    except Exception as e:
        logger.error("Failed to approve support session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to approve support session")


@router.post("/support-sessions/{session_id}/start")
async def start_support_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """Start approved support session (support agent only)"""
    
    try:
        # Verify user is support agent
        if current_user["role"] != "support":
            raise HTTPException(status_code=403, detail="Only support agents can start sessions")
        
        support_manager = SupportManager()
        session, token = await support_manager.start_session(
            session_id=session_id,
            support_agent_id=current_user["user_id"],
            tenant_id=current_user["tenant_id"]
        )
        
        # Log session start
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.SUPPORT_SESSION_START,
            action="support_session_start",
            resource="support_session",
            target_id=session_id,
            actor_id=current_user["user_id"],
            actor_type=UserRole.SUPPORT,
            tenant_id=current_user["tenant_id"],
            metadata={
                "token_expires_at": session.token_expires_at.isoformat() if session.token_expires_at else None
            }
        )
        
        return {
            "session": session,
            "access_token": token,
            "expires_at": session.token_expires_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start support session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to start support session")


@router.post("/support-sessions/{session_id}/end")
async def end_support_session(
    session_id: UUID,
    current_user: dict = Depends(get_current_user)
):
    """End active support session"""
    
    try:
        support_manager = SupportManager()
        session = await support_manager.end_session(
            session_id=session_id,
            ended_by=current_user["user_id"],
            tenant_id=current_user["tenant_id"]
        )
        
        # Log session end
        audit_logger = AuditLogger()
        await audit_logger.log_event(
            event_type=AuditEventType.SUPPORT_SESSION_END,
            action="support_session_end",
            resource="support_session",
            target_id=session_id,
            actor_id=current_user["user_id"],
            actor_type=UserRole(current_user["role"]),
            tenant_id=current_user["tenant_id"],
            metadata={
                "session_duration_minutes": (session.session_end - session.session_start).total_seconds() / 60 if session.session_end and session.session_start else 0
            }
        )
        
        return session
        
    except Exception as e:
        logger.error("Failed to end support session", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to end support session")
