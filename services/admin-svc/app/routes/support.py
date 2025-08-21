"""
Support session and learner data access endpoints
Consent-based data access with strict audit logging
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import uuid
import hashlib
import secrets
import httpx
import logging

from app.auth import AdminUser, verify_admin_token
from app.audit import log_admin_action, log_data_access
from app.config import settings
from app.database import execute_command, execute_query, get_redis
from app.models import (
    SupportSessionRequest, SupportSession, ConsentRequest, 
    ConsentToken, LearnerDataAccess
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/support-session/request")
async def request_support_session(
    request: SupportSessionRequest,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Request support session for learner data access
    Initiates consent workflow with guardian
    """
    await log_admin_action(
        admin.user_id,
        "support_session_requested",
        details={
            "learner_id": request.learner_id,
            "purpose": request.purpose,
            "urgency": request.urgency,
            "estimated_duration": request.estimated_duration_minutes
        },
        target_resource=f"learner:{request.learner_id}"
    )
    
    try:
        # Check if learner exists and get guardian info
        learner_info = await _get_learner_info(request.learner_id)
        if not learner_info:
            raise HTTPException(status_code=404, detail="Learner not found")
        
        # Check for active consent
        active_consent = await _check_active_consent(request.learner_id)
        
        if not active_consent and request.urgency != "emergency":
            # Initiate consent request to guardian
            consent_request = await _create_consent_request(
                learner_id=request.learner_id,
                guardian_id=learner_info.get("guardian_id"),
                purpose=request.purpose,
                urgency=request.urgency,
                duration_minutes=request.estimated_duration_minutes
            )
            
            return {
                "status": "consent_required",
                "consent_request_id": consent_request["id"],
                "guardian_notified": True,
                "estimated_approval_time": "15-30 minutes",
                "message": "Consent request sent to guardian. You will be notified when approved."
            }
        
        elif request.urgency == "emergency" and settings.ENABLE_EMERGENCY_ACCESS:
            # Emergency access path (requires additional approval)
            if not settings.EMERGENCY_ACCESS_REQUIRES_APPROVAL:
                session = await _create_support_session(request, admin.user_id, emergency=True)
                return {
                    "status": "emergency_session_created",
                    "session_id": session["session_id"],
                    "expires_at": session["expires_at"],
                    "warning": "Emergency access granted. All actions are heavily audited."
                }
            else:
                return {
                    "status": "emergency_approval_required",
                    "message": "Emergency access requires additional system admin approval",
                    "next_steps": "Contact system administrator for emergency access approval"
                }
        
        else:
            # Active consent exists, create session
            session = await _create_support_session(request, admin.user_id)
            return {
                "status": "session_created",
                "session_id": session["session_id"],
                "expires_at": session["expires_at"],
                "consent_token": session.get("consent_token")
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error requesting support session: {e}")
        raise HTTPException(status_code=500, detail="Failed to process support session request")


@router.post("/support-session", response_model=SupportSession)
async def create_support_session(
    request: SupportSessionRequest,
    consent_token: Optional[str] = None,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Create active support session with valid consent
    Requires consent token or emergency override
    """
    await log_admin_action(
        admin.user_id,
        "support_session_creation_attempted",
        details={
            "learner_id": request.learner_id,
            "has_consent_token": bool(consent_token),
            "urgency": request.urgency
        },
        target_resource=f"learner:{request.learner_id}"
    )
    
    try:
        # Validate consent token if provided
        if consent_token:
            consent_valid = await _validate_consent_token(consent_token, request.learner_id)
            if not consent_valid:
                raise HTTPException(status_code=403, detail="Invalid or expired consent token")
        elif request.urgency != "emergency":
            raise HTTPException(status_code=403, detail="Consent token required for data access")
        
        # Create support session
        session = await _create_support_session(request, admin.user_id, consent_token)
        
        await log_admin_action(
            admin.user_id,
            "support_session_created",
            details={
                "session_id": session["session_id"],
                "learner_id": request.learner_id,
                "duration_minutes": request.estimated_duration_minutes
            },
            target_resource=f"session:{session['session_id']}",
            success=True
        )
        
        return SupportSession(**session)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating support session: {e}")
        await log_admin_action(
            admin.user_id,
            "support_session_creation_failed",
            details={"error": str(e), "learner_id": request.learner_id},
            success=False
        )
        raise HTTPException(status_code=500, detail="Failed to create support session")


@router.get("/support-sessions", response_model=List[SupportSession])
async def get_active_support_sessions(
    active_only: bool = Query(True),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get support sessions
    System admins see all, others see only their own
    """
    await log_admin_action(
        admin.user_id,
        "support_sessions_accessed",
        details={"active_only": active_only, "scope": "all" if admin.is_system_admin() else "own"}
    )
    
    try:
        conditions = []
        params = []
        
        if active_only:
            conditions.append("is_active = TRUE AND expires_at > NOW()")
        
        if not admin.is_system_admin():
            conditions.append("staff_user_id = $1")
            params.append(admin.user_id)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
            SELECT session_id, learner_id, staff_user_id, purpose, urgency,
                   consent_token, created_at, expires_at, accessed_data,
                   actions_performed, is_active, closed_at, closure_reason
            FROM support_sessions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT 100
        """
        
        rows = await execute_query(query, *params)
        
        return [
            SupportSession(
                id=str(row["session_id"]),
                learner_id=row["learner_id"],
                staff_user_id=row["staff_user_id"],
                purpose=row["purpose"],
                urgency=row["urgency"],
                consent_token=row["consent_token"],
                created_at=row["created_at"],
                expires_at=row["expires_at"],
                accessed_data=row["accessed_data"] or [],
                actions_performed=row["actions_performed"] or [],
                is_active=row["is_active"]
            )
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Error fetching support sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch support sessions")


@router.get("/learners/{learner_id}/state")
async def get_learner_state(
    learner_id: str,
    session_id: str = Query(..., description="Required support session ID"),
    data_types: List[str] = Query(["basic"], description="Types of data to access"),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Access learner data within active support session
    Requires valid support session and logs all access
    """
    try:
        # Validate support session
        session = await _validate_support_session(session_id, admin.user_id, learner_id)
        if not session:
            raise HTTPException(status_code=403, detail="Invalid or expired support session")
        
        # Check if requesting data types are allowed
        allowed_data_types = ["basic", "progress", "assessments", "interactions", "preferences"]
        invalid_types = [dt for dt in data_types if dt not in allowed_data_types]
        if invalid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid data types: {invalid_types}. Allowed: {allowed_data_types}"
            )
        
        # Fetch learner data based on requested types
        learner_data = {}
        
        for data_type in data_types:
            try:
                data = await _fetch_learner_data(learner_id, data_type)
                learner_data[data_type] = data
                
                # Log data access for compliance
                await log_data_access(
                    user_id=admin.user_id,
                    learner_id=learner_id,
                    data_type=data_type,
                    purpose=session["purpose"],
                    session_id=session_id,
                    data_summary={"record_count": len(data) if isinstance(data, list) else 1}
                )
                
                # Update session accessed data
                await _update_session_accessed_data(session_id, data_type)
                
            except Exception as e:
                logger.warning(f"Could not fetch {data_type} data for learner {learner_id}: {e}")
                learner_data[data_type] = {"error": f"Data unavailable: {str(e)}"}
        
        await log_admin_action(
            admin.user_id,
            "learner_data_accessed",
            details={
                "learner_id": learner_id,
                "session_id": session_id,
                "data_types": data_types,
                "purpose": session["purpose"]
            },
            target_resource=f"learner:{learner_id}"
        )
        
        return {
            "learner_id": learner_id,
            "session_id": session_id,
            "accessed_at": datetime.utcnow(),
            "data_types": data_types,
            "data": learner_data,
            "session_expires_at": session["expires_at"],
            "compliance_notice": "All data access is logged and audited for compliance"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error accessing learner data: {e}")
        raise HTTPException(status_code=500, detail="Failed to access learner data")


@router.post("/support-sessions/{session_id}/close")
async def close_support_session(
    session_id: str,
    reason: str = Query("Session completed"),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Close active support session
    Can be closed by session owner or system admin
    """
    await log_admin_action(
        admin.user_id,
        "support_session_close_attempted",
        details={"session_id": session_id, "reason": reason},
        target_resource=f"session:{session_id}"
    )
    
    try:
        # Validate session ownership
        session = await _validate_support_session(session_id, admin.user_id, check_ownership=True)
        if not session and not admin.is_system_admin():
            raise HTTPException(
                status_code=403, 
                detail="Can only close your own sessions unless system admin"
            )
        
        # Close session
        await execute_command("""
            UPDATE support_sessions 
            SET is_active = FALSE, closed_at = NOW(), closure_reason = $2
            WHERE session_id = $1
        """, uuid.UUID(session_id), reason)
        
        await log_admin_action(
            admin.user_id,
            "support_session_closed",
            details={
                "session_id": session_id,
                "reason": reason,
                "duration_minutes": (datetime.utcnow() - session["created_at"]).total_seconds() / 60
            },
            target_resource=f"session:{session_id}",
            success=True
        )
        
        return {
            "session_id": session_id,
            "status": "closed",
            "closed_at": datetime.utcnow(),
            "reason": reason
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error closing support session: {e}")
        raise HTTPException(status_code=500, detail="Failed to close support session")


# Helper functions

async def _get_learner_info(learner_id: str) -> Optional[dict]:
    """Get basic learner information"""
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        return {
            "learner_id": learner_id,
            "guardian_id": f"guardian_{learner_id[-3:]}",
            "tenant_id": "tenant_001",
            "status": "active"
        }
    
    # Production: call learner service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.LEARNER_SERVICE_URL}/admin/learners/{learner_id}/info",
                timeout=10.0
            )
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        logger.warning(f"Could not fetch learner info: {e}")
    
    return None


async def _check_active_consent(learner_id: str) -> Optional[dict]:
    """Check if learner has active consent for data access"""
    try:
        result = await execute_query("""
            SELECT token_id, expires_at, data_types, usage_count, max_usage
            FROM consent_tokens
            WHERE learner_id = $1 AND is_revoked = FALSE 
            AND expires_at > NOW() AND usage_count < max_usage
            ORDER BY created_at DESC
            LIMIT 1
        """, learner_id)
        
        if result:
            return {
                "token_id": str(result[0]["token_id"]),
                "expires_at": result[0]["expires_at"],
                "data_types": result[0]["data_types"],
                "usage_remaining": result[0]["max_usage"] - result[0]["usage_count"]
            }
    except Exception as e:
        logger.warning(f"Error checking consent: {e}")
    
    return None


async def _create_consent_request(
    learner_id: str,
    guardian_id: Optional[str],
    purpose: str,
    urgency: str,
    duration_minutes: int
) -> dict:
    """Create consent request for guardian approval"""
    
    # Mock consent request for development
    if settings.ENVIRONMENT == "development":
        return {
            "id": f"consent_req_{secrets.token_hex(8)}",
            "status": "sent",
            "estimated_response_time": "15-30 minutes"
        }
    
    # Production: call approval service
    return {"id": "mock_consent_request", "status": "pending"}


async def _create_support_session(
    request: SupportSessionRequest,
    staff_user_id: str,
    consent_token: Optional[str] = None,
    emergency: bool = False
) -> dict:
    """Create new support session"""
    
    session_id = uuid.uuid4()
    expires_at = datetime.utcnow() + timedelta(minutes=request.estimated_duration_minutes)
    
    await execute_command("""
        INSERT INTO support_sessions (
            session_id, learner_id, staff_user_id, purpose, urgency,
            consent_token, created_at, expires_at, is_active
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
    """,
        session_id, request.learner_id, staff_user_id, request.purpose,
        request.urgency, consent_token, datetime.utcnow(), expires_at, True
    )
    
    return {
        "session_id": str(session_id),
        "learner_id": request.learner_id,
        "staff_user_id": staff_user_id,
        "purpose": request.purpose,
        "urgency": request.urgency,
        "consent_token": consent_token,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "accessed_data": [],
        "actions_performed": [],
        "is_active": True
    }


async def _validate_consent_token(token: str, learner_id: str) -> bool:
    """Validate consent token for learner"""
    try:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        result = await execute_query("""
            SELECT token_id FROM consent_tokens
            WHERE token_hash = $1 AND learner_id = $2 
            AND is_revoked = FALSE AND expires_at > NOW()
            AND usage_count < max_usage
        """, token_hash, learner_id)
        
        if result:
            # Increment usage count
            await execute_command("""
                UPDATE consent_tokens 
                SET usage_count = usage_count + 1
                WHERE token_hash = $1
            """, token_hash)
            return True
            
    except Exception as e:
        logger.warning(f"Error validating consent token: {e}")
    
    return False


async def _validate_support_session(
    session_id: str,
    staff_user_id: str,
    learner_id: Optional[str] = None,
    check_ownership: bool = False
) -> Optional[dict]:
    """Validate support session"""
    try:
        conditions = ["session_id = $1", "is_active = TRUE", "expires_at > NOW()"]
        params = [uuid.UUID(session_id)]
        
        if learner_id:
            conditions.append("learner_id = $2")
            params.append(learner_id)
        
        if check_ownership:
            conditions.append(f"staff_user_id = ${len(params) + 1}")
            params.append(staff_user_id)
        
        query = f"""
            SELECT session_id, learner_id, staff_user_id, purpose, urgency,
                   created_at, expires_at, accessed_data, actions_performed
            FROM support_sessions
            WHERE {' AND '.join(conditions)}
        """
        
        result = await execute_query(query, *params)
        
        if result:
            row = result[0]
            return {
                "session_id": str(row["session_id"]),
                "learner_id": row["learner_id"],
                "staff_user_id": row["staff_user_id"],
                "purpose": row["purpose"],
                "urgency": row["urgency"],
                "created_at": row["created_at"],
                "expires_at": row["expires_at"],
                "accessed_data": row["accessed_data"] or [],
                "actions_performed": row["actions_performed"] or []
            }
    except Exception as e:
        logger.warning(f"Error validating support session: {e}")
    
    return None


async def _fetch_learner_data(learner_id: str, data_type: str) -> dict:
    """Fetch specific type of learner data"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        mock_data = {
            "basic": {
                "learner_id": learner_id,
                "status": "active",
                "enrollment_date": "2024-01-15",
                "last_activity": datetime.utcnow().isoformat(),
                "tenant_id": "tenant_001"
            },
            "progress": {
                "courses_completed": 3,
                "courses_in_progress": 2,
                "total_study_hours": 45.5,
                "achievements": ["first_course", "week_streak"],
                "current_level": "intermediate"
            },
            "assessments": {
                "total_assessments": 8,
                "passed": 6,
                "average_score": 85.2,
                "recent_assessment": {
                    "date": "2024-01-10",
                    "subject": "Mathematics",
                    "score": 92
                }
            }
        }
        return mock_data.get(data_type, {"error": "Data type not available"})
    
    # Production: call learner service
    return {"error": "Production data access not configured"}


async def _update_session_accessed_data(session_id: str, data_type: str):
    """Update session with accessed data type"""
    try:
        await execute_command("""
            UPDATE support_sessions
            SET accessed_data = array_append(
                COALESCE(accessed_data, ARRAY[]::text[]), 
                $2
            )
            WHERE session_id = $1
        """, uuid.UUID(session_id), data_type)
    except Exception as e:
        logger.warning(f"Could not update session accessed data: {e}")
