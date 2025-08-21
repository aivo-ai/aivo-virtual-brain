"""
Database configuration and connection management for AIVO Admin Service
"""

import asyncpg
import aioredis
from typing import AsyncGenerator
import logging
from contextlib import asynccontextmanager

from app.config import settings

logger = logging.getLogger(__name__)

# Global connection pools
pg_pool = None
redis_pool = None


async def init_db():
    """Initialize database connections"""
    global pg_pool, redis_pool
    
    try:
        # Initialize PostgreSQL connection pool
        pg_pool = await asyncpg.create_pool(
            settings.DATABASE_URL,
            min_size=5,
            max_size=settings.DATABASE_POOL_SIZE,
            command_timeout=60,
            server_settings={
                'application_name': 'aivo-admin-svc',
                'search_path': 'public'
            }
        )
        logger.info("PostgreSQL connection pool initialized")
        
        # Initialize Redis connection pool
        redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
            decode_responses=True
        )
        logger.info("Redis connection pool initialized")
        
        # Run database migrations if needed
        await _run_migrations()
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_db():
    """Close database connections"""
    global pg_pool, redis_pool
    
    if pg_pool:
        await pg_pool.close()
        logger.info("PostgreSQL connection pool closed")
    
    if redis_pool:
        await redis_pool.disconnect()
        logger.info("Redis connection pool closed")


