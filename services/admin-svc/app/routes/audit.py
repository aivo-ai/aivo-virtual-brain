"""
Audit and compliance endpoints
Query audit events and export compliance reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io
import json
import logging

from app.auth import AdminUser, verify_admin_token, require_system_admin
from app.audit import log_admin_action, get_audit_events, get_admin_actions
from app.config import settings
from app.models import AuditEvent, AuditQuery, AuditSummary, AdminAction

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/audit/events", response_model=List[AuditEvent])
async def query_audit_events(
    start_date: Optional[datetime] = Query(None, description="Start date for query"),
    end_date: Optional[datetime] = Query(None, description="End date for query"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    outcome: Optional[str] = Query(None, description="Filter by outcome"),
    limit: int = Query(100, le=1000, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Query audit events with filtering
    Available to all staff roles (read-only)
    """
    await log_admin_action(
        admin.user_id,
        "audit_events_queried",
        details={
            "filters": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "user_id": user_id,
                "event_type": event_type,
                "outcome": outcome
            },
            "pagination": {"limit": limit, "offset": offset}
        }
    )
    
    try:
        # Default to last 24 hours if no date range specified
        if not start_date and not end_date:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(hours=24)
        
        events = await get_audit_events(
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            event_type=event_type,
            outcome=outcome,
            limit=limit,
            offset=offset
        )
        
        return [AuditEvent(**event) for event in events]
        
    except Exception as e:
        logger.error(f"Error querying audit events: {e}")
        raise HTTPException(status_code=500, detail="Failed to query audit events")


@router.get("/audit/summary", response_model=AuditSummary)
async def get_audit_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to summarize"),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get audit event summary for specified time period
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "audit_summary_accessed",
        details={"days_back": days}
    )
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Get all events for period
        events = await get_audit_events(
            start_date=start_date,
            end_date=end_date,
            limit=5000  # Get more for summary
        )
        
        # Calculate summary statistics
        total_events = len(events)
        
        by_event_type = {}
        by_outcome = {}
        by_user = {}
        
        for event in events:
            # Count by event type
            event_type = event.get("event_type", "unknown")
            by_event_type[event_type] = by_event_type.get(event_type, 0) + 1
            
            # Count by outcome
            outcome = event.get("outcome", "unknown")
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
            
            # Count by user (anonymized for non-system-admins)
            user_id = event.get("user_id")
            if user_id:
                if admin.is_system_admin():
                    by_user[user_id] = by_user.get(user_id, 0) + 1
                else:
                    # Anonymize user IDs for non-system admins
                    anonymized = f"user_{hash(user_id) % 1000:03d}"
                    by_user[anonymized] = by_user.get(anonymized, 0) + 1
        
        # Get recent events (last 10)
        recent_events = events[:10] if events else []
        
        return AuditSummary(
            total_events=total_events,
            date_range={
                "start_date": start_date,
                "end_date": end_date
            },
            by_event_type=by_event_type,
            by_outcome=by_outcome,
            by_user=by_user,
            recent_events=[AuditEvent(**event) for event in recent_events]
        )
        
    except Exception as e:
        logger.error(f"Error generating audit summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate audit summary")


