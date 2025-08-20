"""
Database connection and management for the FinOps service.

This module provides database connection pooling, session management, and table creation
for cost tracking, budget management, and financial operations.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

from .models import (
    UsageEvent,
    Budget,
    BudgetAlert,
    ProviderPricing,
    CostSummary,
    CostForecast,
    CostOptimization
)
from .config import config

logger = logging.getLogger(__name__)

# SQLAlchemy base
Base = declarative_base()

# Global engine and session factory
engine = None
async_session_factory = None
connection_pool = None


async def init_database() -> None:
    """Initialize database connection and create tables."""
    global engine, async_session_factory, connection_pool
    
    try:
        # Create async engine with connection pooling
        database_url = config.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
        
        engine = create_async_engine(
            database_url,
            echo=config.DEBUG,
            pool_size=20,
            max_overflow=30,
            pool_pre_ping=True,
            pool_recycle=3600,
            connect_args={
                "server_settings": {
                    "application_name": "finops-service",
                }
            }
        )
        
        # Create session factory
        async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Create connection pool for raw queries
        connection_pool = await asyncpg.create_pool(
            config.DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=60,
            server_settings={
                "application_name": "finops-service-pool",
            }
        )
        
        # Create tables and indexes
        await create_tables()
        await create_indexes()
        
        logger.info("Database initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


async def close_database() -> None:
    """Close database connections."""
    global engine, connection_pool
    
    try:
        if connection_pool:
            await connection_pool.close()
            connection_pool = None
            
        if engine:
            await engine.dispose()
            engine = None
            
        logger.info("Database connections closed")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session with automatic cleanup."""
    if not async_session_factory:
        raise RuntimeError("Database not initialized")
        
    async with async_session_factory() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_connection():
    """Get raw database connection from pool."""
    if not connection_pool:
        raise RuntimeError("Connection pool not initialized")
        
    async with connection_pool.acquire() as connection:
        yield connection


