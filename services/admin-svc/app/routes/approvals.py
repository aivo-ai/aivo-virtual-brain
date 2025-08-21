"""
Approval queue monitoring endpoints
Read-only access to approval workflows and status
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from datetime import datetime, timedelta
import httpx
import logging

from app.auth import AdminUser, verify_admin_token
from app.audit import log_admin_action
from app.config import settings
from app.models import ApprovalRequest, ApprovalStats, ApprovalStatus, ApprovalPriority

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/approvals", response_model=List[ApprovalRequest])
async def get_approval_queue(
    status: Optional[ApprovalStatus] = None,
    priority: Optional[ApprovalPriority] = None,
    type_filter: Optional[str] = Query(None, alias="type"),
    tenant_id: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get approval queue with filtering
    Read-only access for all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "approval_queue_accessed",
        details={
            "filters": {
                "status": status,
                "priority": priority,
                "type": type_filter,
                "tenant_id": tenant_id
            },
            "pagination": {"limit": limit, "offset": offset}
        }
    )
    
    # Ensure tenant-scoped access for tenant admins
    if admin.has_role("tenant_admin") and not admin.is_system_admin():
        tenant_id = admin.tenant_id
    
    try:
        approvals = await _fetch_approvals(
            status=status,
            priority=priority,
            type_filter=type_filter,
            tenant_id=tenant_id,
            limit=limit,
            offset=offset
        )
        return approvals
    except Exception as e:
        logger.error(f"Error fetching approvals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch approval queue")


@router.get("/approvals/stats", response_model=ApprovalStats)
async def get_approval_stats(
    tenant_id: Optional[str] = None,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get approval queue statistics
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "approval_stats_accessed",
        details={"tenant_filter": tenant_id}
    )
    
    # Ensure tenant-scoped access for tenant admins
    if admin.has_role("tenant_admin") and not admin.is_system_admin():
        tenant_id = admin.tenant_id
    
    try:
        stats = await _fetch_approval_stats(tenant_id)
        return stats
    except Exception as e:
        logger.error(f"Error fetching approval stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch approval statistics")


@router.get("/approvals/{approval_id}", response_model=ApprovalRequest)
async def get_approval_details(
    approval_id: str,
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get detailed approval information
    Read-only access with audit logging
    """
    await log_admin_action(
        admin.user_id,
        "approval_details_accessed",
        details={"approval_id": approval_id},
        target_resource=f"approval:{approval_id}"
    )
    
    try:
        approval = await _fetch_approval_by_id(approval_id)
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval not found")
        
        # Check tenant access for tenant admins
        if (admin.has_role("tenant_admin") and not admin.is_system_admin() 
            and approval.tenant_id != admin.tenant_id):
            raise HTTPException(status_code=403, detail="Access denied to this approval")
        
        return approval
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching approval details: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch approval details")


