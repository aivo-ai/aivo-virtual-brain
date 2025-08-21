"""
Audit logging functionality for AIVO Admin Service
Comprehensive tracking of all admin actions for compliance
"""

import uuid
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import json
import logging
from fastapi import Request

from app.database import execute_command, execute_query
from app.config import settings

logger = logging.getLogger(__name__)


async def log_admin_action(
    user_id: str,
    action_type: str,
    details: Dict[str, Any] = None,
    target_resource: str = None,
    session_id: str = None,
    success: bool = True,
    ip_address: str = None,
    user_agent: str = None,
    tenant_id: str = None
):
    """
    Log admin action to audit trail
    
    Args:
        user_id: ID of admin user performing action
        action_type: Type of action (e.g., 'queue_job_requeued', 'approval_viewed')
        details: Additional action details
        target_resource: Resource being acted upon
        session_id: Admin session ID
        success: Whether action was successful
        ip_address: Client IP address
        user_agent: Client user agent
        tenant_id: Tenant context if applicable
    """
    try:
        action_id = str(uuid.uuid4())
        
        # Sanitize details to ensure JSON serializable
        clean_details = _sanitize_details(details or {})
        
        await execute_command("""
            INSERT INTO admin_actions (
                action_id, user_id, session_id, action_type, target_resource,
                timestamp, success, details, ip_address, user_agent, tenant_id
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        """, 
            action_id, user_id, session_id, action_type, target_resource,
            datetime.utcnow(), success, json.dumps(clean_details), 
            ip_address, user_agent, tenant_id
        )
        
        # Also log to application logger for immediate visibility
        logger.info(
            f"ADMIN_ACTION: {action_type} by {user_id} "
            f"{'SUCCESS' if success else 'FAILED'} - {clean_details}"
        )
        
    except Exception as e:
        logger.error(f"Failed to log admin action: {e}")
        # Don't raise exception to avoid breaking the main operation