@asynccontextmanager
async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Get database connection from pool"""
    if not pg_pool:
        raise RuntimeError("Database pool not initialized")
    
    async with pg_pool.acquire() as connection:
        yield connection


async def get_redis() -> aioredis.Redis:
    """Get Redis connection"""
    if not redis_pool:
        raise RuntimeError("Redis pool not initialized")
    
    return aioredis.Redis(connection_pool=redis_pool)


async def _run_migrations():
    """Run database migrations"""
    migrations = [
        _create_admin_sessions_table,
        _create_audit_events_table,
        _create_support_sessions_table,
        _create_consent_tokens_table,
        _create_admin_actions_table
    ]
    
    async with get_db() as db:
        for migration in migrations:
            try:
                await migration(db)
                logger.info(f"Migration {migration.__name__} completed")
            except Exception as e:
                logger.error(f"Migration {migration.__name__} failed: {e}")
                # Continue with other migrations


async def _create_admin_sessions_table(db: asyncpg.Connection):
    """Create admin sessions table"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS admin_sessions (
            session_id UUID PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            email VARCHAR(255) NOT NULL,
            roles TEXT[] NOT NULL,
            tenant_id VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            ip_address INET,
            user_agent TEXT,
            
            INDEX idx_admin_sessions_user_id ON admin_sessions(user_id),
            INDEX idx_admin_sessions_expires_at ON admin_sessions(expires_at),
            INDEX idx_admin_sessions_active ON admin_sessions(is_active, expires_at)
        )
    """)


async def _create_audit_events_table(db: asyncpg.Connection):
    """Create audit events table"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS audit_events (
            event_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_type VARCHAR(100) NOT NULL,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            user_id VARCHAR(255),
            session_id UUID,
            ip_address INET,
            user_agent TEXT,
            resource_type VARCHAR(100),
            resource_id VARCHAR(255),
            action VARCHAR(100) NOT NULL,
            outcome VARCHAR(50) NOT NULL,
            details JSONB DEFAULT '{}',
            tenant_id VARCHAR(255),
            
            INDEX idx_audit_events_timestamp ON audit_events(timestamp DESC),
            INDEX idx_audit_events_user_id ON audit_events(user_id, timestamp DESC),
            INDEX idx_audit_events_event_type ON audit_events(event_type, timestamp DESC),
            INDEX idx_audit_events_outcome ON audit_events(outcome, timestamp DESC),
            INDEX idx_audit_events_tenant_id ON audit_events(tenant_id, timestamp DESC)
        )
    """)


async def _create_support_sessions_table(db: asyncpg.Connection):
    """Create support sessions table"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS support_sessions (
            session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            learner_id VARCHAR(255) NOT NULL,
            staff_user_id VARCHAR(255) NOT NULL,
            purpose TEXT NOT NULL,
            urgency VARCHAR(50) NOT NULL DEFAULT 'normal',
            consent_token VARCHAR(512),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            accessed_data TEXT[] DEFAULT '{}',
            actions_performed TEXT[] DEFAULT '{}',
            is_active BOOLEAN DEFAULT TRUE,
            closed_at TIMESTAMP WITH TIME ZONE,
            closure_reason TEXT,
            
            INDEX idx_support_sessions_learner_id ON support_sessions(learner_id),
            INDEX idx_support_sessions_staff_user_id ON support_sessions(staff_user_id),
            INDEX idx_support_sessions_active ON support_sessions(is_active, expires_at),
            INDEX idx_support_sessions_created_at ON support_sessions(created_at DESC)
        )
    """)


async def _create_consent_tokens_table(db: asyncpg.Connection):
    """Create consent tokens table"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS consent_tokens (
            token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            learner_id VARCHAR(255) NOT NULL,
            guardian_id VARCHAR(255),
            granted_by VARCHAR(255) NOT NULL,
            purpose TEXT NOT NULL,
            data_types TEXT[] NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
            usage_count INTEGER DEFAULT 0,
            max_usage INTEGER DEFAULT 10,
            is_revoked BOOLEAN DEFAULT FALSE,
            revoked_at TIMESTAMP WITH TIME ZONE,
            revoked_by VARCHAR(255),
            
            INDEX idx_consent_tokens_learner_id ON consent_tokens(learner_id),
            INDEX idx_consent_tokens_expires_at ON consent_tokens(expires_at),
            INDEX idx_consent_tokens_active ON consent_tokens(is_revoked, expires_at)
        )
    """)


async def _create_admin_actions_table(db: asyncpg.Connection):
    """Create admin actions log table"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS admin_actions (
            action_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id VARCHAR(255) NOT NULL,
            session_id UUID,
            action_type VARCHAR(100) NOT NULL,
            target_resource VARCHAR(255),
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            success BOOLEAN NOT NULL,
            details JSONB DEFAULT '{}',
            ip_address INET,
            user_agent TEXT,
            tenant_id VARCHAR(255),
            
            INDEX idx_admin_actions_user_id ON admin_actions(user_id, timestamp DESC),
            INDEX idx_admin_actions_timestamp ON admin_actions(timestamp DESC),
            INDEX idx_admin_actions_action_type ON admin_actions(action_type, timestamp DESC),
            INDEX idx_admin_actions_success ON admin_actions(success, timestamp DESC)
        )
    """)


# Database utility functions
async def execute_query(query: str, *args) -> list:
    """Execute a query and return results"""
    async with get_db() as db:
        return await db.fetch(query, *args)


async def execute_single(query: str, *args):
    """Execute a query and return single result"""
    async with get_db() as db:
        return await db.fetchrow(query, *args)


async def execute_command(query: str, *args) -> str:
    """Execute a command (INSERT, UPDATE, DELETE)"""
    async with get_db() as db:
        return await db.execute(query, *args)


async def execute_transaction(queries: list):
    """Execute multiple queries in a transaction"""
    async with get_db() as db:
        async with db.transaction():
            results = []
            for query, args in queries:
                result = await db.execute(query, *args)
                results.append(result)
            return results


# Redis utility functions
async def cache_set(key: str, value: str, expire: int = 3600):
    """Set cache value with expiration"""
    redis = await get_redis()
    await redis.setex(key, expire, value)


async def cache_get(key: str) -> str:
    """Get cache value"""
    redis = await get_redis()
    return await redis.get(key)


async def cache_delete(key: str):
    """Delete cache key"""
    redis = await get_redis()
    await redis.delete(key)


async def cache_exists(key: str) -> bool:
    """Check if cache key exists"""
    redis = await get_redis()
    return await redis.exists(key)


# Health check functions
async def check_database_health() -> bool:
    """Check database connectivity"""
    try:
        async with get_db() as db:
            await db.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def check_redis_health() -> bool:
    """Check Redis connectivity"""
    try:
        redis = await get_redis()
        await redis.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False