async def create_tables() -> None:
    """Create all database tables with proper schemas."""
    if not engine:
        raise RuntimeError("Database engine not initialized")
    
    # Define table creation SQL
    create_tables_sql = """
    -- Usage Events Table
    CREATE TABLE IF NOT EXISTS usage_events (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id VARCHAR(255) NOT NULL,
        learner_id VARCHAR(255),
        service_name VARCHAR(255) NOT NULL,
        session_id VARCHAR(255),
        provider VARCHAR(50) NOT NULL,
        model_name VARCHAR(255) NOT NULL,
        model_type VARCHAR(50) NOT NULL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        total_tokens INTEGER GENERATED ALWAYS AS (input_tokens + output_tokens) STORED,
        request_count INTEGER DEFAULT 1,
        images_processed INTEGER DEFAULT 0,
        audio_minutes DECIMAL(10,3) DEFAULT 0,
        storage_gb DECIMAL(10,3) DEFAULT 0,
        calculated_cost DECIMAL(15,6) NOT NULL,
        cost_category VARCHAR(50) DEFAULT 'inference',
        currency VARCHAR(3) DEFAULT 'USD',
        processing_duration_ms INTEGER,
        metadata JSONB,
        timestamp TIMESTAMPTZ DEFAULT NOW(),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Budgets Table
    CREATE TABLE IF NOT EXISTS budgets (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        budget_type VARCHAR(20) NOT NULL,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        tenant_id VARCHAR(255),
        learner_id VARCHAR(255),
        service_name VARCHAR(255),
        model_name VARCHAR(255),
        amount DECIMAL(15,2) NOT NULL,
        period VARCHAR(20) NOT NULL,
        currency VARCHAR(3) DEFAULT 'USD',
        start_date TIMESTAMPTZ NOT NULL,
        end_date TIMESTAMPTZ NOT NULL,
        is_recurring BOOLEAN DEFAULT true,
        alert_thresholds DECIMAL(5,2)[] DEFAULT ARRAY[50.0, 75.0, 90.0, 100.0],
        alert_channels VARCHAR(20)[] DEFAULT ARRAY['email'],
        alert_recipients TEXT[],
        webhook_url TEXT,
        current_spend DECIMAL(15,6) DEFAULT 0,
        last_alert_sent TIMESTAMPTZ,
        last_alert_threshold DECIMAL(5,2),
        is_active BOOLEAN DEFAULT true,
        is_exceeded BOOLEAN DEFAULT false,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Budget Alerts Table
    CREATE TABLE IF NOT EXISTS budget_alerts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        budget_id UUID NOT NULL REFERENCES budgets(id) ON DELETE CASCADE,
        budget_name VARCHAR(255) NOT NULL,
        severity VARCHAR(20) NOT NULL,
        threshold_percentage DECIMAL(5,2) NOT NULL,
        current_spend DECIMAL(15,6) NOT NULL,
        budget_amount DECIMAL(15,2) NOT NULL,
        percentage_used DECIMAL(5,2) NOT NULL,
        tenant_id VARCHAR(255),
        learner_id VARCHAR(255),
        period_start TIMESTAMPTZ NOT NULL,
        period_end TIMESTAMPTZ NOT NULL,
        channels_sent VARCHAR(20)[],
        recipients_notified TEXT[],
        alert_title VARCHAR(500) NOT NULL,
        alert_message TEXT NOT NULL,
        is_acknowledged BOOLEAN DEFAULT false,
        acknowledged_by VARCHAR(255),
        acknowledged_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Provider Pricing Table
    CREATE TABLE IF NOT EXISTS provider_pricing (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        provider VARCHAR(50) NOT NULL,
        model_name VARCHAR(255) NOT NULL,
        model_type VARCHAR(50) NOT NULL,
        input_token_price DECIMAL(12,8) NOT NULL,
        output_token_price DECIMAL(12,8) NOT NULL,
        image_price DECIMAL(10,6),
        audio_price DECIMAL(10,6),
        request_price DECIMAL(10,6) DEFAULT 0,
        storage_price DECIMAL(10,6),
        currency VARCHAR(3) DEFAULT 'USD',
        effective_date TIMESTAMPTZ NOT NULL,
        expires_date TIMESTAMPTZ,
        is_active BOOLEAN DEFAULT true,
        rate_limit_rpm INTEGER,
        rate_limit_tpm INTEGER,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(provider, model_name, effective_date)
    );

    -- Cost Summaries Table (for pre-calculated aggregates)
    CREATE TABLE IF NOT EXISTS cost_summaries (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id VARCHAR(255),
        learner_id VARCHAR(255),
        service_name VARCHAR(255),
        period_start TIMESTAMPTZ NOT NULL,
        period_end TIMESTAMPTZ NOT NULL,
        period_type VARCHAR(10) NOT NULL,
        total_cost DECIMAL(15,6) NOT NULL,
        cost_by_provider JSONB,
        cost_by_model JSONB,
        cost_by_category JSONB,
        total_tokens BIGINT DEFAULT 0,
        total_requests BIGINT DEFAULT 0,
        unique_sessions INTEGER DEFAULT 0,
        avg_cost_per_token DECIMAL(12,8),
        avg_cost_per_request DECIMAL(10,6),
        avg_cost_per_session DECIMAL(10,6),
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW(),
        UNIQUE(tenant_id, learner_id, service_name, period_start, period_type)
    );

    -- Cost Forecasts Table
    CREATE TABLE IF NOT EXISTS cost_forecasts (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id VARCHAR(255),
        learner_id VARCHAR(255),
        service_name VARCHAR(255),
        forecast_start TIMESTAMPTZ NOT NULL,
        forecast_end TIMESTAMPTZ NOT NULL,
        baseline_start TIMESTAMPTZ NOT NULL,
        baseline_end TIMESTAMPTZ NOT NULL,
        baseline_cost DECIMAL(15,6) NOT NULL,
        predicted_cost DECIMAL(15,6) NOT NULL,
        confidence_interval_low DECIMAL(15,6) NOT NULL,
        confidence_interval_high DECIMAL(15,6) NOT NULL,
        confidence_level DECIMAL(3,2) DEFAULT 0.95,
        growth_rate DECIMAL(5,2),
        trend_direction VARCHAR(20),
        seasonality_factor DECIMAL(5,3),
        forecast_model VARCHAR(50),
        model_accuracy DECIMAL(3,2),
        created_at TIMESTAMPTZ DEFAULT NOW()
    );

    -- Cost Optimizations Table
    CREATE TABLE IF NOT EXISTS cost_optimizations (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        tenant_id VARCHAR(255),
        service_name VARCHAR(255),
        recommendation_type VARCHAR(50) NOT NULL,
        title VARCHAR(500) NOT NULL,
        description TEXT NOT NULL,
        current_monthly_cost DECIMAL(15,2) NOT NULL,
        projected_monthly_cost DECIMAL(15,2) NOT NULL,
        potential_savings DECIMAL(15,2) NOT NULL,
        savings_percentage DECIMAL(5,2) NOT NULL,
        implementation_effort VARCHAR(20),
        implementation_time VARCHAR(100),
        risk_level VARCHAR(20),
        recommended_models TEXT[],
        recommended_settings JSONB,
        status VARCHAR(20) DEFAULT 'pending',
        approved_by VARCHAR(255),
        implemented_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT NOW(),
        updated_at TIMESTAMPTZ DEFAULT NOW()
    );
    """
    
    async with engine.begin() as conn:
        await conn.execute(text(create_tables_sql))
        logger.info("Database tables created successfully")


