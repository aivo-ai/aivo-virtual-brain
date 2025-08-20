"""
Support Manager Module
Just-In-Time support session management with guardian consent
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID, uuid4

import structlog

from .models import (
    SupportSession, SupportSessionStatus, UserRole
)
from .database import get_db_pool

logger = structlog.get_logger()


class SupportManager:
    """Manages JIT support sessions with guardian consent workflow"""
    
    def __init__(self):
        self.logger = structlog.get_logger(__name__)
    
    async def create_session(
        self,
        learner_id: UUID,
        guardian_id: UUID,
        reason: str,
        description: Optional[str] = None,
        urgency: str = "normal",
        max_duration_minutes: int = 60,
        allowed_data_types: Optional[List[str]] = None,
        tenant_id: UUID = None
    ) -> SupportSession:
        """Create a new support session request"""
        
        session = SupportSession(
            learner_id=learner_id,
            guardian_id=guardian_id,
            reason=reason,
            description=description,
            urgency=urgency,
            max_duration_minutes=max_duration_minutes,
            allowed_data_types=allowed_data_types or [],
            tenant_id=tenant_id or uuid4(),
            status=SupportSessionStatus.REQUESTED
        )
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            await conn.execute(
                """
                INSERT INTO support_sessions (
                    id, created_at, updated_at, learner_id, guardian_id,
                    status, reason, description, urgency, requested_at,
                    max_duration_minutes, allowed_data_types, tenant_id
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
                """,
                session.id, session.created_at, session.updated_at,
                session.learner_id, session.guardian_id, session.status.value,
                session.reason, session.description, session.urgency,
                session.requested_at, session.max_duration_minutes,
                session.allowed_data_types, session.tenant_id
            )
        
        # Automatically request approval from guardian
        await self._request_guardian_approval(session)
        
        self.logger.info(
            "Support session created",
            session_id=str(session.id),
            learner_id=str(learner_id),
            guardian_id=str(guardian_id),
            reason=reason,
            urgency=urgency
        )
        
        return session
    
    async def _request_guardian_approval(self, session: SupportSession):
        """Request approval from guardian (mock implementation)"""
        
        # In a real implementation, this would:
        # 1. Send notification to guardian (email, SMS, push notification)
        # 2. Create approval workflow in notification service
        # 3. Set up approval timeout
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            await conn.execute(
                """
                UPDATE support_sessions 
                SET status = $1, approval_requested_at = $2, updated_at = $3
                WHERE id = $4
                """,
                SupportSessionStatus.PENDING_APPROVAL.value,
                datetime.utcnow(),
                datetime.utcnow(),
                session.id
            )
        
        self.logger.info(
            "Guardian approval requested",
            session_id=str(session.id),
            guardian_id=str(session.guardian_id)
        )
    
    async def approve_session(
        self,
        session_id: UUID,
        approved: bool,
        reason: Optional[str] = None,
        approver_id: UUID = None,
        max_duration_minutes: Optional[int] = None,
        allowed_data_types: Optional[List[str]] = None,
        tenant_id: UUID = None
    ) -> SupportSession:
        """Approve or deny support session"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Get current session
            session_row = await conn.fetchrow(
                """
                SELECT * FROM support_sessions 
                WHERE id = $1 AND tenant_id = $2
                """,
                session_id, tenant_id
            )
            
            if not session_row:
                raise ValueError("Support session not found")
            
            session_data = dict(session_row)
            session_data['status'] = SupportSessionStatus(session_data['status'])
            session = SupportSession(**session_data)
            
            # Verify guardian permission
            if approver_id and session.guardian_id != approver_id:
                raise ValueError("Only the guardian can approve this session")
            
            # Update session status
            new_status = SupportSessionStatus.APPROVED if approved else SupportSessionStatus.DENIED
            update_time = datetime.utcnow()
            
            update_fields = {
                "status": new_status.value,
                "updated_at": update_time,
                "approval_reason": reason
            }
            
            if approved:
                update_fields["approved_at"] = update_time
                # Override duration and data types if specified
                if max_duration_minutes:
                    update_fields["max_duration_minutes"] = max_duration_minutes
                if allowed_data_types is not None:
                    update_fields["allowed_data_types"] = allowed_data_types
            else:
                update_fields["denied_at"] = update_time
            
            # Build update query
            set_clauses = []
            params = []
            param_count = 0
            
            for field, value in update_fields.items():
                param_count += 1
                set_clauses.append(f"{field} = ${param_count}")
                params.append(value)
            
            param_count += 1
            params.append(session_id)
            
            query = f"""
                UPDATE support_sessions 
                SET {', '.join(set_clauses)}
                WHERE id = ${param_count}
            """
            
            await conn.execute(query, *params)
            
            # Get updated session
            updated_row = await conn.fetchrow(
                "SELECT * FROM support_sessions WHERE id = $1",
                session_id
            )
            
            updated_data = dict(updated_row)
            updated_data['status'] = SupportSessionStatus(updated_data['status'])
            updated_session = SupportSession(**updated_data)
        
        self.logger.info(
            "Support session approval processed",
            session_id=str(session_id),
            approved=approved,
            approver_id=str(approver_id) if approver_id else None,
            reason=reason
        )
        
        return updated_session
    
    async def start_session(
        self,
        session_id: UUID,
        support_agent_id: UUID,
        tenant_id: UUID
    ) -> Tuple[SupportSession, str]:
        """Start an approved support session and issue access token"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Get session
            session_row = await conn.fetchrow(
                """
                SELECT * FROM support_sessions 
                WHERE id = $1 AND tenant_id = $2 AND status = $3
                """,
                session_id, tenant_id, SupportSessionStatus.APPROVED.value
            )
            
            if not session_row:
                raise ValueError("Approved support session not found")
            
            session_data = dict(session_row)
            session_data['status'] = SupportSessionStatus(session_data['status'])
            session = SupportSession(**session_data)
            
            # Generate secure access token
            access_token = self._generate_access_token(session_id, support_agent_id)
            
            # Calculate token expiry
            session_start = datetime.utcnow()
            token_expires_at = session_start + timedelta(minutes=session.max_duration_minutes)
            
            # Update session
            await conn.execute(
                """
                UPDATE support_sessions 
                SET 
                    status = $1,
                    support_agent_id = $2,
                    session_start = $3,
                    access_token = $4,
                    token_expires_at = $5,
                    updated_at = $6
                WHERE id = $7
                """,
                SupportSessionStatus.ACTIVE.value,
                support_agent_id,
                session_start,
                access_token,
                token_expires_at,
                datetime.utcnow(),
                session_id
            )
            
            # Get updated session
            updated_row = await conn.fetchrow(
                "SELECT * FROM support_sessions WHERE id = $1",
                session_id
            )
            
            updated_data = dict(updated_row)
            updated_data['status'] = SupportSessionStatus(updated_data['status'])
            updated_session = SupportSession(**updated_data)
        
        # Schedule automatic session termination
        await self._schedule_session_termination(session_id, token_expires_at)
        
        self.logger.info(
            "Support session started",
            session_id=str(session_id),
            support_agent_id=str(support_agent_id),
            expires_at=token_expires_at.isoformat()
        )
        
        return updated_session, access_token
    
    def _generate_access_token(self, session_id: UUID, support_agent_id: UUID) -> str:
        """Generate secure time-limited access token"""
        
        # Create token payload
        payload = f"{session_id}:{support_agent_id}:{datetime.utcnow().isoformat()}"
        
        # Add random component for uniqueness
        random_component = secrets.token_hex(16)
        
        # Hash the payload for security
        token_hash = hashlib.sha256(f"{payload}:{random_component}".encode()).hexdigest()
        
        # Create final token (could be JWT in real implementation)
        access_token = f"support_{token_hash[:32]}"
        
        return access_token
    
    async def _schedule_session_termination(self, session_id: UUID, expires_at: datetime):
        """Schedule automatic session termination (mock implementation)"""
        
        # In a real implementation, this would:
        # 1. Schedule a background job to terminate the session
        # 2. Set up monitoring for token expiry
        # 3. Create alerts for overdue sessions
        
        self.logger.info(
            "Session termination scheduled",
            session_id=str(session_id),
            expires_at=expires_at.isoformat()
        )
    
    async def end_session(
        self,
        session_id: UUID,
        ended_by: UUID,
        tenant_id: UUID,
        reason: Optional[str] = None
    ) -> SupportSession:
        """End an active support session"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Get current session
            session_row = await conn.fetchrow(
                """
                SELECT * FROM support_sessions 
                WHERE id = $1 AND tenant_id = $2 AND status = $3
                """,
                session_id, tenant_id, SupportSessionStatus.ACTIVE.value
            )
            
            if not session_row:
                raise ValueError("Active support session not found")
            
            session_data = dict(session_row)
            session_data['status'] = SupportSessionStatus(session_data['status'])
            session = SupportSession(**session_data)
            
            # End session
            session_end = datetime.utcnow()
            
            await conn.execute(
                """
                UPDATE support_sessions 
                SET 
                    status = $1,
                    session_end = $2,
                    access_token = NULL,
                    updated_at = $3
                WHERE id = $4
                """,
                SupportSessionStatus.COMPLETED.value,
                session_end,
                datetime.utcnow(),
                session_id
            )
            
            # Get updated session
            updated_row = await conn.fetchrow(
                "SELECT * FROM support_sessions WHERE id = $1",
                session_id
            )
            
            updated_data = dict(updated_row)
            updated_data['status'] = SupportSessionStatus(updated_data['status'])
            updated_session = SupportSession(**updated_data)
        
        # Calculate session duration
        if session.session_start:
            duration = (session_end - session.session_start).total_seconds() / 60
        else:
            duration = 0
        
        self.logger.info(
            "Support session ended",
            session_id=str(session_id),
            ended_by=str(ended_by),
            duration_minutes=duration,
            reason=reason
        )
        
        return updated_session
    
    async def validate_access_token(
        self,
        access_token: str,
        tenant_id: UUID
    ) -> Optional[SupportSession]:
        """Validate support access token"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            session_row = await conn.fetchrow(
                """
                SELECT * FROM support_sessions 
                WHERE access_token = $1 AND tenant_id = $2 AND status = $3
                """,
                access_token, tenant_id, SupportSessionStatus.ACTIVE.value
            )
            
            if not session_row:
                return None
            
            session_data = dict(session_row)
            session_data['status'] = SupportSessionStatus(session_data['status'])
            session = SupportSession(**session_data)
            
            # Check if token has expired
            if session.token_expires_at and datetime.utcnow() > session.token_expires_at:
                # Mark session as expired
                await conn.execute(
                    """
                    UPDATE support_sessions 
                    SET status = $1, access_token = NULL, updated_at = $2
                    WHERE id = $3
                    """,
                    SupportSessionStatus.EXPIRED.value,
                    datetime.utcnow(),
                    session.id
                )
                
                self.logger.warning(
                    "Support session token expired",
                    session_id=str(session.id),
                    expired_at=session.token_expires_at.isoformat()
                )
                
                return None
            
            return session
    
    async def log_support_action(
        self,
        session_id: UUID,
        action: str,
        resource: str,
        details: Dict[str, Any],
        tenant_id: UUID
    ):
        """Log action performed during support session"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            # Get current actions
            session_row = await conn.fetchrow(
                "SELECT actions_performed FROM support_sessions WHERE id = $1 AND tenant_id = $2",
                session_id, tenant_id
            )
            
            if not session_row:
                raise ValueError("Support session not found")
            
            current_actions = session_row['actions_performed'] or []
            
            # Add new action
            new_action = {
                "timestamp": datetime.utcnow().isoformat(),
                "action": action,
                "resource": resource,
                "details": details
            }
            
            current_actions.append(new_action)
            
            # Update session
            await conn.execute(
                """
                UPDATE support_sessions 
                SET actions_performed = $1, updated_at = $2
                WHERE id = $3
                """,
                current_actions,
                datetime.utcnow(),
                session_id
            )
        
        self.logger.info(
            "Support action logged",
            session_id=str(session_id),
            action=action,
            resource=resource
        )
    
    async def get_active_sessions(self, tenant_id: UUID) -> List[SupportSession]:
        """Get all active support sessions for tenant"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            rows = await conn.fetch(
                """
                SELECT * FROM support_sessions 
                WHERE tenant_id = $1 AND status = $2
                ORDER BY session_start
                """,
                tenant_id, SupportSessionStatus.ACTIVE.value
            )
            
            sessions = []
            for row in rows:
                session_data = dict(row)
                session_data['status'] = SupportSessionStatus(session_data['status'])
                sessions.append(SupportSession(**session_data))
            
            return sessions
    
    async def expire_overdue_sessions(self, tenant_id: Optional[UUID] = None):
        """Expire sessions that have exceeded their time limit"""
        
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            
            where_clause = "status = $1 AND token_expires_at < $2"
            params = [SupportSessionStatus.ACTIVE.value, datetime.utcnow()]
            
            if tenant_id:
                where_clause += " AND tenant_id = $3"
                params.append(tenant_id)
            
            # Get overdue sessions
            overdue_sessions = await conn.fetch(
                f"SELECT id, learner_id, support_agent_id FROM support_sessions WHERE {where_clause}",
                *params
            )
            
            if overdue_sessions:
                # Mark as expired
                await conn.execute(
                    f"""
                    UPDATE support_sessions 
                    SET status = $1, access_token = NULL, session_end = $2, updated_at = $3
                    WHERE {where_clause}
                    """,
                    SupportSessionStatus.EXPIRED.value,
                    datetime.utcnow(),
                    datetime.utcnow(),
                    *params[1:]  # Skip the first status parameter
                )
                
                self.logger.info(
                    "Expired overdue support sessions",
                    count=len(overdue_sessions),
                    tenant_id=str(tenant_id) if tenant_id else "all"
                )
            
            return len(overdue_sessions)
