"""
Chat Service Database Configuration
SQLAlchemy setup with async support and connection pooling
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import event
from typing import AsyncGenerator
import logging

from .config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create async engine with connection pooling
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_timeout=settings.database_pool_timeout,
    pool_pre_ping=True,  # Validate connections before use
    echo=settings.enable_sql_logging,  # Log SQL queries if enabled
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session
    Ensures proper session lifecycle management
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db_session() -> AsyncSession:
    """
    Get a database session for direct use
    Remember to close the session manually
    """
    return AsyncSessionLocal()


# Database event listeners for enhanced security and compliance

@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set database pragmas for security (if using SQLite)"""
    if "sqlite" in str(engine.url):
        cursor = dbapi_connection.cursor()
        # Enable foreign key constraints
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log SQL queries for security auditing"""
    if settings.enable_sql_logging:
        logger.debug(f"SQL: {statement}")
        if parameters:
            logger.debug(f"Parameters: {parameters}")


# Health check functions

async def check_database_health() -> bool:
    """
    Check if the database is healthy
    Returns True if database is accessible, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            # Simple query to test connection
            result = await session.execute("SELECT 1")
            return result.scalar() == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


async def get_database_info() -> dict:
    """
    Get database information for monitoring
    Returns connection pool stats and database version
    """
    try:
        info = {
            "pool_size": engine.pool.size(),
            "checked_in": engine.pool.checkedin(),
            "checked_out": engine.pool.checkedout(),
            "overflow": engine.pool.overflow(),
            "url": str(engine.url).replace(engine.url.password or "", "****"),
        }
        
        # Get database version
        async with AsyncSessionLocal() as session:
            if "postgresql" in str(engine.url):
                result = await session.execute("SELECT version()")
                info["version"] = result.scalar()
            elif "sqlite" in str(engine.url):
                result = await session.execute("SELECT sqlite_version()")
                info["version"] = f"SQLite {result.scalar()}"
                
        return info
    except Exception as e:
        logger.error(f"Failed to get database info: {e}")
        return {"error": str(e)}


# Cleanup function for graceful shutdown

async def cleanup_database():
    """
    Clean up database connections on shutdown
    """
    try:
        await engine.dispose()
        logger.info("Database connections cleaned up")
    except Exception as e:
        logger.error(f"Error cleaning up database: {e}")


# Transaction helpers

async def execute_in_transaction(func, *args, **kwargs):
    """
    Execute a function within a database transaction
    Automatically handles commit/rollback
    """
    async with AsyncSessionLocal() as session:
        try:
            result = await func(session, *args, **kwargs)
            await session.commit()
            return result
        except Exception as e:
            await session.rollback()
            logger.error(f"Transaction failed: {e}")
            raise


# Connection testing for startup

async def test_database_connection():
    """
    Test database connection during startup
    Raises exception if connection fails
    """
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connectivity
            await session.execute("SELECT 1")
            
            # Test that our models can be accessed
            from .models import Thread, Message
            
            logger.info("Database connection test successful")
            return True
            
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        raise Exception(f"Cannot connect to database: {e}")


async def create_tables():
    """
    Create all database tables
    """
    try:
        # Import models to ensure they're registered
        from . import models
        
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


# Tenant isolation helpers

def apply_tenant_filter(query, tenant_id: str):
    """
    Apply tenant isolation filter to queries
    Ensures data is scoped to the correct tenant
    """
    return query.filter_by(tenant_id=tenant_id)


async def filter_by_tenant(query, model, tenant_id: str):
    """
    Helper function to filter queries by tenant ID
    """
    return query.where(model.tenant_id == tenant_id)


def validate_tenant_access(obj, tenant_id: str) -> bool:
    """
    Validate that an object belongs to the specified tenant
    Returns True if access is allowed, False otherwise
    """
    return getattr(obj, 'tenant_id', None) == tenant_id