async def create_indexes() -> None:
    """Create database indexes for optimal query performance."""
    if not engine:
        raise RuntimeError("Database engine not initialized")
    
    indexes_sql = """
    -- Usage Events Indexes
    CREATE INDEX IF NOT EXISTS idx_usage_events_tenant_timestamp 
        ON usage_events(tenant_id, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_usage_events_learner_timestamp 
        ON usage_events(learner_id, timestamp DESC) WHERE learner_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_usage_events_service_timestamp 
        ON usage_events(service_name, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_usage_events_provider_model 
        ON usage_events(provider, model_name);
    CREATE INDEX IF NOT EXISTS idx_usage_events_session 
        ON usage_events(session_id) WHERE session_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_usage_events_cost_category 
        ON usage_events(cost_category, timestamp DESC);
    CREATE INDEX IF NOT EXISTS idx_usage_events_metadata_gin 
        ON usage_events USING gin(metadata);
    
    -- Budgets Indexes
    CREATE INDEX IF NOT EXISTS idx_budgets_tenant_active 
        ON budgets(tenant_id, is_active) WHERE tenant_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_budgets_learner_active 
        ON budgets(learner_id, is_active) WHERE learner_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_budgets_service_active 
        ON budgets(service_name, is_active) WHERE service_name IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_budgets_type_period 
        ON budgets(budget_type, period);
    CREATE INDEX IF NOT EXISTS idx_budgets_dates 
        ON budgets(start_date, end_date);
    CREATE INDEX IF NOT EXISTS idx_budgets_exceeded 
        ON budgets(is_exceeded, is_active);
    
    -- Budget Alerts Indexes
    CREATE INDEX IF NOT EXISTS idx_budget_alerts_budget_id 
        ON budget_alerts(budget_id);
    CREATE INDEX IF NOT EXISTS idx_budget_alerts_tenant_severity 
        ON budget_alerts(tenant_id, severity, created_at DESC) WHERE tenant_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_budget_alerts_acknowledged 
        ON budget_alerts(is_acknowledged, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_budget_alerts_created 
        ON budget_alerts(created_at DESC);
    
    -- Provider Pricing Indexes
    CREATE INDEX IF NOT EXISTS idx_provider_pricing_active 
        ON provider_pricing(provider, model_name, is_active);
    CREATE INDEX IF NOT EXISTS idx_provider_pricing_dates 
        ON provider_pricing(effective_date DESC, expires_date);
    CREATE INDEX IF NOT EXISTS idx_provider_pricing_model_type 
        ON provider_pricing(model_type, provider);
    
    -- Cost Summaries Indexes
    CREATE INDEX IF NOT EXISTS idx_cost_summaries_tenant_period 
        ON cost_summaries(tenant_id, period_start DESC, period_type) WHERE tenant_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_summaries_learner_period 
        ON cost_summaries(learner_id, period_start DESC, period_type) WHERE learner_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_summaries_service_period 
        ON cost_summaries(service_name, period_start DESC, period_type) WHERE service_name IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_summaries_period_type 
        ON cost_summaries(period_type, period_start DESC);
    
    -- Cost Forecasts Indexes
    CREATE INDEX IF NOT EXISTS idx_cost_forecasts_tenant_forecast 
        ON cost_forecasts(tenant_id, forecast_start DESC) WHERE tenant_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_forecasts_learner_forecast 
        ON cost_forecasts(learner_id, forecast_start DESC) WHERE learner_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_forecasts_service_forecast 
        ON cost_forecasts(service_name, forecast_start DESC) WHERE service_name IS NOT NULL;
    
    -- Cost Optimizations Indexes
    CREATE INDEX IF NOT EXISTS idx_cost_optimizations_tenant_status 
        ON cost_optimizations(tenant_id, status, created_at DESC) WHERE tenant_id IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_optimizations_service_status 
        ON cost_optimizations(service_name, status, created_at DESC) WHERE service_name IS NOT NULL;
    CREATE INDEX IF NOT EXISTS idx_cost_optimizations_type_status 
        ON cost_optimizations(recommendation_type, status);
    CREATE INDEX IF NOT EXISTS idx_cost_optimizations_savings 
        ON cost_optimizations(savings_percentage DESC, status);
    """
    
    async with engine.begin() as conn:
        await conn.execute(text(indexes_sql))
        logger.info("Database indexes created successfully")


