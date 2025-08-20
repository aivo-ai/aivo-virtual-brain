"""
Database Connection and Audit Event Storage
PostgreSQL connection management for audit service
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

import asyncpg
import structlog
from asyncpg import Pool

from .models import AuditEvent, AuditEventType, AuditSeverity, UserRole

logger = structlog.get_logger()

# Global connection pool
_pool: Optional[Pool] = None


async def init_db_pool() -> Pool:
    """Initialize database connection pool"""
    
    global _pool
    
    if _pool is not None:
        return _pool
    
    # Database configuration from environment
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "aivo_audit"),
        "user": os.getenv("POSTGRES_USER", "audit_user"),
        "password": os.getenv("POSTGRES_PASSWORD", "audit_password"),
        "min_size": int(os.getenv("DB_POOL_MIN_SIZE", "5")),
        "max_size": int(os.getenv("DB_POOL_MAX_SIZE", "20")),
        "command_timeout": int(os.getenv("DB_COMMAND_TIMEOUT", "30")),
    }
    
    try:
        _pool = await asyncpg.create_pool(**db_config)
        logger.info("Database pool created", host=db_config["host"], database=db_config["database"])
        
        # Test connection and create tables if needed
        async with _pool.acquire() as conn:
            await create_audit_tables(conn)
        
        return _pool
        
    except Exception as e:
        logger.error("Failed to create database pool", error=str(e))
        raise


async def get_db_pool() -> Pool:
    """Get database connection pool"""
    
    global _pool
    
    if _pool is None:
        _pool = await init_db_pool()
    
    return _pool


async def close_db_pool():
    """Close database connection pool"""
    
    global _pool
    
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def create_audit_tables(conn: asyncpg.Connection):
    """Create audit-related database tables"""
    
    logger.info("Creating audit database tables")
    
    # Audit events table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            id UUID PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL DEFAULT 'medium',
            
            -- Actor information
            actor_id UUID,
            actor_type VARCHAR(20),
            actor_email VARCHAR(255),
            actor_ip INET,
            actor_user_agent TEXT,
            
            -- Target information
            target_id UUID,
            target_type VARCHAR(100),
            target_classification VARCHAR(20),
            
            -- Context
            tenant_id UUID NOT NULL,
            session_id VARCHAR(100),
            request_id VARCHAR(100),
            
            -- Event details
            action VARCHAR(100) NOT NULL,
            resource VARCHAR(100) NOT NULL,
            outcome VARCHAR(20) NOT NULL DEFAULT 'success',
            reason TEXT,
            
            -- Metadata
            metadata JSONB DEFAULT '{}',
            
            -- Compliance
            retention_days INTEGER DEFAULT 2555,
            
            -- Indexes
            CONSTRAINT valid_event_type CHECK (event_type IN (
                'data_read', 'data_write', 'data_delete', 'data_export', 'data_anonymize',
                'login_success', 'login_failure', 'logout', 'password_change', 'mfa_enabled', 'mfa_disabled',
                'permission_granted', 'permission_denied', 'role_assigned', 'role_removed',
                'support_session_request', 'support_session_approved', 'support_session_denied',
                'support_session_start', 'support_session_end', 'support_token_issued', 'support_token_expired',
                'user_created', 'user_updated', 'user_disabled', 'system_config_changed',
                'access_review_started', 'access_review_completed', 'access_certified', 'access_revoked'
            )),
            CONSTRAINT valid_severity CHECK (severity IN ('low', 'medium', 'high', 'critical')),
            CONSTRAINT valid_outcome CHECK (outcome IN ('success', 'failure', 'error'))
        )
    """)
    
    # Data access logs table (specialized for sensitive data access)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS data_access_logs (
            id UUID PRIMARY KEY,
            timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            -- Who
            user_id UUID NOT NULL,
            user_role VARCHAR(20) NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            
            -- What
            data_type VARCHAR(100) NOT NULL,
            data_id UUID,
            data_classification VARCHAR(20) NOT NULL,
            
            -- How
            operation VARCHAR(20) NOT NULL,
            endpoint VARCHAR(255),
            sql_query_hash VARCHAR(64),
            
            -- Why
            purpose VARCHAR(255) NOT NULL,
            justification TEXT,
            
            -- Context
            tenant_id UUID NOT NULL,
            session_id VARCHAR(100) NOT NULL,
            ip_address INET,
            
            -- Result
            records_affected INTEGER DEFAULT 0,
            success BOOLEAN DEFAULT TRUE,
            error_message TEXT,
            
            CONSTRAINT valid_operation CHECK (operation IN ('read', 'write', 'delete', 'export')),
            CONSTRAINT valid_classification CHECK (data_classification IN ('public', 'internal', 'confidential', 'restricted'))
        )
    """)
    
    # Access reviews table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS access_reviews (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            -- Review scope
            tenant_id UUID NOT NULL,
            review_type VARCHAR(20) NOT NULL DEFAULT 'quarterly',
            review_period_start TIMESTAMPTZ NOT NULL,
            review_period_end TIMESTAMPTZ NOT NULL,
            
            -- Status
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            due_date TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            
            -- Reviewer
            reviewer_id UUID NOT NULL,
            reviewer_email VARCHAR(255) NOT NULL,
            
            -- Scope filters
            roles_to_review TEXT[] DEFAULT ARRAY[]::TEXT[],
            departments TEXT[] DEFAULT ARRAY[]::TEXT[],
            risk_levels TEXT[] DEFAULT ARRAY[]::TEXT[],
            
            -- Results
            total_users_reviewed INTEGER DEFAULT 0,
            access_certified INTEGER DEFAULT 0,
            access_revoked INTEGER DEFAULT 0,
            access_modified INTEGER DEFAULT 0,
            
            -- Metadata
            notes TEXT,
            attachments TEXT[] DEFAULT ARRAY[]::TEXT[],
            
            CONSTRAINT valid_status CHECK (status IN ('pending', 'in_progress', 'completed', 'overdue'))
        )
    """)
    
    # Access review items table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS access_review_items (
            id UUID PRIMARY KEY,
            review_id UUID NOT NULL REFERENCES access_reviews(id) ON DELETE CASCADE,
            
            -- User being reviewed
            user_id UUID NOT NULL,
            user_email VARCHAR(255) NOT NULL,
            user_role VARCHAR(20) NOT NULL,
            department VARCHAR(100),
            
            -- Access details
            permissions TEXT[] DEFAULT ARRAY[]::TEXT[],
            roles TEXT[] DEFAULT ARRAY[]::TEXT[],
            last_login TIMESTAMPTZ,
            last_activity TIMESTAMPTZ,
            
            -- Review decision
            status VARCHAR(20) DEFAULT 'pending',
            reviewed_at TIMESTAMPTZ,
            reviewer_notes TEXT,
            
            -- Risk assessment
            risk_score DECIMAL(3,2) DEFAULT 0.0,
            risk_factors TEXT[] DEFAULT ARRAY[]::TEXT[],
            
            -- Changes made
            changes_made JSONB DEFAULT '[]',
            
            CONSTRAINT valid_item_status CHECK (status IN ('pending', 'certified', 'revoked', 'modified'))
        )
    """)
    
    # Support sessions table
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS support_sessions (
            id UUID PRIMARY KEY,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            
            -- Request details
            learner_id UUID NOT NULL,
            guardian_id UUID NOT NULL,
            support_agent_id UUID,
            
            -- Session details
            status VARCHAR(20) NOT NULL DEFAULT 'requested',
            reason VARCHAR(255) NOT NULL,
            description TEXT,
            urgency VARCHAR(20) DEFAULT 'normal',
            
            -- Approval workflow
            requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            approval_requested_at TIMESTAMPTZ,
            approved_at TIMESTAMPTZ,
            denied_at TIMESTAMPTZ,
            approval_reason TEXT,
            
            -- Session timing
            session_start TIMESTAMPTZ,
            session_end TIMESTAMPTZ,
            max_duration_minutes INTEGER DEFAULT 60,
            
            -- Access control
            read_only BOOLEAN DEFAULT TRUE,
            allowed_data_types TEXT[] DEFAULT ARRAY[]::TEXT[],
            restricted_data_types TEXT[] DEFAULT ARRAY[]::TEXT[],
            
            -- Tracking
            access_token VARCHAR(255),
            token_expires_at TIMESTAMPTZ,
            actions_performed JSONB DEFAULT '[]',
            
            -- Metadata
            tenant_id UUID NOT NULL,
            ip_address INET,
            user_agent TEXT,
            
            CONSTRAINT valid_session_status CHECK (status IN ('requested', 'pending_approval', 'approved', 'denied', 'active', 'completed', 'expired')),
            CONSTRAINT valid_urgency CHECK (urgency IN ('low', 'normal', 'high', 'emergency'))
        )
    """)
    
    # Create indexes for performance
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audit_events_timestamp ON audit_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_audit_events_tenant_id ON audit_events(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_audit_events_event_type ON audit_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id ON audit_events(actor_id);
        CREATE INDEX IF NOT EXISTS idx_audit_events_target_id ON audit_events(target_id);
        CREATE INDEX IF NOT EXISTS idx_audit_events_severity ON audit_events(severity);
        CREATE INDEX IF NOT EXISTS idx_audit_events_outcome ON audit_events(outcome);
        CREATE INDEX IF NOT EXISTS idx_audit_events_metadata ON audit_events USING GIN(metadata);
        
        CREATE INDEX IF NOT EXISTS idx_data_access_logs_timestamp ON data_access_logs(timestamp);
        CREATE INDEX IF NOT EXISTS idx_data_access_logs_tenant_id ON data_access_logs(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_data_access_logs_user_id ON data_access_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_data_access_logs_data_type ON data_access_logs(data_type);
        CREATE INDEX IF NOT EXISTS idx_data_access_logs_operation ON data_access_logs(operation);
        
        CREATE INDEX IF NOT EXISTS idx_access_reviews_tenant_id ON access_reviews(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_access_reviews_status ON access_reviews(status);
        CREATE INDEX IF NOT EXISTS idx_access_reviews_due_date ON access_reviews(due_date);
        CREATE INDEX IF NOT EXISTS idx_access_reviews_reviewer_id ON access_reviews(reviewer_id);
        
        CREATE INDEX IF NOT EXISTS idx_access_review_items_review_id ON access_review_items(review_id);
        CREATE INDEX IF NOT EXISTS idx_access_review_items_user_id ON access_review_items(user_id);
        CREATE INDEX IF NOT EXISTS idx_access_review_items_status ON access_review_items(status);
        
        CREATE INDEX IF NOT EXISTS idx_support_sessions_tenant_id ON support_sessions(tenant_id);
        CREATE INDEX IF NOT EXISTS idx_support_sessions_status ON support_sessions(status);
        CREATE INDEX IF NOT EXISTS idx_support_sessions_learner_id ON support_sessions(learner_id);
        CREATE INDEX IF NOT EXISTS idx_support_sessions_guardian_id ON support_sessions(guardian_id);
        CREATE INDEX IF NOT EXISTS idx_support_sessions_support_agent_id ON support_sessions(support_agent_id);
        CREATE INDEX IF NOT EXISTS idx_support_sessions_token_expires_at ON support_sessions(token_expires_at);
    """)
    
    logger.info("Audit database tables created successfully")


async def log_audit_event(
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
    target_classification: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    pool: Optional[Pool] = None
) -> UUID:
    """Log an audit event to the database"""
    
    if pool is None:
        pool = await get_db_pool()
    
    event = AuditEvent(
        event_type=event_type,
        severity=severity,
        action=action,
        resource=resource,
        outcome=outcome,
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
        reason=reason,
        metadata=metadata or {}
    )
    
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO audit_events (
                id, timestamp, event_type, severity,
                actor_id, actor_type, actor_email, actor_ip, actor_user_agent,
                target_id, target_type, target_classification,
                tenant_id, session_id, request_id,
                action, resource, outcome, reason, metadata, retention_days
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21
            )
            """,
            event.id, event.timestamp, event.event_type.value, event.severity.value,
            event.actor_id, event.actor_type.value if event.actor_type else None, 
            event.actor_email, event.actor_ip, event.actor_user_agent,
            event.target_id, event.target_type, event.target_classification.value if event.target_classification else None,
            event.tenant_id, event.session_id, event.request_id,
            event.action, event.resource, event.outcome, event.reason, event.metadata, event.retention_days
        )
    
    logger.debug("Audit event logged", event_id=str(event.id), event_type=event_type.value, action=action)
    return event.id


async def log_data_access(
    user_id: UUID,
    user_role: UserRole,
    user_email: str,
    data_type: str,
    operation: str,
    purpose: str,
    tenant_id: UUID,
    session_id: str,
    data_id: Optional[UUID] = None,
    data_classification: str = "internal",
    endpoint: Optional[str] = None,
    sql_query_hash: Optional[str] = None,
    justification: Optional[str] = None,
    ip_address: Optional[str] = None,
    records_affected: int = 0,
    success: bool = True,
    error_message: Optional[str] = None,
    pool: Optional[Pool] = None
) -> UUID:
    """Log sensitive data access"""
    
    if pool is None:
        pool = await get_db_pool()
    
    from uuid import uuid4
    log_id = uuid4()
    
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO data_access_logs (
                id, timestamp, user_id, user_role, user_email,
                data_type, data_id, data_classification,
                operation, endpoint, sql_query_hash,
                purpose, justification, tenant_id, session_id, ip_address,
                records_affected, success, error_message
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
            )
            """,
            log_id, datetime.utcnow(), user_id, user_role.value, user_email,
            data_type, data_id, data_classification,
            operation, endpoint, sql_query_hash,
            purpose, justification, tenant_id, session_id, ip_address,
            records_affected, success, error_message
        )
    
    logger.debug("Data access logged", log_id=str(log_id), user_id=str(user_id), data_type=data_type, operation=operation)
    return log_id