@router.get("/audit/admin-actions")
async def query_admin_actions(
    user_id: Optional[str] = Query(None, description="Filter by admin user ID"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    start_date: Optional[datetime] = Query(None, description="Start date for query"),
    end_date: Optional[datetime] = Query(None, description="End date for query"),
    limit: int = Query(100, le=500),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Query admin actions with filtering
    System admins see all, others see only their own actions
    """
    # Non-system admins can only see their own actions
    if not admin.is_system_admin():
        user_id = admin.user_id
    
    await log_admin_action(
        admin.user_id,
        "admin_actions_queried",
        details={
            "filters": {
                "user_id": user_id,
                "action_type": action_type,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            },
            "scope": "all" if admin.is_system_admin() else "own"
        }
    )
    
    try:
        # Default to last 7 days if no date range specified
        if not start_date and not end_date:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=7)
        
        actions = await get_admin_actions(
            user_id=user_id,
            action_type=action_type,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
        
        return {
            "total_actions": len(actions),
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "filters": {
                "user_id": user_id,
                "action_type": action_type
            },
            "actions": [AdminAction(**action) for action in actions]
        }
        
    except Exception as e:
        logger.error(f"Error querying admin actions: {e}")
        raise HTTPException(status_code=500, detail="Failed to query admin actions")


@router.post("/audit/export")
async def export_audit_log(
    query: AuditQuery,
    format: str = Query("csv", regex="^(csv|json)$"),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Export audit log for compliance reporting
    Available to all staff roles, with appropriate filtering
    """
    if not settings.ENABLE_AUDIT_EXPORT:
        raise HTTPException(
            status_code=403, 
            detail="Audit export is not enabled"
        )
    
    await log_admin_action(
        admin.user_id,
        "audit_export_requested",
        details={
            "format": format,
            "query_filters": {
                "start_date": query.start_date.isoformat() if query.start_date else None,
                "end_date": query.end_date.isoformat() if query.end_date else None,
                "event_type": query.event_type,
                "outcome": query.outcome,
                "limit": query.limit
            }
        }
    )
    
    try:
        # Non-system admins have limited export capabilities
        if not admin.is_system_admin():
            # Limit date range to last 30 days for non-system admins
            max_end_date = datetime.utcnow()
            min_start_date = max_end_date - timedelta(days=30)
            
            if query.end_date and query.end_date > max_end_date:
                query.end_date = max_end_date
            if query.start_date and query.start_date < min_start_date:
                query.start_date = min_start_date
            
            # Limit number of records
            query.limit = min(query.limit, 1000)
        
        # Get audit events
        events = await get_audit_events(
            start_date=query.start_date,
            end_date=query.end_date,
            user_id=query.user_id,
            event_type=query.event_type,
            outcome=query.outcome,
            limit=query.limit,
            offset=query.offset
        )
        
        # Generate export file
        if format == "csv":
            output = await _generate_csv_export(events)
            media_type = "text/csv"
            filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        else:  # json
            output = await _generate_json_export(events)
            media_type = "application/json"
            filename = f"audit_export_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Log successful export
        await log_admin_action(
            admin.user_id,
            "audit_exported",
            details={
                "format": format,
                "record_count": len(events),
                "filename": filename
            },
            success=True
        )
        
        return StreamingResponse(
            io.BytesIO(output.encode()),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting audit log: {e}")
        await log_admin_action(
            admin.user_id,
            "audit_export_failed",
            details={"error": str(e), "format": format},
            success=False
        )
        raise HTTPException(status_code=500, detail="Failed to export audit log")


@router.get("/audit/security-events")
async def get_security_events(
    hours: int = Query(24, ge=1, le=168, description="Hours back to search"),
    severity: Optional[str] = Query(None, regex="^(low|medium|high|critical)$"),
    admin: AdminUser = Depends(verify_admin_token)
):
    """
    Get security-related audit events
    Available to all staff roles
    """
    await log_admin_action(
        admin.user_id,
        "security_events_accessed",
        details={"hours_back": hours, "severity_filter": severity}
    )
    
    try:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(hours=hours)
        
        # Security-related event types
        security_events = [
            "admin_login", "token_expired", "invalid_token", "insufficient_permissions",
            "role_required", "access_denied", "support_session_created", 
            "learner_data_accessed", "job_requeued", "job_cancelled"
        ]
        
        all_security_events = []
        
        for event_type in security_events:
            events = await get_audit_events(
                start_date=start_date,
                end_date=end_date,
                event_type=event_type,
                limit=100
            )
            all_security_events.extend(events)
        
        # Sort by timestamp (most recent first)
        all_security_events.sort(
            key=lambda x: x.get("timestamp", datetime.min), 
            reverse=True
        )
        
        return {
            "timeframe_hours": hours,
            "security_event_count": len(all_security_events),
            "date_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "events": [AuditEvent(**event) for event in all_security_events[:100]]
        }
        
    except Exception as e:
        logger.error(f"Error fetching security events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch security events")


@router.get("/audit/compliance-report")
async def generate_compliance_report(
    start_date: datetime = Query(..., description="Report start date"),
    end_date: datetime = Query(..., description="Report end date"),
    admin: AdminUser = Depends(require_system_admin)
):
    """
    Generate comprehensive compliance report
    Only available to system admins
    """
    await log_admin_action(
        admin.user_id,
        "compliance_report_generated",
        details={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    )
    
    try:
        # Get all audit events for period
        events = await get_audit_events(
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )
        
        # Get admin actions
        admin_actions = await get_admin_actions(
            start_date=start_date,
            end_date=end_date,
            limit=5000
        )
        
        # Generate compliance metrics
        data_access_events = [e for e in events if e.get("event_type") == "data_access"]
        failed_auth_events = [e for e in events if e.get("outcome") == "failure"]
        
        report = {
            "report_period": {
                "start_date": start_date,
                "end_date": end_date,
                "generated_at": datetime.utcnow(),
                "generated_by": admin.user_id
            },
            "summary": {
                "total_audit_events": len(events),
                "total_admin_actions": len(admin_actions),
                "data_access_events": len(data_access_events),
                "failed_authentication_attempts": len(failed_auth_events),
                "unique_admin_users": len(set(e.get("user_id") for e in events if e.get("user_id")))
            },
            "data_access_summary": {
                "total_accesses": len(data_access_events),
                "unique_learners_accessed": len(set(
                    e.get("resource_id") for e in data_access_events 
                    if e.get("resource_type") == "learner_data"
                )),
                "purposes": list(set(
                    e.get("details", {}).get("purpose") for e in data_access_events
                    if e.get("details", {}).get("purpose")
                ))
            },
            "security_summary": {
                "failed_auth_count": len(failed_auth_events),
                "access_denied_count": len([
                    e for e in events if e.get("event_type") == "access_denied"
                ]),
                "emergency_access_count": len([
                    e for e in events if "emergency" in str(e.get("details", {}))
                ])
            },
            "admin_activity": {
                "most_active_users": _get_top_users(events, 10),
                "action_types": _count_by_field(admin_actions, "action_type"),
                "success_rate": _calculate_success_rate(admin_actions)
            }
        }
        
        return report
        
    except Exception as e:
        logger.error(f"Error generating compliance report: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate compliance report")


# Helper functions

async def _generate_csv_export(events: List[dict]) -> str:
    """Generate CSV export of audit events"""
    output = io.StringIO()
    
    if not events:
        return "No events found for the specified criteria"
    
    # Define CSV columns
    fieldnames = [
        "event_id", "event_type", "timestamp", "user_id", "session_id",
        "ip_address", "resource_type", "resource_id", "action", "outcome",
        "tenant_id", "details"
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for event in events:
        row = {}
        for field in fieldnames:
            value = event.get(field)
            if field == "details" and isinstance(value, dict):
                row[field] = json.dumps(value)
            elif field == "timestamp" and isinstance(value, datetime):
                row[field] = value.isoformat()
            else:
                row[field] = str(value) if value is not None else ""
        writer.writerow(row)
    
    return output.getvalue()


async def _generate_json_export(events: List[dict]) -> str:
    """Generate JSON export of audit events"""
    # Convert datetime objects to ISO strings
    serializable_events = []
    
    for event in events:
        serializable_event = {}
        for key, value in event.items():
            if isinstance(value, datetime):
                serializable_event[key] = value.isoformat()
            else:
                serializable_event[key] = value
        serializable_events.append(serializable_event)
    
    export_data = {
        "export_metadata": {
            "generated_at": datetime.utcnow().isoformat(),
            "event_count": len(events),
            "format_version": "1.0"
        },
        "events": serializable_events
    }
    
    return json.dumps(export_data, indent=2)


def _get_top_users(events: List[dict], limit: int) -> List[dict]:
    """Get most active users from events"""
    user_counts = {}
    
    for event in events:
        user_id = event.get("user_id")
        if user_id:
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
    
    # Sort by count and return top users
    sorted_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)
    
    return [
        {"user_id": user_id, "event_count": count}
        for user_id, count in sorted_users[:limit]
    ]


def _count_by_field(items: List[dict], field: str) -> dict:
    """Count occurrences of field values"""
    counts = {}
    
    for item in items:
        value = item.get(field)
        if value:
            counts[value] = counts.get(value, 0) + 1
    
    return counts


def _calculate_success_rate(actions: List[dict]) -> float:
    """Calculate success rate of admin actions"""
    if not actions:
        return 0.0
    
    successful = sum(1 for action in actions if action.get("success", False))
    return (successful / len(actions)) * 100