async def check_database_health() -> dict:
    """Check database connection health and return status."""
    try:
        if not engine:
            return {
                "status": "unhealthy",
                "error": "Database engine not initialized"
            }
        
        # Test connection with simple query
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as health_check"))
            health_check = result.scalar()
            
        if health_check == 1:
            # Get database statistics
            async with get_db_connection() as conn:
                stats = await conn.fetchrow("""
                    SELECT 
                        (SELECT COUNT(*) FROM usage_events WHERE created_at > NOW() - INTERVAL '24 hours') as daily_events,
                        (SELECT COUNT(*) FROM budgets WHERE is_active = true) as active_budgets,
                        (SELECT COUNT(*) FROM budget_alerts WHERE is_acknowledged = false) as pending_alerts,
                        (SELECT MAX(timestamp) FROM usage_events) as latest_event
                """)
                
            return {
                "status": "healthy",
                "daily_events": stats["daily_events"],
                "active_budgets": stats["active_budgets"],
                "pending_alerts": stats["pending_alerts"],
                "latest_event": stats["latest_event"].isoformat() if stats["latest_event"] else None
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Database health check failed"
            }
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def get_database_metrics() -> dict:
    """Get database metrics for monitoring."""
    try:
        async with get_db_connection() as conn:
            metrics = await conn.fetchrow("""
                SELECT 
                    pg_database_size(current_database()) as db_size_bytes,
                    (SELECT COUNT(*) FROM usage_events) as total_usage_events,
                    (SELECT COUNT(*) FROM budgets) as total_budgets,
                    (SELECT COUNT(*) FROM budget_alerts) as total_alerts,
                    (SELECT COUNT(*) FROM provider_pricing WHERE is_active = true) as active_pricing_records,
                    (SELECT AVG(calculated_cost) FROM usage_events WHERE timestamp > NOW() - INTERVAL '24 hours') as avg_daily_cost
            """)
            
        return {
            "database_size_bytes": int(metrics["db_size_bytes"]),
            "total_usage_events": metrics["total_usage_events"],
            "total_budgets": metrics["total_budgets"],
            "total_alerts": metrics["total_alerts"],
            "active_pricing_records": metrics["active_pricing_records"],
            "avg_daily_cost": float(metrics["avg_daily_cost"] or 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to get database metrics: {e}")
        return {}


async def cleanup_old_data() -> None:
    """Clean up old data based on retention policies."""
    try:
        retention_days = config.DATA_RETENTION_DAYS
        
        async with get_db_connection() as conn:
            # Clean up old usage events (keep detailed events for retention period)
            deleted_events = await conn.execute(
                "DELETE FROM usage_events WHERE created_at < NOW() - INTERVAL '%s days'",
                retention_days
            )
            
            # Clean up old budget alerts (keep alerts for 90 days)
            deleted_alerts = await conn.execute(
                "DELETE FROM budget_alerts WHERE created_at < NOW() - INTERVAL '90 days'"
            )
            
            # Clean up expired pricing data
            deleted_pricing = await conn.execute(
                "DELETE FROM provider_pricing WHERE expires_date < NOW() AND is_active = false"
            )
            
            # Clean up old forecasts (keep for 30 days)
            deleted_forecasts = await conn.execute(
                "DELETE FROM cost_forecasts WHERE created_at < NOW() - INTERVAL '30 days'"
            )
            
        logger.info(f"Data cleanup completed: {deleted_events} events, {deleted_alerts} alerts, "
                   f"{deleted_pricing} pricing records, {deleted_forecasts} forecasts deleted")
        
    except Exception as e:
        logger.error(f"Data cleanup failed: {e}")


# Connection dependency for FastAPI
async def get_database_session():
    """FastAPI dependency for database sessions."""
    async with get_db_session() as session:
        yield session
