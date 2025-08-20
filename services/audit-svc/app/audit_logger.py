"""
Audit Logger Module
Core audit logging functionality with who/what/when/why tracking
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4

import structlog

from .models import (
    AuditEvent, AuditEventType, AuditSeverity, DataAccessLog, AuditQuery, AuditReport,
    UserRole, DataClassification
)
from .database import get_db_pool, log_audit_event, log_data_access

logger = structlog.get_logger()


class AuditLogger:
    """Centralized audit logging with comprehensive tracking"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def log_event(
        self,
        event_type: AuditEventType,
        action: str,
        resource: str,
        outcome: str = "success",
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        actor_id: Optional[UUID] = None,
        actor_type: Optional[UserRole] = None,
        actor_email: Optional[str] = None,
        actor_ip: Optional[str] = None,
        actor_user_agent: Optional[str] = None,
        target_id: Optional[UUID] = None,
        target_type: Optional[str] = None,
        target_classification: Optional[DataClassification] = None,
        tenant_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditEvent:
        """Log a comprehensive audit event"""
        
        # Generate IDs if not provided
        if not tenant_id:
            tenant_id = uuid4()  # Default tenant in real implementation
        if not session_id:
            session_id = str(uuid4())
        if not request_id:
            request_id = str(uuid4())
        
        event_id = await log_audit_event(
            event_type=event_type,
            action=action,
            resource=resource,
            outcome=outcome,
            severity=severity,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_email=actor_email,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            target_id=target_id,
            target_type=target_type,
            target_classification=target_classification.value if target_classification else None,
            tenant_id=tenant_id,
            session_id=session_id,
            request_id=request_id,
            reason=reason,
            metadata=metadata
        )
        
        # Create event object for return
        event = AuditEvent(
            id=event_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            severity=severity,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_email=actor_email,
            actor_ip=actor_ip,
            actor_user_agent=actor_user_agent,
            target_id=target_id,
            target_type=target_type,
            target_classification=target_classification,
            tenant_id=tenant_id,
            session_id=session_id,
            request_id=request_id,
            action=action,
            resource=resource,
            outcome=outcome,
            reason=reason,
            metadata=metadata or {}
        )
        
        # Log to structured logger as well
        self.logger.info(
            "Audit event logged",
            event_id=str(event_id),
            event_type=event_type.value,
            action=action,
            resource=resource,
            outcome=outcome,
            severity=severity.value,
            actor_id=str(actor_id) if actor_id else None,
            target_id=str(target_id) if target_id else None
        )
        
        return event
    
    async def log_sensitive_data_access(
        self,
        user_id: UUID,
        user_role: UserRole,
        user_email: str,
        data_type: str,
        operation: str,
        purpose: str,
        tenant_id: UUID,
        session_id: str,
        data_id: Optional[UUID] = None,
        data_classification: DataClassification = DataClassification.INTERNAL,
        endpoint: Optional[str] = None,
        sql_query: Optional[str] = None,
        justification: Optional[str] = None,
        ip_address: Optional[str] = None,
        records_affected: int = 0,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> UUID:
        """Log sensitive data access with enhanced tracking"""
        
        # Hash SQL query for privacy
        sql_query_hash = None
        if sql_query:
            sql_query_hash = hashlib.sha256(sql_query.encode()).hexdigest()[:64]
        
        # Log data access
        log_id = await log_data_access(
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
            data_type=data_type,
            operation=operation,
            purpose=purpose,
            tenant_id=tenant_id,
            session_id=session_id,
            data_id=data_id,
            data_classification=data_classification.value,
            endpoint=endpoint,
            sql_query_hash=sql_query_hash,
            justification=justification,
            ip_address=ip_address,
            records_affected=records_affected,
            success=success,
            error_message=error_message
        )
        
        # Also create corresponding audit event
        await self.log_event(
            event_type=AuditEventType.DATA_READ if operation == "read" else 
                      AuditEventType.DATA_WRITE if operation == "write" else
                      AuditEventType.DATA_DELETE if operation == "delete" else
                      AuditEventType.DATA_EXPORT,
            action=f"data_{operation}",
            resource=data_type,
            outcome="success" if success else "failure",
            severity=self._get_severity_for_data_access(data_classification, operation),
            actor_id=user_id,
            actor_type=user_role,
            actor_email=user_email,
            actor_ip=ip_address,
            target_id=data_id,
            target_type=data_type,
            target_classification=data_classification,
            tenant_id=tenant_id,
            session_id=session_id,
            reason=justification,
            metadata={
                "purpose": purpose,
                "endpoint": endpoint,
                "records_affected": records_affected,
                "sql_query_hash": sql_query_hash,
                "error_message": error_message if not success else None
            }
        )
        
        return log_id
    
    async def log_api_access(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str,
        user_agent: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_id: Optional[UUID] = None,
        tenant_id: Optional[UUID] = None
    ):
        """Log API access for audit trail"""
        
        severity = AuditSeverity.LOW
        if status_code >= 500:
            severity = AuditSeverity.HIGH
        elif status_code >= 400:
            severity = AuditSeverity.MEDIUM
        
        await self.log_event(
            event_type=AuditEventType.DATA_READ,
            action="api_access",
            resource="api_endpoint",
            outcome="success" if status_code < 400 else "failure",
            severity=severity,
            actor_id=user_id,
            actor_ip=ip_address,
            actor_user_agent=user_agent,
            tenant_id=tenant_id or uuid4(),
            request_id=request_id,
            metadata={
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms
            }
        )
    
    async def query_events(self, query: AuditQuery) -> List[AuditEvent]:
        """Query audit events with filters"""
        
        pool = await get_db_pool()
        
        # Build SQL query
        where_conditions = []
        params = []
        param_count = 0
        
        # Time range filter
        if query.start_date:
            param_count += 1
            where_conditions.append(f"timestamp >= ${param_count}")
            params.append(query.start_date)
        
        if query.end_date:
            param_count += 1
            where_conditions.append(f"timestamp <= ${param_count}")
            params.append(query.end_date)
        
        # Event type filter
        if query.event_types:
            param_count += 1
            where_conditions.append(f"event_type = ANY(${param_count})")
            params.append([et.value for et in query.event_types])
        
        # Severity filter
        if query.severities:
            param_count += 1
            where_conditions.append(f"severity = ANY(${param_count})")
            params.append([s.value for s in query.severities])
        
        # Actor filter
        if query.actor_ids:
            param_count += 1
            where_conditions.append(f"actor_id = ANY(${param_count})")
            params.append(query.actor_ids)
        
        # Target filter
        if query.target_ids:
            param_count += 1
            where_conditions.append(f"target_id = ANY(${param_count})")
            params.append(query.target_ids)
        
        # Tenant filter
        if query.tenant_id:
            param_count += 1
            where_conditions.append(f"tenant_id = ${param_count}")
            params.append(query.tenant_id)
        
        # Search filter
        if query.search_term:
            param_count += 1
            where_conditions.append(f"(action ILIKE ${param_count} OR resource ILIKE ${param_count} OR reason ILIKE ${param_count})")
            params.append(f"%{query.search_term}%")
        
        # Build complete query
        base_query = "SELECT * FROM audit_events"
        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)
        
        # Add sorting
        base_query += f" ORDER BY {query.sort_by} {query.sort_order.upper()}"
        
        # Add pagination
        param_count += 1
        base_query += f" LIMIT ${param_count}"
        params.append(query.page_size)
        
        param_count += 1
        base_query += f" OFFSET ${param_count}"
        params.append((query.page - 1) * query.page_size)
        
        async with pool.acquire() as conn:
            rows = await conn.fetch(base_query, *params)
            
            events = []
            for row in rows:
                event_data = dict(row)
                # Convert string enums back to enum objects
                event_data['event_type'] = AuditEventType(event_data['event_type'])
                event_data['severity'] = AuditSeverity(event_data['severity'])
                if event_data['actor_type']:
                    event_data['actor_type'] = UserRole(event_data['actor_type'])
                if event_data['target_classification']:
                    event_data['target_classification'] = DataClassification(event_data['target_classification'])
                
                events.append(AuditEvent(**event_data))
            
            return events
    
    async def generate_summary_report(
        self,
        tenant_id: UUID,
        start_date: datetime,
        end_date: datetime
    ) -> AuditReport:
        """Generate comprehensive audit summary report"""
        
        pool = await get_db_pool()
        
        async with pool.acquire() as conn:
            
            # Total events
            total_events = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3
                """,
                tenant_id, start_date, end_date
            )
            
            # Events by type
            events_by_type_rows = await conn.fetch(
                """
                SELECT event_type, COUNT(*) as count 
                FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3
                GROUP BY event_type
                ORDER BY count DESC
                """,
                tenant_id, start_date, end_date
            )
            events_by_type = {row['event_type']: row['count'] for row in events_by_type_rows}
            
            # Events by severity
            events_by_severity_rows = await conn.fetch(
                """
                SELECT severity, COUNT(*) as count 
                FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3
                GROUP BY severity
                ORDER BY count DESC
                """,
                tenant_id, start_date, end_date
            )
            events_by_severity = {row['severity']: row['count'] for row in events_by_severity_rows}
            
            # Unique actors
            unique_actors = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT actor_id) FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3 AND actor_id IS NOT NULL
                """,
                tenant_id, start_date, end_date
            )
            
            # Failed events
            failed_events = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3 AND outcome IN ('failure', 'error')
                """,
                tenant_id, start_date, end_date
            )
            
            # Top actors
            top_actors_rows = await conn.fetch(
                """
                SELECT actor_id, actor_email, COUNT(*) as event_count
                FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3 AND actor_id IS NOT NULL
                GROUP BY actor_id, actor_email
                ORDER BY event_count DESC
                LIMIT 10
                """,
                tenant_id, start_date, end_date
            )
            top_actors = [
                {
                    "actor_id": str(row['actor_id']),
                    "actor_email": row['actor_email'],
                    "event_count": row['event_count']
                }
                for row in top_actors_rows
            ]
            
            # Top resources
            top_resources_rows = await conn.fetch(
                """
                SELECT resource, COUNT(*) as access_count
                FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3
                GROUP BY resource
                ORDER BY access_count DESC
                LIMIT 10
                """,
                tenant_id, start_date, end_date
            )
            top_resources = [
                {
                    "resource": row['resource'],
                    "access_count": row['access_count']
                }
                for row in top_resources_rows
            ]
            
            # Risk events (high/critical severity)
            risk_events_rows = await conn.fetch(
                """
                SELECT id, timestamp, event_type, action, resource, severity, outcome
                FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3 
                AND severity IN ('high', 'critical')
                ORDER BY timestamp DESC
                LIMIT 50
                """,
                tenant_id, start_date, end_date
            )
            risk_events = [
                {
                    "id": str(row['id']),
                    "timestamp": row['timestamp'].isoformat(),
                    "event_type": row['event_type'],
                    "action": row['action'],
                    "resource": row['resource'],
                    "severity": row['severity'],
                    "outcome": row['outcome']
                }
                for row in risk_events_rows
            ]
            
            # Compliance metrics
            access_reviews_completed = await conn.fetchval(
                """
                SELECT COUNT(*) FROM access_reviews 
                WHERE tenant_id = $1 AND completed_at BETWEEN $2 AND $3
                """,
                tenant_id, start_date, end_date
            )
            
            support_sessions_approved = await conn.fetchval(
                """
                SELECT COUNT(*) FROM support_sessions 
                WHERE tenant_id = $1 AND approved_at BETWEEN $2 AND $3
                """,
                tenant_id, start_date, end_date
            )
            
            policy_violations = await conn.fetchval(
                """
                SELECT COUNT(*) FROM audit_events 
                WHERE tenant_id = $1 AND timestamp BETWEEN $2 AND $3 
                AND event_type = 'permission_denied' AND severity IN ('high', 'critical')
                """,
                tenant_id, start_date, end_date
            )
        
        report = AuditReport(
            tenant_id=tenant_id,
            report_type="summary",
            period_start=start_date,
            period_end=end_date,
            total_events=total_events,
            events_by_type=events_by_type,
            events_by_severity=events_by_severity,
            unique_actors=unique_actors,
            failed_events=failed_events,
            top_actors=top_actors,
            top_resources=top_resources,
            risk_events=risk_events,
            access_reviews_completed=access_reviews_completed,
            support_sessions_approved=support_sessions_approved,
            policy_violations=policy_violations
        )
        
        return report
    
    def _get_severity_for_data_access(
        self, 
        classification: DataClassification, 
        operation: str
    ) -> AuditSeverity:
        """Determine severity based on data classification and operation"""
        
        if classification == DataClassification.RESTRICTED:
            return AuditSeverity.CRITICAL if operation in ["write", "delete"] else AuditSeverity.HIGH
        elif classification == DataClassification.CONFIDENTIAL:
            return AuditSeverity.HIGH if operation in ["write", "delete"] else AuditSeverity.MEDIUM
        elif classification == DataClassification.INTERNAL:
            return AuditSeverity.MEDIUM if operation in ["write", "delete"] else AuditSeverity.LOW
        else:  # PUBLIC
            return AuditSeverity.LOW