async def log_auth_event(
    event_type: str,
    user_id: str = None,
    details: Dict[str, Any] = None,
    ip_address: str = None,
    user_agent: str = None,
    outcome: str = "success"
):
    """
    Log authentication/authorization events
    
    Args:
        event_type: Type of auth event (login, logout, token_expired, etc.)
        user_id: User ID if known
        details: Additional event details
        ip_address: Client IP address
        user_agent: Client user agent
        outcome: Event outcome (success, failure, error)
    """
    try:
        event_id = str(uuid.uuid4())
        clean_details = _sanitize_details(details or {})
        
        await execute_command("""
            INSERT INTO audit_events (
                event_id, event_type, timestamp, user_id, ip_address, 
                user_agent, action, outcome, details
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
            event_id, event_type, datetime.utcnow(), user_id, ip_address,
            user_agent, event_type, outcome, json.dumps(clean_details)
        )
        
        logger.info(f"AUTH_EVENT: {event_type} - {outcome} - User: {user_id}")
        
    except Exception as e:
        logger.error(f"Failed to log auth event: {e}")


async def log_security_event(
    event_type: str,
    details: Dict[str, Any] = None,
    user_id: str = None,
    ip_address: str = None,
    resource_type: str = None,
    resource_id: str = None
):
    """
    Log security-related events (access denials, suspicious activity)
    
    Args:
        event_type: Type of security event
        details: Event details
        user_id: User ID if known
        ip_address: Client IP address
        resource_type: Type of resource accessed
        resource_id: Specific resource ID
    """
    try:
        event_id = str(uuid.uuid4())
        clean_details = _sanitize_details(details or {})
        
        await execute_command("""
            INSERT INTO audit_events (
                event_id, event_type, timestamp, user_id, ip_address,
                resource_type, resource_id, action, outcome, details
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
            event_id, event_type, datetime.utcnow(), user_id, ip_address,
            resource_type, resource_id, "security_check", "failure", 
            json.dumps(clean_details)
        )
        
        # Security events also go to security logger
        security_logger = logging.getLogger("security")
        security_logger.warning(
            f"SECURITY_EVENT: {event_type} - User: {user_id} - IP: {ip_address} - {clean_details}"
        )
        
    except Exception as e:
        logger.error(f"Failed to log security event: {e}")


async def log_system_event(
    event_type: str,
    details: Dict[str, Any] = None,
    resource_type: str = None,
    resource_id: str = None
):
    """
    Log system events (errors, performance issues, etc.)
    
    Args:
        event_type: Type of system event
        details: Event details
        resource_type: Type of resource involved
        resource_id: Specific resource ID
    """
    try:
        event_id = str(uuid.uuid4())
        clean_details = _sanitize_details(details or {})
        
        await execute_command("""
            INSERT INTO audit_events (
                event_id, event_type, timestamp, resource_type, resource_id,
                action, outcome, details
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
            event_id, event_type, datetime.utcnow(), resource_type, resource_id,
            "system_event", "error", json.dumps(clean_details)
        )
        
        logger.error(f"SYSTEM_EVENT: {event_type} - {clean_details}")
        
    except Exception as e:
        logger.error(f"Failed to log system event: {e}")


async def log_data_access(
    user_id: str,
    learner_id: str,
    data_type: str,
    purpose: str,
    session_id: str,
    data_summary: Dict[str, Any] = None,
    ip_address: str = None
):
    """
    Log learner data access for compliance
    
    Args:
        user_id: Staff user accessing data
        learner_id: Learner whose data is accessed
        data_type: Type of data accessed
        purpose: Business purpose for access
        session_id: Support session ID
        data_summary: Summary of data accessed (no PII)
        ip_address: Client IP address
    """
    try:
        # Log as admin action
        await log_admin_action(
            user_id=user_id,
            action_type="learner_data_accessed",
            details={
                "learner_id": learner_id,
                "data_type": data_type,
                "purpose": purpose,
                "data_summary": data_summary or {},
                "compliance_logged": True
            },
            target_resource=f"learner:{learner_id}",
            session_id=session_id,
            ip_address=ip_address
        )
        
        # Also log as audit event for compliance tracking
        await execute_command("""
            INSERT INTO audit_events (
                event_id, event_type, timestamp, user_id, resource_type,
                resource_id, action, outcome, details
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
            str(uuid.uuid4()), "data_access", datetime.utcnow(), user_id,
            "learner_data", learner_id, "data_read", "success",
            json.dumps({
                "data_type": data_type,
                "purpose": purpose,
                "session_id": session_id,
                "data_summary": data_summary or {}
            })
        )
        
        # Compliance logger
        compliance_logger = logging.getLogger("compliance")
        compliance_logger.info(
            f"DATA_ACCESS: User {user_id} accessed {data_type} for learner {learner_id} "
            f"Purpose: {purpose} Session: {session_id}"
        )
        
    except Exception as e:
        logger.error(f"Failed to log data access: {e}")


async def get_audit_events(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_id: Optional[str] = None,
    event_type: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Query audit events with filters
    
    Returns:
        List of audit events matching criteria
    """
    try:
        conditions = []
        params = []
        param_count = 0
        
        # Build WHERE clause
        if start_date:
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(start_date)
            
        if end_date:
            param_count += 1
            conditions.append(f"timestamp <= ${param_count}")
            params.append(end_date)
            
        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
            
        if event_type:
            param_count += 1
            conditions.append(f"event_type = ${param_count}")
            params.append(event_type)
            
        if outcome:
            param_count += 1
            conditions.append(f"outcome = ${param_count}")
            params.append(outcome)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Add pagination
        param_count += 1
        limit_clause = f"LIMIT ${param_count}"
        params.append(limit)
        
        param_count += 1
        offset_clause = f"OFFSET ${param_count}"
        params.append(offset)
        
        query = f"""
            SELECT event_id, event_type, timestamp, user_id, session_id,
                   ip_address, resource_type, resource_id, action, outcome,
                   details, tenant_id
            FROM audit_events
            {where_clause}
            ORDER BY timestamp DESC
            {limit_clause} {offset_clause}
        """
        
        rows = await execute_query(query, *params)
        
        return [
            {
                "event_id": row["event_id"],
                "event_type": row["event_type"],
                "timestamp": row["timestamp"],
                "user_id": row["user_id"],
                "session_id": row["session_id"],
                "ip_address": str(row["ip_address"]) if row["ip_address"] else None,
                "resource_type": row["resource_type"],
                "resource_id": row["resource_id"],
                "action": row["action"],
                "outcome": row["outcome"],
                "details": json.loads(row["details"]) if row["details"] else {},
                "tenant_id": row["tenant_id"]
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Failed to query audit events: {e}")
        return []


async def get_admin_actions(
    user_id: Optional[str] = None,
    action_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Query admin actions with filters
    
    Returns:
        List of admin actions matching criteria
    """
    try:
        conditions = []
        params = []
        param_count = 0
        
        if user_id:
            param_count += 1
            conditions.append(f"user_id = ${param_count}")
            params.append(user_id)
            
        if action_type:
            param_count += 1
            conditions.append(f"action_type = ${param_count}")
            params.append(action_type)
            
        if start_date:
            param_count += 1
            conditions.append(f"timestamp >= ${param_count}")
            params.append(start_date)
            
        if end_date:
            param_count += 1
            conditions.append(f"timestamp <= ${param_count}")
            params.append(end_date)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        param_count += 1
        params.append(limit)
        
        query = f"""
            SELECT action_id, user_id, session_id, action_type, target_resource,
                   timestamp, success, details, ip_address, user_agent, tenant_id
            FROM admin_actions
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_count}
        """
        
        rows = await execute_query(query, *params)
        
        return [
            {
                "action_id": row["action_id"],
                "user_id": row["user_id"],
                "session_id": row["session_id"],
                "action_type": row["action_type"],
                "target_resource": row["target_resource"],
                "timestamp": row["timestamp"],
                "success": row["success"],
                "details": json.loads(row["details"]) if row["details"] else {},
                "ip_address": str(row["ip_address"]) if row["ip_address"] else None,
                "user_agent": row["user_agent"],
                "tenant_id": row["tenant_id"]
            }
            for row in rows
        ]
        
    except Exception as e:
        logger.error(f"Failed to query admin actions: {e}")
        return []


def _sanitize_details(details: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize details dict to ensure JSON serializable and no sensitive data
    """
    if not isinstance(details, dict):
        return {}
    
    sanitized = {}
    
    # Fields that should never be logged
    sensitive_fields = [
        "password", "token", "secret", "key", "auth", "credential",
        "jwt", "bearer", "oauth", "session_token", "api_key"
    ]
    
    for key, value in details.items():
        # Skip sensitive fields
        if any(sensitive in key.lower() for sensitive in sensitive_fields):
            sanitized[key] = "[REDACTED]"
            continue
        
        # Ensure JSON serializable
        try:
            json.dumps(value)
            sanitized[key] = value
        except (TypeError, ValueError):
            sanitized[key] = str(value)
    
    return sanitized


# Middleware helper to extract request info
def extract_request_info(request: Request) -> Dict[str, str]:
    """Extract IP address and user agent from request"""
    return {
        "ip_address": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "method": request.method,
        "path": str(request.url.path)
    }