@router.get("/approvals/expiring")
async def get_expiring_approvals(
    hours: int = Query(24, ge=1, le=168),  # 1 hour to 7 days
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get approvals expiring within specified timeframe
    Helps identify urgent approvals needing attention
    """
    await log_admin_action(
        admin.user_id,
        "expiring_approvals_accessed",
        details={"expiring_within_hours": hours}
    )
    
    try:
        cutoff_time = datetime.utcnow() + timedelta(hours=hours)
        
        approvals = await _fetch_approvals(
            status=ApprovalStatus.PENDING,
            expires_before=cutoff_time,
            tenant_id=admin.tenant_id if admin.has_role("tenant_admin") else None
        )
        
        return {
            "expiring_count": len(approvals),
            "cutoff_time": cutoff_time,
            "hours_ahead": hours,
            "approvals": approvals
        }
    except Exception as e:
        logger.error(f"Error fetching expiring approvals: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch expiring approvals")


@router.get("/approvals/by-type/{approval_type}")
async def get_approvals_by_type(
    approval_type: str,
    limit: int = Query(50, le=200),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get approvals filtered by type (consent, access, etc.)
    """
    await log_admin_action(
        admin.user_id,
        "approvals_by_type_accessed",
        details={"approval_type": approval_type, "limit": limit}
    )
    
    try:
        approvals = await _fetch_approvals(
            type_filter=approval_type,
            limit=limit,
            tenant_id=admin.tenant_id if admin.has_role("tenant_admin") else None
        )
        
        return {
            "approval_type": approval_type,
            "count": len(approvals),
            "approvals": approvals
        }
    except Exception as e:
        logger.error(f"Error fetching approvals by type: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch approvals by type")


async def _fetch_approvals(
    status: Optional[ApprovalStatus] = None,
    priority: Optional[ApprovalPriority] = None,
    type_filter: Optional[str] = None,
    tenant_id: Optional[str] = None,
    expires_before: Optional[datetime] = None,
    limit: int = 50,
    offset: int = 0
) -> List[ApprovalRequest]:
    """Fetch approvals from approval service"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        mock_approvals = [
            ApprovalRequest(
                id="app_001",
                type="consent",
                status=ApprovalStatus.PENDING,
                priority=ApprovalPriority.HIGH,
                learner_id="learner_123",
                guardian_id="guardian_456",
                tenant_id="tenant_001",
                requested_by="staff_789",
                requested_at=datetime.utcnow() - timedelta(hours=2),
                expires_at=datetime.utcnow() + timedelta(hours=22),
                metadata={
                    "data_types": ["learning_progress", "assessment_results"],
                    "purpose": "Support request investigation"
                }
            ),
            ApprovalRequest(
                id="app_002",
                type="data_access",
                status=ApprovalStatus.PENDING,
                priority=ApprovalPriority.MEDIUM,
                learner_id="learner_456",
                guardian_id="guardian_789",
                tenant_id="tenant_001",
                requested_by="staff_101",
                requested_at=datetime.utcnow() - timedelta(hours=6),
                expires_at=datetime.utcnow() + timedelta(hours=18),
                metadata={
                    "access_level": "read_only",
                    "duration_minutes": 30
                }
            ),
            ApprovalRequest(
                id="app_003",
                type="consent",
                status=ApprovalStatus.APPROVED,
                priority=ApprovalPriority.URGENT,
                learner_id="learner_789",
                guardian_id="guardian_101",
                tenant_id="tenant_002",
                requested_by="staff_202",
                requested_at=datetime.utcnow() - timedelta(hours=1),
                approved_at=datetime.utcnow() - timedelta(minutes=30),
                approved_by="guardian_101",
                metadata={
                    "emergency_access": True,
                    "incident_id": "INC-2024-001"
                }
            )
        ]
        
        # Apply filters
        filtered = mock_approvals
        
        if status:
            filtered = [a for a in filtered if a.status == status]
        if priority:
            filtered = [a for a in filtered if a.priority == priority]
        if type_filter:
            filtered = [a for a in filtered if a.type == type_filter]
        if tenant_id:
            filtered = [a for a in filtered if a.tenant_id == tenant_id]
        if expires_before:
            filtered = [a for a in filtered if a.expires_at and a.expires_at <= expires_before]
        
        # Apply pagination
        return filtered[offset:offset + limit]
    
    # Production API call
    try:
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if status:
            params["status"] = status.value
        if priority:
            params["priority"] = priority.value
        if type_filter:
            params["type"] = type_filter
        if tenant_id:
            params["tenant_id"] = tenant_id
        if expires_before:
            params["expires_before"] = expires_before.isoformat()
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.APPROVAL_SERVICE_URL}/admin/approvals",
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 200:
                return [ApprovalRequest(**item) for item in response.json()]
            else:
                logger.warning(f"Approval service returned {response.status_code}")
                return []
                
    except Exception as e:
        logger.error(f"Error calling approval service: {e}")
        return []


async def _fetch_approval_by_id(approval_id: str) -> Optional[ApprovalRequest]:
    """Fetch specific approval by ID"""
    
    # Mock data for development
    if settings.ENVIRONMENT == "development":
        mock_approval = ApprovalRequest(
            id=approval_id,
            type="consent",
            status=ApprovalStatus.PENDING,
            priority=ApprovalPriority.HIGH,
            learner_id="learner_123",
            guardian_id="guardian_456",
            tenant_id="tenant_001",
            requested_by="staff_789",
            requested_at=datetime.utcnow() - timedelta(hours=2),
            expires_at=datetime.utcnow() + timedelta(hours=22),
            metadata={
                "data_types": ["learning_progress", "assessment_results"],
                "purpose": "Support request investigation",
                "urgency_reason": "Learner experiencing technical difficulties",
                "estimated_resolution": "30 minutes"
            }
        )
        return mock_approval
    
    # Production API call
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.APPROVAL_SERVICE_URL}/admin/approvals/{approval_id}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                return ApprovalRequest(**response.json())
            elif response.status_code == 404:
                return None
            else:
                logger.warning(f"Approval service returned {response.status_code}")
                return None
                
    except Exception as e:
        logger.error(f"Error fetching approval by ID: {e}")
        return None


async def _fetch_approval_stats(tenant_id: Optional[str] = None) -> ApprovalStats:
    """Fetch approval statistics"""
    
    # Mock stats for development
    if settings.ENVIRONMENT == "development":
        return ApprovalStats(
            total_pending=8,
            total_approved=245,
            total_rejected=12,
            avg_processing_time_hours=2.4,
            urgent_count=2,
            expiring_soon_count=3,
            by_type={
                "consent": 5,
                "data_access": 2,
                "emergency_access": 1
            },
            by_priority={
                "low": 1,
                "medium": 4,
                "high": 2,
                "urgent": 1
            }
        )
    
    # Production API call
    try:
        params = {}
        if tenant_id:
            params["tenant_id"] = tenant_id
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.APPROVAL_SERVICE_URL}/admin/stats",
                params=params,
                timeout=10.0
            )
            
            if response.status_code == 200:
                return ApprovalStats(**response.json())
            else:
                logger.warning(f"Approval service stats returned {response.status_code}")
                return ApprovalStats(
                    total_pending=0,
                    total_approved=0,
                    total_rejected=0,
                    avg_processing_time_hours=0,
                    urgent_count=0,
                    expiring_soon_count=0,
                    by_type={},
                    by_priority={}
                )
                
    except Exception as e:
        logger.error(f"Error fetching approval stats: {e}")
        return ApprovalStats(
            total_pending=0,
            total_approved=0,
            total_rejected=0,
            avg_processing_time_hours=0,
            urgent_count=0,
            expiring_soon_count=0,
            by_type={},
            by_priority={}
        )
