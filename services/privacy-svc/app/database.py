"""
Database connection and utilities
"""

import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import Optional
import structlog

logger = structlog.get_logger()

# Global database pool
db_pool: Optional[asyncpg.Pool] = None

async def init_db(database_url: str) -> asyncpg.Pool:
    """Initialize database connection pool"""
    global db_pool
    
    # Convert SQLAlchemy URL to asyncpg format
    if database_url.startswith("postgresql://"):
        asyncpg_url = database_url.replace("postgresql://", "postgresql://", 1)
    else:
        asyncpg_url = database_url
    
    db_pool = await asyncpg.create_pool(
        asyncpg_url,
        min_size=5,
        max_size=20,
        command_timeout=30,
        server_settings={
            'jit': 'off',
            'application_name': 'privacy-svc'
        }
    )
    
    # Create tables if they don't exist
    await create_tables()
    
    return db_pool

async def get_db_pool() -> asyncpg.Pool:
    """Get database pool"""
    if db_pool is None:
        raise RuntimeError("Database not initialized")
    return db_pool

async def create_tables():
    """Create database tables"""
    create_tables_sql = """
    -- Privacy requests table
    CREATE TABLE IF NOT EXISTS privacy_requests (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        learner_id UUID NOT NULL,
        request_type VARCHAR(20) NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ,
        completed_at TIMESTAMPTZ,
        expires_at TIMESTAMPTZ,
        
        data_categories JSONB,
        export_format VARCHAR(20),
        include_metadata BOOLEAN DEFAULT TRUE,
        
        file_path VARCHAR(500),
        file_size_bytes INTEGER,
        records_processed INTEGER DEFAULT 0,
        error_message TEXT,
        
        requested_by VARCHAR(100) NOT NULL,
        requester_ip VARCHAR(45),
        processed_by VARCHAR(100)
    );
    
    CREATE INDEX IF NOT EXISTS idx_privacy_requests_learner_id ON privacy_requests(learner_id);
    CREATE INDEX IF NOT EXISTS idx_privacy_requests_status ON privacy_requests(status);
    CREATE INDEX IF NOT EXISTS idx_privacy_requests_created_at ON privacy_requests(created_at);
    
    -- Audit log table
    CREATE TABLE IF NOT EXISTS privacy_audit_log (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        request_id UUID,
        learner_id UUID,
        event_type VARCHAR(50) NOT NULL,
        event_data JSONB,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        user_id VARCHAR(100),
        ip_address VARCHAR(45),
        user_agent VARCHAR(500)
    );
    
    CREATE INDEX IF NOT EXISTS idx_audit_log_request_id ON privacy_audit_log(request_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_learner_id ON privacy_audit_log(learner_id);
    CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON privacy_audit_log(timestamp);
    
    -- Data retention policies table
    CREATE TABLE IF NOT EXISTS data_retention_policies (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        data_category VARCHAR(50) NOT NULL UNIQUE,
        retention_days INTEGER NOT NULL,
        checkpoint_count INTEGER DEFAULT 3,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ,
        policy_description TEXT,
        legal_basis VARCHAR(200),
        active BOOLEAN DEFAULT TRUE
    );
    
    -- Insert default retention policies
    INSERT INTO data_retention_policies (data_category, retention_days, checkpoint_count, policy_description, legal_basis)
    VALUES 
        ('profile', 2555, 3, 'User profile data retained for 7 years', 'Contract performance'),
        ('learning', 1825, 3, 'Learning progress retained for 5 years', 'Educational records'),
        ('progress', 1825, 3, 'Progress tracking retained for 5 years', 'Educational records'),
        ('assessments', 2555, 5, 'Assessment results retained for 7 years', 'Legal obligation'),
        ('interactions', 365, 2, 'Interaction logs retained for 1 year', 'Legitimate interest'),
        ('analytics', 730, 1, 'Analytics data retained for 2 years', 'Legitimate interest'),
        ('system', 90, 1, 'System logs retained for 90 days', 'Legitimate interest')
    ON CONFLICT (data_category) DO NOTHING;
    
    -- Triggers for updated_at
    CREATE OR REPLACE FUNCTION update_updated_at_column()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = NOW();
        RETURN NEW;
    END;
    $$ language 'plpgsql';
    
    DROP TRIGGER IF EXISTS update_privacy_requests_updated_at ON privacy_requests;
    CREATE TRIGGER update_privacy_requests_updated_at
        BEFORE UPDATE ON privacy_requests
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
        
    DROP TRIGGER IF EXISTS update_retention_policies_updated_at ON data_retention_policies;
    CREATE TRIGGER update_retention_policies_updated_at
        BEFORE UPDATE ON data_retention_policies
        FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
    """
    
    async with db_pool.acquire() as conn:
        await conn.execute(create_tables_sql)
        logger.info("Database tables created/verified")

async def log_audit_event(
    event_type: str,
    learner_id: Optional[str] = None,
    request_id: Optional[str] = None,
    event_data: Optional[dict] = None,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """Log an audit event"""
    async with db_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO privacy_audit_log 
            (request_id, learner_id, event_type, event_data, user_id, ip_address, user_agent)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            request_id, learner_id, event_type, event_data, user_id, ip_address, user_agent
        )
